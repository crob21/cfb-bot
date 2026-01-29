#!/usr/bin/env python3
"""
CFB Data Cog for CFB 26 League Bot

Provides commands to look up college football data from CollegeFootballData.com.
Commands:
- /cfb player - Look up a single player
- /cfb players - Look up multiple players
- /cfb rankings - Get AP/Coaches/CFP rankings
- /cfb matchup - Head-to-head history
- /cfb schedule - Team's schedule
- /cfb draft - NFL draft picks
- /cfb transfers - Portal activity
- /cfb betting - Game lines
- /cfb ratings - Advanced ratings (SP+, SRS, Elo)
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors, Footers
from ..services.checks import check_module_enabled, check_module_enabled_deferred
from ..utils.server_config import server_config, FeatureModule
from ..utils.cfb_data import cfb_data

logger = logging.getLogger('CFB26Bot.CFBData')


class CFBDataCog(commands.Cog):
    """College football data from CollegeFootballData.com"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("📊 CFBDataCog initialized")

    # Command group
    cfb_group = app_commands.Group(
        name="cfb",
        description="📊 College football data, stats, and rankings"
    )

    async def _check_cfb_available(self, interaction: discord.Interaction) -> bool:
        """Check if CFB data API is available"""
        if not cfb_data.is_available:
            await interaction.followup.send(
                "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
                ephemeral=True
            )
            return False
        return True

    @cfb_group.command(name="player", description="Look up a college football player's stats and info")
    @app_commands.describe(
        name="Player name to search for (e.g., 'James Smith')",
        team="Optional team name to filter results (e.g., 'Alabama')"
    )
    async def player(
        self,
        interaction: discord.Interaction,
        name: str,
        team: Optional[str] = None
    ):
        """Look up player info from CollegeFootballData.com"""
        # Check module enabled BEFORE deferring so we can respond ephemerally if needed
        if not await check_module_enabled(interaction, FeatureModule.CFB_DATA, server_config):
            return

        # Now defer publicly (results will be public)
        await interaction.response.defer()

        if not await self._check_cfb_available(interaction):
            return

        logger.info(f"🏈 /cfb player from {interaction.user}: {name}" + (f" from {team}" if team else ""))

        try:
            player_info = await cfb_data.get_full_player_info(name, team)

            if player_info:
                response = cfb_data.format_player_response(player_info)
                embed = discord.Embed(
                    title="🏈 Player Info",
                    description=response,
                    color=Colors.PRIMARY
                )

                # Check if it's an Oregon player and add snark (Harry always hates Oregon)
                player_team = player_info.get('player', {}).get('team', '').lower()
                if 'oregon' in player_team and 'oregon state' not in player_team:
                    embed.set_footer(text="Harry's Player Lookup 🏈 | Though why you'd care about a Duck is beyond me...")
                else:
                    embed.set_footer(text=Footers.PLAYER_LOOKUP)

                await interaction.followup.send(embed=embed)
            else:
                # Player not found - delete the public "thinking" message and respond ephemerally
                await interaction.delete_original_response()
                embed = discord.Embed(
                    title="❓ Player Not Found",
                    description=f"Couldn't find a player matching **{name}**" + (f" from **{team}**" if team else "") + ".",
                    color=Colors.WARNING
                )
                embed.add_field(
                    name="💡 Tips",
                    value="• Check the spelling\n• Use full name (First Last)\n• FCS/smaller schools may have limited data\n• Try without the team name",
                    inline=False
                )
                embed.set_footer(text=Footers.PLAYER_LOOKUP)
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error in /cfb player: {e}", exc_info=True)
            # Try to delete the public "thinking" message
            try:
                await interaction.delete_original_response()
            except:
                pass  # May already be deleted or expired
            await interaction.followup.send(f"❌ Error looking up player: {str(e)}", ephemeral=True)

    @cfb_group.command(name="players", description="Look up multiple players at once")
    @app_commands.describe(
        player_list="Players separated by commas, e.g., 'James Smith (Bama DT); Isaiah Horton (Bama WR)'"
    )
    async def players(
        self,
        interaction: discord.Interaction,
        player_list: str
    ):
        """Look up multiple players at once"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        # Parse the player list
        players = cfb_data.parse_player_list(player_list)

        if not players:
            await interaction.followup.send(
                "❌ Couldn't parse any players from that list, mate!\n\n"
                "**Supported formats:**\n"
                "• `James Smith (Bama DT)`\n"
                "• `Isaiah Horton, Alabama, WR`\n"
                "• `Dre'Lon Miller (WR Colorado)`\n\n"
                "Separate multiple players with `;` or put each on a new line.",
                ephemeral=True
            )
            return

        if len(players) > 15:
            await interaction.followup.send(
                f"❌ That's {len(players)} players - max is 15 at a time to avoid rate limits!",
                ephemeral=True
            )
            return

        logger.info(f"🏈 /cfb players bulk lookup from {interaction.user}: {len(players)} players")

        try:
            results = await cfb_data.lookup_multiple_players(players)
            response = cfb_data.format_bulk_player_response(results)

            # Split into multiple messages if too long
            if len(response) > 4000:
                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                for i, chunk in enumerate(chunks):
                    embed = discord.Embed(
                        title="🏈 Player Lookup Results" + (f" (Part {i+1})" if len(chunks) > 1 else ""),
                        description=chunk,
                        color=Colors.PRIMARY
                    )
                    if i == len(chunks) - 1:
                        embed.set_footer(text="Harry's Bulk Lookup 🏈 | Data from CollegeFootballData.com")
                    await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="🏈 Player Lookup Results",
                    description=response,
                    color=Colors.PRIMARY
                )
                embed.set_footer(text="Harry's Bulk Lookup 🏈 | Data from CollegeFootballData.com")
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb players: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error looking up players: {str(e)}", ephemeral=True)

    @cfb_group.command(name="rankings", description="Get college football rankings (AP, Coaches, CFP)")
    @app_commands.describe(
        team="Optional team to highlight",
        year="Season year (default: current)",
        week="Week number (default: latest)",
        poll="Poll type: AP, Coaches, or CFP",
        top="Number of teams to show (default: 10)"
    )
    async def rankings(
        self,
        interaction: discord.Interaction,
        team: Optional[str] = None,
        year: Optional[int] = None,
        week: Optional[int] = None,
        poll: Optional[str] = None,
        top: int = 10
    ):
        """Get CFB rankings - optionally filter by team, week, or poll"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        # Clamp top to reasonable range
        top = max(1, min(25, top))

        try:
            if team:
                # Team-specific ranking lookup
                result = await cfb_data.get_team_ranking(team, year)
                response = cfb_data.format_team_ranking(result)
                title = f"📊 {team} Rankings ({year})"

                embed = discord.Embed(title=title, description=response, color=Colors.PRIMARY)
                embed.set_footer(text=Footers.CFB_DATA)
                await interaction.followup.send(embed=embed)
            else:
                # Full rankings - use fields to avoid character limit
                result = await cfb_data.get_rankings(year, week=week)
                fields, week_num = cfb_data.format_rankings(result, poll_filter=poll, top_n=top)

                if not fields:
                    await interaction.followup.send("No rankings found for the specified criteria.", ephemeral=True)
                    return

                # Build title with week info
                title = f"🏈 College Football Rankings ({year})"
                if week_num:
                    title += f" - Week {week_num}"
                if poll:
                    title += f" - {poll}"

                embed = discord.Embed(title=title, color=Colors.PRIMARY)

                # Add fields (Discord limit: 25 fields, 1024 chars per field value)
                for field in fields[:6]:  # Limit to 6 polls max
                    value = field['value']
                    # Truncate if too long for a field
                    if len(value) > 1024:
                        lines = value.split('\n')[:top]
                        value = '\n'.join(lines)
                        if len(value) > 1020:
                            value = value[:1020] + "..."

                    embed.add_field(
                        name=field['name'],
                        value=value,
                        inline=True
                    )

                embed.set_footer(text=f"Week {week_num} | Top {top} | Harry's CFB Data 🏈")
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb rankings: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @cfb_group.command(name="matchup", description="Get historical matchup data between two teams")
    @app_commands.describe(
        team1="First team (e.g., 'Alabama')",
        team2="Second team (e.g., 'Auburn')"
    )
    async def matchup(
        self,
        interaction: discord.Interaction,
        team1: str,
        team2: str
    ):
        """Get all-time matchup history between two teams"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        try:
            result = await cfb_data.get_matchup_history(team1, team2)
            response = cfb_data.format_matchup(result)

            embed = discord.Embed(
                title=f"🏈 {team1} vs {team2}",
                description=response,
                color=Colors.PRIMARY
            )
            embed.set_footer(text=Footers.CFB_DATA)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb matchup: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @cfb_group.command(name="schedule", description="Get a team's schedule and results")
    @app_commands.describe(
        team="Team name (e.g., 'Nebraska')",
        year="Season year (default: current)"
    )
    async def schedule(
        self,
        interaction: discord.Interaction,
        team: str,
        year: Optional[int] = None
    ):
        """Get a team's full schedule for a season"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        try:
            result = await cfb_data.get_team_schedule(team, year)
            response = cfb_data.format_schedule(result, team)

            embed = discord.Embed(
                title=f"📅 {team} Schedule ({year})",
                description=response,
                color=Colors.PRIMARY
            )
            embed.set_footer(text=Footers.CFB_DATA)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb schedule: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @cfb_group.command(name="draft", description="Get NFL draft picks from a college")
    @app_commands.describe(
        team="Optional college team to filter by",
        year="Draft year (default: current year)"
    )
    async def draft(
        self,
        interaction: discord.Interaction,
        team: Optional[str] = None,
        year: Optional[int] = None
    ):
        """Get NFL draft picks, optionally filtered by college"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        try:
            result = await cfb_data.get_draft_picks(team, year)
            response = cfb_data.format_draft_picks(result, team)

            title = f"🏈 {year} NFL Draft Picks" + (f" from {team}" if team else "")
            embed = discord.Embed(title=title, description=response, color=Colors.PRIMARY)
            embed.set_footer(text=Footers.CFB_DATA)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb draft: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @cfb_group.command(name="transfers", description="Get transfer portal activity for a team")
    @app_commands.describe(
        team="Team name (e.g., 'USC')",
        year="Year to check (default: current)"
    )
    async def transfers(
        self,
        interaction: discord.Interaction,
        team: str,
        year: Optional[int] = None
    ):
        """Get transfer portal incoming and outgoing for a team"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        try:
            result = await cfb_data.get_team_transfers(team, year)
            response = cfb_data.format_transfers(result, team)

            embed = discord.Embed(
                title=f"🔄 {team} Transfer Portal ({year})",
                description=response,
                color=Colors.PRIMARY
            )
            embed.set_footer(text=Footers.CFB_DATA)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb transfers: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @cfb_group.command(name="betting", description="Get betting lines for games")
    @app_commands.describe(
        team="Optional team to filter by",
        year="Season year (default: current)",
        week="Week number (default: current)"
    )
    async def betting(
        self,
        interaction: discord.Interaction,
        team: Optional[str] = None,
        year: Optional[int] = None,
        week: Optional[int] = None
    ):
        """Get betting lines for games"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        try:
            result, query_info = await cfb_data.get_betting_lines(team, year, week)
            response = cfb_data.format_betting_lines(result, query_info)

            # Build title from query info
            title = "💰 Betting Lines"
            if team:
                title += f" - {team}"

            # Add year to title
            q_year = query_info.get('year', '')
            q_season_type = query_info.get('season_type', 'regular')
            q_week = query_info.get('week', '')

            if q_season_type == 'postseason':
                title += f" ({q_year} Postseason)"
            elif q_week and q_week != 'none':
                title += f" ({q_year} Week {q_week})"
            else:
                title += f" ({q_year})"

            embed = discord.Embed(title=title, description=response, color=Colors.PRIMARY)
            embed.set_footer(text=Footers.CFB_DATA)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb betting: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @cfb_group.command(name="ratings", description="Get advanced ratings (SP+, SRS, Elo) for a team")
    @app_commands.describe(
        team="Team name (e.g., 'Ohio State')",
        year="Season year (default: current)"
    )
    async def ratings(
        self,
        interaction: discord.Interaction,
        team: str,
        year: Optional[int] = None
    ):
        """Get advanced analytics ratings for a team"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        try:
            result = await cfb_data.get_team_ratings(team, year)
            response = cfb_data.format_ratings(result)

            embed = discord.Embed(
                title=f"📈 {team} Advanced Ratings ({year})",
                description=response,
                color=Colors.PRIMARY
            )
            embed.set_footer(text=Footers.CFB_DATA)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb ratings: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @cfb_group.command(name="teamstats", description="Get full season statistics for a team (offense & defense)")
    @app_commands.describe(
        team="Team name (e.g., 'Washington')",
        year="Season year (default: current)"
    )
    async def teamstats(
        self,
        interaction: discord.Interaction,
        team: str,
        year: Optional[int] = None
    ):
        """Get comprehensive team statistics for a season"""
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA, server_config):
            return

        if not await self._check_cfb_available(interaction):
            return

        try:
            result = await cfb_data.get_team_season_stats(team, year)
            
            if not result:
                await interaction.followup.send(
                    f"❌ No statistics found for **{team}** ({year or 'current season'}).\n\n"
                    "**Tips:**\n"
                    "• Check the team name spelling\n"
                    "• Some teams may not have complete data for recent seasons\n"
                    "• FCS teams may have limited stats",
                    ephemeral=True
                )
                return
            
            response = cfb_data.format_team_stats(result)

            # Split into multiple embeds if too long
            if len(response) > 4000:
                # Split by offense/defense sections
                lines = response.split('\n')
                offense_section = []
                defense_section = []
                header = []
                current_section = header
                
                for line in lines:
                    if '**🏈 OFFENSE**' in line:
                        current_section = offense_section
                    elif '**🛡️ DEFENSE**' in line:
                        current_section = defense_section
                    current_section.append(line)
                
                # Send offense first
                if offense_section:
                    offense_text = '\n'.join(header + offense_section)
                    embed = discord.Embed(
                        title=f"📊 {team} Season Statistics ({year}) - Offense",
                        description=offense_text,
                        color=Colors.PRIMARY
                    )
                    embed.set_footer(text="Harry's CFB Stats 🏈 | Part 1 of 2")
                    await interaction.followup.send(embed=embed)
                
                # Then defense
                if defense_section:
                    defense_text = '\n'.join([''] + defense_section)
                    embed = discord.Embed(
                        title=f"📊 {team} Season Statistics ({year}) - Defense",
                        description=defense_text,
                        color=Colors.PRIMARY
                    )
                    embed.set_footer(text=Footers.CFB_DATA + " | Part 2 of 2")
                    await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title=f"📊 {team} Season Statistics ({year})",
                    description=response,
                    color=Colors.PRIMARY
                )
                embed.set_footer(text=Footers.CFB_DATA)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /cfb teamstats: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = CFBDataCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ CFBDataCog loaded")
    logger.info("✅ CFBDataCog loaded")
