import re
from datetime import datetime
from utils import get_player_input_type
import difflib

import discord
from discord.ext.commands import BadArgument

from rcon import instances, logs
from rcon.commands import Rcon
from rcon.connection import RconAuthError

SQUAD_PLAYER_LIMITS = {
    "Command": 2,
    "Infantry": 10,
    "Heavy MG": 2,
    "Recon": 2,
    "Artillery": 3
}

SHORT_TEAM_NAMES = {
    "German Empire": "GER",
    "French Republic": "FR",
    "American Expeditionary Force": "AEF",

    "British Army": "BA",
    "Canadian Army": "CA",
    "Middle Eastern Alliance": "MEA",
    "Russian Ground Forces": "RGF",
    "United States Army": "USA",
    "Insurgent Forces": "IF",
    "Irregular Militia Forces": "IM"
}


class Cache():
    def __init__(self):
        self.instances = {}
        for instance in instances.get_instances():
            self._connect_instance(instance)

        self.selected_instance = {}

    def _connect_instance(self, instance, return_exception=False):
        try:
            rcon = Rcon(instance.address, instance.port, instance.password, instance_id=instance.id)
        except Exception as e:
            self.instances[instance.id] = None
            if return_exception: return e 
        else:
            self.instances[instance.id] = ServerInstance(instance.id, rcon)
        return self.instances[instance.id]

    def _get_user_id(self, user):
        if isinstance(user, (discord.User, discord.Member)):
            user = user.id
        elif not isinstance(user, int):
            raise BadArgument("user needs to be either int or discord.User")
        return user

    def _get_selected_instance(self, user, guild_id=None):
        user = self._get_user_id(user)

        if user not in self.selected_instance:
            self.selected_instance[user] = -1

        try:
            instances.Instance(self.selected_instance[user])
        except:
            try: self.selected_instance[user] = instances.get_available_instances(user, guild_id)[0][0].id
            except: self.selected_instance[user] = -1

        return self.selected_instance[user]

    def perms(self, user, guild_id):
        selected_instance = self._get_selected_instance(user, guild_id)
        perms = instances.get_perms(user, guild_id, selected_instance)
        return perms

    def instance(self, user, by_inst_id=False):
        guild_id = None
        if by_inst_id:
            instance_id = user
        else:
            if isinstance(user, discord.Member):
                guild_id = user.guild.id
            user = self._get_user_id(user)
            instance_id = self._get_selected_instance(user, guild_id)

        if instance_id in self.instances:
            inst = self.instances[instance_id]
            if inst == None:
                raise CacheNotFound("No cached data found for instance ID %s" % instance_id)
            elif inst.rcon._sock == None:
                inst = None
                raise CacheNotFound("Socket disconnected, please reconnect using r!inst connect")
            return inst
        else:
            raise BadArgument("No instance cached with ID %s" % instance_id)

    def update_all(self):
        for i, inst in self.instances:
            inst.update()
            self.instances[i] = inst

    def delete_instance(self, instance_id):
        if instance_id in self.instances:
            del self.instances[instance_id]
        instances.Instance(instance_id).delete()

class ServerInstance():
    def __init__(self, instance_id, rcon):
        self.id = instance_id
        self.rcon = rcon

        self.current_map = None
        self.next_map = None
        self.last_map_change = None
        self.is_transitioning = False

        self.players = []
        self.ids = []

        self.team1 = None
        self.team2 = None
        
        self.update()

    def select(self, steam_id: int = None, name: str = None, team_id: int = None, squad_id: int = None, player_id: int = None, min_online_time: int = None, max_online_time: int = None):
        pool = self.players
        if pool and steam_id != None: pool = [player for player in pool if player.steam_id == steam_id]
        if pool and name != None: pool = [player for player in pool if player.name == name]
        if pool and team_id != None: pool = [player for player in pool if player.team_id == team_id]
        if pool and squad_id != None: pool = [player for player in pool if player.squad_id == squad_id]
        if pool and player_id != None: pool = [player for player in pool if player.player_id == player_id]
        if pool and min_online_time != None: pool = [player for player in pool if player.min_online_time >= player.online_time()]
        if pool and max_online_time != None: pool = [player for player in pool if player.max_online_time <= player.online_time()]
        return pool

    def get_player(self, name_or_id: str, multi=False, related_names=False):
        input_type = get_player_input_type(name_or_id)
        players = self.select(name=str(name_or_id))

        if related_names:
            all_names = [player.name for player in self.players]
            player_names = difflib.get_close_matches(name_or_id, all_names, cutoff=0.6, n=1)
            players = [self.select(name=name)[0] for name in player_names]

        if input_type == "steam64id":
            players = self.select(steam_id=int(name_or_id)) + players
        elif input_type == "squadid":
            players += self.select(player_id=int(name_or_id))

        if multi: return players
        else: 
            player = None
            if players: player = players[0]
            return player

    def update(self):
        try:
            self._parse_maps()
            if not self.is_transitioning:
                self._parse_players()
                self._parse_squads()
            self.last_updated = datetime.now()
        except RconAuthError as e:
            self = None
            raise ConnectionLost("Lost connection to RCON: " + str(e))
        
        return self

    def _parse_players(self):
        res = self.rcon.list_players()

        """
        We need to turn the data given by the server into a more feasible structure.
        This is what the result from the server looks like:

        ----- Active Players -----
        ID: 0 | SteamID: 76561199023367826 | Name: (WTH) Heidegger | Team ID: 1 | Squad ID: N/A
        ID: 4 | SteamID: 76561199023367826 | Name: (WTH) Abusify | Team ID: 2 | Squad ID: 1

        ----- Recently Disconnected Players [Max of 15] -----
        ID: 10 | SteamID: 76561198062628191 | Since Disconnect: 02m.30s | Name: [2.FJg]Gh0st
        """

        players = []
        disconnected = []
        
        lines = res.split("\n")
        for line in lines:
            if not line.strip() or len(line) < 20: continue # Line is empty
            if "----- Active Players -----" in line: continue # Skip this line
            elif "----- Recently Disconnected Players [Max of 15] -----" in line: break # Stop parsing

            else: # Parse line
                try:
                    re_res = re.search(r'ID: (\d+) \| SteamID: (\d{17}) \| Name: (.*) \| Team ID: ([12]) \| Squad ID: ([\w/]*)', line).groups()
                except: # Unable to fetch all data, skip this line
                    pass
                else:
                    data = {}
                    data['id'] = int(re_res[0])
                    data['steam_id'] = int(re_res[1])
                    data['name'] = str(re_res[2])
                    data['team_id'] = int(re_res[3])
                    try:
                        data['squad_id'] = int(re_res[4].strip())
                    except:
                        data['squad_id'] = -1

                    player = OnlinePlayer(data['steam_id'], data['name'], data['team_id'], data['squad_id'], data['id'])
                    players.append(player)
        ids = [player.steam_id for player in players]

        """
        Now that we've added all online players to a nice dict, lets compare them with what's cached.
        Let's start off by getting a list of steam64id's that connected or disconnected. Then, we
        update what's cached and do whatever else we like with this information.
        """
        
        connected = [player for player in players if int(player) not in self.ids]
        disconnected = [player for player in self.players if int(player) not in ids]

        # Update the cache
        for i, player in enumerate(players):
            old_player = self.select(steam_id=player.steam_id)
            if old_player:
                players[i].online_since = old_player[0].online_since
        self.players = players
        self.ids = ids

        # Log players connecting and disconnecting
        messages = []
        for player in connected:
            messages.append(f'{player.name} connected')
        for player in disconnected:
            messages.append(f'{player.name} disconnected after {str(player.online_time())} minutes')
        if messages:
            logs.ServerLogs(self.id).add('joins', messages)

    def _parse_maps(self):
        res = self.rcon.show_maps()
        
        """
        Response format example:
        Current map is Logar Valley Skirmish v1, Next map is Gorodok AAS v2
        """

        # Try to read the current map
        try:
            current_map = re.search(r"Current map is (.+),", res).group(1)
        except:
            current_map = self.current_map
        # Try to read the upcoming map
        try:
            next_map = re.search(r"Next map is (.+)", res).group(1)
        except:
            next_map = self.next_map

        self.is_transitioning = False
        if current_map == "/Game/Maps/TransitionMap":
            self.is_transitioning = True
            current_map = self.current_map

        if self.current_map and current_map != self.current_map: # Map has changed
            self.is_transitioning = True
            time = datetime.now().strftime("%H:%M")
            message = f"Map changed from {self.current_map} to {current_map}."
            if self.last_map_change:
                message += f" The match lasted {str(int((datetime.now() - self.last_map_change).total_seconds() / 60))} minutes."
            else:
                message += " Match duration is unknown."
            logs.ServerLogs(self.id).add('match', message)
            self.last_map_change = datetime.now()
        
        self.current_map = current_map
        self.next_map = next_map
        
    def _parse_squads(self):
        res = self.rcon.list_squads()

        """
        This is what the result from the server looks like:

        ----- Active Squads -----
        Team ID: 1 (French Republic)
        ID: 1 | Name: LOUTRE | Size: 2 | Locked: False
        ID: 2 | Name: Infantry | Size: 5 | Locked: False
        Team ID: 2 (German Empire)
        ID: 1 | Name: Infantry | Size: 6 | Locked: False
        ID: 2 | Name: HEAVY MG | Size: 2 | Locked: False


        This is what the default squad names look like:

        Command, Infantry, HEAVY MG, RECON, Artillery
        """

        lines = res.split("\n")

        for line in lines:
            if line.startswith("Team ID"):
                re_res = re.search(r'Team ID: ([12]) \(([\w\s]*)\)', line).groups()
                team_id = int(re_res[0])
                team_faction = str(re_res[1])
                # TODO: Currently the team info gets replaced without comparing old to new.
                if team_id == 1: self.team1 = Team(team_id, team_faction)
                elif team_id == 2: self.team2 = Team(team_id, team_faction)
                
            elif line.startswith("ID"):
                re_res = re.search(r'ID: (\d*) \| Name: (.*) \| Size: (\d*) \| Locked: (True|False)', line).groups()
                squad_id = int(re_res[0])
                name = str(re_res[1])
                size = int(re_res[2])
                player_ids = [player.steam_id for player in self.select(team_id=team_id, squad_id=squad_id)]
                locked = True if re_res[3] == "True" else False

                if team_id == 1: self.team1.set_squad(squad_id, name, player_ids, locked)
                elif team_id == 2: self.team2.set_squad(squad_id, name, player_ids, locked)
            
        self.team1.unassigned = [player.steam_id for player in self.select(team_id=1, squad_id=-1)]
        self.team2.unassigned = [player.steam_id for player in self.select(team_id=2, squad_id=-1)]

    def disconnect_player(self, player):
        if not isinstance(player, OnlinePlayer):
            player = self.get_player(player)
        if not player: return
        self.players.remove(player)
        self.ids.remove(player.steam_id)
        logs.ServerLogs(self.id).add('joins', f'{player.name} was disconnected after {str(player.online_time())} minutes')

class OnlinePlayer():
    def __init__(self, steam_id: int, name: str, team_id: int, squad_id: int, player_id: int, online_since: datetime = None):
        self.steam_id = steam_id
        self.name = name
        self.team_id = team_id
        self.squad_id = squad_id
        self.player_id = player_id
        self.online_since = online_since if online_since else datetime.now()

    def update(self, team_id: int = None, squad_id: int = None):
        if team_id: self.team_id = team_id
        if squad_id: self.squad_id = squad_id
        return self

    def __str__(self):
        return self.name

    def __int__(self):
        return self.steam_id
    
    def online_time(self):
        return int((datetime.now() - self.online_since).total_seconds() / 60)

class Team():
    def __init__(self, id: int, faction: str):
        self.id = id
        self.faction = faction
        self.faction_short = SHORT_TEAM_NAMES[self.faction] if self.faction in SHORT_TEAM_NAMES else self.faction
        self.squads = []
        self.unassigned = []

    def __len__(self):
        return sum([len(squad) for squad in self.squads]) + len(self.unassigned)

    def set_squad(self, id: int, name: str, player_ids: list, locked: bool):
        squad = None
        for i, squad in enumerate(self.squads):
            if squad.id == id:
                break
            squad = None
        
        if squad: # There is a squad with this ID
            squad = squad[0]
            if squad.name != name: # The previous squad was replaced
                self.squads[i] = Squad(id, name, player_ids, locked)
            else: # This squad already existed before
                self.squads[i].update(player_ids, locked)
        else: # This is a new squad
            squad = Squad(id, name, player_ids, locked)
            self.squads.append(squad)

class Squad():
    def __init__(self, id: int, name: str, player_ids: list, locked: bool):
        self.id = id
        self.name = name
        self.player_ids = player_ids
        self.locked = locked
        """
        self.type = None
        self._possible_types = [key for key in SQUAD_PLAYER_LIMITS.keys()]
        self._update_type()
        """

    def __len__(self):
        return len(self.player_ids)

    """
    def _update_type(self):
        for squad_type in self._possible_types:
            if SQUAD_PLAYER_LIMITS[squad_type] < len(self.player_ids):
                self._possible_types.remove(squad_type)
            elif squad_type.lower() == self.name.lower():
                self.type = squad_type
        if len(self._possible_types) == 1:
            self.type = self._possible_types[0]
        elif not self._possible_types:
            self._possible_types == [key for key in SQUAD_PLAYER_LIMITS.keys()]
    """

    def update(self, player_ids: list, locked: bool = None):
        old_player_ids = self.player_ids

        self.player_ids = player_ids
        """self._update_type()"""

        if locked != None:
            self.locked = bool(locked)

        joined = []
        left = []
        for player in player_ids:
            if player not in old_player_ids:
                joined.append(player)
        for player in old_player_ids:
            if player not in player_ids:
                left.append(player)
        
        return joined, left



class ConnectionLost(Exception):
    """Raised when a RCON connection is lost"""
    pass
class CacheNotFound(Exception):
    """Raised when no cache is found, usually when RCON is disconnected"""
    pass 