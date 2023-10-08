import discord
from discord.ext import commands, tasks

from datetime import datetime
import sqlite3

from rcon.instances import check_perms, get_available_instances, get_perms

from utils import Config, get_player_input_type, add_empty_fields, base_embed, get_name
config = Config()



class ServerStatusWidgets(commands.Cog):
    """Server Status widget Extension"""

    def __init__(self, bot):
        self.db = sqlite3.connect('instances.db')
        self.cur = self.db.cursor()
        self.bot = bot


    @commands.group(invoke_without_command=True, name="widget", description="Create, select and manage widgets",
                    usage="r!server widget mangagment", aliases=["status_widget"])
    @check_perms(instance=True)
    async def widget(self, ctx):
        await ctx.send(
            f"**Available Operations**\n{ctx.prefix}cog reload [cog]\n{ctx.prefix}cog enable <cog>\n{ctx.prefix}cog disable <cog>\n{ctx.prefix}cog info <cog>")

    @widget.command()
    @check_perms(instance=True)
    async def setup(self, ctx):
        now = datetime.now()
        instances = get_available_instances(ctx.author, ctx.guild.id)
        which_instance = await self.ask_instance(ctx)
        actual_instance = which_instance - 1
        instance_id = instances[actual_instance][0].id
        inst = self.bot.cache.instance(instance_id, by_inst_id=True).update()
        playercount = len(inst.players)

        embed = discord.Embed(title="Test Server", color=0xde1b1b)
        embed.add_field(name="Current Players", value=f"{str(playercount)}/100", inline=False)
        embed.add_field(name="Current Map: ", value=inst.current_map)
        embed.add_field(name="Next Map: ", value=inst.next_map)
        embed.set_footer(text="Last updated: " + now.strftime("%H:%M:%S"))

        channel_id = ctx.message.channel.id
        message_id = await ctx.send(embed=embed)
        self.cur.execute(f'INSERT INTO widget_config VALUES (?,?,?)', (instance_id, channel_id, message_id.id))
        self.db.commit()
        print(message_id)

    async def ask_instance(self, ctx):
        instances = get_available_instances(ctx.author, ctx.guild.id)
        await ctx.author.send(f'Please select Instance"')
        embed = discord.Embed(title=f"Available Instances ({str(len(instances))})")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        acceptable_inputs = []
        for i, (inst, perms) in enumerate(instances):
            try: self.bot.cache.instance(inst.id, by_inst_id=True)
            except: availability = "\🔴"
            else: availability = "\🟢"

            acceptable_inputs.append(str(i+1))
            perms = ", ".join([perm for perm, val in perms.to_dict().items() if val])
            embed.add_field(name=f"{str(i+1)} | {inst.name} {availability}", value=None)
        embed = add_empty_fields(embed)

        msg = await ctx.author.send(embed=embed)

        def check(message):
            return message.channel == msg.channel and message.author == ctx.author

        answer = ""
        while answer not in acceptable_inputs:
            answer = await self.bot.wait_for('message', check=check, timeout=120.0)
            answer = answer.content.lower()
            if answer not in acceptable_inputs:
                await ctx.author.send(f'Send Server ID Number"')
        return int(answer)

    @widget.command()
    async def start(self, ctx):
        #TODO Remove this and just and just have extension loaded
        self.update_widget.start()
        await ctx.send("Starting Wdiget")

    @tasks.loop(seconds=30.0)
    async def update_widget(self):
        self.cur.execute('SELECT * FROM widget_config')
        res = self.cur.fetchall()
        for instance_id, channel_id, message_id in res:
            channel = self.bot.get_channel(channel_id)
            message = channel.get_partial_message(message_id)
            now = datetime.now()
            inst = self.bot.cache.instance(instance_id, by_inst_id=True).update()
            playercount = len(inst.players)
            embed = discord.Embed(title="Test Server", color=0xde1b1b)
            embed.add_field(name="Current Players", value=f"{str(playercount)}/100", inline=False)
            embed.add_field(name="Current Map: ", value=inst.current_map)
            embed.add_field(name="Next Map: ", value=inst.next_map)
            embed.set_footer(text="Last updated: " + now.strftime("%H:%M:%S"))
            await message.edit(embed=embed)





async def setup(bot):
    await bot.add_cog(ServerStatusWidgets(bot))
