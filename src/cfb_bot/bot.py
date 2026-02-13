#!/usr/bin/env python3
# =============================================================================
# CRITICAL: audioop fix MUST be imported before discord!
# Python 3.13 removed audioop module which discord.py needs.
# DO NOT MOVE THIS IMPORT - IT MUST BE BEFORE DISCORD!
# =============================================================================
from cfb_bot.utils import audioop_fix  # noqa: E402, I001, I002 isort:skip
"""
CFB 26 League Bot - A Discord bot for the CFB 26 online dynasty league

This bot provides AI-powered assistance for league members, including:
- Natural language processing for league questions
- Slash commands for quick access to rules and information
- Rivalry responses and fun interactions
- Integration with the official league charter

Author: CFB 26 League
License: MIT
Version: 1.0.0
"""
import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# =============================================================================
# CONSTANTS
# =============================================================================

class Colors:
    """Discord embed colors for consistent theming"""
    PRIMARY = 0x1e90ff    # Dodger blue - main bot color
    SUCCESS = 0x00ff00    # Green - success messages
    ERROR = 0xff0000      # Red - error messages
    WARNING = 0xffa500    # Orange - warnings
    ADMIN = 0xffaa00      # Golden - admin logs
    HS_STATS = 0x2ecc71   # Emerald - HS stats module
    RECRUITING = 0xffd700 # Gold - recruiting module (247Sports)


class Footers:
    """Standard footer texts"""
    CFB_DATA = "Harry's CFB Data 🏈 | Data from CollegeFootballData.com"
    PLAYER_LOOKUP = "Harry's Player Lookup 🏈 | Data from CollegeFootballData.com"
    HS_STATS = "Harry's HS Stats 🏈 | Data scraped from MaxPreps"
    CONFIG = "Harry's Server Config 🏈"
    # League-specific footer (only when LEAGUE module enabled)
    LEAGUE = "Harry - Your CFB 26 League Assistant 🏈"
    # Generic footer (when LEAGUE module disabled)
    DEFAULT = "Harry - Your CFB Assistant 🏈"


def get_footer_for_guild(guild_id: int) -> str:
    """Get appropriate footer based on whether LEAGUE is enabled for this guild"""
    if guild_id and server_config.is_module_enabled(guild_id, FeatureModule.LEAGUE):
        return Footers.LEAGUE
    return Footers.DEFAULT


# Admin-only channel for bot notifications (Booze's Playground)
ADMIN_CHANNEL_ID = 1417663211292852244

# Default notification channel for timer announcements (can be changed with /set_timer_channel)
# This is the fallback - the persisted value from timekeeper takes precedence
DEFAULT_NOTIFICATION_CHANNEL_ID = 1261662233109205146  # #general
GENERAL_CHANNEL_ID = DEFAULT_NOTIFICATION_CHANNEL_ID  # Will be updated on startup from saved settings


def get_notification_channel():
    """Get the notification channel, using timekeeper's saved value if available"""
    if timekeeper_manager:
        channel_id = timekeeper_manager.get_notification_channel_id()
    else:
        channel_id = GENERAL_CHANNEL_ID
    return bot.get_channel(channel_id)


async def send_admin_notification(title: str, description: str, color: int = 0x1e90ff, fields: list = None, guild_id: int = None):
    """
    Send a notification to configured admin channels.

    Args:
        title: Embed title
        description: Embed description
        color: Embed color (default blue)
        fields: Optional list of {"name": str, "value": str, "inline": bool} dicts
        guild_id: Optional - only send to this guild's admin channel
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", False)
            )
    embed.set_footer(text="Harry Admin Notification 🔧")

    sent_count = 0
    guilds_to_notify = [bot.get_guild(guild_id)] if guild_id else bot.guilds

    for guild in guilds_to_notify:
        if not guild:
            continue
        admin_channel_id = server_config.get_admin_channel(guild.id)
        if admin_channel_id:
            channel = guild.get_channel(admin_channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to send to {guild.name}: {e}")

    return sent_count


async def send_admin_error(error_type: str, error_msg: str, context: str = None, guild_id: int = None):
    """
    Send an error report to admin channels.

    Args:
        error_type: Type of error (e.g., "Command Error", "AI Error")
        error_msg: Error message/details
        context: Optional context (e.g., which command, which user)
        guild_id: Optional - only send to this guild's admin channel
    """
    description = f"**Error:** {error_msg[:500]}"
    if context:
        description = f"**Context:** {context}\n\n{description}"

    await send_admin_notification(
        title=f"❌ {error_type}",
        description=description,
        color=Colors.ERROR,
        guild_id=guild_id
    )


async def send_admin_log(event: str, details: str = None, guild_id: int = None):
    """
    Send an important log event to admin channels.

    Args:
        event: Event name (e.g., "Config Changed", "Module Enabled")
        details: Optional details about the event
        guild_id: Optional - only send to this guild's admin channel
    """
    description = details if details else "No additional details."

    await send_admin_notification(
        title=f"📋 {event}",
        description=description,
        color=Colors.ADMIN,
        guild_id=guild_id
    )


async def send_startup_notification(version: str):
    """
    Send a combined startup notification with version info, features, and timer status.
    """
    version_mgr = VersionManager()
    version_info = version_mgr.get_latest_version_info()
    version_title = version_info.get('title', 'Update')
    version_emoji = version_info.get('emoji', '📌')

    # Get latest features preview
    changes_preview = []
    for feature_group in version_info.get('features', [])[:2]:
        for change in feature_group.get('changes', [])[:3]:
            changes_preview.append(f"• {change}")
    changes_text = "\n".join(changes_preview[:5]) if changes_preview else "No changes listed"

    # Build description
    description = f"**Version {version}** - {version_title}\n\n"
    description += f"**Guilds:** {len(bot.guilds)} | **Status:** Online ✅\n\n"

    # Check for restored timer
    timer_info = None
    if timekeeper_manager:
        timer_info = timekeeper_manager.get_restored_timer_info()

    if timer_info:
        description += f"**⏰ Timer Restored**\n"
        description += f"Channel: #{timer_info['channel_name']}\n"
        description += f"Time Remaining: {int(timer_info['hours_remaining'])}h {timer_info['minutes_remaining']}m\n"
        description += f"Ends At: {timer_info['end_time']}\n\n"

    # Create embed
    embed = discord.Embed(
        title="🏈 Harry is Online!",
        description=description,
        color=Colors.SUCCESS
    )

    embed.add_field(
        name=f"{version_emoji} What's New",
        value=changes_text,
        inline=False
    )

    embed.set_footer(text="Harry Admin Notification 🔧 | Use /whats_new for full details")

    # Send to all admin channels
    sent_count = 0
    for guild in bot.guilds:
        admin_channel_id = server_config.get_admin_channel(guild.id)
        if admin_channel_id:
            channel = guild.get_channel(admin_channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"❌ Failed to send startup to {guild.name}: {e}")

    if sent_count > 0:
        logger.info(f"📢 Sent startup notification to {sent_count} admin channel(s)")
    else:
        logger.info(f"📢 Startup complete (no admin channels configured)")


async def send_week_schedule(channel, week_num, guild_id=None):
    """Send the schedule for a given week to a channel (if schedule_announcement setting is enabled)."""
    if week_num is None:
        return

    if guild_id is not None and not server_config.get_setting(guild_id, "schedule_announcement", True):
        logger.info("📅 Schedule announcement disabled for this server, skipping")
        return

    # Only show schedule for regular season weeks (0-13)
    if week_num > 13:
        logger.info(f"📅 Week {week_num} is not regular season, skipping schedule")
        return

    try:
        schedule_mgr = get_schedule_manager()
        if not schedule_mgr:
            return

        week_data = schedule_mgr.get_week_schedule(week_num)
        if not week_data:
            logger.warning(f"⚠️ No schedule data for Week {week_num}")
            return

        # Build the schedule embed
        schedule_embed = discord.Embed(
            title=f"📅 Week {week_num} Matchups",
            description="Here's what's on the slate this week, ya muppets!",
            color=Colors.SUCCESS
        )

        # Bye teams (bold user teams)
        bye_teams = week_data.get('bye_teams', [])
        if bye_teams:
            schedule_embed.add_field(
                name="🛋️ Bye Week",
                value=schedule_mgr.format_bye_teams(bye_teams),
                inline=False
            )

        # Games (bold user teams)
        games = week_data.get('games', [])
        if games:
            games_text = "\n".join([schedule_mgr.format_game(g) for g in games])
            schedule_embed.add_field(
                name="🎮 This Week's Games",
                value=games_text,
                inline=False
            )

        schedule_embed.set_footer(text="Harry's Schedule Tracker 🏈 | Get your games done!")
        await channel.send(embed=schedule_embed)
        logger.info(f"📅 Sent Week {week_num} schedule")

    except Exception as e:
        logger.error(f"❌ Failed to send schedule: {e}")


from .utils import \
    timekeeper as timekeeper_module  # For updating NOTIFICATION_CHANNEL_ID
from .utils.admin_check import AdminManager
from .utils.cfb_data import cfb_data
from .utils.channel_manager import ChannelManager
from .utils.charter_editor import CharterEditor
from .utils.hs_stats_scraper import hs_stats_scraper
from .utils.on3_scraper import on3_scraper
from .utils.recruiting_scraper import recruiting_scraper
from .utils.schedule_manager import ScheduleManager, get_schedule_manager
from .utils.server_config import FeatureModule, RecruitingSource, server_config
from .utils.summarizer import ChannelSummarizer
# Import timekeeper, summarizer, charter editor, admin manager, version manager, and channel manager
from .utils.timekeeper import (CFB_DYNASTY_WEEKS, TOTAL_WEEKS_PER_SEASON,
                               TimekeeperManager, format_est_time,
                               get_week_actions, get_week_info, get_week_name,
                               get_week_notes, get_week_phase)
from .utils.version_manager import VersionManager


async def check_channel_allowed(interaction) -> bool:
    """
    Check if Harry is allowed to respond in this channel.
    Returns True if allowed, False if not (and sends error message).
    Use this BEFORE defer() - uses interaction.response
    """
    if not interaction.guild:
        return True  # Allow in DMs

    guild_id = interaction.guild.id
    channel_id = interaction.channel.id if interaction.channel else 0

    if server_config.is_channel_enabled(guild_id, channel_id):
        return True

    # Channel not whitelisted
    await interaction.response.send_message(
        "🔇 Harry isn't enabled in this channel.\n"
        "An admin can enable it with `/admin channels enable`",
        ephemeral=True
    )
    return False


async def check_channel_allowed_deferred(interaction) -> bool:
    """
    Check if Harry is allowed to respond in this channel (for use AFTER defer()).
    Returns True if allowed, False if not (and sends error message).
    Use this AFTER defer() - uses interaction.followup
    """
    if not interaction.guild:
        return True  # Allow in DMs

    guild_id = interaction.guild.id
    channel_id = interaction.channel.id if interaction.channel else 0

    if server_config.is_channel_enabled(guild_id, channel_id):
        return True

    # Channel not whitelisted
    await interaction.followup.send(
        "🔇 Harry isn't enabled in this channel.\n"
        "An admin can enable it with `/admin channels enable`",
        ephemeral=True
    )
    return False


async def check_module_enabled(interaction, module) -> bool:
    """
    Check if a module is enabled for this server AND channel is whitelisted.
    Returns True if enabled, False if disabled (and sends error message).
    Use this BEFORE defer() - uses interaction.response
    """
    if not interaction.guild:
        return True  # Allow in DMs

    guild_id = interaction.guild.id
    channel_id = interaction.channel.id if interaction.channel else 0

    # First check channel whitelist
    if not server_config.is_channel_enabled(guild_id, channel_id):
        await interaction.response.send_message(
            "🔇 Harry isn't enabled in this channel.\n"
            "An admin can enable it with `/admin channels enable`",
            ephemeral=True
        )
        return False

    # Then check module
    if server_config.is_module_enabled(guild_id, module):
        return True

    # Module is disabled - send helpful message
    module_names = {
        FeatureModule.CFB_DATA: "CFB Data",
        FeatureModule.LEAGUE: "League Features",
        FeatureModule.HS_STATS: "High School Stats",
        FeatureModule.RECRUITING: "Recruiting",
        FeatureModule.AI_CHAT: "AI Chat",
    }
    name = module_names.get(module, module.value)

    await interaction.response.send_message(
        f"❌ **{name}** module is not enabled on this server.\n"
        f"An admin can enable it with: `/admin config enable {module.value}`",
        ephemeral=True
    )
    return False


async def check_module_enabled_deferred(interaction, module) -> bool:
    """
    Check if a module is enabled for this server AND channel is whitelisted (for use AFTER defer()).
    Returns True if enabled, False if disabled (and sends error message).
    Use this AFTER defer() - uses interaction.followup
    """
    if not interaction.guild:
        return True  # Allow in DMs

    guild_id = interaction.guild.id
    channel_id = interaction.channel.id if interaction.channel else 0

    # First check channel whitelist
    if not server_config.is_channel_enabled(guild_id, channel_id):
        await interaction.followup.send(
            "🔇 Harry isn't enabled in this channel.\n"
            "An admin can enable it with `/admin channels enable`",
            ephemeral=True
        )
        return False

    # Then check module
    if server_config.is_module_enabled(guild_id, module):
        return True

    # Module is disabled - send helpful message
    module_names = {
        FeatureModule.CFB_DATA: "CFB Data",
        FeatureModule.LEAGUE: "League Features",
        FeatureModule.HS_STATS: "High School Stats",
        FeatureModule.RECRUITING: "Recruiting",
        FeatureModule.AI_CHAT: "AI Chat",
    }
    name = module_names.get(module, module.value)

    await interaction.followup.send(
        f"❌ **{name}** module is not enabled on this server.\n"
        f"An admin can enable it with: `/admin config enable {module.value}`",
        ephemeral=True
    )
    return False


# Optional Google Docs integration
try:
    from google_docs_integration import GoogleDocsIntegration
    GOOGLE_DOCS_AVAILABLE = True
except ImportError:
    GOOGLE_DOCS_AVAILABLE = False

# Optional AI integration
try:
    from .ai.ai_integration import AICharterAssistant

    # Check if at least one AI API key is available
    AI_AVAILABLE = bool(os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY'))
except ImportError:
    AI_AVAILABLE = False

# Load environment variables
load_dotenv()

# League-related keywords for classification
LEAGUE_KEYWORDS = [
    'rules', 'charter'
]

def classify_question(question: str) -> tuple[bool, bool, list[str]]:
    """Classify a question and return (is_question, league_related, matched_keywords)"""
    is_question = question.strip().endswith('?')
    league_related = any(f' {keyword} ' in f' {question.lower()} ' for keyword in LEAGUE_KEYWORDS)
    matched_keywords = [kw for kw in LEAGUE_KEYWORDS if f' {kw} ' in f' {question.lower()} '] if league_related else []
    return is_question, league_related, matched_keywords

# Set up comprehensive logging
def setup_logging():
    """
    Set up comprehensive logging for Render deployment.

    Configures logging to both file and console output with proper formatting.
    Creates logs directory if it doesn't exist.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set Discord.py logging level
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)

    # Set our bot logger
    bot_logger = logging.getLogger('CFB26Bot')
    bot_logger.setLevel(logging.INFO)

    return bot_logger

# Initialize logging
logger = setup_logging()

# Bot configuration
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix='!', intents=intents)

# =============================================================================
# COMMAND GROUPS
# Organized command structure for better discoverability
# =============================================================================

# Recruiting data commands (On3/247Sports)
recruiting_group = app_commands.Group(
    name="recruiting",
    description="🏈 Recruiting data - players, rankings, team commits"
)

# High School stats commands (MaxPreps)
hs_group = app_commands.Group(
    name="hs",
    description="🏫 High school football stats from MaxPreps"
)

# CFB data commands (CollegeFootballData.com)
cfb_group = app_commands.Group(
    name="cfb",
    description="📊 College football data - players, rankings, schedules"
)

# Charter/rules commands
charter_group = app_commands.Group(
    name="charter",
    description="📜 League charter - rules, search, history"
)

# League management commands (includes season & timer)
league_group = app_commands.Group(
    name="league",
    description="🏆 League management - staff, season, timer, dynasty"
)

# Admin commands
admin_group = app_commands.Group(
    name="admin",
    description="⚙️ Bot administration - config, channels, permissions"
)

# Background task to clean up expired pending requests
@tasks.loop(minutes=5)
async def cleanup_expired_pending():
    """Clean up expired pending charter updates and rule scans"""
    now = datetime.now().timestamp()

    # Clean up pending charter updates
    if hasattr(bot, 'pending_charter_updates'):
        expired = [msg_id for msg_id, data in bot.pending_charter_updates.items()
                   if now > data.get("expires", 0)]
        for msg_id in expired:
            del bot.pending_charter_updates[msg_id]
        if expired:
            logger.info(f"🧹 Cleaned up {len(expired)} expired charter update(s)")

    # Clean up pending rule scans
    if hasattr(bot, 'pending_rule_scans'):
        expired = [msg_id for msg_id, data in bot.pending_rule_scans.items()
                   if now > data.get("expires", 0)]
        for msg_id in expired:
            del bot.pending_rule_scans[msg_id]
        if expired:
            logger.info(f"🧹 Cleaned up {len(expired)} expired rule scan(s)")

    # Clean up old processed messages (keep last 1000)
    global processed_messages
    if len(processed_messages) > 1000:
        # Convert to list, keep last 1000, convert back to set
        processed_messages = set(list(processed_messages)[-1000:])
        logger.info("🧹 Trimmed processed_messages set")

@cleanup_expired_pending.before_loop
async def before_cleanup():
    await bot.wait_until_ready()

# Initialize Google Docs integration if available
google_docs = None
if GOOGLE_DOCS_AVAILABLE:
    google_docs = GoogleDocsIntegration()

# Initialize AI integration if available
ai_assistant = None
if AI_AVAILABLE:
    ai_assistant = AICharterAssistant()

# Initialize timekeeper manager, summarizer, charter editor, admin manager, version manager, and channel manager
timekeeper_manager = None
channel_summarizer = None
charter_editor = None
admin_manager = None
version_manager = None
channel_manager = None
schedule_manager = None

# Simple rate limiting to prevent duplicate responses
last_message_time = {}
processed_messages = set()  # Track processed message IDs
processed_content = set()  # Track processed content+author combinations
recent_content_times = {}  # Track content + timestamp for time-based deduplication
processing_lock = asyncio.Lock()  # Lock for atomic message processing checks

@bot.event
async def on_ready():
    """
    Called when the bot is ready and connected to Discord.

    Performs initial setup including:
    - Loading league data
    - Syncing slash commands
    - Logging connection status
    """
    global timekeeper_manager, channel_summarizer, charter_editor, admin_manager, version_manager, channel_manager, schedule_manager

    try:
        # Initialize version manager first to get version
        version_manager = VersionManager()
        current_version = version_manager.get_current_version()

        logger.info(f'🏈 CFB 26 League Bot ({bot.user}) v{current_version} has connected to Discord!')
        logger.info(f'🔗 Bot ID: {bot.user.id}')
        logger.info(f'📛 Bot Username: {bot.user.name}')
        logger.info(f'🏷️ Bot Display Name: {bot.user.display_name}')
        logger.info(f'📊 Connected to {len(bot.guilds)} guilds')
        for guild in bot.guilds:
            logger.info(f'   🏠 Guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})')
        logger.info(f'👋 Harry is ready to help with league questions!')

        # Start cleanup task
        if not cleanup_expired_pending.is_running():
            cleanup_expired_pending.start()
            logger.info('🧹 Started cleanup task for expired pending requests')

        # Initialize channel manager
        channel_manager = ChannelManager()
        logger.info(f'🔇 Channel manager initialized ({channel_manager.get_blocked_count()} blocked channels)')

        # Initialize admin manager
        admin_manager = AdminManager()
        logger.info(f'🔐 Admin manager initialized ({admin_manager.get_admin_count()} admin(s) configured)')

        # Initialize timekeeper manager
        timekeeper_manager = TimekeeperManager(bot)
        logger.info('⏰ Timekeeper manager initialized')

        # Restore any saved timer state (wrap in try/except to prevent crashes)
        try:
            await timekeeper_manager.load_saved_state()
        except Exception as e:
            logger.error(f"❌ Failed to load saved timer state: {e}")
            logger.exception("Full error details:")
            # Don't crash - bot can still work without restored timers

        # Initialize channel summarizer (with AI if available)
        channel_summarizer = ChannelSummarizer(ai_assistant if AI_AVAILABLE else None)
        logger.info('📊 Channel summarizer initialized')

        # Initialize charter editor (with AI if available and bot for Discord persistence)
        charter_editor = CharterEditor(ai_assistant if AI_AVAILABLE else None, bot=bot)
        logger.info('📝 Charter editor initialized')

        # Load charter from Discord (persisted across deployments)
        discord_charter = await charter_editor.load_from_discord()
        if discord_charter:
            logger.info('📜 Charter loaded from Discord persistence')
        else:
            logger.info('📜 Using charter from file (no Discord version found)')

        # Initialize server config manager
        server_config.set_bot(bot)
        await server_config.load_from_discord()
        logger.info(f'⚙️ Server config manager initialized ({len(server_config._configs)} server configs loaded)')

        # Initialize schedule manager
        schedule_manager = get_schedule_manager()
        logger.info(f'📅 Schedule manager initialized ({len(schedule_manager.teams)} teams)')

        # Load league data
        await load_league_data()

        # Sync slash commands
        try:
            # Sync to specific guilds for instant command updates (5 seconds instead of 1 hour!)
            guild_ids = [
                1261662233109205144,  # CFB 25 Dynasty Bros
                780882032867803168,   # Test server
                756923098325975161,   # King's and Queen's of the North
            ]

            # Sync to each guild (instant)
            for guild_id in guild_ids:
                guild = discord.Object(id=guild_id)
                bot.tree.copy_global_to(guild=guild)
                synced_guild = await bot.tree.sync(guild=guild)
                logger.info(f'✅ Synced {len(synced_guild)} command(s) to guild {guild_id} (instant!)')

            # Also sync globally for other servers (takes up to 1 hour)
            synced_global = await bot.tree.sync()
            logger.info(f'✅ Synced {len(synced_global)} command(s) globally (may take up to 1 hour)')

            logger.info(f'🎯 Try: /harry what are the league rules?')
            logger.info(f'💬 Or mention @Harry in chat for natural conversations!')
        except Exception as e:
            logger.error(f'❌ Failed to sync commands: {e}')

        # Send combined startup notification to admin channels
        try:
            await send_startup_notification(current_version)
        except Exception as e:
            logger.error(f"❌ Failed to send startup notification: {e}")

    except Exception as e:
        logger.error(f"❌ Critical error in on_ready: {e}")
        logger.exception("Full error details:")
        # Try to send error to admin channels (might fail if server_config not loaded)
        try:
            await send_admin_error("Startup Error", str(e), "on_ready initialization")
        except Exception:
            pass  # Can't send if bot not fully initialized
        # Don't re-raise - let bot continue running
        # The bot will still connect, just without some features

@bot.event
async def on_guild_join(guild):
    """Log when the bot joins a new guild"""
    logger.info(f'🆕 Bot joined new guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})')

    # Try to sync commands to the new guild
    try:
        synced = await bot.tree.sync(guild=guild)
        logger.info(f'✅ Synced {len(synced)} command(s) to new guild {guild.id}')
    except Exception as e:
        logger.error(f'❌ Failed to sync commands to new guild {guild.id}: {e}')

@bot.event
async def on_guild_remove(guild):
    """Log when the bot is removed from a guild"""
    logger.info(f'👋 Bot removed from guild: {guild.name} (ID: {guild.id})')

@bot.event
async def on_message(message):
    """
    Handle regular chat messages and provide intelligent responses.

    Processes messages for:
    - Bot mentions
    - League-related keywords
    - Direct questions
    - Greetings
    - Rivalry responses

    Args:
        message (discord.Message): The message received
    """
    # PRIORITY CHECK: Don't deduplicate @everyone/@here + "advanced" messages (important trigger)
    is_advance_trigger = False
    if message.mention_everyone or (message.role_mentions and len(message.role_mentions) > 0):
        message_lower = message.content.lower()
        if 'advanced' in message_lower:
            is_advance_trigger = True
            logger.info(f"🔥 Detected advance trigger - bypassing deduplication")

    # Prevent duplicate processing of the same message (check first!)
    # Use atomic check-and-add with lock to prevent race conditions
    if not is_advance_trigger:  # Skip deduplication for advance triggers
        global recent_content_times, processing_lock
        content_key = f"{message.author.id}:{message.content}:{message.channel.id}"
        current_time = asyncio.get_event_loop().time()

        # Use lock to make check-and-add atomic
        async with processing_lock:
            # ATOMIC: Check and add message ID immediately to prevent race conditions
            # If it's already in the set, another handler is processing it
            if message.id in processed_messages:
                logger.info(f"⏭️ Skipping duplicate message ID: {message.id}")
                return

            # Add message ID FIRST before any other checks (atomic operation)
            processed_messages.add(message.id)

            # Now check content-based deduplication
            if content_key in processed_content:
                logger.info(f"⏭️ Skipping duplicate content: {content_key[:50]}...")
                return

            # Time-based deduplication: check if same content was processed in last 2 seconds
            if content_key in recent_content_times:
                time_diff = current_time - recent_content_times[content_key]
                if time_diff < 2.0:  # Within 2 seconds
                    logger.info(f"⏭️ Skipping duplicate content (time-based): {content_key[:50]}... (seen {time_diff:.2f}s ago, msg_id={message.id})")
                    return

            # Add to content tracking sets
            processed_content.add(content_key)
            recent_content_times[content_key] = current_time

        # Clean up old entries from recent_content_times (keep last 100 entries)
        if len(recent_content_times) > 100:
            # Remove entries older than 10 seconds
            cutoff_time = current_time - 10.0
            # Filter in place by rebuilding the dict
            keys_to_remove = [k for k, v in recent_content_times.items() if v <= cutoff_time]
            for key in keys_to_remove:
                del recent_content_times[key]

        logger.debug(f"✅ Processing new message: ID={message.id}, Content={content_key[:50]}...")
    else:
        # For advance triggers, just log that we're processing it
        logger.info(f"⚡ Processing advance trigger message: ID={message.id}, from {message.author}")

    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Check if Harry is enabled in this channel (channel whitelist)
    if message.guild:
        channel_id = message.channel.id
        guild_id = message.guild.id
        if not server_config.is_channel_enabled(guild_id, channel_id):
            # Harry is not enabled in this channel - stay silent
            logger.debug(f"🔇 Channel {channel_id} not enabled for Harry in guild {guild_id}")
            return
    else:
        guild_id = 0

    # Check if LEAGUE module is enabled for this server (used for AI context)
    league_enabled = server_config.is_module_enabled(guild_id, FeatureModule.LEAGUE)

    # Check if the bot is @mentioned (only responds to @CFB Bot, not just "harry" in text)
    bot_mentioned = False
    if message.mentions:
        for mention in message.mentions:
            if mention.id == bot.user.id:
                bot_mentioned = True
                break

    # PRIORITY: Check for @everyone/@here + "advanced" to restart timer
    # Available to everyone - no admin check needed
    if message.mention_everyone or (message.role_mentions and len(message.role_mentions) > 0):
        # Check if message contains "advanced" (case-insensitive)
        message_lower = message.content.lower()
        if 'advanced' in message_lower:
            logger.info(f"🔄 @everyone/@channel + 'advanced' detected from {message.author} - restarting timer")

            if not timekeeper_manager:
                logger.warning("⚠️ Timekeeper manager not available for restart")
            else:
                # Stop current timer (if exists)
                await timekeeper_manager.stop_timer(message.channel)

                # Increment the week (manual advance)
                season_info = timekeeper_manager.get_season_week()
                if season_info['season'] and season_info['week'] is not None:
                    old_week = season_info['week']
                    old_week_name = season_info.get('week_name', f"Week {old_week}")
                    await timekeeper_manager.increment_week()
                    # Refresh season_info after increment
                    season_info = timekeeper_manager.get_season_week()
                    new_week_name = season_info.get('week_name', f"Week {season_info['week']}")
                    logger.info(f"📅 Manual advance: {old_week_name} → {new_week_name}")

                # Start new timer (default 48 hours)
                success = await timekeeper_manager.start_timer(message.channel, 48)

                if success:
                    # Get season/week info for display (already refreshed above if incremented)
                    if not season_info:
                        season_info = timekeeper_manager.get_season_week()
                    if season_info['season'] and season_info['week'] is not None:
                        week_name = season_info.get('week_name', f"Week {season_info['week']}")
                        next_week_name = get_week_name(season_info['week'] + 1)
                        phase = season_info.get('phase', 'Regular Season')
                        season_text = f"**Season {season_info['season']}**\n📍 {week_name} → **{next_week_name}**\n🏈 Phase: {phase}\n\n"
                    else:
                        season_text = ""

                    embed = discord.Embed(
                        title="⏰ Advance Countdown Restarted!",
                        description=f"Right then! Timer's been restarted!\n\n🏈 **48 HOUR COUNTDOWN STARTED** 🏈\n\n{season_text}You got **48 hours** to get your bleedin' games done!\n\nI'll be remindin' you lot at:\n• 24 hours remaining\n• 12 hours remaining\n• 6 hours remaining\n• 1 hour remaining\n\nAnd when time's up... well, you'll know! 😈",
                        color=Colors.SUCCESS
                    )
                    status = timekeeper_manager.get_status(message.channel)
                    embed.add_field(
                        name="⏳ Deadline",
                        value=format_est_time(status['end_time'], '%A, %B %d at %I:%M %p'),
                        inline=False
                    )
                    embed.set_footer(text="Harry's Advance Timer 🏈 | Use /league timer_status to check progress")
                    # Send to notification channel (#general)
                    notification_channel = get_notification_channel()
                    if notification_channel:
                        await notification_channel.send(content="@everyone", embed=embed)
                        logger.info(f"⏰ Timer restarted by {message.author} via @everyone + 'advanced' - announced in #{notification_channel.name}")

                        # Send schedule for the new week (if schedule_announcement enabled)
                        if message.guild:
                            await send_week_schedule(notification_channel, season_info.get('week') if season_info else None, message.guild.id)
                        else:
                            await send_week_schedule(notification_channel, season_info.get('week') if season_info else None)
                    else:
                        await message.channel.send(content="@everyone", embed=embed)
                        logger.warning(f"⚠️ #general not found, announced in {message.channel}")
                else:
                    embed = discord.Embed(
                        title="❌ Failed to Restart Timer",
                        description="Couldn't restart the timer, mate. Try using `/league timer` instead!",
                        color=Colors.ERROR
                    )
                    await message.channel.send(embed=embed)
                    logger.error(f"❌ Failed to restart timer for {message.author}")

            # Don't process this message further - timer restart was handled
            return

    # Check if unprompted responses are allowed in this channel
    channel_allows_unprompted = True
    if channel_manager:
        channel_allows_unprompted = channel_manager.can_respond_unprompted(message.channel.id)

    # If bot is mentioned, ALWAYS respond (works in any channel)
    # If bot is NOT mentioned, only respond if channel allows unprompted responses
    if not bot_mentioned and not channel_allows_unprompted:
        return

    # Check if AI_CHAT module is enabled for this server
    # If disabled, Harry won't respond to @mentions or auto-responses
    ai_chat_enabled = server_config.is_module_enabled(guild_id, FeatureModule.AI_CHAT)
    if not ai_chat_enabled:
        # If someone @mentions Harry but AI chat is disabled, let them know
        if bot_mentioned:
            try:
                await message.channel.send(
                    "💬 AI Chat is disabled on this server. "
                    "An admin can enable it with `/admin config enable ai_chat`"
                )
            except Exception:
                pass  # Silently fail if we can't send
        return

    # Comprehensive logging (only after deduplication and channel checks)
    guild_name = message.guild.name if message.guild else "DM"
    logger.info(f"📨 Message received: '{message.content}' from {message.author} in #{message.channel} (Server: {guild_name})")
    logger.info(f"📊 Message details: length={len(message.content)}, type={type(message.content)}, repr={repr(message.content)}")
    logger.info(f"🔍 DEBUG: Starting message processing for: '{message.content}'")
    logger.info(f"🔍 Channel check: current='{message.channel.name}' (ID: {message.channel.id}), bot_mentioned={bot_mentioned}, unprompted_allowed={channel_allows_unprompted}")

    # Skip empty messages
    if not message.content or message.content.strip() == '':
        logger.info(f"⏭️ Skipping empty message from {message.author}")
        return

    # Simple rate limiting to prevent duplicate responses (5 second cooldown per user)
    # Reuse current_time from deduplication check above
    user_id = message.author.id
    if user_id in last_message_time and current_time - last_message_time[user_id] < 5:
        logger.info(f"⏭️ Rate limiting: skipping message from {message.author} (too recent)")
        return
    last_message_time[user_id] = current_time

    # Log mention info (bot_mentioned already set above)
    if message.mentions:
        for mention in message.mentions:
            logger.info(f"🔍 Mention found: {mention} (ID: {mention.id}) vs bot ID: {bot.user.id}")
            if mention.id == bot.user.id:
                break  # Already set bot_mentioned above

    # Very specific rule-related phrases that indicate actual questions about league rules
    rule_keywords = [
        'what are the rules', 'league rules', 'recruiting rules', 'transfer rules', 'charter rules',
        'league policy', 'recruiting policy', 'transfer policy', 'penalty rules', 'difficulty rules',
        'sim rules', 'what are the league rules', 'how do the rules work', 'explain the rules',
        'tell me about the rules', 'league charter', 'recruiting policy', 'transfer policy'
    ]
    contains_keywords = any(keyword in message.content.lower() for keyword in rule_keywords)
    is_question = message.content.strip().endswith('?')

    # Debug: show which keyword was matched
    matched_keywords = [keyword for keyword in rule_keywords if keyword in message.content.lower()]
    if matched_keywords:
        logger.info(f"🔍 Matched rule keywords: {matched_keywords}")

    logger.info(f"🔍 Message analysis: bot_mentioned={bot_mentioned}, contains_keywords={contains_keywords}, is_question={is_question}")

    # Check for greetings (only when bot is @mentioned)
    greetings = ['hi', 'hello', 'hey']
    is_greeting = bot_mentioned and any(greeting in message.content.lower() for greeting in greetings)

    # Check for auto jump-in responses (gated by auto_responses setting)
    guild_id = message.guild.id if message.guild else 0
    channel_id = message.channel.id if message.channel else 0
    auto_responses = server_config.auto_responses_enabled(guild_id, channel_id)

    # Check if LEAGUE module is enabled
    league_enabled = server_config.is_module_enabled(guild_id, FeatureModule.LEAGUE)

    # Team banter responses - only if auto_responses is enabled
    team_keywords = {
        'oregon': 'Fuck Oregon! 🦆💩',
        'ducks': 'Ducks are assholes! 🦆💩',
        'oregon ducks': 'Fuck Oregon! 🦆💩',
        'oregon state': 'BEAVS!',
        'detroit lions': 'Go Lions! 🦁',
        'lions': 'Go Lions! 🦁',
        'tampa bay buccaneers': 'Go Bucs! 🏴‍☠️',
        'buccaneers': 'Go Bucs! 🏴‍☠️',
        'bucs': 'Go Bucs! 🏴‍☠️',
        'chicago bears': 'Da Bears! 🧸',
        'bears': 'Da Bears! 🧸',
        'washington': 'Go Huskies! 🐕',
        'huskies': 'Go Huskies! 🐕',
        'uw': 'Go Huskies! 🐕',
        'alabama': 'Roll Tide! 🐘',
        'crimson tide': 'Roll Tide! 🐘',
        'georgia': 'Wrong Dawgs...',
        'bulldogs': 'Wrong Dawgs...',
        'ohio state': 'Ohio sucks! 🌰',
        'buckeyes': 'Ohio sucks! 🌰',
        'michigan': 'Go Blue! 💙',
        'wolverines': 'Go Blue! 💙',
    } if auto_responses else {}

    # League-specific info responses - only if LEAGUE module is enabled
    info_keywords = {
        'rules': 'Here are the CFB 26 league rules! 📋\n\n[📖 **Full League Charter**](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)',
        'league rules': 'Here are the CFB 26 league rules! 📋\n\n[📖 **Full League Charter**](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)',
        'charter': 'Here\'s the official CFB 26 league charter! 📋\n\n[📖 **Full League Charter**](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)',
        'league charter': 'Here\'s the official CFB 26 league charter! 📋\n\n[📖 **Full League Charter**](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)'
    } if league_enabled else {}

    # Combine both keyword dicts
    all_keywords = {**team_keywords, **info_keywords}

    auto_response = None
    for keyword, response in all_keywords.items():
        if keyword in message.content.lower():
            auto_response = response
            break

    # Don't trigger auto response if it's a clear question (especially with "harry" mentioned)
    if auto_response and (is_question or (bot_mentioned and len(message.content.split()) > 2)):
        auto_response = None
        logger.info(f"🔍 Auto response overridden: question detected or harry mentioned with context")

    logger.info(f"🔍 Response triggers: is_greeting={is_greeting}, auto_response={auto_response is not None}")

    # PRIORITY 1: Handle auto responses immediately (no AI processing needed)
    if auto_response:
        logger.info(f"🏆 Auto response triggered: {auto_response[:50]}...")
        logger.info(f"✅ Bot will respond to message: '{message.content}' (Server: {guild_name})")

        # Don't respond to slash commands
        if message.content.startswith('/'):
            return

        # Add a small delay to make it feel more natural
        await asyncio.sleep(1)

        # Create a friendly response
        embed = discord.Embed(
            title="🏈 Harry's Response",
            color=Colors.PRIMARY
        )
        embed.description = auto_response
        embed.set_footer(text=get_footer_for_guild(guild_id))

        # Send the response immediately
        await message.channel.send(embed=embed)
        return

    # PRIORITY 2: Handle direct mentions and league-related questions with AI
    is_question, league_related_question, matched_keywords = classify_question(message.content)

    logger.info(f"🔍 DEBUG: bot_mentioned={bot_mentioned}, is_question={is_question}, league_related_question={league_related_question}")

    # Direct mentions get AI responses regardless of content
    if bot_mentioned or league_related_question:
        # Enhanced classification logging
        classification_reason = []
        if bot_mentioned:
            classification_reason.append("bot_mentioned=True")
        if league_related_question:
            classification_reason.append(f"league_question=True (matched: {matched_keywords})")

        logger.info(f"🎯 CLASSIFICATION: {message.author} ({message.author.id}) - '{message.content}'")
        logger.info(f"🔍 Classification reason: {', '.join(classification_reason)}")
        logger.info(f"💬 Response triggered: bot_mentioned={bot_mentioned}, league_question={league_related_question}")
        logger.info(f"✅ Bot will respond to message: '{message.content}' (Server: {guild_name})")

        # Don't respond to slash commands
        if message.content.startswith('/'):
            return

        # Add a small delay to make it feel more natural
        await asyncio.sleep(1)

        # Create a friendly response
        embed = discord.Embed(
            title="🏈 Harry's Response",
            color=Colors.PRIMARY
        )

        # Handle AI responses
        # Step 0: Check if this is a "tell X to Y" relay request
        if bot_mentioned:
            # Check for "tell <user> [to] <message>" pattern (to is optional)
            # Handles: "tell @user to message" OR "tell @user message"
            tell_pattern = re.search(r'tell\s+<@!?(\d+)>\s+(?:to\s+)?(.+)', message.content, re.IGNORECASE)
            if tell_pattern:
                target_user_id = int(tell_pattern.group(1))
                relay_message = tell_pattern.group(2).strip()

                # Get the target user
                target_user = message.guild.get_member(target_user_id) if message.guild else None
                if target_user:
                    logger.info(f"📨 Relay request: {message.author} wants to tell {target_user} '{relay_message}'")

                    # Send the relay message
                    embed = discord.Embed(
                        title=f"📨 Message from {message.author.display_name}",
                        description=f"Oi {target_user.mention}! {relay_message}",
                        color=Colors.WARNING
                    )
                    embed.set_footer(text=f"Relayed by Harry 🏈")
                    await message.channel.send(embed=embed)
                    logger.info(f"✅ Relay message sent to {target_user}")
                    return  # Don't continue with AI response
                else:
                    logger.warning(f"⚠️ Could not find target user {target_user_id} for relay")
            else:
                logger.debug(f"🔍 No relay pattern matched for: {message.content[:50]}...")

            # Check if this is a commissioner update request
            commish_patterns = [
                (r'update\s+(?:the\s+)?(?:league\s+)?commish(?:ioner)?\s+to\s+(.+)', 1),
                (r'change\s+(?:the\s+)?(?:league\s+)?commish(?:ioner)?\s+to\s+(.+)', 1),
                (r'set\s+(?:the\s+)?(?:league\s+)?commish(?:ioner)?\s+to\s+(.+)', 1),
                (r'make\s+(.+)\s+(?:the\s+)?(?:league\s+)?commish(?:ioner)', 1),
            ]

            new_commish_name = None
            for pattern, group_num in commish_patterns:
                match = re.search(pattern, message.content, re.IGNORECASE)
                if match and match.lastindex >= group_num:
                    new_commish_name = match.group(group_num)
                    break

            if new_commish_name and bot_mentioned and admin_manager and admin_manager.is_admin(message.author, message):
                # Check if charter editor is available
                if not charter_editor:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="Charter editor not available",
                        color=Colors.ERROR
                    )
                    await message.channel.send(embed=embed)
                    return

                # Clean up the name (remove @mentions, extra whitespace)
                new_commish_name = new_commish_name.strip()

                # Check if it's a user mention
                mention_match = re.search(r'<@!?(\d+)>', new_commish_name)
                if mention_match:
                    user_id = int(mention_match.group(1))
                    try:
                        target_user = await message.guild.fetch_member(user_id) if message.guild else None
                        if target_user:
                            new_commish_name = target_user.display_name
                    except Exception:
                        pass  # User not found, use raw name

                logger.info(f"👔 Commissioner update requested by {message.author}: {new_commish_name}")

                # Update the commissioner
                result = charter_editor.update_commissioner(new_commish_name)

                if result['success']:
                    embed = discord.Embed(
                        title="✅ Commissioner Updated!",
                        description=f"Right then! I've updated the League Commish to **{new_commish_name}**!\n\nCharter has been updated and backed up automatically.",
                        color=Colors.SUCCESS
                    )
                    embed.set_footer(text=f"Updated by {message.author.display_name} 🏈")
                    await message.channel.send(embed=embed)
                    logger.info(f"✅ Commissioner updated to: {new_commish_name}")
                else:
                    embed = discord.Embed(
                        title="❌ Update Failed",
                        description=f"Couldn't update the commissioner, mate!\n\n**Error:** {result['message']}",
                        color=Colors.ERROR
                    )
                    await message.channel.send(embed=embed)
                    logger.error(f"❌ Failed to update commissioner: {result['message']}")

                return  # Don't continue with AI response
            elif new_commish_name and bot_mentioned:
                # User requested update but isn't admin
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="You need to be a bot admin to update the commissioner, ya muppet!",
                    color=Colors.ERROR
                )
                await message.channel.send(embed=embed)
                return

            # Check if this is an interactive charter update request
            charter_update_keywords = [
                'update the', 'change the', 'modify the', 'edit the',
                'add a rule', 'add rule', 'new rule', 'remove the', 'delete the',
                'update rule', 'change rule', 'set the'
            ]

            # Check for charter-related update patterns
            message_lower = message.content.lower()
            is_charter_update = (
                bot_mentioned and
                any(keyword in message_lower for keyword in charter_update_keywords) and
                any(term in message_lower for term in ['rule', 'charter', 'policy', 'schedule', 'advance', 'recruiting', 'transfer', 'quarter', 'difficulty', 'setting'])
            )

            if is_charter_update and admin_manager and admin_manager.is_admin(message.author, message):
                if not charter_editor:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="Charter editor not available",
                        color=Colors.ERROR
                    )
                    await message.channel.send(embed=embed)
                    return

                if not AI_AVAILABLE or not ai_assistant:
                    embed = discord.Embed(
                        title="❌ Error",
                        description="AI not available for charter updates",
                        color=Colors.ERROR
                    )
                    await message.channel.send(embed=embed)
                    return

                logger.info(f"📝 Charter update request from {message.author}: {message.content}")

                # Show thinking message
                thinking_msg = await message.channel.send("🔧 Analyzing your charter update request...")

                try:
                    # Parse the update request
                    parsed = await charter_editor.parse_update_request(message.content)

                    if not parsed or parsed.get("action") == "unknown":
                        error_msg = parsed.get("error", "I couldn't understand that update request") if parsed else "Failed to parse request"
                        await thinking_msg.edit(content=f"❌ {error_msg}\n\nTry being more specific, like:\n• `update the advance time to 10am`\n• `add a rule: no trading during playoffs`\n• `change quarter length to 5 minutes`")
                        return

                    # Generate preview
                    preview = await charter_editor.generate_update_preview(parsed)

                    if not preview:
                        await thinking_msg.edit(content="❌ Couldn't generate a preview for this change. The section might not exist or the request was unclear.")
                        return

                    # Delete thinking message
                    await thinking_msg.delete()

                    # Show before/after preview
                    embed = discord.Embed(
                        title="📝 Charter Update Preview",
                        description=f"**{parsed.get('summary', 'Proposed change')}**",
                        color=Colors.WARNING
                    )

                    # Truncate long text for display
                    before_text = preview.get("before", "N/A")
                    after_text = preview.get("after", "N/A")

                    if len(before_text) > 500:
                        before_text = before_text[:500] + "..."
                    if len(after_text) > 500:
                        after_text = after_text[:500] + "..."

                    embed.add_field(
                        name="📄 BEFORE",
                        value=f"```\n{before_text}\n```",
                        inline=False
                    )
                    embed.add_field(
                        name="📝 AFTER",
                        value=f"```\n{after_text}\n```",
                        inline=False
                    )
                    embed.add_field(
                        name="⚠️ Confirm Change",
                        value="React with ✅ to apply this change, or ❌ to cancel.\n*This will create an automatic backup.*",
                        inline=False
                    )
                    embed.set_footer(text=f"Requested by {message.author.display_name} | Expires in 60 seconds")

                    preview_msg = await message.channel.send(embed=embed)

                    # Add reaction options
                    await preview_msg.add_reaction("✅")
                    await preview_msg.add_reaction("❌")

                    # Store pending update for reaction handler
                    if not hasattr(bot, 'pending_charter_updates'):
                        bot.pending_charter_updates = {}

                    bot.pending_charter_updates[preview_msg.id] = {
                        "user_id": message.author.id,
                        "user_name": message.author.display_name,
                        "new_charter": preview.get("full_new_charter"),
                        "description": parsed.get("summary"),
                        "before": preview.get("before"),
                        "after": preview.get("after"),
                        "expires": datetime.now().timestamp() + 60  # 60 second timeout
                    }

                    logger.info(f"📝 Charter update preview sent, awaiting confirmation from {message.author}")
                    return

                except Exception as e:
                    logger.error(f"❌ Error processing charter update: {e}", exc_info=True)
                    await thinking_msg.edit(content=f"❌ Error processing update: {str(e)}")
                    return

            elif is_charter_update and bot_mentioned:
                # User requested update but isn't admin
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="You need to be a bot admin to update the charter, ya muppet!",
                    color=Colors.ERROR
                )
                await message.channel.send(embed=embed)
                return

            # Check if this is a CFB data query (player, rankings, matchup, etc.)
            if bot_mentioned and cfb_data.is_available:
                message_lower = message.content.lower()

                # Check for bulk player lookup (multiple lines with player names)
                bulk_indicators = [
                    'look up these', 'lookup these', 'find these', 'check these',
                    'these players', 'player list', 'tell me about:', 'about these',
                    'look up:', 'lookup:', 'players:', 'look these up', 'info on these',
                    'stats for these', 'stats on these'
                ]
                content_lines = message.content.strip().split('\n')

                # Position indicators for detecting "Name Position Team" format
                positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'OT', 'OG', 'DL', 'DT', 'DE', 'LB', 'CB', 'DB', 'S', 'K', 'P']

                # Detect bulk lookup: either explicit request or multiple lines with player-like content
                is_bulk_request = any(ind in message_lower for ind in bulk_indicators)

                # Check for multiple player-like lines (with parentheses OR position codes)
                def looks_like_player_line(line):
                    """Check if a line looks like a player entry"""
                    line = line.strip()
                    if not line or len(line) < 5:
                        return False
                    # Has parentheses (Name (Team Position))
                    if '(' in line:
                        return True
                    # Has position code in middle (Name Position Team)
                    line_upper = line.upper()
                    for pos in positions:
                        if f' {pos} ' in line_upper:
                            return True
                    # At least 3 words (First Last Team)
                    words = line.split()
                    if len(words) >= 3 and all(w[0].isupper() for w in words if w):
                        return True
                    return False

                player_like_lines = [l for l in content_lines if looks_like_player_line(l)]
                has_multiple_players = len(player_like_lines) >= 2

                if is_bulk_request or has_multiple_players:
                    logger.info(f"🏈 Bulk lookup triggered: is_bulk_request={is_bulk_request}, player_lines={len(player_like_lines)}")
                    # Try to parse as player list
                    player_list = cfb_data.parse_player_list(message.content)

                    if len(player_list) >= 2:
                        logger.info(f"🏈 Bulk player lookup: {len(player_list)} players detected")
                        thinking_msg = await message.channel.send(f"🔍 Looking up {len(player_list)} players, hang on...")

                        try:
                            results = await cfb_data.lookup_multiple_players(player_list)
                            response = cfb_data.format_bulk_player_response(results)

                            await thinking_msg.delete()

                            # Split into multiple messages if too long
                            if len(response) > 4000:
                                # Send as multiple embeds
                                chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                                for i, chunk in enumerate(chunks):
                                    embed = discord.Embed(
                                        title="🏈 Player Lookup Results" + (f" (Part {i+1})" if len(chunks) > 1 else ""),
                                        description=chunk,
                                        color=Colors.PRIMARY
                                    )
                                    if i == len(chunks) - 1:
                                        embed.set_footer(text="Harry's Bulk Lookup 🏈 | Data from CollegeFootballData.com")
                                    await message.channel.send(embed=embed)
                            else:
                                embed = discord.Embed(
                                    title="🏈 Player Lookup Results",
                                    description=response,
                                    color=Colors.PRIMARY
                                )
                                embed.set_footer(text="Harry's Bulk Lookup 🏈 | Data from CollegeFootballData.com")
                                await message.channel.send(embed=embed)
                            return

                        except Exception as e:
                            logger.error(f"❌ Error in bulk player lookup: {e}", exc_info=True)
                            await thinking_msg.edit(content=f"❌ Error looking up players: {str(e)}")
                            return

                # First check if it's a CFB data query using our comprehensive parser
                cfb_query = cfb_data.parse_cfb_query(message.content)
                query_type = cfb_query.get('type')

                if query_type:
                    logger.info(f"🏈 CFB query detected - type: {query_type}, data: {cfb_query}")
                    thinking_msg = await message.channel.send(f"🔍 Looking that up, hang on...")

                    try:
                        if query_type == 'rankings':
                            team = cfb_query.get('team')
                            if team:
                                result = await cfb_data.get_team_ranking(team)
                                response = cfb_data.format_team_ranking(result)
                                title = f"📊 {team} Rankings"
                                await thinking_msg.delete()
                                embed = discord.Embed(title=title, description=response, color=Colors.PRIMARY)
                                embed.set_footer(text=Footers.CFB_DATA)
                                await message.channel.send(embed=embed)
                            else:
                                result = await cfb_data.get_rankings()
                                fields, week_num = cfb_data.format_rankings(result)
                                title = f"📊 College Football Rankings (Week {week_num})" if week_num else "📊 College Football Rankings"
                                await thinking_msg.delete()
                                embed = discord.Embed(title=title, color=Colors.PRIMARY)
                                for field in fields[:6]:
                                    embed.add_field(name=field['name'], value=field['value'], inline=True)
                                embed.set_footer(text=Footers.CFB_DATA)
                                await message.channel.send(embed=embed)
                            return

                        elif query_type == 'matchup':
                            team1 = cfb_query.get('team1')
                            team2 = cfb_query.get('team2')
                            result = await cfb_data.get_matchup_history(team1, team2)
                            response = cfb_data.format_matchup(result)
                            await thinking_msg.delete()
                            embed = discord.Embed(title=f"🏈 {team1} vs {team2}", description=response, color=Colors.PRIMARY)
                            embed.set_footer(text=Footers.CFB_DATA)
                            await message.channel.send(embed=embed)
                            return

                        elif query_type == 'schedule':
                            team = cfb_query.get('team')
                            result = await cfb_data.get_team_schedule(team)
                            response = cfb_data.format_schedule(result, team)
                            await thinking_msg.delete()
                            embed = discord.Embed(title=f"📅 {team} Schedule", description=response, color=Colors.PRIMARY)
                            embed.set_footer(text=Footers.CFB_DATA)
                            await message.channel.send(embed=embed)
                            return

                        elif query_type == 'draft':
                            team = cfb_query.get('team')
                            result = await cfb_data.get_draft_picks(team)
                            response = cfb_data.format_draft_picks(result, team)
                            await thinking_msg.delete()
                            embed = discord.Embed(title=f"🏈 NFL Draft Picks", description=response, color=Colors.PRIMARY)
                            embed.set_footer(text=Footers.CFB_DATA)
                            await message.channel.send(embed=embed)
                            return

                        elif query_type == 'transfers':
                            team = cfb_query.get('team')
                            result = await cfb_data.get_team_transfers(team)
                            response = cfb_data.format_transfers(result, team)
                            await thinking_msg.delete()
                            embed = discord.Embed(title=f"🔄 {team} Transfers", description=response, color=Colors.PRIMARY)
                            embed.set_footer(text=Footers.CFB_DATA)
                            await message.channel.send(embed=embed)
                            return

                        elif query_type == 'betting':
                            team1 = cfb_query.get('team1')
                            team2 = cfb_query.get('team2')
                            result, query_info = await cfb_data.get_betting_lines(team=team1)
                            response = cfb_data.format_betting_lines(result, query_info)
                            await thinking_msg.delete()
                            embed = discord.Embed(title=f"💰 Betting Lines", description=response, color=Colors.PRIMARY)
                            embed.set_footer(text=Footers.CFB_DATA)
                            await message.channel.send(embed=embed)
                            return

                        elif query_type == 'ratings':
                            team = cfb_query.get('team')
                            result = await cfb_data.get_team_ratings(team)
                            response = cfb_data.format_ratings(result)
                            await thinking_msg.delete()
                            embed = discord.Embed(title=f"📈 {team} Ratings", description=response, color=Colors.PRIMARY)
                            embed.set_footer(text=Footers.CFB_DATA)
                            await message.channel.send(embed=embed)
                            return

                    except Exception as e:
                        logger.error(f"❌ Error in CFB query: {e}", exc_info=True)
                        await thinking_msg.edit(content=f"❌ Error looking that up: {str(e)}")
                        return

                # Check for high school player lookup (HS_STATS module)
                hs_keywords = ['high school', 'hs stats', 'hs player', 'recruit', 'maxpreps', 'high schooler']
                if any(kw in message_lower for kw in hs_keywords):
                    # Check if HS_STATS module is enabled
                    if server_config.is_module_enabled(message.guild.id, FeatureModule.HS_STATS):
                        if hs_stats_scraper.is_available:
                            # Parse the HS player query
                            # Look for patterns like "HS stats for John Smith (TX)" or "recruit John Smith from Texas"
                            hs_patterns = [
                                r'(?:hs\s+(?:stats|player)|high\s+school(?:er)?\s+(?:stats)?|recruit|maxpreps)\s+(?:for\s+)?(.+?)(?:\s+from\s+|\s*\()([\w\s]+)\)?',
                                r'(?:hs\s+(?:stats|player)|high\s+school(?:er)?\s+(?:stats)?|recruit|maxpreps)\s+(?:for\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
                                r'(?:what do you know about|tell me about|lookup|info on)\s+(?:hs\s+|high\s+school\s+)?recruit\s+(.+?)(?:\s+from\s+|\s*\()([\w\s]+)\)?',
                            ]

                            player_name = None
                            state = None

                            for pattern in hs_patterns:
                                match = re.search(pattern, message.content, re.IGNORECASE)
                                if match:
                                    player_name = match.group(1).strip()
                                    if len(match.groups()) > 1 and match.group(2):
                                        state = match.group(2).strip()
                                    break

                            # Fallback: extract any capitalized names after keywords
                            if not player_name:
                                for kw in hs_keywords:
                                    if kw in message_lower:
                                        # Look for capitalized words after the keyword
                                        idx = message_lower.find(kw)
                                        after_kw = message.content[idx + len(kw):].strip()
                                        # Find capitalized name pattern
                                        name_match = re.search(r'(?:for\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', after_kw)
                                        if name_match:
                                            player_name = name_match.group(1)
                                        break

                            if player_name and len(player_name) > 3:
                                logger.info(f"🏈 HS stats lookup request: {player_name}" + (f" ({state})" if state else ""))
                                thinking_msg = await message.channel.send("🔍 Looking up high school stats, hang on...")

                                try:
                                    player_data = await hs_stats_scraper.lookup_player(player_name, state)
                                    await thinking_msg.delete()

                                    if player_data:
                                        formatted = hs_stats_scraper.format_player_stats(player_data)
                                        embed = discord.Embed(
                                            title="🏈 High School Stats",
                                            description=formatted,
                                            color=Colors.HS_STATS
                                        )
                                        embed.set_footer(text=Footers.HS_STATS)
                                        await message.channel.send(embed=embed)
                                    else:
                                        embed = discord.Embed(
                                            title=f"🔍 No Results for '{player_name}'",
                                            description=(
                                                f"Couldn't find a high school player matching **{player_name}**.\n\n"
                                                "**Tips:**\n"
                                                "• Check the spelling\n"
                                                "• Add a state (e.g., 'HS stats for John Smith (TX)')\n"
                                                "• Use `/hs_stats` for more options"
                                            ),
                                            color=Colors.WARNING
                                        )
                                        embed.set_footer(text=Footers.HS_STATS)
                                        await message.channel.send(embed=embed)
                                    return

                                except Exception as e:
                                    logger.error(f"❌ Error in HS stats lookup: {e}", exc_info=True)
                                    await thinking_msg.edit(content=f"❌ Error looking up HS stats: {str(e)}")
                                    return
                        else:
                            await message.channel.send(
                                "❌ HS stats scraper not available. Missing dependencies: `pip install httpx beautifulsoup4`"
                            )
                            return

                # Check for transfer portal player lookup (RECRUITING module)
                portal_keywords = ['portal player', 'transfer portal', 'portal recruit', 'transfer player', 'in the portal']
                if any(kw in message_lower for kw in portal_keywords):
                    # Check if RECRUITING module is enabled
                    if server_config.is_module_enabled(message.guild.id, FeatureModule.RECRUITING):
                        # Extract player name from message
                        player_name = None
                        team_hint = None

                        # Try patterns like "portal player John Smith" or "John Smith in the portal"
                        for kw in portal_keywords:
                            if kw in message_lower:
                                idx = message_lower.find(kw)
                                # Look for name after keyword
                                after_kw = message.content[idx + len(kw):].strip()
                                # Look for capitalized name pattern
                                name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', after_kw)
                                if name_match:
                                    player_name = name_match.group(1)
                                    break
                                # Also try before the keyword for "John Smith in the portal"
                                before_kw = message.content[:idx].strip()
                                name_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$', before_kw)
                                if name_match:
                                    player_name = name_match.group(1)
                                    break

                        # Check for team hint like "from Alabama"
                        team_match = re.search(r'from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', message.content)
                        if team_match:
                            team_hint = team_match.group(1)

                        if player_name and len(player_name) > 3:
                            logger.info(f"🔄 Portal lookup request: {player_name}" + (f" ({team_hint})" if team_hint else ""))
                            thinking_msg = await message.channel.send("🔄 Looking up transfer portal player, hang on...")

                            try:
                                # Get recruiting data from On3
                                recruit_data = None
                                try:
                                    recruit_data = await on3_scraper.search_recruit(player_name)
                                except Exception as e:
                                    logger.warning(f"⚠️ On3 lookup failed for {player_name}: {e}")

                                # Get college stats
                                college_stats = None
                                try:
                                    college_stats = await cfb_data.get_full_player_info(player_name, team_hint)
                                except Exception as e:
                                    logger.warning(f"⚠️ CFB lookup failed for {player_name}: {e}")

                                await thinking_msg.delete()

                                if recruit_data or college_stats:
                                    embed = discord.Embed(
                                        title=f"🔄 Transfer Portal: {player_name}",
                                        color=Colors.RECRUITING if hasattr(Colors, 'RECRUITING') else 0xffd700
                                    )

                                    # Add recruiting data
                                    if recruit_data:
                                        recruit_lines = []
                                        stars = recruit_data.get('stars', 0)
                                        rating = recruit_data.get('rating')
                                        if rating:
                                            star_display = '⭐' * stars if stars else ''
                                            recruit_lines.append(f"**Rating:** {rating} ({star_display})")
                                        if recruit_data.get('national_rank'):
                                            recruit_lines.append(f"**National Rank:** #{recruit_data['national_rank']}")
                                        if recruit_data.get('committed_to'):
                                            recruit_lines.append(f"**Committed to:** {recruit_data['committed_to']} ✅")
                                        if recruit_lines:
                                            embed.add_field(name="📊 Recruiting", value='\n'.join(recruit_lines), inline=False)

                                    # Add college stats
                                    if college_stats:
                                        stats_lines = []
                                        team_name = college_stats.get('team', '')
                                        if team_name:
                                            stats_lines.append(f"**Previous:** {team_name}")
                                        stats = college_stats.get('stats', {})
                                        if stats:
                                            years = sorted(stats.keys(), reverse=True)
                                            if years:
                                                y = years[0]
                                                ys = stats[y]
                                                if ys.get('receiving', {}).get('YDS'):
                                                    stats_lines.append(f"**{y}:** {ys['receiving'].get('REC', 0)} REC | {ys['receiving']['YDS']} YDS | {ys['receiving'].get('TD', 0)} TD")
                                                elif ys.get('rushing', {}).get('YDS'):
                                                    stats_lines.append(f"**{y}:** {ys['rushing'].get('CAR', 0)} CAR | {ys['rushing']['YDS']} YDS | {ys['rushing'].get('TD', 0)} TD")
                                                elif ys.get('passing', {}).get('YDS'):
                                                    stats_lines.append(f"**{y}:** {ys['passing']['YDS']} YDS | {ys['passing'].get('TD', 0)} TD | {ys['passing'].get('INT', 0)} INT")
                                        if stats_lines:
                                            embed.add_field(name="🏈 College Stats", value='\n'.join(stats_lines), inline=False)

                                    embed.set_footer(text="Harry's Portal Tracker 🔄 | Use /recruiting player for more details")
                                    await message.channel.send(embed=embed)
                                else:
                                    embed = discord.Embed(
                                        title=f"❓ Not Found: {player_name}",
                                        description="Couldn't find this player in transfer portal data.\n\nTry `/recruiting player` for more options.",
                                        color=Colors.WARNING
                                    )
                                    await message.channel.send(embed=embed)
                                return

                            except Exception as e:
                                logger.error(f"❌ Error in portal lookup: {e}", exc_info=True)
                                await thinking_msg.edit(content=f"❌ Error looking up portal player: {str(e)}")
                                return

                # Fall back to player lookup if no other query type matched
                player_keywords = ['from', 'player', 'stats', 'what do you know', 'tell me about', 'who is', 'info on', 'lookup']
                # Check for player-related queries (but not league rule queries)
                if any(kw in message_lower for kw in player_keywords) and not any(term in message_lower for term in ['rule', 'charter', 'policy', 'advance']):
                    # Use the player_lookup parser
                    parsed = cfb_data.parse_player_query(message.content)
                    if parsed.get('name') and len(parsed['name']) > 2:
                        # DUPLICATE CHECK: Use a unique key for this specific lookup
                        lookup_key = f"player_lookup:{message.id}:{parsed['name']}"
                        if hasattr(bot, '_active_player_lookups') and lookup_key in bot._active_player_lookups:
                            logger.warning(f"⚠️ DUPLICATE player lookup blocked: {lookup_key}")
                            return
                        if not hasattr(bot, '_active_player_lookups'):
                            bot._active_player_lookups = set()
                        bot._active_player_lookups.add(lookup_key)

                        logger.info(f"🏈 Player lookup request from {message.author}: {message.content} [key={lookup_key}]")

                        thinking_msg = await message.channel.send("🔍 Looking up that player, hang on...")

                        try:
                            name = parsed.get('name')
                            team = parsed.get('team')

                            logger.info(f"🔍 Searching for player: {name}" + (f" from {team}" if team else ""))

                            player_info = await cfb_data.get_full_player_info(name, team)

                            await thinking_msg.delete()

                            if player_info:
                                response = cfb_data.format_player_response(player_info)
                                embed = discord.Embed(
                                    title="🏈 Player Info",
                                    description=response,
                                    color=Colors.PRIMARY
                                )

                                # Try to find recruiting/portal data for this player
                                is_portal_player = False
                                try:
                                    recruit_data = await on3_scraper.search_recruit(name)
                                    if recruit_data and recruit_data.get('is_transfer'):
                                        is_portal_player = True
                                        recruit_lines = []
                                        stars = recruit_data.get('stars', 0)
                                        rating = recruit_data.get('rating')
                                        if rating:
                                            star_display = '⭐' * stars if stars else ''
                                            recruit_lines.append(f"**Rating:** {rating} ({star_display})")
                                        if recruit_data.get('national_rank'):
                                            recruit_lines.append(f"**Rank:** #{recruit_data['national_rank']} Nationally")
                                        if recruit_data.get('committed_to'):
                                            recruit_lines.append(f"**Committed to:** {recruit_data['committed_to']} ✅")
                                        predictions = recruit_data.get('top_predictions', [])
                                        if predictions:
                                            pred_str = ", ".join([f"{p['team']} ({p.get('prediction', '?')})" for p in predictions[:3]])
                                            recruit_lines.append(f"**Predictions:** {pred_str}")
                                        if recruit_lines:
                                            embed.add_field(
                                                name="🔄 Transfer Portal",
                                                value='\n'.join(recruit_lines),
                                                inline=False
                                            )
                                except Exception as e:
                                    logger.debug(f"No recruiting data for {name}: {e}")

                                # Check if it's an Oregon player and add snark (Harry always hates Oregon)
                                player_team = player_info.get('player', {}).get('team', '').lower()
                                if 'oregon' in player_team and 'oregon state' not in player_team:
                                    embed.set_footer(text="Harry's Player Lookup 🏈 | Though why you'd care about a Duck is beyond me...")
                                elif is_portal_player:
                                    embed.set_footer(text="Harry's Portal Tracker 🔄 | CFB + Recruiting combined")
                                else:
                                    embed.set_footer(text=Footers.PLAYER_LOOKUP)

                                await message.channel.send(embed=embed)
                            else:
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
                                await message.channel.send(embed=embed)
                            # Clean up lookup key
                            if hasattr(bot, '_active_player_lookups') and lookup_key in bot._active_player_lookups:
                                bot._active_player_lookups.discard(lookup_key)
                            return

                        except Exception as e:
                            logger.error(f"❌ Error in player lookup: {e}", exc_info=True)
                            await thinking_msg.edit(content=f"❌ Error looking up player: {str(e)}")
                            # Clean up lookup key
                            if hasattr(bot, '_active_player_lookups') and lookup_key in bot._active_player_lookups:
                                bot._active_player_lookups.discard(lookup_key)
                            return

            # Check if this is a rule scan request (e.g., "scan #channel for rules")
            rule_scan_patterns = [
                r'scan\s+(?:<#(\d+)>|#?(\w+[-\w]*))\s+for\s+(?:rule|voting|changes)',
                r'check\s+(?:<#(\d+)>|#?(\w+[-\w]*))\s+for\s+(?:rule|voting|changes)',
                r'find\s+(?:rule|voting)\s+(?:changes\s+)?in\s+(?:<#(\d+)>|#?(\w+[-\w]*))',
                r'what\s+rules?\s+(?:passed|changed|were voted)\s+in\s+(?:<#(\d+)>|#?(\w+[-\w]*))',
            ]

            channel_to_scan = None
            for pattern in rule_scan_patterns:
                match = re.search(pattern, message.content, re.IGNORECASE)
                if match:
                    # Try to get channel from mention or name
                    channel_id = match.group(1) if match.group(1) else None
                    channel_name = match.group(2) if len(match.groups()) > 1 and match.group(2) else None

                    if channel_id:
                        channel_to_scan = message.guild.get_channel(int(channel_id))
                    elif channel_name and message.guild:
                        # Try to find channel by name
                        for ch in message.guild.text_channels:
                            if ch.name.lower() == channel_name.lower() or channel_name.lower() in ch.name.lower():
                                channel_to_scan = ch
                                break
                    break

            if channel_to_scan and bot_mentioned and admin_manager and admin_manager.is_admin(message.author, message):
                if not charter_editor or not channel_summarizer or not AI_AVAILABLE:
                    await message.channel.send("❌ Required components not available for rule scanning")
                    return

                logger.info(f"📜 Rule scan request from {message.author} for #{channel_to_scan.name}")

                thinking_msg = await message.channel.send(f"🔍 Scanning #{channel_to_scan.name} for rule changes...")

                try:
                    # Fetch and analyze messages
                    messages_list = await channel_summarizer.fetch_messages(channel_to_scan, hours=168, limit=500)

                    if not messages_list:
                        await thinking_msg.edit(content=f"❌ No messages found in #{channel_to_scan.name}")
                        return

                    formatted = [f"[{m.author.display_name}]: {m.content}" for m in messages_list]
                    rule_changes = await charter_editor.find_rule_changes_in_messages(formatted, channel_to_scan.name)

                    await thinking_msg.delete()

                    if not rule_changes:
                        embed = discord.Embed(
                            title=f"📜 Rule Scan: #{channel_to_scan.name}",
                            description="No rule changes or votes found in the last week.",
                            color=Colors.ADMIN
                        )
                        await message.channel.send(embed=embed)
                        return

                    # Show found rules
                    embed = discord.Embed(
                        title=f"📜 Rule Changes Found in #{channel_to_scan.name}",
                        description=f"Found **{len(rule_changes)}** rule changes/votes",
                        color=Colors.PRIMARY
                    )

                    passed_rules = []
                    for i, rule in enumerate(rule_changes[:8], 1):
                        status = rule.get("status", "unknown")
                        emoji = {"passed": "✅", "failed": "❌", "proposed": "📋", "decided": "✅"}.get(status, "❓")

                        votes = ""
                        if rule.get("votes_for") is not None:
                            votes = f" ({rule.get('votes_for', 0)}-{rule.get('votes_against', 0)})"

                        rule_text = rule.get("rule", "Unknown rule")
                        context = rule.get("context", "")

                        field_value = f"📝 {rule_text}"
                        if context and context.strip() and context.lower() != rule_text.lower():
                            field_value += f"\n> _{context}_"

                        if len(field_value) > 500:
                            field_value = field_value[:497] + "..."

                        embed.add_field(name=f"{emoji} {status.upper()}{votes}", value=field_value, inline=False)

                        if status in ["passed", "decided"]:
                            passed_rules.append(rule)

                    if passed_rules:
                        embed.add_field(
                            name="🔧 Update Charter?",
                            value=f"Found **{len(passed_rules)}** passed rules. React with 📝 to generate charter updates.",
                            inline=False
                        )

                    msg = await message.channel.send(embed=embed)

                    if passed_rules:
                        await msg.add_reaction("📝")
                        if not hasattr(bot, 'pending_rule_scans'):
                            bot.pending_rule_scans = {}
                        bot.pending_rule_scans[msg.id] = {
                            "user_id": message.author.id,
                            "user_name": message.author.display_name,
                            "rule_changes": passed_rules,
                            "channel_name": channel_to_scan.name,
                            "expires": datetime.now().timestamp() + 600  # 10 minute timeout
                        }

                except Exception as e:
                    logger.error(f"❌ Error in rule scan: {e}", exc_info=True)
                    await thinking_msg.edit(content=f"❌ Error scanning: {str(e)}")

                return

            elif channel_to_scan and bot_mentioned:
                embed = discord.Embed(
                    title="❌ Permission Denied",
                    description="You need to be a bot admin to scan for rules, ya muppet!",
                    color=Colors.ERROR
                )
                await message.channel.send(embed=embed)
                return

        # Step 1: Check if this is a channel summary request
        question_lower = message.content.lower()

        # Keywords that indicate a summary request
        summary_keywords = [
            'summarize', 'summary', 'what happened', 'tell me what happened',
            'recap', 'what\'s been going on', 'what passed', 'what was approved',
            'what was voted', 'what rules passed', 'what rules were approved',
            'what did we vote', 'what did we approve', 'what changed'
        ]

        # Check for time references (e.g., "last 3 hours", "past 24 hours", "in the last day")
        time_patterns = [
            r'(\d+)\s*(?:hour|hr|h)',
            r'last\s+(\d+)\s*(?:hour|hr|h)',
            r'past\s+(\d+)\s*(?:hour|hr|h)',
            r'in\s+the\s+last\s+(\d+)\s*(?:hour|hr|h)',
            r'over\s+the\s+last\s+(\d+)\s*(?:hour|hr|h)'
        ]

        summary_hours = None
        has_time_reference = False
        for pattern in time_patterns:
            hours_match = re.search(pattern, question_lower)
            if hours_match:
                summary_hours = int(hours_match.group(1))
                has_time_reference = True
                break

        # Check if it's asking about channel activity/history
        is_asking_about_channel = any(keyword in question_lower for keyword in summary_keywords)

        # It's a summary request if:
        # 1. Has explicit summary keywords (summarize, recap, etc.)
        # 2. Has time reference AND asks about what happened/passed/approved (channel activity)
        is_summary_request = is_asking_about_channel or (has_time_reference and any(
            phrase in question_lower for phrase in ['what happened', 'what passed', 'what was', 'what did', 'what changed', 'what rules']
        ))

        # Log summary detection for debugging
        if bot_mentioned:
            logger.info(f"🔍 Summary detection: has_time={has_time_reference}, asking_about_channel={is_asking_about_channel}, is_summary={is_summary_request}, hours={summary_hours}")

        # If it's a summary request and bot is mentioned, use the summarizer
        if is_summary_request and bot_mentioned and channel_summarizer:
            try:
                hours = summary_hours or 24  # Default to 24 hours if not specified
                logger.info(f"📊 Summary requested via @mention by {message.author} - {hours} hours")

                # Use summarizer to generate summary
                summary = await channel_summarizer.get_channel_summary(
                    message.channel,
                    hours=hours,
                    focus=None,  # Could extract focus from message if needed
                    limit=500
                )

                if summary:
                    embed = discord.Embed(
                        title=f"📊 Channel Summary - Last {hours} {'Hour' if hours == 1 else 'Hours'}",
                        description=summary,
                        color=Colors.SUCCESS
                    )
                    embed.add_field(
                        name="📍 Channel",
                        value=f"#{message.channel.name}",
                        inline=True
                    )
                    embed.add_field(
                        name="⏰ Time Period",
                        value=f"Last {hours} {'hour' if hours == 1 else 'hours'}",
                        inline=True
                    )
                    embed.set_footer(text=f"Harry's Channel Summary 🏈 | Requested by {message.author.display_name}")
                    await message.channel.send(embed=embed)
                    logger.info(f"✅ Summary delivered via @mention for #{message.channel.name}")
                    return  # Don't continue with AI response
                else:
                    # Fall through to AI response if summarizer fails
                    pass
            except Exception as e:
                logger.error(f"❌ Error generating summary via @mention: {e}")
                # Fall through to AI response

        # Step 2: Try AI with charter content first
        ai_response = None
        if AI_AVAILABLE and ai_assistant:
            try:
                question = message.content
                if bot_mentioned:
                    # Remove the mention from the question
                    question = question.replace(f'<@{bot.user.id}>', '').strip()

                # Use league-specific AI logic for mentions or allowed channels
                # Bot was mentioned or channel allows unprompted responses
                if bot_mentioned or channel_allows_unprompted:
                    # Determine if this is a league-related question
                    is_league_related = any(f' {keyword} ' in f' {question.lower()} ' for keyword in LEAGUE_KEYWORDS)

                    # Get personality prompt based on server settings
                    personality = server_config.get_personality_prompt(guild_id)

                    if is_league_related:
                        # Step 1: Try AI with charter content for league questions
                        charter_question = f"""{personality} Answer this question using ONLY the league charter content:

Question: {question}

If the charter contains relevant information, provide a helpful answer. If not, respond with "NO_CHARTER_INFO"."""

                        # Log the question and who asked it
                        logger.info(f"🤖 League AI Question from {message.author} ({message.author.id}): {question}")
                        logger.info(f"📝 Full AI prompt: {charter_question[:200]}...")

                        # Include league context since this is a league-related question
                        ai_response = await ai_assistant.ask_ai(charter_question, f"{message.author} ({message.author.id})", include_league_context=league_enabled)

                        # Step 2: If no charter info, try general AI search without charter context
                        if ai_response and "NO_CHARTER_INFO" in ai_response:
                            logger.info("No charter info found, trying general AI search without charter context")
                            general_question = f"""{personality} Answer this question about CFB 26 league rules, recruiting, transfers, or dynasty management:

Question: {question}

IMPORTANT: Only provide a direct answer if you're confident about CFB 26 league specifics. If you're not sure about the exact league rules, say "I don't have that specific information about our league rules, but you can check our full charter for the official details."

Keep responses concise and helpful. Do NOT mention "charter" unless you truly don't know the answer."""

                            # Log the general AI question
                            logger.info(f"🤖 General AI Question from {message.author} ({message.author.id}): {question}")
                            logger.info(f"📝 General AI prompt: {general_question[:200]}...")
                            logger.info("🌍 Fallback to general AI without charter context")

                            # Use AI without charter context since charter had no info
                            general_context = personality

                            # Call OpenAI directly with general context (include league context only if LEAGUE enabled)
                            ai_response = await ai_assistant.ask_openai(general_question, general_context, personality_prompt=personality, include_league_context=league_enabled)
                            if not ai_response:
                                # Fallback to Anthropic
                                ai_response = await ai_assistant.ask_anthropic(general_question, general_context, personality_prompt=personality, include_league_context=league_enabled)
                    else:
                        # For non-league questions, use general AI WITHOUT charter context
                        general_question = f"""{personality} Answer this question helpfully and accurately:

Question: {question}

Please provide a helpful, accurate answer."""

                        # Log the general AI question
                        logger.info(f"🤖 General AI Question from {message.author} ({message.author.id}): {question}")
                        logger.info(f"📝 General AI prompt: {general_question[:200]}...")
                        logger.info("🌍 General question - using AI without charter context")

                        # Use AI without charter context (like /ask command)
                        general_context = personality

                        # Call OpenAI directly with general context (include league context only if LEAGUE enabled)
                        ai_response = await ai_assistant.ask_openai(general_question, general_context, personality_prompt=personality, include_league_context=league_enabled)
                        if not ai_response:
                            # Fallback to Anthropic
                            ai_response = await ai_assistant.ask_anthropic(general_question, general_context, personality_prompt=personality, include_league_context=league_enabled)
                else:
                    # For non-allowed channels, this should only happen with slash commands
                    # Use general AI without league context
                    personality = server_config.get_personality_prompt(guild_id)
                    general_question = f"""{personality} Answer this question helpfully and accurately:

Question: {question}

Please provide a helpful, accurate answer. This is a general conversation, not about league rules."""

                    logger.info(f"🤖 General AI Question from {message.author} ({message.author.id}): {question}")
                    logger.info(f"📝 General AI prompt: {general_question[:200]}...")
                    logger.info("🌍 General question - using AI without charter context")

                    # Use AI without charter context
                    general_context = personality

                    # Call OpenAI directly with general context (no league context for non-allowed channels)
                    ai_response = await ai_assistant.ask_openai(general_question, general_context, personality_prompt=personality, include_league_context=False)
                    if not ai_response:
                        # Fallback to Anthropic
                        ai_response = await ai_assistant.ask_anthropic(general_question, general_context, include_league_context=False)

            except Exception as e:
                logger.error(f"AI error: {e}")
                ai_response = None

        # Use AI response if available, otherwise fall back to generic
        # Note: guild_id and league_enabled already calculated at the start of on_message

        if ai_response and "NO_CHARTER_INFO" not in ai_response:
            embed.description = ai_response
            # Only add charter link if LEAGUE enabled AND AI indicates it doesn't know the answer
            if league_enabled and ("check the full charter" in ai_response.lower() or "charter" in ai_response.lower()):
                embed.add_field(
                    name="📖 Full League Charter",
                    value="[View Complete Rules](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
                    inline=False
                )
        else:
            # Generic fallback - different message based on LEAGUE status
            if league_enabled:
                embed.description = "Well, you stumped me! But check our charter below - it has all the official CFB 26 league rules, recruiting policies, and dynasty management guidelines!"
                embed.add_field(
                    name="📖 Full League Charter",
                    value="[View Complete Rules](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
                    inline=False
                )
            else:
                embed.description = "Hmm, I'm not quite sure about that one! Try asking me about college football players, teams, rankings, or schedules."

        embed.set_footer(text=get_footer_for_guild(guild_id))

        # Send the response
        await message.channel.send(embed=embed)

    # PRIORITY 3: Handle direct mentions that aren't league-related
    elif bot_mentioned:
        logger.info(f"💬 Direct mention but not league-related: '{message.content}' (Server: {guild_name})")

        # Don't respond to slash commands
        if message.content.startswith('/'):
            return

        # Add a small delay to make it feel more natural
        await asyncio.sleep(1)

        # Create a friendly response
        embed = discord.Embed(
            title="🏈 Harry's Response",
            color=Colors.PRIMARY
        )
        guild_id = message.guild.id if message.guild else 0
        league_enabled = server_config.is_module_enabled(guild_id, FeatureModule.LEAGUE)

        if league_enabled:
            embed.description = "Hey there! I'm Harry, your CFB 26 league assistant! I'm here to help with league rules, recruiting, transfers, dynasty management, and all things college football. Ask me about our league charter, game settings, or anything CFB 26 related!"
            embed.add_field(
                name="📖 Full League Charter",
                value="[View Complete Rules](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
                inline=False
            )
        else:
            embed.description = "Hey there! I'm Harry, your college football assistant! I can help with player lookups, team stats, rankings, schedules, and all things CFB. Try `/player` or `/rankings` to get started!"
        embed.set_footer(text=get_footer_for_guild(guild_id))

        # Send the response
        await message.channel.send(embed=embed)

    else:
        logger.info(f"❌ No response triggers met")

    # Process other bot commands
    await bot.process_commands(message)

async def safe_clear_reactions(message):
    """Safely clear reactions - doesn't fail if bot lacks Manage Messages permission"""
    try:
        await message.clear_reactions()
    except discord.errors.Forbidden:
        logger.debug("Could not clear reactions - missing Manage Messages permission")
    except Exception as e:
        logger.debug(f"Could not clear reactions: {e}")


@bot.event
async def on_reaction_add(reaction, user):
    """Handle emoji reactions"""
    logger.debug(f"🔔 Reaction event: {reaction.emoji} by {user.display_name} on msg {reaction.message.id}")

    # Ignore reactions from the bot itself
    if user == bot.user:
        logger.debug("  Ignoring bot's own reaction")
        return

    # Only respond to reactions on Harry's messages
    if reaction.message.author != bot.user:
        logger.debug("  Ignoring reaction on non-Harry message")
        return

    logger.info(f"📝 Processing reaction: {reaction.emoji} from {user.display_name}")

    # Handle charter update confirmations
    if hasattr(bot, 'pending_charter_updates') and reaction.message.id in bot.pending_charter_updates:
        pending = bot.pending_charter_updates[reaction.message.id]

        # Only the original requester can confirm/cancel
        if user.id != pending["user_id"]:
            return

        # Check if expired
        if datetime.now().timestamp() > pending["expires"]:
            del bot.pending_charter_updates[reaction.message.id]
            await reaction.message.edit(embed=discord.Embed(
                title="⏰ Update Expired",
                description="This charter update request has expired. Please try again.",
                color=Colors.WARNING
            ))
            return

        if str(reaction.emoji) == "✅":
            # Apply the update
            if charter_editor and pending.get("new_charter"):
                success = await charter_editor.apply_update(
                    new_charter=pending["new_charter"],
                    user_id=pending["user_id"],
                    user_name=pending["user_name"],
                    description=pending["description"],
                    before_text=pending.get("before"),
                    after_text=pending.get("after")
                )

                if success:
                    embed = discord.Embed(
                        title="✅ Charter Updated!",
                        description=f"**{pending['description']}**\n\nThe charter has been updated and backed up automatically.",
                        color=Colors.SUCCESS
                    )
                    embed.set_footer(text=f"Updated by {pending['user_name']} 🏈")
                    await reaction.message.edit(embed=embed)
                    await safe_clear_reactions(reaction.message)
                    logger.info(f"✅ Charter updated by {pending['user_name']}: {pending['description']}")
                else:
                    embed = discord.Embed(
                        title="❌ Update Failed",
                        description="Failed to apply the charter update. Check the logs for details.",
                        color=Colors.ERROR
                    )
                    await reaction.message.edit(embed=embed)
                    await safe_clear_reactions(reaction.message)

            del bot.pending_charter_updates[reaction.message.id]
            return

        elif str(reaction.emoji) == "❌":
            # Cancel the update
            embed = discord.Embed(
                title="❌ Update Cancelled",
                description="Charter update has been cancelled. No changes were made.",
                color=Colors.WARNING
            )
            await reaction.message.edit(embed=embed)
            await safe_clear_reactions(reaction.message)
            del bot.pending_charter_updates[reaction.message.id]
            logger.info(f"❌ Charter update cancelled by {pending['user_name']}")
            return

    # Handle rule scan -> charter update requests
    # Log what's in pending_rule_scans for debugging
    if hasattr(bot, 'pending_rule_scans'):
        logger.debug(f"  pending_rule_scans keys: {list(bot.pending_rule_scans.keys())}")
        logger.debug(f"  Looking for msg_id: {reaction.message.id}")

    if hasattr(bot, 'pending_rule_scans') and reaction.message.id in bot.pending_rule_scans:
        pending = bot.pending_rule_scans[reaction.message.id]
        logger.info(f"📝 Rule scan reaction: {reaction.emoji} from {user.display_name} on msg {reaction.message.id}")

        # Only the original requester can trigger
        if user.id != pending["user_id"]:
            logger.info(f"⚠️ Wrong user reacted: {user.id} != {pending['user_id']}")
            return

        # Check if expired
        if datetime.now().timestamp() > pending["expires"]:
            logger.info(f"⚠️ Rule scan expired for msg {reaction.message.id}")
            del bot.pending_rule_scans[reaction.message.id]
            return

        logger.info(f"✅ Processing rule scan reaction: {reaction.emoji}")

        if str(reaction.emoji) == "📝":
            # Generate charter updates from the found rules
            await safe_clear_reactions(reaction.message)

            thinking_embed = discord.Embed(
                title="🔧 Generating Charter Updates...",
                description="Analyzing passed rules and generating charter updates...",
                color=Colors.ADMIN
            )
            await reaction.message.edit(embed=thinking_embed)

            try:
                # Generate updates
                updates = await charter_editor.generate_charter_updates_from_rules(
                    pending["rule_changes"]
                )

                if not updates:
                    embed = discord.Embed(
                        title="📜 No Updates Needed",
                        description="The passed rules are either already in the charter or couldn't be automatically applied.",
                        color=Colors.SUCCESS
                    )
                    await reaction.message.edit(embed=embed)
                    del bot.pending_rule_scans[reaction.message.id]
                    return

                # Show the suggested updates
                embed = discord.Embed(
                    title="📝 Suggested Charter Updates",
                    description=f"Based on passed rules in #{pending['channel_name']}",
                    color=Colors.PRIMARY
                )

                for i, update in enumerate(updates[:5], 1):  # Show max 5
                    action = update.get("action", "update")
                    action_emoji = "➕" if action == "add" else "✏️"

                    new_text = update.get("new_text", "")[:200]
                    if len(update.get("new_text", "")) > 200:
                        new_text += "..."

                    embed.add_field(
                        name=f"{action_emoji} {update.get('rule_description', 'Update')[:50]}",
                        value=f"**Section:** {update.get('section', 'Unknown')}\n```\n{new_text}\n```",
                        inline=False
                    )

                embed.add_field(
                    name="⚠️ Apply Updates?",
                    value="React with ✅ to apply ALL these updates, or ❌ to cancel.\n*Each change will be backed up automatically.*",
                    inline=False
                )

                await reaction.message.edit(embed=embed)
                await reaction.message.add_reaction("✅")
                await reaction.message.add_reaction("❌")

                # Update the pending data with the generated updates
                pending["generated_updates"] = updates
                pending["expires"] = datetime.now().timestamp() + 120  # Reset timeout

            except Exception as e:
                logger.error(f"❌ Error generating charter updates: {e}", exc_info=True)
                embed = discord.Embed(
                    title="❌ Error",
                    description=f"Failed to generate updates: {str(e)}",
                    color=Colors.ERROR
                )
                await reaction.message.edit(embed=embed)
                del bot.pending_rule_scans[reaction.message.id]

            return

        elif str(reaction.emoji) == "✅" and pending.get("generated_updates"):
            # Apply the generated updates
            await safe_clear_reactions(reaction.message)

            updates = pending["generated_updates"]
            current_charter = charter_editor.read_charter()

            if not current_charter:
                embed = discord.Embed(
                    title="❌ Error",
                    description="Could not read current charter",
                    color=Colors.ERROR
                )
                await reaction.message.edit(embed=embed)
                del bot.pending_rule_scans[reaction.message.id]
                return

            # Apply updates one by one
            applied = 0
            new_charter = current_charter

            for update in updates:
                old_text = update.get("old_text")
                new_text = update.get("new_text")

                if update.get("action") == "add":
                    # Add new content at end of relevant section or end of charter
                    section = update.get("section", "")
                    # Simple append for now
                    new_charter = new_charter + f"\n\n{new_text}"
                    applied += 1
                elif old_text and new_text and old_text in new_charter:
                    new_charter = new_charter.replace(old_text, new_text, 1)
                    applied += 1

            if applied > 0:
                success = await charter_editor.apply_update(
                    new_charter=new_charter,
                    user_id=pending["user_id"],
                    user_name=pending["user_name"],
                    description=f"Applied {applied} rule updates from #{pending['channel_name']}",
                    before_text=f"Applied {applied} updates from voting",
                    after_text=f"Rules from #{pending['channel_name']}"
                )

                if success:
                    embed = discord.Embed(
                        title="✅ Charter Updated!",
                        description=f"Applied **{applied}** rule updates from #{pending['channel_name']}!\n\nBackup created automatically.",
                        color=Colors.SUCCESS
                    )
                    embed.set_footer(text=f"Updated by {pending['user_name']} 🏈")
                else:
                    embed = discord.Embed(
                        title="❌ Update Failed",
                        description="Failed to apply updates to the charter.",
                        color=Colors.ERROR
                    )
            else:
                embed = discord.Embed(
                    title="⚠️ No Updates Applied",
                    description="Could not apply any updates - text may not match exactly.",
                    color=Colors.ADMIN
                )

            await reaction.message.edit(embed=embed)
            del bot.pending_rule_scans[reaction.message.id]
            return

        elif str(reaction.emoji) == "❌":
            embed = discord.Embed(
                title="❌ Updates Cancelled",
                description="Charter updates cancelled. No changes were made.",
                color=Colors.WARNING
            )
            await reaction.message.edit(embed=embed)
            await safe_clear_reactions(reaction.message)
            del bot.pending_rule_scans[reaction.message.id]
        return

    # Handle different emoji reactions
    reaction_guild_id = reaction.message.guild.id if reaction.message.guild else 0
    league_enabled_reaction = server_config.is_module_enabled(reaction_guild_id, FeatureModule.LEAGUE)

    if reaction.emoji == '❓':
        # Question mark - offer help
        embed = discord.Embed(
            title="🏈 Harry's Help",
            color=Colors.PRIMARY
        )

        if league_enabled_reaction:
            embed.description = "I'm here to help with CFB 26 league questions! Here are some ways to interact with me:"
            embed.add_field(
                name="💬 Chat Commands:",
                value="• Mention me: `@Harry what are the rules?`\n• Ask questions: `What's the transfer policy?`\n• Say hi: `Hi Harry!`",
                inline=False
            )
            embed.add_field(
                name="⚡ Slash Commands:",
                value="• `/harry <question>` - Ask me anything\n• `/charter` - Link to full charter\n• `/help_cfb` - See all commands",
                inline=False
            )
            embed.add_field(
                name="📖 Full Charter",
                value="[Open Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
                inline=False
            )
        else:
            embed.description = "I'm here to help with college football! Here are some ways to interact with me:"
            embed.add_field(
                name="💬 Chat Commands:",
                value="• Mention me: `@Harry tell me about [player]`\n• Ask questions: `What's Ohio State's ranking?`",
                inline=False
            )
            embed.add_field(
                name="⚡ Slash Commands:",
                value="• `/player <name>` - Player lookup\n• `/rankings` - CFB rankings\n• `/betting` - Betting lines\n• `/help_cfb` - See all commands",
                inline=False
            )

        embed.set_footer(text=get_footer_for_guild(reaction_guild_id))

        await reaction.message.channel.send(embed=embed)

    elif reaction.emoji == '🏈':
        # Football emoji - CFB enthusiasm
        embed = discord.Embed(
            title="🏈 CFB Hype!",
            color=Colors.PRIMARY
        )
        if league_enabled_reaction:
            embed.description = "CFB 26 is the best dynasty league! 🏆\n\nNeed help with league rules? Just ask me anything!"
        else:
            embed.description = "College football is the best! 🏆\n\nNeed player stats, rankings, or schedules? Just ask!"
        embed.set_footer(text=get_footer_for_guild(reaction_guild_id))
        await reaction.message.channel.send(embed=embed)

    elif reaction.emoji == '🦆':
        # Duck emoji - Oregon rivalry (only if auto_responses is on)
        if server_config.auto_responses_enabled(reaction_guild_id):
            embed = discord.Embed(
                title="🦆 Oregon Sucks!",
                color=Colors.PRIMARY
            )
            if league_enabled_reaction:
                embed.description = "Oregon sucks! 🦆💩\n\nBut CFB 26 rules are awesome! Ask me about them!"
            else:
                embed.description = "Oregon sucks! 🦆💩\n\nNeed any CFB stats or info? Just ask!"
            embed.set_footer(text=get_footer_for_guild(reaction_guild_id))
            await reaction.message.channel.send(embed=embed)

    elif reaction.emoji == '🐕':
        # Dog emoji - Huskies support
        embed = discord.Embed(
            title="🐕 Go Huskies!",
            color=Colors.PRIMARY
        )
        if league_enabled_reaction:
            embed.description = "Go Huskies! 🐕\n\nSpeaking of teams, need help with league rules?"
        else:
            embed.description = "Go Huskies! 🐕\n\nNeed player stats or team info? Just ask!"
        embed.set_footer(text=get_footer_for_guild(reaction_guild_id))
        await reaction.message.channel.send(embed=embed)

    elif reaction.emoji == '🤖':
        # Robot emoji - AI explanation
        embed = discord.Embed(
            title="🤖 AI Assistant",
            color=Colors.PRIMARY
        )
        if league_enabled_reaction:
            embed.description = "I'm powered by AI to help with your CFB 26 league questions! Ask me anything about rules, recruiting, transfers, or penalties!"
        else:
            embed.description = "I'm powered by AI to help with college football questions! Ask me about players, teams, rankings, or schedules!"
        embed.set_footer(text=get_footer_for_guild(reaction_guild_id))
        await reaction.message.channel.send(embed=embed)

    elif reaction.emoji == '💡':
        # Lightbulb emoji - tips
        embed = discord.Embed(
            title="💡 Pro Tips",
            color=Colors.PRIMARY
        )
        if league_enabled_reaction:
            embed.description = "Here are some pro tips for CFB 26:\n\n• Follow all league rules to avoid penalties\n• Recruit smart - quality over quantity\n• Use the right difficulty settings\n• Don't sim games without permission\n\nNeed more help? Just ask!"
        else:
            embed.description = "Here are some CFB data tips:\n\n• Use `/player` for player lookups\n• Use `/rankings` for current polls\n• Use `/betting` for game lines\n• Use `/cfb_schedule` for team schedules\n\nNeed more help? Just ask!"
        embed.set_footer(text=get_footer_for_guild(reaction_guild_id))
        await reaction.message.channel.send(embed=embed)

async def load_league_data():
    """Load league rules and data from JSON files"""
    try:
        with open('data/league_rules.json', 'r') as f:
            bot.league_data = json.load(f)
        logger.info("✅ League data loaded successfully")
    except FileNotFoundError:
        logger.warning("⚠️  League data file not found - using default data")
        bot.league_data = {"league_info": {"name": "CFB 26 Online Dynasty"}}
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing league data: {e}")
        bot.league_data = {"league_info": {"name": "CFB 26 Online Dynasty"}}

@charter_group.command(name="lookup", description="Look up CFB 26 league rules")
@app_commands.describe(rule_name="Rule keyword or topic to search for")
async def charter_lookup(interaction: discord.Interaction, rule_name: str):
    """Look up a specific league rule"""
    # This command requires LEAGUE module
    if not await check_module_enabled(interaction, FeatureModule.LEAGUE):
        return

    await interaction.response.send_message("📋 Looking up rule...", ephemeral=True)

    # Search for rule in league data
    rule_found = False
    embed = discord.Embed(
        title=f"CFB 26 League Rule: {rule_name.title()}",
        color=Colors.PRIMARY
    )

    # Search through league rules (if any exist)
    if hasattr(bot, 'league_data') and 'rules' in bot.league_data:
        for category, rules in bot.league_data['rules'].items():
            if rule_name.lower() in category.lower():
                embed.description = rules.get('description', 'Rule information available')
                if 'topics' in rules:
                    topics_text = '\n'.join([f"• {topic}" for topic in rules['topics'].keys()])
                    embed.add_field(name="Related Topics", value=topics_text, inline=False)
                rule_found = True
                break

    # If no specific rule found, provide general guidance
    if not rule_found:
        embed.description = f"Specific rule '{rule_name}' not found in local data. All CFB 26 league rules are in the official charter."

    # Always add the charter link
    embed.add_field(
        name="📖 Full League Charter",
        value="[View Complete Rules](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
        inline=False
    )

    await interaction.followup.send(embed=embed)

@league_group.command(name="rules", description="Get recruiting rules and policies")
@app_commands.describe(topic="Rule topic to look up")
async def league_rules(interaction: discord.Interaction, topic: str):
    """Get information about recruiting rules"""
    await interaction.response.defer()

    embed = discord.Embed(
        title=f"CFB 26 Recruiting: {topic.title()}",
        color=0x32cd32
    )

    # Check if recruiting rules exist
    if hasattr(bot, 'league_data') and 'rules' in bot.league_data and 'recruiting' in bot.league_data['rules']:
        recruiting_rules = bot.league_data['rules']['recruiting']
        embed.description = recruiting_rules.get('description', 'Recruiting rules and policies')

        if 'topics' in recruiting_rules:
            topics = recruiting_rules['topics']
            if topic.lower() in topics:
                embed.add_field(name="Information", value=topics[topic.lower()], inline=False)
            else:
                available_topics = '\n'.join([f"• {t}" for t in topics.keys()])
                embed.add_field(name="Available Topics", value=available_topics, inline=False)
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
async def league_team(interaction: discord.Interaction, team_name: str):
    """Get information about a college football team"""
    await interaction.response.defer()

    # TODO: Implement team lookup logic
    embed = discord.Embed(
        title=f"Team: {team_name.title()}",
        description="Team lookup functionality coming soon!",
        color=0x32cd32
    )
    embed.add_field(name="Status", value="🚧 Under Development", inline=False)

    await interaction.followup.send(embed=embed)

@league_group.command(name="dynasty", description="Get dynasty management rules")
@app_commands.describe(topic="Dynasty topic to look up")
async def league_dynasty(interaction: discord.Interaction, topic: str):
    """Get information about dynasty management rules"""
    await interaction.response.defer()

    embed = discord.Embed(
        title=f"CFB 26 Dynasty: {topic.title()}",
        color=0xff6b6b
    )

    # Check if dynasty rules exist
    if hasattr(bot, 'league_data') and 'rules' in bot.league_data:
        # Look for dynasty-related rules
        dynasty_topics = ['transfers', 'gameplay', 'scheduling', 'conduct']
        found_topic = None

        for dt in dynasty_topics:
            if topic.lower() in dt.lower() and dt in bot.league_data['rules']:
                found_topic = dt
                break

        if found_topic:
            rules = bot.league_data['rules'][found_topic]
            embed.description = rules.get('description', 'Dynasty management rules')

            if 'topics' in rules:
                topics = rules['topics']
                if topic.lower() in topics:
                    embed.add_field(name="Information", value=topics[topic.lower()], inline=False)
                else:
                    available_topics = '\n'.join([f"• {t}" for t in topics.keys()])
                    embed.add_field(name="Available Topics", value=available_topics, inline=False)
        else:
            embed.description = "Dynasty topic not found. Available topics: transfers, gameplay, scheduling, conduct"
    else:
        embed.description = "Dynasty rules not found in league data."

    embed.add_field(
        name="League Charter",
        value="[View Full Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
        inline=False
    )

    await interaction.followup.send(embed=embed)

@charter_group.command(name="link", description="Get link to the official league charter")
async def charter_link(interaction: discord.Interaction):
    """Get the official league charter link"""
    # Check if league module is enabled
    if not await check_module_enabled(interaction, FeatureModule.LEAGUE):
        return

    embed = discord.Embed(
        title="📋 CFB 26 League Charter",
        description="Official league rules, policies, and guidelines",
        color=Colors.PRIMARY
    )

    embed.add_field(
        name="📖 View Full Charter",
        value="[Open League Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
        inline=False
    )

    embed.add_field(
        name="📝 Quick Commands",
        value="Use `/rule <topic>`, `/recruiting <topic>`, or `/dynasty <topic>` for specific information",
        inline=False
    )

    embed.set_footer(text="CFB 26 League Bot - Always check the charter for complete rules")

    await interaction.response.send_message(embed=embed)

@charter_group.command(name="scan", description="Scan a channel for rule changes and votes")
@app_commands.describe(
    channel="Channel to scan (e.g., #offseason-voting)",
    hours="Hours of history to scan (default: 168 = 1 week)"
)
async def charter_scan(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    hours: int = 168
):
    """Scan a channel for rule changes and offer to update the charter"""
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message(
            "❌ Only admins can scan for rule changes, ya muppet!",
            ephemeral=True
        )
        return

    if not charter_editor:
        await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
        return

    if not channel_summarizer:
        await interaction.response.send_message("❌ Channel summarizer not available", ephemeral=True)
        return

    if not AI_AVAILABLE or not ai_assistant:
        await interaction.response.send_message("❌ AI not available for this analysis", ephemeral=True)
        return

    # Validate hours
    if hours < 24:
        await interaction.response.send_message("❌ Need at least 24 hours of history!", ephemeral=True)
        return
    if hours > 720:  # 30 days max
        await interaction.response.send_message("❌ Max 720 hours (30 days)", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        # Fetch messages from the channel
        messages = await channel_summarizer.fetch_messages(channel, hours=hours, limit=500)

        if not messages:
            await interaction.followup.send(f"❌ No messages found in {channel.mention} in the last {hours} hours")
            return

        # Format messages for analysis - include both text and polls
        formatted_messages = []
        poll_count = 0
        for msg in messages:
            # Add regular message content
            if msg.content:
                formatted_messages.append(f"[{msg.author.display_name}]: {msg.content}")

            # Check for polls (requires discord.py 2.4+)
            try:
                if hasattr(msg, 'poll') and msg.poll:
                    poll_count += 1
                    poll = msg.poll
                    poll_text = f"[{msg.author.display_name}] POLL: {poll.question}"

                    # Add poll answers/options
                    if hasattr(poll, 'answers') and poll.answers:
                        options = []
                        for answer in poll.answers:
                            vote_count = getattr(answer, 'vote_count', 0)
                            answer_text = getattr(answer, 'text', str(answer))
                            options.append(f"  - {answer_text} ({vote_count} votes)")
                        poll_text += "\n" + "\n".join(options)

                    # Add poll status
                    if getattr(poll, 'is_finalized', False):
                        total = getattr(poll, 'total_votes', 0)
                        poll_text += f"\n  STATUS: CLOSED (Total: {total} votes)"
                        victor = getattr(poll, 'victor_answer', None)
                        if victor:
                            victor_text = getattr(victor, 'text', str(victor))
                            poll_text += f" - WINNER: {victor_text}"
                    else:
                        total = getattr(poll, 'total_votes', 0)
                        poll_text += f"\n  STATUS: OPEN (Total: {total} votes so far)"

                    formatted_messages.append(poll_text)
            except Exception as e:
                logger.debug(f"Could not process poll: {e}")

        logger.info(f"📊 Rule scan: Found {len(messages)} messages, {poll_count} polls in #{channel.name}")
        # Log sample of formatted messages for debugging
        if formatted_messages:
            logger.debug(f"📝 First 3 formatted messages for AI:")
            for fm in formatted_messages[:3]:
                logger.debug(f"  - {fm[:100]}...")

        # Find rule changes
        rule_changes = await charter_editor.find_rule_changes_in_messages(
            formatted_messages,
            channel_name=channel.name
        )

        if not rule_changes:
            embed = discord.Embed(
                title=f"📜 Rule Scan: #{channel.name}",
                description=f"No rule changes or votes found in the last {hours} hours.",
                color=Colors.ADMIN
            )
            embed.set_footer(text=f"Scanned {len(messages)} messages ({poll_count} polls)")
            await interaction.followup.send(embed=embed)
            return

        # Create embed showing found rules
        embed = discord.Embed(
            title=f"📜 Rule Changes Found in #{channel.name}",
            description=f"Found **{len(rule_changes)}** rule changes/votes",
            color=Colors.PRIMARY
        )

        passed_rules = []
        for i, rule in enumerate(rule_changes[:10], 1):  # Show max 10
            status = rule.get("status", "unknown")
            status_emoji = {
                "passed": "✅",
                "failed": "❌",
                "proposed": "📋",
                "decided": "✅"
            }.get(status, "❓")

            votes = ""
            if rule.get("votes_for") is not None:
                votes = f" ({rule.get('votes_for', 0)}-{rule.get('votes_against', 0)})"

            # Build detailed rule text
            rule_text = rule.get("rule", "Unknown rule")
            context = rule.get("context", "")

            # Format the field value with rule and context
            field_value = f"📝 {rule_text}"
            if context and context.strip() and context.lower() != rule_text.lower():
                field_value += f"\n> _{context}_"

            # Truncate if too long (Discord field limit is 1024)
            if len(field_value) > 500:
                field_value = field_value[:497] + "..."

            logger.debug(f"Rule scan field: rule='{rule_text[:30]}...', context='{context[:30] if context else 'NONE'}...'")

            embed.add_field(
                name=f"{i}. {status_emoji} {status.upper()}{votes}",
                value=field_value,
                inline=False
            )

            if status in ["passed", "decided"]:
                passed_rules.append(rule)

        embed.set_footer(text=f"Scanned {len(messages)} messages ({poll_count} polls) over {hours} hours")

        if passed_rules:
            embed.add_field(
                name="🔧 Update Charter?",
                value=f"Found **{len(passed_rules)}** passed rules. React with 📝 to generate charter updates.",
                inline=False
            )

        msg = await interaction.followup.send(embed=embed)

        if passed_rules:
            await msg.add_reaction("📝")

            # Store for reaction handler
            if not hasattr(bot, 'pending_rule_scans'):
                bot.pending_rule_scans = {}

            bot.pending_rule_scans[msg.id] = {
                "user_id": interaction.user.id,
                "user_name": interaction.user.display_name,
                "rule_changes": passed_rules,
                "channel_name": channel.name,
                "expires": datetime.now().timestamp() + 600  # 10 minute timeout
            }
            logger.info(f"📝 Stored pending rule scan: msg_id={msg.id}, user={interaction.user.id}, rules={len(passed_rules)}")

        logger.info(f"📜 Rule scan completed for #{channel.name} by {interaction.user}")

    except Exception as e:
        logger.error(f"❌ Error scanning rules: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error scanning for rules: {str(e)}")

@charter_group.command(name="sync", description="Sync charter to Discord for persistence (Admin only)")
async def charter_sync(interaction: discord.Interaction):
    """Manually sync the charter file to Discord for persistence across deployments"""
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ Only admins can sync the charter!", ephemeral=True)
        return

    if not charter_editor:
        await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    # Read current file and save to Discord
    content = charter_editor.read_charter()
    if not content:
        await interaction.followup.send("❌ No charter file found to sync!", ephemeral=True)
        return

    success = await charter_editor.save_to_discord(content)

    if success:
        await interaction.followup.send(
            f"✅ Charter synced to Discord!\n\n"
            f"📄 **{len(content)}** characters saved\n"
            f"💾 Will persist across bot restarts/deployments",
            ephemeral=True
        )
        logger.info(f"📜 Charter manually synced to Discord by {interaction.user}")
    else:
        await interaction.followup.send("❌ Failed to sync charter to Discord", ephemeral=True)


@charter_group.command(name="history", description="View recent charter changes")
async def charter_history(interaction: discord.Interaction):
    """View recent charter update history"""
    if not charter_editor:
        await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
        return

    changes = charter_editor.get_recent_changes(limit=10)

    if not changes:
        embed = discord.Embed(
            title="📜 Charter History",
            description="No charter changes have been recorded yet.",
            color=Colors.PRIMARY
        )
        await interaction.response.send_message(embed=embed)
        return

    embed = discord.Embed(
        title="📜 Charter Update History",
        description="Recent changes to the league charter",
        color=Colors.PRIMARY
    )

    for i, change in enumerate(changes[:5], 1):  # Show top 5
        timestamp = change.get("timestamp", "Unknown")
        if isinstance(timestamp, str) and "T" in timestamp:
            # Format ISO timestamp nicely
            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime("%b %d, %Y %I:%M %p")
            except (ValueError, TypeError):
                pass  # Keep original timestamp if parsing fails

        user_name = change.get("user_name", "Unknown")
        description = change.get("description", "No description")

        embed.add_field(
            name=f"{i}. {timestamp}",
            value=f"**By:** {user_name}\n**Change:** {description[:100]}{'...' if len(description) > 100 else ''}",
            inline=False
        )

    embed.set_footer(text="Use @Harry to update charter rules interactively 🏈")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information - filtered to show only enabled modules"""
    from .utils.version_manager import VersionManager
    version_mgr = VersionManager()
    current_version = version_mgr.get_current_version()

    # Get enabled modules for this server
    guild_id = interaction.guild.id if interaction.guild else 0
    enabled_modules = server_config.get_enabled_modules(guild_id) if guild_id else []

    # Track disabled modules for footer note
    disabled_modules = []

    embed = discord.Embed(
        title="🏈 Harry - Command Reference",
        description=f"Type `/` and the group name to see all options.\n**Version {current_version}**",
        color=Colors.PRIMARY
    )

    # Recruiting Group - requires RECRUITING module
    if "recruiting" in enabled_modules:
        embed.add_field(
            name="⭐ `/recruiting`",
            value=(
                "`player` - Look up a recruit\n"
                "`top` - Top recruits by pos/state\n"
                "`class` - Team's recruiting class\n"
                "`commits` - List team's commits\n"
                "`rankings` - Top 25 team rankings"
            ),
            inline=True
        )
    else:
        disabled_modules.append("Recruiting")

    # CFB Data Group - requires CFB_DATA module
    if "cfb_data" in enabled_modules:
        embed.add_field(
            name="📊 `/cfb`",
            value=(
                "`player` - College player lookup\n"
                "`rankings` - AP/Coaches/CFP polls\n"
                "`schedule` - Team's schedule\n"
                "`matchup` - Head-to-head history\n"
                "`transfers` - Portal activity"
            ),
            inline=True
        )
    else:
        disabled_modules.append("CFB Data")

    # HS Stats Group - requires HS_STATS module
    if "hs_stats" in enabled_modules:
        embed.add_field(
            name="🏫 `/hs`",
            value=(
                "`stats` - HS player stats\n"
                "`bulk` - Multiple players"
            ),
            inline=True
        )
    else:
        disabled_modules.append("HS Stats")

    # League Group - requires LEAGUE module
    if "league" in enabled_modules:
        embed.add_field(
            name="🏆 `/league`",
            value=(
                "**Season:** `week`, `weeks`, `games`, `byes`\n"
                "**Timer:** `timer`, `timer_status`, `timer_stop`\n"
                "**Staff:** `staff`, `set_owner`, `set_commish`"
            ),
            inline=True
        )
        # Charter is part of League
        embed.add_field(
            name="📜 `/charter`",
            value=(
                "`lookup` - Find a rule\n"
                "`search` - Search charter\n"
                "`link` - Charter URL\n"
                "`history` - Recent changes"
            ),
            inline=True
        )
    else:
        disabled_modules.append("League")

    # AI Chat commands - requires AI_CHAT module
    if "ai_chat" in enabled_modules:
        embed.add_field(
            name="💬 **AI Chat**",
            value=(
                "`/harry` - Ask about CFB/league\n"
                "`/ask` - General AI questions\n"
                "`/summarize` - Channel summary\n"
                "`@Harry` - Chat naturally!"
            ),
            inline=True
        )
    else:
        disabled_modules.append("AI Chat")

    # Always available commands
    embed.add_field(
        name="🤖 **Always Available**",
        value=(
            "`/help` - This menu\n"
            "`/version` - Bot version\n"
            "`/whats_new` - Latest features"
        ),
        inline=True
    )

    # Show disabled modules note if any
    if disabled_modules:
        embed.add_field(
            name="ℹ️ Additional Features",
            value=f"_{', '.join(disabled_modules)}_ disabled on this server.\nAsk an admin about `/admin config`",
            inline=False
        )

    embed.set_footer(text="Harry 🏈 | Type /group to see subcommands")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="tokens", description="Show AI token usage statistics")
async def show_tokens(interaction: discord.Interaction):
    """Show AI token usage statistics"""
    if AI_AVAILABLE and ai_assistant:
        stats = ai_assistant.get_token_usage()
        embed = discord.Embed(
            title="🔢 AI Token Usage Statistics",
            color=Colors.SUCCESS
        )

        embed.add_field(
            name="📊 Usage Summary",
            value=f"**Total Requests:** {stats['total_requests']}\n**OpenAI Tokens:** {stats['openai_tokens']:,}\n**Anthropic Tokens:** {stats['anthropic_tokens']:,}\n**Total Tokens:** {stats['total_tokens']:,}",
            inline=False
        )

        if stats['total_requests'] > 0:
            avg_tokens = stats['total_tokens'] / stats['total_requests']
            embed.add_field(
                name="📈 Averages",
                value=f"**Avg Tokens per Request:** {avg_tokens:.1f}",
                inline=False
            )

        # Add cost estimates (rough approximations)
        openai_cost = stats['openai_tokens'] * 0.000002  # GPT-3.5-turbo pricing
        embed.add_field(
            name="💰 Estimated Costs",
            value=f"**OpenAI Cost:** ~${openai_cost:.4f}\n**Note:** Actual costs may vary based on model and pricing",
            inline=False
        )

        embed.set_footer(text="Token usage since bot startup")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("❌ AI integration not available")

@charter_group.command(name="search", description="Search the official league charter")
@app_commands.describe(search_term="Text to search for in the charter")
async def charter_search(interaction: discord.Interaction, search_term: str):
    """Search for specific terms in the league charter"""
    await interaction.response.send_message("🔍 Searching...", ephemeral=True)

    embed = discord.Embed(
        title=f"🔍 Search Results: '{search_term}'",
        color=Colors.WARNING
    )

    if GOOGLE_DOCS_AVAILABLE and google_docs:
        try:
            results = google_docs.search_document(search_term)
            if results:
                embed.description = "Found in the league charter:"
                for i, result in enumerate(results, 1):
                    # Truncate long results
                    if len(result) > 200:
                        result = result[:200] + "..."
                    embed.add_field(
                        name=f"Result {i}",
                        value=result,
                        inline=False
                    )
            else:
                embed.description = "No results found in the charter."
        except Exception as e:
            embed.description = f"Error searching charter: {str(e)}"
    else:
        embed.description = "Google Docs integration not available. Use the direct link to search manually."

    embed.add_field(
        name="📖 Full Charter",
        value="[Open League Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
        inline=False
    )

    await interaction.followup.send(embed=embed)


@cfb_group.command(name="player", description="Look up a college football player's stats and info")
@app_commands.describe(
    name="Player name to search for (e.g., 'James Smith')",
    team="Optional team name to filter results (e.g., 'Alabama')"
)
async def cfb_player(
    interaction: discord.Interaction,
    name: str,
    team: str = None
):
    """
    Look up player info from CollegeFootballData.com

    Args:
        name: Player name to search for (e.g., "James Smith")
        team: Optional team name to filter results (e.g., "Alabama")
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ Player lookup is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
        return

    logger.info(f"🏈 /player command from {interaction.user}: {name}" + (f" from {team}" if team else ""))

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
        logger.error(f"❌ Error in /player command: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error looking up player: {str(e)}", ephemeral=True)


@cfb_group.command(name="players", description="Look up multiple players at once")
@app_commands.describe(
    player_list="Players separated by commas, e.g., 'James Smith (Bama DT); Isaiah Horton (Bama WR)'"
)
async def cfb_players(
    interaction: discord.Interaction,
    player_list: str
):
    """
    Look up multiple players at once.

    Args:
        player_list: List of players separated by commas or semicolons.
                     Format: "Name (Team Position)" or "Name, Team"
                     Example: "James Smith (Bama DT); Isaiah Horton (Bama WR)"
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
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

    logger.info(f"🏈 /players bulk lookup from {interaction.user}: {len(players)} players")

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
        logger.error(f"❌ Error in /players command: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error looking up players: {str(e)}", ephemeral=True)


@cfb_group.command(name="rankings", description="Get college football rankings (AP, Coaches, CFP)")
@app_commands.describe(
    team="Optional team to highlight",
    year="Season year (default: current)",
    week="Week number (default: latest)",
    poll="Poll type: AP, Coaches, or CFP",
    top="Number of teams to show (default: 10)"
)
async def cfb_rankings(
    interaction: discord.Interaction,
    team: str = None,
    year: int = None,
    week: int = None,
    poll: str = None,
    top: int = 10
):
    """
    Get CFB rankings - optionally filter by team, week, or poll

    Args:
        team: Optional team to check ranking for
        year: Year to check (default: current season)
        week: Specific week (default: latest available)
        poll: Filter by poll name (AP, Coaches, CFP)
        top: How many teams to show per poll (default: 10, max: 25)
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
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
        logger.error(f"❌ Error in /rankings: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@cfb_group.command(name="matchup", description="Get historical matchup data between two teams")
@app_commands.describe(
    team1="First team (e.g., 'Alabama')",
    team2="Second team (e.g., 'Auburn')"
)
async def cfb_matchup(
    interaction: discord.Interaction,
    team1: str,
    team2: str
):
    """
    Get all-time matchup history between two teams

    Args:
        team1: First team (e.g., "Alabama")
        team2: Second team (e.g., "Auburn")
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
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
        logger.error(f"❌ Error in /matchup: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@cfb_group.command(name="schedule", description="Get a team's schedule and results")
@app_commands.describe(
    team="Team name (e.g., 'Nebraska')",
    year="Season year (default: current)"
)
async def cfb_schedule(
    interaction: discord.Interaction,
    team: str,
    year: int = None
):
    """
    Get a team's full schedule for a season

    Args:
        team: Team name (e.g., "Nebraska")
        year: Season year (default: current season)
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
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
        logger.error(f"❌ Error in /cfb_schedule: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@cfb_group.command(name="draft", description="Get NFL draft picks from a college")
@app_commands.describe(
    team="Optional college team to filter by",
    year="Draft year (default: current year)"
)
async def cfb_draft(
    interaction: discord.Interaction,
    team: str = None,
    year: int = None
):
    """
    Get NFL draft picks, optionally filtered by college

    Args:
        team: Optional college team to filter by
        year: Draft year (default: current year)
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
        return

    try:
        result = await cfb_data.get_draft_picks(team, year)
        response = cfb_data.format_draft_picks(result, team)

        title = f"🏈 {year} NFL Draft Picks" + (f" from {team}" if team else "")
        embed = discord.Embed(title=title, description=response, color=Colors.PRIMARY)
        embed.set_footer(text=Footers.CFB_DATA)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"❌ Error in /draft_picks: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@cfb_group.command(name="transfers", description="Get transfer portal activity for a team")
@app_commands.describe(
    team="Team name (e.g., 'USC')",
    year="Year to check (default: current)"
)
async def cfb_transfers(
    interaction: discord.Interaction,
    team: str,
    year: int = None
):
    """
    Get transfer portal incoming and outgoing for a team

    Args:
        team: Team name (e.g., "USC")
        year: Year to check (default: current year)
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
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
        logger.error(f"❌ Error in /transfers: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@cfb_group.command(name="betting", description="Get betting lines for games")
@app_commands.describe(
    team="Optional team to filter by",
    year="Season year (default: current)",
    week="Week number (default: current)"
)
async def cfb_betting(
    interaction: discord.Interaction,
    team: str = None,
    year: int = None,
    week: int = None
):
    """
    Get betting lines for games

    Args:
        team: Optional team to filter by
        year: Season year (default: current season)
        week: Optional week number
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
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
        logger.error(f"❌ Error in /betting: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


@cfb_group.command(name="ratings", description="Get advanced ratings (SP+, SRS, Elo) for a team")
@app_commands.describe(
    team="Team name (e.g., 'Ohio State')",
    year="Season year (default: current)"
)
async def cfb_ratings(
    interaction: discord.Interaction,
    team: str,
    year: int = None
):
    """
    Get advanced analytics ratings for a team

    Args:
        team: Team name (e.g., "Ohio State")
        year: Season year (default: current season)
    """
    # Defer FIRST to avoid interaction timeout (3 sec limit)
    await interaction.response.defer()

    if not await check_module_enabled_deferred(interaction, FeatureModule.CFB_DATA):
        return

    if not cfb_data.is_available:
        await interaction.followup.send(
            "❌ CFB data is not configured. CFB_DATA_API_KEY is missing.",
            ephemeral=True
        )
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
        logger.error(f"❌ Error in /team_ratings: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


# =============================================================================
# HIGH SCHOOL STATS COMMANDS (HS_STATS Module - Off by Default)
# =============================================================================


@hs_group.command(name="stats", description="Look up high school football player stats from MaxPreps")
@app_commands.describe(
    name="Player name (e.g., 'Arch Manning')",
    state="Optional state to narrow search (e.g., 'Louisiana', 'TX')",
    school="Optional high school name to narrow search"
)
async def hs_stats(
    interaction: discord.Interaction,
    name: str,
    state: str = None,
    school: str = None
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

    if not await check_module_enabled_deferred(interaction, FeatureModule.HS_STATS):
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
                f"_Add a state filter to narrow results: `/hs_stats name:{name} state:XX`_\n\n"
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
            title=f"🏈 High School Stats",
            description=formatted,
            color=Colors.HS_STATS
        )
        embed.set_footer(text=Footers.HS_STATS)
        await interaction.followup.send(embed=embed)

    except Exception as e:
        logger.error(f"❌ Error in /hs_stats: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Error looking up player: {str(e)}",
            ephemeral=True
        )


@hs_group.command(name="bulk", description="Look up multiple HS players at once")
@app_commands.describe(
    players="Comma-separated player names, e.g., 'Arch Manning (LA), Dylan Raiola (AZ)'"
)
async def hs_bulk(
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

    if not await check_module_enabled_deferred(interaction, FeatureModule.HS_STATS):
        return

    if not hs_stats_scraper.is_available:
        await interaction.followup.send(
            "❌ High school stats scraper is not available.\n"
            "Missing dependencies: `pip install httpx beautifulsoup4`",
            ephemeral=True
        )
        return

    try:
        import re

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
                school = data.get('school', 'Unknown School')
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

                value = f"🏫 {school}"
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
        logger.error(f"❌ Error in /hs_stats_bulk: {e}", exc_info=True)
        await interaction.followup.send(
            f"❌ Error during bulk lookup: {str(e)}",
            ephemeral=True
        )


# ==================== RECRUITING COMMANDS ====================

def get_recruiting_scraper(guild_id: int):
    """Get the appropriate recruiting scraper based on server config"""
    source = server_config.get_recruiting_source(guild_id)
    if source == RecruitingSource.SPORTS247:
        return recruiting_scraper, "247Sports Composite"
    else:
        return on3_scraper, "On3/Rivals"


@recruiting_group.command(name="player", description="Look up a recruit's ranking")
@app_commands.describe(
    name="Recruit name (e.g., 'Arch Manning')",
    year="Recruiting class year (default: current)",
    deep_search="(247Sports only) Search ALL ranked recruits (~3000+) instead of top 1000"
)
async def recruiting_player(
    interaction: discord.Interaction,
    name: str,
    year: Optional[int] = None,
    deep_search: bool = False
):
    """Look up a recruit from configured recruiting source (On3/Rivals or 247Sports)"""
    # Check channel + module enabled
    if not await check_module_enabled(interaction, FeatureModule.RECRUITING):
        return

    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        # Interaction expired (3 second timeout) - can't respond
        logger.warning(f"⚠️ /recruit interaction expired for {name}")
        return

    if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING):
        return

    try:
        guild_id = interaction.guild.id if interaction.guild else 0
        scraper, source_name = get_recruiting_scraper(guild_id)

        search_depth = "deep (all ~3000)" if deep_search else "standard"
        logger.info(f"🔍 /recruit lookup: {name} ({year or 'current'}) via {source_name} - {search_depth}")

        # Use more pages for deep search (only affects 247Sports)
        max_pages = 65 if deep_search else 20
        recruit = await scraper.search_recruit(name, year, max_pages=max_pages)

        if recruit:
            embed = discord.Embed(
                title=f"⭐ Recruit: {recruit.get('name', name)}",
                description=scraper.format_recruit(recruit),
                color=Colors.RECRUITING if hasattr(Colors, 'RECRUITING') else 0xffd700
            )

            # Add player photo as thumbnail if available
            if recruit.get('image_url'):
                embed.set_thumbnail(url=recruit['image_url'])

            # If this is a transfer portal player, auto-fetch college stats
            if recruit.get('is_transfer'):
                try:
                    college_stats = await cfb_data.get_full_player_info(recruit.get('name', name))
                    if college_stats and college_stats.get('stats'):
                        stats_lines = []
                        team_name = college_stats.get('team', '')
                        if team_name:
                            stats_lines.append(f"**Previous School:** {team_name}")

                        stats = college_stats.get('stats', {})
                        years = sorted(stats.keys(), reverse=True)
                        for yr in years[:2]:  # Show last 2 seasons
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
                except Exception as e:
                    logger.warning(f"⚠️ Failed to fetch college stats for transfer {name}: {e}")

            # Add profile link at the bottom (after college stats if present)
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
            if not deep_search and source_name == "247Sports Composite":
                tips.append("• Try `deep_search:True` to search all ~3000 ranked recruits")

            embed = discord.Embed(
                title="❓ Recruit Not Found",
                description=f"Couldn't find **{name}** in {source_name}.\n\n"
                           f"💡 **Tips:**\n" + '\n'.join(tips),
                color=Colors.WARNING
            )
            embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"❌ Error in /recruit: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error looking up recruit: {str(e)}", ephemeral=True)


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
async def recruiting_top(
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
        logger.warning("⚠️ /top_recruits interaction expired")
        return

    if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING):
        return

    try:
        # Validate top parameter
        if top and (top < 1 or top > 50):
            await interaction.followup.send("❌ 'top' must be between 1 and 50", ephemeral=True)
            return

        guild_id = interaction.guild.id if interaction.guild else 0
        scraper, source_name = get_recruiting_scraper(guild_id)

        actual_year = year or scraper._get_current_recruiting_year()
        logger.info(f"🔍 /top_recruits via {source_name}: pos={position}, state={state}, year={actual_year}, top={top}")

        recruits = await scraper.get_top_recruits(
            year=actual_year,
            position=position,
            state=state,
            limit=top or 15
        )

        if recruits:
            # Build title
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
                color=Colors.RECRUITING if hasattr(Colors, 'RECRUITING') else 0xffd700
            )
            embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                f"❌ Couldn't find recruits matching your criteria. Try different filters!",
                ephemeral=True
            )

    except Exception as e:
        logger.error(f"❌ Error in /top_recruits: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error getting recruits: {str(e)}", ephemeral=True)


@recruiting_group.command(name="class", description="Get a team's recruiting class ranking")
@app_commands.describe(
    team="Team name (e.g., 'Georgia', 'Ohio State')",
    year="Recruiting class year (default: current)"
)
async def recruiting_class(
    interaction: discord.Interaction,
    team: str,
    year: Optional[int] = None
):
    """Get a team's recruiting class details"""
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        logger.warning(f"⚠️ /recruiting_class interaction expired for {team}")
        return

    if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING):
        return

    try:
        guild_id = interaction.guild.id if interaction.guild else 0
        scraper, source_name = get_recruiting_scraper(guild_id)

        actual_year = year or scraper._get_current_recruiting_year()
        logger.info(f"🔍 /recruiting_class via {source_name}: {team} ({actual_year})")

        team_data = await scraper.get_team_recruiting_class(team, actual_year)

        if team_data:
            embed = discord.Embed(
                title=f"📋 {team_data.get('team', team)} Recruiting Class",
                description=scraper.format_team_class(team_data),
                color=Colors.RECRUITING if hasattr(Colors, 'RECRUITING') else 0xffd700
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
        logger.error(f"❌ Error in /recruiting_class: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error getting class: {str(e)}", ephemeral=True)


@recruiting_group.command(name="commits", description="List all committed recruits for a team")
@app_commands.describe(
    team="Team name (e.g., 'Washington', 'Ohio State')",
    year="Recruiting class year (default: current)",
    show="Number of commits to show (default: 30, max: 50)"
)
async def recruiting_commits(
    interaction: discord.Interaction,
    team: str,
    year: Optional[int] = None,
    show: Optional[int] = 30
):
    """Get list of committed recruits for a team"""
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        logger.warning(f"⚠️ /team_commits interaction expired for {team}")
        return

    if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING):
        return

    try:
        guild_id = interaction.guild.id if interaction.guild else 0
        scraper, source_name = get_recruiting_scraper(guild_id)

        # Only On3 scraper has team commits
        if source_name != "On3/Rivals":
            await interaction.followup.send(
                f"❌ Team commits list is only available with **On3/Rivals** data source.\n"
                f"💡 Switch with `/recruit_source on3`",
                ephemeral=True
            )
            return

        actual_year = year or scraper._get_current_recruiting_year()
        logger.info(f"🔍 /team_commits: {team} ({actual_year})")

        commits_data = await scraper.get_team_commits(team, actual_year)

        if commits_data and commits_data.get('commits'):
            embed = discord.Embed(
                title=f"🏈 {commits_data.get('team', team)} Commits ({actual_year})",
                description=scraper.format_team_commits(commits_data, limit=show),
                color=Colors.RECRUITING if hasattr(Colors, 'RECRUITING') else 0xffd700
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
        logger.error(f"❌ Error in /team_commits: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Error getting commits: {str(e)}", ephemeral=True)


@recruiting_group.command(name="rankings", description="Get top team recruiting class rankings")
@app_commands.describe(
    year="Recruiting class year (default: current)",
    top="Number of teams to show (default: 25)"
)
async def recruiting_rankings(
    interaction: discord.Interaction,
    year: Optional[int] = None,
    top: Optional[int] = 25
):
    """Get top team recruiting class rankings"""
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        logger.warning("⚠️ /recruiting_rankings interaction expired")
        return

    if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING):
        return

    try:
        if top and (top < 1 or top > 50):
            await interaction.followup.send("❌ 'top' must be between 1 and 50", ephemeral=True)
            return

        guild_id = interaction.guild.id if interaction.guild else 0
        scraper, source_name = get_recruiting_scraper(guild_id)

        actual_year = year or scraper._get_current_recruiting_year()
        logger.info(f"🔍 /recruiting_rankings via {source_name}: year={actual_year}, top={top}")

        teams = await scraper.get_team_rankings(actual_year, top or 25)

        if teams:
            # Format rankings
            lines = [f"**Top {len(teams)} Recruiting Classes ({actual_year})**", ""]
            for team in teams:
                rank = team.get('rank', '?')
                name = team.get('team', 'Unknown')
                commits = team.get('total_commits', '?')
                points = team.get('points', 0)
                points_str = f" ({points:.1f} pts)" if points else ""
                lines.append(f"`{rank:2d}.` **{name}** - {commits} commits{points_str}")

            embed = discord.Embed(
                title=f"🏆 Team Recruiting Rankings ({actual_year})",
                description='\n'.join(lines),
                color=Colors.RECRUITING if hasattr(Colors, 'RECRUITING') else 0xffd700
            )
            embed.set_footer(text=f"Harry's Recruiting 🏈 | Data from {source_name}")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                f"❌ Couldn't load team rankings for {actual_year}",
                ephemeral=True
            )

    except Exception as e:
        logger.error(f"❌ Error in /recruiting_rankings: {e}", exc_info=True)


@recruiting_group.command(name="portal", description="Look up a transfer portal player (recruiting + college stats)")
@app_commands.describe(
    name="Player name (e.g., 'John Smith')",
    team="Previous/current team to help find the right player"
)
async def recruiting_portal(
    interaction: discord.Interaction,
    name: str,
    team: Optional[str] = None
):
    """
    Look up a transfer portal player - combines recruiting data with college stats.

    Shows:
    - On3/Rivals recruiting rating and rankings
    - College statistics from their previous school
    - Transfer predictions (if available)
    """
    try:
        await interaction.response.defer()
    except discord.errors.NotFound:
        logger.warning(f"⚠️ /recruiting portal interaction expired for {name}")
        return

    if not await check_module_enabled_deferred(interaction, FeatureModule.RECRUITING):
        return

    try:
        guild_id = interaction.guild.id if interaction.guild else 0
        logger.info(f"🔄 Portal lookup: {name}" + (f" ({team})" if team else ""))

        # Get recruiting data from On3 (uses broader search for transfers)
        recruit_data = None
        on3_name = None
        try:
            recruit_data = await on3_scraper.search_recruit(name)
            if recruit_data:
                on3_name = recruit_data.get('name')  # May differ (nickname vs legal)
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

        # Cross-reference: If On3 has a different name, try CFB with that name
        if recruit_data and not college_stats and on3_name and on3_name.lower() != name.lower():
            logger.info(f"🔄 Cross-reference: trying CFB lookup with On3 name '{on3_name}'")
            try:
                college_stats = await cfb_data.get_full_player_info(on3_name, team)
            except Exception as e:
                logger.debug(f"Cross-reference CFB lookup failed: {e}")

        # Fallback: If we have recruit data but no CFB stats, try last name only
        # This handles nicknames like "Hollywood Smothers" -> search "Smothers" in CFB
        if recruit_data and not college_stats:
            name_parts = (on3_name or name).split()
            if len(name_parts) >= 2:
                last_name = name_parts[-1]
                on3_pos = recruit_data.get('position', '').upper()
                logger.info(f"🔄 Fallback: trying CFB lookup with last name '{last_name}' (pos: {on3_pos})")
                try:
                    # Search for all players with this last name
                    players = await cfb_data.search_player(last_name, team)
                    if players and on3_pos:
                        # Position mapping (On3 -> CFB equivalents)
                        pos_groups = {
                            'RB': ['RB', 'HB', 'FB'], 'WR': ['WR'], 'QB': ['QB'], 'TE': ['TE'],
                            'OT': ['OT', 'OL', 'T'], 'OG': ['OG', 'OL', 'G'], 'OL': ['OL', 'OT', 'OG', 'C'],
                            'DL': ['DL', 'DE', 'DT', 'NT'], 'DE': ['DE', 'DL', 'EDGE'], 'DT': ['DT', 'DL', 'NT'],
                            'LB': ['LB', 'ILB', 'OLB', 'MLB'], 'CB': ['CB', 'DB'], 'S': ['S', 'SS', 'FS', 'DB'],
                            'DB': ['DB', 'CB', 'S'], 'K': ['K', 'PK'], 'P': ['P'],
                        }
                        valid_pos = pos_groups.get(on3_pos, [on3_pos])
                        # Find player with matching position
                        for p in players:
                            cfb_pos = (p.get('position') or '').upper()
                            if cfb_pos in valid_pos or on3_pos in cfb_pos:
                                logger.info(f"✅ Position match: {p.get('name')} ({cfb_pos}) = On3 ({on3_pos})")
                                college_stats = await cfb_data.get_full_player_info(p.get('name'), p.get('team'))
                                break
                        else:
                            logger.warning(f"⚠️ No position match in {len(players)} results")
                    elif players:
                        # No position from On3, use first result
                        college_stats = await cfb_data.get_full_player_info(players[0].get('name'), players[0].get('team'))
                except Exception as e:
                    logger.debug(f"Last name CFB lookup failed: {e}")

        # Cross-reference: If CFB has a different name, try On3 with that name
        if college_stats and not recruit_data and cfb_name and cfb_name.lower() != name.lower():
            logger.info(f"🔄 Cross-reference: trying On3 lookup with CFB name '{cfb_name}'")
            try:
                recruit_data = await on3_scraper.search_recruit(cfb_name)
            except Exception as e:
                logger.debug(f"Cross-reference On3 lookup failed: {e}")

        # If neither found, show error
        if not recruit_data and not college_stats:
            embed = discord.Embed(
                title="❓ Portal Player Not Found",
                description=f"Couldn't find **{name}** in transfer portal data.\n\n"
                           f"💡 **Tips:**\n"
                           f"• Check the spelling\n"
                           f"• Try their nickname (e.g., 'Hollywood Smothers' not 'Daylan Smothers')\n"
                           f"• Add their team: `/recruiting player name:{name}`\n"
                           f"• Try `/cfb player` for college stats only",
                color=Colors.WARNING
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Build combined response
        embed = discord.Embed(
            title=f"🔄 Transfer Portal: {name}",
            color=Colors.RECRUITING if hasattr(Colors, 'RECRUITING') else 0xffd700
        )

        # Add player photo as thumbnail if available
        if recruit_data and recruit_data.get('image_url'):
            embed.set_thumbnail(url=recruit_data['image_url'])

        # Add recruiting data section
        if recruit_data:
            recruit_lines = []

            # Basic info
            stars = recruit_data.get('stars', 0)
            star_display = '⭐' * stars if stars else 'Unranked'
            rating = recruit_data.get('rating')

            if rating:
                recruit_lines.append(f"**Rating:** {rating} ({star_display})")

            # Rankings
            ranks = []
            if recruit_data.get('national_rank'):
                ranks.append(f"#{recruit_data['national_rank']} Nationally")
            if recruit_data.get('position_rank'):
                pos = recruit_data.get('position', '')
                ranks.append(f"#{recruit_data['position_rank']} {pos}")
            if ranks:
                recruit_lines.append(f"**Rank:** {' | '.join(ranks)}")

            # Position/physical
            pos = recruit_data.get('position', '')
            height = recruit_data.get('height', '')
            weight = recruit_data.get('weight', '')
            if pos:
                phys = f" | {height} | {weight}lbs" if height and weight else ""
                recruit_lines.append(f"**Position:** {pos}{phys}")

            # Commitment status
            if recruit_data.get('committed_to'):
                recruit_lines.append(f"**Committed to:** {recruit_data['committed_to']} ✅")

            # Top predictions
            predictions = recruit_data.get('top_predictions', [])
            if predictions:
                pred_str = ", ".join([f"{p['team']} ({p.get('prediction', '?')})" for p in predictions[:3]])
                recruit_lines.append(f"**Predictions:** {pred_str}")

            # Offers
            offers = recruit_data.get('offers', [])
            if offers:
                recruit_lines.append(f"**Offers:** {len(offers)} schools")

            embed.add_field(
                name="📊 Recruiting Profile",
                value='\n'.join(recruit_lines) if recruit_lines else "No recruiting data",
                inline=False
            )

        # Add college stats section
        if college_stats:
            stats_lines = []

            # Player info
            team_name = college_stats.get('team', '')
            position = college_stats.get('position', '')
            jersey = college_stats.get('jersey', '')

            if team_name:
                jersey_str = f" #{jersey}" if jersey else ""
                stats_lines.append(f"**Previous School:** {team_name}{jersey_str}")

            # Season stats (most recent)
            stats = college_stats.get('stats', {})
            if stats:
                # Get most recent year
                years = sorted(stats.keys(), reverse=True)
                if years:
                    recent_year = years[0]
                    year_stats = stats[recent_year]
                    stats_lines.append(f"**{recent_year} Stats:**")

                    # Passing
                    passing = year_stats.get('passing', {})
                    if passing.get('YDS'):
                        stats_lines.append(f"  🎯 {passing.get('YDS', 0)} YDS | {passing.get('TD', 0)} TD | {passing.get('INT', 0)} INT")

                    # Rushing
                    rushing = year_stats.get('rushing', {})
                    if rushing.get('YDS'):
                        stats_lines.append(f"  🏃 {rushing.get('CAR', 0)} CAR | {rushing.get('YDS', 0)} YDS | {rushing.get('TD', 0)} TD")

                    # Receiving
                    receiving = year_stats.get('receiving', {})
                    if receiving.get('YDS'):
                        stats_lines.append(f"  🎯 {receiving.get('REC', 0)} REC | {receiving.get('YDS', 0)} YDS | {receiving.get('TD', 0)} TD")

                    # Defense
                    defense = year_stats.get('defense', {})
                    if defense.get('TOT') or defense.get('SOLO'):
                        stats_lines.append(f"  🛡️ {defense.get('TOT', defense.get('SOLO', 0))} TKL | {defense.get('TFL', 0)} TFL | {defense.get('SACKS', 0)} Sacks")

            embed.add_field(
                name="🏈 College Stats",
                value='\n'.join(stats_lines) if stats_lines else "No college stats found",
                inline=False
            )

        # Add profile link if available
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


@bot.tree.command(name="harry", description="Ask Harry about college football")
async def ask_harry(interaction: discord.Interaction, question: str):
    """Ask Harry (the bot) about college football or league rules"""
    guild_id = interaction.guild.id if interaction.guild else 0
    channel_id = interaction.channel.id if interaction.channel else 0

    # Check if AI_CHAT module is enabled
    if not server_config.is_module_enabled(guild_id, FeatureModule.AI_CHAT):
        await interaction.response.send_message(
            "💬 AI Chat is disabled on this server.\n"
            "An admin can enable it with `/admin config enable ai_chat`",
            ephemeral=True
        )
        return

    # Check if Harry is enabled in this channel
    if not server_config.is_channel_enabled(guild_id, channel_id):
        await interaction.response.send_message(
            "🔇 Harry isn't enabled in this channel.\n"
            "An admin can enable it with `/admin channels`",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🏈 Harry's Response",
        color=Colors.PRIMARY
    )

    league_enabled = server_config.is_module_enabled(guild_id, FeatureModule.LEAGUE)

    if AI_AVAILABLE and ai_assistant:
        try:
            # Send initial response immediately
            await interaction.response.send_message("🤔 Harry is thinking...", ephemeral=True)

            # Log the slash command usage
            guild_name = interaction.guild.name if interaction.guild else "DM"
            logger.info(f"🎯 SLASH COMMAND: /harry from {interaction.user} ({interaction.user.id}) in {guild_name} - '{question}'")
            logger.info(f"🔍 Slash command question: '{question}'")
            logger.info(f"🏠 Server: {guild_name} (ID: {interaction.guild.id if interaction.guild else 'DM'})")

            # Classification for slash commands
            is_question, league_related, matched_keywords = classify_question(question)

            logger.info(f"🔍 CLASSIFICATION: is_question={is_question}, league_related={league_related}")
            if league_related:
                logger.info(f"🎯 Matched keywords: {matched_keywords}")

            # Get personality based on server settings
            personality = server_config.get_personality_prompt(guild_id)

            # Make the AI response conversational - context depends on LEAGUE status
            if league_enabled:
                conversational_question = f"{personality} Answer this question about CFB 26 league rules: {question}"
            else:
                conversational_question = f"{personality} Answer this question about college football: {question}"
            response = await ai_assistant.ask_ai(conversational_question, f"{interaction.user} ({interaction.user.id})", include_league_context=league_enabled)

            if response:
                embed.description = response
                embed.add_field(
                    name="💬 Responding to:",
                    value=f"*{question}*",
                    inline=False
                )
                if league_enabled:
                    embed.add_field(
                        name="💡 Need More Info?",
                        value="Ask me anything about league rules, or check the full charter below!",
                        inline=False
                    )
            else:
                if league_enabled:
                    embed.description = "Sorry, I couldn't get a response right now. Let me check the charter for you!"
                else:
                    embed.description = "Sorry, I couldn't get a response right now. Try asking another way!"
                embed.add_field(
                    name="💬 Responding to:",
                    value=f"*{question}*",
                    inline=False
                )
        except Exception as e:
            embed.description = f"Oops! Something went wrong: {str(e)}"
            embed.add_field(
                name="💬 Responding to:",
                value=f"*{question}*",
                inline=False
            )
    else:
        if league_enabled:
            embed.description = "Hi! I'm Harry, your CFB 26 league assistant. I'm having some technical difficulties right now, but you can always check the charter directly!"
        else:
            embed.description = "Hi! I'm Harry, your college football assistant. I'm having some technical difficulties right now. Try again in a bit!"
        embed.add_field(
            name="💬 Responding to:",
            value=f"*{question}*",
            inline=False
        )

    # Only add charter link if LEAGUE module is enabled
    if league_enabled:
        embed.add_field(
            name="📖 Full League Charter",
            value="[Open Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
            inline=False
        )

    embed.set_footer(text=get_footer_for_guild(guild_id))

    # Send the actual response
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="ask", description="Ask Harry general questions (not league-specific)")
async def ask_ai(interaction: discord.Interaction, question: str):
    """Ask AI general questions (use /harry for league-specific questions)"""
    guild_id = interaction.guild.id if interaction.guild else 0
    channel_id = interaction.channel.id if interaction.channel else 0

    # Check if AI_CHAT module is enabled
    if not server_config.is_module_enabled(guild_id, FeatureModule.AI_CHAT):
        await interaction.response.send_message(
            "💬 AI Chat is disabled on this server.\n"
            "An admin can enable it with `/admin config enable ai_chat`",
            ephemeral=True
        )
        return

    # Check if Harry is enabled in this channel
    if not server_config.is_channel_enabled(guild_id, channel_id):
        await interaction.response.send_message(
            "🔇 Harry isn't enabled in this channel.\n"
            "An admin can enable it with `/admin channels`",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🤖 AI Assistant Response",
        color=0x9b59b6
    )

    response_sent = False

    try:
        # Send initial response immediately
        await interaction.response.send_message("🤖 Thinking...", ephemeral=True)
        response_sent = True

        # Log the slash command usage
        guild_name = interaction.guild.name if interaction.guild else "DM"
        logger.info(f"🎯 SLASH COMMAND: /ask from {interaction.user} ({interaction.user.id}) in {guild_name} - '{question}'")
        logger.info(f"🔍 Slash command question: '{question}'")
        logger.info(f"🏠 Server: {guild_name} (ID: {interaction.guild.id if interaction.guild else 'DM'})")

        if not AI_AVAILABLE or not ai_assistant:
            embed.description = "AI integration not available. Please check the charter directly or use other commands."
        else:
            # Get personality based on server settings
            ask_guild_id = interaction.guild.id if interaction.guild else 0
            personality = server_config.get_personality_prompt(ask_guild_id)

            # Add Harry's personality to the ask command
            harry_question = f"{personality} Answer this question: {question}"

            # /ask ALWAYS uses general AI without charter context (not league-specific)
            # But we respect the LEAGUE module setting for schedule context
            ask_league_enabled = server_config.is_module_enabled(ask_guild_id, FeatureModule.LEAGUE)
            logger.info(f"🌍 /ask command - general AI without charter context (league_enabled={ask_league_enabled})")
            general_context = personality

            # Call OpenAI directly with general context (include league context only if LEAGUE enabled)
            logger.info("🔄 Attempting OpenAI API call...")
            response = await ai_assistant.ask_openai(harry_question, general_context, personality_prompt=personality, include_league_context=ask_league_enabled)
            if not response:
                # Fallback to Anthropic
                logger.info("⚠️ OpenAI failed, attempting Anthropic fallback...")
                response = await ai_assistant.ask_anthropic(harry_question, general_context, personality_prompt=personality, include_league_context=ask_league_enabled)

            if response:
                logger.info(f"✅ AI response received ({len(response)} characters)")
                embed.description = response
                embed.add_field(
                    name="💡 Note",
                    value="This is a general question. For league-specific questions, use `/harry` instead!",
                    inline=False
                )
            else:
                logger.error("❌ Both OpenAI and Anthropic failed to respond")
                embed.description = "Sorry, I couldn't get an AI response right now. Both OpenAI and Anthropic APIs failed. Check your API keys or try again later!"
                embed.add_field(
                    name="🔧 Troubleshooting",
                    value="Make sure OPENAI_API_KEY or ANTHROPIC_API_KEY is set in your environment variables.",
                    inline=False
                )
    except Exception as e:
        logger.error(f"❌ Exception in /ask command: {str(e)}", exc_info=True)
        if not response_sent:
            # If we haven't sent a response yet, send it as the initial response
            try:
                embed.description = f"Error getting AI response: {str(e)}"
                embed.add_field(
                    name="🔍 Error Details",
                    value=f"Check the logs for more information. Error type: {type(e).__name__}",
                    inline=False
                )
                await interaction.response.send_message(embed=embed)
                return
            except discord.errors.InteractionResponded:
                pass  # Already responded, try followup
        else:
            # Already sent initial response, use followup
            embed.description = f"Error getting AI response: {str(e)}"
            embed.add_field(
                name="🔍 Error Details",
                value=f"Check the logs for more information. Error type: {type(e).__name__}",
                inline=False
            )

    # Add charter link only if LEAGUE module is enabled
    guild_id_for_league = interaction.guild.id if interaction.guild else 0
    if server_config.is_module_enabled(guild_id_for_league, FeatureModule.LEAGUE):
        embed.add_field(
            name="📖 Full Charter",
            value="[Open League Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
            inline=False
        )

    embed.set_footer(text="CFB 26 League Bot - AI Assistant")

    # Send the actual response
    if response_sent:
        await interaction.followup.send(embed=embed)
    else:
        # Fallback: send as initial response if something went wrong
        try:
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error(f"❌ Failed to send /ask response: {str(e)}", exc_info=True)

@league_group.command(name="timer", description="Start advance countdown timer (Admin only)")
@app_commands.describe(hours="Number of hours for the countdown (default: 48)")
async def league_timer(interaction: discord.Interaction, hours: int = 48):
    """
    Start the advance countdown timer

    Args:
        hours: Number of hours for the countdown (default: 48)
    """
    # Check if league module is enabled
    if not await check_module_enabled(interaction, FeatureModule.LEAGUE):
        return

    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to start countdowns, ya muppet!", ephemeral=True)
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    # Validate hours (minimum 1, maximum 336 = 2 weeks)
    if hours < 1:
        await interaction.response.send_message("❌ Hours must be at least 1, ya numpty!", ephemeral=True)
        return
    if hours > 336:
        await interaction.response.send_message("❌ Maximum is 336 hours (2 weeks), mate!", ephemeral=True)
        return

    # Defer immediately - this operation takes time (stop timer, increment week, start timer, DM updates)
    try:
        await interaction.response.defer()
    except Exception as e:
        logger.error(f"Failed to defer /advance interaction: {e}")
        return

    # Stop existing timer if one is running (manual advance)
    status = timekeeper_manager.get_status(interaction.channel)
    if status.get('active'):
        logger.info(f"⏹️ Stopping existing timer before manual /advance")
        await timekeeper_manager.stop_timer(interaction.channel)

    # Increment the week (manual advance)
    season_info = timekeeper_manager.get_season_week()
    if season_info['season'] and season_info['week'] is not None:
        old_week = season_info['week']
        old_week_name = season_info.get('week_name', f"Week {old_week}")
        await timekeeper_manager.increment_week()
        # Refresh season_info after increment
        season_info = timekeeper_manager.get_season_week()
        new_week_name = season_info.get('week_name', f"Week {season_info['week']}")
        logger.info(f"📅 Manual /advance: {old_week_name} → {new_week_name}")

    # Start the countdown
    success = await timekeeper_manager.start_timer(interaction.channel, hours)

    if success:
        # Get season/week info for display (already refreshed above if incremented)
        if not season_info:
            season_info = timekeeper_manager.get_season_week()
        if season_info['season'] and season_info['week'] is not None:
            week_name = season_info.get('week_name', f"Week {season_info['week']}")
            next_week_name = get_week_name(season_info['week'] + 1)
            phase = season_info.get('phase', 'Regular Season')
            season_text = f"**Season {season_info['season']}**\n📍 {week_name} → **{next_week_name}**\n🏈 Phase: {phase}\n\n"
        else:
            season_text = ""

        embed = discord.Embed(
            title="⏰ Advance Countdown Started!",
            description=f"Right then, listen up ya wankers!\n\n🏈 **{hours} HOUR COUNTDOWN STARTED** 🏈\n\n{season_text}You got **{hours} hours** to get your bleedin' games done!\n\nI'll be remindin' you lot at:\n• 24 hours remaining (if applicable)\n• 12 hours remaining (if applicable)\n• 6 hours remaining (if applicable)\n• 1 hour remaining\n\nAnd when time's up... well, you'll know! 😈",
            color=Colors.SUCCESS
        )
        status = timekeeper_manager.get_status(interaction.channel)
        embed.add_field(
            name="⏳ Deadline",
            value=format_est_time(status['end_time'], '%A, %B %d at %I:%M %p'),
            inline=False
        )
        embed.set_footer(text="Harry's Advance Timer 🏈 | Use /league timer_status to check progress")

        # Send ephemeral confirmation to admin
        await interaction.followup.send("✅ Timer started! Announcement sent to #general.", ephemeral=True)

        # Send public announcement to #general
        notification_channel = get_notification_channel()
        if notification_channel:
            await notification_channel.send(content="@everyone", embed=embed)
            logger.info(f"⏰ Advance countdown started by {interaction.user} - {hours} hours - announced in #{notification_channel.name}")

            # Send schedule for the current week (if schedule_announcement enabled)
            if season_info and season_info.get('week') is not None:
                await send_week_schedule(notification_channel, season_info['week'], interaction.guild.id)
        else:
            # Fallback to current channel if #general not found
            await interaction.channel.send(content="@everyone", embed=embed)
            logger.warning(f"⚠️ #general not found, announced in {interaction.channel}")
    else:
        embed = discord.Embed(
            title="❌ Failed to Start Countdown!",
            description="Blimey, something went wrong starting the timer, mate!",
            color=Colors.ERROR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@league_group.command(name="timer_status", description="Check the current advance countdown status")
async def league_timer_status(interaction: discord.Interaction):
    """Check the current advance countdown status"""
    # Check if league module is enabled
    if not await check_module_enabled(interaction, FeatureModule.LEAGUE):
        return

    # Defer immediately to prevent timeout
    try:
        await interaction.response.defer()
    except discord.errors.InteractionResponded:
        # Already responded, continue with followup
        pass

    if not timekeeper_manager:
        await interaction.followup.send("❌ Timekeeper not available", ephemeral=True)
        return

    try:
        status = timekeeper_manager.get_status(interaction.channel)

        if not status['active']:
            embed = discord.Embed(
                title="⏰ No Countdown Active",
                description="There ain't no countdown runnin' right now, mate.\n\nUse `/league timer` to start the 48-hour countdown.",
                color=0x808080
            )
            await interaction.followup.send(embed=embed)
        else:
            hours = status['hours']
            minutes = status['minutes']

            # Determine urgency color
            if hours >= 24:
                color = 0x00ff00  # Green
                urgency = "Loads of time, but still play your fucking games!"
            elif hours >= 12:
                color = 0xffa500  # Orange
                urgency = "Getting closer now, better get crackin'!"
            elif hours >= 6:
                color = 0xff8c00  # Dark orange
                urgency = "Time's tickin' away! Get your games done!"
            elif hours >= 1:
                color = 0xff4500  # Red orange
                urgency = "BLOODY HELL! Time's almost up!"
            else:
                color = 0xff0000  # Red
                urgency = "LAST HOUR! GET MOVIN'!"

            # Get season/week info
            season_info = timekeeper_manager.get_season_week()
            season_text = ""
            if season_info['season'] and season_info['week'] is not None:
                week_name = season_info.get('week_name', f"Week {season_info['week']}")
                current_week = season_info['week']

                # Check if we're at Preseason (Week 29) - next advance starts new season!
                if current_week >= TOTAL_WEEKS_PER_SEASON - 1:
                    next_season = season_info['season'] + 1
                    season_text = f"\n\n🎉 **LAST WEEK OF SEASON {season_info['season']}!** 🎉\n"
                    season_text += f"📍 {week_name} → **Season {next_season}, Week 0 - Season Kickoff**\n"
                    season_text += f"🏈 Next advance starts a NEW SEASON!"
                else:
                    next_week = current_week + 1
                    next_week_info = get_week_info(next_week)
                    next_week_name = next_week_info["name"]
                    next_phase = next_week_info["phase"]
                    next_actions = next_week_info.get("actions", "")
                    next_notes = next_week_info.get("notes", "")

                    season_text = f"\n\n**Season {season_info['season']}**\n📍 {week_name} → **{next_week_name}**\n🏈 Phase: {next_phase}"
                    if next_actions:
                        season_text += f"\n\n📋 **Next Week Actions:**\n{next_actions}"
                    if next_notes:
                        season_text += f"\n⚠️ {next_notes}"

            embed = discord.Embed(
                title="⏰ Advance Countdown Status",
                description=f"**Time Remaining:** {hours}h {minutes}m\n\n{urgency}{season_text}",
                color=color
            )

            embed.add_field(
                name="📅 Started",
                value=format_est_time(status['start_time'], '%I:%M %p on %B %d'),
                inline=True
            )
            embed.add_field(
                name="⏳ Deadline",
                value=format_est_time(status['end_time'], '%I:%M %p on %B %d'),
                inline=True
            )

            # Add progress bar
            timer = timekeeper_manager.get_timer(interaction.channel)
            if timer:
                total_seconds = timer.duration_hours * 3600
                remaining_seconds = status['remaining'].total_seconds()
                progress = 1 - (remaining_seconds / total_seconds)
                bar_length = 20
                filled = int(bar_length * progress)
                bar = '█' * filled + '░' * (bar_length - filled)

                embed.add_field(
                    name="📊 Progress",
                    value=f"{bar} {int(progress * 100)}%",
                    inline=False
                )

                # Add persistence status (for verification)
                persistence_status = "✅ Persisted" if timekeeper_manager.state_message_id else "⚠️ Not persisted"
                embed.add_field(
                    name="💾 Persistence",
                    value=f"{persistence_status}\nTimer state saved to Discord for deployment survival",
                    inline=False
                )

            embed.set_footer(text="Harry's Advance Timer 🏈")
            await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(f"❌ Error in /time_status: {str(e)}", exc_info=True)
        await interaction.followup.send(f"❌ Error checking timer status: {str(e)}", ephemeral=True)

@league_group.command(name="timer_stop", description="Stop the current advance countdown (Admin only)")
async def league_timer_stop(interaction: discord.Interaction):
    """Stop the current advance countdown"""
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to stop countdowns!", ephemeral=True)
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    success = await timekeeper_manager.stop_timer(interaction.channel)

    if success:
        embed = discord.Embed(
            title="⏹️ Countdown Stopped",
            description="Right, countdown's been cancelled then!\n\nAll timers have been stopped.",
            color=Colors.ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)  # Admin-only confirmation
        logger.info(f"⏹️ Countdown stopped by {interaction.user} in {interaction.channel}")
    else:
        embed = discord.Embed(
            title="❌ No Active Countdown",
            description="There ain't no countdown to stop, ya numpty!",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@league_group.command(name="week", description="Check the current season and week")
async def league_week(interaction: discord.Interaction):
    """Check the current season and week"""
    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    season_info = timekeeper_manager.get_season_week()

    if not season_info['season'] or season_info['week'] is None:
        embed = discord.Embed(
            title="📅 Season/Week Not Set",
            description="The season and week haven't been set yet, mate!\n\nAn admin needs to use `/league set_week` to set it up.",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed)
        return

    week_name = season_info.get('week_name', f"Week {season_info['week']}")
    phase = season_info.get('phase', 'Unknown')
    week_num = season_info['week']

    # Get week details
    week_info = get_week_info(week_num)
    actions = week_info.get("actions", "")
    notes = week_info.get("notes", "")

    # Build description
    description = f"**Season {season_info['season']}**\n\n"
    description += f"📍 **{week_name}**\n"
    description += f"🏈 Phase: {phase}\n"
    description += f"📊 Week {week_num} of {TOTAL_WEEKS_PER_SEASON - 1}"

    if actions:
        description += f"\n\n📋 **Available Actions:**\n{actions}"
    if notes:
        description += f"\n\n⚠️ **Note:** {notes}"

    # Show what's next
    if week_num >= TOTAL_WEEKS_PER_SEASON - 1:
        description += f"\n\n🎉 **Next:** Season {season_info['season'] + 1}, Week 0 - Season Kickoff!"
    else:
        next_week_info = get_week_info(week_num + 1)
        description += f"\n\n➡️ **Next:** {next_week_info['name']}"

    embed = discord.Embed(
        title="📅 Current Week",
        description=description,
        color=Colors.SUCCESS
    )
    embed.set_footer(text="Harry's Week Tracker 🏈 | Use /league set_week to change")
    await interaction.response.send_message(embed=embed)

@league_group.command(name="weeks", description="View the full CFB 26 Dynasty week schedule")
async def league_weeks(interaction: discord.Interaction):
    """View the full week schedule for a CFB 26 Dynasty season"""
    # Get current week info
    current_week = None
    current_season = None
    if timekeeper_manager:
        season_info = timekeeper_manager.get_season_week()
        if season_info['week'] is not None:
            current_week = season_info['week']
            current_season = season_info['season']

    # Build description with current/next week at the top
    description = ""

    if current_week is not None and current_season is not None:
        # Current week info
        current_info = get_week_info(current_week)
        current_actions = current_info.get("actions", "")
        current_notes = current_info.get("notes", "")

        description += f"**Season {current_season}**\n\n"
        description += f"📍 **Current Week:** {current_info['name']}\n"
        description += f"🏈 Phase: {current_info['phase']}\n"
        if current_actions:
            description += f"📋 Actions: {current_actions}\n"
        if current_notes:
            description += f"⚠️ {current_notes}\n"

        # Next week info
        if current_week >= TOTAL_WEEKS_PER_SEASON - 1:
            description += f"\n➡️ **Next Week:** Season {current_season + 1}, Week 0 - Season Kickoff\n"
            description += f"🏈 Phase: Regular Season\n"
            description += f"📋 Actions: Season begins\n"
        else:
            next_week = current_week + 1
            next_info = get_week_info(next_week)
            next_actions = next_info.get("actions", "")
            next_notes = next_info.get("notes", "")

            description += f"\n➡️ **Next Week:** {next_info['name']}\n"
            description += f"🏈 Phase: {next_info['phase']}\n"
            if next_actions:
                description += f"📋 Actions: {next_actions}\n"
            if next_notes:
                description += f"⚠️ {next_notes}\n"

        description += "\n───────────────────────\n"
    else:
        description += "*Season/week not set. Use `/league set_week` to set it.*\n\n"

    description += "**Full Week Schedule:**\n"

    # Create embed
    embed = discord.Embed(
        title="📅 CFB 26 Dynasty Week Schedule",
        description=description,
        color=Colors.SUCCESS
    )

    # Build the week lists by phase
    regular_season = []
    post_season = []
    offseason = []

    for week_num in sorted(CFB_DYNASTY_WEEKS.keys()):
        week_data = CFB_DYNASTY_WEEKS[week_num]
        phase = week_data["phase"]
        name = week_data["short"]  # Use short name for the list

        # Add marker if this is the current week
        if current_week is not None and week_num == current_week:
            line = f"**► `{week_num:2d}` {name}** ◄"
        else:
            line = f"`{week_num:2d}` {name}"

        if phase == "Regular Season":
            regular_season.append(line)
        elif phase == "Post-Season":
            post_season.append(line)
        else:
            offseason.append(line)

    # Regular Season field
    embed.add_field(
        name="🏈 Regular Season",
        value="\n".join(regular_season),
        inline=True
    )

    # Post-Season field
    embed.add_field(
        name="🏆 Post-Season",
        value="\n".join(post_season),
        inline=True
    )

    # Offseason field
    embed.add_field(
        name="📝 Offseason",
        value="\n".join(offseason),
        inline=True
    )

    embed.set_footer(text="Harry's Week Tracker 🏈 | Use /league week for more details")
    await interaction.response.send_message(embed=embed)

# ==================== Schedule Commands ====================

@league_group.command(name="games", description="View the games for a specific week")
@app_commands.describe(
    week="Week number (0-13 for regular season, leave empty for current week)"
)
async def league_games(interaction: discord.Interaction, week: Optional[int] = None):
    """View the schedule for a specific week"""
    # Check if league module is enabled
    if not await check_module_enabled(interaction, FeatureModule.LEAGUE):
        return

    if not schedule_manager:
        await interaction.response.send_message("❌ Schedule manager not available", ephemeral=True)
        return

    # If no week specified, use current week
    if week is None:
        if timekeeper_manager:
            season_info = timekeeper_manager.get_season_week()
            if season_info['week'] is not None and season_info['week'] <= 13:
                week = season_info['week']
            else:
                await interaction.response.send_message(
                    "❌ No week specified and current week is not in regular season. Use `/league games week:X`",
                    ephemeral=True
                )
                return
        else:
            await interaction.response.send_message(
                "❌ No week specified. Use `/league games week:X`",
                ephemeral=True
            )
            return

    # Validate week
    if week < 0 or week > 13:
        await interaction.response.send_message(
            "❌ Week must be between 0 and 13 (regular season), ya numpty!",
            ephemeral=True
        )
        return

    week_data = schedule_manager.get_week_schedule(week)
    if not week_data:
        await interaction.response.send_message(
            f"❌ No schedule data for Week {week}",
            ephemeral=True
        )
        return

    # Build embed
    embed = discord.Embed(
        title=f"📅 Week {week} Schedule",
        description=f"Season {schedule_manager.season} matchups:",
        color=Colors.SUCCESS
    )

    # Bye teams (bold user teams)
    bye_teams = week_data.get('bye_teams', [])
    if bye_teams:
        embed.add_field(
            name="🛋️ Bye Week",
            value=schedule_manager.format_bye_teams(bye_teams),
            inline=False
        )

    # Games (bold user teams)
    games = week_data.get('games', [])
    if games:
        games_text = "\n".join([schedule_manager.format_game(g, "•") for g in games])
        embed.add_field(
            name="🏈 Games",
            value=games_text,
            inline=False
        )

    embed.set_footer(text="Harry's Schedule Tracker 🏈 | Use /find_game for specific team info")
    await interaction.response.send_message(embed=embed)

@league_group.command(name="find_game", description="Find a team's game for a specific week")
@app_commands.describe(
    team="Team name (e.g., Hawaii, LSU, Notre Dame)",
    week="Week number (0-13, leave empty for current week)"
)
async def league_find_game(interaction: discord.Interaction, team: str, week: Optional[int] = None):
    """Find a specific team's game in the dynasty schedule"""
    if not schedule_manager:
        await interaction.response.send_message("❌ Schedule manager not available", ephemeral=True)
        return

    # If no week specified, use current week
    if week is None:
        if timekeeper_manager:
            season_info = timekeeper_manager.get_season_week()
            if season_info['week'] is not None and season_info['week'] <= 13:
                week = season_info['week']
            else:
                await interaction.response.send_message(
                    "❌ No week specified and current week is not in regular season. Use `/find_game team:X week:Y`",
                    ephemeral=True
                )
                return
        else:
            await interaction.response.send_message(
                "❌ No week specified. Use `/find_game team:X week:Y`",
                ephemeral=True
            )
            return

    # Find the team
    found_team = schedule_manager.find_team(team)
    if not found_team:
        await interaction.response.send_message(
            f"❌ Couldn't find team '{team}'. Available teams: {', '.join(schedule_manager.teams)}",
            ephemeral=True
        )
        return

    # Get the game
    game = schedule_manager.get_team_game(found_team, week)
    if not game:
        await interaction.response.send_message(
            f"❌ No game data for {found_team} in Week {week}",
            ephemeral=True
        )
        return

    if game.get('bye'):
        embed = discord.Embed(
            title=f"🛋️ {found_team} - Week {week}",
            description=f"**{found_team}** has a bye week!\n\nTime to rest up and prepare for the next game.",
            color=0x808080
        )
    else:
        location_emoji = "🏠" if game['location'] == 'home' else "✈️"
        location_text = "HOME" if game['location'] == 'home' else "AWAY"

        embed = discord.Embed(
            title=f"🏈 {found_team} - Week {week}",
            description=f"**{game['matchup']}**",
            color=Colors.SUCCESS
        )
        embed.add_field(
            name="Opponent",
            value=game['opponent'],
            inline=True
        )
        embed.add_field(
            name=f"{location_emoji} Location",
            value=location_text,
            inline=True
        )

    embed.set_footer(text="Harry's Schedule Tracker 🏈")
    await interaction.response.send_message(embed=embed)

@league_group.command(name="byes", description="Show which teams have a bye this week")
@app_commands.describe(
    week="Week number (0-13, leave empty for current week)"
)
async def league_byes(interaction: discord.Interaction, week: Optional[int] = None):
    """Show teams on bye for a specific week"""
    if not schedule_manager:
        await interaction.response.send_message("❌ Schedule manager not available", ephemeral=True)
        return

    # If no week specified, use current week
    if week is None:
        if timekeeper_manager:
            season_info = timekeeper_manager.get_season_week()
            if season_info['week'] is not None and season_info['week'] <= 13:
                week = season_info['week']
            else:
                await interaction.response.send_message(
                    "❌ No week specified and current week is not in regular season.",
                    ephemeral=True
                )
                return
        else:
            await interaction.response.send_message("❌ No week specified.", ephemeral=True)
            return

    bye_teams = schedule_manager.get_bye_teams(week)

    if bye_teams:
        embed = discord.Embed(
            title=f"🛋️ Week {week} Bye Teams",
            description=f"These lucky sods get a week off:\n\n**{', '.join(bye_teams)}**",
            color=0x808080
        )
    else:
        embed = discord.Embed(
            title=f"🏈 Week {week} - No Byes!",
            description="Everyone's playing this week! No rest for the wicked!",
            color=Colors.SUCCESS
        )

    embed.set_footer(text="Harry's Schedule Tracker 🏈")
    await interaction.response.send_message(embed=embed)

@league_group.command(name="set_week", description="Set the current season and week (Admin only)")
@app_commands.describe(
    season="Season number",
    week="Week number (0-13 for regular season)"
)
async def league_set_week(interaction: discord.Interaction, season: int, week: int):
    """Set the current season and week"""
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to set season/week, ya muppet!", ephemeral=True)
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    # Validate inputs
    if season < 1:
        await interaction.response.send_message("❌ Season must be at least 1, ya numpty!", ephemeral=True)
        return
    if week < 0:
        await interaction.response.send_message("❌ Week must be at least 0, ya numpty!", ephemeral=True)
        return

    # Set season/week
    success = await timekeeper_manager.set_season_week(season, week)

    if success:
        week_info = get_week_info(week)
        week_name = week_info["name"]
        phase = week_info["phase"]
        actions = week_info.get("actions", "")
        notes = week_info.get("notes", "")

        description = f"Right then! Season and week have been set.\n\n**Season {season}**\n📍 **{week_name}**\n🏈 Phase: {phase}"
        if actions:
            description += f"\n\n📋 **Actions Available:**\n{actions}"
        if notes:
            description += f"\n\n⚠️ **Note:** {notes}"
        description += "\n\nThe week will automatically increment when the advance timer completes!"

        embed = discord.Embed(
            title="📅 Season/Week Set!",
            description=description,
            color=Colors.SUCCESS
        )
        embed.set_footer(text="Harry's Advance Timer 🏈 | Week will increment on advance")
        await interaction.response.send_message(embed=embed, ephemeral=True)  # Admin-only confirmation
        logger.info(f"📅 Season/Week set to Season {season}, {week_name} by {interaction.user}")
    else:
        embed = discord.Embed(
            title="❌ Failed to Set Season/Week",
            description="Couldn't set the season/week, mate. Check your inputs!",
            color=Colors.ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@league_group.command(name="timer_channel", description="Set the channel for timer notifications (Admin only)")
@app_commands.describe(channel="Channel for timer notifications")
async def league_timer_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set the channel where timer notifications (advance announcements, countdowns) will be sent"""
    global GENERAL_CHANNEL_ID

    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to set the timer channel, ya muppet!", ephemeral=True)
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    # Update the channel ID and persist it
    success = await timekeeper_manager.set_notification_channel(channel.id)
    if success:
        GENERAL_CHANNEL_ID = channel.id  # Also update the module-level constant

        embed = discord.Embed(
            title="📢 Timer Notification Channel Set!",
            description=f"Right then! All timer notifications will now go to:\n\n**#{channel.name}** (<#{channel.id}>)\n\nThis includes:\n• Advance countdown start\n• 24h/12h/6h/1h warnings\n• TIME'S UP announcements\n• Schedule updates\n\n✅ **Saved!** This will persist across bot restarts.",
            color=Colors.SUCCESS
        )
        embed.set_footer(text="Harry's Advance Timer 🏈")
        await interaction.response.send_message(embed=embed, ephemeral=True)  # Admin-only confirmation
        logger.info(f"📢 Timer notification channel set to #{channel.name} by {interaction.user}")
    else:
        await interaction.response.send_message("❌ Failed to save the timer channel setting!", ephemeral=True)


@admin_group.command(name="set_channel", description="Set the channel for admin outputs and bot updates (Admin only)")
@app_commands.describe(
    channel="Select a channel from the list (for visible channels)",
    channel_id="Or paste a channel ID directly (for private channels)"
)
async def admin_set_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel = None,
    channel_id: str = None
):
    """Set the channel where admin messages and bot updates will be sent"""
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to set the admin channel, ya muppet!", ephemeral=True)
        return

    if not interaction.guild:
        await interaction.response.send_message("❌ This command only works in servers!", ephemeral=True)
        return

    # Determine channel - either from picker or from ID
    if channel:
        target_channel_id = channel.id
        channel_name = f"#{channel.name}"
    elif channel_id:
        try:
            target_channel_id = int(channel_id.strip())
            # Try to fetch channel name if possible
            fetched_channel = interaction.guild.get_channel(target_channel_id)
            if fetched_channel:
                channel_name = f"#{fetched_channel.name}"
            else:
                channel_name = f"<#{target_channel_id}> (private)"
        except ValueError:
            await interaction.response.send_message("❌ Invalid channel ID! It should be a number like `1459372492387778704`", ephemeral=True)
            return
    else:
        await interaction.response.send_message("❌ Provide either a `channel` or a `channel_id`!", ephemeral=True)
        return

    guild_id = interaction.guild.id

    # Update the channel ID and persist it
    server_config.set_admin_channel(guild_id, target_channel_id)
    await server_config.save_to_discord()

    embed = discord.Embed(
        title="🔧 Admin Channel Set!",
        description=f"Right then! Admin outputs will now go to:\n\n**{channel_name}** (<#{target_channel_id}>)\n\nThis includes:\n• Bot startup/restart notifications\n• Timer restore messages\n• Config change confirmations\n• Error reports\n\n✅ **Saved!** This will persist across bot restarts.\n\n⚠️ **Note:** Make sure Harry has access to send messages in that channel!",
        color=Colors.SUCCESS
    )
    embed.set_footer(text=Footers.CONFIG)
    await interaction.response.send_message(embed=embed, ephemeral=True)
    logger.info(f"🔧 Admin channel set to #{channel.name} for guild {guild_id} by {interaction.user}")


# ==================== League Staff Commands ====================

@league_group.command(name="staff", description="View the current league owner and co-commissioner")
async def league_staff(interaction: discord.Interaction):
    """View current league staff"""
    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    staff = timekeeper_manager.get_league_staff()

    # Build the embed
    owner_text = f"<@{staff['owner_id']}>" if staff['owner_id'] else "Not set"

    if staff['co_commish_name'] == timekeeper_manager.NO_CO_COMMISH:
        co_commish_text = f"😤 {timekeeper_manager.NO_CO_COMMISH}"
    elif staff['co_commish_id']:
        co_commish_text = f"<@{staff['co_commish_id']}>"
    else:
        co_commish_text = "Not set"

    embed = discord.Embed(
        title="👑 League Staff",
        description="The brave souls running this circus...",
        color=0xffd700  # Gold
    )
    embed.add_field(
        name="🏆 League Owner",
        value=owner_text,
        inline=False
    )
    embed.add_field(
        name="👤 Co-Commissioner",
        value=co_commish_text,
        inline=False
    )
    embed.set_footer(text="Harry's League Tracker 🏈 | Admins use /set_league_owner and /set_co_commish")

    await interaction.response.send_message(embed=embed)

@league_group.command(name="set_owner", description="Set the league owner (Admin only)")
@app_commands.describe(user="User to set as league owner")
async def league_set_owner(interaction: discord.Interaction, user: discord.User):
    """Set the league owner"""
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to set the league owner, ya muppet!", ephemeral=True)
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    success = await timekeeper_manager.set_league_owner(user)

    if success:
        embed = discord.Embed(
            title="👑 League Owner Set!",
            description=f"All hail the new boss!\n\n**League Owner:** <@{user.id}>\n\nMay their reign be glorious (or at least not completely shite)!",
            color=0xffd700
        )
        embed.set_footer(text="Harry's League Tracker 🏈")
        await interaction.response.send_message(embed=embed, ephemeral=True)  # Admin-only confirmation
        logger.info(f"👑 League owner set to {user.display_name} by {interaction.user}")
    else:
        await interaction.response.send_message("❌ Failed to set league owner, mate!", ephemeral=True)

@league_group.command(name="set_commish", description="Set the co-commissioner (Admin only)")
@app_commands.describe(
    user="The user to set as co-commissioner (leave empty if setting to 'none')",
    none="Set to 'We don't fucking have one'"
)
async def league_set_commish(
    interaction: discord.Interaction,
    user: Optional[discord.User] = None,
    none: bool = False
):
    """Set the co-commissioner"""
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to set the co-commish, ya muppet!", ephemeral=True)
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    # Must specify either user or none
    if not user and not none:
        await interaction.response.send_message(
            "❌ You gotta either pick a user OR set `none` to True if you don't have a co-commish, ya numpty!",
            ephemeral=True
        )
        return

    if user and none:
        await interaction.response.send_message(
            "❌ Make up your mind! Either pick a user OR set none to True, not both!",
            ephemeral=True
        )
        return

    success = await timekeeper_manager.set_co_commish(user=user, no_co_commish=none)

    if success:
        if none:
            embed = discord.Embed(
                title="👤 Co-Commissioner Updated!",
                description=f"Right then, no co-commish it is!\n\n**Co-Commissioner:** 😤 {timekeeper_manager.NO_CO_COMMISH}\n\nThe owner's flying solo on this one!",
                color=Colors.WARNING
            )
        else:
            embed = discord.Embed(
                title="👤 Co-Commissioner Set!",
                description=f"We've got ourselves a co-commish!\n\n**Co-Commissioner:** <@{user.id}>\n\nHope they're ready to help wrangle these muppets!",
                color=Colors.SUCCESS
            )
        embed.set_footer(text="Harry's League Tracker 🏈")
        await interaction.response.send_message(embed=embed, ephemeral=True)  # Admin-only confirmation
        if none:
            logger.info(f"👤 Co-commish set to 'none' by {interaction.user}")
        else:
            logger.info(f"👤 Co-commish set to {user.display_name} by {interaction.user}")
    else:
        await interaction.response.send_message("❌ Failed to set co-commish, mate!", ephemeral=True)

@league_group.command(name="pick_commish", description="Harry analyzes the chat and picks a co-commissioner")
@app_commands.describe(
    channel="Channel to analyze (default: current channel)",
    hours="How many hours of chat history to analyze (default: 168 = 1 week)"
)
async def league_pick_commish(
    interaction: discord.Interaction,
    channel: Optional[discord.TextChannel] = None,
    hours: int = 168
):
    """Have Harry analyze chat activity and recommend a co-commissioner"""
    # Defer IMMEDIATELY - this takes a while and Discord times out after 3 seconds
    await interaction.response.defer()

    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.followup.send(
            "❌ Only admins can ask me to pick a commish, ya muppet!",
            ephemeral=True
        )
        return

    # Use provided channel or fall back to current channel
    target_channel = channel or interaction.channel

    if not channel_summarizer:
        await interaction.followup.send("❌ Channel summarizer not available", ephemeral=True)
        return

    if not AI_AVAILABLE or not ai_assistant:
        await interaction.followup.send("❌ AI not available for this analysis", ephemeral=True)
        return

    # Validate hours
    if hours < 24:
        await interaction.followup.send("❌ Need at least 24 hours of history to judge these muppets!", ephemeral=True)
        return
    if hours > 720:  # 30 days max
        await interaction.followup.send("❌ Max 720 hours (30 days). I ain't reading a novel!", ephemeral=True)
        return

    try:
        # Fetch messages
        messages = await channel_summarizer.fetch_messages(target_channel, hours, limit=1000)

        if not messages or len(messages) < 10:
            await interaction.followup.send(
                f"❌ Not enough chat activity in #{target_channel.name} to analyze! Need more messages to judge you lot."
            )
            return

        # Format messages for analysis
        formatted_messages = channel_summarizer.format_messages_for_summary(messages)

        # Count participation
        participant_counts = {}
        for msg in messages:
            author = msg.author.display_name
            author_id = msg.author.id
            if not msg.author.bot:  # Skip bots
                if author not in participant_counts:
                    participant_counts[author] = {"count": 0, "id": author_id}
                participant_counts[author]["count"] += 1

        # Sort by participation
        sorted_participants = sorted(
            participant_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )

        # Build participation summary
        participation_summary = "Chat Participation (last {} hours):\n".format(hours)
        for name, data in sorted_participants[:15]:  # Top 15
            participation_summary += f"- {name}: {data['count']} messages\n"

        # Create the AI prompt
        num_participants = len(participant_counts)
        participant_names = ", ".join(participant_counts.keys())

        prompt = f"""You are Harry, a completely insane and hilariously sarcastic CFB 26 league assistant. You've been asked to analyze chat activity and recommend who should be the new co-commissioner.

⚠️ THERE ARE EXACTLY {num_participants} PARTICIPANTS TO RANK: {participant_names}
⚠️ YOUR OUTPUT MUST HAVE EXACTLY {num_participants} RANKINGS (#{1} through #{num_participants})
⚠️ EACH PERSON APPEARS ONLY ONCE - NO DUPLICATES!

PARTICIPATION DATA:
{participation_summary}

RECENT CHAT MESSAGES (sample):
{formatted_messages[:8000]}

YOUR TASK:
Analyze each active participant and rate them on these factors (1-10 scale):

📊 **ANALYSIS FACTORS:**
1. **Activity Level** - How often do they show up and participate?
2. **Helpfulness** - Do they answer questions and help others?
3. **Leadership** - Do they take initiative and organize things?
4. **🚨 Asshole Detector** - Are they a dick? Do they start drama? Toxic behavior?
5. **Reliability** - Do they follow through? Play their games on time?
6. **Humor/Vibes** - Are they fun to have around or a buzzkill?
7. **Knowledge** - Do they know the rules and the game?
8. **Drama Score** - Do they cause unnecessary drama? (Lower is better)

Based on your analysis:
1. Rate EVERY participant with scores and a summary
2. Pick your TOP RECOMMENDATION for co-commissioner
3. Call out the BIGGEST ASSHOLE who should NEVER be commish
4. Roast everyone appropriately

FORMAT YOUR RESPONSE LIKE THIS:

🏆 **HARRY'S CO-COMMISSIONER ANALYSIS**

**📊 FULL RANKINGS (Best to Worst):**

**#1. [Name]** ✅ RECOMMENDED
- 📊 Activity: X/10 | 🤝 Helpful: X/10 | 👑 Leadership: X/10
- 🚨 Asshole: X/10 | 🎭 Drama: X/10 | 😂 Vibes: X/10
- **Overall: X/10** - [2-3 sentence sarcastic roast/commentary about them]

**#2. [Name]**
- 📊 Activity: X/10 | 🤝 Helpful: X/10 | 👑 Leadership: X/10
- 🚨 Asshole: X/10 | 🎭 Drama: X/10 | 😂 Vibes: X/10
- **Overall: X/10** - [2-3 sentence sarcastic roast/commentary]

[Continue for ALL participants, ranked from best to worst]

**#[Last]. [Name]** 🚨 DO NOT PICK
- 📊 Activity: X/10 | 🤝 Helpful: X/10 | 👑 Leadership: X/10
- 🚨 Asshole: X/10 | 🎭 Drama: X/10 | 😂 Vibes: X/10
- **Overall: X/10** - [Brutal but funny roast of why they're last]

---
🏆 **FINAL VERDICT:** [Winner Name] should be co-commish because [brief funny reason]
🚫 **DO NOT PICK:** [Last Ranked Name] - [Why they're a terrible co-commish candidate]
🚨 **BIGGEST ASSHOLE:** [Name with highest asshole score] - [Savage one-liner about why they're the biggest dick]

⚠️⚠️⚠️ CRITICAL RULES - READ CAREFULLY ⚠️⚠️⚠️
1. There are EXACTLY {num_participants} people. You MUST have EXACTLY {num_participants} rankings.
2. Each person appears ONLY ONCE! If you list someone twice, you FAILED.
3. The names are: {participant_names} - rank ALL of them, each ONE time only.
4. #1 is the BEST candidate for co-commissioner, #{num_participants} is the WORST candidate.
5. FINAL VERDICT winner must be #1 ranked person.
6. DO NOT PICK is the #{num_participants} ranked person - they're the worst CO-COMMISH CANDIDATE
   - Could be due to: low activity, unreliable, bad leadership, absent, etc.
7. BIGGEST ASSHOLE is whoever has the HIGHEST "🚨 Asshole" score - this could be ANYONE!
   - Could be #1 ranked (great leader but a dick) or #last (inactive AND a dick) or anyone in between
   - Look at the messages - who starts drama? Who is toxic? Who is rude to others?
   - If everyone has low asshole scores (0-2), say "No major assholes detected... yet 👀"
8. DO NOT PICK and BIGGEST ASSHOLE can be DIFFERENT people or the SAME person

Be extremely sarcastic, funny, and insane. Give each person a proper roast!"""

        # Ask AI with higher token limit for full analysis with proper roasts
        # This command is LEAGUE-only, so always include league context
        response = await ai_assistant.ask_openai(prompt, "Co-Commissioner Selection Analysis", max_tokens=2000, include_league_context=True)
        if not response:
            response = await ai_assistant.ask_anthropic(prompt, "Co-Commissioner Selection Analysis", max_tokens=2000, include_league_context=True)

        if not response:
            await interaction.followup.send("❌ AI couldn't analyze the chat. Maybe you're all equally terrible?")
            return

        # Discord embed description limit is 4096 chars
        # If response is too long, send as regular message(s) instead
        stats_text = (f"\n\n---\n📊 **Analysis Details**\n"
                      f"📍 Channel: **#{target_channel.name}**\n"
                      f"📨 Analyzed **{len(messages)}** messages over **{hours}** hours\n"
                      f"👥 **{len(participant_counts)}** participants evaluated\n"
                      f"🚨 Asshole detector: **ACTIVE**\n"
                      f"*Use /set_co_commish to make it official!*")

        full_response = f"# 👑 Co-Commissioner Selection Analysis\n\n{response}{stats_text}"

        # Discord message limit is 2000 chars - split if needed
        if len(full_response) <= 2000:
            await interaction.followup.send(full_response)
        else:
            # Split into chunks
            chunks = []
            current_chunk = ""

            for line in full_response.split('\n'):
                if len(current_chunk) + len(line) + 1 > 1900:  # Leave some buffer
                    chunks.append(current_chunk)
                    current_chunk = line
                else:
                    current_chunk += '\n' + line if current_chunk else line

            if current_chunk:
                chunks.append(current_chunk)

            # Send each chunk
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await interaction.followup.send(chunk)
                else:
                    await interaction.channel.send(chunk)
        logger.info(f"👑 Co-commish analysis completed by {interaction.user} for #{target_channel.name}")

    except Exception as e:
        logger.error(f"❌ Error in pick_commish: {e}", exc_info=True)
        await interaction.followup.send(f"❌ Something went wrong analyzing you muppets: {str(e)}")

# ==================== Owner Nagging Commands (Bot Owner Only) ====================

@league_group.command(name="nag", description="Start spamming the league owner to advance (Bot Owner only)")
@app_commands.describe(
    interval="How often to nag in minutes (default: 5)"
)
async def league_nag(interaction: discord.Interaction, interval: int = 5):
    """Start nagging the league owner to advance the week"""
    # This is for the bot owner ONLY - check application info
    try:
        app_info = await bot.application_info()
        bot_owner_id = app_info.owner.id if app_info.owner else None
    except Exception:
        bot_owner_id = None  # Couldn't fetch app info

    if not bot_owner_id or interaction.user.id != bot_owner_id:
        await interaction.response.send_message(
            "❌ Nice try, but only the bot owner can unleash this chaos! 😈",
            ephemeral=True
        )
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    # Check if league owner is set
    staff = timekeeper_manager.get_league_staff()
    if not staff['owner_id']:
        await interaction.response.send_message(
            "❌ No league owner set! Use `/set_league_owner` first, ya numpty!",
            ephemeral=True
        )
        return

    # Validate interval
    if interval < 1:
        await interaction.response.send_message("❌ Interval must be at least 1 minute!", ephemeral=True)
        return
    if interval > 60:
        await interaction.response.send_message("❌ Max interval is 60 minutes. We want to annoy 'em, not forget about 'em!", ephemeral=True)
        return

    # Check if already nagging
    if timekeeper_manager.is_nagging():
        await interaction.response.send_message(
            "❌ Already nagging the owner! Use `/stop_nag` to stop first.",
            ephemeral=True
        )
        return

    success = await timekeeper_manager.start_nagging(interval)

    if success:
        embed = discord.Embed(
            title="😈 NAGGING ACTIVATED!",
            description=f"Alright, let the chaos begin!\n\n"
                       f"**Target:** <@{staff['owner_id']}>\n"
                       f"**Frequency:** Every {interval} minute{'s' if interval > 1 else ''}\n\n"
                       f"They're gonna LOVE this! 🔥\n\n"
                       f"Use `/stop_nag` when they finally advance (or beg for mercy).",
            color=Colors.ERROR
        )
        embed.set_footer(text="Harry's Revenge System 🏈 | May God have mercy on their soul")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"😈 Nagging started by {interaction.user} - interval: {interval} minutes")
    else:
        await interaction.response.send_message("❌ Failed to start nagging!", ephemeral=True)

@league_group.command(name="stop_nag", description="Stop spamming the league owner (Bot Owner only)")
async def league_stop_nag(interaction: discord.Interaction):
    """Stop nagging the league owner"""
    # This is for the bot owner ONLY
    try:
        app_info = await bot.application_info()
        bot_owner_id = app_info.owner.id if app_info.owner else None
    except Exception:
        bot_owner_id = None  # Couldn't fetch app info

    if not bot_owner_id or interaction.user.id != bot_owner_id:
        await interaction.response.send_message(
            "❌ Only the bot owner can stop the chaos they started! 😈",
            ephemeral=True
        )
        return

    if not timekeeper_manager:
        await interaction.response.send_message("❌ Timekeeper not available", ephemeral=True)
        return

    if not timekeeper_manager.is_nagging():
        await interaction.response.send_message(
            "❌ Not currently nagging anyone. Use `/nag_owner` to start!",
            ephemeral=True
        )
        return

    success = await timekeeper_manager.stop_nagging()

    if success:
        embed = discord.Embed(
            title="😇 Nagging Stopped",
            description="Alright, I'll give 'em a break... for now.\n\n"
                       "The league owner has been spared (temporarily).",
            color=Colors.SUCCESS
        )
        embed.set_footer(text="Harry's Mercy System 🏈 | They got lucky this time")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"😇 Nagging stopped by {interaction.user}")
    else:
        await interaction.response.send_message("❌ Failed to stop nagging!", ephemeral=True)

@bot.tree.command(name="summarize", description="Summarize channel activity for a time period")
async def summarize_channel(
    interaction: discord.Interaction,
    hours: int = 24,
    focus: Optional[str] = None
):
    """
    Summarize channel activity

    Args:
        hours: Number of hours to look back (default: 24)
        focus: Optional focus area for the summary (e.g., "rules", "voting", "decisions")
    """
    guild_id = interaction.guild.id if interaction.guild else 0
    channel_id = interaction.channel.id if interaction.channel else 0

    # Check if AI_CHAT module is enabled
    if not server_config.is_module_enabled(guild_id, FeatureModule.AI_CHAT):
        await interaction.response.send_message(
            "💬 AI Chat is disabled on this server.\n"
            "An admin can enable it with `/admin config enable ai_chat`",
            ephemeral=True
        )
        return

    # Check if Harry is enabled in this channel
    if not server_config.is_channel_enabled(guild_id, channel_id):
        await interaction.response.send_message(
            "🔇 Harry isn't enabled in this channel.\n"
            "An admin can enable it with `/admin channels`",
            ephemeral=True
        )
        return

    if not channel_summarizer:
        await interaction.response.send_message("❌ Channel summarizer not available", ephemeral=True)
        return

    try:
        # Send initial response IMMEDIATELY to avoid timeout
        await interaction.response.defer()

        # Validate hours input
        if hours < 1:
            hours = 1
        elif hours > 168:  # Max 1 week
            hours = 168

        # Clean up focus parameter
        focus_text = focus.strip() if focus else None
        if focus_text:
            focus_text = focus_text.strip()

        # Send "working" message
        focus_description = f" focusing on **{focus_text}**" if focus_text else ""
        embed = discord.Embed(
            title="📊 Generating Summary...",
            description=f"Right then, let me 'ave a look through the last **{hours} hours** of messages in this channel{focus_description}...\n\nThis might take a mo', so don't get your knickers in a twist!",
            color=Colors.WARNING
        )
        await interaction.followup.send(embed=embed)

        # Generate the summary
        focus_log = f" (focus: {focus_text})" if focus_text else ""
        logger.info(f"📊 Summary requested by {interaction.user} for #{interaction.channel.name} ({hours} hours{focus_log})")
        summary = await channel_summarizer.get_channel_summary(
            interaction.channel,
            hours=hours,
            focus=focus_text,
            limit=500
        )

        # Format the response
        title_focus = f" - {focus_text.title()}" if focus_text else ""
        embed = discord.Embed(
            title=f"📊 Channel Summary - Last {hours} Hour{'s' if hours > 1 else ''}{title_focus}",
            description=summary,
            color=Colors.SUCCESS
        )

        embed.add_field(
            name="📍 Channel",
            value=f"#{interaction.channel.name}",
            inline=True
        )

        embed.add_field(
            name="⏰ Time Period",
            value=f"Last {hours} hour{'s' if hours > 1 else ''}",
            inline=True
        )

        if focus_text:
            embed.add_field(
                name="🎯 Focus",
                value=focus_text,
                inline=True
            )

        embed.set_footer(text=f"Harry's Channel Summary 🏈 | Requested by {interaction.user.display_name}")

        await interaction.followup.send(embed=embed)
        logger.info(f"✅ Summary delivered for #{interaction.channel.name}")

    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Oi! I don't 'ave permission to read message history in this channel, ya muppet!\n\n**To fix:** Give me 'Read Message History' permission in channel settings.",
            color=Colors.ERROR
        )
        await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(f"❌ Error generating summary: {e}")
        embed = discord.Embed(
            title="❌ Summary Failed",
            description=f"Bloody hell! Somethin' went wrong while generatin' the summary:\n\n`{str(e)}`\n\nTry again later, mate!",
            color=Colors.ERROR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@charter_group.command(name="add", description="Add a new rule to the charter (Admin only)")
@app_commands.describe(
    section_title="Title for the new rule section",
    rule_content="The rule text content",
    position="Where to add: 'end' or 'start' (default: end)"
)
async def charter_add(
    interaction: discord.Interaction,
    section_title: str,
    rule_content: str,
    position: str = "end"
):
    """
    Add a new rule section to the charter

    Args:
        section_title: Title of the new rule section
        rule_content: Content of the rule
        position: Where to add it (default: "end")
    """
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to edit the charter, ya muppet!", ephemeral=True)
        return

    if not charter_editor:
        await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
        return

    # Send initial response
    await interaction.response.defer()

    try:
        # Format the rule with AI if available
        formatted_content = await charter_editor.format_rule_with_ai(rule_content)

        # Add the rule
        result = await charter_editor.add_rule_section(
            section_title=section_title,
            section_content=formatted_content or rule_content,
            position=position
        )

        if result['success']:
            embed = discord.Embed(
                title="✅ Rule Added Successfully!",
                description=f"Right then! I've added the new rule to the charter, mate!\n\n**Section**: {section_title}\n**Position**: {position}",
                color=Colors.SUCCESS
            )
            embed.add_field(
                name="📝 Content",
                value=formatted_content[:1000] if formatted_content else rule_content[:1000],
                inline=False
            )
            embed.set_footer(text=f"Charter edited by {interaction.user.display_name} 🏈")
            await interaction.followup.send(embed=embed)
            logger.info(f"✅ Rule added by {interaction.user}: {section_title}")
        else:
            embed = discord.Embed(
                title="❌ Failed to Add Rule",
                description=f"Bloody hell! Couldn't add the rule:\n\n{result['message']}",
                color=Colors.ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"❌ Error adding rule: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Somethin' went wrong, mate:\n\n`{str(e)}`",
            color=Colors.ERROR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@charter_group.command(name="update", description="Update an existing rule in the charter (Admin only)")
@app_commands.describe(
    section_identifier="Section title or number to update",
    new_content="New content for the section"
)
async def charter_update(
    interaction: discord.Interaction,
    section_identifier: str,
    new_content: str
):
    """
    Update an existing rule section

    Args:
        section_identifier: Identifier for the section to update (e.g., "1.1", "Scheduling")
        new_content: New content for the section
    """
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to edit the charter!", ephemeral=True)
        return

    if not charter_editor:
        await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
        return

    # Send initial response
    await interaction.response.defer()

    try:
        # Format the content with AI if available
        formatted_content = await charter_editor.format_rule_with_ai(new_content)

        # Update the rule
        result = await charter_editor.update_rule_section(
            section_identifier=section_identifier,
            new_content=formatted_content or new_content
        )

        if result['success']:
            embed = discord.Embed(
                title="✅ Rule Updated Successfully!",
                description=f"Sorted! I've updated that section for ya, mate!\n\n**Section**: {section_identifier}",
                color=Colors.SUCCESS
            )
            embed.add_field(
                name="📝 New Content",
                value=(formatted_content or new_content)[:1000],
                inline=False
            )
            embed.set_footer(text=f"Charter updated by {interaction.user.display_name} 🏈")
            await interaction.followup.send(embed=embed)
            logger.info(f"✅ Rule updated by {interaction.user}: {section_identifier}")
        else:
            embed = discord.Embed(
                title="❌ Failed to Update Rule",
                description=f"Couldn't update the rule, mate:\n\n{result['message']}",
                color=Colors.ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"❌ Error updating rule: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Somethin' went wrong:\n\n`{str(e)}`",
            color=Colors.ERROR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@charter_group.command(name="backups", description="View available charter backups (Admin only)")
async def charter_backups(interaction: discord.Interaction):
    """View available charter backups"""
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to view backups!", ephemeral=True)
        return

    if not charter_editor:
        await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
        return

    try:
        backups = charter_editor.get_backup_list()

        if not backups:
            embed = discord.Embed(
                title="📋 Charter Backups",
                description="No backups found, mate! The charter hasn't been backed up yet.",
                color=0x808080
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 Charter Backups",
            description=f"Found **{len(backups)}** charter backup{'s' if len(backups) > 1 else ''}!",
            color=Colors.SUCCESS
        )

        # Show up to 10 most recent backups
        for backup in backups[:10]:
            timestamp = backup['modified'].strftime('%Y-%m-%d %I:%M %p')
            size_kb = backup['size'] / 1024

            embed.add_field(
                name=f"📄 {backup['filename']}",
                value=f"**Date**: {timestamp}\n**Size**: {size_kb:.1f} KB",
                inline=False
            )

        if len(backups) > 10:
            embed.add_field(
                name="ℹ️ Note",
                value=f"Showing 10 most recent backups. Total backups: {len(backups)}",
                inline=False
            )

        embed.set_footer(text="Use /restore_charter_backup to restore a backup")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"❌ Error viewing backups: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Couldn't get the backups list:\n\n`{str(e)}`",
            color=Colors.ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@charter_group.command(name="restore", description="Restore charter from a backup (Admin only)")
@app_commands.describe(backup_filename="Name of the backup file to restore")
async def charter_restore(interaction: discord.Interaction, backup_filename: str):
    """
    Restore the charter from a backup

    Args:
        backup_filename: Name of the backup file to restore
    """
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to restore backups!", ephemeral=True)
        return

    if not charter_editor:
        await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
        return

    # Send initial response
    await interaction.response.defer()

    try:
        success = charter_editor.restore_backup(backup_filename)

        if success:
            embed = discord.Embed(
                title="✅ Charter Restored!",
                description=f"Right then! Charter has been restored from backup:\n\n**Backup**: {backup_filename}\n\nThe current charter was backed up before restorin', so don't worry!",
                color=Colors.SUCCESS
            )
            embed.set_footer(text=f"Charter restored by {interaction.user.display_name} 🏈")
            await interaction.followup.send(embed=embed)
            logger.info(f"✅ Charter restored by {interaction.user} from {backup_filename}")
        else:
            embed = discord.Embed(
                title="❌ Restore Failed",
                description=f"Couldn't restore the charter from that backup, mate!\n\nMake sure the filename is correct.",
                color=Colors.ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"❌ Error restoring backup: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description=f"Somethin' went wrong:\n\n`{str(e)}`",
            color=Colors.ERROR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@admin_group.command(name="add", description="Add a user as bot admin (Admin only)")
@app_commands.describe(user="The Discord user to make a bot admin")
async def admin_add(interaction: discord.Interaction, user: discord.Member):
    """
    Add a user as bot admin

    Args:
        user: The Discord user to make a bot admin
    """
    if not admin_manager:
        await interaction.response.send_message("❌ Admin manager not available", ephemeral=True)
        return

    # Check if command user is admin (either Discord admin or bot admin)
    if not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to use this command, ya muppet!", ephemeral=True)
        return

    # Add the user as admin
    success = admin_manager.add_admin(user.id)

    if success:
        embed = discord.Embed(
            title="✅ Bot Admin Added!",
            description=f"Right then! **{user.display_name}** is now a bot admin!\n\nThey can now use all admin commands.",
            color=Colors.SUCCESS
        )
        embed.set_footer(text=f"Added by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"✅ Bot admin added: {user.display_name} ({user.id}) by {interaction.user.display_name}")
    else:
        embed = discord.Embed(
            title="ℹ️ Already an Admin",
            description=f"{user.display_name} is already a bot admin, mate!",
            color=Colors.WARNING
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(name="remove", description="Remove a user as bot admin (Admin only)")
@app_commands.describe(user="The Discord user to remove as bot admin")
async def admin_remove(interaction: discord.Interaction, user: discord.Member):
    """
    Remove a user as bot admin

    Args:
        user: The Discord user to remove as bot admin
    """
    if not admin_manager:
        await interaction.response.send_message("❌ Admin manager not available", ephemeral=True)
        return

    # Check if command user is admin
    if not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to use this command!", ephemeral=True)
        return

    # Remove the user as admin
    success = admin_manager.remove_admin(user.id)

    if success:
        embed = discord.Embed(
            title="✅ Bot Admin Removed",
            description=f"Right then! **{user.display_name}** is no longer a bot admin.",
            color=Colors.ERROR
        )
        embed.set_footer(text=f"Removed by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"✅ Bot admin removed: {user.display_name} ({user.id}) by {interaction.user.display_name}")
    else:
        embed = discord.Embed(
            title="ℹ️ Not an Admin",
            description=f"{user.display_name} isn't a bot admin, mate!",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(name="list", description="List all bot admins")
async def admin_list(interaction: discord.Interaction):
    """List all bot admins"""
    if not admin_manager:
        await interaction.response.send_message("❌ Admin manager not available", ephemeral=True)
        return

    admin_ids = admin_manager.get_admin_list()

    if not admin_ids:
        embed = discord.Embed(
            title="🔐 Bot Admins",
            description="No bot-specific admins configured.\n\nAnyone with Discord Administrator permission can use admin commands.\n\nUse `/add_bot_admin @user` to add bot admins!",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="🔐 Bot Admins",
        description=f"Found **{len(admin_ids)}** bot admin{'s' if len(admin_ids) > 1 else ''}:",
        color=Colors.SUCCESS
    )

    # Try to fetch user info for each admin
    admin_info = []
    for admin_id in admin_ids:
        try:
            user = await bot.fetch_user(admin_id)
            admin_info.append(f"• **{user.display_name}** (`{user.name}`) - ID: {admin_id}")
        except (discord.NotFound, discord.HTTPException):
            admin_info.append(f"• User ID: {admin_id} (user not found)")

    embed.add_field(
        name="📋 Admin List",
        value="\n".join(admin_info) if admin_info else "No admins",
        inline=False
    )

    embed.add_field(
        name="ℹ️ Note",
        value="Users with Discord Administrator permission also have bot admin access.",
        inline=False
    )

    embed.set_footer(text="CFB 26 League Bot - Admin Management")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(name="block", description="Block unprompted responses in a channel (Admin only)")
@app_commands.describe(channel="The channel to block")
async def admin_block(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Block unprompted responses in a channel (Harry can still be @mentioned)

    Args:
        channel: The channel to block
    """
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to block channels, ya muppet!", ephemeral=True)
        return

    if not channel_manager:
        await interaction.response.send_message("❌ Channel manager not available", ephemeral=True)
        return

    was_blocked = channel_manager.block_channel(channel.id)

    if was_blocked:
        embed = discord.Embed(
            title="🔇 Channel Blocked!",
            description=f"Right then! I won't make unprompted responses in {channel.mention} anymore.\n\n**But:** You can still @mention me there for questions!\n\nI'll just stay quiet unless you ask, yeah?",
            color=Colors.WARNING
        )
        embed.add_field(
            name="📋 How It Works",
            value="• **@mentions still work** - I'll respond when you ping me\n• **No unprompted replies** - I won't jump into conversations\n• **Slash commands work** - All `/` commands still function",
            inline=False
        )
        embed.set_footer(text=f"Blocked by {interaction.user.display_name} 🔇")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"🔇 {interaction.user} blocked channel #{channel.name} (ID: {channel.id})")
    else:
        embed = discord.Embed(
            title="ℹ️ Already Blocked",
            description=f"That channel is already blocked, mate!\n\n{channel.mention} is on the blocked list.",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(name="unblock", description="Allow unprompted responses in a channel (Admin only)")
@app_commands.describe(channel="The channel to unblock")
async def admin_unblock(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Allow unprompted responses in a channel

    Args:
        channel: The channel to unblock
    """
    # Check if user is admin
    if not admin_manager or not admin_manager.is_admin(interaction.user, interaction):
        await interaction.response.send_message("❌ You need to be a bot admin to unblock channels, ya muppet!", ephemeral=True)
        return

    if not channel_manager:
        await interaction.response.send_message("❌ Channel manager not available", ephemeral=True)
        return

    was_unblocked = channel_manager.unblock_channel(channel.id)

    if was_unblocked:
        embed = discord.Embed(
            title="🔊 Channel Unblocked!",
            description=f"Brilliant! I can make unprompted responses in {channel.mention} again!\n\nI'll jump in when I see league questions and interesting conversations!",
            color=Colors.SUCCESS
        )
        embed.set_footer(text=f"Unblocked by {interaction.user.display_name} 🔊")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"🔊 {interaction.user} unblocked channel #{channel.name} (ID: {channel.id})")
    else:
        embed = discord.Embed(
            title="ℹ️ Not Blocked",
            description=f"That channel wasn't blocked, mate!\n\n{channel.mention} already allows unprompted responses.",
            color=0x808080
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@admin_group.command(name="blocked", description="Show all blocked channels")
async def admin_blocked(interaction: discord.Interaction):
    """Show all channels where unprompted responses are blocked"""
    if not channel_manager:
        await interaction.response.send_message("❌ Channel manager not available", ephemeral=True)
        return

    blocked_ids = channel_manager.get_blocked_channels()

    if not blocked_ids:
        embed = discord.Embed(
            title="🔊 No Blocked Channels",
            description="No channels are blocked!\n\nI can make unprompted responses in all channels.\n\nUse `/block_channel #channel` to block channels (Admin only).",
            color=Colors.SUCCESS
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    embed = discord.Embed(
        title="🔇 Blocked Channels",
        description=f"Found **{len(blocked_ids)}** blocked channel{'s' if len(blocked_ids) > 1 else ''}:\n\n**Note:** I can still be @mentioned in these channels!",
        color=Colors.WARNING
    )

    # Try to fetch channel info for each blocked channel
    channel_info = []
    for channel_id in blocked_ids:
        try:
            channel = bot.get_channel(channel_id)
            if channel:
                channel_info.append(f"• {channel.mention} (`#{channel.name}`) - ID: {channel_id}")
            else:
                channel_info.append(f"• Channel ID: {channel_id} (channel not found)")
        except (discord.NotFound, discord.HTTPException):
            channel_info.append(f"• Channel ID: {channel_id} (error fetching info)")

    embed.add_field(
        name="📋 Blocked Channels List",
        value="\n".join(channel_info) if channel_info else "No channels",
        inline=False
    )

    embed.add_field(
        name="ℹ️ How It Works",
        value="• **@mentions still work** - I respond when you ping me\n• **No unprompted replies** - I won't jump into conversations\n• **Admins can manage** - Use `/block_channel` or `/unblock_channel`",
        inline=False
    )

    embed.set_footer(text="CFB 26 League Bot - Channel Management")
    await interaction.response.send_message(embed=embed, ephemeral=True)


@admin_group.command(name="config", description="Configure Harry's features for this server")
@app_commands.describe(
    action="What to do: view, enable, or disable",
    module="Which module to toggle"
)
@app_commands.choices(action=[
    app_commands.Choice(name="view", value="view"),
    app_commands.Choice(name="enable", value="enable"),
    app_commands.Choice(name="disable", value="disable"),
])
@app_commands.choices(module=[
    app_commands.Choice(name="ai_chat - /harry, /ask, @mentions, auto-responses", value="ai_chat"),
    app_commands.Choice(name="cfb_data - Player lookup, rankings, matchups, etc.", value="cfb_data"),
    app_commands.Choice(name="league - Timer, charter, rules, dynasty features", value="league"),
    app_commands.Choice(name="hs_stats - High school stats from MaxPreps (scraping)", value="hs_stats"),
    app_commands.Choice(name="recruiting - On3/Rivals or 247Sports rankings", value="recruiting"),
    app_commands.Choice(name="schedule_announcement - Week matchups when timer starts", value="schedule_announcement"),
])
async def config_command(
    interaction: discord.Interaction,
    action: str = "view",
    module: str = None
):
    """
    Configure which features Harry has enabled on this server.

    Modules:
    - core: Always enabled - /help, /admin, /version (can't disable)
    - ai_chat: Harry's AI - /harry, /ask, /summarize, @mentions
    - cfb_data: Player lookup, rankings, matchups, schedules, draft, transfers
    - league: Timer, advance, charter, rules, league staff, dynasty features
    - hs_stats: High school stats from MaxPreps
    - recruiting: On3/Rivals or 247Sports rankings
    """
    if not interaction.guild:
        await interaction.response.send_message("❌ This command only works in servers, not DMs!", ephemeral=True)
        return

    guild_id = interaction.guild.id

    # Check admin for enable/disable
    if action in ["enable", "disable"]:
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (admin_manager and admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message(
                "❌ Only server admins can change feature settings, ya muppet!",
                ephemeral=True
            )
            return

    # Defer for view action to avoid timeout
    if action == "view":
        await interaction.response.defer(ephemeral=True)

    if action == "view":
        # Show current configuration
        enabled = server_config.get_enabled_modules(guild_id)

        embed = discord.Embed(
            title="⚙️ Harry's Configuration",
            description=f"Feature settings for **{interaction.guild.name}**",
            color=Colors.PRIMARY
        )

        for mod in FeatureModule:
            is_enabled = mod.value in enabled
            status = "✅ Enabled" if is_enabled else "❌ Disabled"
            if mod == FeatureModule.CORE:
                status = "✅ Always On"

            desc = server_config.get_module_description(mod)
            commands = server_config.get_module_commands(mod)
            # Commands now include / prefix already (e.g., "/cfb player")
            cmd_list = ", ".join([f"`{c}`" for c in commands[:5]])
            if len(commands) > 5:
                cmd_list += f" +{len(commands) - 5} more"

            embed.add_field(
                name=f"{desc}",
                value=f"**Status:** {status}\n**Commands:** {cmd_list}",
                inline=False
            )

        # Show admin channel
        admin_channel_id = server_config.get_admin_channel(guild_id)
        if admin_channel_id:
            admin_ch = interaction.guild.get_channel(admin_channel_id)
            admin_channel_text = f"#{admin_ch.name}" if admin_ch else f"ID: {admin_channel_id}"
        else:
            admin_channel_text = "❌ Not Set"

        # Show channel/auto-response status
        enabled_channels = server_config.get_enabled_channels(guild_id)
        current_channel_enabled = server_config.is_channel_enabled(guild_id, interaction.channel.id)
        auto_responses = server_config.auto_responses_enabled(guild_id, interaction.channel.id)

        channel_status = f"**Admin Channel:** {admin_channel_text}"
        channel_status += f"\n**This Channel:** {'✅ Enabled' if current_channel_enabled else '❌ Disabled'}"
        if enabled_channels:
            channel_status += f"\n**Enabled Channels:** {len(enabled_channels)} channel(s)"
        else:
            channel_status += "\n**Enabled Channels:** None (Harry disabled everywhere)"

        # Show rivalry responses status - but note if AI_CHAT is off, they won't work
        ai_chat_enabled = FeatureModule.AI_CHAT.value in enabled
        if not ai_chat_enabled:
            channel_status += "\n**Rivalry Responses:** 💤 Off (AI Chat disabled)"
        elif auto_responses:
            channel_status += "\n**Rivalry Responses:** ✅ On"
        else:
            channel_status += "\n**Rivalry Responses:** ❌ Off"

        embed.add_field(
            name="📺 Channel Settings",
            value=channel_status,
            inline=False
        )

        # Show League-specific settings only if League module is enabled
        league_enabled = FeatureModule.LEAGUE.value in enabled
        if league_enabled:
            timer_channel_id = server_config.get_timer_channel(guild_id)
            if timer_channel_id:
                timer_ch = interaction.guild.get_channel(timer_channel_id)
                timer_text = f"#{timer_ch.name}" if timer_ch else f"ID: {timer_channel_id}"
            else:
                timer_text = "#general (default)"

            sched_ann = server_config.get_setting(guild_id, "schedule_announcement", True)
            league_status = f"**Timer Channel:** {timer_text}\n**Schedule announcement:** {'✅ On' if sched_ann else '❌ Off'} (Week matchups when timer starts)"

            # Get league staff if timekeeper is available
            if timekeeper_manager:
                staff = timekeeper_manager.get_league_staff()
                owner_name = staff.get('owner_name', 'Not Set')
                co_commish_name = staff.get('co_commish_name', 'Not Set')
                league_status += f"\n**League Owner:** {owner_name}"
                league_status += f"\n**Co-Commissioner:** {co_commish_name}"

            embed.add_field(
                name="🏆 League Settings",
                value=league_status,
                inline=False
            )

        embed.add_field(
            name="💡 How to Change",
            value=(
                "`/admin config enable cfb_data` - Enable CFB data\n"
                "`/admin config disable league` - Disable league features\n"
                "`/admin set_channel #channel` - Set admin channel\n"
                "`/admin channels enable` - Enable Harry in a channel\n"
                "`/admin channels toggle_rivalry` - Toggle Fuck Oregon! 🦆"
            ),
            inline=False
        )

        embed.set_footer(text=Footers.CONFIG)
        await interaction.followup.send(embed=embed, ephemeral=True)

    elif action == "enable":
        if not module:
            await interaction.response.send_message("❌ Please specify a module to enable!", ephemeral=True)
            return

        if module == "schedule_announcement":
            server_config.set_setting(guild_id, "schedule_announcement", True)
            await server_config.save_to_discord()
            embed = discord.Embed(
                title="✅ Schedule Announcement On",
                description="Week matchups (bye week + games) will be sent when the timer starts or advances.",
                color=Colors.SUCCESS
            )
            embed.set_footer(text=Footers.CONFIG)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            mod = FeatureModule(module)
        except ValueError:
            await interaction.response.send_message(f"❌ Unknown module: {module}", ephemeral=True)
            return

        if mod == FeatureModule.CORE:
            await interaction.response.send_message("Core features are always enabled, mate! Can't turn off my personality! 😎", ephemeral=True)
            return

        server_config.enable_module(guild_id, mod)
        await server_config.save_to_discord()

        commands = server_config.get_module_commands(mod)
        cmd_list = ", ".join([f"`/{c}`" for c in commands[:8]])

        embed = discord.Embed(
            title="✅ Module Enabled!",
            description=f"**{mod.value.upper()}** features are now enabled for this server!",
            color=Colors.SUCCESS
        )
        embed.add_field(
            name="Available Commands",
            value=cmd_list + (f"\n+{len(commands) - 8} more" if len(commands) > 8 else ""),
            inline=False
        )
        embed.set_footer(text=Footers.CONFIG)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log to admin channel
        await send_admin_log(
            "Module Enabled",
            f"**{mod.value.upper()}** enabled by {interaction.user.display_name}",
            guild_id=guild_id
        )

    elif action == "disable":
        if not module:
            await interaction.response.send_message("❌ Please specify a module to disable!", ephemeral=True)
            return

        if module == "schedule_announcement":
            server_config.set_setting(guild_id, "schedule_announcement", False)
            await server_config.save_to_discord()
            embed = discord.Embed(
                title="❌ Schedule Announcement Off",
                description="Week matchups will no longer be sent when the timer starts or advances.",
                color=Colors.WARNING
            )
            embed.set_footer(text=Footers.CONFIG)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            mod = FeatureModule(module)
        except ValueError:
            await interaction.response.send_message(f"❌ Unknown module: {module}", ephemeral=True)
            return

        if mod == FeatureModule.CORE:
            await interaction.response.send_message("Nice try, but you can't turn off my personality! I'm always here, mate! 😏", ephemeral=True)
            return

        server_config.disable_module(guild_id, mod)
        await server_config.save_to_discord()

        embed = discord.Embed(
            title="❌ Module Disabled",
            description=f"**{mod.value.upper()}** features are now disabled for this server.",
            color=Colors.WARNING
        )
        embed.add_field(
            name="Re-enable Anytime",
            value=f"`/config enable {mod.value}` to turn it back on",
            inline=False
        )
        embed.set_footer(text=Footers.CONFIG)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Log to admin channel
        await send_admin_log(
            "Module Disabled",
            f"**{mod.value.upper()}** disabled by {interaction.user.display_name}",
            guild_id=guild_id
        )


@recruiting_group.command(name="source", description="Set the recruiting data source (On3/Rivals or 247Sports)")
@app_commands.describe(
    source="Which recruiting data source to use"
)
@app_commands.choices(source=[
    app_commands.Choice(name="On3/Rivals (default) - Server-side rendered, reliable", value="on3"),
    app_commands.Choice(name="247Sports Composite - Legacy, more data but slower", value="247"),
])
async def recruiting_source(
    interaction: discord.Interaction,
    source: str = None
):
    """
    Set or view the recruiting data source for this server.

    On3/Rivals (default): Server-side rendered, fast and reliable
    247Sports: Legacy source with more detailed data but slower scraping
    """
    # Check channel + module enabled
    if not await check_module_enabled(interaction, FeatureModule.RECRUITING):
        return

    if not interaction.guild:
        await interaction.response.send_message("❌ This command only works in servers!", ephemeral=True)
        return

    guild_id = interaction.guild.id

    # View current source if no argument
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
            value="`/recruit_source on3` or `/recruit_source 247`",
            inline=False
        )
        embed.set_footer(text=Footers.CONFIG)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Check admin for changing
    is_admin = (
        interaction.user.guild_permissions.administrator or
        (admin_manager and admin_manager.is_admin(interaction.user, interaction))
    )
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
        value=f"Commands like `/recruit`, `/top_recruits`, etc. will now pull data from {source_name}.",
        inline=False
    )
    embed.set_footer(text=Footers.CONFIG)
    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log to admin channel
    await send_admin_log(
        "Recruiting Source Changed",
        f"Recruiting source set to **{source_name}** by {interaction.user.display_name}",
        guild_id=guild_id
    )


@admin_group.command(name="sync", description="Force sync slash commands to this server (Admin only)")
async def admin_sync(interaction: discord.Interaction):
    """Force sync slash commands to update dropdowns and choices"""
    # Check admin
    is_admin = (
        interaction.user.guild_permissions.administrator or
        (admin_manager and admin_manager.is_admin(interaction.user, interaction))
    )
    if not is_admin:
        await interaction.response.send_message(
            "❌ Only server admins can sync commands!",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        # Sync to this guild specifically (instant)
        guild = interaction.guild
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)

        await interaction.followup.send(
            f"✅ Synced **{len(synced)}** commands to this server!\n"
            f"Slash command dropdowns should now be updated.",
            ephemeral=True
        )
        logger.info(f"🔄 Manual sync by {interaction.user}: {len(synced)} commands synced to {guild.name}")
    except Exception as e:
        await interaction.followup.send(
            f"❌ Failed to sync: {str(e)}",
            ephemeral=True
        )
        logger.error(f"❌ Manual sync failed: {e}")


@admin_group.command(name="channels", description="View/manage which channels Harry can respond in (no args = view status)")
@app_commands.describe(
    action="What to do (leave empty to view current status)",
    channel="Which channel to configure (defaults to current channel)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="enable - Allow Harry in this channel", value="enable"),
    app_commands.Choice(name="disable - Remove Harry from this channel", value="disable"),
    app_commands.Choice(name="disable_all - Remove Harry from ALL channels", value="disable_all"),
    app_commands.Choice(name="toggle_rivalry - Toggle rivalry responses (Fuck Oregon!, etc.)", value="toggle_rivalry"),
])
async def channel_command(
    interaction: discord.Interaction,
    action: str = None,
    channel: discord.TextChannel = None
):
    """
    Manage which channels Harry can respond in.

    By default, Harry is DISABLED everywhere. You must explicitly enable
    channels for him to respond in using /channel enable.
    """
    if not interaction.guild:
        await interaction.response.send_message("❌ This command only works in servers!", ephemeral=True)
        return

    guild_id = interaction.guild.id
    target_channel = channel or interaction.channel

    # Check admin for enable/disable
    if action in ["enable", "disable", "disable_all", "toggle_rivalry"]:
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (admin_manager and admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message(
                "❌ Only server admins can change channel settings, ya muppet!",
                ephemeral=True
            )
            return

    if action is None or action == "view":
        # Defer immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)

        enabled_channels = server_config.get_enabled_channels(guild_id)
        auto_responses = server_config.auto_responses_enabled(guild_id, target_channel.id)
        channel_enabled = server_config.is_channel_enabled(guild_id, target_channel.id)

        embed = discord.Embed(
            title="📺 Channel Settings",
            description=f"Harry's channel configuration for **{interaction.guild.name}**",
            color=Colors.PRIMARY
        )

        # Current channel status
        current_status = "✅ Enabled" if channel_enabled else "❌ Disabled"

        # Auto-responses only work if AI_CHAT is enabled
        ai_chat_on = server_config.is_module_enabled(guild_id, FeatureModule.AI_CHAT)
        if not ai_chat_on:
            auto_status = "💤 Off (AI Chat disabled)"
        elif auto_responses:
            auto_status = "✅ On"
        else:
            auto_status = "❌ Off"

        embed.add_field(
            name=f"#{target_channel.name}",
            value=f"**Status:** {current_status}\n**Auto-Responses:** {auto_status}",
            inline=False
        )

        # Show enabled channels
        if enabled_channels:
            channel_mentions = []
            for ch_id in enabled_channels[:10]:
                ch = interaction.guild.get_channel(ch_id)
                if ch:
                    channel_mentions.append(f"#{ch.name}")
            channels_text = ", ".join(channel_mentions)
            if len(enabled_channels) > 10:
                channels_text += f" +{len(enabled_channels) - 10} more"
            embed.add_field(
                name="📋 Enabled Channels",
                value=f"Harry responds in:\n{channels_text}",
                inline=False
            )
        else:
            embed.add_field(
                name="🔇 No Channels Enabled",
                value="Harry is **disabled everywhere**.\nUse `/admin channels enable` to enable him in specific channels.",
                inline=False
            )

        # Show available commands based on enabled modules
        enabled_modules = server_config.get_enabled_modules(guild_id)

        # Build command list by module - show enabled and disabled
        enabled_list = []
        disabled_list = []

        # AI Chat
        if "ai_chat" in enabled_modules:
            enabled_list.append("💬 **AI Chat:** `/harry`, `/ask`, `/summarize`, @mentions")
        else:
            disabled_list.append("💬 AI Chat")

        # Recruiting
        if "recruiting" in enabled_modules:
            enabled_list.append("⭐ **Recruiting:** `/recruiting player`, `top`, `class`, `commits`")
        else:
            disabled_list.append("⭐ Recruiting")

        # CFB Data
        if "cfb_data" in enabled_modules:
            enabled_list.append("🏈 **CFB Data:** `/cfb player`, `rankings`, `schedule`, `matchup`")
        else:
            disabled_list.append("🏈 CFB Data")

        # HS Stats
        if "hs_stats" in enabled_modules:
            enabled_list.append("🏫 **HS Stats:** `/hs stats`, `/hs bulk`")
        else:
            disabled_list.append("🏫 HS Stats")

        # League
        if "league" in enabled_modules:
            enabled_list.append("🏆 **League:** `/league week`, `timer`, `staff` + `/charter`")
        else:
            disabled_list.append("🏆 League")

        # Always available
        enabled_list.append("🤖 **Always On:** `/help`, `/admin`, `/version`")

        # Show enabled commands
        if channel_enabled:
            embed.add_field(
                name="✅ Available Commands",
                value="\n".join(enabled_list) if enabled_list else "None",
                inline=False
            )
        else:
            embed.add_field(
                name="⚡ Commands (if channel enabled)",
                value="\n".join(enabled_list) + "\n\n*Enable this channel first!*",
                inline=False
            )

        # Show disabled modules
        if disabled_list:
            embed.add_field(
                name="❌ Disabled Modules",
                value=", ".join(disabled_list) + "\n`/admin config enable <module>`",
                inline=False
            )

        # Explain auto-responses - only relevant if AI_CHAT is on
        if "ai_chat" in enabled_modules:
            embed.add_field(
                name="💡 Auto-Responses",
                value="Fun replies like **'Fuck Oregon! 🦆'** when keywords mentioned.\nPer-channel toggle: `/admin channels toggle_rivalry`",
                inline=False
            )
        else:
            embed.add_field(
                name="💤 Auto-Responses",
                value="Disabled (requires **AI Chat** module)\nEnable with `/admin config enable ai_chat`",
                inline=False
            )

        embed.add_field(
            name="💡 Admin Commands",
            value=(
                "`/admin channels enable` - Enable in channel\n"
                "`/admin channels disable` - Disable in channel\n"
                "`/admin config enable/disable` - Toggle modules"
            ),
            inline=False
        )

        embed.set_footer(text="Harry's Channel Config 🏈 | Channels = WHERE, Modules = WHAT")
        await interaction.followup.send(embed=embed, ephemeral=True)

    elif action == "enable":
        server_config.enable_channel(guild_id, target_channel.id)
        await server_config.save_to_discord()

        enabled_channels = server_config.get_enabled_channels(guild_id)

        embed = discord.Embed(
            title="✅ Channel Enabled",
            description=f"Harry can now respond in **#{target_channel.name}**!",
            color=Colors.SUCCESS
        )

        embed.add_field(
            name="📋 Enabled Channels",
            value=f"Harry is now active in **{len(enabled_channels)}** channel(s).",
            inline=False
        )

        embed.set_footer(text="Harry's Channel Config 🏈")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif action == "disable":
        server_config.disable_channel(guild_id, target_channel.id)
        await server_config.save_to_discord()

        enabled_channels = server_config.get_enabled_channels(guild_id)

        embed = discord.Embed(
            title="❌ Channel Disabled",
            description=f"Harry will no longer respond in **#{target_channel.name}**.",
            color=Colors.WARNING
        )

        if enabled_channels:
            embed.add_field(
                name="📋 Remaining Channels",
                value=f"Harry is still active in **{len(enabled_channels)}** channel(s).",
                inline=False
            )
        else:
            embed.add_field(
                name="🔇 Harry Disabled",
                value="No channels enabled - Harry is now disabled everywhere.",
                inline=False
            )

        embed.set_footer(text="Harry's Channel Config 🏈")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif action == "disable_all":
        # Clear the enabled channels list (disables Harry everywhere)
        config = server_config.get_config(guild_id)
        config["enabled_channels"] = []
        await server_config.save_to_discord()

        embed = discord.Embed(
            title="🔇 Harry Disabled Everywhere",
            description="Harry is now **disabled in all channels**.",
            color=Colors.WARNING
        )
        embed.add_field(
            name="💡 To Enable Again",
            value="Use `/channel enable` in the channels where you want Harry to respond.",
            inline=False
        )
        embed.set_footer(text="Harry's Channel Config 🏈")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif action == "toggle_rivalry":
        current = server_config.auto_responses_enabled(guild_id, target_channel.id)
        new_value = not current
        server_config.set_channel_override(guild_id, target_channel.id, "auto_responses", new_value)
        await server_config.save_to_discord()

        status = "✅ Enabled" if new_value else "❌ Disabled"
        embed = discord.Embed(
            title="💬 Auto-Responses Toggled",
            description=f"Auto-responses in **#{target_channel.name}**: {status}",
            color=Colors.SUCCESS if new_value else 0xff6600
        )

        if new_value:
            embed.add_field(
                name="What This Means",
                value="Harry will jump in with team banter (like 'Fuck Oregon!') when keywords are mentioned.",
                inline=False
            )
        else:
            embed.add_field(
                name="What This Means",
                value="Harry won't auto-respond to keywords. He'll only respond when @mentioned or asked directly.",
                inline=False
            )

        embed.set_footer(text="Harry's Channel Config 🏈")
        await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="whats_new", description="See what's new with Harry!")
async def whats_new(interaction: discord.Interaction):
    """Show the latest features and updates"""
    embed = discord.Embed(
        title="🎉 What's New with Harry! 🎉",
        description="Oi! Look at all the brilliant new stuff I can do now, mate!",
        color=Colors.SUCCESS
    )

    # Feature 1: Advance Timer
    embed.add_field(
        name="⏰ **Advance Timer with Custom Duration**",
        value=(
            "I can now manage advance countdowns with **custom durations**!\n"
            "• `/league timer` - Default 48 hour countdown\n"
            "• `/league timer 24` - 24 hour countdown\n"
            "• `/league timer 72` - 3 day countdown\n"
            "• Automatic reminders at 24h, 12h, 6h, 1h\n"
            "• \"TIME'S UP! LET'S ADVANCE!\" when done\n"
            "• `/league timer_status` - Check progress with fancy progress bar!"
        ),
        inline=False
    )

    # Feature 2: Channel Summarization
    embed.add_field(
        name="📊 **Channel Summarization** (NEW!)",
        value=(
            "I can read through channel messages and give you AI-powered summaries!\n"
            "• `/summarize` - Last 24 hours\n"
            "• `/summarize 48` - Last 48 hours\n"
            "• `/summarize 24 recruiting` - Focused summary\n"
            "• Shows main topics, decisions, key participants, and notable moments\n"
            "• Perfect for catching up on what you missed!"
        ),
        inline=False
    )

    # Feature 3: Charter Management
    embed.add_field(
        name="📝 **Charter Management** (NEW! - Admin Only)",
        value=(
            "I can edit the league charter directly from Discord!\n"
            "• `/add_rule` - Add new rules to charter\n"
            "• `/update_rule` - Update existing rules\n"
            "• `/view_charter_backups` - See all backups\n"
            "• `/restore_charter_backup` - Restore from backup\n"
            "• Automatic backups before every change\n"
            "• AI-assisted rule formatting!"
        ),
        inline=False
    )

    # Feature 4: Bot Admin System
    embed.add_field(
        name="🔐 **Bot Admin System** (NEW!)",
        value=(
            "Manage bot admins directly through Discord!\n"
            "• `/add_bot_admin @user` - Make someone a bot admin\n"
            "• `/remove_bot_admin @user` - Remove bot admin\n"
            "• `/list_bot_admins` - See all bot admins\n"
            "• Bot admins can use all admin commands\n"
            "• Discord Administrators also have bot admin access"
        ),
        inline=False
    )

    # Other improvements
    embed.add_field(
        name="✨ **Other Improvements**",
        value=(
            "• Better error handling\n"
            "• Improved logging\n"
            "• More sarcastic responses (you're welcome!)\n"
            "• All features maintain my cockney personality!"
        ),
        inline=False
    )

    embed.add_field(
        name="📖 **Learn More**",
        value="Use `/help_cfb` to see all available commands!",
        inline=False
    )

    # Add version info
    if version_manager:
        current_ver = version_manager.get_current_version()
        embed.set_footer(text=f"Harry v{current_ver} - Your CFB 26 League Assistant 🏈 | Updated November 2025")
    else:
        embed.set_footer(text="Harry - Your CFB 26 League Assistant 🏈 | Updated November 2025")

    embed.set_thumbnail(url="https://i.imgur.com/3xzKq7L.png")  # Football emoji as thumbnail

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="version", description="Show current bot version")
async def show_version(interaction: discord.Interaction):
    """Show the current version"""
    if not version_manager:
        await interaction.response.send_message("❌ Version manager not available", ephemeral=True)
        return

    current_ver = version_manager.get_current_version()
    version_info = version_manager.get_latest_version_info()

    embed = discord.Embed(
        title=f"🏈 Harry v{current_ver}",
        description=f"{version_info.get('emoji', '🎉')} {version_info.get('title', 'Current Version')}",
        color=Colors.SUCCESS
    )

    embed.add_field(
        name="📅 Release Date",
        value=version_info.get('date', 'Unknown'),
        inline=True
    )

    embed.add_field(
        name="📊 Total Versions",
        value=str(len(version_manager.get_all_versions())),
        inline=True
    )

    embed.add_field(
        name="📖 View Details",
        value="Use `/changelog` to see all changes!",
        inline=False
    )

    guild_id = interaction.guild.id if interaction.guild else 0
    embed.set_footer(text=get_footer_for_guild(guild_id))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="changelog", description="View version changelog")
async def view_changelog(interaction: discord.Interaction, version: str = None):
    """
    View the changelog for a specific version or all versions

    Args:
        version: Specific version to view (e.g., "1.1.0") or leave blank for summary
    """
    if not version_manager:
        await interaction.response.send_message("❌ Version manager not available", ephemeral=True)
        return

    # If no version specified, show summary of all versions
    if not version:
        embed = discord.Embed(
            title="📜 Harry's Version History",
            description="Here's all the brilliant updates I've had, mate!",
            color=Colors.SUCCESS
        )

        summary = version_manager.get_version_summary()
        # Discord embed fields have a 1024 character limit
        if len(summary) > 1000:
            summary = summary[:997] + "..."
        embed.add_field(
            name="📋 All Versions",
            value=summary,
            inline=False
        )

        embed.add_field(
            name="🔍 View Specific Version",
            value="Use `/changelog 1.1.0` to see details for a specific version!",
            inline=False
        )

        current_ver = version_manager.get_current_version()
        embed.set_footer(text=f"Current Version: v{current_ver}")

        await interaction.response.send_message(embed=embed)
        return

    # Show specific version details
    embed_data = version_manager.format_version_embed_data(version)

    if not embed_data:
        embed = discord.Embed(
            title="❌ Version Not Found",
            description=f"Sorry mate, I don't have any info about version {version}!\n\nUse `/changelog` to see all available versions.",
            color=Colors.ERROR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Create embed with version details
    embed = discord.Embed(
        title=embed_data['title'],
        description=embed_data['description'],
        color=Colors.SUCCESS
    )

    for field in embed_data['fields']:
        embed.add_field(
            name=field['name'],
            value=field['value'],
            inline=field['inline']
        )

    current_ver = version_manager.get_current_version()
    is_current = version == current_ver
    footer_text = f"Version v{version}" + (" (Current)" if is_current else "")
    embed.set_footer(text=footer_text)

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Missing required argument. Use `/help` for command usage.")
    else:
        print(f"Error: {error}")


# =============================================================================
# ADD COMMAND GROUPS TO BOT TREE
# =============================================================================
bot.tree.add_command(recruiting_group)
bot.tree.add_command(hs_group)
bot.tree.add_command(cfb_group)
bot.tree.add_command(charter_group)
bot.tree.add_command(league_group)  # Includes season & timer commands
bot.tree.add_command(admin_group)


def main():
    """Main function to run the bot"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("❌ DISCORD_BOT_TOKEN not found in environment variables")
        logger.error("📝 Please create a .env file with your bot token")
        exit(1)

    logger.info("🚀 Starting CFB Rules Bot...")
    logger.info(f"📊 Environment: {'Production' if os.getenv('RENDER') else 'Development'}")
    logger.info(f"🤖 AI Available: {AI_AVAILABLE}")
    logger.info(f"📄 Google Docs Available: {GOOGLE_DOCS_AVAILABLE}")

    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"❌ Bot failed to start: {e}")
        raise

if __name__ == "__main__":
    main()
