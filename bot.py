# RCON for games running on the OWI core, accessed through Discord, by timraay

import discord
from discord.ext import commands
import os
from pathlib import Path
import re

from rcon.instances import get_available_instances

from utils import Config
config = Config()

intents = discord.Intents.default()
intents.members = True

async def command_prefix(bot, msg):
    res = re.search(r"\A[rR](\d*)!", msg.content)
    try:
        prefix = res.group()
        inst_id = res.groups()[0]
    except:
        return ("r!", "R!")

    if inst_id:
        inst_id = int(inst_id)
        instances = get_available_instances(msg.author, msg.guild.id)
        try: inst = [inst for i, (inst, perms) in enumerate(instances) if i+1 == inst_id][0]
        except IndexError:
            await msg.channel.send(":no_entry_sign: Invalid command prefix!\n`No instance found with ID %s`" % inst_id)
            return ("r!", "R!")
        bot.cache.selected_instance[msg.author.id] = inst.id
    return prefix

bot = commands.Bot(intents=intents, command_prefix=command_prefix, case_insensitive=True)
bot.remove_command('help')

@bot.group(invoke_without_command=True, aliases=['cog'])
@commands.is_owner()
async def module(ctx):
    await ctx.send(f"**Available Operations**\n{ctx.prefix}cog reload [cog]\n{ctx.prefix}cog enable <cog>\n{ctx.prefix}cog disable <cog>\n{ctx.prefix}cog info <cog>")

@module.command(aliases=["load"])
@commands.is_owner()
async def enable(ctx, cog: str):
    """ Enable a cog """
    cog = cog.lower()
    if os.path.exists(Path(f"./cogs/{cog}.py")):
        bot.load_extension(f"cogs.{cog}")
        await ctx.send(f"Enabled {cog}")
    else:
        await ctx.send(f"{cog} doesn't exist")

@module.command(aliases=["unload"])
@commands.is_owner()
async def disable(ctx, cog: str):
    """ Disable a cog """
    cog = cog.lower()
    if os.path.exists(Path(f"./cogs/{cog}.py")):
        bot.unload_extension(f"cogs.{cog}")
        await ctx.send(f"Disabled {cog}")
    else:
        await ctx.send(f"{cog} doesn't exist")

@module.command()
@commands.is_owner()
async def reload(ctx, cog: str = None):
    """ Reload cogs """

    async def reload_cog(ctx, cog):
        """ Reloads a cog """
        try:
            bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"Reloaded {cog}")
        except Exception as e:
            await ctx.send(f"Couldn't reload {cog}, " + str(e))

    if not cog:
        for cog in os.listdir(Path("./cogs")):
            if cog.endswith(".py"):
                cog = cog.replace(".py", "")
                await reload_cog(ctx, cog)
    else:
        if os.path.exists(Path(f"./cogs/{cog}.py")):
            await reload_cog(ctx, cog)
        else:
            await ctx.send(f"{cog} doesn't exist")

@module.command(aliases=["list"])
@commands.is_owner()
async def info(ctx, cog: str = None):
    """ List cogs' commands and events """

    if cog:
        # A single cog
        cog = cog.lower()
        if os.path.exists(Path(f"./cogs/{cog}.py")):
            cog = bot.get_cog(cog)
            if not cog:
                await ctx.send(f"{cog} is not a module")
            else:
                commands_list = [command.name for command in cog.get_commands()]
                events_list = [listener.name for listener in cog.get_listeners()]

                if not commands_list: commands = "None"
                else: commands = ", ".join(commands_list)

                if not events_list: events = "None"
                else: events = ", ".join(events_list)

                embed=discord.Embed(title=f"Module \"{cog.qualified_name}\"")
                embed.add_field(name=f"Commands ({str(len(commands_list))})", value=commands, inline=False)
                embed.add_field(name=f"Events ({str(len(events_list))})", value=events, inline=False)

                await ctx.send(embed=embed)
        else:
            await ctx.send(f"{cog} doesn't exist")
    
    else:
        # All cogs
        embed = discord.Embed(title="All modules")
        for cog in os.listdir(Path("./cogs")):
            if cog.endswith(".py"):
                cog = cog.replace(".py", "")
                cog = bot.get_cog(cog)
                if cog:
                    commands_list = cog.get_commands()
                    events_list = cog.get_listeners()

                    embed.add_field(name=cog.qualified_name, value=f"{str(len(commands_list))} commands & {str(len(events_list))} events", inline=False)
        await ctx.send(embed=embed)

# Load all cogs
for cog in os.listdir(Path("./cogs")):
    if cog.endswith(".py"):
        try:
            cog = f"cogs.{cog.replace('.py', '')}"
            bot.load_extension(cog)
        except Exception as e:
            print(f"{cog} can not be loaded:")
            raise e

# Setup logger
import logging
from datetime import datetime
logname = datetime.utcnow().strftime('logs/Archon-%Y.%m.%d-%H.%M.%S.log')
logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%m/%d %H:%M:%S', filename=logname, filemode='w+', level=logging.INFO)
logging.info('Launching bot...')

# Initialize cache
from rcon.cache import Cache
try:
    bot.cache = Cache()
except:
    logging.fatal('Failed to build the cache')
    raise

# Run the bot
with open("token.txt", "r") as f:
    token = f.read()

bot.run(token)