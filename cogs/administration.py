import discord
from discord.ext import commands, tasks
import json
from ast import literal_eval

from rcon.commands import Rcon
from rcon.instances import check_perms

from utils import Config
config = Config()



class administration(commands.Cog):
    """Server administration commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Request a command through RCON", usage="r!execute <cmd>", aliases=["exec"], hidden=False)
    @check_perms(administration=True)
    async def execute(self, ctx, *, cmd):
        res = self.bot.cache.instance(ctx.author.id).rcon.exec_command(cmd)
        res = literal_eval(res)
        if not res: # An empty list was received
            res = "Empty response received"
        else:
            res = res[0].strip(b'\x00\x01').decode('utf-8')
            if len(res) > 1018: # too big to be sent in one embed field
                res = res[:1015] + "..."

        embed = discord.Embed(title="Command executed")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.add_field(name="Request", value=f"`{cmd}`", inline=False)
        embed.add_field(name="Response", value=f"```{res}```")
        await ctx.send(embed=embed)


    @commands.command(description="Set the max player limit", usage="r!set_max_player_limit", aliases=["set_player_limit", "player_limit"])
    @check_perms(administration=True)
    async def set_max_player_limit(self, ctx, limit: int):
        res = self.bot.cache.instance(ctx.author.id).rcon.set_max_player_limit(limit)

        embed = discord.Embed(title="Max player limit changed", description=res)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)
    
    @commands.command(description="Set or remove a server password", usage="r!password [password]", aliases=["set_password"])
    @check_perms(administration=True)
    async def password(self, ctx, password: str = ""):
        res = self.bot.cache.instance(ctx.author.id).rcon.set_password(password)

        embed = discord.Embed(title="Password updated", description=res)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(administration(bot))