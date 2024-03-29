import re
from datetime import datetime, timedelta
from utils import get_player_input_type
import difflib
import os
from pathlib import Path

import logging

import discord
from discord.ext.commands import BadArgument

from rcon import instances, logs, permissions
from rcon.commands import Rcon
from rcon.connection import RconAuthError
from rcon.query import SourceQuery
from rcon.map_rotation import MapRotation, Map

DETACHMENT_PLAYER_LIMITS = {
    "Command": 2,
    "Infantry": 10,
    "French Infantry": 10,
    "HMG Det": 2,
    "Recon Det": 2,
    "Artillery": 3,
    "Engineers": 3
}

SHORT_TEAM_NAMES = {
    "German Empire": "GER",
    "Imperial German Army": "GER",
    "Jäger-Battalion": "JAG",
    "Jäger-Battalion, Army Detachment Gaede": "JAG",
    "French Republic": "FR",
    "French Army": "FR",
    "Chasseurs Alpins": "CHA",
    "American Expeditionary Force": "AEF",
    "British Expeditionary Force": "BEF",
    "369th Infantry Division": "HHF",
    "Canadian Expeditionary Force": "CEF",

    "British Army": "UK",
    "Canadian Army": "CAF",
    "Middle Eastern Alliance": "MEA",
    "Russian Ground Forces": "RU",
    "United States Army": "US",
    "Insurgent Forces": "INS",
    "Irregular Militia Forces": "MIL"
}

DIVISION_FACTIONS = {
    "US 504th Parachute Infantry Regiment": "United States Army",
    "US 37th Armor Regiment": "United States Army",
    "US 1st Infantry Division": "United States Army",
    "US 149th Brigade, Kentucky Army National Guard": "United States Army",
    "US 1st Cavalry Regiment": "United States Army",
    "US 2nd Cavalry Regiment": "United States Army",

    "UK 2nd Battalion Parachute Regiment": "British Army",
    "UK Queen's Royal Hussars": "British Army",
    "UK 3rd Division": "British Army",
    "UK 1st Battalion, Grenadier Guards": "British Army",
    "UK 1st Battalion Yorkshire Regiment": "British Army",
    "UK 3 Battalion The Rifles": "British Army",
    
    "CAF 3rd Battalion Royal Canadian Regiment": "Canadian Armed Forces",
    "CAF Lord Strathcona's Horse Regiment": "Canadian Armed Forces",
    "CAF 1 Canadian Mechanized Brigade Group": "Canadian Armed Forces",
    "CAF 3rd Battallion PPCLI": "Canadian Armed Forces",
    "CAF Royal Newfoundland Regiment": "Canadian Armed Forces",
    "CAF 1st Battalion Royal 22e Régiment": "Canadian Armed Forces",
    "CAF Royal Westminster Regiment": "Canadian Armed Forces",
    "CAF Canadian Combat Support Brigade": "Canadian Armed Forces",
    
    "MEA 91st Air Assault Battalion": "Middle Eastern Alliance",
    "MEA 60th Prince Assur Armored Brigade": "Middle Eastern Alliance",
    "MEA 1st Battalion, Legion of Babylon": "Middle Eastern Alliance",
    "MEA 4th Border Guards Group": "Middle Eastern Alliance",
    "MEA 3rd King Qadesh Mechanized Infantry Brigade": "Middle Eastern Alliance",
    "MEA 83rd Prince Zaid Motorized Infantry Brigade": "Middle Eastern Alliance",
    
    "Local Insurgent Cell": "Insurgent Forces",
    "Insurgent Homeland Freedom Fighters": "Insurgent Forces",

    "Local Militia Group": "Irregular Militia Forces",
    "The Peoples' Front Militia": "Irregular Militia Forces"
}

DIVISION_TYPES = {
    "US 504th Parachute Infantry Regiment": "Air Assault",
    "US 37th Armor Regiment": "Armored",
    "US 1st Infantry Division": "Combined Arms",
    "US 149th Brigade, Kentucky Army National Guard": "Light Infantry",
    "US 1st Cavalry Regiment": "Mechanized",
    "US 2nd Cavalry Regiment": "Motorized",

    "UK 2nd Battalion Parachute Regiment": "Air Assault",
    "UK Queen's Royal Hussars": "Armored",
    "UK 3rd Division": "Combined Arms",
    "UK 1st Battalion, Grenadier Guards": "Light Infantry",
    "UK 1st Battalion Yorkshire Regiment": "Mechanized",
    "UK 3 Battalion The Rifles": "Motorized",
    
    "CAF 3rd Battalion Royal Canadian Regiment": "Air Assault",
    "CAF Lord Strathcona's Horse Regiment": "Armored",
    "CAF 1 Canadian Mechanized Brigade Group": "Combined Arms",
    "CAF 3rd Battallion PPCLI": "Light Infantry",
    "CAF Royal Newfoundland Regiment": "Light Infantry",
    "CAF 1st Battalion Royal 22e Régiment": "Mechanized",
    "CAF Royal Westminster Regiment": "Motorized",
    "CAF Canadian Combat Support Brigade": "Support",

    "RU 108th Guards Airborne Kuban Cossack Regiment": "Air Assault",
    "RU 6th Separate Czestochowa Tank Brigade": "Armored",
    "RU 49th Combined Arms Army": "Combined Arms",
    "RU 205th Detached Mechanized Cossacks Brigade": "Light Infantry",
    "RU 205th Separate Cossacks Mechanized Rifle Brigade": "Mechanized",
    "RU 247th Guards Air Assault Caucasus Cossacks Regiment": "Motorized",
    
    "MEA 91st Air Assault Battalion": "Air Assault",
    "MEA 60th Prince Assur Armored Brigade": "Armored",
    "MEA 1st Battalion, Legion of Babylon": "Combined Arms",
    "MEA 4th Border Guards Group": "Light Infantry",
    "MEA 3rd King Qadesh Mechanized Infantry Brigade": "Mechanized",
    "MEA 83rd Prince Zaid Motorized Infantry Brigade": "Motorized",
    
    "Local Insurgent Cell": "Combined Arms",
    "Insurgent Homeland Freedom Fighters": "Light Infantry",

    "Local Militia Group": "Combined Arms",
    "The Peoples' Front Militia": "Light Infantry"
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
    def _get_guild_id(self, guild):
        if isinstance(guild, discord.Guild):
            guild = guild.id
        elif not isinstance(guild, int):
            raise BadArgument("guild needs to be either int or discord.Guild")
        return guild

    def _get_selected_instance(self, user, guild_id=None):
        if user.id not in self.selected_instance:
            self.selected_instance[user.id] = -1

        try:
            instances.Instance(self.selected_instance[user.id])
        except:
            try: self.selected_instance[user.id] = instances.get_available_instances(user, guild_id)[0][0].id
            except: self.selected_instance[user.id] = -1

        return self.selected_instance[user.id]

    def perms(self, user, guild=None):
        guild_id = self._get_guild_id(guild)
        selected_instance = self._get_selected_instance(user, guild_id)
        perms = instances.get_perms(user, guild_id, selected_instance)
        return perms

    def instance(self, user, guild=None, by_inst_id=False):
        if by_inst_id:
            instance_id = user
        else:
            guild = self._get_guild_id(guild)
            instance_id = self._get_selected_instance(user, guild)

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

class ServerInstance(MapRotation):
    def __init__(self, instance_id, rcon):
        logging.info('Registring new instance with ID %s', instance_id)
        
        self.id = instance_id
        self.rcon = rcon

        self.map_rotation = None
        self.current_map = None
        self.next_map = None
        self.last_map_change = None
        self.is_transitioning = False

        self.players = []
        self.ids = []

        self.team1 = None
        self.team2 = None

        self.update()

        path = Path(f'rotations/{str(self.id)}.json')
        if os.path.exists(path) and instances.Instance(self.id).uses_custom_rotation:
            try: self.import_rotation(fp=path)
            except: pass

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
            logging.info('Inst %s: Updating...', self.id)
            self._parse_maps()
            if not self.is_transitioning:
                self._parse_players()
                self._parse_squads()
                if self.map_rotation and self.next_map:
                    self.validate_next_map()
            else:
                logging.info('Inst %s: Map is transitioning', self.id)
            self.last_updated = datetime.now()
        except RconAuthError as e:
            if (datetime.now() - timedelta(minutes=30)) > self.last_updated:
                logging.error('Inst %s: Failed to connect for 5 minutes, disconnecting...', self.id)
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
        ID: 4 | SteamID: 76561199023367826 | Name: (WTH) Abusify | Team ID: 2 | Squad ID: 1 | Is Leader: True | Role: USA_Marksman_01

        ----- Recently Disconnected Players [Max of 15] -----
        ID: 10 | SteamID: 76561198062628191 | Since Disconnect: 02m.30s | Name: [2.FJg]Gh0st

        Note that Team ID can be N/A during map change
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
                    re_res = re.search(r'ID: (\d+) \| SteamID: (\d{17}|N/A) \| Name: (.*) \| Team ID: (\d+|N/A) \| Squad ID: (\d+|N/A)( \| Is Leader: (True|False) | Role: (.*))?', line).groups()
                except: # Unable to fetch all data, skip this line
                    logging.error('Inst %s: Could not parse player line: %s', self.id, line)
                    pass
                else:
                    if re_res[1] == "N/A":
                        continue
                    data = {}
                    data['player_id'] = int(re_res[0])
                    data['steam_id'] = int(re_res[1])
                    data['name'] = str(re_res[2])
                    try: data['team_id'] = int(re_res[3].strip())
                    except: data['team_id'] = 0
                    try: data['squad_id'] = int(re_res[4].strip())
                    except: data['squad_id'] = -1

                    if re_res[5]: # Is Squad v2.12
                        data['role'] = re_res[7]

                    player = OnlinePlayer(**data)
                    players.append(player)
        ids = [player.steam_id for player in players]

        """
        Now that we've added all online players to a nice dict, lets compare them with what's cached.
        Let's start off by getting a list of steam64id's that connected or disconnected. Then, we
        update what's cached and do whatever else we like with this information.
        """
        
        connected = [player for player in players if int(player) not in self.ids]
        disconnected = [player for player in self.players if int(player) not in ids]
        if connected: logging.info('Inst %s: Connected: %s', self.id, ', '.join([player.name for player in connected]))
        if connected: logging.info('Inst %s: Disonnected: %s', self.id, ', '.join([player.name for player in disconnected]))

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
        current_map = self.rcon.show_current_map()
        next_map = self.rcon.show_next_map()
        
        """
        Old response format example:
        'Current map is Logar Valley Skirmish v1, Next map is Gorodok AAS v2'

        New response format example:
        'Current level is Yehorivka, layer is Yehorivka RAAS v3'
        'Next level is Kohat, layer is Kohat RAAS v4'
        """

        try:
            res = re.match(r"Current map is (.+), Next map is (.+)", next_map).groups()
        except:
            # Try to read the current map
            try: current_map = Map(re.match(r"Current level is (.+), layer is (.+)", current_map).group(2))
            except: current_map = self.current_map
            # Try to read the upcoming map
            try: next_map = Map(re.match(r"Next level is (.+), layer is (.+)", next_map).group(2))
            except: next_map = self.next_map
        else:
            current_map = Map(res[0])
            next_map = Map(res[1])

        logging.info('Inst %s: Current map is %s, next map is %s', self.id, current_map, next_map)

        self.is_transitioning = False
        if current_map == "/Game/Maps/TransitionMap":
            self.is_transitioning = True
            return

        if self.current_map and current_map != self.current_map: # Map has changed
            self.is_transitioning = True
            message = f"Map changed from {self.current_map} to {current_map}."
            if self.last_map_change:
                message += f" The match lasted {str(int((datetime.now() - self.last_map_change).total_seconds() / 60))} minutes."
            else:
                message += " Match duration is unknown."
            logging.info('Inst %s: %s', self.id, message)
            logs.ServerLogs(self.id).add('match', message)
            self.last_map_change = datetime.now()

            if self.map_rotation:
                try:
                    next_map = self.map_changed(current_map)
                    logging.info('Inst %s: MAPROT: Next map will be %s', self.id, next_map)
                except Exception as e:
                    logging.error('Inst %s: MAPROT: An error was raised while looking for next map: %s: %s', self.id, e.__class__.__name__, e)
        
        if self.current_map != current_map: self.current_map = current_map
        if self.next_map != next_map: self.next_map = next_map
        
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

        Or possibly:

        ID: 1 | Name: Squad 1 | Size: 9 | Locked: False | Creator Name: HunterChillz | Creator Steam ID: 76561199130883877


        This is what the default squad names look like:

        Command, Infantry, HEAVY MG, RECON, Artillery
        """

        lines = res.split("\n")
        team_id = None

        for line in lines:
            if line.startswith("Team ID"):
                try: re_res = re.search(r'Team ID: ([12]) \((.*)\)', line).groups()
                except: continue
                team_id = int(re_res[0])
                team_faction = str(re_res[1])
                # TODO: Currently the team info gets replaced without comparing old to new.
                if team_id == 1: self.team1 = Team(team_id, team_faction)
                elif team_id == 2: self.team2 = Team(team_id, team_faction)
                
            elif line.startswith("ID") and team_id:
                try:
                    re_res = re.search(r'ID: (\d*) \| Name: (.*) \| Size: (\d*) \| Locked: (True|False)( \| Creator Name: (.*) \| Creator Steam ID: (\d{17}))?', line).groups()
                except:
                    logging.error('Inst %s: Failed to parse squad line: %s', self.id, line)
                else:
                    data = dict(
                        squad_id = int(re_res[0]),
                        name = str(re_res[1]),
                        #size = int(re_res[2]),
                        player_ids = [player.steam_id for player in self.select(team_id=team_id, squad_id=int(re_res[0]))],
                        locked = True if re_res[3] == "True" else False,
                        creator_name = None,
                        creator_steam_id = None,
                    )
                    if re_res[4]:
                        data['creator_name'] = str(re_res[5])
                        data['creator_steam_id'] = int(re_res[6])

                    if team_id == 1: self.team1.set_squad(**data)
                    elif team_id == 2: self.team2.set_squad(**data)
            
        self.team1.unassigned = [player.steam_id for player in self.select(team_id=1, squad_id=-1)]
        self.team2.unassigned = [player.steam_id for player in self.select(team_id=2, squad_id=-1)]

    def _get_player_score(self):
        # Need to know the query port...
        pass

    def disconnect_player(self, player):
        if not isinstance(player, OnlinePlayer):
            player = self.get_player(player)
        if not player: return
        self.players.remove(player)
        self.ids.remove(player.steam_id)
        logs.ServerLogs(self.id).add('joins', f'{player.name} was disconnected after {str(player.online_time())} minutes')

class OnlinePlayer():
    def __init__(self, steam_id: int, name: str, team_id: int, squad_id: int, player_id: int, online_since: datetime = None, score: int = 0, role: str = "Unknown"):
        self.steam_id = steam_id
        self.name = name
        self.team_id = team_id
        self.squad_id = squad_id
        self.player_id = player_id
        self.online_since = online_since if online_since else datetime.now()
        self.score = score
        self.role = role

    def update(self, team_id: int = None, squad_id: int = None, score: int = None, role: str = None):
        if team_id is not None: self.team_id = team_id
        if squad_id is not None: self.squad_id = squad_id
        if score is not None: self.score = score
        if role is not None: self.role = role
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
        self.faction = DIVISION_FACTIONS.get(faction, faction)
        self.faction_short = SHORT_TEAM_NAMES.get(self.faction, self.faction)
        self.division = faction if faction != self.faction else None
        self.division_type = DIVISION_TYPES.get(self.division, None)
        self.squads = []
        self.unassigned = []

    def __len__(self):
        return sum([len(squad) for squad in self.squads]) + len(self.unassigned)

    def __str__(self):
        if self.division_type:
            return f"{self.faction} ({self.division_type})"
        elif self.division:
            return self.division
        else:
            return self.faction

    def set_squad(self, squad_id: int, name: str, player_ids: list, locked: bool, creator_name: str, creator_steam_id: int):
        squad = None
        for i, squad in enumerate(self.squads):
            if squad.id == squad_id:
                break
            squad = None
        
        if squad: # There is a squad with this ID
            squad = squad[0]
            if squad.name != name or squad.creator_steam_id != creator_steam_id: # The previous squad was replaced
                self.squads[i] = Squad(squad_id, name, player_ids, locked, creator_name, creator_steam_id)
            else: # This squad already existed before
                self.squads[i].update(player_ids, locked)
        else: # This is a new squad
            squad = Squad(squad_id, name, player_ids, locked, creator_name, creator_steam_id)
            self.squads.append(squad)

class Squad():
    def __init__(self, id: int, name: str, player_ids: list, locked: bool, creator_name: str = None, creator_steam_id: str = None):
        self.id = id
        self.name = name
        self.player_ids = player_ids
        self.locked = locked
        self.creator = creator_steam_id if creator_steam_id else self.player_ids[0]
        self.creator_name = creator_name
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
