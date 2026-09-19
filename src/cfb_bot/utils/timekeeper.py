#!/usr/bin/env python3
"""
Timekeeper Module for CFB 26 League Bot
Manages advance countdown timers with notifications
Includes persistence to survive restarts/deployments
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

import discord

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    # Fallback for older Python versions
    try:
        from backports.zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None

logger = logging.getLogger('CFB26Bot.Timekeeper')

# CFB 26 Dynasty Season Week Structure
# A full online-dynasty season is exactly 27 sequential advances, keyed by step number (1-27):
#   Preseason (1), Regular Season Weeks 0-14 (2-16), Postseason (17-22), Offseason (23-27).
# Advancing past step 27 rolls over to step 1 (Preseason) of the next season.
# "game_week" is the in-game week number used as the key in the league schedule JSON
# (only regular-season steps have one).
CFB_DYNASTY_WEEKS = {
    # Preseason (1)
    1: {"name": "Preseason", "short": "Preseason", "phase": "Preseason", "game_week": None, "actions": "Season begins", "notes": ""},
    # Regular Season (2-16) - Week 0 through Week 14
    **{
        step: {"name": f"Week {step - 2}", "short": f"Week {step - 2}", "phase": "Regular Season", "game_week": step - 2, "actions": "", "notes": ""}
        for step in range(2, 17)
    },
    # Postseason (17-22)
    17: {"name": "Conference Championship", "short": "Conf Champ", "phase": "Postseason", "game_week": None, "actions": "Play Championship Games", "notes": ""},
    18: {"name": "Bowl Week 1", "short": "Bowl Wk 1", "phase": "Postseason", "game_week": None, "actions": "Bowl Games", "notes": ""},
    19: {"name": "Bowl Week 2 / CFP Quarterfinals", "short": "Bowl Wk 2 / CFP QF", "phase": "Postseason", "game_week": None, "actions": "CFP Quarterfinals", "notes": ""},
    20: {"name": "Bowl Week 3 / CFP Semifinals", "short": "Bowl Wk 3 / CFP SF", "phase": "Postseason", "game_week": None, "actions": "CFP Semifinals", "notes": ""},
    21: {"name": "Bowl Week 4", "short": "Bowl Wk 4", "phase": "Postseason", "game_week": None, "actions": "Bowl Games", "notes": ""},
    22: {"name": "National Championship", "short": "Natl Champ", "phase": "Postseason", "game_week": None, "actions": "National Championship", "notes": ""},
    # Offseason (23-27)
    23: {"name": "Staff Moves", "short": "Staff Moves", "phase": "Offseason", "game_week": None, "actions": "Coaching staff hires/fires", "notes": ""},
    24: {"name": "Transfer Portal Stage 1 (Open)", "short": "Portal 1 (Open)", "phase": "Offseason", "game_week": None, "actions": "Transfer Portal opens", "notes": ""},
    25: {"name": "Transfer Portal Stage 2 (Close)", "short": "Portal 2 (Close)", "phase": "Offseason", "game_week": None, "actions": "Transfer Portal closes", "notes": ""},
    26: {"name": "National Signing Day", "short": "Signing Day", "phase": "Offseason", "game_week": None, "actions": "National Signing Day", "notes": ""},
    27: {"name": "Training Results", "short": "Training", "phase": "Offseason", "game_week": None, "actions": "Training Results", "notes": "Advancing resets to Preseason of the next season"},
}

FIRST_WEEK = 1  # Preseason
TOTAL_WEEKS_PER_SEASON = 27  # Steps 1-27
LAST_WEEK = TOTAL_WEEKS_PER_SEASON  # Training Results

# Persisted season/week state format. Version 1 used the old 26-stage table (indices 0-25).
WEEK_SCHEME_VERSION = 2

# Best-effort mapping from the old 0-25 index table to the new 1-27 step numbers
_LEGACY_WEEK_MAP = {
    0: 1,                                       # Preseason (Week 0) -> Preseason
    **{i: i + 2 for i in range(1, 14)},         # Week 1-13 -> Week 1-13
    14: 17,                                     # Week 14 (Conf Champs) -> Conference Championship
    15: 18, 16: 19, 17: 20,                     # Bowl Weeks 1-3
    18: 22,                                     # Bowl Week 4 (Natl Champ) -> National Championship
    19: 23, 20: 23,                             # Carousel / Players Leaving -> Staff Moves
    21: 24, 22: 24,                             # Portal Wk 1-2 -> Portal Stage 1
    23: 25, 24: 25,                             # Portal Wk 3-4 -> Portal Stage 2
    25: 27,                                     # Training -> Training Results
}


def migrate_legacy_week(week: Optional[int]) -> Optional[int]:
    """Convert a week index saved under the old 0-25 table to a 1-27 step number."""
    if week is None:
        return None
    return _LEGACY_WEEK_MAP.get(week, FIRST_WEEK)


def is_valid_week(week: int) -> bool:
    """True if week is a valid step number (1-27)."""
    return week in CFB_DYNASTY_WEEKS


def get_next_week(week: int) -> int:
    """Step number that follows week, wrapping Training Results (27) back to Preseason (1)."""
    return FIRST_WEEK if week >= LAST_WEEK else week + 1


def _is_timer_state_message(content: str) -> bool:
    """True for an untyped timer-state JSON message (settings/staff/week messages carry a "type")."""
    body = content.strip()
    if body.startswith("```json"):
        body = body[7:]
    if body.endswith("```"):
        body = body[:-3]
    try:
        state = json.loads(body.strip())
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(state, dict) and 'type' not in state and 'channel_id' in state


_ADVANCED_WORD = re.compile(r"\badvanced\b", re.IGNORECASE)


def is_advance_trigger(message, advance_channel_id: Optional[int]) -> bool:
    """
    True if a message should advance the week: posted directly in the advance channel
    (not a thread or any other channel/server), pinging @everyone/@here or a role,
    and containing the whole word "advanced".
    """
    if not advance_channel_id or message.channel.id != advance_channel_id:
        return False
    if not (message.mention_everyone or message.role_mentions):
        return False
    return bool(_ADVANCED_WORD.search(message.content or ""))


def get_prev_week(week: int) -> int:
    """Step number before week, wrapping Preseason (1) back to Training Results (27)."""
    return LAST_WEEK if week <= FIRST_WEEK else week - 1


def get_week_name(week: int, short: bool = False) -> str:
    """
    Get the display name for a given step number.

    Args:
        week: The step number (1-27)
        short: If True, return the short name

    Returns:
        The week name string
    """
    if week in CFB_DYNASTY_WEEKS:
        return CFB_DYNASTY_WEEKS[week]["short" if short else "name"]
    # Fallback for any number outside the standard structure
    return f"Step {week}"


def get_week_phase(week: int) -> str:
    """
    Get the season phase for a given step number.

    Args:
        week: The step number (1-27)

    Returns:
        The phase name (Preseason, Regular Season, Postseason, or Offseason)
    """
    if week in CFB_DYNASTY_WEEKS:
        return CFB_DYNASTY_WEEKS[week]["phase"]
    return "Unknown"


def get_game_week(week: Optional[int]) -> Optional[int]:
    """
    Get the in-game schedule week (0-14) for a step number.

    Returns None for steps with no regular-season games (Preseason, Postseason, Offseason).
    """
    if week in CFB_DYNASTY_WEEKS:
        return CFB_DYNASTY_WEEKS[week]["game_week"]
    return None


def get_week_actions(week: int) -> str:
    """
    Get the available actions for a given step.

    Args:
        week: The step number (1-27)

    Returns:
        String describing available actions, or empty string
    """
    if week in CFB_DYNASTY_WEEKS:
        return CFB_DYNASTY_WEEKS[week].get("actions", "")
    return ""


def get_week_notes(week: int) -> str:
    """
    Get any important notes for a given step.

    Args:
        week: The step number (1-27)

    Returns:
        String with notes, or empty string
    """
    if week in CFB_DYNASTY_WEEKS:
        return CFB_DYNASTY_WEEKS[week].get("notes", "")
    return ""


def get_week_info(week: int) -> Dict:
    """
    Get full information about a step.

    Args:
        week: The step number (1-27)

    Returns:
        Dict with name, short name, phase, game_week, actions, and notes
    """
    if week in CFB_DYNASTY_WEEKS:
        return CFB_DYNASTY_WEEKS[week].copy()
    return {
        "name": get_week_name(week),
        "short": get_week_name(week, short=True),
        "phase": get_week_phase(week),
        "game_week": None,
        "actions": "",
        "notes": ""
    }


# EST/EDT timezone (America/New_York handles DST automatically)
EST_TIMEZONE = ZoneInfo('America/New_York') if ZoneInfo else None

def to_est(dt: datetime) -> datetime:
    """Convert a datetime to EST/EDT"""
    if not dt:
        return dt
    if EST_TIMEZONE and ZoneInfo:
        # If datetime is naive, assume it's UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
        # Convert to EST
        return dt.astimezone(EST_TIMEZONE)
    return dt  # Fallback if timezone not available

def format_est_time(dt: datetime, format_str: str = '%I:%M %p on %B %d') -> str:
    """Format a datetime in EST/EDT"""
    if not dt:
        return "N/A"
    est_dt = to_est(dt)
    if EST_TIMEZONE:
        return est_dt.strftime(format_str) + ' EST/EDT'
    return est_dt.strftime(format_str)

# Timer state file location
TIMER_STATE_FILE = Path(__file__).parent.parent.parent.parent / "data" / "timer_state.json"

# Hours-remaining warnings sent during a countdown
NOTIFICATION_THRESHOLDS = (24, 12, 6, 1)

# Channel ID for timer notifications (defaults to #general, can be changed)
NOTIFICATION_CHANNEL_ID = 1261662233109205146  # #general

class AdvanceTimer:
    """Manages advance countdown timers with custom durations"""

    def __init__(self, channel: discord.TextChannel, bot: discord.Client, manager=None):
        self.channel = channel  # Original channel where timer was started
        self.bot = bot
        self.manager = manager  # Reference to TimekeeperManager for Discord persistence
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.duration_hours: int = 48
        self.is_active = False
        self.task: Optional[asyncio.Task] = None
        self.notifications_sent = {
            24: False,
            12: False,
            6: False,
            1: False
        }

    def get_notification_channel(self) -> Optional[discord.TextChannel]:
        """Get the channel where timer notifications should be sent (always #general)"""
        notification_channel = self.bot.get_channel(NOTIFICATION_CHANNEL_ID)
        if notification_channel:
            return notification_channel
        # Fallback to original channel if notification channel not found
        logger.warning(f"⚠️ Notification channel {NOTIFICATION_CHANNEL_ID} not found, using original channel")
        return self.channel

    async def save_state(self):
        """Save timer state to disk, environment variable, and Discord for persistence"""
        if not self.is_active:
            # Clear saved state if timer is not active
            if TIMER_STATE_FILE.exists():
                TIMER_STATE_FILE.unlink()
            # Clear environment variable
            if 'TIMER_STATE' in os.environ:
                del os.environ['TIMER_STATE']
            # Clear Discord state
            if self.manager:
                await self.manager._save_state_to_discord({
                    'channel_id': self.channel.id,
                    'is_active': False
                })
            logger.info("💾 Cleared timer state (no active timer)")
            return

        try:
            state = {
                'channel_id': self.channel.id,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'duration_hours': self.duration_hours,
                'is_active': self.is_active,
                'notifications_sent': self.notifications_sent
            }

            state_json = json.dumps(state)

            # Save to file (for local development)
            try:
                TIMER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(TIMER_STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=2)
                logger.info(f"💾 Timer state saved to {TIMER_STATE_FILE}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save timer state to file: {e}")

            # Save to environment variable (for Render/Railway if manually set)
            try:
                os.environ['TIMER_STATE'] = state_json
                logger.debug("💾 Timer state saved to environment variable")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save timer state to environment variable: {e}")

            # Save to Discord (persists across deployments!)
            # This MUST succeed for persistence to work
            if self.manager:
                discord_saved = await self.manager._save_state_to_discord(state)
                if not discord_saved:
                    logger.error("❌ CRITICAL: Failed to save timer state to Discord - timer will NOT persist!")
                else:
                    logger.info("✅ Timer state saved to Discord successfully")
            else:
                logger.error("❌ CRITICAL: No manager available - timer state NOT saved to Discord!")

        except Exception as e:
            logger.error(f"❌ Failed to save timer state: {e}")
            logger.exception("Full error details:")

    async def start_countdown(self, hours: int = 48) -> bool:
        """Start a countdown with custom duration"""
        if self.is_active:
            logger.warning("⚠️ Countdown already active")
            return False

        # Cancel any existing monitoring task before starting a new one
        if self.task and not self.task.done():
            logger.info("🔄 Cancelling old monitoring task before starting new countdown")
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass  # Expected

        self.start_time = datetime.now()
        self.duration_hours = hours
        self.end_time = self.start_time + timedelta(hours=hours)
        self.is_active = True
        # Warnings at or above the full duration would be wrong (e.g. "24 hours left" on a 10h timer)
        self.notifications_sent = {h: h >= hours for h in NOTIFICATION_THRESHOLDS}

        # Save state to disk, env var, and Discord
        await self.save_state()

        # Start the monitoring task
        self.task = asyncio.create_task(self._monitor_countdown())

        logger.info(f"⏰ Countdown started at {self.start_time}")
        logger.info(f"⏰ Duration: {hours} hours")
        logger.info(f"⏰ Countdown will end at {self.end_time}")
        return True

    async def stop_countdown(self) -> bool:
        """Stop the countdown"""
        if not self.is_active:
            return False

        self.is_active = False
        if self.task and not self.task.done():
            self.task.cancel()

        # Clear saved state
        await self.save_state()

        logger.info("⏹️ Countdown stopped")
        return True

    def get_time_remaining(self) -> Optional[timedelta]:
        """Get the time remaining on the countdown"""
        if not self.is_active or not self.end_time:
            return None

        remaining = self.end_time - datetime.now()
        if remaining.total_seconds() < 0:
            return timedelta(0)
        return remaining

    def get_status(self) -> Dict:
        """Get the current status of the countdown"""
        if not self.is_active:
            return {
                'active': False,
                'message': 'No countdown active'
            }

        remaining = self.get_time_remaining()
        if remaining is None:
            return {
                'active': False,
                'message': 'No countdown active'
            }

        total_seconds = int(remaining.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        return {
            'active': True,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'remaining': remaining,
            'hours': hours,
            'minutes': minutes,
            'message': f'{hours}h {minutes}m remaining'
        }

    async def _monitor_countdown(self):
        """Monitor the countdown and send notifications"""
        try:
            while self.is_active:
                remaining = self.get_time_remaining()
                if remaining is None:
                    break

                total_hours = remaining.total_seconds() / 3600

                # Check for notification thresholds. If several were crossed at once (bot was
                # offline, or a restored timer), only send the most urgent one.
                crossed = [h for h in NOTIFICATION_THRESHOLDS
                           if total_hours <= h and not self.notifications_sent.get(h)]
                if crossed and total_hours > 0:
                    await self._send_notification(min(crossed))
                    for h in crossed:
                        self.notifications_sent[h] = True
                    await self.save_state()  # Save after notification

                # Check if time is up
                if total_hours <= 0:
                    await self._send_times_up()
                    self.is_active = False
                    await self.save_state()  # Clear state when timer ends
                    break

                # Check every minute
                await asyncio.sleep(60)

        except asyncio.CancelledError:
            logger.info("⏹️ Countdown monitoring task cancelled")
        except Exception as e:
            logger.error(f"❌ Error in countdown monitoring: {type(e).__name__}: {e}")

    async def _send_notification(self, hours: int):
        """Send a countdown notification to the notification channel (#general)"""
        # More urgent messages and colors for lower time remaining
        if hours <= 1:
            color = 0xff0000  # Red - URGENT
            description = f"🚨 **FINAL HOUR WARNING!** 🚨\n\nYou've got **ONE BLOODY HOUR** left!\n\nIf your game ain't done, GET IT DONE NOW!"
        elif hours <= 6:
            color = 0xff4500  # Red-orange - Getting serious
            description = f"⚠️ Only **{hours} hours** left until advance time!\n\n**GET YOUR GAMES PLAYED NOW, YA MUPPETS!**"
        else:
            color = 0xffa500  # Orange - Warning
            description = f"Oi! Only **{hours} hour{'s' if hours > 1 else ''}** left until advance time, ya muppets!\n\nGet your bleedin' games played!"

        embed = discord.Embed(
            title=f"⏰ {hours} Hour{'s' if hours > 1 else ''} Remaining!",
            description=description,
            color=color
        )

        embed.set_footer(text=f"Harry's Advance Timer 🏈 | Ends at {format_est_time(self.end_time, '%I:%M %p')}")

        try:
            notification_channel = self.get_notification_channel()
            # Add @everyone ping for 6 hour and 1 hour warnings to cut through muted channels
            if hours <= 6:
                await notification_channel.send(content="@everyone", embed=embed)
                logger.info(f"📢 Sent {hours}h notification with @everyone ping to #{notification_channel.name}")
            else:
                await notification_channel.send(embed=embed)
                logger.info(f"📢 Sent {hours}h notification to #{notification_channel.name}")
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")

    async def _send_times_up(self):
        """Send the final TIMES UP message"""
        # Get season/week info for display
        season_info = None
        old_season = None
        old_week = None
        old_week_name = None
        is_new_season = False

        if self.manager:
            season_info = self.manager.get_season_week()
            # Store old values before increment
            if season_info['season'] and season_info['week'] is not None:
                old_season = season_info['season']
                old_week = season_info['week']
                old_week_name = season_info.get('week_name', f"Week {old_week}")

                # Check if this will trigger a new season (advancing from Training Results)
                is_new_season = old_week >= LAST_WEEK

                # Increment the week. Flag it so the "@everyone advanced" post that follows
                # doesn't increment a second time.
                self.manager.advance_pending = True
                await self.manager.increment_week()

                # Get new week info after increment
                new_season_info = self.manager.get_season_week()
                new_week_name = new_season_info.get('week_name', f"Week {new_season_info['week']}")
                logger.info(f"📅 Advanced from {old_week_name} to {new_week_name}")

        # Build description with season/week if available
        if is_new_season and self.manager:
            # NEW SEASON celebration!
            new_season_info = self.manager.get_season_week()
            description = "🎉 **NEW SEASON STARTING!** 🎉\n\n"
            description += "RIGHT THEN, TIME'S UP YA WANKERS!\n\n"
            description += f"**Season {old_season}** is in the books!\n\n"
            description += f"🏈 **WELCOME TO SEASON {new_season_info['season']}!** 🏈\n\n"
            description += f"📍 {old_week_name} → **{new_season_info.get('week_name', 'Preseason')}**\n\n"
            description += "Time to start fresh! Good luck to all you muppets! 🏈"
        else:
            description = "RIGHT THEN, TIME'S UP YA WANKERS!\n\n🏈 **LET'S ADVANCE THE BLOODY LEAGUE!** 🏈\n\n"
            if season_info and season_info['season'] and old_week is not None:
                new_season_info = self.manager.get_season_week() if self.manager else None
                if new_season_info:
                    new_week_name = new_season_info.get('week_name', f"Week {new_season_info['week']}")
                    phase = new_season_info.get('phase', get_week_phase(new_season_info['week']))
                else:
                    new_week_name = get_week_name(get_next_week(old_week))
                    phase = get_week_phase(get_next_week(old_week))

                description += f"**Season {season_info['season']}**\n"
                description += f"📍 {old_week_name} → **{new_week_name}**\n"
                description += f"🏈 Phase: {phase}\n\n"
            description += "All games should be done. If they ain't, tough luck mate!"

        embed = discord.Embed(
            title="⏰ TIME'S UP! LET'S ADVANCE! ⏰",
            description=description,
            color=0xff0000
        )

        embed.set_footer(text="Harry's Advance Timer 🏈")

        try:
            notification_channel = self.get_notification_channel()
            # @everyone for TIME'S UP - this is the most important one!
            await notification_channel.send(content="@everyone", embed=embed)
            logger.info(f"📢 Sent TIMES UP message with @everyone ping to #{notification_channel.name}")

            # Send the upcoming week's schedule if we're in regular season
            await self._send_upcoming_schedule()

        except Exception as e:
            logger.error(f"❌ Failed to send times up message: {e}")

    async def _send_upcoming_schedule(self):
        """Send the upcoming week's schedule after advance (if schedule_announcement setting is enabled)"""
        try:
            notification_channel = self.get_notification_channel()
            if notification_channel and notification_channel.guild:
                from .server_config import server_config
                if not server_config.get_setting(notification_channel.guild.id, "schedule_announcement", True):
                    logger.info("📅 Schedule announcement disabled for this server, skipping")
                    return

            # Import here to avoid circular imports
            from .schedule_manager import get_schedule_manager

            if not self.manager:
                return

            season_info = self.manager.get_season_week()
            if not season_info or season_info['week'] is None:
                return

            new_week = get_game_week(season_info['week'])

            # Only send schedule for regular season weeks (Week 0-14)
            if new_week is None:
                logger.info(f"📅 {season_info.get('week_name')} is not regular season, skipping schedule announcement")
                return

            schedule_mgr = get_schedule_manager()
            if not schedule_mgr:
                return

            schedule_embed = schedule_mgr.build_week_embed(new_week)
            if not schedule_embed:
                logger.warning(f"⚠️ No schedule data for Week {new_week}")
                return

            notification_channel = self.get_notification_channel()
            await notification_channel.send(embed=schedule_embed)
            logger.info(f"📅 Sent Week {new_week} schedule announcement to #{notification_channel.name}")

        except Exception as e:
            logger.error(f"❌ Failed to send schedule announcement: {e}")


class TimekeeperManager:
    """Manages advance timers across multiple channels"""

    # Special value for "no co-commish"
    NO_CO_COMMISH = "We don't fucking have one"

    # Nag messages to cycle through
    NAG_MESSAGES = [
        "🚨 OI! ADVANCE THE BLOODY WEEK ALREADY! 🚨",
        "⏰ Still waiting on that advance, ya lazy sod!",
        "🏈 The league ain't gonna advance itself, mate!",
        "😤 ADVANCE. THE. WEEK. How hard is it?!",
        "🔔 *aggressive bell ringing* ADVANCE TIME!",
        "💀 People are DYING waiting for this advance!",
        "🐌 My nan moves faster than this league advances!",
        "📢 THIS IS YOUR REMINDER TO ADVANCE THE WEEK!",
        "🎯 You've got ONE JOB! Advance the week!",
        "🤬 FOR THE LOVE OF ALL THAT IS HOLY, ADVANCE!",
        "⚡ ADVANCE NOW OR I'LL KEEP SPAMMING YA!",
        "🦆 Even the Oregon Ducks advance faster than you!",
        "🧠 Did you forget how to click buttons?!",
        "🎪 This ain't a circus! Well, actually it is. ADVANCE!",
        "💤 Wake up and ADVANCE THE BLOODY WEEK!",
    ]

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.timers: Dict[int, AdvanceTimer] = {}  # channel_id -> timer
        self.state_message_id: Optional[int] = None  # Discord message ID for state storage
        self.state_channel_id: Optional[int] = None  # Channel ID for state storage
        self.season: Optional[int] = None  # Current season number
        self.week: Optional[int] = None  # Current week number
        # League staff tracking
        self.league_owner_id: Optional[int] = None  # Discord user ID of league owner
        self.league_owner_name: Optional[str] = None  # Display name (cached)
        self.co_commish_id: Optional[int] = None  # Discord user ID of co-commish (None = not set)
        self.co_commish_name: Optional[str] = None  # Display name (cached, or NO_CO_COMMISH)
        # Nagging system
        self.nag_task: Optional[asyncio.Task] = None
        self.nag_active: bool = False
        self.nag_interval_minutes: int = 5
        self.nag_message_index: int = 0
        # Notification channel (for timer announcements)
        self.notification_channel_id: Optional[int] = NOTIFICATION_CHANNEL_ID
        # Restored timer info (for combined startup notification)
        self._restored_timer_info: Optional[Dict] = None
        # True when a timer expired and already advanced the week, until the next timer starts
        self.advance_pending: bool = False
        # Serializes "@everyone advanced" handling so simultaneous posts can't double-advance
        self.advance_lock = asyncio.Lock()
        self.last_manual_advance_at: Optional[datetime] = None

    def get_restored_timer_info(self) -> Optional[Dict]:
        """Get info about restored timer (for startup notification) and clear it"""
        info = self._restored_timer_info
        self._restored_timer_info = None  # Clear after reading
        return info

    async def _save_state_to_discord(self, state: Dict):
        """Save timer state to a Discord DM channel (persists across deployments, invisible to users)"""
        try:
            # Try to get bot owner for DM channel (more private)
            bot_owner_id = None
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None
            except Exception as e:
                logger.debug(f"Could not get application info: {e}")
                pass

            # If we have bot owner, use DM channel (invisible to users)
            if bot_owner_id:
                try:
                    bot_owner = await self.bot.fetch_user(bot_owner_id)
                    # Try to get existing DM channel first
                    dm_channel = bot_owner.dm_channel
                    if not dm_channel:
                        # Try to create DM channel (may fail if user hasn't interacted with bot)
                        dm_channel = await bot_owner.create_dm()

                    # Store state as JSON
                    state_json = json.dumps(state)

                    # Try to find existing state message in DM
                    if self.state_message_id:
                        try:
                            message = await dm_channel.fetch_message(self.state_message_id)
                            await message.edit(content=f"```json\n{state_json}\n```")
                            logger.info("💾 Updated timer state message in bot owner DM")
                            return True
                        except discord.NotFound:
                            self.state_message_id = None

                    # Clean up old state messages
                    try:
                        async for message in dm_channel.history(limit=100):
                            if (message.author == self.bot.user and
                                message.content.startswith("```json") and
                                _is_timer_state_message(message.content)):
                                if message.id != self.state_message_id:
                                    try:
                                        await message.delete()
                                    except Exception:
                                        pass  # Ignore delete failures
                    except Exception:
                        pass  # Ignore iteration failures

                    # Create new state message in DM (invisible to users!)
                    message = await dm_channel.send(content=f"```json\n{state_json}\n```")
                    self.state_message_id = message.id
                    logger.info("💾 Created timer state message in bot owner DM (invisible to users)")
                    return True
                except Exception as e:
                    logger.warning(f"⚠️ Could not use DM channel for state storage: {e}, falling back to timer channel")
                    logger.debug("DM channel error details", exc_info=True)
                    # Continue to fallback below

            # Fallback: Use timer's channel (visible but necessary)
            channel_id = state.get('channel_id')
            if not channel_id:
                logger.error("❌ No channel_id in state - cannot save to Discord")
                return False

            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.error(f"❌ Channel {channel_id} not found - cannot save state")
                return False

            # Store state as JSON in message content
            state_json = json.dumps(state)

            # Try to find existing state message and update it
            if self.state_message_id:
                try:
                    message = await channel.fetch_message(self.state_message_id)
                    # Update existing message (edit is less visible than new message)
                    await message.edit(content=f"```json\n{state_json}\n```")
                    logger.info("💾 Updated timer state message in Discord channel")
                    return True
                except discord.NotFound:
                    # Message was deleted, create new one
                    logger.debug("State message not found, will create new one")
                    self.state_message_id = None
                except Exception as e:
                    logger.warning(f"⚠️ Failed to update state message: {e}, will create new one")
                    self.state_message_id = None

            # Clean up old state messages from this bot to avoid clutter
            try:
                async for message in channel.history(limit=50):
                    if (message.author == self.bot.user and
                        message.content.startswith("```json") and
                        "channel_id" in message.content and
                        "end_time" in message.content and
                        message.id != self.state_message_id):  # Don't delete the one we're tracking
                        # Delete old state messages to keep channel clean
                        try:
                            await message.delete()
                            logger.debug(f"🗑️ Deleted old timer state message")
                        except Exception:
                            pass  # Ignore if we can't delete
            except Exception as e:
                logger.debug(f"Could not clean up old messages: {e}")

            # Create new state message (silent, but still visible)
            try:
                message = await channel.send(
                    content=f"```json\n{state_json}\n```",
                    silent=True  # Don't notify users (but message still visible)
                )
                self.state_message_id = message.id
                self.state_channel_id = channel_id
                logger.info(f"💾 Created timer state message in #{channel.name} (fallback - visible to users)")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to create state message in channel: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to save timer state to Discord: {e}")
            logger.exception("Full error details:")
            return False

    async def _load_state_from_discord(self) -> Optional[Dict]:
        """Load timer state from Discord (DM channel first, then public channels)"""
        try:
            # First, try to get state from bot owner's DM channel (preferred, invisible)
            logger.info("🔍 Checking bot owner DM channel for timer state...")
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None

                if bot_owner_id:
                    logger.info(f"📧 Bot owner ID: {bot_owner_id}")
                    try:
                        bot_owner = await self.bot.fetch_user(bot_owner_id)
                    except Exception as e:
                        logger.warning(f"⚠️ Could not fetch bot owner: {e}")
                        raise  # Will fall back to public channels

                    try:
                        dm_channel = bot_owner.dm_channel
                        if not dm_channel:
                            # Try to create DM channel (may fail if user hasn't interacted with bot)
                            dm_channel = await bot_owner.create_dm()
                    except Exception as e:
                        logger.warning(f"⚠️ Could not create/access DM channel: {e}")
                        logger.info("💡 Tip: Bot owner needs to have DMs enabled - falling back to public channels")
                        raise  # Will fall back to public channels

                    logger.info(f"📧 DM channel created/accessed: {dm_channel.id}")

                    # Search DM channel for state messages (search more messages - state could be older)
                    message_count = 0
                    async for message in dm_channel.history(limit=100):
                        message_count += 1
                        if message.author != self.bot.user:
                            continue

                        content = message.content.strip()

                        # Try to extract JSON - handle both code block and raw JSON formats
                        json_content = None

                        # Format 1: ```json ... ```
                        if content.startswith("```json"):
                            json_content = content[7:]  # Remove ```json
                            if json_content.endswith("```"):
                                json_content = json_content[:-3]
                            json_content = json_content.strip()
                        # Format 2: Raw JSON starting with {
                        elif content.startswith("{") and "channel_id" in content and "end_time" in content:
                            json_content = content

                        if not json_content:
                            continue

                        try:
                            state = json.loads(json_content)
                            if not isinstance(state, dict) or 'type' in state or 'channel_id' not in state:
                                continue
                            # The newest timer state message is authoritative. If it says the
                            # timer is inactive, stop — don't resurrect an older, stopped timer.
                            self.state_message_id = message.id
                            if 'end_time' not in state or not state.get('is_active', True):
                                logger.info(f"📧 Newest timer state in DM is inactive (message #{message_count})")
                                return None
                            logger.info(f"✅ Found timer state in bot owner DM (message #{message_count})")
                            return state
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse JSON from DM message: {e}")
                            continue
                    logger.info(f"📧 Searched {message_count} messages in DM, no timer state found")
                    # If we got here, DM worked but no state found - continue to public channels
                else:
                    logger.warning("⚠️ Could not get bot owner ID")
            except Exception as e:
                logger.warning(f"⚠️ Could not check DM channel: {e}")
                logger.debug("Full error details", exc_info=True)
                # Continue to fallback - public channels

            # Fallback: Search for state messages in all channels the bot can access
            logger.info("🔍 Checking public channels for timer state...")
            channels_checked = 0
            messages_checked = 0
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if not channel.permissions_for(guild.me).read_message_history:
                        continue

                    channels_checked += 1

                    # Search recent messages for state (look for JSON in code blocks)
                    try:
                        async for message in channel.history(limit=100):
                            messages_checked += 1
                            if message.author == self.bot.user and message.content.startswith("```json"):
                                # Extract JSON from code block
                                content = message.content.strip()
                                if content.startswith("```json"):
                                    content = content[7:]  # Remove ```json
                                if content.endswith("```"):
                                    content = content[:-3]  # Remove ```
                                content = content.strip()

                                try:
                                    state = json.loads(content)
                                    # Validate it's a timer state
                                    if 'channel_id' in state and 'end_time' in state:
                                        # Found state in public channel - migrate to DM and delete this one
                                        self.state_message_id = message.id
                                        self.state_channel_id = channel.id
                                        logger.info(f"📂 Found timer state message in #{channel.name}, will migrate to DM")

                                        # Delete the visible message after we've loaded it
                                        try:
                                            await message.delete()
                                            logger.info(f"🗑️ Deleted visible timer state message from #{channel.name}")
                                        except Exception:
                                            pass  # Ignore delete failures

                                        return state
                                except json.JSONDecodeError:
                                    continue
                    except discord.Forbidden:
                        continue
                    except Exception as e:
                        logger.debug(f"Error searching channel {channel.name}: {e}")
                        continue

            logger.info(f"📂 Searched {channels_checked} channels, {messages_checked} messages - no timer state found")

            return None

        except Exception as e:
            logger.error(f"❌ Failed to load timer state from Discord: {e}")
            logger.exception("Full error details:")
            return None

    async def load_saved_state(self):
        """Load and restore any saved timer state from Discord, environment variable, or file"""
        logger.info("🔄 Attempting to load saved timer state...")
        state = None

        # Try loading from Discord first (most reliable for ephemeral file systems)
        logger.info("📂 Checking Discord for timer state...")
        state = await self._load_state_from_discord()
        if state:
            logger.info("✅ Loaded timer state from Discord")
        else:
            logger.info("📂 No timer state found in Discord")

        # Fallback to environment variable (for Render/Railway if manually set)
        if not state and 'TIMER_STATE' in os.environ:
            logger.info("📂 Checking environment variable for timer state...")
            try:
                state_json = os.environ['TIMER_STATE']
                state = json.loads(state_json)
                logger.info("✅ Loaded timer state from environment variable")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load timer state from environment variable: {e}")

        # Fallback to file system (for local development)
        if not state and TIMER_STATE_FILE.exists():
            logger.info(f"📂 Checking file system for timer state ({TIMER_STATE_FILE})...")
            try:
                with open(TIMER_STATE_FILE, 'r') as f:
                    state = json.load(f)
                logger.info("✅ Loaded timer state from file")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load timer state from file: {e}")

        if not state:
            logger.info("📂 No saved timer state found anywhere")

        # Load season/week state
        await self._load_season_week_state()

        # Load league staff state
        await self._load_league_staff_state()

        # Load bot settings (notification channel, etc.)
        await self._load_settings_state()

        if not state:
            return

        try:

            channel_id = state.get('channel_id')
            if not channel_id:
                logger.warning("⚠️ Invalid timer state: no channel_id")
                return

            # Get the channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"⚠️ Could not find channel {channel_id}, clearing saved state")
                TIMER_STATE_FILE.unlink(missing_ok=True)
                return

            # Parse timestamps
            start_time = datetime.fromisoformat(state['start_time']) if state.get('start_time') else None
            end_time = datetime.fromisoformat(state['end_time']) if state.get('end_time') else None

            if not start_time or not end_time:
                logger.warning("⚠️ Invalid timer state: missing timestamps")
                return

            # Check if timer already expired
            if end_time < datetime.now():
                logger.info(f"⏰ Saved timer already expired, clearing state")
                # Clear file
                if TIMER_STATE_FILE.exists():
                    TIMER_STATE_FILE.unlink()
                # Clear Discord state
                await self._save_state_to_discord({
                    'channel_id': channel_id,
                    'is_active': False
                })
                return

            # Restore the timer
            timer = AdvanceTimer(channel, self.bot, manager=self)
            timer.start_time = start_time
            timer.end_time = end_time
            timer.duration_hours = state.get('duration_hours', 48)
            timer.is_active = True
            # JSON converts int keys to strings, so convert them back to ints
            raw_notifications = state.get('notifications_sent', {24: False, 12: False, 6: False, 1: False})
            timer.notifications_sent = {int(k): v for k, v in raw_notifications.items()}

            # Start monitoring task
            timer.task = asyncio.create_task(timer._monitor_countdown())

            # Store in manager
            self.timers[channel_id] = timer

            # Save state to DM (migrate from public channel if needed)
            await timer.save_state()

            time_remaining = end_time - datetime.now()
            hours_remaining = time_remaining.total_seconds() / 3600

            logger.info(f"✅ Restored timer for {channel.guild.name} (ID: {channel.guild.id}) - #{channel.name}")
            logger.info(f"⏰ Season {self.season}, Week {self.week}")
            logger.info(f"⏰ Time remaining: {hours_remaining:.1f} hours")
            logger.info(f"⏰ End time: {end_time}")

            # Store restore info for combined startup notification
            self._restored_timer_info = {
                'channel_id': channel.id,
                'channel_name': channel.name,
                'guild_id': channel.guild.id,
                'guild_name': channel.guild.name,
                'hours_remaining': hours_remaining,
                'minutes_remaining': int((time_remaining.total_seconds() % 3600) / 60),
                'end_time': end_time.strftime('%I:%M %p'),
                'season': self.season,
                'week': self.week
            }

        except Exception as e:
            logger.error(f"❌ Failed to load timer state: {e}")
            # Clear corrupted state file
            if TIMER_STATE_FILE.exists():
                TIMER_STATE_FILE.unlink()
                logger.info("💾 Cleared corrupted timer state file")

    def get_timer(self, channel: discord.TextChannel) -> AdvanceTimer:
        """Get or create a timer for a channel"""
        if channel.id not in self.timers:
            self.timers[channel.id] = AdvanceTimer(channel, self.bot, manager=self)
        return self.timers[channel.id]

    async def start_timer(self, channel: discord.TextChannel, hours: int = 48) -> bool:
        """Start a timer for a channel with custom duration"""
        timer = self.get_timer(channel)
        started = await timer.start_countdown(hours)
        if started and self.advance_pending:
            self.advance_pending = False
            await self._save_season_week_state()
        return started

    def is_duplicate_advance(self, window_minutes: int = 3) -> bool:
        """True if a manual advance was already handled moments ago (e.g. two people posting it)."""
        return (
            self.last_manual_advance_at is not None
            and datetime.now() - self.last_manual_advance_at < timedelta(minutes=window_minutes)
        )

    async def stop_timer(self, channel: discord.TextChannel) -> bool:
        """Stop a timer for a channel"""
        if channel.id not in self.timers:
            return False
        return await self.timers[channel.id].stop_countdown()

    def get_advance_channel(self, fallback: Optional[discord.abc.Messageable] = None):
        """The channel the single league advance timer runs in (the configured notification channel)."""
        return self.bot.get_channel(self.get_notification_channel_id()) or fallback

    async def stop_all_timers(self) -> int:
        """
        Stop every active timer in every channel. Returns how many were stopped.

        The league has one advance countdown; a stray timer left running in another
        channel would expire later and advance the week a second time.
        """
        stopped = 0
        for channel_id, timer in list(self.timers.items()):
            if timer.is_active and await timer.stop_countdown():
                logger.info(f"⏹️ Stopped timer in channel {channel_id}")
                stopped += 1
        return stopped

    async def stop_timer_by_id(self, channel_id: int) -> bool:
        """Stop a timer by its channel id (used by the /league timers manager)."""
        if channel_id not in self.timers:
            return False
        return await self.timers[channel_id].stop_countdown()

    def get_all_active_timers(self) -> list:
        """Return status info for every active timer, one entry per channel.

        Used by /league timers so an admin can see and stop all running timers.
        """
        active = []
        for channel_id, timer in self.timers.items():
            if not timer.is_active:
                continue
            status = timer.get_status()
            if not status.get('active'):
                continue
            channel = self.bot.get_channel(channel_id)
            guild = getattr(channel, 'guild', None)
            active.append({
                'channel_id': channel_id,
                'channel_name': getattr(channel, 'name', str(channel_id)),
                'guild_name': getattr(guild, 'name', 'Unknown'),
                'hours': status['hours'],
                'minutes': status['minutes'],
                'end_time': status.get('end_time'),
            })
        return active

    def get_status(self, channel: discord.TextChannel) -> Dict:
        """Get timer status for a channel"""
        if channel.id not in self.timers:
            return {
                'active': False,
                'message': 'No countdown active'
            }
        return self.timers[channel.id].get_status()

    def get_season_week(self) -> Dict:
        """Get current season and week with proper CFB 26 week names"""
        week_info = get_week_info(self.week) if self.week is not None else None
        return {
            'season': self.season,
            'week': self.week,
            'week_name': week_info["name"] if week_info else None,
            'week_short': week_info["short"] if week_info else None,
            'phase': week_info["phase"] if week_info else None,
            'game_week': week_info["game_week"] if week_info else None
        }

    async def set_season_week(self, season: int, week: int) -> bool:
        """Set the current season and week"""
        if season < 1 or not is_valid_week(week):
            return False
        self.season = season
        self.week = week
        self.advance_pending = False
        # Save season/week to state
        await self._save_season_week_state()
        logger.info(f"📅 Season/Week set to Season {season}, {get_week_name(week)} (step {week})")
        return True

    async def increment_week(self) -> bool:
        """
        Increment the week (called when advance happens).
        Automatically rolls over to a new season after Training Results (step 27).
        """
        if self.week is None:
            logger.warning("⚠️ Cannot increment week - week not set")
            return False

        old_week = self.week
        old_week_name = get_week_name(old_week)

        # Check if we're at Training Results (step 27) - time to start a new season!
        if self.week >= LAST_WEEK:
            self.week = FIRST_WEEK  # Reset to Preseason
            if self.season:
                self.season += 1  # Increment season
            else:
                self.season = 1  # Default to season 1 if not set
            logger.info(f"🎉 NEW SEASON! {old_week_name} → Season {self.season}, {get_week_name(self.week)}")
        else:
            self.week += 1
            logger.info(f"📅 Week incremented: {old_week_name} → {get_week_name(self.week)}")

        # Save season/week to state
        await self._save_season_week_state()
        return True

    async def _save_season_week_state(self):
        """Save season/week state to Discord"""
        state = {
            'season': self.season,
            'week': self.week,
            'scheme': WEEK_SCHEME_VERSION,
            'advance_pending': self.advance_pending,
            'type': 'season_week'  # Mark as season/week state, not timer state
        }
        try:
            # Try to save to DM channel
            bot_owner_id = None
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None
            except Exception:
                pass  # Ignore if we can't get app info

            if bot_owner_id:
                try:
                    bot_owner = await self.bot.fetch_user(bot_owner_id)
                    dm_channel = bot_owner.dm_channel
                    if not dm_channel:
                        dm_channel = await bot_owner.create_dm()

                    state_json = json.dumps(state)

                    # Try to find existing season/week message
                    async for message in dm_channel.history(limit=100):
                        if (message.author == self.bot.user and
                            message.content.startswith("```json") and
                            '"type": "season_week"' in message.content):
                            await message.edit(content=f"```json\n{state_json}\n```")
                            logger.info("💾 Updated season/week state in DM")
                            return

                    # Create new message
                    await dm_channel.send(content=f"```json\n{state_json}\n```")
                    logger.info("💾 Created season/week state in DM")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Could not save season/week to DM: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save season/week state: {e}")

    async def _load_season_week_state(self):
        """Load season/week state from Discord"""
        try:
            # Try to load from DM channel
            bot_owner_id = None
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None
            except Exception:
                pass  # Ignore if we can't get app info

            if bot_owner_id:
                try:
                    bot_owner = await self.bot.fetch_user(bot_owner_id)
                    dm_channel = bot_owner.dm_channel
                    if not dm_channel:
                        dm_channel = await bot_owner.create_dm()

                    # Search more messages (100 instead of 10)
                    async for message in dm_channel.history(limit=100):
                        if message.author != self.bot.user:
                            continue

                        # Check if message contains season_week marker
                        if '"type": "season_week"' not in message.content and '"season"' not in message.content:
                            continue

                        content = message.content.strip()

                        # Handle both code block and raw JSON formats
                        if content.startswith("```json"):
                            content = content[7:]
                            if content.endswith("```"):
                                content = content[:-3]
                            content = content.strip()
                        elif not content.startswith("{"):
                            continue

                        try:
                            state = json.loads(content)
                            # Check for season_week type OR just season/week keys
                            if state.get('type') == 'season_week' or ('season' in state and 'week' in state and 'channel_id' not in state):
                                self.season = state.get('season')
                                self.week = state.get('week')
                                self.advance_pending = bool(state.get('advance_pending', False))
                                if state.get('scheme') != WEEK_SCHEME_VERSION:
                                    legacy_week = self.week
                                    self.week = migrate_legacy_week(legacy_week)
                                    logger.warning(
                                        f"⚠️ Migrated legacy week index {legacy_week} → step {self.week} "
                                        f"({get_week_name(self.week) if self.week else '?'}). Verify with /league week."
                                    )
                                    await self._save_season_week_state()
                                logger.info(f"✅ Loaded season/week: Season {self.season}, Week {self.week}")
                                return
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    logger.debug(f"Could not load season/week from DM: {e}")
        except Exception as e:
            logger.debug(f"Failed to load season/week state: {e}")

    # ==================== League Staff Methods ====================

    def get_league_staff(self) -> Dict:
        """Get current league owner and co-commish"""
        return {
            'owner_id': self.league_owner_id,
            'owner_name': self.league_owner_name,
            'co_commish_id': self.co_commish_id,
            'co_commish_name': self.co_commish_name,
            'has_co_commish': self.co_commish_id is not None and self.co_commish_name != self.NO_CO_COMMISH
        }

    async def set_league_owner(self, user: discord.User) -> bool:
        """Set the league owner"""
        try:
            self.league_owner_id = user.id
            self.league_owner_name = user.display_name
            await self._save_league_staff_state()
            logger.info(f"👑 League owner set to {user.display_name} (ID: {user.id})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set league owner: {e}")
            return False

    async def set_co_commish(self, user: Optional[discord.User] = None, no_co_commish: bool = False) -> bool:
        """
        Set the co-commissioner.

        Args:
            user: The Discord user to set as co-commish, or None
            no_co_commish: If True, set to "We don't fucking have one"
        """
        try:
            if no_co_commish:
                self.co_commish_id = None
                self.co_commish_name = self.NO_CO_COMMISH
                logger.info(f"👤 Co-commish set to: {self.NO_CO_COMMISH}")
            elif user:
                self.co_commish_id = user.id
                self.co_commish_name = user.display_name
                logger.info(f"👤 Co-commish set to {user.display_name} (ID: {user.id})")
            else:
                self.co_commish_id = None
                self.co_commish_name = None
                logger.info("👤 Co-commish cleared")

            await self._save_league_staff_state()
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set co-commish: {e}")
            return False

    async def set_notification_channel(self, channel_id: int) -> bool:
        """Set the notification channel for timer announcements"""
        global NOTIFICATION_CHANNEL_ID
        try:
            self.notification_channel_id = channel_id
            NOTIFICATION_CHANNEL_ID = channel_id  # Update module-level constant
            await self._save_settings_state()
            logger.info(f"📢 Notification channel set to {channel_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set notification channel: {e}")
            return False

    def get_notification_channel_id(self) -> int:
        """Get the notification channel ID"""
        return self.notification_channel_id or NOTIFICATION_CHANNEL_ID

    async def _save_settings_state(self):
        """Save bot settings (notification channel, etc.) to Discord"""
        state = {
            'notification_channel_id': self.notification_channel_id,
            'type': 'bot_settings'
        }
        try:
            bot_owner_id = None
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None
            except Exception:
                pass  # Ignore if we can't get app info

            if bot_owner_id:
                try:
                    bot_owner = await self.bot.fetch_user(bot_owner_id)
                    dm_channel = bot_owner.dm_channel
                    if not dm_channel:
                        dm_channel = await bot_owner.create_dm()

                    state_json = json.dumps(state)

                    # Try to find existing settings message
                    async for message in dm_channel.history(limit=100):
                        if (message.author == self.bot.user and
                            message.content.startswith("```json") and
                            '"type": "bot_settings"' in message.content):
                            await message.edit(content=f"```json\n{state_json}\n```")
                            logger.info("💾 Updated bot settings state in DM")
                            return

                    # Create new message
                    await dm_channel.send(content=f"```json\n{state_json}\n```")
                    logger.info("💾 Created bot settings state in DM")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Could not save bot settings to DM: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save bot settings state: {e}")

    async def _load_settings_state(self):
        """Load bot settings from Discord"""
        global NOTIFICATION_CHANNEL_ID
        try:
            bot_owner_id = None
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None
            except Exception:
                pass  # Ignore if we can't get app info

            if bot_owner_id:
                try:
                    bot_owner = await self.bot.fetch_user(bot_owner_id)
                    dm_channel = bot_owner.dm_channel
                    if not dm_channel:
                        dm_channel = await bot_owner.create_dm()

                    async for message in dm_channel.history(limit=100):
                        if (message.author == self.bot.user and
                            message.content.startswith("```json") and
                            '"type": "bot_settings"' in message.content):
                            content = message.content.strip()
                            if content.startswith("```json"):
                                content = content[7:]
                            if content.endswith("```"):
                                content = content[:-3]
                            content = content.strip()

                            try:
                                state = json.loads(content)
                                if state.get('type') == 'bot_settings':
                                    saved_channel = state.get('notification_channel_id')
                                    if saved_channel:
                                        self.notification_channel_id = saved_channel
                                        NOTIFICATION_CHANNEL_ID = saved_channel
                                        logger.info(f"✅ Loaded notification channel: {saved_channel}")
                                    return
                            except json.JSONDecodeError:
                                pass
                except Exception as e:
                    logger.warning(f"⚠️ Could not load bot settings from DM: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load bot settings state: {e}")

    async def _save_league_staff_state(self):
        """Save league staff state to Discord"""
        state = {
            'league_owner_id': self.league_owner_id,
            'league_owner_name': self.league_owner_name,
            'co_commish_id': self.co_commish_id,
            'co_commish_name': self.co_commish_name,
            'type': 'league_staff'
        }
        try:
            bot_owner_id = None
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None
            except Exception:
                pass  # Ignore if we can't get app info

            if bot_owner_id:
                try:
                    bot_owner = await self.bot.fetch_user(bot_owner_id)
                    dm_channel = bot_owner.dm_channel
                    if not dm_channel:
                        dm_channel = await bot_owner.create_dm()

                    state_json = json.dumps(state)

                    # Try to find existing league staff message
                    async for message in dm_channel.history(limit=100):
                        if (message.author == self.bot.user and
                            message.content.startswith("```json") and
                            '"type": "league_staff"' in message.content):
                            await message.edit(content=f"```json\n{state_json}\n```")
                            logger.info("💾 Updated league staff state in DM")
                            return

                    # Create new message
                    await dm_channel.send(content=f"```json\n{state_json}\n```")
                    logger.info("💾 Created league staff state in DM")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Could not save league staff to DM: {e}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save league staff state: {e}")

    async def _load_league_staff_state(self):
        """Load league staff state from Discord"""
        try:
            bot_owner_id = None
            try:
                app_info = await self.bot.application_info()
                bot_owner_id = app_info.owner.id if app_info.owner else None
            except Exception:
                pass  # Ignore if we can't get app info

            if bot_owner_id:
                try:
                    bot_owner = await self.bot.fetch_user(bot_owner_id)
                    dm_channel = bot_owner.dm_channel
                    if not dm_channel:
                        dm_channel = await bot_owner.create_dm()

                    # Search more messages (100 instead of 15)
                    async for message in dm_channel.history(limit=100):
                        if message.author != self.bot.user:
                            continue

                        # Check if message contains league_staff marker
                        if '"type": "league_staff"' not in message.content and '"league_owner_id"' not in message.content:
                            continue

                        content = message.content.strip()

                        # Handle both code block and raw JSON formats
                        if content.startswith("```json"):
                            content = content[7:]
                            if content.endswith("```"):
                                content = content[:-3]
                            content = content.strip()
                        elif not content.startswith("{"):
                            continue

                        try:
                            state = json.loads(content)
                            # Check for league_staff type OR just league_owner_id key
                            if state.get('type') == 'league_staff' or 'league_owner_id' in state:
                                self.league_owner_id = state.get('league_owner_id')
                                self.league_owner_name = state.get('league_owner_name')
                                self.co_commish_id = state.get('co_commish_id')
                                self.co_commish_name = state.get('co_commish_name')
                                logger.info(f"✅ Loaded league staff: Owner={self.league_owner_name}, Co-Commish={self.co_commish_name}")
                                return
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    logger.debug(f"Could not load league staff from DM: {e}")
        except Exception as e:
            logger.debug(f"Failed to load league staff state: {e}")

    # ==================== Owner Nagging System ====================

    async def start_nagging(self, interval_minutes: int = 5) -> bool:
        """
        Start nagging the league owner to advance the week.

        Args:
            interval_minutes: How often to nag (default 5 minutes)
        """
        if not self.league_owner_id:
            logger.warning("⚠️ Cannot nag - no league owner set!")
            return False

        if self.nag_active:
            logger.warning("⚠️ Already nagging the owner!")
            return False

        self.nag_active = True
        self.nag_interval_minutes = interval_minutes
        self.nag_message_index = 0
        self.nag_task = asyncio.create_task(self._nag_loop())
        logger.info(f"😈 Started nagging league owner every {interval_minutes} minutes!")
        return True

    async def stop_nagging(self) -> bool:
        """Stop nagging the league owner"""
        if not self.nag_active:
            return False

        self.nag_active = False
        if self.nag_task and not self.nag_task.done():
            self.nag_task.cancel()

        # Send a final message letting them know they're off the hook
        try:
            owner = await self.bot.fetch_user(self.league_owner_id)
            dm_channel = owner.dm_channel
            if not dm_channel:
                dm_channel = await owner.create_dm()
            await dm_channel.send("✅ Alright, alright! I'll stop nagging ya... FOR NOW. 😈")
        except Exception:
            pass  # Ignore if we can't DM the owner

        logger.info("😇 Stopped nagging the league owner")
        return True

    def is_nagging(self) -> bool:
        """Check if currently nagging"""
        return self.nag_active

    async def _nag_loop(self):
        """Background task that sends nag messages"""
        try:
            # Send first message immediately
            await self._send_nag_message()

            while self.nag_active:
                # Wait for the interval
                await asyncio.sleep(self.nag_interval_minutes * 60)

                if not self.nag_active:
                    break

                await self._send_nag_message()

        except asyncio.CancelledError:
            logger.info("😇 Nag task cancelled")
        except Exception as e:
            logger.error(f"❌ Error in nag loop: {e}")
            self.nag_active = False

    async def _send_nag_message(self):
        """Send a nag message to the league owner"""
        if not self.league_owner_id:
            return

        try:
            owner = await self.bot.fetch_user(self.league_owner_id)
            dm_channel = owner.dm_channel
            if not dm_channel:
                dm_channel = await owner.create_dm()

            # Get the next message in rotation
            message = self.NAG_MESSAGES[self.nag_message_index % len(self.NAG_MESSAGES)]
            self.nag_message_index += 1

            # Add week info if available
            if self.season and self.week is not None:
                week_name = get_week_name(self.week)
                message += f"\n\n📅 **Season {self.season}, {week_name}**"

            await dm_channel.send(message)
            logger.info(f"📢 Sent nag message #{self.nag_message_index} to league owner")

        except Exception as e:
            logger.error(f"❌ Failed to send nag message: {e}")
