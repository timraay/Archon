from rcon.connection import RconConnection, RconError
from ast import literal_eval

class Rcon(RconConnection):

    def _res_to_str(self, res):
        res = literal_eval(res)
        #print(len(res))
        if not res: # An empty list was received
            res = "Empty response received"
        else:
            res = b"".join(res).strip(b'\x00\x01')
            #print(res)
            res = res.decode('utf-8', errors='replace').replace('�', '')
            if res.startswith("ERROR: "):
                res = res.replace("ERROR: ", "")
                raise RconCommandError(res)
        return res

    # PLAYERS
    def list_players(self):
        res = self.exec_command(f"ListPlayers")
        res = self._res_to_str(res)
        return res
    def list_disconnected_players(self):
        res = self.exec_command(f"AdminListDisconnectedPlayers")
        res = self._res_to_str(res)
        return res

    # MODERATION
    def warn(self, name_or_steam64id: str, reason: str):
        res = self.exec_command(f"AdminWarn {name_or_steam64id} {reason}")
        res = self._res_to_str(res)
        return res
    def warn_by_id(self, player_id: str, reason: str):
        res = self.exec_command(f"AdminWarnById {player_id} {reason}")
        res = self._res_to_str(res)
        return res
    def kick(self, name_or_steam64id: str, reason: str):
        res = self.exec_command(f"AdminKick {name_or_steam64id} {reason}")
        res = self._res_to_str(res)
        return res
    def kick_by_id(self, player_id: str, reason: str):
        res = self.exec_command(f"AdminKickById {player_id} {reason}")
        res = self._res_to_str(res)
        return res
    def ban(self, name_or_steam64id: str, length: str, reason: str):
        res = self.exec_command(f"AdminBan {name_or_steam64id} {length} {reason}")
        res = self._res_to_str(res)
        return res
    def ban_by_id(self, player_id: str, length: str, reason: str):
        res = self.exec_command(f"AdminBanById {player_id} {length} {reason}")
        res = self._res_to_str(res)
        return res
    def broadcast(self, message: str):
        res = self.exec_command(f"AdminBroadcast {message}")
        res = self._res_to_str(res)
        return res

    # TEAMS
    def demote_commander(self, name_or_steam64id: str):
        res = self.exec_command(f"AdminDemoteCommander {name_or_steam64id}")
        res = self._res_to_str(res)
        return res
    def demote_commander_by_id(self, player_id: str):
        res = self.exec_command(f"AdminDemoteCommanderById {player_id}")
        res = self._res_to_str(res)
        return res
    def remove_from_squad(self, name_or_steam64id: str):
        res = self.exec_command(f"AdminRemovePlayerFromSquad {name_or_steam64id}")
        res = self._res_to_str(res)
        return res
    def remove_from_squad_by_id(self, player_id: str):
        res = self.exec_command(f"AdminRemovePlayerFromSquadById {player_id}")
        res = self._res_to_str(res)
        return res
    def change_team(self, name_or_steam64id: str):
        res = self.exec_command(f"AdminForceTeamChange {name_or_steam64id}")
        res = self._res_to_str(res)
        return res
    def change_team_by_id(self, player_id: str):
        res = self.exec_command(f"AdminForceTeamChangeById {player_id}")
        res = self._res_to_str(res)
        return res
    def disband_squad(self, team_1_or_2: str, squad_index: str):
        res = self.exec_command(f"AdminDisbandSquad {team_1_or_2} {squad_index}")
        res = self._res_to_str(res)
        return res
    def list_squads(self):
        res = self.exec_command(f"ListSquads")
        res = self._res_to_str(res)
        return res

    # MATCHES
    def end_match(self):
        res = self.exec_command(f"AdminEndMatch")
        res = self._res_to_str(res)
        return res
    def restart_match(self):
        res = self.exec_command(f"AdminRestartMatch")
        res = self._res_to_str(res)
        return res
    def switch_to_map(self, map_name: str):
        res = self.exec_command(f"AdminChangeMap {map_name}")
        res = self._res_to_str(res)
        return res
    def set_next_map(self, map_name: str):
        res = self.exec_command(f"AdminSetNextMap {map_name}")
        res = self._res_to_str(res)
        return res
    def show_maps(self):
        res = self.exec_command(f"ShowNextMap")
        res = self._res_to_str(res)
        return res

    # ADMINISTRATION
    def set_max_player_limit(self, limit: str):
        res = self.exec_command(f"AdminSetMaxNumPlayers")
        res = self._res_to_str(res)
        return res
    def change_password(self, password: str):
        res = self.exec_command(f"AdminSetServerPassword {password}")
        res = self._res_to_str(res)
        return res


class RconCommandError(RconError):
    """ Raised when the server returns an error as response """
    pass