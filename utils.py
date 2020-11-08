import discord
from discord.ext import commands

from rcon.instances import Instance


GAME_IMAGES = {
    "squad": "https://media.discordapp.net/attachments/729998051288285256/765669813338374144/unknown.png",
    "btw": "https://media.discordapp.net/attachments/768095907102720051/772495252850212884/2Q.png"
}


def get_name(user):
    return user.nick if user.nick else user.name


class Config:

    def __init__(self, path: str = "config.txt"):
        self.update()

    def update(self):
        self.config = {}
        with open("config.txt", "r") as f:
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


def add_empty_fields(embed: discord.Embed):
    fields = len(embed.fields)
    if fields > 3:
        empty_fields_to_add = 3 - (fields % 3)
        if empty_fields_to_add in range(1, 2):
            for i in range(empty_fields_to_add):
                embed.add_field(name="‏‎ ", value="‏‎ ") # These are special characters that can not be seen
    return embed


def base_embed(instance, title: str = None, description: str = None, color=discord.Embed.Empty):
    if isinstance(instance, int):
        instance = Instance(instance)
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name=instance.name, icon_url=GAME_IMAGES[instance.game])
    return embed