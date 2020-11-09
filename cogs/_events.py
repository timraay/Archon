import discord
from discord.ext import commands, tasks
import random
from datetime import datetime, timedelta
from ast import literal_eval
import difflib
import re

from utils import Config
config = Config()

from rcon.commands import RconCommandError
from rcon.cache import CacheNotFound, ConnectionLost

def convert_time(seconds):
    sec = timedelta(seconds=seconds)
    d = datetime(1,1,1) + sec

    output = ("%dh%dm%ds" % (d.hour, d.minute, d.second))
    if output.startswith("0h"):
        output = output.replace("0h", "")
    if output.startswith("0m"):
        output = output.replace("0m", "")

    return output


class _events(commands.Cog):
    """A class with most events in it"""

    def __init__(self, bot):
        self.bot = bot
        self.update_status.start()


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        
        error_emoji = config.get("error_message_emoji")

        if not isinstance(error, commands.CommandOnCooldown) and not isinstance(error, commands.CommandNotFound):
            ctx.command.reset_cooldown(ctx)
        
        if hasattr(ctx.command, 'on_error'):
            return

        if isinstance(error, commands.CheckFailure) and not isinstance(error, commands.MissingPermissions):
            return

        if isinstance(error, commands.CommandInvokeError):
            error = error.original

        if isinstance(error, commands.CommandNotFound):
            used_command = re.search(r'Command "(.*)" is not found', str(error)).group(1)
            all_commands = [command.name for command in self.bot.commands]
            close_matches = difflib.get_close_matches(used_command, all_commands, cutoff=0.3)
            desc = f"{error_emoji} Unknown command!"
            if close_matches:
                desc += f"\n`Maybe try one of the following: {self.bot.command_prefix}{f', {self.bot.command_prefix}'.join(close_matches)}`"
            await ctx.send(desc)
            
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"{error_emoji} That command is still on cooldown! Cooldown expires in " + convert_time(round(int(error.retry_after), 0)) + ".")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"{error_emoji} Missing required permissions to use that command!\n`{str(error)}`")
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.send(f"{error_emoji} I am missing required permissions to use that command!\n`{str(error)}`")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send(f"{error_emoji} Couldn't run that command!\n`{str(error)}`")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"{error_emoji} Missing required argument(s)!\n`{str(error)}`")
        elif isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send(f"{error_emoji} You can't do that right now!\n`{str(error)}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"{error_emoji} Invalid argument!\n`{str(error)}`")
        elif isinstance(error, RconCommandError):
            await ctx.send(f"{error_emoji} The game server returned an error!\n`{str(error)}`")
        elif isinstance(error, ConnectionLost):
            await ctx.send(f"{error_emoji} Connection to the server was lost! Try reconnecting using `r!inst reconnect`\n`{str(error)}`.")
        elif isinstance(error, CacheNotFound):
            await ctx.send(f"{error_emoji} This instance was shut down! Try reconnecting using `r!inst reconnect`.")
        else:
            await ctx.send(f"{error_emoji} Oops, something went wrong!\n`{str(error)}`")

        if not isinstance(error, commands.CommandOnCooldown):
            try:
                print("\nError in " + ctx.guild.name + " #" + ctx.channel.name + ":\n" + str(error))
            except:
                print("\nFailed to log error")



    @commands.Cog.listener()
    async def on_ready(self):
        print("\nLaunched " + self.bot.user.name + " on " + str(datetime.now()))
        print("ID: " + str(self.bot.user.id))



    @tasks.loop(minutes=15.0)
    async def update_status(self):

        statuses = [
            {"type": "playing", "message": "with {playercount} other players"},
            {"type": "playing", "message": "with {playercount} other players"},
            {"type": "playing", "message": "with {playercount} other players"},
            {"type": "watching", "message": "over {servercount} servers"},
            {"type": "watching", "message": "over {servercount} servers"},
            {"type": "watching", "message": "over {servercount} servers"},
            {"type": "playing", "message": "In the midst of chaos, there is also opportunity..."},
            {"type": "playing", "message": "The greatest victory is that which requires no battle..."},
            {"type": "playing", "message": "Squad"},
            {"type": "playing", "message": "Beyond The Wire"}
        ]
        playercount = str(sum([len(inst.players) for inst in self.bot.cache.instances.values()]))
        servercount = str(len(self.bot.cache.instances))
        status = random.choice(statuses)
        message = status["message"].format(playercount=playercount, servercount=servercount)
        activity = status["type"]
        if activity == "playing": activity = discord.ActivityType.playing
        elif activity == "streaming": activity = discord.ActivityType.streaming
        elif activity == "listening": activity = discord.ActivityType.listening
        elif activity == "watching": activity = discord.ActivityType.watching
        else: activity = discord.ActivityType.playing

        await self.bot.change_presence(activity=discord.Activity(name=message, type=activity))
    @update_status.before_loop
    async def before_status(self):
        await self.bot.wait_until_ready()



def setup(bot):
    bot.add_cog(_events(bot))