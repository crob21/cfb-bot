#!/usr/bin/env python3
"""
Recruiting Cog for CFB 26 League Bot

Provides commands to look up recruiting data from On3/Rivals or 247Sports.
Commands:
- /recruiting player - Look up a recruit
- /recruiting top - Top recruits by position/state
- /recruiting class - Team recruiting class
- /recruiting commits - Team's committed recruits
- /recruiting rankings - Top team rankings
- /recruiting portal - Transfer portal player lookup
- /recruiting source - Change data source
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors, Footers
from ..services.checks import check_module_enabled, check_module_enabled_deferred
from ..utils.server_config import server_config, FeatureModule, RecruitingSource
from ..utils.on3_scraper import on3_scraper
from ..utils.recruiting_scraper import recruiting_scraper
from ..utils.cfb_data import cfb_data
from ..utils.cache import get_cache

logger = logging.getLogger('CFB26Bot.Recruiting')


def get_recruiting_scraper(guild_id: int):
    """Get the appropriate recruiting scraper based on server config"""
    source = server_config.get_recruiting_source(guild_id)
    if source == RecruitingSource.SPORTS247:
        return recruiting_scraper, "247Sports Composite"
    else:
        return on3_scraper, "On3/Rivals"


class RecruitingCog(commands.Cog):
    """Recruiting data from On3/Rivals and 247Sports"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.admin_manager = None  # Will be set by bot after loading
        logger.info("⭐ RecruitingCog initialized")

    # Command group
    recruiting_group = app_commands.Group(
        name="recruiting",
        description="⭐ Recruiting rankings, commits, and player lookups"
    )

    @recruiting_group.command(name="player", description="Look up a recruit's ranking")
    @app_commands.describe(
        name="Recruit name (e.g., 'Arch Manning')",
        year="Recruiting class year (default: current)",
        position="Position filter (for duplicate names like 'Elijah Brown')",
        deep_search="(247Sports only) Search ALL ranked recruits (~3000+) instead of top 1000"
    )
    @app_commands.choices(position=[
        app_commands.Choice(name="QB - Quarterback", value="QB"),
        app_commands.Choice(name="RB - Running Back", value="RB"),
        app_commands.Choice(name="WR - Wide Receiver", value="WR"),
        app_commands.Choice(name="TE - Tight End", value="TE"),
        app_commands.Choice(name="OT - Offensive Tackle", value="OT"),
        app_commands.Choice(name="OG - Offensive Guard", value="OG"),
        app_commands.Choice(name="C - Center", value="C"),
        app_commands.Choice(name="EDGE - Edge Rusher", value="EDGE"),
        app_commands.Choice(name="DL - Defensive Line", value="DL"),
        app_commands.Choice(name="LB - Linebacker", value="LB"),
        app_commands.Choice(name="CB - Cornerback", value="CB"),
        app_commands.Choice(name="S - Safety", value="S"),
        app_commands.Choice(name="ATH - Athlete", value="ATH"),
    ])
    async def player(
        self,
        interaction: discord.Interaction,
        name: str,
        year: Optional[int] = None,
        position: Optional[str] = None,
        deep_search: bool = False
    ):
        """Look up a recruit from configured recruiting source"""
        if not await check_module_enabled(interaction, FeatureModule.RECRUITING, server_config):
            return

        # Defer immediately as PUBLIC - On3 searches can take 5-10+ seconds with retries/blocks
        # This means "not found" errors will also be public, but that's better than interaction timeout
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning(f"⚠️ /recruiting player interaction expired for {name}")
            return

        try:
            guild_id = interaction.guild.id if interaction.guild else 0
            scraper, source_name = get_recruiting_scraper(guild_id)

            search_depth = "deep (all ~3000)" if deep_search else "standard"
            pos_filter = f" (position: {position})" if position else ""
            logger.info(f"🔍 /recruiting player: {name} ({year or 'current'}){pos_filter} via {source_name} - {search_depth}")

            # Check cache first (24 hour TTL) - include position in cache key
            cache = get_cache()
            cache_key = f"{name.lower()}:{year or 'current'}:{source_name}:{deep_search}:{position or 'any'}"
            recruit = cache.get(cache_key, namespace='recruiting')

            if recruit:
                logger.info(f"✅ Cache HIT for {name} - saved API call!")
            else:
                # Cache miss - scrape the data
                max_pages = 65 if deep_search else 20
                recruit = await scraper.search_recruit(name, year, max_pages=max_pages, position=position)

                if recruit:
                    # Cache successful lookups for 24 hours (86400 seconds)
                    cache.set(cache_key, recruit, ttl_seconds=86400, namespace='recruiting')
                    logger.info(f"💾 Cached {name} for 24 hours")

            # Check if we got multiple candidates
            if recruit and recruit.get('multiple'):
                candidates = recruit.get('candidates', [])
                query_name = recruit.get('query_name', name)
                total_found = recruit.get('total_found', len(candidates))
                
                if len(candidates) == 0:
                    # No candidates found (likely filtered out by position)
                    pos_msg = f" with position **{position}**" if position else ""
                    embed = discord.Embed(
                        title="❓ No Players Found",
                        description=f"Couldn't find **{query_name}**{pos_msg}.\n\n"
                                   f"💡 Try removing the position filter or check the spelling.",
                        color=Colors.WARNING
                    )
                    embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                elif len(candidates) == 1:
                    # Exactly one candidate (possibly after position filter)
                    recruit = candidates[0]
                else:
                    # Show selection menu
                    filter_msg = f" (filtered by position: **{position}**)" if position else ""
                    
                    # Show "X of Y" if we had to limit results
                    count_msg = f"**{len(candidates)}** player(s)"
                    if total_found > len(candidates):
                        count_msg = f"**{len(candidates)} of {total_found}** players (showing top 15)"
                    
                    embed = discord.Embed(
                        title=f"🔍 Multiple players found: {query_name}",
                        description=f"Found {count_msg} with this name{filter_msg}. Please select which one you're looking for:",
                        color=Colors.WARNING
                    )

                    # Add each candidate as a field
                    for i, candidate in enumerate(candidates, 1):  # Show all candidates (up to 15)
                        stars = '⭐' * candidate.get('stars', 0) if candidate.get('stars') else 'Unranked'
                        pos = candidate.get('position', '?')
                        school = candidate.get('committed_to') or candidate.get('high_school', 'Unknown')
                        class_year = candidate.get('class', year or '?')

                        field_value = f"**Position:** {pos}\n**Class:** {class_year}\n**Rating:** {stars}"
                        if candidate.get('committed_to'):
                            field_value += f"\n**Committed:** {candidate['committed_to']} ✅"
                        elif candidate.get('high_school'):
                            field_value += f"\n**HS:** {school}"

                        embed.add_field(
                            name=f"{i}. {candidate.get('name', query_name)}",
                            value=field_value,
                            inline=True
                        )

                    # Create select menu
                    select = discord.ui.Select(
                        placeholder="Choose which player you want to see...",
                        options=[
                            discord.SelectOption(
                                label=f"{candidate.get('name', query_name)} ({candidate.get('position', '?')})",
                                description=f"Class {candidate.get('class', '?')} - {(candidate.get('committed_to') or candidate.get('high_school') or 'Unknown')[:50]}",
                                value=str(i)
                            )
                            for i, candidate in enumerate(candidates)  # Show all candidates (up to 15)
                        ]
                    )

                    async def select_callback(select_interaction: discord.Interaction):
                        selected_idx = int(select.values[0])
                        selected_recruit = candidates[selected_idx]

                        # Build the full recruit embed
                        result_embed = discord.Embed(
                            title=f"⭐ Recruit: {selected_recruit.get('name', query_name)}",
                            description=scraper.format_recruit(selected_recruit),
                            color=Colors.RECRUITING
                        )

                        if selected_recruit.get('image_url'):
                            result_embed.set_thumbnail(url=selected_recruit['image_url'])

                        if selected_recruit.get('profile_url'):
                            result_embed.add_field(
                                name="🔗 Profile",
                                value=f"[View Full Profile on On3/Rivals]({selected_recruit['profile_url']})",
                                inline=False
                            )

                        result_embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
                        await select_interaction.response.edit_message(embed=result_embed, view=None)

                    select.callback = select_callback
                    view = discord.ui.View(timeout=180)  # 3 minute timeout
                    view.add_item(select)
                    
                    # Add helpful footer
                    footer_text = "Harry's Recruiting 🏈 | Use the menu below to select"
                    if total_found > 15 and not position:
                        footer_text = "Harry's Recruiting 🏈 | 💡 Tip: Use position: filter to narrow results"
                    
                    embed.set_footer(text=footer_text)
                    await interaction.followup.send(embed=embed, view=view)
                    return

            if recruit:
                embed = discord.Embed(
                    title=f"⭐ Recruit: {recruit.get('name', name)}",
                    description=scraper.format_recruit(recruit),
                    color=Colors.RECRUITING
                )

                if recruit.get('image_url'):
                    embed.set_thumbnail(url=recruit['image_url'])

                # Auto-fetch college stats for transfer portal players
                if recruit.get('is_transfer'):
                    college_stats = None
                    recruit_name = recruit.get('name', name)
                    previous_school = recruit.get('previous_school')

                    # Try 1: Full name lookup
                    try:
                        college_stats = await cfb_data.get_full_player_info(recruit_name, previous_school)
                    except Exception as e:
                        logger.debug(f"Full name CFB lookup failed for {recruit_name}: {e}")

                    # Try 2: Last name only with position matching (handles nicknames like "Hollywood Smothers" -> "Daylan Smothers")
                    if not college_stats:
                        name_parts = recruit_name.split()
                        if len(name_parts) >= 2:
                            last_name = name_parts[-1]
                            on3_pos = recruit.get('position', '').upper()
                            try:
                                players = await cfb_data.search_player(last_name, previous_school)
                                if players and on3_pos:
                                    # Position group mapping
                                    pos_groups = {
                                        'RB': ['RB', 'HB', 'FB'], 'WR': ['WR'], 'QB': ['QB'], 'TE': ['TE'],
                                        'OT': ['OT', 'OL', 'T'], 'OG': ['OG', 'OL', 'G'], 'C': ['C', 'OL'],
                                        'DL': ['DL', 'DE', 'DT', 'NT'], 'DE': ['DE', 'DL', 'EDGE'],
                                        'LB': ['LB', 'ILB', 'OLB'], 'CB': ['CB', 'DB'], 'S': ['S', 'SS', 'FS', 'DB'],
                                    }
                                    valid_pos = pos_groups.get(on3_pos, [on3_pos])
                                    for p in players:
                                        cfb_pos = (p.get('position') or '').upper()
                                        if cfb_pos in valid_pos or on3_pos in cfb_pos:
                                            college_stats = await cfb_data.get_full_player_info(p.get('name'), p.get('team'))
                                            if college_stats:
                                                logger.info(f"✅ Found college stats via last name match: {p.get('name')}")
                                                break
                                elif players:
                                    # No position to match, take first result
                                    college_stats = await cfb_data.get_full_player_info(players[0].get('name'), players[0].get('team'))
                            except Exception as e:
                                logger.debug(f"Last name CFB lookup failed: {e}")

                    # Display college stats if found
                    if college_stats and college_stats.get('stats'):
                        stats_lines = []
                        team_name = college_stats.get('team', '')
                        if team_name:
                            stats_lines.append(f"**School:** {team_name}")

                        stats = college_stats.get('stats', {})
                        years = sorted(stats.keys(), reverse=True)
                        for yr in years[:2]:
                            ys = stats[yr]
                            stat_str = None
                            if ys.get('receiving', {}).get('YDS'):
                                stat_str = f"🎯 {ys['receiving'].get('REC', 0)} REC | {ys['receiving']['YDS']} YDS | {ys['receiving'].get('TD', 0)} TD"
                            elif ys.get('rushing', {}).get('YDS'):
                                stat_str = f"🏃 {ys['rushing'].get('CAR', 0)} CAR | {ys['rushing']['YDS']} YDS | {ys['rushing'].get('TD', 0)} TD"
                            elif ys.get('passing', {}).get('YDS'):
                                stat_str = f"🎯 {ys['passing']['YDS']} YDS | {ys['passing'].get('TD', 0)} TD | {ys['passing'].get('INT', 0)} INT"
                            elif ys.get('defense', {}).get('TOT') or ys.get('defense', {}).get('SOLO'):
                                d = ys['defense']
                                stat_str = f"🛡️ {d.get('TOT', d.get('SOLO', 0))} TKL | {d.get('TFL', 0)} TFL | {d.get('SACKS', 0)} Sacks"
                            if stat_str:
                                stats_lines.append(f"**{yr}:** {stat_str}")

                        if stats_lines:
                            embed.add_field(
                                name="🏈 College Stats (Transfer)",
                                value='\n'.join(stats_lines),
                                inline=False
                            )

                # Profile link at bottom
                if recruit.get('profile_url'):
                    embed.add_field(
                        name="🔗 Profile",
                        value=f"[View Full Profile on On3/Rivals]({recruit['profile_url']})",
                        inline=False
                    )

                footer = f"Harry's Recruiting 🏈 | Data from {source_name}"
                if recruit.get('is_transfer'):
                    footer = f"Harry's Portal Tracker 🔄 | Data from {source_name}"
                elif deep_search and source_name == "247Sports Composite":
                    footer += " | Deep Search"
                embed.set_footer(text=footer)
                await interaction.followup.send(embed=embed)
            else:
                tips = [
                    "• Check the spelling",
                    "• Try the full name",
                    "• Specify the year if not current class",
                ]
                if not position:
                    tips.append("• Add `position:WR` (or QB, RB, etc.) if multiple players share this name")
                if not deep_search and source_name == "247Sports Composite":
                    tips.append("• Try `deep_search:True` to search all ~3000 ranked recruits")

                # Suggest alternative source
                if source_name == "On3/Rivals":
                    tips.append("• Try `/recruiting source 247sports` if On3 is blocked")
                else:
                    tips.append("• Try `/recruiting source on3` for transfer portal data")

                embed = discord.Embed(
                    title="❓ Recruit Not Found",
                    description=f"Couldn't find **{name}** in {source_name}.\n\n"
                               f"💡 **Tips:**\n" + '\n'.join(tips),
                    color=Colors.WARNING
                )
                embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
                # Send as followup (we deferred at start, so this will be public)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /recruiting player: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error looking up recruit: {str(e)}")

    @recruiting_group.command(name="top", description="Get top recruits by position or state")
    @app_commands.describe(
        position="Filter by position (QB, WR, RB, etc.)",
        state="Filter by state (TX, CA, FL, etc.)",
        year="Recruiting class year (default: current)",
        top="Number of recruits to show (default: 15)"
    )
    @app_commands.choices(position=[
        app_commands.Choice(name="QB - Quarterback", value="QB"),
        app_commands.Choice(name="RB - Running Back", value="RB"),
        app_commands.Choice(name="WR - Wide Receiver", value="WR"),
        app_commands.Choice(name="TE - Tight End", value="TE"),
        app_commands.Choice(name="OT - Offensive Tackle", value="OT"),
        app_commands.Choice(name="EDGE - Edge Rusher", value="EDGE"),
        app_commands.Choice(name="DL - Defensive Line", value="DL"),
        app_commands.Choice(name="LB - Linebacker", value="LB"),
        app_commands.Choice(name="CB - Cornerback", value="CB"),
        app_commands.Choice(name="S - Safety", value="S"),
    ])
    async def top(
        self,
        interaction: discord.Interaction,
        position: Optional[str] = None,
        state: Optional[str] = None,
        year: Optional[int] = None,
        top: Optional[int] = 15
    ):
        """Get top recruits with optional filters"""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning("⚠️ /recruiting top interaction expired")
            return

        if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING, server_config):
            return

        try:
            if top and (top < 1 or top > 50):
                await interaction.followup.send("❌ 'top' must be between 1 and 50", ephemeral=True)
                return

            guild_id = interaction.guild.id if interaction.guild else 0
            scraper, source_name = get_recruiting_scraper(guild_id)

            actual_year = year or scraper._get_current_recruiting_year()
            logger.info(f"🔍 /recruiting top via {source_name}: pos={position}, state={state}, year={actual_year}")

            recruits = await scraper.get_top_recruits(
                year=actual_year,
                position=position,
                state=state,
                limit=top or 15
            )

            if recruits:
                title_parts = ["⭐ Top"]
                if top:
                    title_parts.append(str(top))
                if position:
                    title_parts.append(position)
                title_parts.append("Recruits")
                if state:
                    title_parts.append(f"from {state.upper()}")
                title_parts.append(f"({actual_year})")

                embed = discord.Embed(
                    title=' '.join(title_parts),
                    description=scraper.format_top_recruits(recruits, ""),
                    color=Colors.RECRUITING
                )
                embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ Couldn't find recruits matching your criteria. Try different filters!",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"❌ Error in /recruiting top: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error getting recruits: {str(e)}", ephemeral=True)

    @recruiting_group.command(name="class", description="Get a team's recruiting class ranking")
    @app_commands.describe(
        team="Team name (e.g., 'Georgia', 'Ohio State')",
        year="Recruiting class year (default: current)"
    )
    async def class_cmd(
        self,
        interaction: discord.Interaction,
        team: str,
        year: Optional[int] = None
    ):
        """Get a team's recruiting class details"""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning(f"⚠️ /recruiting class interaction expired for {team}")
            return

        if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING, server_config):
            return

        try:
            guild_id = interaction.guild.id if interaction.guild else 0
            scraper, source_name = get_recruiting_scraper(guild_id)

            actual_year = year or scraper._get_current_recruiting_year()
            logger.info(f"🔍 /recruiting class via {source_name}: {team} ({actual_year})")

            team_data = await scraper.get_team_recruiting_class(team, actual_year)

            if team_data:
                embed = discord.Embed(
                    title=f"📋 {team_data.get('team', team)} Recruiting Class",
                    description=scraper.format_team_class(team_data),
                    color=Colors.RECRUITING
                )
                embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ Couldn't find recruiting class for **{team}** ({actual_year}).\n"
                    f"💡 Try the full school name (e.g., 'Ohio State' not 'OSU')",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"❌ Error in /recruiting class: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error getting class: {str(e)}", ephemeral=True)

    @recruiting_group.command(name="commits", description="List all committed recruits for a team")
    @app_commands.describe(
        team="Team name (e.g., 'Washington', 'Ohio State')",
        year="Recruiting class year (default: current)",
        show="Number of commits to show (default: 30, max: 50)"
    )
    async def commits(
        self,
        interaction: discord.Interaction,
        team: str,
        year: Optional[int] = None,
        show: Optional[int] = 30
    ):
        """Get list of committed recruits for a team"""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning(f"⚠️ /recruiting commits interaction expired for {team}")
            return

        if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING, server_config):
            return

        try:
            guild_id = interaction.guild.id if interaction.guild else 0
            scraper, source_name = get_recruiting_scraper(guild_id)

            # Only On3 scraper has team commits
            if source_name != "On3/Rivals":
                await interaction.followup.send(
                    f"❌ Team commits list is only available with **On3/Rivals** data source.\n"
                    f"💡 Switch with `/recruiting source on3`",
                    ephemeral=True
                )
                return

            actual_year = year or scraper._get_current_recruiting_year()
            logger.info(f"🔍 /recruiting commits: {team} ({actual_year})")

            commits_data = await scraper.get_team_commits(team, actual_year)

            if commits_data and commits_data.get('commits'):
                embed = discord.Embed(
                    title=f"🏈 {commits_data.get('team', team)} Commits ({actual_year})",
                    description=scraper.format_team_commits(commits_data, limit=show),
                    color=Colors.RECRUITING
                )
                embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ Couldn't find commits for **{team}** ({actual_year}).\n"
                    f"💡 Try the full school name (e.g., 'Ohio State' not 'OSU')",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"❌ Error in /recruiting commits: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error getting commits: {str(e)}", ephemeral=True)

    @recruiting_group.command(name="rankings", description="Get top team recruiting class rankings")
    @app_commands.describe(
        year="Recruiting class year (default: current)",
        top="Number of teams to show (default: 25)"
    )
    async def rankings(
        self,
        interaction: discord.Interaction,
        year: Optional[int] = None,
        top: Optional[int] = 25
    ):
        """Get top team recruiting class rankings"""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning("⚠️ /recruiting rankings interaction expired")
            return

        if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING, server_config):
            return

        try:
            if top and (top < 1 or top > 50):
                await interaction.followup.send("❌ 'top' must be between 1 and 50", ephemeral=True)
                return

            guild_id = interaction.guild.id if interaction.guild else 0
            scraper, source_name = get_recruiting_scraper(guild_id)

            actual_year = year or scraper._get_current_recruiting_year()
            logger.info(f"🔍 /recruiting rankings via {source_name}: year={actual_year}, top={top}")

            # Check cache first
            cache_key = f"rankings_{source_name}_{actual_year}_{top}"
            cached_teams = self.cache.get(cache_key)

            if cached_teams:
                logger.info(f"💾 Cache hit for recruiting rankings: {cache_key}")
                teams = cached_teams
            else:
                logger.info(f"🔍 Cache miss for recruiting rankings: {cache_key}")
                teams = await scraper.get_team_rankings(actual_year, top or 25)

                # Cache for 24 hours (rankings don't change often)
                if teams:
                    self.cache.set(cache_key, teams, ttl=86400)

            if teams:
                lines = [f"**Top {len(teams)} Recruiting Classes ({actual_year})**", ""]
                for team_data in teams:
                    rank = team_data.get('rank', '?')
                    name = team_data.get('team', 'Unknown')
                    commits = team_data.get('total_commits', '?')
                    points = team_data.get('points', 0)
                    points_str = f" ({points:.1f} pts)" if points else ""
                    lines.append(f"`{rank:2d}.` **{name}** - {commits} commits{points_str}")

                embed = discord.Embed(
                    title=f"🏆 Team Recruiting Rankings ({actual_year})",
                    description='\n'.join(lines),
                    color=Colors.RECRUITING
                )
                embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"❌ Couldn't load team rankings for {actual_year}",
                    ephemeral=True
                )

        except Exception as e:
            logger.error(f"❌ Error in /recruiting rankings: {e}", exc_info=True)

    @recruiting_group.command(name="portal", description="Look up a transfer portal player (recruiting + college stats)")
    @app_commands.describe(
        name="Player name (e.g., 'John Smith')",
        team="Previous/current team to help find the right player"
    )
    async def portal(
        self,
        interaction: discord.Interaction,
        name: str,
        team: Optional[str] = None
    ):
        """Look up a transfer portal player - combines recruiting data with college stats"""
        try:
            await interaction.response.defer()
        except discord.errors.NotFound:
            logger.warning(f"⚠️ /recruiting portal interaction expired for {name}")
            return

        if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING, server_config):
            return

        try:
            logger.info(f"🔄 Portal lookup: {name}" + (f" ({team})" if team else ""))

            # Get recruiting data from On3
            recruit_data = None
            on3_name = None
            try:
                recruit_data = await on3_scraper.search_recruit(name)
                if recruit_data:
                    on3_name = recruit_data.get('name')
            except Exception as e:
                logger.warning(f"⚠️ On3 lookup failed for {name}: {e}")

            # Get college stats from CFB Data
            college_stats = None
            cfb_name = None
            try:
                college_stats = await cfb_data.get_full_player_info(name, team)
                if college_stats:
                    cfb_name = college_stats.get('name')
            except Exception as e:
                logger.warning(f"⚠️ CFB Data lookup failed for {name}: {e}")

            # Cross-reference names
            if recruit_data and not college_stats and on3_name and on3_name.lower() != name.lower():
                try:
                    college_stats = await cfb_data.get_full_player_info(on3_name, team)
                except Exception as e:
                    logger.debug(f"Cross-reference CFB lookup failed: {e}")

            # Fallback: last name only search
            if recruit_data and not college_stats:
                name_parts = (on3_name or name).split()
                if len(name_parts) >= 2:
                    last_name = name_parts[-1]
                    on3_pos = recruit_data.get('position', '').upper()
                    try:
                        players = await cfb_data.search_player(last_name, team)
                        if players and on3_pos:
                            pos_groups = {
                                'RB': ['RB', 'HB', 'FB'], 'WR': ['WR'], 'QB': ['QB'], 'TE': ['TE'],
                                'OT': ['OT', 'OL', 'T'], 'OG': ['OG', 'OL', 'G'],
                                'DL': ['DL', 'DE', 'DT', 'NT'], 'DE': ['DE', 'DL', 'EDGE'],
                                'LB': ['LB', 'ILB', 'OLB'], 'CB': ['CB', 'DB'], 'S': ['S', 'SS', 'FS', 'DB'],
                            }
                            valid_pos = pos_groups.get(on3_pos, [on3_pos])
                            for p in players:
                                cfb_pos = (p.get('position') or '').upper()
                                if cfb_pos in valid_pos or on3_pos in cfb_pos:
                                    college_stats = await cfb_data.get_full_player_info(p.get('name'), p.get('team'))
                                    break
                        elif players:
                            college_stats = await cfb_data.get_full_player_info(players[0].get('name'), players[0].get('team'))
                    except Exception as e:
                        logger.debug(f"Last name CFB lookup failed: {e}")

            # Cross-reference: CFB name -> On3
            if college_stats and not recruit_data and cfb_name and cfb_name.lower() != name.lower():
                try:
                    recruit_data = await on3_scraper.search_recruit(cfb_name)
                except Exception as e:
                    logger.debug(f"Cross-reference On3 lookup failed: {e}")

            # Not found
            if not recruit_data and not college_stats:
                embed = discord.Embed(
                    title="❓ Portal Player Not Found",
                    description=f"Couldn't find **{name}** in transfer portal data.\n\n"
                               f"💡 **Tips:**\n"
                               f"• Check the spelling\n"
                               f"• Try their nickname (e.g., 'Hollywood Smothers')\n"
                               f"• Add their team: `/recruiting player name:{name}`\n"
                               f"• Try `/cfb player` for college stats only",
                    color=Colors.WARNING
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

            # Build response
            embed = discord.Embed(
                title=f"🔄 Transfer Portal: {name}",
                color=Colors.RECRUITING
            )

            if recruit_data and recruit_data.get('image_url'):
                embed.set_thumbnail(url=recruit_data['image_url'])

            # Recruiting section
            if recruit_data:
                recruit_lines = []
                stars = recruit_data.get('stars', 0)
                star_display = '⭐' * stars if stars else 'Unranked'
                rating = recruit_data.get('rating')
                if rating:
                    recruit_lines.append(f"**Rating:** {rating} ({star_display})")

                ranks = []
                if recruit_data.get('national_rank'):
                    ranks.append(f"#{recruit_data['national_rank']} Nationally")
                if recruit_data.get('position_rank'):
                    ranks.append(f"#{recruit_data['position_rank']} {recruit_data.get('position', '')}")
                if ranks:
                    recruit_lines.append(f"**Rank:** {' | '.join(ranks)}")

                pos = recruit_data.get('position', '')
                if pos:
                    h = recruit_data.get('height', '')
                    w = recruit_data.get('weight', '')
                    phys = f" | {h} | {w}lbs" if h and w else ""
                    recruit_lines.append(f"**Position:** {pos}{phys}")

                if recruit_data.get('committed_to'):
                    recruit_lines.append(f"**Committed to:** {recruit_data['committed_to']} ✅")

                predictions = recruit_data.get('top_predictions', [])
                if predictions:
                    pred_str = ", ".join([f"{p['team']} ({p.get('prediction', '?')})" for p in predictions[:3]])
                    recruit_lines.append(f"**Predictions:** {pred_str}")

                offers = recruit_data.get('offers', [])
                if offers:
                    recruit_lines.append(f"**Offers:** {len(offers)} schools")

                embed.add_field(
                    name="📊 Recruiting Profile",
                    value='\n'.join(recruit_lines) if recruit_lines else "No recruiting data",
                    inline=False
                )

            # College stats section
            if college_stats:
                stats_lines = []
                team_name = college_stats.get('team', '')
                jersey = college_stats.get('jersey', '')
                if team_name:
                    jersey_str = f" #{jersey}" if jersey else ""
                    stats_lines.append(f"**Previous School:** {team_name}{jersey_str}")

                stats = college_stats.get('stats', {})
                if stats:
                    years = sorted(stats.keys(), reverse=True)
                    if years:
                        recent_year = years[0]
                        year_stats = stats[recent_year]
                        stats_lines.append(f"**{recent_year} Stats:**")

                        passing = year_stats.get('passing', {})
                        if passing.get('YDS'):
                            stats_lines.append(f"  🎯 {passing.get('YDS', 0)} YDS | {passing.get('TD', 0)} TD | {passing.get('INT', 0)} INT")

                        rushing = year_stats.get('rushing', {})
                        if rushing.get('YDS'):
                            stats_lines.append(f"  🏃 {rushing.get('CAR', 0)} CAR | {rushing.get('YDS', 0)} YDS | {rushing.get('TD', 0)} TD")

                        receiving = year_stats.get('receiving', {})
                        if receiving.get('YDS'):
                            stats_lines.append(f"  🎯 {receiving.get('REC', 0)} REC | {receiving.get('YDS', 0)} YDS | {receiving.get('TD', 0)} TD")

                        defense = year_stats.get('defense', {})
                        if defense.get('TOT') or defense.get('SOLO'):
                            stats_lines.append(f"  🛡️ {defense.get('TOT', defense.get('SOLO', 0))} TKL | {defense.get('TFL', 0)} TFL | {defense.get('SACKS', 0)} Sacks")

                embed.add_field(
                    name="🏈 College Stats",
                    value='\n'.join(stats_lines) if stats_lines else "No college stats found",
                    inline=False
                )

            # Profile link
            if recruit_data and recruit_data.get('profile_url'):
                embed.add_field(
                    name="🔗 Links",
                    value=f"[On3/Rivals Profile]({recruit_data['profile_url']})",
                    inline=False
                )

            embed.set_footer(text="💡 Tip: /recruiting player now does the same thing!")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in /recruiting portal: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error looking up portal player: {str(e)}", ephemeral=True)

    @recruiting_group.command(name="source", description="Set the recruiting data source")
    @app_commands.describe(source="Which recruiting data source to use")
    @app_commands.choices(source=[
        app_commands.Choice(name="On3/Rivals (default) - Server-side rendered, reliable", value="on3"),
        app_commands.Choice(name="247Sports Composite - Legacy, more data but slower", value="247"),
    ])
    async def source(
        self,
        interaction: discord.Interaction,
        source: Optional[str] = None
    ):
        """Set or view the recruiting data source"""
        if not await check_module_enabled(interaction, FeatureModule.RECRUITING, server_config):
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ This command only works in servers!", ephemeral=True)
            return

        guild_id = interaction.guild.id

        # View current source
        if source is None:
            current_source = server_config.get_recruiting_source(guild_id)
            source_name = "On3/Rivals" if current_source == RecruitingSource.ON3 else "247Sports Composite"

            embed = discord.Embed(
                title="⭐ Recruiting Data Source",
                description=f"Current source: **{source_name}**",
                color=Colors.PRIMARY
            )
            embed.add_field(
                name="Available Sources",
                value=(
                    "• **On3/Rivals** (`on3`) - Default, server-side rendered, fast\n"
                    "• **247Sports** (`247`) - Composite rankings, more data, slower"
                ),
                inline=False
            )
            embed.add_field(
                name="Change Source",
                value="`/recruiting source on3` or `/recruiting source 247`",
                inline=False
            )
            embed.set_footer(text=Footers.CONFIG)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check admin permission
        is_admin = interaction.user.guild_permissions.administrator
        if self.admin_manager:
            is_admin = is_admin or self.admin_manager.is_admin(interaction.user, interaction)

        if not is_admin:
            await interaction.response.send_message(
                "❌ Only server admins can change the recruiting source!",
                ephemeral=True
            )
            return

        # Set the source
        if source not in [RecruitingSource.ON3, RecruitingSource.SPORTS247]:
            await interaction.response.send_message(f"❌ Invalid source: {source}", ephemeral=True)
            return

        server_config.set_recruiting_source(guild_id, source)
        await server_config.save_to_discord()

        source_name = "On3/Rivals" if source == RecruitingSource.ON3 else "247Sports Composite"

        embed = discord.Embed(
            title="✅ Recruiting Source Updated!",
            description=f"Now using **{source_name}** for recruiting data.",
            color=Colors.SUCCESS
        )
        embed.add_field(
            name="What Changed",
            value=f"Commands like `/recruiting player`, `/recruiting top`, etc. will now pull data from {source_name}.",
            inline=False
        )
        embed.set_footer(text=Footers.CONFIG)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = RecruitingCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ RecruitingCog loaded")
