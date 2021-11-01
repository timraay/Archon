import aiorcon
from functools import wraps

def catch_game_errors(func):
    """Decorator that catches and raises error responses returned by
    the game server. Works only with coroutines."""
    @wraps(func)
    async def wrap(*args, **kwargs):
        res = await func(*args, **kwargs)
        if res.startswith("ERROR: "):
            res = res.replace("ERROR: ", "")
            raise RconCommandError(res)
        return res
    return wrap


class Rcon(aiorcon.RCON):

    @catch_game_errors
    async def exec_command(self, command):
        return await self(command)

    # PLAYERS
    async def list_players(self):
        return await self.exec_command(f"ListPlayers")

    async def list_disconnected_players(self):
        return await self.exec_command(f"AdminListDisconnectedPlayers")

    # MODERATION
    async def warn(self, name_or_steam64id: str, reason: str):
        return await self.exec_command(f"AdminWarn {name_or_steam64id} {reason}")

    async def warn_by_id(self, player_id: str, reason: str):
        return await self.exec_command(f"AdminWarnById {player_id} {reason}")

    async def kick(self, name_or_steam64id: str, reason: str):
        return await self.exec_command(f"AdminKick {name_or_steam64id} {reason}")

    async def kick_by_id(self, player_id: str, reason: str):
        return await self.exec_command(f"AdminKickById {player_id} {reason}")

    async def ban(self, name_or_steam64id: str, length: str, reason: str):
        return await self.exec_command(f"AdminBan {name_or_steam64id} {length} {reason}")

    async def ban_by_id(self, player_id: str, length: str, reason: str):
        return await self.exec_command(f"AdminBanById {player_id} {length} {reason}")

    async def broadcast(self, message: str):
        return await self.exec_command(f"AdminBroadcast {message}")

    # TEAMS
    async def demote_commander(self, name_or_steam64id: str):
        return await self.exec_command(f"AdminDemoteCommander {name_or_steam64id}")

    async def demote_commander_by_id(self, player_id: str):
        return await self.exec_command(f"AdminDemoteCommanderById {player_id}")

    async def remove_from_squad(self, name_or_steam64id: str):
        return await self.exec_command(f"AdminRemovePlayerFromSquad {name_or_steam64id}")

    async def remove_from_squad_by_id(self, player_id: str):
        return await self.exec_command(f"AdminRemovePlayerFromSquadById {player_id}")

    async def change_team(self, name_or_steam64id: str):
        return await self.exec_command(f"AdminForceTeamChange {name_or_steam64id}")

    async def change_team_by_id(self, player_id: str):
        return await self.exec_command(f"AdminForceTeamChangeById {player_id}")

    async def disband_squad(self, team_1_or_2: str, squad_index: str):
        return await self.exec_command(f"AdminDisbandSquad {team_1_or_2} {squad_index}")

    async def list_squads(self):
        return await self.exec_command(f"ListSquads")

    # MATCHES
    async def end_match(self):
        return await self.exec_command(f"AdminEndMatch")

    async def restart_match(self):
        return await self.exec_command(f"AdminRestartMatch")

    async def switch_to_map(self, map_name: str):
        return await self.exec_command(f"AdminChangeMap {map_name}")

    async def set_next_map(self, map_name: str):
        return await self.exec_command(f"AdminSetNextMap {map_name}")

    async def show_current_map(self):
        return await self.exec_command(f"ShowCurrentMap")

    async def show_next_map(self):
        return await self.exec_command(f"ShowNextMap")

    async def set_next_layer(self, layer_name: str):
        return await self.exec_command(f"AdminSetNextLayer {layer_name}")

    async def change_layer(self, layer_name: str):
        return await self.exec_command(f"AdminChangeLayer {layer_name}")


    # ADMINISTRATION
    async def set_max_player_limit(self, limit: str):
        return await self.exec_command(f"AdminSetMaxNumPlayers")

    async def change_password(self, password: str = ""):
        return await self.exec_command(f"AdminSetServerPassword {password}")

    async def set_clockspeed(self, percentage: float):
        return await self.exec_command(f"AdminSlomo {str(percentage)}")


class RconCommandError(aiorcon.RCONError):
    """Raised when the game server communicates that there was an input error"""
    pass
