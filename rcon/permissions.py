import sqlite3
from discord.ext import commands

"""
Permissions are stored as an integer. These can be converted to bits.
Each bit represents a permission. Below is a list of all permissions and their int.
If you sum the ints of the permissions you want to assign you get the permission integer.

1       - public        r!server, r!servers, r!map
2       - players       r!players, r!player, r!squad
4       - changemap     r!set_next_map, r!change_map, r!end_match
8       - cheat         r!slomo
16      - message       r!broadcast, r!warn
32      - logs          r!logs, r!chat
64      - password      r!password
128     - teamchange    r!switch_player, r!switch_squad
256     - kick          r!kick, r!punish,
512     - disband       r!disband_squad, r!demote_commander
1028    - ban           r!ban
2048    - config        r!set_max_player_limit, r!maprotation
4069    - execute       r!execute
8192    - manage        r!alerts, r!logging
16384   - creds         r!inst creds
32768   - instance      r!inst connect, r!inst disconnect, r!config, r!perms
"""

class Permissions:
    __perms__ = ['public', 'players', 'changemap', 'cheat', 'message',
    'logs', 'password', 'teamchange', 'kick', 'disband', 'ban', 'config',
    'execute', 'manage', 'creds', 'instance']

    __max__ = int(len(__perms__)*'1', 2)

    def __init__(self, **permissions):
        for perm in self.__perms__:
            self.__setattr__(perm, bool(permissions.get(perm, False)))

    @classmethod
    def from_int(cls, _int):
        perms_bin = format(_int, 'b').zfill(len(cls.__perms__))[::-1]
        perms_dict = {perm: bool(int(perms_bin[i])) for i, perm in enumerate(cls.__perms__)}
        return cls(**perms_dict)

    def __int__(self):
        perms_bin = ''.join([str(int(self.__getattribute__(perm))) for perm in self.__perms__][::-1])
        return int(perms_bin, 2)

    def __str__(self):
        perms_str = ", ".join([perm for perm, val in self.to_dict().items() if val])
        return perms_str if perms_str else "None"

    def __add__(self, other):
        if isinstance(other, Permissions):
            other = other.to_dict()
        return Permissions(**{**self.to_dict(), **{perm: True for perm, val in other.items() if val}})
    def __sub__(self, other):
        if isinstance(other, Permissions):
            other = other.to_dict()
        return Permissions(**{**self.to_dict(), **{perm: False for perm, val in other.items() if val}})

    def to_dict(self):
        return {perm: self.__getattribute__(perm) for perm in self.__perms__}

    def has_perms(self, **perms):
        return all([self.__getattribute__(perm) == val for perm, val in perms.items() if perm in self.__perms__])

db = sqlite3.connect('instances.db')
cur = db.cursor()

def get_instances_for_user(user, guild_id: int = None):
    """
    Get a dict of instances this user has permissions for
    """

    instances = dict()
    ids = [*[role.id for role in user.roles], user.id]

    if guild_id:
        cur.execute('SELECT instance_id, default_perms FROM instances WHERE instance_id IN (SELECT instance_id FROM config WHERE guild_id = ?) AND default_perms > 0 ORDER BY instance_id', (guild_id,))
        res = cur.fetchall()
        for instance_id, perms in res:
            instances[instance_id] = perms
    
    cur.execute(f'SELECT user_id, instance_id, perms FROM permissions WHERE ({" OR ".join(["user_id = ?"]*len(ids))}) AND perms > 0 ORDER BY instance_id', ids)
    res = cur.fetchall()
    res = [t for x in ids for t in res if t[0] == x] # Sort by order of "ids"
    for user_id, instance_id, perms in res:
        instances[instance_id] = perms

    cur.execute('SELECT instance_id FROM instances WHERE owner_id = ? ORDER BY instance_id', (user.id,))
    res = [(row[0], Permissions.__max__) for row in cur.fetchall()]
    for instance_id, perms in res:
        instances[instance_id] = perms

    return instances

def get_perms(user, guild_id: int, instance_id: int):
    for _id, perms in get_instances_for_user(user, guild_id).items():
        if _id == instance_id:
            return Permissions.from_int(perms)

def set_perms(user_id: int, instance_id: int, perms: int, perms_type: str = 'user'):
    # Check if object already has perms set for this instance
    cur.execute('SELECT * FROM permissions WHERE user_id = ? AND instance_id = ?', (user_id, instance_id))
    
    # Object already has perms set for this instance
    if cur.fetchone():
        cur.execute('UPDATE permissions SET perms = ? WHERE user_id = ? AND instance_id = ?', (perms, user_id, instance_id))
        db.commit()
    
    # Object doesn't have any perms set for this instance yet
    else:
        cur.execute('INSERT INTO permissions VALUES (?,?,?,?)', (instance_id, user_id, perms, perms_type))
        db.commit()
def reset_perms(user_id: int, instance_id: int):
    cur.execute('DELETE FROM permissions WHERE user_id = ? AND instance_id = ?', (user_id, instance_id))
    db.commit()

def get_guild_perms(instance_id: int, guild_id: int):
    cur.execute('SELECT default_perms FROM instances WHERE instance_id = ? AND instance_id IN (SELECT instance_id FROM config WHERE guild_id = ?) LIMIT 1', (instance_id, guild_id,))
    res = cur.fetchone()
    if not res: return None
    else: return Permissions.from_int(res[0])
def get_perms_for_instance(instance_id: int, guild_id: int):
    cur.execute('SELECT user_id, perms, perms_type FROM permissions WHERE instance_id = ?', (instance_id,))
    res = cur.fetchall()

    mapping = dict(default=get_guild_perms(instance_id, guild_id), users=dict(), roles=dict())
    for (_id, perms, perms_type) in res:
        perms = Permissions.from_int(perms)
        if perms_type == 'user': mapping['users'][_id] = perms
        elif perms_type == 'role': mapping['roles'][_id] = perms

    return mapping

def get_perms_entry(instance_id: int, object_id: int):
    cur.execute('SELECT perms FROM permissions WHERE instance_id = ? AND user_id = ?', (instance_id, object_id,))
    res = cur.fetchone()
    if res: return Permissions.from_int(res[0])

# Command predicate
def check_perms(**perms):
    async def predicate(ctx):
        _perms = ctx.bot.cache.perms(ctx.author, ctx.guild.id)
        if not _perms.has_perms(**perms):
            instance_id = ctx.bot.cache._get_selected_instance(ctx.author)
            if instance_id == -1:
                await ctx.send(":no_entry_sign: You don't have access to any instances yet!")
            else:
                await ctx.send(":no_entry_sign: You don't have the required permissions to execute this command!")
            return False
        else:
            return True
    return commands.check(predicate)


if __name__ == '__main__':
    pass
