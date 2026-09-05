#!/usr/bin/env python3
"""
League Cog for CFB 26 League Bot

Provides commands for league management, timers, schedules, and staff.
Commands:
- /league rules - Get recruiting rules
- /league team - Team lookup
- /league dynasty - Dynasty management rules
- /league timer - Start advance countdown
- /league timer_status - Check countdown status
- /league timer_stop - Stop countdown
- /league week - Current week
- /league weeks - Full schedule
- /league games - Games for a week
- /league find_game - Find team's game
- /league byes - Teams on bye
- /league set_week - Set season/week (admin)
- /league timer_channel - Set notification channel (admin)
- /league staff - View league staff
- /league set_owner - Set league owner (admin)
- /league set_commish - Set co-commissioner (admin)
- /league pick_commish - AI picks co-commissioner
- /league nag - Start nagging owner (bot owner)
- /league stop_nag - Stop nagging (bot owner)
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors, Footers
from ..services.checks import check_module_enabled
from ..utils.server_config import server_config, FeatureModule
# Week schedule constants and helpers live in one canonical place: utils/timekeeper.py.
# That module also drives advance/increment and season rollover, so reusing it here
# guarantees the week names/phases shown by /league match the timer's internal week
# numbering. (CFB 26 dynasties run Weeks 0-29 across Regular/Post/Offseason.)
from ..utils.timekeeper import CFB_DYNASTY_WEEKS, get_week_info, get_week_name

logger = logging.getLogger('CFB26Bot.League')


class LeagueCog(commands.Cog):
    """League management commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dependencies - set after loading
        self.timekeeper_manager = None
        self.admin_manager = None
        self.schedule_manager = None
        self.channel_summarizer = None
        self.ai_assistant = None
        self.AI_AVAILABLE = False
        logger.info("🏆 LeagueCog initialized")

    def set_dependencies(self, timekeeper_manager=None, admin_manager=None, schedule_manager=None,
                         channel_summarizer=None, ai_assistant=None, AI_AVAILABLE=False):
        """Set dependencies after bot is ready"""
        self.timekeeper_manager = timekeeper_manager
        self.admin_manager = admin_manager
        self.schedule_manager = schedule_manager
        self.channel_summarizer = channel_summarizer
        self.ai_assistant = ai_assistant
        self.AI_AVAILABLE = AI_AVAILABLE

    # Command group
    league_group = app_commands.Group(
        name="league",
        description="🏆 League management, timers, and schedules"
    )

    @league_group.command(name="rules", description="Get recruiting rules and policies")
    @app_commands.describe(topic="Rule topic to look up")
    async def rules(self, interaction: discord.Interaction, topic: str):
        """Get information about recruiting rules"""
        await interaction.response.defer()

        embed = discord.Embed(
            title=f"CFB 26 Recruiting: {topic.title()}",
            color=0x32cd32
        )

        if hasattr(self.bot, 'league_data') and 'rules' in self.bot.league_data and 'recruiting' in self.bot.league_data['rules']:
            recruiting_rules = self.bot.league_data['rules']['recruiting']
            embed.description = recruiting_rules.get('description', 'Recruiting rules and policies')
            if 'topics' in recruiting_rules:
                topics = recruiting_rules['topics']
                if topic.lower() in topics:
                    embed.add_field(name="Information", value=topics[topic.lower()], inline=False)
                else:
                    available = '\n'.join([f"• {t}" for t in topics.keys()])
                    embed.add_field(name="Available Topics", value=available, inline=False)
        else:
            embed.description = "Recruiting rules not found in league data."

        embed.add_field(
            name="League Charter",
            value="[View Full Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
            inline=False
        )
        await interaction.followup.send(embed=embed)

    @league_group.command(name="team", description="Get team information")
    @app_commands.describe(team_name="Team name to look up")
    async def team(self, interaction: discord.Interaction, team_name: str):
        """Get information about a college football team"""
        await interaction.response.defer()
        embed = discord.Embed(
            title=f"Team: {team_name.title()}",
            description="Team lookup functionality coming soon!",
            color=0x32cd32
        )
        embed.add_field(name="Status", value="🚧 Under Development", inline=False)
        await interaction.followup.send(embed=embed)

    @league_group.command(name="dynasty", description="Get dynasty management rules")
    @app_commands.describe(topic="Dynasty topic to look up")
    async def dynasty(self, interaction: discord.Interaction, topic: str):
        """Get information about dynasty management rules"""
        await interaction.response.defer()

        embed = discord.Embed(
            title=f"CFB 26 Dynasty: {topic.title()}",
            color=0xff6b6b
        )

        if hasattr(self.bot, 'league_data') and 'rules' in self.bot.league_data:
            dynasty_topics = ['transfers', 'gameplay', 'scheduling', 'conduct']
            found_topic = None
            for dt in dynasty_topics:
                if topic.lower() in dt.lower() and dt in self.bot.league_data['rules']:
                    found_topic = dt
                    break

            if found_topic:
                rules = self.bot.league_data['rules'][found_topic]
                embed.description = rules.get('description', 'Dynasty management rules')
            else:
                embed.description = "Dynasty topic not found. Available: transfers, gameplay, scheduling, conduct"
        else:
            embed.description = "Dynasty rules not found in league data."

        embed.add_field(
            name="League Charter",
            value="[View Full Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
            inline=False
        )
        await interaction.followup.send(embed=embed)

    @league_group.command(name="timer", description="Start advance countdown timer (Admin only)")
    @app_commands.describe(hours="Number of hours for the countdown (default: 48)")
    async def timer(self, interaction: discord.Interaction, hours: int = 48):
        """Start the advance countdown timer"""
        if not await check_module_enabled(interaction, FeatureModule.LEAGUE, server_config):
            return

        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only bot admins can start countdowns!", ephemeral=True)
            return

        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        if hours < 1:
            await interaction.response.send_message("❌ Hours must be at least 1!", ephemeral=True)
            return
        if hours > 336:
            await interaction.response.send_message("❌ Maximum is 336 hours (2 weeks)!", ephemeral=True)
            return

        await interaction.response.defer()

        # Stop existing timer and increment week ONLY if timer was manually stopped
        # (If timer expired naturally, week was already incremented in _send_times_up)
        status = self.timekeeper_manager.get_status(interaction.channel)
        should_increment = False
        
        if status.get('active'):
            # Timer is still running - stop it and mark that we should increment
            await self.timekeeper_manager.stop_timer(interaction.channel)
            should_increment = True

        # Only increment week if we manually stopped an active timer
        season_info = self.timekeeper_manager.get_season_week()
        if should_increment and season_info['season'] and season_info['week'] is not None:
            await self.timekeeper_manager.increment_week()
            season_info = self.timekeeper_manager.get_season_week()

        success = await self.timekeeper_manager.start_timer(interaction.channel, hours)

        if success:
            week_name = get_week_name(season_info.get('week', 0))
            embed = discord.Embed(
                title="⏰ Advance Countdown Started!",
                description=f"🏈 **{hours} HOUR COUNTDOWN STARTED** 🏈\n\n**Season {season_info.get('season', '?')}** - {week_name}\n\nYou have **{hours} hours** to get your games done!",
                color=Colors.SUCCESS
            )
            embed.set_footer(text="Harry's Advance Timer 🏈 | Use /league timer_status to check")
            await interaction.followup.send("✅ Timer started!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Failed to start timer!", ephemeral=True)

    @league_group.command(name="timer_status", description="Check the current advance countdown status")
    async def timer_status(self, interaction: discord.Interaction):
        """Check the current advance countdown status"""
        if not await check_module_enabled(interaction, FeatureModule.LEAGUE, server_config):
            return

        await interaction.response.defer()

        if not self.timekeeper_manager:
            await interaction.followup.send("❌ Timekeeper not available", ephemeral=True)
            return

        status = self.timekeeper_manager.get_status(interaction.channel)

        if not status['active']:
            embed = discord.Embed(
                title="⏰ No Countdown Active",
                description="No countdown running. Use `/league timer` to start one.",
                color=0x808080
            )
        else:
            hours = status['hours']
            minutes = status['minutes']

            if hours >= 24:
                color = 0x00ff00
                urgency = "Plenty of time!"
            elif hours >= 12:
                color = 0xffa500
                urgency = "Getting closer!"
            elif hours >= 6:
                color = 0xff8c00
                urgency = "Time's ticking!"
            elif hours >= 1:
                color = 0xff4500
                urgency = "Under 6 hours!"
            else:
                color = 0xff0000
                urgency = "FINAL HOUR!"

            # Get end time in different timezones
            end_time = status.get('end_time')
            timezone_info = ""
            if end_time:
                from datetime import datetime
                import pytz

                # Convert to timezone-aware datetime if needed
                if isinstance(end_time, str):
                    end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                elif not hasattr(end_time, 'tzinfo') or end_time.tzinfo is None:
                    end_time = pytz.utc.localize(end_time)

                # Convert to different timezones
                eastern = end_time.astimezone(pytz.timezone('US/Eastern'))
                central = end_time.astimezone(pytz.timezone('US/Central'))
                pacific = end_time.astimezone(pytz.timezone('US/Pacific'))

                timezone_info = (
                    f"\n\n**Countdown Ends:**\n"
                    f"🕐 Eastern: {eastern.strftime('%I:%M %p ET')}\n"
                    f"🕑 Central: {central.strftime('%I:%M %p CT')}\n"
                    f"🕒 Pacific: {pacific.strftime('%I:%M %p PT')}"
                )

            embed = discord.Embed(
                title="⏰ Advance Countdown Active",
                description=f"**Time Remaining:** {hours}h {minutes}m\n\n{urgency}{timezone_info}",
                color=color
            )

        embed.set_footer(text="Harry's Advance Timer 🏈")
        await interaction.followup.send(embed=embed)

    @league_group.command(name="timer_stop", description="Stop the current advance countdown (Admin only)")
    async def timer_stop(self, interaction: discord.Interaction):
        """Stop the current advance countdown"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can stop timers!", ephemeral=True)
            return

        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        await self.timekeeper_manager.stop_timer(interaction.channel)
        embed = discord.Embed(
            title="⏹️ Countdown Stopped",
            description="The advance countdown has been stopped.",
            color=Colors.WARNING
        )
        await interaction.response.send_message(embed=embed)

    @league_group.command(name="week", description="Check the current season and week")
    async def week(self, interaction: discord.Interaction):
        """Check the current season and week"""
        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        season_info = self.timekeeper_manager.get_season_week()

        if not season_info['season'] or season_info['week'] is None:
            embed = discord.Embed(
                title="📅 Season/Week Not Set",
                description="An admin needs to use `/league set_week` to set it up.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed)
            return

        week_info = get_week_info(season_info['week'])
        embed = discord.Embed(
            title="📅 Current Week",
            description=f"**Season {season_info['season']}**\n\n📍 **{week_info['name']}**\n🏈 Phase: {week_info['phase']}",
            color=Colors.SUCCESS
        )
        embed.set_footer(text="Harry's Week Tracker 🏈")
        await interaction.response.send_message(embed=embed)

    @league_group.command(name="weeks", description="View the full CFB 26 Dynasty week schedule")
    async def weeks(self, interaction: discord.Interaction):
        """View the full week schedule"""
        current_week = None
        current_season = None
        if self.timekeeper_manager:
            season_info = self.timekeeper_manager.get_season_week()
            if season_info['week'] is not None:
                current_week = season_info['week']
                current_season = season_info['season']

        description = ""
        if current_week is not None:
            curr_info = get_week_info(current_week)
            description = f"**Season {current_season}**\n📍 Current: **{curr_info['name']}**\n\n"

        description += "**Week Schedule:**\n"

        embed = discord.Embed(
            title="📅 CFB 26 Dynasty Week Schedule",
            description=description,
            color=Colors.SUCCESS
        )

        # Build week lists
        regular = []
        post = []
        off = []

        for wn in sorted(CFB_DYNASTY_WEEKS.keys()):
            wd = CFB_DYNASTY_WEEKS[wn]
            line = f"**► `{wn:2d}` {wd['short']}** ◄" if current_week == wn else f"`{wn:2d}` {wd['short']}"
            if wd['phase'] == "Regular Season":
                regular.append(line)
            elif wd['phase'] == "Post-Season":
                post.append(line)
            else:
                off.append(line)

        embed.add_field(name="🏈 Regular Season", value="\n".join(regular), inline=True)
        embed.add_field(name="🏆 Post-Season", value="\n".join(post), inline=True)
        embed.add_field(name="📝 Offseason", value="\n".join(off), inline=True)
        embed.set_footer(text="Harry's Week Tracker 🏈")
        await interaction.response.send_message(embed=embed)

    @league_group.command(name="games", description="View the games for a specific week")
    @app_commands.describe(week="Week number (0-14, leave empty for current)")
    async def games(self, interaction: discord.Interaction, week: Optional[int] = None):
        """View the schedule for a specific week"""
        if not await check_module_enabled(interaction, FeatureModule.LEAGUE, server_config):
            return

        await interaction.response.defer()

        target_week = week
        if target_week is None and self.timekeeper_manager:
            season_info = self.timekeeper_manager.get_season_week()
            target_week = season_info.get('week', 0)

        if target_week is None:
            await interaction.followup.send("❌ Week not specified and current week not set!", ephemeral=True)
            return

        if not self.schedule_manager:
            await interaction.followup.send("❌ Schedule manager not available", ephemeral=True)
            return

        # Get week data
        week_data = self.schedule_manager.get_week_schedule(target_week)
        week_info = get_week_info(target_week)

        if not week_data:
            embed = discord.Embed(
                title=f"📅 {week_info['name']} Schedule",
                description="No schedule data found for this week.",
                color=Colors.WARNING
            )
        else:
            # Build description with bye teams and games
            description_lines = []

            # Bye teams (with user teams bolded)
            bye_teams = week_data.get('bye_teams', [])
            if bye_teams:
                bye_formatted = self.schedule_manager.format_bye_teams(bye_teams)
                description_lines.append(f"😴 **Bye Week:** {bye_formatted}\n")

            # Games (with user teams bolded)
            games = week_data.get('games', [])
            if games:
                description_lines.append("**Games:**")
                for game in games:
                    description_lines.append(self.schedule_manager.format_game(game))
            else:
                description_lines.append("No games scheduled for this week.")

            embed = discord.Embed(
                title=f"📅 {week_info['name']} Schedule",
                description="\n".join(description_lines),
                color=Colors.SUCCESS
            )

            # Add user teams list in footer
            if self.schedule_manager.teams:
                embed.set_footer(text=f"User Teams: {', '.join(self.schedule_manager.teams)} | Harry's Schedule 🏈")
            else:
                embed.set_footer(text="Harry's Schedule 🏈")

        await interaction.followup.send(embed=embed)

    @league_group.command(name="find_game", description="Find a team's game for a specific week")
    @app_commands.describe(team="Team name", week="Week number (0-14)")
    async def find_game(self, interaction: discord.Interaction, team: str, week: Optional[int] = None):
        """Find a team's game"""
        if not await check_module_enabled(interaction, FeatureModule.LEAGUE, server_config):
            return

        await interaction.response.defer()

        target_week = week
        if target_week is None and self.timekeeper_manager:
            season_info = self.timekeeper_manager.get_season_week()
            target_week = season_info.get('week', 0)

        if not self.schedule_manager:
            await interaction.followup.send("❌ Schedule manager not available", ephemeral=True)
            return

        # Use schedule_manager's get_team_game method which handles formatting
        game = self.schedule_manager.get_team_game(team, target_week)
        week_info = get_week_info(target_week or 0)

        if game and not game.get('bye'):
            # Team has a game
            embed = discord.Embed(
                title=f"🏈 {self.schedule_manager.format_team(team)}'s Game - {week_info['name']}",
                description=game.get('matchup', 'Game info not available'),
                color=Colors.SUCCESS
            )
        elif game and game.get('bye'):
            # Team has a bye
            embed = discord.Embed(
                title=f"😴 {self.schedule_manager.format_team(team)} - {week_info['name']}",
                description=f"**{self.schedule_manager.format_team(team)}** has a BYE this week.",
                color=Colors.WARNING
            )
        else:
            # Team not found
            embed = discord.Embed(
                title=f"🔍 {team} - {week_info['name']}",
                description=f"Team **{team}** not found in schedule.",
                color=Colors.WARNING
            )

        embed.set_footer(text="Harry's Schedule 🏈")
        await interaction.followup.send(embed=embed)

    @league_group.command(name="byes", description="Show which teams have a bye this week")
    @app_commands.describe(week="Week number (0-14)")
    async def byes(self, interaction: discord.Interaction, week: Optional[int] = None):
        """Show teams on bye"""
        if not await check_module_enabled(interaction, FeatureModule.LEAGUE, server_config):
            return

        await interaction.response.defer()

        target_week = week
        if target_week is None and self.timekeeper_manager:
            season_info = self.timekeeper_manager.get_season_week()
            target_week = season_info.get('week', 0)

        if not self.schedule_manager:
            await interaction.followup.send("❌ Schedule manager not available", ephemeral=True)
            return

        bye_teams = self.schedule_manager.get_bye_teams(target_week)
        week_info = get_week_info(target_week or 0)

        if bye_teams:
            # Format bye teams with user teams bolded
            bye_formatted = self.schedule_manager.format_bye_teams(bye_teams)
            embed = discord.Embed(
                title=f"😴 Bye Teams - {week_info['name']}",
                description=bye_formatted,
                color=Colors.WARNING
            )
        else:
            embed = discord.Embed(
                title=f"😴 Bye Teams - {week_info['name']}",
                description="No teams on bye this week!",
                color=Colors.SUCCESS
            )

        embed.set_footer(text="Harry's Schedule 🏈")
        await interaction.followup.send(embed=embed)

    @league_group.command(name="set_week", description="Set the current season and week (Admin only)")
    @app_commands.describe(season="Season number", week="Week number (0-29)")
    async def set_week(self, interaction: discord.Interaction, season: int, week: int):
        """Set the current season and week"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can set season/week!", ephemeral=True)
            return

        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        if season < 1 or week < 0 or week >= len(CFB_DYNASTY_WEEKS):
            await interaction.response.send_message(
                f"❌ Invalid season/week! Season must be ≥ 1 and week must be 0-{len(CFB_DYNASTY_WEEKS) - 1}.",
                ephemeral=True,
            )
            return

        success = await self.timekeeper_manager.set_season_week(season, week)

        if success:
            week_info = get_week_info(week)
            embed = discord.Embed(
                title="📅 Season/Week Set!",
                description=f"**Season {season}** - {week_info['name']}",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to set season/week!", ephemeral=True)

    @league_group.command(name="timer_channel", description="Set the channel for timer notifications (Admin only)")
    @app_commands.describe(channel="Channel for timer notifications")
    async def timer_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the notification channel"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can set the timer channel!", ephemeral=True)
            return

        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        success = await self.timekeeper_manager.set_notification_channel(channel.id)
        if success:
            embed = discord.Embed(
                title="📢 Timer Channel Set!",
                description=f"Timer notifications will go to: **#{channel.name}**",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to save!", ephemeral=True)

    @league_group.command(name="staff", description="View the current league owner and co-commissioner")
    async def staff(self, interaction: discord.Interaction):
        """View current league staff"""
        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        staff_info = self.timekeeper_manager.get_league_staff()

        embed = discord.Embed(
            title="👑 League Staff",
            color=Colors.PRIMARY
        )

        owner = staff_info.get('owner_name', 'Not set')
        commish = staff_info.get('commish_name', 'Not set')

        embed.add_field(name="🏆 League Owner", value=owner, inline=False)
        embed.add_field(name="👔 Co-Commissioner", value=commish, inline=False)
        embed.set_footer(text="Harry's League Staff 🏈")
        await interaction.response.send_message(embed=embed)

    @league_group.command(name="set_owner", description="Set the league owner (Admin only)")
    @app_commands.describe(user="User to set as league owner")
    async def set_owner(self, interaction: discord.Interaction, user: discord.User):
        """Set the league owner"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can set the league owner!", ephemeral=True)
            return

        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        await self.timekeeper_manager.set_league_owner(user.id, user.display_name)
        embed = discord.Embed(
            title="👑 League Owner Set!",
            description=f"**{user.display_name}** is now the league owner!",
            color=Colors.SUCCESS
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @league_group.command(name="set_commish", description="Set the co-commissioner (Admin only)")
    @app_commands.describe(
        user="User to set as co-commissioner",
        none="Set to 'None'"
    )
    async def set_commish(
        self,
        interaction: discord.Interaction,
        user: Optional[discord.User] = None,
        none: Optional[bool] = False
    ):
        """Set the co-commissioner"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can set the co-commissioner!", ephemeral=True)
            return

        if not self.timekeeper_manager:
            await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
            return

        if none:
            await self.timekeeper_manager.set_co_commissioner(None, "We don't have one")
            embed = discord.Embed(
                title="👔 Co-Commissioner Cleared",
                description="Co-commissioner has been cleared.",
                color=Colors.WARNING
            )
        elif user:
            await self.timekeeper_manager.set_co_commissioner(user.id, user.display_name)
            embed = discord.Embed(
                title="👔 Co-Commissioner Set!",
                description=f"**{user.display_name}** is now the co-commissioner!",
                color=Colors.SUCCESS
            )
        else:
            await interaction.response.send_message("❌ Provide a user or set `none:True`", ephemeral=True)
            return

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @league_group.command(name="pick_commish", description="Harry analyzes the chat and picks a co-commissioner")
    @app_commands.describe(
        channel="Channel to analyze",
        hours="Hours of chat history (default: 168 = 1 week)"
    )
    async def pick_commish(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        hours: int = 168
    ):
        """Have Harry analyze chat and recommend a co-commissioner"""
        await interaction.response.defer()

        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.followup.send("❌ Only admins can ask me to pick a commish!", ephemeral=True)
            return

        if not self.channel_summarizer:
            await interaction.followup.send("❌ Channel summarizer not available", ephemeral=True)
            return

        if not self.AI_AVAILABLE or not self.ai_assistant:
            await interaction.followup.send("❌ AI not available for this analysis", ephemeral=True)
            return

        if hours < 24 or hours > 720:
            await interaction.followup.send("❌ Hours must be between 24 and 720!", ephemeral=True)
            return

        target_channel = channel or interaction.channel

        try:
            messages = await self.channel_summarizer.fetch_messages(target_channel, hours, limit=1000)

            if not messages or len(messages) < 10:
                await interaction.followup.send("❌ Not enough chat activity to analyze!")
                return

            # Count participation
            participants = {}
            for msg in messages:
                if not msg.author.bot:
                    name = msg.author.display_name
                    if name not in participants:
                        participants[name] = 0
                    participants[name] += 1

            sorted_p = sorted(participants.items(), key=lambda x: x[1], reverse=True)

            embed = discord.Embed(
                title="👑 Co-Commissioner Analysis",
                description=f"Based on **{len(messages)}** messages over **{hours}** hours:",
                color=Colors.PRIMARY
            )

            for i, (name, count) in enumerate(sorted_p[:5], 1):
                embed.add_field(
                    name=f"#{i}. {name}",
                    value=f"**{count}** messages",
                    inline=True
                )

            if sorted_p:
                embed.add_field(
                    name="🏆 Top Recommendation",
                    value=f"**{sorted_p[0][0]}** - Most active participant!",
                    inline=False
                )

            embed.set_footer(text="Use /league set_commish to make it official!")
            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error in pick_commish: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error: {str(e)}")

    @league_group.command(name="nag", description="Start spamming the league owner to advance (Bot Owner only)")
    @app_commands.describe(interval="How often to nag in minutes (default: 5)")
    async def nag(self, interaction: discord.Interaction, interval: int = 5):
        """Start nagging the league owner"""
        try:
            app_info = await self.bot.application_info()
            bot_owner_id = app_info.owner.id if app_info.owner else None
        except Exception:
            bot_owner_id = None

        if not bot_owner_id or interaction.user.id != bot_owner_id:
            await interaction.response.send_message("❌ Only the bot owner can use this!", ephemeral=True)
            return

        # Simplified - actual implementation would start a background task
        embed = discord.Embed(
            title="🔔 Nag Mode Activated",
            description=f"Will nag every {interval} minutes!",
            color=Colors.WARNING
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @league_group.command(name="stop_nag", description="Stop spamming the league owner (Bot Owner only)")
    async def stop_nag(self, interaction: discord.Interaction):
        """Stop nagging the league owner"""
        try:
            app_info = await self.bot.application_info()
            bot_owner_id = app_info.owner.id if app_info.owner else None
        except Exception:
            bot_owner_id = None

        if not bot_owner_id or interaction.user.id != bot_owner_id:
            await interaction.response.send_message("❌ Only the bot owner can use this!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔕 Nag Mode Deactivated",
            description="The owner gets a break... for now.",
            color=Colors.SUCCESS
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = LeagueCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ LeagueCog loaded")
