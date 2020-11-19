import discord
from discord.ext import commands
import random
from random import randint
import os
import ast

from utils import Config
config = Config()

def insert_returns(body):
    # insert return stmt if the l expression is a expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the orelse
    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)


class _util(commands.Cog):
    """Utility commands to get help, stats, links and more"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="Get help with any of my commands", usage="r!help [category] [command]")
    async def help(self, ctx, *args):
        
        args = [arg.lower() for arg in args] # Make all args lowercase

        output = ""
        data = {} # This will hold all cogs and their commands
        prefix = ctx.prefix

        """ Create a dict with all cogs and their commands """
        for cog in self.bot.cogs:
            cog = self.bot.get_cog(cog)

            name = cog.qualified_name
            if name.startswith("_"):
                continue # Ignore backend cogs

            cmds = cog.get_commands() # This holds all of the cog's commands
            commands = [] # While this will hold dicts of to-be-displayed commands

            if not cmds:
                continue # Cog doesn't have any commands

            for command in cmds:

                if not command.hidden:
                    command_data = {
                        "name": command.name,
                        "cog": command.cog,
                        "desc": command.description,
                        "usage": command.usage,
                        "aliases": command.aliases
                    }
                    commands.append(command_data)
            
            if commands: # Only append if there are commands to be displayed
                data[name] = commands


        """ Functions to format the final message """
        def list_categories(data):
            output = f"{config.get('help_command_emoji')} **Help - All categories**"
            for category in data:
                output += f"\n        `{category.capitalize()}` - {self.bot.get_cog(category).description}"
            output += f"\n\nUse `{prefix}help <category>` to browse categories"
            return output
        def list_commands(category, commands):
            output = f"{config.get('help_command_emoji')} **Help - {category.capitalize()}**"
            for command in commands:
                output = output + f"\n        `{prefix}{command['name']}` - {command['desc']}"
            output += f"\n\nUse `{prefix}help [category] <command>` to browse commands"
            return output
        def list_command_info(category, command):                   
            output = f"{config.get('help_command_emoji')} **Help - {category.capitalize()} - {command['name']}**"
            if command["usage"] != None:
                output = output + "\n        Usage: `" + command["usage"] + "`"
            if command["aliases"] != []:
                output = output + "\n        Aliases: " + "`" + "`, `".join(command["aliases"]) + "`"
            if command["desc"] != []:
                output = output + "\n        Description: " + command["desc"]
            return output

        
        if len(args) > 1: # Both a category and command are specified
            
            category = args[0]
            name = args[1]

            try:
                commands = data[category]
            except KeyError:
                await ctx.send(f"{config.get('error_message_emoji')} Couldn't find category \"{category}\"!")
                return

            command = None
            for cmd in commands:
                if name == cmd["name"] or name in cmd["aliases"]:
                    command = cmd
                    break
            if command: # A command was found
                output = list_command_info(category, command)
            else: # No command was found
                await ctx.send(f"{config.get('error_message_emoji')} Couldn't find command \"{name}\"!")
                return


        elif len(args) == 1: # Either a category or command is specified 
            try:
                category = args[0]
                commands = data[category]


            except KeyError: # Only a command is specified
                name = args[0]
                for category, commands in data.items():
                    command = None
                    for cmd in commands:
                        if name == cmd["name"] or name in cmd["aliases"]:
                            command = cmd
                            break
                    if command: # A command was found
                        output = list_command_info(category, command)
                        break
                if not command: # No command was found
                    await ctx.send(f"{config.get('error_message_emoji')} Couldn't find category or command \"{name}\"!")
                    return


            else: # Only a category is specified
                output = list_commands(category, commands)


        else: # Neither a category or command are specified
            output = list_categories(data)

        """ Send the output """
        await ctx.send(output)


    @commands.command(description="View my current latency", usage="r!ping")
    async def ping(self, ctx):
        await ctx.send('Pong! {0}ms'.format(round(self.bot.latency * 1000, 1)))


    @commands.command(description="Evaluate a python variable or expression", usage="r!eval <cmd>", hidden=True)
    @commands.is_owner()
    async def eval(self, ctx, *, cmd):
        """Evaluates input.
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
        - `bot`: the bot instance
        - `discord`: the discord module
        - `commands`: the discord.ext.commands module
        - `ctx`: the invokation context
        - `__import__`: the builtin `__import__` function
        Such that `>eval 1 + 1` gives `2` as the result.
        The following invokation will cause the bot to send the text '9'
        to the channel of invokation and return '3' as the result of evaluating
        >eval ```
        a = 1 + 2
        b = a * 2
        await ctx.send(a + b)
        a
        ```
        """
        fn_name = "_eval_expr"

        cmd = cmd.strip("` ")
        if cmd.startswith("py"): cmd = cmd.replace("py", "", 1)

        # add a layer of indentation
        cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

        # wrap in async def body
        body = f"async def {fn_name}():\n{cmd}"

        parsed = ast.parse(body)
        body = parsed.body[0].body

        insert_returns(body)

        env = {
            'self': self,
            'discord': discord,
            'commands': commands,
            'ctx': ctx,
            '__import__': __import__
        }
        exec(compile(parsed, filename="<ast>", mode="exec"), env)

        result = (await eval(f"{fn_name}()", env))
        try:
            await ctx.send(result)
        except discord.HTTPException:
            pass

   
    


def setup(bot):
    bot.add_cog(_util(bot))