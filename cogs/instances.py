import discord
from discord.ext import commands
import asyncio
import re

from rcon.connection import RconAuthError
from rcon.instances import *

from utils import add_empty_fields, base_embed, get_name


CONFIG_DESC = {
    "guild_id": "**Guild ID (guild\\_id)**\nThis is the ID of the Discord guild your instance will mainly operate in. Guild permissions will be applied to this guild only. Channels for game logs must be in this guild. Users with user permissions will still be able to access your instance outside of this guild.",
    "chat_trigger_words": "**Chat Trigger Words (chat\\_trigger\\_words)**\nChat trigger words send a notification through Discord whenever one of the specified words is mentioned by a player in-game. This allows admins to respond quickly to requests.\n\n`chat_trigger_words` is a comma-seperated list of words. What that means, is you can add as many trigger words as you like. Just make sure to put a comma inbetween them.",
    "chat_trigger_channel_id": "**Chat Trigger Channel ID (chat\\_trigger\\_channel\\_id)**\nThis is where the chat trigger will send notifications to. When a channel with this ID can not be found inside the guild specified with `guild_id`, this feature will be disabled.",
    "chat_trigger_mentions": "**Chat Trigger Mentions (chat\\_trigger\\_mentions)**\nThis is the message attached to the notification. To turn it into an actual notification, you probably want to include a role or user mention in here.\n\nThe bot doesn't automatically format this into mentions, you have to do that yourself. Mentions are formatted like this:```<@USER_ID> for user mentions\n<@&ROLE_ID> for role mentions```You can also mention a role or user and put a backslash (\\) in front of it to get it in this format.",
    "chat_log_channel_id": "**Chat Log Channel ID (chat\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log chat messages to.",
    "joins_log_channel_id": "**Joins Log Channel ID (joins\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log players joining and leaving to.",
    "rcon_log_channel_id": "**RCON Log Channel ID (rcon\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log RCON actions to.",
    "teamkills_log_channel_id": "**Teamkills Log Channel ID (teamkills\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log teamkills to.",
    "match_log_channel_id": "**Match Log Channel ID (match\\_log\\_channel\\_id)**\nThis is the channel ID of the channel to automatically log match changes to."
}



CONFIGS = {
    "chat_trigger_words": {
        "name": "Trigger Words",
        "emoji": "📜",
        "short_desc": "Words that trigger an alert",
        "long_desc": "**Chat Trigger Words (chat\\_trigger\\_words)**\nChat trigger words send a notification through Discord whenever one of the specified words is mentioned by a player in-game. This allows admins to respond quickly to requests.\n\n`chat_trigger_words` is a comma-seperated list of words. What that means, is you can add as many trigger words as you like. Just make sure to put a comma inbetween them."
    },
    "chat_trigger_channel_id": {
        "name": "Alerts Channel",
        "emoji": "🔗",
        "short_desc": "The ID of the channel to send alerts to",
        "long_desc": ""
    },
    "chat_trigger_mentions": {
        "name": "Mentions",
        "emoji": "🗣️",
        "short_desc": "What roles to mention when an alert is sent",
        "long_desc": ""
    },
    "chat_trigger_confirmation": {
        "name": "Confirmation Warning",
        "emoji": "🪃",
        "short_desc": "The message sent to the alerting player",
        "long_desc": ""
    },
    "chat_trigger_cooldown": {
        "name": "Alert Cooldown",
        "emoji": "⏰",
        "short_desc": "The cooldown inbetween alerts from one player",
        "long_desc": ""
    },
    "chat_trigger_require_reason": {
        "name": "Require Reason",
        "emoji": "🤏",
        "short_desc": "Whether the player must include a reason",
        "long_desc": ""
    },

    "channel_log_chat": {
        "name": "Chat Log Channel",
        "emoji": "💬",
        "short_desc": "The ID of the channel to log chat messages in",
        "long_desc": ""
    },
    "channel_log_joins": {
        "name": "Joins Log Channel",
        "emoji": "👥",
        "short_desc": "The ID of the channel to log player connectivity in",
        "long_desc": ""
    },
    "channel_log_match": {
        "name": "Match Log Channel",
        "emoji": "🌊",
        "short_desc": "The ID of the channel to log match events in",
        "long_desc": ""
    },
    "channel_log_teamkills": {
        "name": "Teamkills Log Channel",
        "emoji": "🕵️‍♂️",
        "short_desc": "The ID of the channel to log teamkills in",
        "long_desc": ""
    },
    "channel_log_rcon": {
        "name": "RCON Log Channel",
        "emoji": "🤖",
        "short_desc": "The ID of the channel to log RCON actions in",
        "long_desc": ""
    }
}

PERMISSION_LIST = {
    'public': ['server', 'servers'],
    'players': ['players', 'squad', 'player'],
    'changemap': ['skip_match', 'restart_match', 'set_next_map'],
    'cheat': ['slomo'],
    'message': ['broadcast', 'warn', 'warn_all'],
    'logs': ['logs', 'chat'],
    'password': ['password'],
    'teamchange': ['switch_team', 'switch_squad'],
    'kick': ['kick', 'punish'],
    'disband': ['disband_squad', 'kick_from_squad', 'demote_commander'],
    'ban': ['ban'],
    'config': ['player_limit', 'map_rotation'],
    'execute': ['execute'],
    'manage': ['alerts', 'logging'],
    'creds': ['inst creds'],
    'instance': ['inst connect', 'inst disconnect', 'inst config', 'permissions']
}


class instances(commands.Cog):
    """Create, select and manage instances"""

    def __init__(self, bot):
        self.bot = bot


    ### r!instance
    ### r!instance <instance>
    @commands.group(invoke_without_command=True, name="instance", description="Create, select and manage instances", usage="r!inst help", aliases=["inst"])
    async def instance_command(self, ctx, *, instance_id=None):
        if instance_id:
            await self.select_instance.__call__(ctx, instance_id=instance_id)
        
        else:
            current_instance = self.bot.cache._get_selected_instance(ctx.author)
            try: embed = base_embed(current_instance)
            except:
                embed = discord.Embed()
                embed.set_author(name="No instance selected")
            embed.set_footer(text='Use "r!inst help" to view a list of options')
            await ctx.send(embed=embed)
    
    ### r!instance help
    @instance_command.command(name="help")
    async def instance_help(self, ctx):
        embed = discord.Embed(title="Server Instances Help")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
        embed.add_field(name="Public Commands", value="```r!instance <name_or_id>\nr!instance list\nr!instance perms```", inline=False)
        embed.add_field(name="Admin Commands", value="```r!perms\nr!perms help\nr!perms (set|grant|remove|reset) (default|<role>|<user>) <perms...>\nr!alerts [option] [value]\nr!logging [option] [value]\nr!instance config\nr!instance config <key>\nr!instance config <key> <value>\n\nr!instance add\nr!instance reconnect\nr!instance disconnect\nr!instance credentials\nr!instance delete```", inline=False)
        await ctx.send(embed=embed)

    ### r!instance list
    @instance_command.command(name="list", description="List all available instances", usage="r!instance list", aliases=["view", "show"])
    async def list_instances(self, ctx):
        instances = get_available_instances(ctx.author, ctx.guild.id)
        current_instance = self.bot.cache._get_selected_instance(ctx.author)
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
            perms = ", ".join([perm for perm, val in perms.to_dict().items() if val])
            embed.add_field(name=f"{str(i+1)} | {inst.name} {availability}", value=f"> **Perms:** {perms}")
        embed = add_empty_fields(embed)

        await ctx.send(embed=embed)
    ### r!instance select <instance>
    @instance_command.command(name="select", description="Select an instance to control", usage="r!instance <instance>")
    async def select_instance(self, ctx, *, instance_id: str):
        instances = get_available_instances(ctx.author, ctx.guild.id)
        inst = None
        for i, (instance, perms) in enumerate(instances):
            if str(i+1) == instance_id or instance.name.lower() == instance_id.lower():
                inst = instance
                break
        if not inst:
            raise commands.BadArgument("No instance found with name or ID %s" % instance_id)
        self.bot.cache.selected_instance[ctx.author.id] = instance.id

        perms = ", ".join([perm for perm, val in perms.to_dict().items() if val])
        embed = discord.Embed(title=f'Selected the "{instance.name}" instance', description=f"> **Perms:** {perms}")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(4)
        await msg.delete()

    ### r!instance connect
    @instance_command.command(name="connect", aliases=["reconnect"])
    @check_perms(instance=True)
    async def connect_instance(self, ctx):
        instance_id = self.bot.cache._get_selected_instance(ctx.author)
        inst = Instance(instance_id)

        res = self.bot.cache._connect_instance(inst, return_exception=True)
        if isinstance(res, Exception): # Instance could not be connected
            raise res
        else: # Instance was successfully connected
            embed = base_embed(instance_id, title="Instance was successfully (re)connected")
            await ctx.send(embed=embed)
    ### r!instance disconnect
    @instance_command.command(name="disconnect", aliases=["shutdown"])
    @check_perms(instance=True)
    async def disconnect_instance(self, ctx):
        instance_id = self.bot.cache._get_selected_instance(ctx.author)
        inst = Instance(instance_id)

        self.bot.cache.instances[instance_id] = None
        embed = base_embed(instance_id, title="Instance was shut down")
        await ctx.send(embed=embed)
    
    ### r!instance delete
    @instance_command.command(name="delete")
    @is_owner()
    async def delete_instance(self, ctx):
        instance_id = self.bot.cache._get_selected_instance(ctx.author)
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
            embed = base_embed(inst.id, title="Instance deleted")
            self.bot.cache.delete_instance(instance_id)
            await msg.edit(embed=embed)
    ### r!instance create
    @instance_command.command(name="create", aliases=["add"])
    @commands.has_permissions(administrator=True)
    async def create_instance(self, ctx):
        await self.ask_server_info(ctx, operation=0)

    ### r!instance credentials
    @instance_command.command(name="credentials", aliases=["creds", "edit"])
    @check_perms(creds=True)
    async def change_credentials(self, ctx):
        await self.ask_server_info(ctx, operation=1)


    async def ask_server_info(self, ctx, operation = 0):
        try: await ctx.author.send(ctx.author.mention)
        except:
            await ctx.send(f":no_entry_sign: {ctx.author.mention}, please enable DMs")
            return

        if operation not in [0, 1]:
            operation = 0
        
        if operation == 1:
            inst = Instance(self.bot.cache._get_selected_instance(ctx.author, ctx.guild.id))

        # Create embed
        def setup_embed(question):
            embed = discord.Embed(title=question, description="Type your answer down below. You can change your answers later.")
            if operation == 0:
                embed = discord.Embed(title=question, description="Type your answer down below. You can change your answers later.")
                embed.set_author(name="Creating your instance...")
            elif operation == 1:
                embed = base_embed(inst, title=question, description="Type your answer down below. You can change your answers later.")
                embed._author['name'] = f"Editing {inst.name}..."
            embed.set_footer(text="This action will be canceled if the channel remains inactive for 2 minutes during its creation.")
            return embed

        async def ask_game():
            embed = setup_embed("What game is your server for, Squad, PS or BTW?")
            msg = await ctx.author.send(embed=embed)
            def check(message):
                return message.channel == msg.channel and message.author == ctx.author
            answer = ""
            while answer not in ['squad', 'ps', 'btw']:
                answer = await self.bot.wait_for('message', check=check, timeout=120.0)
                answer = answer.content.lower()
                if answer not in ['squad', 'ps', 'btw']:
                    await ctx.author.send(f'Send either "Squad", "PS" or "BTW", not "{answer}"')
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
                    if operation == 0: await ctx.author.send("Instance creation cancelled.")
                    elif operation == 0: await ctx.author.send("Instance editing cancelled.")
                    return
                values = [game, address, port, password, name]
                
                if confirmation == "✅":
                    msg = await ctx.author.send("Trying to establish a connection...")
                    try:
                        if operation == 0:
                            inst = add_instance(game=values[0], address=values[1], port=values[2], password=values[3], name=values[4], owner_id=ctx.author.id)
                            inst.config['guild_id'] = ctx.guild.id
                            inst.store_config()
                        elif operation == 1:
                            inst = edit_instance(inst.id, game=values[0], address=values[1], port=values[2], password=values[3], name=values[4])
                    except RconAuthError as e:
                        await ctx.author.send(f"Unable to connect to the server: {str(e)}")
                        await asyncio.sleep(3)
                        confirmation = ""
                    except commands.BadArgument as e:
                        await ctx.author.send(f"An instance using this address already exists!")
                        await asyncio.sleep(3)
                        confirmation = ""
                    else:
                        await msg.edit(content="Connection established!")
                        self.bot.cache._connect_instance(inst)
                        embed = base_embed(inst.id, description="You can now customize your instance further by setting permissions and changing config options. See `r!inst help` for more information.", color=discord.Color.green())
                        if operation == 0: embed.title = "Instance created!"
                        elif operation == 1: embed.title = "Instance edited!"
                        await ctx.author.send(embed=embed)

        except asyncio.TimeoutError:
            await ctx.author.send("You took too long to respond. Execute the command again to retry.")
            return


    async def get_perms_object(self, ctx, object):
        if object.lower() in ['guild', 'default']:
            object = 'default'
            object_type = 'default'
        else:
            try:
                object = await commands.UserConverter().convert(ctx, object)
                object_type = 'user'
            except:
                try:
                    object = await commands.RoleConverter().convert(ctx, object)
                    object_type = 'role'
                except:
                    object = None
                    object_type = None
        if not object:
            raise commands.BadArgument('Unknown permission object. Should be a user, role, or "default".')
        return object, object_type

    @commands.group(invoke_without_command=True, name="permissions", description="Set or view RCON permissions", aliases=["perms"])
    @check_perms(instance=True)
    async def permissions_group(self, ctx):
        instance_id = self.bot.cache._get_selected_instance(ctx.author)
        instance = Instance(instance_id)
        embed = base_embed(instance, title='All Permissions')
        perms = get_perms_for_instance(instance_id, ctx.guild.id)

        embed.description = f'**Default Permissions:**\n> {str(perms["default"])}'

        if perms['roles']:
            embed.description += '\n\n**Roles:**'
            for role, perm in perms['roles'].items():
                mention = ctx.guild.get_role(role)
                mention = mention.mention if mention else role
                embed.description += f'\n{mention}: {perm}'

        if perms['users']:
            embed.description += '\n\n**Users:**'
            for user, perm in perms['users'].items():
                mention = ctx.bot.get_user(user)
                mention = mention.mention if mention else user
                embed.description += f'\n{mention}: {perm}'
        
        await ctx.send(embed=embed)

    @permissions_group.command(name='set', aliases=[])
    @check_perms(instance=True)
    async def set_permissions(self, ctx, object, *, perms):
        object, object_type = await self.get_perms_object(ctx, object)
        perms = Permissions(**{p: True for p in re.split(', |,\n|,| |\n', perms)})
        instance_id = ctx.bot.cache._get_selected_instance(ctx.author)
        instance = Instance(instance_id)
        embed = base_embed(instance)
        
        if object_type == 'default':
            old_perms = Permissions.from_int(instance.default_perms)
            instance.set_default_perms(int(perms))
            embed.title = "Updated default permissions"
        else:
            old_perms = get_perms_entry(instance_id, object.id)
            set_perms(object.id, instance_id, int(perms), object_type)
            embed.title = f"Updated permissions for {object_type} {object.name}"

        embed.add_field(name='Old permissions', value=f'> {old_perms}')
        embed.add_field(name='New permissions', value=f'> {perms}')
        await ctx.send(embed=embed)

    @permissions_group.command(name='grant', aliases=['add'])
    @check_perms(instance=True)
    async def grant_permissions(self, ctx, object, *, perms):
        object, object_type = await self.get_perms_object(ctx, object)
        perms = Permissions(**{p: True for p in re.split(', |,\n|,| |\n', perms)})
        instance_id = ctx.bot.cache._get_selected_instance(ctx.author)
        instance = Instance(instance_id)
        embed = base_embed(instance)

        if object_type == 'default':
            old_perms = Permissions.from_int(instance.default_perms)
            new_perms = old_perms + perms
            instance.set_default_perms(int(new_perms))
            embed.title = "Updated default permissions"
        else:
            old_perms = get_perms_entry(instance_id, object.id)
            new_perms = old_perms + perms if old_perms else perms
            set_perms(object.id, instance_id, int(new_perms), object_type)
            embed.title = f"Updated permissions for {object_type} {object.name}"

        embed.add_field(name='Old permissions', value=f'> {old_perms}')
        embed.add_field(name='New permissions', value=f'> {new_perms}')
        await ctx.send(embed=embed)
    
    @permissions_group.command(name='revoke', aliases=['remove'])
    @check_perms(instance=True)
    async def revoke_permissions(self, ctx, object, *, perms):
        object, object_type = await self.get_perms_object(ctx, object)
        perms = Permissions(**{p: True for p in re.split(', |,\n|,| |\n', perms)})
        instance_id = ctx.bot.cache._get_selected_instance(ctx.author)
        instance = Instance(instance_id)
        embed = base_embed(instance)

        if object_type == 'default':
            old_perms = Permissions.from_int(instance.default_perms)
            new_perms = old_perms - perms
            instance.set_default_perms(int(new_perms))
            embed.title = "Updated default permissions"
        else:
            old_perms = get_perms_entry(instance_id, object.id)
            new_perms = old_perms - perms if old_perms else Permissions()
            set_perms(object.id, instance_id, int(new_perms), object_type)
            embed.title = f"Updated permissions for {object_type} {object.name}"

        embed.add_field(name='Old permissions', value=f'> {old_perms}')
        embed.add_field(name='New permissions', value=f'> {new_perms}')
        await ctx.send(embed=embed)
        
    @permissions_group.command(name='reset', aliases=['delete'])
    @check_perms(instance=True)
    async def reset_permissions(self, ctx, object):
        object, object_type = await self.get_perms_object(ctx, object)
        instance_id = ctx.bot.cache._get_selected_instance(ctx.author)
        instance = Instance(instance_id)
        embed = base_embed(instance)
        new_perms = None

        if object_type == 'default':
            old_perms = Permissions.from_int(instance.default_perms)
            instance.set_default_perms(int(new_perms))
            embed.title = "Removed default permissions"
        else:
            old_perms = get_perms_entry(instance_id, object.id)
            reset_perms(object.id, instance_id)
            embed.title = f"Removed permissions for {object_type} {object.name}"

        embed.add_field(name='Old permissions', value=f'> {old_perms}')
        embed.add_field(name='New permissions', value=f'> {new_perms}')
        await ctx.send(embed=embed)
        
    @permissions_group.command(name='help', aliases=['info', 'list'])
    @check_perms(instance=True)
    async def permissions_help(self, ctx):
        embed = discord.Embed(title='Permissions')
        embed.description = f'By default, everyone in the Discord server will be given the default permissions. These can be overwritten by permissions linked to roles. If a user has multiple roles with permissions linked, the top role will count. These permissions can then be overwritten on a per-user basis. Permissions don\'t stack. The instance owner will always have all permissions.\n\n`{ctx.prefix}perms (set|grant|remove|reset) (default|<role>|<user>) <perms...>`'
        embed.add_field(name='List of permissions', value='\n'.join([f'`{k}` - {ctx.prefix}{(", "+ctx.prefix).join(v)}' for k, v in PERMISSION_LIST.items()]))
        await ctx.send(embed=embed)


    ### r!instance config
    ### r!instance config <setting>
    ### r!instance config <setting> <value>
    @instance_command.command(name="config")
    @check_perms(instance=True)
    async def instance_config(self, ctx, key: str = None, value = None):
        instance_id = self.bot.cache._get_selected_instance(ctx.author)
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
            try: value = type(old_value)(value)
            except: raise commands.BadArgument('%s should be %s, not %s' % (value, type(old_value).__name__, type(value).__name__))
            else:

                if key == "guild_id":
                    guild = self.bot.get_guild(int(value))
                    if not guild:
                        raise commands.BadArgument('Unable to find a guild with ID %s' % value)
                    member = guild.get_member(ctx.author.id)
                    if not member:
                        raise commands.BadArgument('You haven\'t joined that guild yourself')
                    if not member.guild_permissions.administrator:
                        raise commands.BadArgument('You need to have administrator permissions in that guild')

                instance.config[key] = value
                instance.store_config()

                if not old_value: old_value = "None"
                embed = base_embed(instance.id, title='Updated config')
                embed.add_field(name="Old Value", value=str(old_value))
                embed.add_field(name="New value", value=str(value))
                await ctx.send(embed=embed)



    ### r!alerts [option] [value]
    @commands.command(description="Configure the chat alerts feature", usage="r!alerts [option] [value]", aliases=["triggers"])
    @check_perms(manage=True)
    async def alerts(self, ctx, option: str = None, value = None):
        CONFIG_KEY = "chat_trigger_"
        CONFIG_TITLE = "Chat Alerts"
        await self.config_menu(ctx, CONFIG_TITLE, CONFIG_KEY, option, value)

    ### r!logging [option] [value]
    @commands.command(description="Configure the logging channels", usage="r!alerts [option] [value]", aliases=["channels", "log_channels", "logchannels"])
    @check_perms(manage=True)
    async def logging(self, ctx, option: str = None, value = None):
        CONFIG_KEY = "channel_log_"
        CONFIG_TITLE = "Logging Channels"
        await self.config_menu(ctx, CONFIG_TITLE, CONFIG_KEY, option, value)



    async def config_menu(self, ctx, config_title, config_key, option: str = None, value = None):
        inst_id = self.bot.cache._get_selected_instance(ctx.author, ctx.channel.id)
        inst = Instance(inst_id)
        CONFIG_KEY = str(config_key)
        CONFIG_TITLE = str(config_title)

        if option:
            option = option.replace(CONFIG_KEY, "")
            key = CONFIG_KEY+option

        def update_value(option, value):
            option = option.replace(CONFIG_KEY, "")
            key = CONFIG_KEY+option
            if key not in inst.config.keys():
                raise KeyError("Config option %s does not exist" % key)
            old_value = inst.config[key]

            try: value = type(inst.config[key])(value)
            except ValueError: raise commands.BadArgument("Value should be %s, not %s" % (type(inst.config[key]).__name__, type(value).__name__))

            inst.config[CONFIG_KEY + option] = value
            inst.store_config()

            return old_value, value

        if not option:
            embed = base_embed(inst, title=f"{CONFIG_TITLE} Configuration", description=f"To edit values, react with the emojis below or type `r!{ctx.command.name} <option> <value>`")
            for k, v in inst.config.items():
                if k.startswith(CONFIG_KEY):
                    try: option_info = CONFIGS[k]
                    except KeyError: continue
                    value = v if v else "None"
                    embed.add_option(option_info["emoji"], title=option_info['name'], description=f"ID: {k.replace(CONFIG_KEY, '')}\nValue: `{value}`\n\n*{option_info['short_desc']}*")

            reaction = await embed.run(ctx)

            if reaction:
                (key, info) = [(k, v) for k, v in CONFIGS.items() if v['emoji'] == str(reaction.emoji)][0]
                option = key.replace(CONFIG_KEY, "")
                embed = base_embed(inst, title=f"Editing value {key}... ({info['name']})", description=f"{get_name(ctx.author)}, what should the new value be? To cancel, type \"cancel\".")
                msg = await ctx.send(embed=embed)

                def check(m): return m.author == ctx.author and m.channel == ctx.channel
                try: m = await self.bot.wait_for('message', timeout=120, check=check)
                except: await msg.edit(embed=base_embed(inst, description=f"{get_name(ctx.author)}, you took too long to respond."))
                else:
                    
                    if m.content.lower() == "cancel":
                        embed.description = "You cancelled the action."
                        embed.color = discord.Color.dark_red()
                        await msg.edit(embed=embed)
                        return
                    value = m.content
                    
                    old_value, value = update_value(option, value)

                    embed = base_embed(inst, title=f'Updated {CONFIGS[key]["name"]}')
                    embed.add_field(name="Old Value", value=str(old_value) if old_value else 'None')
                    embed.add_field(name="New value", value=str(value) if value else 'None')
                    await ctx.send(embed=embed)

        elif value == None:
            embed = base_embed(inst, title=f'Chat Alerts: {option}', description=f"> **Current value:**\n> {inst.config[key] if inst.config[key] else 'None'}")
            desc = CONFIGS[key]['long_desc'] if key in CONFIGS.keys() and CONFIGS[key]['long_desc'] else f"**{key}**\nNo description found."
            embed.description = embed.description + "\n\n" + desc
            await ctx.send(embed=embed)
        
        else:
            old_value, value = update_value(option, value)

            embed = base_embed(inst, title=f'Updated {CONFIGS[key]["name"]}')
            embed.add_field(name="Old Value", value=str(old_value) if old_value else 'None')
            embed.add_field(name="New value", value=str(value) if value else 'None')
            await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(instances(bot))
