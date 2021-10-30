from rcon.connection import RconConnection, RconError
from ast import literal_eval

import logging

class Rcon(RconConnection):

    def _res_to_str(self, res):
        res = literal_eval(res)
        #print(len(res))
        if not res: # An empty list was received
            logging.warning('Empty response received from %s:%s', self.server, self.port)
            res = "Empty response received"
        else:
            res = b"".join(res).strip(b'\x00\x01')
            res = res.decode('utf-8', errors='replace').replace('�', '')
            if res.startswith("ERROR: "):
                res = res.replace("ERROR: ", "")
                logging.error('%s:%s returned error: %s', self.server, self.port, res)
                raise RconCommandError(res)
            else:
                logging.info('%s:%s returned response: %s', self.server, self.port, res)
        return res

    # PLAYERS
    async def list_players(self):
        res = await self.exec_command(f"ListPlayers")
        res = self._res_to_str(res)
        return res
    async def list_disconnected_players(self):
        res = await self.exec_command(f"AdminListDisconnectedPlayers")
        res = self._res_to_str(res)
        return res

    # MODERATION
    async def warn(self, name_or_steam64id: str, reason: str):
        res = await self.exec_command(f"AdminWarn {name_or_steam64id} {reason}")
        res = self._res_to_str(res)
        return res
    async def warn_by_id(self, player_id: str, reason: str):
        res = await self.exec_command(f"AdminWarnById {player_id} {reason}")
        res = self._res_to_str(res)
        return res
    async def kick(self, name_or_steam64id: str, reason: str):
        res = await self.exec_command(f"AdminKick {name_or_steam64id} {reason}")
        res = self._res_to_str(res)
        return res
    async def kick_by_id(self, player_id: str, reason: str):
        res = await self.exec_command(f"AdminKickById {player_id} {reason}")
        res = self._res_to_str(res)
        return res
    async def ban(self, name_or_steam64id: str, length: str, reason: str):
        res = await self.exec_command(f"AdminBan {name_or_steam64id} {length} {reason}")
        res = self._res_to_str(res)
        return res
    async def ban_by_id(self, player_id: str, length: str, reason: str):
        res = await self.exec_command(f"AdminBanById {player_id} {length} {reason}")
        res = self._res_to_str(res)
        return res
    async def broadcast(self, message: str):
        res = await self.exec_command(f"AdminBroadcast {message}")
        res = self._res_to_str(res)
        return res

    # TEAMS
    async def demote_commander(self, name_or_steam64id: str):
        res = await self.exec_command(f"AdminDemoteCommander {name_or_steam64id}")
        res = self._res_to_str(res)
        return res
    async def demote_commander_by_id(self, player_id: str):
        res = await self.exec_command(f"AdminDemoteCommanderById {player_id}")
        res = self._res_to_str(res)
        return res
    async def remove_from_squad(self, name_or_steam64id: str):
        res = await self.exec_command(f"AdminRemovePlayerFromSquad {name_or_steam64id}")
        res = self._res_to_str(res)
        return res
    async def remove_from_squad_by_id(self, player_id: str):
        res = await self.exec_command(f"AdminRemovePlayerFromSquadById {player_id}")
        res = self._res_to_str(res)
        return res
    async def change_team(self, name_or_steam64id: str):
        res = await self.exec_command(f"AdminForceTeamChange {name_or_steam64id}")
        res = self._res_to_str(res)
        return res
    async def change_team_by_id(self, player_id: str):
        res = await self.exec_command(f"AdminForceTeamChangeById {player_id}")
        res = self._res_to_str(res)
        return res
    async def disband_squad(self, team_1_or_2: str, squad_index: str):
        res = await self.exec_command(f"AdminDisbandSquad {team_1_or_2} {squad_index}")
        res = self._res_to_str(res)
        return res
    async def list_squads(self):
        res = await self.exec_command(f"ListSquads")
        res = self._res_to_str(res)
        return res

    # MATCHES
    async def end_match(self):
        res = await self.exec_command(f"AdminEndMatch")
        res = self._res_to_str(res)
        return res
    async def restart_match(self):
        res = await self.exec_command(f"AdminRestartMatch")
        res = self._res_to_str(res)
        return res
    async def switch_to_map(self, map_name: str):
        res = await self.exec_command(f"AdminChangeMap {map_name}")
        res = self._res_to_str(res)
        return res
    async def set_next_map(self, map_name: str):
        res = await self.exec_command(f"AdminSetNextMap {map_name}")
        res = self._res_to_str(res)
        return res
    async def show_current_map(self):
        res = await self.exec_command(f"ShowCurrentMap")
        res = self._res_to_str(res)
        return res
    async def show_next_map(self):
        res = await self.exec_command(f"ShowNextMap")
        res = self._res_to_str(res)
        return res

    async def set_next_layer(self, layer_name: str):
        res = await self.exec_command(f"AdminSetNextLayer {layer_name}")
        res = self._res_to_str(res)
        return res

    async def change_layer(self, layer_name: str):
        res = await self.exec_command(f"AdminChangeLayer {layer_name}")
        res = self._res_to_str(res)
        return res


    # ADMINISTRATION
    async def set_max_player_limit(self, limit: str):
        res = await self.exec_command(f"AdminSetMaxNumPlayers")
        res = self._res_to_str(res)
        return res
    async def change_password(self, password: str = ""):
        res = await self.exec_command(f"AdminSetServerPassword {password}")
        res = self._res_to_str(res)
        return res
    async def set_clockspeed(self, percentage: float):
        res = await self.exec_command(f"AdminSlomo {str(percentage)}")
        res = self._res_to_str(res)
        return res


class RconCommandError(RconError):
    """ Raised when the server returns an error as response """
    pass
