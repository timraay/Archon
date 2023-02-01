import discord
from discord.ext import commands
from asyncio import TimeoutError

from rcon.instances import Instance


GAME_IMAGES = {
    "squad": "https://media.discordapp.net/attachments/729998051288285256/765669813338374144/unknown.png",
    "ps": "https://media.discordapp.net/attachments/779050069252243477/790620643958718504/PostScriptum.png",
    "btw": "https://media.discordapp.net/attachments/768095907102720051/772495252850212884/2Q.png"
}


SIMPLIFIED_CLASS_NAMES = {
    int: "number",
    str: "text",
    discord.TextChannel: "text channel"
}


def get_name(user):
    return user.nick if user.nick else user.name


class Config:

    def __init__(self, path: str = "config.txt"):
        self.path = path
        self.update()

    def update(self):
        self.config = {}
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f.readlines():
                line = line.strip("\n").split("=", 1)
                if len(line) == 2:
                    self.config[line[0]] = line[1]
    
    def get(self, key: str, alternative_value=None, update_config=False):
        if update_config:
            self.update()
        try:
            res = self.config[key]
        except KeyError:
            res = alternative_value
        finally:
            return res


def get_player_input_type(player: str):
    try: # Can the value be an ID?
        int(player)
    except: # Value can't be converted to an int, must be a name
        return "name"
    else: # Value can be converted to an int, can be an ID
        if len(str(player)) == 17: # Value is same length as steam64id
            return "steam64id"
        elif len(str(player)) <= 3: # Value can be a squadid
            return "squadid"
        else: # Can't be steam64id or squadid, must be a name
            return "name"


def add_empty_fields(embed):
    try: fields = len(embed._fields)
    except AttributeError: fields = 0
    if fields > 3:
        empty_fields_to_add = 3 - (fields % 3)
        if empty_fields_to_add in [1, 2]:
            for i in range(empty_fields_to_add):
                embed.add_field(name="‏‎ ", value="‏‎ ") # These are special characters that can not be seen
    return embed


def base_embed(instance, title: str = None, description: str = None, color=None):
    if isinstance(instance, int):
        instance = Instance(instance)
    embed = EmbedMenu(title=title, description=description, color=color)
    embed.set_author(name=instance.name, icon_url=GAME_IMAGES[instance.game])
    return embed


class EmbedMenu(discord.Embed):
    def add_option(self, emoji, title, description):
        option = {
            'emoji': str(emoji),
            'name': str(title),
            'value': str(description)
        }
        try:
            self._options.append(option)
        except AttributeError:
            self._options = [option]
    
    def remove_option(self, index):
        try:
            del self._options[index]
        except (AttributeError, IndexError):
            pass
    
    def set_option_at(self, index, *, emoji, title, description):
        try:
            option = self._option[index]
        except (TypeError, IndexError, AttributeError):
            raise IndexError('option index out of range')

        option['emoji'] = str(emoji)
        option['name'] = str(title)
        option['value'] = str(description)
        return self
    
    def insert_option_at(self, index, *, emoji, title, description):
        option = {
            'emoji': str(emoji),
            'name': str(title),
            'value': str(description)
        }

        try:
            self._options.insert(index, option)
        except AttributeError:
            self._options = [option]

        return self

    def clear_options(self):
        try:
            self._options.clear()
        except AttributeError:
            self._options = []

    async def run(self, ctx, timeout=60):
        emojis = []
        self._fields = []
        for i, option in enumerate(self._options):
            field = {
                'inline': True,
                'name': option["emoji"] + " " + option["name"],
                'value': option["value"]
            }
            self._fields.append(field)
        
        self._fields = add_empty_fields(self)._fields

        emojis = [option['emoji'] for option in self._options]
        msg = await ctx.send(embed=self)
        for emoji in emojis:
            await msg.add_reaction(emoji)
        
        def check(reaction, user):
            return str(reaction.emoji) in emojis and user == ctx.author
        try:
            reaction, user = await ctx.bot.wait_for('reaction_add', timeout=timeout, check=check)
        except TimeoutError:
            await msg.clear_reactions()
            return None
        else:
            await msg.clear_reactions()
            return reaction
