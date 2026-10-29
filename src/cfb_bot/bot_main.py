#!/usr/bin/env python3
"""
CFB League Bot - Cog-Based Architecture

Entry point: loads the cogs, wires their dependencies, and handles on_message
(the @everyone advance, the season history thread, team banter).

Cogs loaded:
- CoreCog: /help, /version, /changelog, /whats_new, /tokens
- AIChatCog: /harry, /ask, /summarize
- RecruitingCog: /recruiting group
- CFBDataCog: /cfb group
- HSStatsCog: /hs group
- LeagueCog: /league group
- CharterCog: /charter group
- AdminCog: /admin group
- FunCog: /fun group
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

import discord
from discord.ext import commands, tasks

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('CFBBot')

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None  # We use /help from CoreCog
)

# Import utilities after bot setup to avoid circular imports
from .utils import instance_lock
from .utils.server_config import server_config
from .config import Colors

# ==================== COG LOADING ====================

COG_EXTENSIONS = [
    'cfb_bot.cogs.core',
    'cfb_bot.cogs.ai_chat',
    'cfb_bot.cogs.recruiting',
    'cfb_bot.cogs.cfb_data',
    'cfb_bot.cogs.hs_stats',
    'cfb_bot.cogs.league',
    'cfb_bot.cogs.charter',
    'cfb_bot.cogs.admin',
    'cfb_bot.cogs.fun',
]


async def load_cogs():
    """Load all cog extensions"""
    for extension in COG_EXTENSIONS:
        try:
            await bot.load_extension(extension)
            logger.info(f"Loaded cog: {extension}")
        except Exception as e:
            logger.error(f"Failed to load cog {extension}: {e}", exc_info=True)


# Global references for dependencies (set in on_ready)
timekeeper_manager = None
charter_editor = None
# on_ready fires again after Discord reconnects; one-time startup must not re-run
_startup_complete = False
version_manager = None
schedule_manager = None
_background_tasks = set()
# guild id -> commands synced at startup, for the dev-channel status embed
_sync_results = {}


async def setup_dependencies():
    """
    Set up dependencies for cogs that need them.
    This is called after bot is ready so we can access Discord objects.
    """
    global timekeeper_manager, charter_editor, version_manager, schedule_manager

    logger.info("Setting up cog dependencies...")

    # Import optional dependencies
    ai_assistant = None
    AI_AVAILABLE = False
    channel_summarizer = None
    admin_manager = None
    channel_manager = None
    schedule_manager = None

    try:
        from .ai import AI_AVAILABLE as _ai_avail
        from .ai import ai_assistant as _ai
        ai_assistant = _ai
        AI_AVAILABLE = _ai_avail
        if AI_AVAILABLE:
            logger.info("AI assistant available")
        else:
            logger.info("AI assistant not configured")
    except ImportError as e:
        logger.warning(f"AI assistant not available: {e}")

    try:
        from .utils.error_reporter import get_error_reporter
        get_error_reporter(bot)
        logger.info("Error reporting to bot owner DM enabled")
    except ImportError:
        logger.warning("Error reporter not available")

    try:
        from .utils.charter_editor import CharterEditor
        charter_editor = CharterEditor(ai_assistant if AI_AVAILABLE else None, bot=bot)
        # Restore the Discord-persisted charter into the local file (survives redeploys)
        await charter_editor.restore_from_discord()
        logger.info("Charter editor initialized and loaded from Discord")
    except ImportError:
        logger.warning("Charter editor not available")

    try:
        from .utils.summarizer import ChannelSummarizer
        channel_summarizer = ChannelSummarizer(ai_assistant if AI_AVAILABLE else None)
        logger.info("Channel summarizer initialized")
    except ImportError as e:
        logger.warning("Channel summarizer not available: %s", e)

    try:
        from .utils.admin_check import AdminManager
        admin_manager = AdminManager()
        logger.info(f"Admin manager initialized ({admin_manager.get_admin_count()} admins)")
    except ImportError as e:
        logger.warning(f"Admin manager not available: {e}")

    try:
        from .utils.channel_manager import ChannelManager
        channel_manager = ChannelManager()
        logger.info("Channel manager initialized")
    except ImportError:
        logger.warning("Channel manager not available")

    try:
        from .utils.timekeeper import TimekeeperManager
        timekeeper_manager = TimekeeperManager(bot)
        logger.info("Timekeeper manager initialized")
        # Restore the timer, week, staff and settings from the owner DM
        try:
            await timekeeper_manager.load_saved_state()
            logger.info("Timer state loaded from Discord")
        except Exception as e:
            logger.error(f"Failed to load timer state: {e}")
    except ImportError:
        logger.warning("Timekeeper not available")

    try:
        # The shared instance: the AI and charter read get_schedule_manager() too, so an
        # uploaded schedule has to land in the same object the cogs update.
        from .utils.schedule_manager import get_schedule_manager
        schedule_manager = get_schedule_manager()
        schedule_manager.set_bot(bot)
        # Restore any schedule uploaded via Discord (survives redeploys)
        try:
            await schedule_manager.load_from_discord()
        except Exception as e:
            logger.error(f"Failed to restore schedule from Discord: {e}")
        logger.info(f"Schedule manager initialized ({len(schedule_manager.teams)} teams)")
    except ImportError:
        logger.warning("Schedule manager not available")

    try:
        from .utils.version_manager import VersionManager
        version_manager = VersionManager()
        logger.info("Version manager initialized")
    except ImportError:
        logger.warning("Version manager not available")

    # Set dependencies on cogs
    for cog_name, cog in bot.cogs.items():
        if hasattr(cog, 'set_dependencies'):
            if cog_name == 'CoreCog':
                cog.set_dependencies(ai_assistant=ai_assistant, AI_AVAILABLE=AI_AVAILABLE)
            elif cog_name == 'AIChatCog':
                cog.set_dependencies(ai_assistant=ai_assistant, channel_summarizer=channel_summarizer, AI_AVAILABLE=AI_AVAILABLE)
            elif cog_name == 'CharterCog':
                cog.set_dependencies(charter_editor=charter_editor, channel_summarizer=channel_summarizer, ai_assistant=ai_assistant, admin_manager=admin_manager)
            elif cog_name == 'LeagueCog':
                cog.set_dependencies(timekeeper_manager=timekeeper_manager, admin_manager=admin_manager, schedule_manager=schedule_manager, channel_summarizer=channel_summarizer, ai_assistant=ai_assistant, AI_AVAILABLE=AI_AVAILABLE)
            elif cog_name == 'AdminCog':
                cog.set_dependencies(admin_manager=admin_manager, channel_manager=channel_manager, timekeeper_manager=timekeeper_manager, ai_assistant=ai_assistant, schedule_manager=schedule_manager)
            elif cog_name == 'FunCog':
                cog.set_dependencies(admin_manager=admin_manager, ai_assistant=ai_assistant, channel_manager=channel_manager)
            elif cog_name == 'RecruitingCog':
                if hasattr(cog, 'admin_manager'):
                    cog.admin_manager = admin_manager
            logger.info(f"  Dependencies set for {cog_name}")

    logger.info("All dependencies configured")


# ==================== BOT EVENTS ====================

@bot.event
async def on_ready():
    """Called when the bot is ready"""
    global _startup_complete
    logger.info(f"{bot.user} is online!")
    logger.info(f"Connected to {len(bot.guilds)} server(s)")

    # discord.py calls on_ready again after a reconnect. Re-running setup would build a
    # second TimekeeperManager and restore the timer again while the old countdown task
    # keeps running — duplicate warnings, duplicate TIME'S UP, and a double week advance.
    if _startup_complete:
        logger.info("Reconnected — startup already done, skipping re-initialization")
        return
    _startup_complete = True

    # One Harry at a time: take over from any older copy, then watch for a newer one
    if await instance_lock.claim(bot) and not watch_instance.is_running():
        watch_instance.start()

    # Initialize server config with bot (needed for Discord storage)
    server_config.set_bot(bot)
    await server_config.load_from_discord()
    logger.info(f"Server config loaded ({len(server_config._configs)} servers)")

    # Setup dependencies (includes loading timer state, charter, etc.)
    await setup_dependencies()

    # Sync commands to guilds (instant) and globally
    try:
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            _sync_results[guild.id] = len(synced)
            logger.info(f"Synced {len(synced)} command(s) to {guild.name}")

        # Global sync (takes up to 1 hour for other servers)
        global_synced = await bot.tree.sync()
        logger.info(f"Synced {len(global_synced)} command(s) globally")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

    # Send startup notification to admin channels
    await send_startup_notification()

    # Start background tasks
    if not check_weekly_digest.is_running():
        check_weekly_digest.start()
        logger.info("Weekly digest task started")


@tasks.loop(seconds=instance_lock.CHECK_SECONDS)
async def watch_instance():
    """Stand down if a newer copy of Harry has started (otherwise both answer everything)."""
    if await instance_lock.superseded(bot):
        watch_instance.stop()
        await instance_lock.stand_down(bot)


@tasks.loop(hours=24)
async def check_weekly_digest():
    """Check daily if weekly digest should be sent"""
    try:
        from .utils.weekly_digest import get_weekly_digest
        digest = get_weekly_digest(bot)

        if await digest.should_send_digest():
            logger.info("Sending weekly digest...")
            await digest.send_digest_to_admins()
    except Exception as e:
        logger.error(f"Error in weekly digest task: {e}")


@check_weekly_digest.before_loop
async def before_digest_check():
    """Wait until bot is ready before starting digest checks"""
    await bot.wait_until_ready()


async def send_startup_notification():
    """Send detailed startup status to development channel only"""
    from datetime import datetime

    from .utils.server_config import FeatureModule

    # ONLY send to dev channel
    DEV_CHANNEL_ID = int(os.getenv('DEV_CHANNEL_ID', '1417732043936108564'))

    dev_channel = bot.get_channel(DEV_CHANNEL_ID)
    if not dev_channel:
        logger.warning(f"Could not find dev channel {DEV_CHANNEL_ID}")
        return

    from . import __version__
    current_version = __version__
    version_title = "Update"
    version_emoji = "🏈"

    if version_manager:
        try:
            current_version = version_manager.get_current_version()
            version_info = version_manager.get_latest_version_info()
            version_title = version_info.get('title', 'Update')
            version_emoji = version_info.get('emoji', '📌')
        except Exception:
            pass

    # Build detailed status
    embed = discord.Embed(
        title="🏈 Harry is Online!",
        description=f"**Version {current_version}** - {version_title} {version_emoji}\n"
                   f"**Status:** Deployed ✅ | **Time:** {datetime.now().strftime('%I:%M:%S %p')}\n",
        color=Colors.SUCCESS,
        timestamp=datetime.now()
    )

    # 📊 Connected Servers
    server_list = []
    for guild in bot.guilds:
        server_list.append(f"• **{guild.name}** (ID: {guild.id}) - {guild.member_count} members")

    embed.add_field(
        name=f"📊 Connected Servers ({len(bot.guilds)})",
        value="\n".join(server_list) if server_list else "None",
        inline=False
    )

    # ⚙️ Command Sync Status
    sync_status = []
    for guild in bot.guilds:
        count = _sync_results.get(guild.id)
        sync_status.append(f"• **{guild.name}**: " + (f"{count} commands ✅" if count is not None else "not synced ❌"))

    embed.add_field(
        name="⚙️ Command Sync Status",
        value="\n".join(sync_status) if sync_status else "None",
        inline=False
    )

    # 📦 Loaded Cogs
    cog_list = []
    for cog_name in bot.cogs.keys():
        cog_list.append(f"• {cog_name}")

    embed.add_field(
        name=f"📦 Loaded Cogs ({len(bot.cogs)})",
        value="\n".join(cog_list) if cog_list else "None",
        inline=False
    )

    # 🔧 Module Status per Server
    module_status = []
    for guild in bot.guilds:
        modules = []
        for module in FeatureModule:
            if server_config.is_module_enabled(guild.id, module):
                modules.append(module.value)
        module_status.append(f"**{guild.name}**: {', '.join(modules) if modules else 'None'}")

    embed.add_field(
        name="🔧 Enabled Modules per Server",
        value="\n".join(module_status) if module_status else "None",
        inline=False
    )

    # ⏰ Timer Status
    if timekeeper_manager:
        try:
            timer_info = timekeeper_manager.get_restored_timer_info()
            if timer_info:
                timer_channel_id = timer_info.get('channel_id')
                guild_name = timer_info.get('guild_name', 'Unknown')
                guild_id = timer_info.get('guild_id', 'Unknown')
                season = timer_info.get('season', '?')
                week = timer_info.get('week', '?')
                if isinstance(week, int):
                    from .utils.timekeeper import get_week_name as get_week_name_util
                    week_label = get_week_name_util(week)
                else:
                    week_label = f"Week {week}"

                timer_text = (
                    f"**✅ Timer Restored Successfully**\n"
                    f"• Server: **{guild_name}** (ID: {guild_id})\n"
                    f"• Channel: #{timer_info['channel_name']} (ID: {timer_channel_id})\n"
                    f"• Season/Week: **Season {season}, {week_label}**\n"
                    f"• Time Remaining: {int(timer_info['hours_remaining'])}h {timer_info['minutes_remaining']}m\n"
                    f"• Ends At: {timer_info['end_time']}"
                )
                embed.add_field(
                    name="⏰ League Timer",
                    value=timer_text,
                    inline=False
                )
                logger.info(f"Timer restored: {guild_name} (ID: {guild_id}) - S{season}W{week}")
            else:
                embed.add_field(
                    name="⏰ League Timer",
                    value="No active timer",
                    inline=False
                )
        except Exception as e:
            logger.warning(f"Could not get timer info: {e}")

    embed.set_footer(text="Harry Development Status 🛠️ | This message only appears in dev channel")

    try:
        await dev_channel.send(embed=embed)
        logger.info("Sent detailed startup status to dev channel")
    except Exception as e:
        logger.warning(f"Could not send startup to dev channel: {e}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    """Catch slash-command failures: tell the user, DM the owner the traceback."""
    from discord import app_commands

    original = getattr(error, 'original', error)
    command_name = interaction.command.qualified_name if interaction.command else "unknown command"

    # Expected, user-facing conditions — no need to wake the owner. Harry's words,
    # not discord.py's ("The check functions for command ... failed").
    if isinstance(error, app_commands.CommandOnCooldown):
        message = f"❌ Slow down, mate. Try again in {error.retry_after:.0f}s."
    elif isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        message = "❌ You can't use that one here, mate."
    else:
        logger.error(f"Error in /{command_name}: {original}", exc_info=original)
        from .utils.error_reporter import get_error_reporter
        await get_error_reporter().report(original, f"/{command_name}")
        from .services.oops import OOPS
        message = OOPS

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception:
        pass  # Interaction may have expired; the report already went out


@bot.event
async def on_error(event_method, *args, **kwargs):
    """Catch errors raised inside event handlers (on_message and friends)."""
    import sys
    error = sys.exc_info()[1]
    logger.error(f"Error in {event_method}", exc_info=True)
    if error is not None:
        from .utils.error_reporter import get_error_reporter
        await get_error_reporter().report(error, f"event {event_method}")


@bot.event
async def on_guild_join(guild):
    """Called when the bot joins a new guild"""
    logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

    # Sync commands to new guild
    try:
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"Synced {len(synced)} command(s) to {guild.name}")
    except Exception as e:
        logger.error(f"Failed to sync to {guild.name}: {e}")


async def _handle_advance(message):
    """Advance the week and restart the 48h countdown for an "@everyone advanced" post."""
    # Serialize advances so two people posting "advanced" at once can't double-advance
    async with timekeeper_manager.advance_lock:
        if timekeeper_manager.is_duplicate_advance():
            logger.info(f"Ignoring duplicate advance from {message.author} (already advanced moments ago)")
            await message.reply(
                "Already got it, mate — the week was just advanced. "
                "If that really was a second advance, an admin can fix it with `/league set_week`.",
                mention_author=False,
            )
            return

        # Stop every running timer (including strays in other channels) so
        # nothing expires later and advances the week a second time
        await timekeeper_manager.stop_all_timers()

        # This post is the only thing that moves the week — a countdown running out
        # just nags; it never advances.
        season_info = timekeeper_manager.get_season_week()
        if season_info['season'] and season_info['week'] is not None:
            old_week_name = season_info.get('week_name', f"Week {season_info['week']}")
            await timekeeper_manager.increment_week()
            season_info = timekeeper_manager.get_season_week()
            new_week_name = season_info.get('week_name', f"Week {season_info['week']}")
            logger.info(f"Manual advance: {old_week_name} → {new_week_name}")
        timekeeper_manager.last_manual_advance_at = datetime.now()

        # Start new timer (default 48 hours)
        success = await timekeeper_manager.start_timer(message.channel, 48)

        if success:
            # Get season/week info for display
            if not season_info:
                season_info = timekeeper_manager.get_season_week()
            if season_info['season'] and season_info['week'] is not None:
                # season_info is the week we just advanced INTO, so show where we came from
                week_name = season_info.get('week_name', f"Week {season_info['week']}")
                from .utils.timekeeper import get_prev_week
                from .utils.timekeeper import \
                    get_week_name as get_week_name_util
                prev_week_name = get_week_name_util(get_prev_week(season_info['week']))
                phase = season_info.get('phase', 'Regular Season')
                season_text = f"**Season {season_info['season']}**\n📍 {prev_week_name} → **{week_name}**\n🏈 Phase: {phase}\n\n"
            else:
                season_text = ""

            from .config import Colors
            from .utils.timekeeper import format_est_time
            embed = discord.Embed(
                title="⏰ Advance Countdown Restarted!",
                description=f"Right then! Timer's been restarted!\n\n🏈 **48 HOUR COUNTDOWN STARTED** 🏈\n\n{season_text}You got **48 hours** to get your bleedin' games done!",
                color=Colors.SUCCESS
            )
            status = timekeeper_manager.get_status(message.channel)
            embed.add_field(
                name="⏳ Deadline",
                value=format_est_time(status['end_time'], '%A, %B %d at %I:%M %p'),
                inline=False
            )
            embed.set_footer(text="Harry's Advance Timer 🏈 | Use /league timer_status to check progress")

            # Send to message channel (usually #general)
            await message.channel.send(content="@everyone", embed=embed)
            logger.info(f"Timer restarted by {message.author} via @everyone + 'advanced'")

            # Send schedule for the new week (if schedule_announcement enabled).
            # Every skip is logged — a silent miss here is hard to debug from Discord.
            from .utils.timekeeper import get_game_week
            week_num = get_game_week(season_info.get('week')) if season_info else None
            if not server_config.get_setting(message.guild.id, "schedule_announcement", True):
                logger.info("Schedule announcement disabled for this server, skipping")
            elif not schedule_manager:
                logger.warning("No schedule manager — can't announce this week's matchups")
            elif season_info.get('week') is None:
                logger.warning("Season/week not set — can't announce this week's matchups")
            elif week_num is None:
                logger.info(f"{season_info.get('week_name')} has no regular-season games, skipping matchups")
            else:
                schedule_embed = schedule_manager.build_week_embed(week_num)
                if not schedule_embed:
                    logger.warning(f"No schedule data for Week {week_num} — nothing to announce")
                else:
                    await message.channel.send(embed=schedule_embed)
                    logger.info(f"Sent Week {week_num} schedule")

            # Season's over: Harry opens a thread to write it into League History. In the
            # background, since reading the chat takes a minute.
            from .utils.server_config import FeatureModule
            from .utils.timekeeper import SEASON_RECAP_WEEK
            charter_cog = bot.get_cog('CharterCog')
            if (season_info.get('week') == SEASON_RECAP_WEEK and charter_cog
                    and server_config.is_module_enabled(message.guild.id, FeatureModule.LEAGUE)):
                task = asyncio.create_task(charter_cog.announce_season_history(message.channel, season_info['season']))
                _background_tasks.add(task)  # asyncio keeps only a weak reference to running tasks
                task.add_done_callback(_background_tasks.discard)
                logger.info(f"Season {season_info['season']} over - Harry's writing the history")
        else:
            from .config import Colors
            embed = discord.Embed(
                title="❌ Failed to Restart Timer",
                description="Couldn't restart the timer, mate. Try using `/league timer` instead!",
                color=Colors.ERROR
            )
            await message.channel.send(embed=embed)
            logger.error(f"Failed to restart timer for {message.author}")


@bot.event
async def on_message(message):
    """Handle messages - for @mentions, rivalry responses, and @everyone advanced"""
    # Ignore bot messages
    if message.author.bot:
        return

    # Holiday reactions (Halloween week: 🎃 / 👻 / 🪦 / 💀) on some posts from certain members
    from .utils.holidays import current_holiday, holiday_reaction, react_this_time
    reaction = holiday_reaction(message.author, current_holiday())
    if reaction and not react_this_time():
        reaction = None
    if reaction:
        try:
            await message.add_reaction(reaction)
        except discord.HTTPException as e:
            logger.warning(f"Could not add holiday reaction: {e}")

    # PRIORITY: Check for @everyone/@here + "advanced" to restart timer
    # This advances the week and restarts the countdown (available to everyone)
    # Only react to "advanced" in the designated advance/notification channel.
    # Without this guard, an @everyone "advanced" post in any other channel, thread,
    # or server the bot can read would hijack the timer and advance the week.
    from .utils.timekeeper import is_advance_trigger
    advance_channel_id = (
        timekeeper_manager.get_notification_channel_id()
        if timekeeper_manager else None
    )

    if is_advance_trigger(message, advance_channel_id):
        logger.info(f"@everyone/@channel + 'advanced' detected from {message.author} - advancing week")

        if not timekeeper_manager:
            logger.warning("Timekeeper manager not available for advance")
        else:
            await _handle_advance(message)

        # Don't process this message further - timer restart was handled
        return

    # "done" from a charter editor in Harry's season history thread opens the charter PR
    if isinstance(message.channel, discord.Thread):
        charter_cog = bot.get_cog('CharterCog')
        if charter_cog and await charter_cog.handle_history_reply(message):
            return

    # Team banter (Fuck Oregon!, etc.) wherever Fun & Games is on
    if message.guild:
        from .cogs.fun import rivalry_response
        from .utils.server_config import FeatureModule
        if server_config.is_module_enabled(message.guild.id, FeatureModule.FUN_GAMES):
            response = rivalry_response(message.content)
            if response:
                await message.channel.send(response)
                logger.info(f"Rivalry response triggered: {response}")

    # Let cogs handle their own message processing (FunCog targeting, command parsing, etc.)
    await bot.process_commands(message)


# ==================== MAIN ====================

async def main():
    """Main entry point"""
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set!")
        sys.exit(1)

    async with bot:
        await load_cogs()
        try:
            await bot.start(token)
        finally:
            # Playwright's headless Chromium outlives the bot otherwise
            from .utils.on3_scraper import on3_scraper
            await on3_scraper.cleanup()

    # Exiting would get a stood-down copy restarted by the host, and it would take the
    # lease back from the live one. Idle until the host stops it instead.
    if instance_lock.stood_down:
        logger.info("Standing by; the newer copy of Harry is live")
        await asyncio.Event().wait()


def run():
    """Run the bot"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
