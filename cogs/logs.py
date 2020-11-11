import discord
from discord.ext import commands, tasks
from datetime import datetime
import re

from rcon.commands import Rcon
from rcon.instances import check_perms, Instance
from rcon.logs import ServerLogs, format_log

from utils import Config, base_embed
config = Config()


SECONDS_BETWEEN_CACHE_REFRESH = 60
SECONDS_BETWEEN_CHECKS = 15


class logs(commands.Cog):
    """"View or export logs"""

    def __init__(self, bot):
        self.bot = bot
        self.check_server.start()


    @commands.command(description="Read all chat messages", usage="r!chat")
    @check_perms(logs=True)
    async def chat(self, ctx):
        
        inst = self.bot.cache.instance(ctx.author)
        await self._query(inst)
        messages = ServerLogs(inst.id).get_logs('chat')

        if not messages:
            await ctx.send(f"{config.get('error_message_emoji')} There aren't any recent messages!")
            return

        output = ""
        for log in messages[::-1]:
            timestamp = log['timestamp']
            time = timestamp.strftime("%H:%M")
            content = log['message']          
            message = f"[{time}] {content}\n"

            if len(message + output) + 12 > 2000: break
            elif (datetime.now() - timestamp).total_seconds() > 60*60*24: break
            else: output = message + output
        output = "```json\n" + output + "```"
        await ctx.send(output)
    
    @commands.command(description="Read all chat messages", usage="r!logs ([category]|export)")
    @check_perms(logs=True)
    async def logs(self, ctx, category: str = None):
        
        inst = self.bot.cache.instance(ctx.author)
        await self._query(inst)

        if category != None: category = category.lower()
        if category in ["export", "file"]:
            inst_name = Instance(inst.id).name
            log_file = discord.File(fp=ServerLogs(inst.id).export(), filename=f"{inst_name}_log.txt")
            await ctx.send(file=log_file)

        else:
            logs = ServerLogs(inst.id).get_logs(category)

            if not logs:
                await ctx.send(f"{config.get('error_message_emoji')} No logs could be found!")
                return
            
            output = ""
            for log in logs[::-1]:
                message = format_log(log) + "\n"
                if len(message + output) + 12 > 2000: break
                else: output = message + output

            output = "```json\n" + output + "```"
            await ctx.send(output)


    async def _query(self, inst):
        # Execute a command to receive new chat packets.
        # We can use this opportunity to update the cache,
        # though we don't want to overdo this.
        if (datetime.now() - inst.last_updated).total_seconds() > SECONDS_BETWEEN_CACHE_REFRESH:
            try:
                inst.update()
            except:
                inst.rcon.exec_command("a")
        else:
            inst.rcon.exec_command("a")

        # Grab all the new chat messages
        new_chat_messages = inst.rcon.get_player_chat()
        inst.rcon.clear_player_chat()

        # Parse incoming messages
        # '[ChatAll] [SteamID:12345678901234567] [FP] Clan Member 1 : Hello world! '
        for message in new_chat_messages:
            raw_data = {}
            raw_data['channel'], raw_data['steam_id'], raw_data['name'], raw_data['message'] = re.search(r'\[(.+)\] \[SteamID:(\d{17})\] (.*) : (.*)', message).groups()

            player = inst.get_player(int(raw_data['steam_id']))
            if player:
                faction = inst.team1.faction_short if player.team_id == 1 else inst.team2.faction_short
                squad = player.squad_id

                if raw_data['channel'] == "ChatAdmin":
                    continue

                if raw_data['channel'] == "ChatAll":
                    channel = "All"
                elif raw_data['channel'] == "ChatTeam":
                    channel = faction
                elif raw_data['channel'] == "ChatSquad":
                    channel = f"{faction}/Squad{str(squad)}"
                else:
                    channel = raw_data['channel']
            else:
                channel = "Unknown"
            
            name = raw_data['name']
            text = raw_data['message']

            message = f"[{channel}] {name}: {text}"
            ServerLogs(inst.id).add("chat", message)

            # Do stuff with new messages
            instance = Instance(inst.id)
            config = instance.config
            guild = self.bot.get_guild(config["guild_id"])

            if guild:

                # Trigger words
                channel = guild.get_channel(config["chat_trigger_channel_id"])
                trigger_words = config["chat_trigger_words"].split(",")
                if channel and trigger_words:
                    trigger_mentions = config["chat_trigger_mentions"]
                    for word in trigger_words:
                        word = word.strip().lower()
                        if word in text.lower():
                            description = f"{name}: {text}"
                            embed = base_embed(inst.id, title="New Report", description=description, color=discord.Color.red())
                            await channel.send(trigger_mentions, embed=embed)
                
                # Auto log
                channel = guild.get_channel(config["chat_log_channel_id"])
                if channel:
                    await channel.send(f"**{instance.name}:** {message}")


    @tasks.loop(seconds=SECONDS_BETWEEN_CHECKS)
    async def check_server(self):
        for inst in self.bot.cache.instances.values():
            if inst:
                await self._query(inst)
    @check_server.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(logs(bot))