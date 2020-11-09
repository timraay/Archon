import discord
from discord.ext import commands, tasks
import json
from ast import literal_eval
from datetime import datetime

from rcon.instances import check_perms, get_available_instances, perms_to_dict

from utils import Config, get_player_input_type, add_empty_fields, base_embed
config = Config()



class public(commands.Cog):
    """Server statuses and player information"""

    def __init__(self, bot):
        self.bot = bot


    @commands.command(description="View the server's current status", usage="r!server [instance]")
    @check_perms(public=True)
    async def server(self, ctx, *, instance_id=None):
        if instance_id:
            instances = get_available_instances(ctx.author.id, ctx.guild.id)
            inst = None
            for i, (instance, perms) in enumerate(instances):
                if str(i+1) == instance_id or instance.name.lower() == instance_id.lower():
                    inst = instance
                    break
            if not inst:
                raise commands.BadArgument("No instance found with name or ID %s" % instance_id)
            if perms_to_dict(perms)["public"] == False:
                raise commands.BadArgument("Missing required permissions for this instance")
            inst = self.bot.cache.instance(inst.id, by_inst_id=True).update()
        else:
            inst = self.bot.cache.instance(ctx.author.id).update()
        
        embed = self.create_server_embed(inst)
        await ctx.send(embed=embed)
    
    @commands.command(description="View statuses of all accessible servers", usage="r!servers")
    async def servers(self, ctx):
        instances = get_available_instances(ctx.author.id, ctx.guild.id)
        instances = [self.bot.cache.instance(inst.id, by_inst_id=True).update() for inst, perms in instances if perms_to_dict(perms)["public"] == True]
        for inst in instances:      
            embed = self.create_server_embed(inst)
            await ctx.send(embed=embed)

    def create_server_embed(self, inst):
        playercount = len(inst.players)
        if playercount >= 100: color = discord.Color.dark_red()
        elif playercount >= 80: color = discord.Color.red()
        elif playercount >= 50: color = discord.Color.orange()
        elif playercount >= 20: color = discord.Color.gold()
        elif playercount >= 10: color = discord.Color.green()
        elif playercount >= 3: color = discord.Color.dark_green()
        else: color = discord.Embed.Empty
        
        embed = base_embed(inst.id, color=color)
        embed.add_field(name="Players", value=f"{str(playercount)}/100")
        embed.add_field(name="Current Map", value=inst.current_map)
        embed.add_field(name="Next Map", value=inst.next_map)
        return embed


    @commands.command(description="Get an overview of both teams", usage="r!players [team id]", aliases=["team", "teams", "squads"])
    @check_perms(public=True)
    async def players(self, ctx, team_id: int = 1):
        if team_id not in [1, 2]:
            raise commands.BadArgument('team_id needs to be either 1 or 2')
        
        inst = self.bot.cache.instance(ctx.author.id).update()

        def build_embed(team_id):
            if team_id == 1: team = inst.team1
            elif team_id == 2: team = inst.team2
            
            embed = base_embed(inst.id, title=f"Team {str(team_id)} - {team.faction}", description=f"{str(len(team))} players")

            # Add a field for each squad
            for squad in team.squads:
                name = f"{str(squad.id)} | {squad.name} ({str(len(squad.player_ids))})"
                players = "\n".join([f"> {inst.get_player(player_id).name}" for player_id in squad.player_ids])
                embed.add_field(name=name, value=players)

            # Add empty fields if needed to make the embed look nicer
            embed = add_empty_fields(embed)

            # Add fields with unassigned players
            if team.unassigned:
                embed.add_field(name="‏‎ ", value="‏‎ ", inline=False)
                field1 = []
                field2 = []
                field3 = []
                for i, player_id in enumerate(team.unassigned):
                    if i % 3 == 0: field1.append(player_id)
                    if i % 3 == 1: field2.append(player_id)
                    if i % 3 == 2: field3.append(player_id)
                total_lines = len(field1)
                for field in [field1, field2, field3]:
                    name = f"Unassigned Players ({str(len(team.unassigned))})" if field == field1 else "‏‎ "
                    lines = ["> ‏‎ "] * total_lines
                    for i, player_id in enumerate(field):
                        lines[i] = "> " + inst.get_player(player_id).name
                    value = "\n".join(lines)
                    embed.add_field(name=name, value=value)

            return embed
        
        embed = build_embed(team_id)
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('1⃣')
        await msg.add_reaction('2⃣')

        def check(reaction, user):
            return reaction.message.id == msg.id and str(reaction.emoji) in ['1⃣', '2⃣'] and not user.bot
            
        while True:
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=120.0, check=check)
            except:
                await msg.clear_reactions()
                break
            else:
                if str(reaction) == '1⃣':
                    team_id = 1
                elif str(reaction) == '2⃣':
                    team_id = 2
                await msg.edit(embed=build_embed(team_id))
                await msg.remove_reaction(reaction.emoji, user)

    @commands.command(description="Get an overview of a squad", usage="r!squad <team id> <squad id>")    
    @check_perms(public=True)
    async def squad(self, ctx, team_id: int, squad_id: int):
        if team_id not in [1, 2]:
            raise commands.BadArgument('team_id needs to be either 1 or 2')
        
        inst = self.bot.cache.instance(ctx.author.id).update()
        if team_id == 1: team = inst.team1
        elif team_id == 2: team = inst.team2
        squad = None
        for itersquad in team.squads:
            if itersquad.id == squad_id:
                squad = itersquad
                break
        if not squad: raise commands.BadArgument('No squad was found with the given squad id')

        embed = base_embed(inst.id, title=squad.name, description=f"> Size: {str(len(squad))}\n> Squad ID: {str(squad_id)}\n> Team: {team.faction}")

        players = [inst.get_player(player_id) for player_id in squad.player_ids]
        for player_num, player in enumerate(players):
            player_num += 1
            if player_num == 1: player_num = "SQL"
            else: player_num = str(player_num)

            embed.add_field(name=f"{player_num} | {player.name}", value=f"*{str(player.steam_id)}*\n> Player ID: {str(player.player_id)}\n> Online For: {str(player.online_time())}m")

        # Add empty fields if needed to make the embed look nicer
        embed = add_empty_fields(embed)

        await ctx.send(embed=embed)
    
    @commands.command(description="Receive playerdata", usage="r!player <name or id>", aliases=["playerdata", "list_player", "listplayer"])
    @check_perms(public=True)
    async def player(self, ctx, *, name_or_id):
        player = self.bot.cache.instance(ctx.author.id).get_player(name_or_id, related_names=True)
        if not player:
            raise commands.BadArgument("Couldn't find a player with this name or ID currently online")
        
        embed = base_embed(self.bot.cache._get_selected_instance(ctx.author.id), title=player.name)
        embed.add_field(name="Steam ID", value=f"`{player.steam_id}`")
        embed.add_field(name="Online For", value=f"{str(player.online_time())} minutes")
        embed.add_field(name="First Logged In", value="Coming Soon")
        embed.add_field(name="Player ID", value=str(player.player_id))
        embed.add_field(name="Team ID", value=str(player.team_id))
        embed.add_field(name="Squad ID", value=str(player.squad_id))
        await ctx.send(embed=embed)
        

    @commands.command(description="View the current and upcoming map", usage="r!map", aliases=["map_rotation", "maprotation", "rotation"])
    @check_perms(public=True)
    async def map(self, ctx):
        inst = self.bot.cache.instance(ctx.author.id)
        current_map = inst.current_map
        next_map = inst.next_map
        try:
            time_since_map_change = int((datetime.now() - inst.last_map_change).total_seconds() / 60)
        except:
            time_since_map_change = -1
        embed = base_embed(inst.id, title=f"Current map is {current_map}", description=f"Next map will be **{next_map}**\nMap last changed {str(time_since_map_change)}m ago")
        await ctx.send(embed=embed)
    

def setup(bot):
    bot.add_cog(public(bot))