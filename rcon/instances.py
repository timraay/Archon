import sqlite3
import discord
from discord.ext import commands
from rcon.connection import RconConnection


"""
We're using a database with four tables for managing servers and permissions:

instances.db


The first table in instances.db will be named "instances" with a row for each instance.
Each of these rows will hold the name, address, port, password and owner_id of that instance.

instances
    - instance_id       # The unique ID of this instance
    - name              # The name of the instance
    - address           # The address used to connect to the instance
    - port              # The port used to connect to the instance
    - password          # The password used to connect to the instance
    - owner_id          # The discord user ID of the owner of the instance
    - default_perms     # The default permissions for each user


The second table in instances.db will be named "config" with a row for each instance.
Each of these rows will hold configurations for this instance for all sorts of features.

config
    - instance_id               # The unique ID of this instance
    - guild_id                  # The guild to apply to default perms and other features (default: guild of creation)
    - chat_trigger_words        # A comma-separated list of keywords to trigger alerts (default: !admin)
    - chat_trigger_channel_id   # The channel to send trigger alerts in


The third table in instances.db will be named "permissions" with a row for each assigned group of permissions.
Each of these rows will hold the instance ID, the user ID, and a permissions integer.

permissions
    - instance_id       # The instance ID this user has permissions for
    - user_id           # The user ID of the discord user that has permissions
    - perms             # The permissions this user has for this instance


The fourth and final table in instances.db will be named "logs" with a row for each logged action.
Each of these rows will hold the instance ID, the category, the message, and the timestamp when the action happend.

logs
    - instance_id       # The instance ID this log is from
    - category          # The category this action belongs to
    - message           # The message to be logged
    - timestamp         # The timestamp when this action was recorded


Permissions are stored as an integer. These can be converted to bits.
Each bit represents a permission. Below is a list of all permissions and their int.
If you sum the ints of the permissions you want to assign you get the permission integer.

1 - public commands
2 - logs
4 - moderation commands
8 - administration commands
16 - instance management
"""


db = sqlite3.connect('instances.db')
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS instances(instance_id INT NOT NULL, name TEXT, address TEXT, port INT, password TEXT, owner_id INT, game TEXT, default_perms INT, PRIMARY KEY (instance_id))')
cur.execute('CREATE TABLE IF NOT EXISTS config(instance_id INT, guild_id INT, chat_trigger_words TEXT, chat_trigger_channel_id INT, chat_trigger_mentions TEXT, chat_log_channel_id INT, FOREIGN KEY (instance_id) REFERENCES instances(instance_id))')
cur.execute('CREATE TABLE IF NOT EXISTS permissions(instance_id INT, user_id INT, perms INT, FOREIGN KEY (instance_id) REFERENCES instances(instance_id))')
db.commit()


def add_instance(name: str, address: str, port: int, password: str, owner_id: int, game: str, default_perms: int = 0):
    # Look for already existing instances that use this address.
    cur.execute('SELECT * FROM instances WHERE address = ?', (address,))
    if cur.fetchone():
        raise commands.BadArgument("A server with this address has already been registered")

    # Open and close a connection to see whether this server can be connected
    # to. The RconConnection class will raise a RconAuthError otherwise.
    rcon = RconConnection(address, port, password)
    rcon._sock.close()

    # The instance can now be added. But first we
    # need to create a new unique ID for this instance.
    cur.execute('SELECT MAX(instance_id) FROM instances')
    instance_id = cur.fetchone()[0]
    instance_id = instance_id + 1 if isinstance(instance_id, int) else 0
    # Now we have all parameters we can add the instance to the database.
    cur.execute('INSERT INTO instances VALUES (?,?,?,?,?,?,?,?)', (instance_id, name, address, port, password, owner_id, game, default_perms))
    cur.execute(f'INSERT INTO permissions VALUES (?,?,?)', (instance_id, owner_id, 31))
    _insert_config_row(instance_id)
    db.commit()

    return Instance(instance_id)

def get_perms(user_id: int, guild_id: int, instance_id: int, is_dict=True):
    perms_int = 0
    
    for instance, perms in get_available_instances(user_id, guild_id):
        if instance.id == instance_id:
            perms_int = perms

    if not is_dict:
        return perms_int
    else:
        perms_dict = perms_to_dict(perms_int)
        return perms_dict

def perms_to_dict(perms: int):
    perms_bin = format(perms, 'b').zfill(5)[::-1]

    perms_dict = {}
    perms_dict['public'] = bool(int(perms_bin[0]))
    perms_dict['logs'] = bool(int(perms_bin[1]))
    perms_dict['moderation'] = bool(int(perms_bin[2]))
    perms_dict['administration'] = bool(int(perms_bin[3]))
    perms_dict['instance'] = bool(int(perms_bin[4]))
    return perms_dict

def get_instances():
    cur.execute('SELECT instance_id FROM instances')
    instances = [Instance(instance_id[0]) for instance_id in cur.fetchall()]
    return instances

def get_available_instances(user_id: int, guild_id: int = None):
    instances = []

    cur.execute('SELECT instance_id FROM instances WHERE owner_id = ?', (user_id,))
    res = [(row[0], 31) for row in cur.fetchall()]
    for instance_id, perms in res:
        instance = Instance(instance_id)
        instances.append((instance, perms))

    cur.execute('SELECT instance_id, perms FROM permissions WHERE user_id = ? AND perms > 0', (user_id,))
    res = cur.fetchall()
    for instance_id, perms in res:
        if instance_id in [instance.id for instance, perms in instances]:
            continue
        instance = Instance(instance_id)
        instances.append((instance, perms))
    
    if guild_id:
        cur.execute('SELECT instance_id, default_perms FROM instances WHERE instance_id IN (SELECT instance_id FROM config WHERE guild_id = ?) AND default_perms > 0', (guild_id,))
        res = cur.fetchall()
        for instance_id, perms in res:
            if instance_id in [instance.id for instance, perms in instances]:
                continue
            instance = Instance(instance_id)
            instances.append((instance, perms))

    
    return instances

def get_guild_instances(guild_id: int):
    instances = []
    cur.execute('SELECT instance_id, default_perms FROM instances WHERE instance_id IN (SELECT instance_id FROM config WHERE guild_id = ?)', (guild_id,))
    res = cur.fetchall()
    for instance_id, perms in res:
        instance = Instance(instance_id)
        instances.append((instance, perms))
    return instances

def set_player_perms(user_id: int, instance_id: int, perms: int):
    # Check if player already has perms set for this instance
    cur.execute('SELECT * FROM permissions WHERE user_id = ? AND instance_id = ?', (user_id, instance_id))
    
    # Players already has perms set for this instance
    if cur.fetchone():
        cur.execute('UPDATE permissions SET perms = ? WHERE user_id = ? AND instance_id = ?', (perms, user_id, instance_id))
        db.commit()
    
    # Player doesn't have any perms set for this instance yet
    else:
        cur.execute('INSERT INTO permissions VALUES (?,?,?)', (instance_id, user_id, perms))
        db.commit()
def reset_player_perms(user_id: int, instance_id: int):
    # Check if player has perms set for this instance
    cur.execute('SELECT * FROM permissions WHERE user_id = ? AND instance_id = ?', (user_id, instance_id))
    
    # Player has perms set for this instance
    if cur.fetchone():
        cur.execute('DELETE FROM permissions WHERE user_id = ? AND instance_id = ?', (user_id, instance_id))
        db.commit()

# Predicate
def has_perms(ctx, public=None, logs=None, moderation=None, administration=None, instance=None):
    perms = ctx.bot.cache.perms(ctx.author.id, ctx.guild.id)
    is_ok = True
    if public != None and public != perms["public"]: is_ok = False
    if logs != None and logs != perms["logs"]: is_ok = False
    if moderation != None and moderation != perms["moderation"]: is_ok = False
    if administration != None and administration != perms["administration"]: is_ok = False
    if instance != None and instance != perms["instance"]: is_ok = False
    return is_ok

# Wrappers
def check_perms(public=None, logs=None, moderation=None, administration=None, instance=None):
    async def predicate(ctx):
        perms = ctx.bot.cache.perms(ctx.author.id, ctx.guild.id)
        is_ok = True
        if public != None and public != perms["public"]: is_ok = False
        if logs != None and logs != perms["logs"]: is_ok = False
        if moderation != None and moderation != perms["moderation"]: is_ok = False
        if administration != None and administration != perms["administration"]: is_ok = False
        if instance != None and instance != perms["instance"]: is_ok = False
        if not is_ok:
            instance_id = ctx.bot.cache._get_selected_instance(ctx.author.id)
            if instance_id == -1:
                await ctx.send(":no_entry_sign: You don't have access to any instances yet!")
            else:
                await ctx.send(":no_entry_sign: You don't have the required permissions to execute this command!")
        return is_ok
    return commands.check(predicate)
def is_game(game: str):
    async def predicate(ctx):
        instance = Instance(ctx.bot.cache._get_selected_instance(ctx.author.id))
        if instance.game != game:
            await ctx.send(f":no_entry_sign: Invalid instance!\n`This command only works for %s servers`" % game.upper())
        return instance.game == game
    return commands.check(predicate)
def is_owner():
    async def predicate(ctx):
        cur.execute('SELECT instance_id FROM instances WHERE instance_id = ? AND owner_id = ?', (ctx.bot.cache._get_selected_instance(ctx.author), ctx.author.id))
        if cur.fetchone():
            return True
        else:
            await ctx.send(":no_entry_sign: You need to be the instance owner to use this command!")
            return False
    return commands.check(predicate)

class Instance:
    def __init__(self, id: int):
        cur.execute('SELECT * FROM instances WHERE instance_id = ?', (id,))
        res = cur.fetchone()
        if not res:
            raise UnknownInstanceError("No instance found with ID %s" % id)
        self.id, self.name, self.address, self.port, self.password, self.owner_id, self.game, self.default_perms = res

        self.config = {}
        cur.execute('SELECT * FROM config WHERE instance_id = ?', (id,))
        res = cur.fetchone()
        if not res:
            res = _insert_config_row(self.id)
        self.id, self.config["guild_id"], self.config["chat_trigger_words"], self.config["chat_trigger_channel_id"], self.config["chat_trigger_mentions"], self.config["chat_log_channel_id"] = res

    def delete(self):
        cur.execute('DELETE FROM permissions WHERE instance_id = ?', (self.id,))
        cur.execute('DELETE FROM config WHERE instance_id = ?', (self.id,))
        cur.execute('DELETE FROM logs WHERE instance_id = ?', (self.id,))
        cur.execute('DELETE FROM instances WHERE instance_id = ?', (self.id,))
        db.commit()

    def _set_db_value(self, header, value):
        cur.execute(f'UPDATE instances SET {header} = ? WHERE instance_id = ?', (value, self.id))
        db.commit()

    def set_credentials(self, address: str, port: int, password: str):
        # Check whether host and port are valid
        rcon = RconConnection(address, port, password)
        rcon._sock.close()

        cur.execute(f'UPDATE instances SET address = ? WHERE instance_id = ?', (address, self.id))
        cur.execute(f'UPDATE instances SET port = ? WHERE instance_id = ?', (port, self.id))
        cur.execute(f'UPDATE instances SET password = ? WHERE instance_id = ?', (password, self.id))
        db.commit()
        self.address = address
        self.port = port
        self.password = password
    
    def set_owner_id(self, value):
        self._set_db_value("owner_id", value)
        self.owner_id = value
    def set_game(self, value):
        self._set_db_value("game", value)
        self.game = value
    def set_default_perms(self, value):
        self._set_db_value("default_perms", value)
        self.default_perms = value

    def store_config(self):
        cur.execute('UPDATE config SET guild_id = ?, chat_trigger_words = ?, chat_trigger_channel_id = ?, chat_trigger_mentions = ?, chat_log_channel_id = ? WHERE instance_id = ?', tuple( [val for val in self.config.values()] + [self.id] ))
        db.commit()

def _insert_config_row(instance_id: int):
    cur.execute("INSERT INTO config VALUES (?,?,?,?,?,?)", (instance_id, 0, "!admin", 0, "", 0))
    db.commit()
    cur.execute("SELECT * FROM config WHERE instance_id = ?", (instance_id,))
    return cur.fetchone()

class UnknownInstanceError(commands.BadArgument):
    pass