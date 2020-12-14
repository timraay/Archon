import discord
from discord.ext import commands, tasks
import json
from ast import literal_eval
import os
from pathlib import Path

from rcon.commands import Rcon
from rcon.instances import check_perms, Instance

from utils import Config, base_embed
config = Config()



class administration(commands.Cog):
    """Server administration commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Request a command through RCON", usage="r!execute <cmd>", aliases=["exec"], hidden=False)
    @check_perms(administration=True)
    async def execute(self, ctx, *, cmd):
        res = self.bot.cache.instance(ctx.author.id, ctx.guild.id).rcon.exec_command(cmd)
        res = literal_eval(res)
        if not res: # An empty list was received
            res = "Empty response received"
        else:
            res = res[0].strip(b'\x00\x01').decode('utf-8')
            if len(res) > 1018: # too big to be sent in one embed field
                res = res[:1015] + "..."

        embed = discord.Embed(title="Command executed")
        embed.add_field(name="Request", value=f"`{cmd}`", inline=False)
        embed.add_field(name="Response", value=f"```{res}```")
        await ctx.send(embed=embed)


    @commands.command(description="Set the max player limit", usage="r!set_max_player_limit", aliases=["set_player_limit", "player_limit"])
    @check_perms(administration=True)
    async def set_max_player_limit(self, ctx, limit: int):
        inst = self.bot.cache.instance(ctx.author.id, ctx.guild.id)
        res = inst.rcon.set_max_player_limit(limit)

        embed = base_embed(inst.id, title="Max player limit changed", description=res)
        await ctx.send(embed=embed)
    
    @commands.command(description="Set or remove a server password", usage="r!password [password]", aliases=["set_password"])
    @check_perms(administration=True)
    async def password(self, ctx, password: str = ""):
        res = self.bot.cache.instance(ctx.author.id, ctx.guild.id).rcon.set_password(password)

        embed = discord.Embed(title="Password updated", description=res)
        await ctx.send(embed=embed)


    @commands.group(invoke_without_command=True, description="Enable or disable a custom map rotation", usage="r!rotation [subcommand]", aliases=["map_rotation", "rotation"])
    @check_perms(administration=True)
    async def maprotation(self, ctx):
        inst = self.bot.cache.instance(ctx.author.id, ctx.guild.id)
        embed = base_embed(inst.id, title="Custom Map Rotation")
        
        embed.description = "`r!rotation upload` - Upload a new custom rotation\n`r!rotation enable` - Enable the custom rotation\n`r!rotation disable` - Disable custom rotation\n`r!rotation download` - Download your custom rotation"

        if os.path.exists(Path(f'rotations/{str(inst.id)}.json')):
            if inst.map_rotation:
                embed.color = discord.Color.green()
                embed.title += " | Status: Enabled"
            else:
                embed.color = discord.Color.red()
                embed.title += " | Status: Disabled"
            
            try: maps = sorted(set([str(entry) for entry in inst.map_rotation.get_entries()]))
            except: maps = ["Failed to fetch maps"]
            embed.add_field(name="Maps in rotation:", value="\n".join(maps))

        else:
            embed.title += " | Status: Unconfigured"

        await ctx.send(embed=embed)

    @maprotation.command()
    @check_perms(administration=True)
    async def upload(self, ctx):
        if not ctx.message.attachments:
            await ctx.send(f":no_entry_sign: Please include your custom rotation as an attachment!")
            return
        attachment = ctx.message.attachments[0]
        if attachment.size > 1000000:
            await ctx.send(f":no_entry_sign: Invalid attachment!\n`File too big! Maximum is 1000000 bytes but received {str(attachment.size)} bytes`")
            return
        if not attachment.filename.endswith(".json"):
            extension = "." + attachment.filename.split(".")[-1]
            await ctx.send(f":no_entry_sign: Invalid attachment!\n`Invalid file extension! Expected .json but received {extension}`")
            return
        
        inst = self.bot.cache.instance(ctx.author.id, ctx.guild.id)

        content = str(await attachment.read(), 'utf-8')
        content = json.loads(content)

        inst.import_rotation(content=content)
        with open(Path(f'rotations/{str(inst.id)}.json'), 'w+') as f:
            f.write(json.dumps(content, indent=2))

        embed = base_embed(inst.id, title="Uploaded and enabled Custom Map Rotation", color=discord.Color.green())
        embed.description = "`r!rotation upload` - Upload a new custom rotation\n`r!rotation enable` - Enable the custom rotation\n`r!rotation disable` - Disable custom rotation\n`r!rotation download` - Download your custom rotation"
        try: maps = sorted(set([str(entry) for entry in inst.map_rotation.get_entries()]))
        except: maps = ["Failed to fetch maps"]
        embed.add_field(name="Maps in rotation:", value="\n".join(maps))

        await ctx.send(embed=embed)

    @maprotation.command()
    @check_perms(administration=True)
    async def enable(self, ctx):        
        inst = self.bot.cache.instance(ctx.author.id, ctx.guild.id)

        if inst.map_rotation:
            await ctx.send(':no_entry_sign: Custom Map Rotation is already enabled!')
            return
        path = Path(f'rotations/{str(inst.id)}.json')
        if not os.path.exists(path):
            await ctx.send(':no_entry_sign: Upload a custom rotation first using `r!rotation upload`!')
            return
        
        inst.import_rotation(fp=path)

        embed = base_embed(inst.id, title="Enabled Custom Map Rotation", color=discord.Color.green())
        embed.description = "`r!rotation upload` - Upload a new custom rotation\n`r!rotation enable` - Enable the custom rotation\n`r!rotation disable` - Disable custom rotation\n`r!rotation download` - Download your custom rotation"
        try: maps = sorted(set([str(entry) for entry in inst.map_rotation.get_entries()]))
        except: maps = ["Failed to fetch maps"]
        embed.add_field(name="Maps in rotation:", value="\n".join(maps))

        await ctx.send(embed=embed)

    @maprotation.command()
    @check_perms(administration=True)
    async def disable(self, ctx):        
        inst = self.bot.cache.instance(ctx.author.id, ctx.guild.id)

        if inst.map_rotation == None:
            await ctx.send(':no_entry_sign: Custom Map Rotation is already disabled!')
            return
        
        inst.map_rotation = None

        embed = base_embed(inst.id, title="Disabled Custom Map Rotation", color=discord.Color.red())
        embed.description = "`r!rotation upload` - Upload a new custom rotation\n`r!rotation enable` - Enable the custom rotation\n`r!rotation disable` - Disable custom rotation\n`r!rotation download` - Download your custom rotation"

        await ctx.send(embed=embed)
    
    @maprotation.command()
    @check_perms(administration=True)
    async def download(self, ctx):
        inst = self.bot.cache.instance(ctx.author.id, ctx.guild.id)

        path = Path(f'rotations/{str(inst.id)}.json')
        if not os.path.exists(path):
            await ctx.send(':no_entry_sign: You don\'t have a custom rotation uploaded!')
            return

        f = discord.File(fp=path, filename=f"{Instance(inst.id).name} map rotation.json")
        await ctx.send(file=f)

def setup(bot):
    bot.add_cog(administration(bot))