#!/usr/bin/env python3
"""
Schedule Manager for CFB 26 League Bot
Manages and queries the league schedule data
"""

import io
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('CFB26Bot.Schedule')

# Schedule data file location
SCHEDULE_FILE = Path(__file__).parent.parent.parent.parent / "data" / "schedule.json"

# Marker for the persisted schedule backup message in the bot-owner DM.
# The full schedule (~4KB) exceeds Discord's text-message limit, so it is
# stored as a JSON *attachment* on this message rather than inline text.
SCHEDULE_BACKUP_MARKER = "SCHEDULE_BACKUP"
SCHEDULE_BACKUP_FILENAME = "schedule_backup.json"


class ScheduleManager:
    """Manages league schedule data and queries"""

    def __init__(self):
        self.schedule_data: Dict = {}
        self.season: int = 1
        self.teams: List[str] = []
        self.bot = None  # set via set_bot() for Discord-backed persistence
        self._load_schedule()

    def set_bot(self, bot):
        """Set the bot instance (needed for Discord-backed persistence)."""
        self.bot = bot

    def _load_schedule(self) -> bool:
        """Load schedule data from JSON file"""
        try:
            if SCHEDULE_FILE.exists():
                with open(SCHEDULE_FILE, 'r') as f:
                    self.schedule_data = json.load(f)
                self.season = self.schedule_data.get('season', 1)
                self.teams = self.schedule_data.get('teams', [])
                logger.info(f"✅ Loaded schedule for Season {self.season} ({len(self.teams)} teams)")
                return True
            else:
                logger.warning(f"⚠️ Schedule file not found: {SCHEDULE_FILE}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to load schedule: {e}")
            return False

    def reload_schedule(self) -> bool:
        """Reload schedule data from file"""
        return self._load_schedule()

    # ==================== Discord-backed persistence ====================
    # The filesystem is ephemeral on Render/Railway, so an uploaded schedule
    # is persisted as a JSON attachment in the bot-owner's DM and restored on
    # startup. The bundled data/schedule.json is the seed/fallback.

    async def _get_owner_dm(self):
        """Get the DM channel with the bot owner (for persistence)."""
        if not self.bot:
            return None
        try:
            app_info = await self.bot.application_info()
            owner = app_info.owner
            if not owner:
                return None
            return owner.dm_channel or await owner.create_dm()
        except Exception as e:
            logger.warning(f"⚠️ Could not open owner DM for schedule persistence: {e}")
            return None

    async def load_from_discord(self) -> bool:
        """Restore the schedule from the owner-DM backup attachment, if present.

        Falls back to whatever _load_schedule() already loaded from disk.
        """
        dm = await self._get_owner_dm()
        if not dm:
            return False
        try:
            async for message in dm.history(limit=50):
                if (message.author == self.bot.user
                        and message.content.startswith(SCHEDULE_BACKUP_MARKER)
                        and message.attachments):
                    raw = await message.attachments[0].read()
                    data = json.loads(raw.decode('utf-8'))
                    ok, err = self.validate_schedule(data)
                    if not ok:
                        logger.warning(f"⚠️ Ignoring invalid schedule backup: {err}")
                        return False
                    self.load_from_dict(data)
                    logger.info(
                        f"✅ Restored schedule from Discord backup "
                        f"(Season {self.season}, {len(self.schedule_data.get('schedule', {}))} weeks)"
                    )
                    return True
            logger.info("📅 No schedule backup in Discord; using bundled schedule.json")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to load schedule from Discord: {e}")
            return False

    async def save_to_discord(self) -> bool:
        """Persist the current schedule as a JSON attachment in the owner DM.

        Also writes the local file best-effort so the running session stays in
        sync (the file is lost on redeploy, which is why the DM backup exists).
        """
        # Best-effort local write for the live session
        try:
            SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SCHEDULE_FILE, 'w') as f:
                json.dump(self.schedule_data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Could not write local schedule file: {e}")

        dm = await self._get_owner_dm()
        if not dm:
            logger.error("❌ No owner DM available — schedule NOT persisted to Discord!")
            return False

        try:
            import discord  # lazy import (audioop_fix ordering handled by bot_main)

            payload = json.dumps(self.schedule_data).encode('utf-8')

            # Remove old backup message(s) to avoid duplicates
            async for message in dm.history(limit=50):
                if (message.author == self.bot.user
                        and message.content.startswith(SCHEDULE_BACKUP_MARKER)):
                    try:
                        await message.delete()
                    except Exception:
                        pass

            file = discord.File(io.BytesIO(payload), filename=SCHEDULE_BACKUP_FILENAME)
            await dm.send(content=f"{SCHEDULE_BACKUP_MARKER} (Season {self.season})", file=file)
            logger.info("✅ Schedule backed up to Discord (owner DM attachment)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to back up schedule to Discord: {e}")
            return False

    @staticmethod
    def validate_schedule(data) -> Tuple[bool, str]:
        """Validate an uploaded schedule dict. Returns (ok, error_message)."""
        if not isinstance(data, dict):
            return False, "Top level must be a JSON object."
        schedule = data.get('schedule')
        if not isinstance(schedule, dict) or not schedule:
            return False, "Missing or empty 'schedule' object."
        if 'teams' in data and not isinstance(data['teams'], list):
            return False, "'teams' must be a list."
        for wk, wd in schedule.items():
            if not str(wk).isdigit():
                return False, f"Week key '{wk}' must be a number (e.g. \"0\", \"1\")."
            if not isinstance(wd, dict):
                return False, f"Week '{wk}' must be an object."
            byes = wd.get('bye_teams', [])
            if not isinstance(byes, list):
                return False, f"Week '{wk}': 'bye_teams' must be a list."
            games = wd.get('games', [])
            if not isinstance(games, list):
                return False, f"Week '{wk}': 'games' must be a list."
            for g in games:
                if not isinstance(g, dict) or 'away' not in g or 'home' not in g:
                    return False, f"Week '{wk}': every game needs 'away' and 'home'."
        return True, ""

    def load_from_dict(self, data: Dict) -> None:
        """Replace the in-memory schedule from a validated dict."""
        self.schedule_data = data
        self.season = data.get('season', self.season)
        self.teams = data.get('teams', self.teams)

    def set_week_games(self, week: int, games: List[Dict], bye_teams: List[str]) -> None:
        """Set (or replace) a single week's games and byes in memory."""
        schedule = self.schedule_data.setdefault('schedule', {})
        schedule[str(week)] = {'bye_teams': bye_teams, 'games': games}

    def format_team(self, team_name: str) -> str:
        """Format a team name, bolding user-controlled teams"""
        if team_name in self.teams:
            return f"**{team_name}**"
        return team_name

    def format_game(self, game: Dict, emoji: str = "🏈") -> str:
        """Format a game matchup with user teams bolded"""
        away = self.format_team(game['away'])
        home = self.format_team(game['home'])
        return f"{emoji} {away} @ {home}"

    def format_bye_teams(self, bye_teams: List[str]) -> str:
        """Format bye teams list with user teams bolded"""
        return ", ".join([self.format_team(t) for t in bye_teams])

    def get_week_schedule(self, week: int) -> Optional[Dict]:
        """
        Get the schedule for a specific week.

        Args:
            week: Week number (0-13 for regular season)

        Returns:
            Dict with 'bye_teams' and 'games' lists, or None if not found
        """
        schedule = self.schedule_data.get('schedule', {})
        return schedule.get(str(week))

    def get_team_game(self, team: str, week: int) -> Optional[Dict]:
        """
        Get a specific team's game for a week.

        Args:
            team: Team name (case-insensitive)
            week: Week number

        Returns:
            Dict with game info including 'opponent', 'location' (home/away), or None if bye/not found
        """
        week_data = self.get_week_schedule(week)
        if not week_data:
            return None

        team_lower = team.lower()

        # Check if team has a bye
        bye_teams = [t.lower() for t in week_data.get('bye_teams', [])]
        if team_lower in bye_teams:
            return {'bye': True, 'team': team}

        # Find the game
        for game in week_data.get('games', []):
            if game['home'].lower() == team_lower:
                return {
                    'bye': False,
                    'team': team,
                    'opponent': game['away'],
                    'location': 'home',
                    'matchup': f"{self.format_team(game['away'])} @ {self.format_team(game['home'])}"
                }
            elif game['away'].lower() == team_lower:
                return {
                    'bye': False,
                    'team': team,
                    'opponent': game['home'],
                    'location': 'away',
                    'matchup': f"{self.format_team(game['away'])} @ {self.format_team(game['home'])}"
                }

        return None

    def get_bye_teams(self, week: int) -> List[str]:
        """Get list of teams on bye for a specific week"""
        week_data = self.get_week_schedule(week)
        if not week_data:
            return []
        return week_data.get('bye_teams', [])

    def get_all_games(self, week: int) -> List[Dict]:
        """Get all games for a specific week"""
        week_data = self.get_week_schedule(week)
        if not week_data:
            return []
        return week_data.get('games', [])

    def find_team(self, query: str) -> Optional[str]:
        """
        Find a team by partial name match.

        Args:
            query: Search query (case-insensitive)

        Returns:
            Full team name if found, None otherwise
        """
        query_lower = query.lower()

        # Try exact match first
        for team in self.teams:
            if team.lower() == query_lower:
                return team

        # Try partial match
        for team in self.teams:
            if query_lower in team.lower():
                return team

        # Try matching common abbreviations
        abbreviations = {
            'msu': 'Michigan St',
            'michigan state': 'Michigan St',
            'mich st': 'Michigan St',
            'nd': 'Notre Dame',
            'irish': 'Notre Dame',
            'huskers': 'Nebraska',
            'neb': 'Nebraska',
            'longhorns': 'Texas',
            'ut': 'Texas',
            'tigers': 'LSU',
            'rainbow warriors': 'Hawaii',
            'warriors': 'Hawaii',
        }

        if query_lower in abbreviations:
            return abbreviations[query_lower]

        return None

    def get_team_full_schedule(self, team: str) -> List[Dict]:
        """
        Get a team's full season schedule.

        Args:
            team: Team name

        Returns:
            List of game info for each week
        """
        schedule = []
        for week in range(14):  # Weeks 0-13
            game = self.get_team_game(team, week)
            if game:
                game['week'] = week
                schedule.append(game)
        return schedule

    def format_week_schedule(self, week: int) -> str:
        """
        Format the week's schedule as a readable string.

        Args:
            week: Week number

        Returns:
            Formatted string of the week's schedule
        """
        week_data = self.get_week_schedule(week)
        if not week_data:
            return f"No schedule data for Week {week}"

        lines = [f"**Week {week} Schedule:**\n"]

        # Bye teams (bold user teams)
        bye_teams = week_data.get('bye_teams', [])
        if bye_teams:
            lines.append(f"🛋️ **Bye Week:** {self.format_bye_teams(bye_teams)}\n")

        # Games (bold user teams)
        games = week_data.get('games', [])
        if games:
            lines.append("**Games:**")
            for game in games:
                lines.append(self.format_game(game, "•"))

        return "\n".join(lines)

    def get_schedule_context_for_ai(self) -> str:
        """
        Generate a context string about the schedule for the AI.

        Returns:
            String containing schedule information for AI context
        """
        context_lines = [
            f"League Schedule Information (Season {self.season}):",
            f"USER-CONTROLLED TEAMS (bold these in responses): {', '.join(self.teams)}",
            "NOTE: When listing matchups, **bold** any team from the user-controlled list above.",
            "",
            "Schedule by week:"
        ]

        schedule = self.schedule_data.get('schedule', {})
        for week_num in sorted(schedule.keys(), key=int):
            week_data = schedule[week_num]
            bye_teams = week_data.get('bye_teams', [])
            games = week_data.get('games', [])

            context_lines.append(f"\nWeek {week_num}:")
            if bye_teams:
                context_lines.append(f"  Bye: {', '.join(bye_teams)}")
            for game in games:
                context_lines.append(f"  {game['away']} at {game['home']}")

        return "\n".join(context_lines)


# Global instance
schedule_manager: Optional[ScheduleManager] = None


def get_schedule_manager() -> ScheduleManager:
    """Get or create the global schedule manager instance"""
    global schedule_manager
    if schedule_manager is None:
        schedule_manager = ScheduleManager()
    return schedule_manager
