import discord
from discord.ext import commands
import asyncio

from rcon.instances import get_available_instances, perms_to_dict, Instance, get_guild_instances, get_perms, set_player_perms, reset_player_perms, has_perms, check_perms, add_instance, is_owner
from rcon.connection import RconAuthError

from utils import add_empty_fields, base_embed


CONFIG_DESC = {
    "guild_id": "**Guild ID (guild\\_id)**\nThis is the ID of the Discord guild your instance will mainly operate in. Guild permissions will be applied to this guild only. Channels for game logs must be in this guild. Users with user permissions will still be able to access your instance outside of this guild.",
    "chat_trigger_words": "**Chat Trigger Words (chat\\_trigger\\_words)**\nChat trigger words send a notification through Discord whenever one of the specified words is mentioned by a player in-game. This allows admins to respond quickly to requests.\n\n`chat_trigger_words` is a comma-seperated list of words. What that means, is you can add as many trigger words as you like. Just make sure to put a comma inbetween them.",
    "chat_trigger_channel_id": "**Chat Trigger Channel ID (chat\\_trigger\\_channel\\_id)**\nThis is where the chat trigger will send notifications to. When a channel with this ID can not be found inside the guild specified with `guild_id`, this feature will be disabled.",
    "chat_trigger_mentions": "**Chat Trigger Mentions (chat\\_trigger\\_mentions)**\nThis is the message attached to the notification. To turn it into an actual notification, you probably want to include a role or user mention in here.\n\nThe bot doesn't automatically format this into mentions, you have to do that yourself. Mentions are formatted like this:```<@USER_ID> for user mentions\n<@&ROLE_ID> for role mentions```You can also mention a role or user and put a backslash (\\) in front of it to get it in this format.",
    "chat_log_channel_id": "**Chat Log Channel ID (chat\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log chat messages to.",
    "joins_log_channel_id": "**Joins Log Channel ID (joins\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log players joining and leaving to.",
    "rcon_log_channel_id": "**RCON Log Channel ID (rcon\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log RCON actions to.",
    "match_log_channel_id": "**Match Log Channel ID (match\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log match changes to."
}



class instances(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, name="instance", description="Create, select and manage instances", usage="r!inst help", aliases=["inst"])
    async def instance_command(self, ctx, *, instance_id=None):
        if instance_id:
            await self.select_instance.__call__(ctx, instance_id)
        
        else:
            current_instance = self.bot.cache._get_selected_instance(ctx.author.id)
            try: embed = base_embed(current_instance)
            except:
                embed = discord.Embed()
                embed.set_author(name="No instance selected")
            embed.set_footer(text='Use "r!inst help" to view a list of options')
            await ctx.send(embed=embed)
        
    @instance_command.command(name="help")
    async def instance_help(self, ctx):
        embed = discord.Embed(title="Server Instances Help")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.add_field(name="Public Commands", value="```r!instance <name_or_id>\nr!instance list\nr!instance perms```", inline=False)
        embed.add_field(name="Admin Commands", value="```r!instance perms help\nr!instance perms <user>\n\nr!instance perms <user> list\nr!instance perms <user> set <perms>\nr!instance perms <user> reset\nr!instance perms guild list\nr!instance perms guild set <perms>\nr!instance config\nr!instance config <key>\nr!instance config <key> <value>```", inline=False)
        await ctx.send(embed=embed)

    @instance_command.command(name="list", description="List all available instances", usage="r!instance list", aliases=["view", "show"])
    async def list_instances(self, ctx):
        instances = get_available_instances(ctx.author.id, ctx.guild.id)
        current_instance = self.bot.cache._get_selected_instance(ctx.author.id)
        try:
            current_instance = Instance(current_instance).name
        except:
            current_instance = "None"

        embed = discord.Embed(title=f"Available Instances ({str(len(instances))})", description=f'> Currently selected: {current_instance}')
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        for i, (inst, perms) in enumerate(instances):
            try: self.bot.cache.instance(inst.id, by_inst_id=True)
            except: availability = "\🔴"
            else: availability = "\🟢"
            perms = ", ".join([perm for perm, val in perms_to_dict(perms).items() if val])
            embed.add_field(name=f"{str(i+1)} | {inst.name} {availability}", value=f"> **Perms:** {perms}")
        embed = add_empty_fields(embed)

        await ctx.send(embed=embed)
    @instance_command.command(name="select", description="Select an instance to control", usage="r!instance <instance>")
    async def select_instance(self, ctx, instance_id: str):
        instances = get_available_instances(ctx.author.id, ctx.guild.id)
        inst = None
        for i, (instance, perms) in enumerate(instances):
            if str(i+1) == instance_id or instance.name.lower() == instance_id.lower():
                inst = instance
                break
        if not inst:
            raise commands.BadArgument("No instance found with name or ID %s" % instance_id)
        self.bot.cache.selected_instance[ctx.author.id] = instance.id

        perms = ", ".join([perm for perm, val in perms_to_dict(perms).items() if val])
        embed = discord.Embed(title=f'Selected the "{instance.name}" instance', description=f"> **Perms:** {perms}")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        await ctx.send(embed=embed)

    @instance_command.command(name="connect", aliases=["reconnect"])
    @check_perms(administration=True)
    async def connect_instance(self, ctx):
        instance_id = self.bot.cache._get_selected_instance(ctx.author.id)
        inst = Instance(instance_id)

        res = self.bot.cache._connect_instance(inst, return_exception=True)
        if isinstance(res, Exception): # Instance could not be connected
            raise res
        else: # Instance was successfully connected
            embed = base_embed(instance_id, title="Instance was successfully (re)connected")
            await ctx.send(embed=embed)
    @instance_command.command(name="disconnect", aliases=["shutdown"])
    async def disconnect_instance(self, ctx):
        instance_id = self.bot.cache._get_selected_instance(ctx.author.id)
        inst = Instance(instance_id)

        self.bot.cache.instances[instance_id] = None
        embed = base_embed(instance_id, title="Instance was shut down")
        await ctx.send(embed=embed)
    
    @instance_command.command(name="delete")
    @is_owner()
    async def delete_instance(self, ctx):
        instance_id = self.bot.cache._get_selected_instance(ctx.author.id)
        inst = Instance(instance_id)

        embed = base_embed(inst.id, title="Are you sure you want to permanently delete this instance?", description="Deleting an instance will break the connection, remove all permissions and clear all the logs. This can NOT be reverted.\n\nReact with 🗑️ to confirm and delete this instance.")
        try: msg = await ctx.author.send(embed=embed)
        except: msg = await ctx.send(embed=embed)

        await msg.add_reaction('🗑️')

        def check(reaction, user):
            return reaction.message.id == msg.id and str(reaction.emoji) == "🗑️" and user.id == ctx.author.id and not user.bot
            
        try:
            await self.bot.wait_for('reaction_add', timeout=120.0, check=check)
        except:
            if isinstance(msg.channel, discord.TextChannel): await msg.clear_reactions()
            embed.description = "You took too long to respond. Execute the command again to retry."
            await msg.edit(embed=embed)
        else:
            if isinstance(msg.channel, discord.TextChannel): await msg.clear_reactions()
            self.bot.cache.delete_instance(instance_id)
            embed = base_embed(inst.id, title="Instance deleted")
            await msg.edit(embed=embed)
    @instance_command.command(name="create", aliases=["add"])
    @commands.has_permissions(administrator=True)
    async def create_instance(self, ctx):
        embed = discord.Embed(title="Creating your instance...")
        try: await ctx.author.send(ctx.author.mention)
        except:
            await ctx.send(f":no_entry_sign: {ctx.author.mention}, please enable DMs")
            return

        # Create embed
        def setup_embed(question):
            embed = discord.Embed(title=question, description="Type your answer down below. You can change your answers later.")
            embed.set_author(name="Creating your instance...")
            embed.set_footer(text="Support ticket will be canceled if the channel remains inactive for 5 minutes during its creation.")
            return embed

        async def ask_game():
            embed = setup_embed("What game is your server for, Squad or BTW?")
            msg = await ctx.author.send(embed=embed)
            def check(message):
                return message.channel == msg.channel and message.author == ctx.author
            answer = ""
            while answer not in ['squad', 'btw']:
                answer = await self.bot.wait_for('message', check=check, timeout=120.0)
                answer = answer.content.lower()
                if answer not in ['squad', 'btw']:
                    await ctx.author.send(f'Send either "Squad" or "BTW", not "{answer}"')
            return answer
        async def ask_address_and_port():
            async def ask_address():
                embed = setup_embed("What is your server's IP address?")
                msg = await ctx.author.send(embed=embed)
                def check(message):
                    return message.channel == msg.channel and message.author == ctx.author
                answer = await self.bot.wait_for('message', check=check, timeout=120.0)
                return answer.content
            async def ask_port():
                embed = setup_embed("What is your server's RCON port?")
                msg = await ctx.author.send(embed=embed)
                def check(message):
                    return message.channel == msg.channel and message.author == ctx.author
                answer = await self.bot.wait_for('message', check=check, timeout=120.0)
                return answer.content
            address = ""
            port = 0
            while not address or not port:
                address = await ask_address()
                if len(address.split(":", 1)) == 2:
                    address, port = address.split(":", 1)
                else:
                    port = await ask_port()
                try: port = int(port)
                except:
                    port = 0
                    await ctx.author.send("Invalid port! Please insert your address and port again.")
            return address, port
        async def ask_password():
            embed = setup_embed("What is your server's RCON password?")
            embed.description += "\n\nNote: Passwords are stored by the bot, but will NEVER be shared."
            msg = await ctx.author.send(embed=embed)
            def check(message):
                return message.channel == msg.channel and message.author == ctx.author
            answer = await self.bot.wait_for('message', check=check, timeout=120.0)
            return answer.content
        async def ask_name():
            embed = setup_embed("What should your instance be called?")
            msg = await ctx.author.send(embed=embed)
            def check(message):
                return message.channel == msg.channel and message.author == ctx.author
            answer = await self.bot.wait_for('message', check=check, timeout=120.0)
            return answer.content

        async def ticket_confirmation(values):
            embed = discord.Embed(title="That was everything!", description="If you need to change something, select one of the fields by reacting to this message. If all information is correct, react with ✅. To cancel, react with 🗑️.", color=discord.Color.gold())
            embed.add_field(name="1⃣ Game", value=values[0], inline=True)
            embed.add_field(name="2⃣ Address:Port", value=values[1] + ":" + str(values[2]), inline=True)
            embed.add_field(name="3⃣ Password", value=values[3], inline=True)
            embed.add_field(name="4⃣ Instance Name", value=values[4], inline=False)
            msg = await ctx.author.send(embed=embed)

            for emoji in ["✅", "1⃣", "2⃣", "3⃣", "4⃣", "🗑️"]:
                await msg.add_reaction(emoji)
            def check(reaction, user):
                return reaction.message.channel == msg.channel and user == ctx.author
            answer = await self.bot.wait_for('reaction_add', check=check, timeout=300.0)
            await msg.delete()

            return str(answer[0].emoji)
        
        try:
            game = await ask_game()
            address, port = await ask_address_and_port()
            password = await ask_password()
            name = await ask_name()
            values = [game, address, port, password, name]
            
            confirmation = ""
            while confirmation != "✅":
                confirmation = await ticket_confirmation(values)
                if confirmation == "1⃣": game = await ask_game()
                elif confirmation == "2⃣": address, port = await ask_address_and_port()
                elif confirmation == "3⃣": password = await ask_password()
                elif confirmation == "4⃣": name = await ask_name()
                elif confirmation == "🗑️":
                    await ctx.author.send("Instance creation cancelled.")
                    return
                values = [game, address, port, password, name]
                
                if confirmation == "✅":
                    msg = await ctx.author.send("Trying to establish a connection...")
                    try:
                        inst = add_instance(game=values[0], address=values[1], port=values[2], password=values[3], name=values[4], owner_id=ctx.author.id)
                    except RconAuthError as e:
                        await ctx.author.send(f"Unable to connect to the server: {str(e)}")
                        await asyncio.sleep(3)
                        confirmation = ""
                    except RconAuthError as e:
                        await ctx.author.send(f"An instance using this address already exists!")
                        await asyncio.sleep(3)
                        confirmation = ""
                    else:
                        await msg.edit(content="Connection established!")
                        self.bot.cache._connect_instance(inst)
                        embed = base_embed(inst.id, title="Instance created!", description="You can now customize your instance further by setting permissions and changing config options. See `r!inst help` for more information.", color=discord.Color.green())
                        await ctx.author.send(embed=embed)

        except asyncio.TimeoutError:
            await ctx.author.send("You took too long to respond. Execute the command again to retry.")
            return

        

    @instance_command.group(invoke_without_command=True, name="permissions", description="Set or view RCON permissions for a user or guild", aliases=["perms"])
    async def permissions_group(self, ctx, user: discord.Member = None, operation: str = "", value: int = None):
        instance_id = self.bot.cache._get_selected_instance(ctx.author.id)
        instance = Instance(instance_id)

        # Limit command usage when missing permissions
        if not has_perms(ctx, instance=True):
            user = ctx.author
            operation = ""
            value = None

        # Default user to message author
        if not user:
            user = ctx.author

        # List all instances this user has access to here
        if operation.lower() == '':
            instances = get_available_instances(user.id, ctx.guild.id)

            if instances:
                embed = discord.Embed(title=f"Permissions in {ctx.guild.name}")
                embed.set_author(icon_url=user.avatar_url, name=f"{user.name}#{user.discriminator}")

                for i, (instance, perms) in enumerate(instances):
                    perms = ", ".join([perm for perm, val in perms_to_dict(perms).items() if val])
                    embed.add_field(name=f"{str(i+1)} | {instance.name}", value=f"> **Perms:** {perms}")
                embed = add_empty_fields(embed)
            
            else:
                embed = discord.Embed(title=f"Permissions in {ctx.guild.name}", description="You don't have access to any instances yet!\n\nInstances can be created by server owners, assuming they are an administrator of that guild.\n`r!instance create")
                embed.set_author(icon_url=user.avatar_url, name=f"{user.name}#{user.discriminator}")

            await ctx.send(embed=embed)
        
        # List user permissions for this user
        elif operation.lower() in ['list', 'view', 'show']:
            perms = get_perms(user.id, -1, instance_id, is_dict=False)
            perms_dict = perms_to_dict(perms)
            perms_str = ", ".join([perm for perm, val in perms_dict.items() if val])
            embed = base_embed(instance.id, title=f'Permission overwrites for {user.name}#{user.discriminator}', description=f"> Current value: {str(perms)}\n> Perms: {perms_str}")
            await ctx.send(embed=embed)

        # Set user permissions for the selected instance
        elif operation.lower() in ['set']:
            # Update the user permissions for the selected instance
            if value != None and int(value) >= 0 and int(value) <= 31:
                old_perms = ", ".join([perm for perm, val in get_perms(user.id, -1, instance_id).items() if val])
                new_perms = ", ".join([perm for perm, val in perms_to_dict(value).items() if val])
                set_player_perms(user.id, instance_id, value)

                embed = base_embed(instance.id, title=f"Changed permission overwrites for {user.name}#{user.discriminator}")
                embed.add_field(name="Old Perms", value=f"> {old_perms}")
                embed.add_field(name="New Perms", value=f"> {new_perms}")
                
                await ctx.send(embed=embed)
                
            # Error
            else:
                raise commands.BadArgument("Permissions value out of range")
        
        # Reset user permissions for the selected instance
        elif operation.lower() in ['reset']:
            reset_player_perms(user.id, instance_id)
            embed = base_embed(instance.id, title=f"Removed permission overwrites for {user.name}#{user.discriminator}")            
            await ctx.send(embed=embed)
        

        # Unknown operation
        else:
            raise commands.BadArgument('Operation needs to be either "list" or "set" or "reset", not "%s"' % operation)

    @permissions_group.command(name="guild", description="Set or view RCON permissions for a guild")
    @check_perms(instance=True)
    async def guild_permissions(self, ctx, operation: str = '', value: int = None):
        # List guild permissions
        if operation.lower() in ['', 'list', 'view', 'show']:
            instances = get_guild_instances(ctx.guild.id)

            if instances:
                embed = discord.Embed(title="Standard guild permissions")
                embed.set_author(icon_url=ctx.guild.icon_url, name=ctx.guild.name)

                for i, (instance, perms) in enumerate(instances):
                    perms = ", ".join([perm for perm, val in perms_to_dict(perms).items() if val])
                    embed.add_field(name=f"{str(i+1)} | {instance.name}", value=f"> **Perms:** {perms}")
                embed = add_empty_fields(embed)
            
            else:
                embed = discord.Embed(title="Standard guild permissions", description="There aren't any instances assigned to this guild just yet.")
                embed.set_author(icon_url=ctx.guild.icon_url, name=ctx.guild.name)

            await ctx.send(embed=embed)

        # Set guild permissions for the selected instance
        elif operation.lower() in ['set']:
            instance = Instance(self.bot.cache._get_selected_instance(ctx.author.id))
            
            # Update the guild permissions for the selected instance
            if value != None and int(value) >= 0 and int(value) <= 31:
                old_value = instance.default_perms
                instance.set_default_perms(value)

                embed = base_embed(instance.id, title=f"Changed guild permissions for {ctx.guild.name}")
                old_perms = ", ".join([perm for perm, val in perms_to_dict(old_value).items() if val])
                new_perms = ", ".join([perm for perm, val in perms_to_dict(value).items() if val])
                embed.add_field(name="Old Perms", value=f"> {old_perms}")
                embed.add_field(name="New Perms", value=f"> {new_perms}")
                
                await ctx.send(embed=embed)
                
            # Error
            else:
                raise commands.BadArgument("Permissions value out of range")

        # Unknown operation
        else:
            raise commands.BadArgument('Operation needs to be either "list" or "set", not "%s"' % operation)

    
    @permissions_group.command(name="help")
    async def permissions_help(self, ctx):
        embed = discord.Embed(title="Permission Values", description="Each of my commands require permission. Instance Managers can change who can use what command by setting permission values for users or even entire guilds (Discord servers).\n\nCurrently, there are 5 different types of permissions. Each of them represent a number, which is the square of the previous one. A list of all permissions can be seen here:```1 - Public commands\n2 - Game logs\n4 - Moderation commands\n8 - Administration commands\n16 - Instance management```\nIf you sum all of the values of the permissions you want together, you'll get the permissions value. For instance, permissions for public commands tied with moderation commands would give a permissions value of 1 + 4 = 5.\n\n**User-Specific Permissions**\nUser permissions grant a single user permission to use the commands belonging to that value. They can use these in every Discord guild this bot is in, as long as they have Administrator permissions in that guild. Every action is still logged.\n\n**Guild-Specific Permissions**\nGuild permissions grant every single member of that Discord guild permission to use the commands belonging to that value. However, these permissions are overwritten by user permissions and will then no longer apply to that user.")
        embed.add_field(name="Permission Commands", value="```r!instance perms [user]\nr!instance perms help\nr!instance perms <user> list\nr!instance perms <user> set <perms>\nr!instance perms <user> reset\nr!instance perms guild list\nr!instance perms guild set <perm> (0|1)```")
        await ctx.send(embed=embed)


    @instance_command.command(name="config")
    @check_perms(instance=True)
    async def instance_config(self, ctx, key: str = None, value = None):
        instance_id = self.bot.cache._get_selected_instance(ctx.author.id)
        instance = Instance(instance_id)
        if key: key = key.lower()

        if key == None or key not in instance.config.keys():
            embed = base_embed(instance.id, title='Config values')
            for key, value in instance.config.items():
                value = str(value) if str(value) else "NULL"
                embed.add_field(name=key, value=value)
            embed = add_empty_fields(embed)
            await ctx.send(embed=embed)
        
        elif value == None:
            embed = base_embed(instance.id, title='Config values', description=f"> **Current value:**\n> {key} = {instance.config[key]}")
            desc = CONFIG_DESC[key] if key in CONFIG_DESC.keys() else f"**{key}**\nNo description found."
            embed.description = embed.description + "\n\n" + desc
            await ctx.send(embed=embed)
        
        else:
            old_value = instance.config[key]
            if not old_value: old_value = "None"
            try: value = type(old_value)(value)
            except: raise commands.BadArgument('%s should be %s, not %s' % (value, type(old_value).__name__, type(value).__name__))
            else:
                instance.config[key] = value
                instance.store_config()

                embed = base_embed(instance.id, title='Updated config')
                embed.set_author(icon_url=ctx.guild.icon_url, name=ctx.guild.name)
                embed.add_field(name="Old Value", value=str(old_value))
                embed.add_field(name="New value", value=str(value))
                await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(instances(bot))
