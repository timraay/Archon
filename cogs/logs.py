import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import re

from rcon.commands import Rcon
from rcon.instances import check_perms, Instance
from rcon.logs import ServerLogs, format_log
from rcon.connection import RconAuthError, RconError
from rcon.cache import ConnectionLost

import logging

from utils import Config, base_embed
config = Config()


SECONDS_BETWEEN_CACHE_REFRESH = 30
SECONDS_BETWEEN_CHECKS = 15


class logs(commands.Cog):
    """View or export logs"""

    def __init__(self, bot):
        self.bot = bot
        self.last_seen_id = {}
        self.trigger_cooldowns = {}

        self.check_server.add_exception_type(Exception)
        self.check_server.start()


    @commands.command(description="Read all chat messages", usage="r!chat")
    @check_perms(logs=True)
    async def chat(self, ctx):
        
        inst = self.bot.cache.instance(ctx.author, ctx.guild.id)
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
    
    @commands.command(description="Read and export logs", usage="r!logs [(<category>|export)]")
    @check_perms(logs=True)
    async def logs(self, ctx, category: str = None):
        
        inst = self.bot.cache.instance(ctx.author, ctx.guild.id)
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
            inst.update()
        else:
            inst.rcon.exec_command("a")

        # Grab all the new chat messages
        new_chat_messages = inst.rcon.get_player_chat()
        inst.rcon.clear_player_chat()

        # Parse incoming messages
        # '[ChatAll] [SteamID:12345678901234567] [FP] Clan Member 1 : Hello world!'
        # '[ChatAdmin] ASQKillDeathRuleset : Player S.T.A.L.K.E.R%s Team Killed Player NUKE'
        # '[SteamID:76561198129591637] (WTH) Dylan has possessed admin camera.'
        for message in new_chat_messages:
            raw_data = {}
            if message.startswith('[ChatAdmin] ASQKillDeathRuleset'):
                # The message is a logged teamkill
                p1_name, p2_name = re.search(r'\[ChatAdmin\] ASQKillDeathRuleset : Player (.*)%s Team Killed Player (.*)', message).groups()
                p1 = inst.get_player(p1_name)
                p2 = inst.get_player(p2_name)
                p1_output = f"{p1_name} ({p1.steam_id})" if p1 else p1_name
                p2_output = f"{p2_name} ({p2.steam_id})" if p2 else p2_name

                message = f"{p1_output} team killed {p2_output}"
                ServerLogs(inst.id).add("teamkill", message)
                continue
            else:
                try: raw_data['channel'], raw_data['steam_id'], raw_data['name'], raw_data['message'] = re.search(r'\[(.+)\] \[SteamID:(\d{17})\] (.*) : (.*)', message).groups()
                except: continue

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
                trigger_channel = guild.get_channel(config["chat_trigger_channel_id"])
                trigger_words = config["chat_trigger_words"].split(",")
                if trigger_channel and trigger_words:
                    trigger_mentions = config["chat_trigger_mentions"]
                    for word in trigger_words:
                        word = word.strip().lower()
                        if word in text.lower():

                            try:
                                last_attempt = self.trigger_cooldowns[player.steam_id]
                                cooldown = int(config['chat_trigger_cooldown'] - (datetime.now() - last_attempt).total_seconds())
                            except KeyError:
                                cooldown = -1
                            if cooldown == 0:
                                # The player sent multiple admin reports in the same period.
                                # Let's not ping the admins twice, because why would we?
                                trigger_mentions = ""
                            
                            if cooldown > 0:
                                # The player tried sending admin reports too fast and is still in cooldown
                                inst.rcon.warn(player.steam_id, f"You're sending reports too fast! Please wait {str(cooldown)}s and try again.")
                                description = f"{name}: {discord.utils.escape_markdown(text)}"
                                embed = base_embed(inst.id, description=description)
                                embed.set_footer(text=f"Cooldown was active for this player ({str(cooldown)}s). He was asked to try again.")
                                await trigger_channel.send(embed=embed)

                            elif len(text.split()) < 3 and config["chat_trigger_require_reason"]:
                                # The player didn't include a reason, which is required
                                inst.rcon.warn(player.steam_id, f"Please include a reason in your '{word}' report and try again.")
                                description = f"{name}: {discord.utils.escape_markdown(text)}"
                                embed = base_embed(inst.id, description=description)
                                embed.set_footer(text="No reason was included in this report. The player was asked to try again.")
                                await trigger_channel.send(embed=embed)

                            else:
                                self.trigger_cooldowns[player.steam_id] = datetime.now()
                                description = f"{name}: {discord.utils.escape_markdown(text)}"
                                embed = base_embed(inst.id, title="New Report", description=description, color=discord.Color.red())
                                if player: embed.set_footer(text="Team ID: %s • Squad ID: %s • Player ID: %s" % (player.team_id, player.squad_id, player.player_id))
                                await trigger_channel.send(trigger_mentions, embed=embed)
                                if config['chat_trigger_confirmation']:
                                    inst.rcon.warn(player.steam_id, config['chat_trigger_confirmation'])
                            
                            break
                
                # Auto log
                chat_channel = guild.get_channel(config["channel_log_chat"])
                if chat_channel:
                    embed = base_embed(instance)
                    title = "{: <20} {}".format("["+channel+"]", name)
                    embed.add_field(name=title, value=discord.utils.escape_markdown(text))
                    
                    embed.set_footer(text=f"Recorded at {datetime.now().strftime('%a, %b %d, %Y %I:%M %p')}")

                    if not player or channel == "Unknown":
                        embed.color = discord.Embed.Empty
                    elif raw_data['channel'] == "ChatAll":
                        embed.color = discord.Color.dark_gray()
                    elif raw_data['channel'] == "ChatTeam":
                        if player.team_id == 1: embed.color = discord.Color.from_rgb(66, 194, 245)
                        else: embed.color = discord.Color.from_rgb(240, 36, 53)
                    elif raw_data['channel'] == "ChatSquad":
                        if player.team_id == 1: embed.color = discord.Color.from_rgb(0, 100, 255)
                        else: embed.color = discord.Color.from_rgb(201, 4, 24)
        
                    await chat_channel.send(embed=embed)


    @tasks.loop(seconds=SECONDS_BETWEEN_CHECKS)
    async def check_server(self):
        for inst in self.bot.cache.instances.values():
            if inst:
                try:
                    await self._query(inst)
                    try:
                        max_id = self.last_seen_id[inst.id]
                    except KeyError:
                        max_id = ServerLogs(inst.id)._get_max_log_id()
                        new_max_id = max_id
                        new_logs = []
                    else:
                        new_max_id, new_logs = ServerLogs(inst.id).get_logs_after(max_id)

                    config = Instance(inst.id).config
                    guild = self.bot.get_guild(config['guild_id'])
                    if guild and new_logs:
                        # Note: Chat logs are handled alongside the triggers
                        channel_joins = guild.get_channel(config['channel_log_joins'])
                        channel_match = guild.get_channel(config['channel_log_match'])
                        channel_rcon = guild.get_channel(config['channel_log_rcon'])
                        channel_teamkills = guild.get_channel(config['channel_log_teamkills'])

                        if channel_rcon:
                            default_embed = base_embed(inst.id)
                            logs = [log for log in new_logs if log['category'] == 'rcon']
                            for log in logs:
                                embed = default_embed
                                embed.color = discord.Color.teal()
                                embed.title = log['message']
                                embed.set_footer(text=f"Recorded at {log['timestamp'].strftime('%a, %b %d, %Y %I:%M %p')}")
                                await channel_rcon.send(embed=embed)
                        if channel_joins:
                            default_embed = base_embed(inst.id)
                            logs = [log for log in new_logs if log['category'] == 'joins']
                            if logs:
                                joins = [log['message'] for log in logs if log['message'].endswith(' connected')]
                                leaves = [log['message'] for log in logs if not log['message'].endswith(' connected')]

                                embed = default_embed
                                embed.set_footer(text=f"Recorded at {logs[-1]['timestamp'].strftime('%a, %b %d, %Y %I:%M %p')}")

                                if joins:    
                                    embed.color = discord.Color.dark_green()
                                    embed.description = "\n".join(joins)
                                    await channel_joins.send(embed=embed)
                                if leaves:    
                                    embed.color = discord.Embed.Empty
                                    embed.description = "\n".join(leaves)
                                    await channel_joins.send(embed=embed)
                        if channel_match:
                            default_embed = base_embed(inst.id)
                            logs = [log for log in new_logs if log['category'] == 'match']
                            for log in logs:
                                embed = default_embed
                                embed.color = discord.Color.from_rgb(255,255,255)
                                embed.title = log['message']
                                embed.set_footer(text=f"Recorded at {log['timestamp'].strftime('%a, %b %d, %Y %I:%M %p')}")
                                await channel_match.send(embed=embed)
                        if channel_teamkills:
                            default_embed = base_embed(inst.id)
                            logs = [log for log in new_logs if log['category'] == 'teamkill']
                            if logs:
                                embed = default_embed
                                embed.set_footer(text=f"Recorded at {logs[-1]['timestamp'].strftime('%a, %b %d, %Y %I:%M %p')}")

                                embed.color = discord.Color.dark_red()
                                embed.description = "\n".join([log['message'] for log in logs])
                                await channel_teamkills.send(embed=embed)

                    self.last_seen_id[inst.id] = new_max_id
                except Exception as e:
                    logging.exception('Inst %s: Unhandled exception whilst updating: %s: %s', inst.id, e.__class__.__name__, e)
                    if isinstance(e, (RconAuthError, ConnectionLost)) and (datetime.now() - timedelta(minutes=5)) > self.last_updated:
                        self.bot.cache.instances[inst.id] = None


    @check_server.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(logs(bot))