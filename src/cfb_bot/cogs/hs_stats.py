#!/usr/bin/env python3
"""
High School Stats Cog for CFB League Bot

Provides commands to look up high school football player stats from MaxPreps.
Commands:
- /hs stats - Look up a single player
- /hs bulk - Look up multiple players at once
"""

import logging
import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors, Footers
from ..services.checks import check_module_enabled_deferred
from ..utils.server_config import server_config, FeatureModule
from ..utils.hs_stats_scraper import hs_stats_scraper

logger = logging.getLogger('CFBBot.HSStats')


class HSStatsCog(commands.Cog):
    """High school football stats from MaxPreps"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("🏫 HSStatsCog initialized")

    # Command group
    hs_group = app_commands.Group(
        name="hs",
        description="🏫 High school football stats from MaxPreps"
    )

    @hs_group.command(name="stats", description="Look up high school football player stats from MaxPreps")
    @app_commands.describe(
        name="Player name (e.g., 'Arch Manning')",
        state="Optional state to narrow search (e.g., 'Louisiana', 'TX')",
        school="Optional high school name to narrow search"
    )
    async def stats(
        self,
        interaction: discord.Interaction,
        name: str,
        state: Optional[str] = None,
        school: Optional[str] = None
    ):
        """
        Look up high school football player stats.

        Args:
            name: Player name (e.g., "Arch Manning")
            state: Optional state to narrow search (e.g., "Louisiana", "TX")
            school: Optional high school name to narrow search
        """
        # Defer FIRST to avoid interaction timeout (3 sec limit)
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.HS_STATS, server_config):
            return

        if not hs_stats_scraper.is_available:
            await interaction.followup.send(
                "❌ High school stats scraper is not available.\n"
                "Missing dependencies: `pip install httpx beautifulsoup4`",
                ephemeral=True
            )
            return

        try:
            # First search to check for multiple results
            search_results = await hs_stats_scraper.search_player(name, state)
            multiple_results_warning = None

            if len(search_results) > 1:
                # Multiple players found - warn the user
                other_players = []
                for result in search_results[1:4]:  # Show up to 3 other matches
                    result_name = result.get('name', 'Unknown')
                    # Clean up the name (MaxPreps concatenates school)
                    if '(' in result_name:
                        result_name = result_name.split('(')[0].strip()
                    other_players.append(result_name)

                multiple_results_warning = (
                    f"⚠️ **Found {len(search_results)} players matching '{name}'**\n"
                    f"Showing first result. Other matches: {', '.join(other_players)}\n"
                    f"_Add a state filter to narrow results: `/hs stats name:{name} state:XX`_\n\n"
                )

            player_data = await hs_stats_scraper.lookup_player(name, state, school)

            if not player_data:
                # No results found - ephemeral so only user sees it
                embed = discord.Embed(
                    title=f"🔍 No Results for '{name}'",
                    description=(
                        f"Couldn't find a player matching **{name}**.\n\n"
                        "**Tips:**\n"
                        "• Check the spelling of the name\n"
                        "• Add a state filter: `/hs stats name:Arch Manning state:LA`\n"
                        "• Add a school filter for common names\n"
                        "• MaxPreps data may be limited for some players"
                    ),
                    color=Colors.WARNING
                )
                embed.set_footer(text=Footers.HS_STATS)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Format and send stats
            formatted = hs_stats_scraper.format_player_stats(player_data)

            # Add warning if multiple results were found
            if multiple_results_warning:
                formatted = multiple_results_warning + formatted

            embed = discord.Embed(
                title="🏈 High School Stats",
                description=formatted,
                color=Colors.HS_STATS
            )
            embed.set_footer(text=Footers.HS_STATS)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /hs stats: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error looking up player: {str(e)}",
                ephemeral=True
            )

    @hs_group.command(name="bulk", description="Look up multiple HS players at once")
    @app_commands.describe(
        players="Comma-separated player names, e.g., 'Arch Manning (LA), Dylan Raiola (AZ)'"
    )
    async def bulk(
        self,
        interaction: discord.Interaction,
        players: str
    ):
        """
        Bulk lookup for high school players.

        Args:
            players: Comma-separated list of player names
                     Format: "Name (State/School), Name (State/School)"
                     Example: "Arch Manning (LA), Dylan Raiola (AZ)"
        """
        # Defer FIRST to avoid interaction timeout (3 sec limit)
        await interaction.response.defer()

        if not await check_module_enabled_deferred(interaction, FeatureModule.HS_STATS, server_config):
            return

        if not hs_stats_scraper.is_available:
            await interaction.followup.send(
                "❌ High school stats scraper is not available.\n"
                "Missing dependencies: `pip install httpx beautifulsoup4`",
                ephemeral=True
            )
            return

        try:
            # Parse player list
            player_list = []
            for player_entry in players.split(','):
                player_entry = player_entry.strip()
                if not player_entry:
                    continue

                # Parse "Name (State/School)" format
                match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', player_entry)
                if match:
                    name = match.group(1).strip()
                    location = match.group(2).strip()
                    # Assume 2-letter = state, otherwise school
                    if len(location) <= 3:
                        player_list.append({'name': name, 'state': location})
                    else:
                        player_list.append({'name': name, 'school': location})
                else:
                    player_list.append({'name': player_entry})

            if not player_list:
                await interaction.followup.send(
                    "❌ No valid player names provided.\n"
                    "Format: `Arch Manning (LA), Dylan Raiola (AZ)`",
                    ephemeral=True
                )
                return

            if len(player_list) > 10:
                await interaction.followup.send(
                    "⚠️ Too many players (max 10). Showing first 10.",
                    ephemeral=True
                )
                player_list = player_list[:10]

            # Send progress message
            await interaction.followup.send(f"🔍 Looking up {len(player_list)} players... (this may take a moment)")

            # Bulk lookup
            results = await hs_stats_scraper.lookup_multiple_players(player_list)

            # Format results
            found_count = sum(1 for r in results if r.get('found'))
            embed = discord.Embed(
                title=f"🏈 HS Stats Bulk Lookup ({found_count}/{len(results)} found)",
                color=Colors.HS_STATS if found_count > 0 else 0xff6b6b
            )

            for result in results:
                query = result.get('query', {})
                player_name = query.get('name', 'Unknown')

                if result.get('found'):
                    data = result.get('data', {})
                    # Compact format for bulk
                    school_name = data.get('school', 'Unknown School')
                    position = data.get('position', '')

                    # Get most recent season stats
                    seasons = data.get('seasons', [])
                    stats_line = ""
                    if seasons:
                        recent = seasons[-1]
                        if recent.get('passing'):
                            p = recent['passing']
                            stats_line = f"Pass: {p.get('yards', '?')} YDS, {p.get('touchdowns', '?')} TD"
                        elif recent.get('rushing'):
                            r = recent['rushing']
                            stats_line = f"Rush: {r.get('yards', '?')} YDS, {r.get('touchdowns', '?')} TD"
                        elif recent.get('receiving'):
                            rc = recent['receiving']
                            stats_line = f"Rec: {rc.get('yards', '?')} YDS, {rc.get('touchdowns', '?')} TD"
                        elif recent.get('defense'):
                            d = recent['defense']
                            stats_line = f"Def: {d.get('tackles', '?')} TKL, {d.get('sacks', '?')} SCK"

                    value = f"🏫 {school_name}"
                    if position:
                        value += f" | 📍 {position}"
                    if stats_line:
                        value += f"\n{stats_line}"

                    embed.add_field(name=f"✅ {player_name}", value=value, inline=False)
                else:
                    error = result.get('error', 'Not found on MaxPreps')
                    embed.add_field(
                        name=f"❌ {player_name}",
                        value=f"_{error}_",
                        inline=False
                    )

            embed.set_footer(text=Footers.HS_STATS)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /hs bulk: {e}", exc_info=True)
            await interaction.followup.send(
                f"❌ Error looking up players: {str(e)}",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = HSStatsCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ HSStatsCog loaded")
    logger.info("✅ HSStatsCog loaded")

