#!/usr/bin/env python3
"""
Admin Cog for CFB 26 League Bot

Provides administrative commands for managing the bot.
Commands:
- /admin set_channel - Set admin notification channel
- /admin add - Add bot admin
- /admin remove - Remove bot admin
- /admin list - List bot admins
- /admin block - Block channel
- /admin unblock - Unblock channel
- /admin blocked - List blocked channels
- /admin config - Configure modules
- /admin sync - Force sync slash commands
- /admin channels - Manage channel whitelist
"""

import logging
import sys
import platform
import time
from datetime import datetime
from typing import Optional

import discord
import aiohttp
from discord import app_commands
from discord.ext import commands
from bs4 import BeautifulSoup

from ..config import Colors, Footers
from ..utils.server_config import server_config, FeatureModule
from ..utils.on3_scraper import on3_scraper

logger = logging.getLogger('CFB26Bot.Admin')


class AdminCog(commands.Cog):
    """Administrative commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dependencies - set after loading
        self.admin_manager = None
        self.channel_manager = None
        self.timekeeper_manager = None
        logger.info("🔧 AdminCog initialized")

    def set_dependencies(self, admin_manager=None, channel_manager=None, timekeeper_manager=None, ai_assistant=None):
        """Set dependencies after bot is ready"""
        self.admin_manager = admin_manager
        self.channel_manager = channel_manager
        self.timekeeper_manager = timekeeper_manager
        # Store ai_assistant on bot for access in commands
        if ai_assistant:
            self.bot.ai_assistant = ai_assistant

    # Command group
    admin_group = app_commands.Group(
        name="admin",
        description="🔧 Admin commands for managing Harry"
    )

    @admin_group.command(name="debug", description="Bot debugging tools")
    @app_commands.describe(
        tool="Tool to run: info, scraper, or test_url",
        url="URL to test (for test_url only)"
    )
    @app_commands.choices(tool=[
        app_commands.Choice(name="ℹ️ System Info", value="info"),
        app_commands.Choice(name="🕸️ Scraper Status", value="scraper"),
        app_commands.Choice(name="🌐 Test URL Fetch", value="test_url"),
    ])
    async def debug(
        self,
        interaction: discord.Interaction,
        tool: str,
        url: Optional[str] = None
    ):
        """Run debug tools"""
        # Check admin
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can use debug tools!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if tool == "info":
            # System Info
            embed = discord.Embed(
                title="ℹ️ System Debug Info",
                color=Colors.PRIMARY
            )

            # System
            embed.add_field(
                name="💻 System",
                value=f"**OS:** {platform.system()} {platform.release()}\n"
                      f"**Python:** {sys.version.split()[0]}\n"
                      f"**Discord.py:** {discord.__version__}",
                inline=True
            )

            # Bot
            uptime = datetime.now() - datetime.fromtimestamp(self.bot.user.created_at.timestamp())
            # Note: bot.user.created_at is account creation, not start time.
            # We don't have start time tracked here easily without adding it to bot.py
            # So just skip uptime for now or use process time

            embed.add_field(
                name="🤖 Bot",
                value=f"**Latency:** {self.bot.latency * 1000:.1f}ms\n"
                      f"**Guilds:** {len(self.bot.guilds)}\n"
                      f"**Users:** {len(self.bot.users)}",
                inline=True
            )

            # Modules status for this guild
            if interaction.guild:
                enabled = server_config.get_enabled_modules(interaction.guild.id)
                enabled_list = [m.upper() for m in enabled]
                embed.add_field(
                    name="⚙️ Enabled Modules",
                    value=", ".join(enabled_list) if enabled_list else "None",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        elif tool == "scraper":
            # Scraper Status
            embed = discord.Embed(
                title="🕸️ Scraper Debug Info",
                color=Colors.PRIMARY
            )

            # Playwright Status
            pw_status = "✅ Available" if on3_scraper.PLAYWRIGHT_AVAILABLE else "❌ Not Installed"
            if on3_scraper.PLAYWRIGHT_AVAILABLE and on3_scraper._browser:
                pw_status += " (Running)"

            embed.add_field(
                name="🎭 Playwright",
                value=pw_status,
                inline=True
            )

            # Blocked Status
            blocked = "🔴 YES" if on3_scraper.is_blocked() else "🟢 No"
            embed.add_field(
                name="🚫 Blocked?",
                value=blocked,
                inline=True
            )

            # Cache Stats
            stats = on3_scraper._cache
            embed.add_field(
                name="💾 Cache",
                value=f"**Size:** {len(stats)} entries",
                inline=True
            )

            # Zyte Status
            zyte = on3_scraper.get_zyte_usage()
            zyte_status = "✅ Configured" if zyte['is_available'] else "❌ Not Configured"
            embed.add_field(
                name="⚡ Zyte API",
                value=f"{zyte_status}\n**Requests:** {zyte['request_count']}",
                inline=True
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        elif tool == "test_url":
            if not url:
                await interaction.followup.send("❌ Please provide a URL to test!", ephemeral=True)
                return

            embed = discord.Embed(
                title="🌐 URL Test",
                description=f"Fetching: {url}",
                color=Colors.PRIMARY
            )

            start_time = time.time()
            try:
                # Try fetching using the scraper's method to test its bypass
                html = await on3_scraper._fetch_page(url)
                duration = time.time() - start_time

                if html:
                    content_len = len(html)
                    title = "Unknown"
                    try:
                        soup = BeautifulSoup(html, 'html.parser')
                        if soup.title:
                            title = soup.title.string.strip()
                    except Exception:
                        pass

                    embed.color = Colors.SUCCESS
                    embed.add_field(name="✅ Status", value="Success (200 OK)", inline=True)
                    embed.add_field(name="⏱️ Time", value=f"{duration:.2f}s", inline=True)
                    embed.add_field(name="📄 Size", value=f"{content_len:,} bytes", inline=True)
                    embed.add_field(name="📑 Title", value=title[:100], inline=False)

                    # Check for blocking text
                    is_blocked = on3_scraper._check_if_blocked(html)
                    embed.add_field(name="🛡️ Block Detected?", value="🔴 YES" if is_blocked else "🟢 No", inline=True)

                else:
                    embed.color = Colors.ERROR
                    embed.add_field(name="❌ Status", value="Failed (None returned)", inline=True)
                    embed.add_field(name="⏱️ Time", value=f"{duration:.2f}s", inline=True)

            except Exception as e:
                duration = time.time() - start_time
                embed.color = Colors.ERROR
                embed.add_field(name="❌ Error", value=str(e), inline=False)
                embed.add_field(name="⏱️ Time", value=f"{duration:.2f}s", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="debug", description="Bot debugging tools")
    @app_commands.describe(
        tool="Tool to run: info, scraper, test_url, or logs",
        url="URL to test (for test_url only)",
        lines="Number of log lines to retrieve (for logs only, default 50)"
    )
    @app_commands.choices(tool=[
        app_commands.Choice(name="ℹ️ System Info", value="info"),
        app_commands.Choice(name="🕸️ Scraper Status", value="scraper"),
        app_commands.Choice(name="🌐 Test URL Fetch", value="test_url"),
        app_commands.Choice(name="📝 View Logs", value="logs"),
    ])
    async def debug(
        self,
        interaction: discord.Interaction,
        tool: str,
        url: Optional[str] = None,
        lines: Optional[int] = 50
    ):
        """Run debug tools"""
        # Check admin
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can use debug tools!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if tool == "info":
            # System Info
            embed = discord.Embed(
                title="ℹ️ System Debug Info",
                color=Colors.PRIMARY
            )

            # System
            embed.add_field(
                name="💻 System",
                value=f"**OS:** {platform.system()} {platform.release()}\n"
                      f"**Python:** {sys.version.split()[0]}\n"
                      f"**Discord.py:** {discord.__version__}",
                inline=True
            )

            # Bot
            embed.add_field(
                name="🤖 Bot",
                value=f"**Latency:** {self.bot.latency * 1000:.1f}ms\n"
                      f"**Guilds:** {len(self.bot.guilds)}\n"
                      f"**Users:** {len(self.bot.users)}",
                inline=True
            )

            # Modules status for this guild
            if interaction.guild:
                enabled = server_config.get_enabled_modules(interaction.guild.id)
                enabled_list = [m.upper() for m in enabled]
                embed.add_field(
                    name="⚙️ Enabled Modules",
                    value=", ".join(enabled_list) if enabled_list else "None",
                    inline=False
                )

            await interaction.followup.send(embed=embed, ephemeral=True)

        elif tool == "scraper":
            # Scraper Status
            embed = discord.Embed(
                title="🕸️ Scraper Debug Info",
                color=Colors.PRIMARY
            )

            # Playwright Status
            pw_status = "✅ Available" if on3_scraper.PLAYWRIGHT_AVAILABLE else "❌ Not Installed"
            if on3_scraper.PLAYWRIGHT_AVAILABLE and on3_scraper._browser:
                pw_status += " (Running)"

            embed.add_field(
                name="🎭 Playwright",
                value=pw_status,
                inline=True
            )

            # Blocked Status
            blocked = "🔴 YES" if on3_scraper.is_blocked() else "🟢 No"
            embed.add_field(
                name="🚫 Blocked?",
                value=blocked,
                inline=True
            )

            # Cache Stats
            stats = on3_scraper._cache
            embed.add_field(
                name="💾 Cache",
                value=f"**Size:** {len(stats)} entries",
                inline=True
            )

            # Zyte Status
            zyte = on3_scraper.get_zyte_usage()
            zyte_status = "✅ Configured" if zyte['is_available'] else "❌ Not Configured"
            embed.add_field(
                name="⚡ Zyte API",
                value=f"{zyte_status}\n**Requests:** {zyte['request_count']}",
                inline=True
            )

            await interaction.followup.send(embed=embed, ephemeral=True)

        elif tool == "test_url":
            if not url:
                await interaction.followup.send("❌ Please provide a URL to test!", ephemeral=True)
                return

            embed = discord.Embed(
                title="🌐 URL Test",
                description=f"Fetching: {url}",
                color=Colors.PRIMARY
            )

            start_time = time.time()
            try:
                # Try fetching using the scraper's method to test its bypass
                html = await on3_scraper._fetch_page(url)
                duration = time.time() - start_time

                if html:
                    content_len = len(html)
                    title = "Unknown"
                    try:
                        soup = BeautifulSoup(html, 'html.parser')
                        if soup.title:
                            title = soup.title.string.strip()
                    except Exception:
                        pass

                    embed.color = Colors.SUCCESS
                    embed.add_field(name="✅ Status", value="Success (200 OK)", inline=True)
                    embed.add_field(name="⏱️ Time", value=f"{duration:.2f}s", inline=True)
                    embed.add_field(name="📄 Size", value=f"{content_len:,} bytes", inline=True)
                    embed.add_field(name="📑 Title", value=title[:100], inline=False)

                    # Check for blocking text
                    is_blocked = on3_scraper._check_if_blocked(html)
                    embed.add_field(name="🛡️ Block Detected?", value="🔴 YES" if is_blocked else "🟢 No", inline=True)

                else:
                    embed.color = Colors.ERROR
                    embed.add_field(name="❌ Status", value="Failed (None returned)", inline=True)
                    embed.add_field(name="⏱️ Time", value=f"{duration:.2f}s", inline=True)

            except Exception as e:
                duration = time.time() - start_time
                embed.color = Colors.ERROR
                embed.add_field(name="❌ Error", value=str(e), inline=False)
                embed.add_field(name="⏱️ Time", value=f"{duration:.2f}s", inline=True)

            await interaction.followup.send(embed=embed, ephemeral=True)

        elif tool == "logs":
            # View Logs
            try:
                with open('bot.log', 'r', encoding='utf-8') as f:
                    # Read all lines
                    all_lines = f.readlines()
                    # Get last N lines
                    last_lines = all_lines[-lines:] if lines else all_lines[-50:]
                    log_content = "".join(last_lines)

                    if not log_content:
                        await interaction.followup.send("ℹ️ Log file is empty.", ephemeral=True)
                        return

                    # Create a file object to send
                    from io import StringIO
                    log_file = discord.File(StringIO(log_content), filename="bot_debug.log")

                    await interaction.followup.send(
                        f"📝 Here are the last **{len(last_lines)}** log lines:",
                        file=log_file,
                        ephemeral=True
                    )
            except FileNotFoundError:
                await interaction.followup.send("❌ Log file `bot.log` not found. Logging might not be configured to file.", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error reading logs: {e}", ephemeral=True)

    @admin_group.command(name="set_channel", description="Set the channel for admin outputs")
    @app_commands.describe(
        channel="Select a channel",
        channel_id="Or paste a channel ID"
    )
    async def set_channel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        channel_id: Optional[str] = None
    ):
        """Set the admin notification channel"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can set the admin channel!", ephemeral=True)
            return

        if not interaction.guild:
            await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        if channel:
            target_channel_id = channel.id
            channel_name = f"#{channel.name}"
        elif channel_id:
            try:
                target_channel_id = int(channel_id.strip())
                fetched = interaction.guild.get_channel(target_channel_id)
                channel_name = f"#{fetched.name}" if fetched else f"<#{target_channel_id}>"
            except ValueError:
                await interaction.response.send_message("❌ Invalid channel ID!", ephemeral=True)
                return
        else:
            await interaction.response.send_message("❌ Provide a channel or channel_id!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        server_config.set_admin_channel(guild_id, target_channel_id)
        await server_config.save_to_discord()

        embed = discord.Embed(
            title="🔧 Admin Channel Set!",
            description=f"Admin outputs will go to: **{channel_name}**",
            color=Colors.SUCCESS
        )
        embed.set_footer(text=Footers.CONFIG)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="add", description="Add a user as bot admin")
    @app_commands.describe(user="The user to make a bot admin")
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        """Add a bot admin"""
        if not self.admin_manager:
            await interaction.response.send_message("❌ Admin manager not available", ephemeral=True)
            return

        if not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ You need to be a bot admin!", ephemeral=True)
            return

        success = self.admin_manager.add_admin(user.id)

        if success:
            embed = discord.Embed(
                title="✅ Bot Admin Added!",
                description=f"**{user.display_name}** is now a bot admin!",
                color=Colors.SUCCESS
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Already an Admin",
                description=f"{user.display_name} is already a bot admin!",
                color=Colors.WARNING
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="remove", description="Remove a user as bot admin")
    @app_commands.describe(user="The user to remove as bot admin")
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        """Remove a bot admin"""
        if not self.admin_manager:
            await interaction.response.send_message("❌ Admin manager not available", ephemeral=True)
            return

        if not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ You need to be a bot admin!", ephemeral=True)
            return

        success = self.admin_manager.remove_admin(user.id)

        if success:
            embed = discord.Embed(
                title="✅ Bot Admin Removed",
                description=f"**{user.display_name}** is no longer a bot admin.",
                color=Colors.ERROR
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Not an Admin",
                description=f"{user.display_name} isn't a bot admin!",
                color=0x808080
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="list", description="List all bot admins")
    async def list_admins(self, interaction: discord.Interaction):
        """List all bot admins"""
        if not self.admin_manager:
            await interaction.response.send_message("❌ Admin manager not available", ephemeral=True)
            return

        admin_ids = self.admin_manager.get_admin_list()

        if not admin_ids:
            embed = discord.Embed(
                title="🔐 Bot Admins",
                description="No bot-specific admins configured.\nDiscord Administrators can use admin commands.",
                color=0x808080
            )
        else:
            admin_info = []
            for aid in admin_ids:
                try:
                    user = await self.bot.fetch_user(aid)
                    admin_info.append(f"• **{user.display_name}** (`{user.name}`)")
                except Exception:
                    admin_info.append(f"• User ID: {aid}")

            embed = discord.Embed(
                title="🔐 Bot Admins",
                description=f"Found **{len(admin_ids)}** bot admin(s):\n\n" + "\n".join(admin_info),
                color=Colors.SUCCESS
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="block", description="Block unprompted responses in a channel")
    @app_commands.describe(channel="The channel to block")
    async def block(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Block unprompted responses"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can block channels!", ephemeral=True)
            return

        if not self.channel_manager:
            await interaction.response.send_message("❌ Channel manager not available", ephemeral=True)
            return

        was_blocked = self.channel_manager.block_channel(channel.id)

        if was_blocked:
            embed = discord.Embed(
                title="🔇 Channel Blocked!",
                description=f"I won't make unprompted responses in {channel.mention}.\n\n**@mentions still work!**",
                color=Colors.WARNING
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Already Blocked",
                description=f"{channel.mention} is already blocked!",
                color=0x808080
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="unblock", description="Allow unprompted responses in a channel")
    @app_commands.describe(channel="The channel to unblock")
    async def unblock(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Allow unprompted responses"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can unblock channels!", ephemeral=True)
            return

        if not self.channel_manager:
            await interaction.response.send_message("❌ Channel manager not available", ephemeral=True)
            return

        was_unblocked = self.channel_manager.unblock_channel(channel.id)

        if was_unblocked:
            embed = discord.Embed(
                title="🔊 Channel Unblocked!",
                description=f"I can respond in {channel.mention} again!",
                color=Colors.SUCCESS
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Not Blocked",
                description=f"{channel.mention} wasn't blocked!",
                color=0x808080
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="blocked", description="Show all blocked channels")
    async def blocked(self, interaction: discord.Interaction):
        """Show all blocked channels"""
        if not self.channel_manager:
            await interaction.response.send_message("❌ Channel manager not available", ephemeral=True)
            return

        blocked_ids = self.channel_manager.get_blocked_channels()

        if not blocked_ids:
            embed = discord.Embed(
                title="🔊 No Blocked Channels",
                description="No channels are blocked!",
                color=Colors.SUCCESS
            )
        else:
            channel_info = []
            for cid in blocked_ids:
                ch = self.bot.get_channel(cid)
                if ch:
                    channel_info.append(f"• {ch.mention}")
                else:
                    channel_info.append(f"• Channel ID: {cid}")

            embed = discord.Embed(
                title="🔇 Blocked Channels",
                description=f"**{len(blocked_ids)}** blocked channel(s):\n\n" + "\n".join(channel_info),
                color=Colors.WARNING
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="config", description="Configure Harry's features for this server")
    @app_commands.describe(
        action="What to do: view, enable, disable, or bulk actions",
        module="Which module to toggle (not needed for enable_all/disable_all)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="enable", value="enable"),
        app_commands.Choice(name="disable", value="disable"),
        app_commands.Choice(name="enable_all - Turn on all modules", value="enable_all"),
        app_commands.Choice(name="disable_all - Turn off all modules", value="disable_all"),
    ])
    @app_commands.choices(module=[
        app_commands.Choice(name="ai_chat - /harry, /ask, @mentions", value="ai_chat"),
        app_commands.Choice(name="cfb_data - Player lookup, rankings", value="cfb_data"),
        app_commands.Choice(name="league - Timer, charter, rules", value="league"),
        app_commands.Choice(name="hs_stats - High school stats", value="hs_stats"),
        app_commands.Choice(name="recruiting - On3/247 rankings", value="recruiting"),
        app_commands.Choice(name="fun_games - Rivalry responses (Fuck Oregon!)", value="fun_games"),
    ])
    async def config(
        self,
        interaction: discord.Interaction,
        action: str = "view",
        module: Optional[str] = None
    ):
        """Configure which features are enabled"""
        # Defer IMMEDIATELY to prevent timeout (building the embed is slow)
        if action == "view":
            await interaction.response.defer(ephemeral=True)

        if not interaction.guild:
            if action == "view":
                await interaction.followup.send("❌ This only works in servers!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        guild_id = interaction.guild.id

        if action in ["enable", "disable", "enable_all", "disable_all"]:
            is_admin = (
                interaction.user.guild_permissions.administrator or
                (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
            )
            if not is_admin:
                await interaction.response.send_message("❌ Only admins can change settings!", ephemeral=True)
                return

        if action == "view":
            enabled = server_config.get_enabled_modules(guild_id)

            embed = discord.Embed(
                title="⚙️ Harry's Configuration",
                description=f"Settings for **{interaction.guild.name}**",
                color=Colors.PRIMARY
            )

            # Module statuses
            for mod in FeatureModule:
                is_enabled = mod.value in enabled
                status = "✅ Enabled" if is_enabled else "❌ Disabled"
                if mod == FeatureModule.CORE:
                    status = "✅ Always On"

                desc = server_config.get_module_description(mod)
                embed.add_field(name=f"{desc}", value=f"**Status:** {status}", inline=False)

            # Server settings section
            embed.add_field(name="━━━━━━━━━━━━━━━", value="", inline=False)  # Divider

            # Recruiting source
            rec_source = server_config.get_recruiting_source(guild_id)
            rec_name = "On3/Rivals" if rec_source == "on3" else "247Sports"
            embed.add_field(
                name="⭐ Recruiting Data Source",
                value=f"**Source:** {rec_name}",
                inline=True
            )

            # Season/Week info (if timekeeper available)
            if self.timekeeper_manager:
                season_info = self.timekeeper_manager.get_season_week()
                if season_info and season_info.get('season'):
                    week_name = season_info.get('week_name', f"Week {season_info.get('week', '?')}")
                    embed.add_field(
                        name="🏈 Current Season",
                        value=f"**S{season_info['season']}{week_name}**",
                        inline=True
                    )

            # Bot admins count
            if self.admin_manager:
                admin_count = self.admin_manager.get_admin_count()
                embed.add_field(
                    name="🔧 Bot Admins",
                    value=f"**{admin_count}** configured\nUse `/admin list` to view",
                    inline=True
                )

            # Blocked channels (global, not per-guild)
            if self.channel_manager:
                blocked_count = self.channel_manager.get_blocked_count()
                if blocked_count > 0:
                    embed.add_field(
                        name="🚫 Blocked Channels",
                        value=f"**{blocked_count}** blocked (global)\nUse `/admin blocked` to view",
                        inline=True
                    )

            embed.add_field(
                name="ℹ️ More Commands",
                value="`/admin list` - View admins\n"
                      "`/admin blocked` - View blocked channels\n"
                      "`/recruiting source` - Change recruiting source\n"
                      "`/league week` - View current season/week",
                inline=False
            )

            embed.set_footer(text=Footers.CONFIG)
            await interaction.followup.send(embed=embed, ephemeral=True)

        elif action == "enable":
            if not module:
                await interaction.response.send_message("❌ Specify a module to enable!", ephemeral=True)
                return

            try:
                mod = FeatureModule(module)
            except ValueError:
                await interaction.response.send_message(f"❌ Unknown module: {module}", ephemeral=True)
                return

            if mod == FeatureModule.CORE:
                await interaction.response.send_message("Core features are always enabled!", ephemeral=True)
                return

            server_config.enable_module(guild_id, mod)
            await server_config.save_to_discord()

            embed = discord.Embed(
                title="✅ Module Enabled!",
                description=f"**{mod.value.upper()}** is now enabled!",
                color=Colors.SUCCESS
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "disable":
            if not module:
                await interaction.response.send_message("❌ Specify a module to disable!", ephemeral=True)
                return

            try:
                mod = FeatureModule(module)
            except ValueError:
                await interaction.response.send_message(f"❌ Unknown module: {module}", ephemeral=True)
                return

            if mod == FeatureModule.CORE:
                await interaction.response.send_message("Can't disable core features!", ephemeral=True)
                return

            server_config.disable_module(guild_id, mod)
            await server_config.save_to_discord()

            embed = discord.Embed(
                title="❌ Module Disabled",
                description=f"**{mod.value.upper()}** is now disabled.",
                color=Colors.WARNING
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "enable_all":
            # Enable all modules except CORE (which is always on)
            enabled_count = 0
            for mod in FeatureModule:
                if mod != FeatureModule.CORE:
                    server_config.enable_module(guild_id, mod)
                    enabled_count += 1

            await server_config.save_to_discord()

            embed = discord.Embed(
                title="✅ All Modules Enabled!",
                description=f"Enabled **{enabled_count}** modules:\n"
                           f"• AI Chat\n"
                           f"• CFB Data\n"
                           f"• League\n"
                           f"• HS Stats\n"
                           f"• Recruiting\n"
                           f"• Fun & Games",
                color=Colors.SUCCESS
            )
            embed.set_footer(text="Use /admin config view to see full status")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "disable_all":
            # Disable all modules except CORE (which can't be disabled)
            disabled_count = 0
            for mod in FeatureModule:
                if mod != FeatureModule.CORE:
                    server_config.disable_module(guild_id, mod)
                    disabled_count += 1

            await server_config.save_to_discord()

            embed = discord.Embed(
                title="❌ All Modules Disabled",
                description=f"Disabled **{disabled_count}** modules.\n\n"
                           f"✅ **CORE** remains active (/help, /whats_new, etc.)\n\n"
                           f"Use `/admin config enable_all` to restore.",
                color=Colors.WARNING
            )
            embed.set_footer(text="Use /admin config view to see full status")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="sync", description="Force sync slash commands")
    async def sync_commands(self, interaction: discord.Interaction):
        """Force sync slash commands"""
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can sync commands!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            if interaction.guild:
                synced = await self.bot.tree.sync(guild=interaction.guild)
                embed = discord.Embed(
                    title="✅ Commands Synced!",
                    description=f"Synced **{len(synced)}** command(s) to this server.",
                    color=Colors.SUCCESS
                )
            else:
                synced = await self.bot.tree.sync()
                embed = discord.Embed(
                    title="✅ Global Sync Complete!",
                    description=f"Synced **{len(synced)}** command(s) globally.",
                    color=Colors.SUCCESS
                )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Sync failed: {str(e)}", ephemeral=True)

    @admin_group.command(name="channels", description="View/manage which channels Harry can respond in")
    @app_commands.describe(
        action="What to do (leave empty to view)",
        channel="Which channel to configure"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="view - Show current channel status", value="view"),
        app_commands.Choice(name="enable - Enable Harry in this channel", value="enable"),
        app_commands.Choice(name="disable - Disable Harry in this channel", value="disable"),
        app_commands.Choice(name="toggle_rivalry - Toggle rivalry auto-responses", value="toggle_rivalry"),
    ])
    async def channels(
        self,
        interaction: discord.Interaction,
        action: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        """Manage channel whitelist"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        guild_id = interaction.guild.id
        target_channel = channel or interaction.channel

        if action is None or action == "view":
            await interaction.response.defer(ephemeral=True)

            enabled_channels = server_config.get_enabled_channels(guild_id)
            is_enabled = server_config.is_channel_enabled(guild_id, target_channel.id)
            rivalry_on = server_config.auto_responses_enabled(guild_id, target_channel.id)

            embed = discord.Embed(
                title="📺 Channel Status",
                color=Colors.PRIMARY
            )

            embed.add_field(
                name=f"#{target_channel.name}",
                value=f"**Commands:** {'✅ Enabled' if is_enabled else '❌ Disabled'}\n**Rivalry Responses:** {'✅ On' if rivalry_on else '❌ Off'}",
                inline=False
            )

            if enabled_channels:
                ch_list = []
                for cid in enabled_channels[:10]:
                    ch = interaction.guild.get_channel(cid)
                    if ch:
                        ch_list.append(f"• #{ch.name}")
                embed.add_field(
                    name="Enabled Channels",
                    value="\n".join(ch_list) if ch_list else "None",
                    inline=False
                )

            embed.set_footer(text="Use /admin channels enable/disable to manage")
            await interaction.followup.send(embed=embed, ephemeral=True)

        elif action in ["enable", "disable", "toggle_rivalry"]:
            is_admin = (
                interaction.user.guild_permissions.administrator or
                (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
            )
            if not is_admin:
                await interaction.response.send_message("❌ Only admins can change channel settings!", ephemeral=True)
                return

            if action == "enable":
                server_config.enable_channel(guild_id, target_channel.id)
                await server_config.save_to_discord()
                embed = discord.Embed(
                    title="✅ Channel Enabled!",
                    description=f"Harry is now enabled in **#{target_channel.name}**",
                    color=Colors.SUCCESS
                )

            elif action == "disable":
                server_config.disable_channel(guild_id, target_channel.id)
                await server_config.save_to_discord()
                embed = discord.Embed(
                    title="❌ Channel Disabled",
                    description=f"Harry is now disabled in **#{target_channel.name}**",
                    color=Colors.WARNING
                )

            elif action == "toggle_rivalry":
                # Toggle rivalry auto-responses
                is_on = server_config.toggle_auto_responses(guild_id, target_channel.id)
                await server_config.save_to_discord()
                status = "ON 🦆" if is_on else "OFF"
                embed = discord.Embed(
                    title=f"🏈 Rivalry Responses: {status}",
                    description=f"Auto-responses for #{target_channel.name} are now **{status}**",
                    color=Colors.SUCCESS if is_on else Colors.WARNING
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="zyte", description="Check Zyte API usage and estimated costs")
    @app_commands.describe(
        view="Choose which stats to view"
    )
    @app_commands.choices(view=[
        app_commands.Choice(name="📊 Bot Tracked (This Session)", value="local"),
        app_commands.Choice(name="🌐 Zyte API (Official - Last 30 Days)", value="api"),
        app_commands.Choice(name="📋 Both (Side by Side)", value="both")
    ])
    async def zyte_usage(self, interaction: discord.Interaction, view: str = "local"):
        """Check Zyte API usage statistics"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        # Check if user is admin
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can view Zyte usage!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Get On3 scraper usage
        from .recruiting import get_recruiting_scraper
        guild_id = interaction.guild.id
        scraper, source_name = get_recruiting_scraper(guild_id)

        # Check if it's On3 scraper (has Zyte)
        if source_name == "On3/Rivals" and hasattr(scraper, 'get_zyte_usage'):
            local_usage = scraper.get_zyte_usage()

            if view == "local":
                # Show only bot-tracked stats
                embed = discord.Embed(
                    title="💰 Zyte Usage Report (Bot Tracked)",
                    description=f"Stats tracked this session for **{interaction.guild.name}**",
                    color=Colors.PRIMARY
                )

                # Availability
                status = "✅ Available" if local_usage['is_available'] else "❌ Not configured"
                embed.add_field(
                    name="📡 Status",
                    value=status,
                    inline=False
                )

                if local_usage['is_available']:
                    # Usage stats
                    embed.add_field(
                        name="📊 Requests This Session",
                        value=f"**{local_usage['request_count']}** requests",
                        inline=True
                    )

                    # Cost
                    embed.add_field(
                        name="💵 Estimated Cost",
                        value=f"**${local_usage['estimated_cost']:.4f}**",
                        inline=True
                    )

                    # Rate
                    embed.add_field(
                        name="💳 Rate",
                        value=f"${local_usage['cost_per_1k']:.3f} per 1K requests",
                        inline=True
                    )

                    # Info
                    embed.add_field(
                        name="ℹ️ How It Works",
                        value="Zyte only triggers when free methods (Playwright, Cloudscraper) are blocked by Cloudflare. "
                              "This keeps costs minimal while ensuring reliability.",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="⚠️ Setup Required",
                        value="Add `ZYTE_API_KEY` to environment variables to enable premium bypass.",
                        inline=False
                    )

                embed.set_footer(text="💡 Session stats | Resets on bot restart")

            elif view == "api":
                # Query Zyte Stats API
                if not local_usage['is_available']:
                    embed = discord.Embed(
                        title="⚠️ Zyte Not Configured",
                        description="Zyte API is not currently configured.",
                        color=Colors.WARNING
                    )
                    embed.add_field(
                        name="⚠️ Setup Required",
                        value="Add `ZYTE_API_KEY` to environment variables first.",
                        inline=False
                    )
                else:
                    api_data = await scraper.get_zyte_usage_from_api(days=30)

                    if not api_data:
                        embed = discord.Embed(
                            title="⚠️ Zyte Stats API Unavailable",
                            description="Could not retrieve data from Zyte Stats API.",
                            color=Colors.WARNING
                        )
                        embed.add_field(
                            name="📝 Setup Required",
                            value="To enable official Zyte stats:\n"
                                  "1. Get your **Dashboard API Key** (different from regular API key!)\n"
                                  "   Go to: https://app.zyte.com/o/YOUR_ORG_ID/settings/apikeys\n"
                                  "2. Add `ZYTE_DASHBOARD_API_KEY` to environment variables\n"
                                  "3. Add `ZYTE_ORG_ID` from your dashboard URL\n"
                                  "   (e.g., if URL is `app.zyte.com/o/123456`, use `123456`)",
                            inline=False
                        )
                        embed.add_field(
                            name="💡 Alternative",
                            value="Use 'Bot Tracked' view or check your [Zyte Dashboard](https://app.zyte.com)",
                            inline=False
                        )
                    else:
                        # Display API data
                        embed = discord.Embed(
                            title="🌐 Zyte API Usage (Official)",
                            description=f"Last 30 days from Zyte Stats API\n*(Includes ALL usage on this API key)*",
                            color=Colors.PRIMARY
                        )

                        # Parse Zyte Stats API response
                        results = api_data.get('results', [])
                        if results:
                            result = results[0]

                            # Convert microUSD to USD
                            total_cost_usd = float(result.get('cost_microusd_total', 0)) / 1000000
                            avg_cost_usd = float(result.get('cost_microusd_avg', 0)) / 1000000
                            request_count = result.get('request_count', 0)
                            avg_response_time = float(result.get('response_time_sec_avg', 0))

                            embed.add_field(
                                name="📊 Request Count",
                                value=f"**{request_count:,}** requests",
                                inline=True
                            )

                            embed.add_field(
                                name="💰 Total Cost",
                                value=f"**${total_cost_usd:.6f}**",
                                inline=True
                            )

                            embed.add_field(
                                name="💵 Avg Cost",
                                value=f"${avg_cost_usd:.6f}/request",
                                inline=True
                            )

                            embed.add_field(
                                name="⏱️ Avg Response Time",
                                value=f"{avg_response_time:.2f} seconds",
                                inline=True
                            )

                            # Status codes
                            status_codes = result.get('status_codes', [])
                            if status_codes:
                                status_summary = "\n".join([f"**{sc.get('code', 'N/A')}**: {sc.get('count', 0)}" for sc in status_codes])
                                embed.add_field(
                                    name="📈 Status Codes",
                                    value=status_summary,
                                    inline=True
                                )
                        else:
                            embed.add_field(
                                name="ℹ️ No Data",
                                value="No usage data available for the last 30 days.",
                                inline=False
                            )

                        embed.set_footer(text="💡 From Zyte Stats API | Last 30 days")

            else:  # view == "both"
                # Show both side by side
                embed = discord.Embed(
                    title="💰 Zyte Usage Report (Comprehensive)",
                    description=f"Comparison of bot-tracked vs official API stats",
                    color=Colors.PRIMARY
                )

                if local_usage['is_available']:
                    # Bot tracked section
                    embed.add_field(
                        name="📊 Bot Tracked (This Session)",
                        value=f"**Requests:** {local_usage['request_count']}\n"
                              f"**Cost:** ${local_usage['estimated_cost']:.4f}",
                        inline=True
                    )

                    # Try to get API data
                    api_data = await scraper.get_zyte_usage_from_api(days=30)
                    if api_data:
                        embed.add_field(
                            name="🌐 Zyte API (Last 30 Days)",
                            value=f"*Official data from Zyte*\n"
                                  f"Check details with `/admin zyte view:api`",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="🌐 Zyte Stats API",
                            value="*Not configured*\nNeeds ZYTE_DASHBOARD_API_KEY + ZYTE_ORG_ID",
                            inline=True
                        )

                    embed.set_footer(text="💡 Use view:api or view:local for detailed breakdowns")
                else:
                    embed.add_field(
                        name="⚠️ Setup Required",
                        value="Add `ZYTE_API_KEY` to environment variables to enable Zyte.",
                        inline=False
                    )

            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="ℹ️ Zyte Not Used",
                description=f"Currently using **{source_name}** which doesn't require Zyte API.",
                color=Colors.WARNING
            )
            embed.add_field(
                name="💡 Tip",
                value="Switch to On3/Rivals with `/recruiting source on3` to enable Zyte bypass.",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="ai", description="Check AI API usage, token consumption, and estimated costs")
    @app_commands.describe(
        view="Choose which stats to view"
    )
    @app_commands.choices(view=[
        app_commands.Choice(name="📊 Bot Tracked (All Time)", value="local"),
        app_commands.Choice(name="🌐 OpenAI API (Official - Today Only)", value="api"),
        app_commands.Choice(name="📋 Both (Side by Side)", value="both")
    ])
    async def ai_usage(self, interaction: discord.Interaction, view: str = "local"):
        """Check AI token usage and cost statistics"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        # Check if user is admin
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can view AI usage!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Get AI integration from bot
        if not hasattr(self.bot, 'ai_assistant') or not self.bot.ai_assistant:
            embed = discord.Embed(
                title="ℹ️ AI Not Available",
                description="AI integration is not currently configured.",
                color=Colors.WARNING
            )
            embed.add_field(
                name="⚠️ Setup Required",
                value="Add `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` to environment variables to enable AI features.",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Get local usage stats
        local_usage = self.bot.ai_assistant.get_token_usage()

        # Decide what to show based on view parameter
        if view == "local":
            # Show only bot-tracked stats
            embed = discord.Embed(
                title="🤖 AI Usage Report (Bot Tracked)",
                description=f"Stats tracked by this bot (all time)",
                color=Colors.PRIMARY
            )

            embed.add_field(
                name="📊 Total Requests",
                value=f"**{local_usage['total_requests']:,}** queries",
                inline=True
            )

            embed.add_field(
                name="🎯 Total Tokens",
                value=f"**{local_usage['total_tokens']:,}** tokens",
                inline=True
            )

            embed.add_field(
                name="💰 Total Cost",
                value=f"**${local_usage['total_cost']:.4f}**",
                inline=True
            )

            # OpenAI breakdown
            if local_usage['openai_tokens'] > 0:
                embed.add_field(
                    name="🟢 OpenAI (GPT-3.5-turbo)",
                    value=f"**{local_usage['openai_tokens']:,}** tokens\n${local_usage['openai_cost']:.4f}",
                    inline=True
                )

            # Anthropic breakdown
            if local_usage['anthropic_tokens'] > 0:
                embed.add_field(
                    name="🔵 Anthropic (Claude 3 Haiku)",
                    value=f"**{local_usage['anthropic_tokens']:,}** tokens\n${local_usage['anthropic_cost']:.4f}",
                    inline=True
                )

            embed.set_footer(text="💡 Bot-tracked stats | Persists across restarts")

        elif view == "api":
            # Query OpenAI Usage API
            api_data = await self.bot.ai_assistant.get_openai_usage_from_api()

            if not api_data:
                embed = discord.Embed(
                    title="⚠️ API Data Unavailable",
                    description="Could not retrieve data from OpenAI Usage API. This may be due to:\n"
                               "- API endpoint not available yet\n"
                               "- Account permissions\n"
                               "- Network issues\n"
                               "- No usage data for today",
                    color=Colors.WARNING
                )
                embed.add_field(
                    name="💡 Alternative",
                    value="Try the 'Bot Tracked' view or check your [OpenAI Dashboard](https://platform.openai.com/usage) for historical data",
                    inline=False
                )
            else:
                # Parse API response and display
                embed = discord.Embed(
                    title="🌐 OpenAI API Usage (Official)",
                    description=f"Today's usage from OpenAI Usage API\n*(Includes ALL usage on this API key)*",
                    color=Colors.PRIMARY
                )

                # Parse OpenAI Usage API response
                data = api_data.get('data', [])

                if data:
                    # Aggregate usage across all entries
                    total_tokens = 0
                    total_requests = 0

                    for entry in data:
                        # OpenAI API returns usage in different formats
                        # Try to extract token counts
                        if 'n_context_tokens_total' in entry:
                            total_tokens += entry.get('n_context_tokens_total', 0)
                        if 'n_generated_tokens_total' in entry:
                            total_tokens += entry.get('n_generated_tokens_total', 0)
                        if 'num_requests' in entry:
                            total_requests += entry.get('num_requests', 0)

                    if total_requests > 0:
                        embed.add_field(
                            name="📊 Requests (Today)",
                            value=f"**{total_requests:,}** requests",
                            inline=True
                        )

                    if total_tokens > 0:
                        embed.add_field(
                            name="🎯 Tokens (Today)",
                            value=f"**{total_tokens:,}** tokens",
                            inline=True
                        )

                        # Estimate cost (rough estimate for GPT-3.5-turbo)
                        estimated_cost = (total_tokens / 1000) * 0.001
                        embed.add_field(
                            name="💰 Est. Cost (Today)",
                            value=f"~${estimated_cost:.6f}",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="ℹ️ No Usage Today",
                            value="No OpenAI API usage recorded for today yet.",
                            inline=False
                        )
                else:
                    embed.add_field(
                        name="ℹ️ No Data Available",
                        value="No usage data available for today. This is normal if you haven't made any OpenAI API calls today.",
                        inline=False
                    )

                embed.set_footer(text="💡 From OpenAI Usage API | Resets daily at midnight UTC")

        else:  # view == "both"
            # Show both side by side
            embed = discord.Embed(
                title="🤖 AI Usage Report (Comprehensive)",
                description=f"Comparison of bot-tracked vs official API stats",
                color=Colors.PRIMARY
            )

            # Bot tracked section
            embed.add_field(
                name="📊 Bot Tracked (This Bot Only)",
                value=f"**Requests:** {local_usage['total_requests']:,}\n"
                      f"**Tokens:** {local_usage['total_tokens']:,}\n"
                      f"**Cost:** ${local_usage['total_cost']:.4f}",
                inline=True
            )

            # Try to get API data
            api_data = await self.bot.ai_assistant.get_openai_usage_from_api()
            if api_data:
                embed.add_field(
                    name="🌐 OpenAI API (Today)",
                    value=f"*Official data from OpenAI*\n"
                          f"Check details with `/admin ai view:api`",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🌐 OpenAI API",
                    value="*Not available for today*\nCheck [Dashboard](https://platform.openai.com/usage)",
                    inline=True
                )

            embed.set_footer(text="💡 Use view:api or view:local for detailed breakdowns")

        # Add common info
        if local_usage['total_requests'] > 0 and view == "local":
            avg_tokens_per_request = local_usage['total_tokens'] / local_usage['total_requests']
            avg_cost_per_request = local_usage['total_cost'] / local_usage['total_requests']

            # Estimate based on 100 requests/month (conservative)
            monthly_requests = 100
            monthly_tokens = int(monthly_requests * avg_tokens_per_request)
            monthly_cost = monthly_requests * avg_cost_per_request

            embed.add_field(
                name="📈 Monthly Projection (est. 100 queries)",
                value=f"~{monthly_tokens:,} tokens\n~${monthly_cost:.2f}/month",
                inline=False
            )

        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="cache", description="View or manage bot cache")
    @app_commands.describe(
        action="Action to perform"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="📊 View Stats", value="stats"),
        app_commands.Choice(name="🗑️ Clear Recruiting Cache", value="clear_recruiting"),
        app_commands.Choice(name="🗑️ Clear All Cache", value="clear_all")
    ])
    async def cache_management(self, interaction: discord.Interaction, action: str = "stats"):
        """Manage bot cache"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        # Check if user is admin
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can manage cache!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from ..utils.cache import get_cache
        cache = get_cache()

        if action == "stats":
            # Show cache statistics
            stats = cache.get_stats()

            embed = discord.Embed(
                title="📦 Cache Statistics",
                description=f"Performance and usage statistics",
                color=Colors.PRIMARY
            )

            # Overall stats
            embed.add_field(
                name="📊 Requests",
                value=f"**Total:** {stats['total_requests']:,}\n"
                      f"**Hits:** {stats['hits']:,}\n"
                      f"**Misses:** {stats['misses']:,}",
                inline=True
            )

            embed.add_field(
                name="✅ Hit Rate",
                value=f"**{stats['hit_rate']:.1f}%**\n"
                      f"(Higher = more savings!)",
                inline=True
            )

            embed.add_field(
                name="💾 Cache Size",
                value=f"**{stats['cache_size']:,}** entries\n"
                      f"**{stats['evictions']:,}** evicted",
                inline=True
            )

            # Per-namespace breakdown
            if stats['namespaces']:
                namespace_text = "\n".join([f"**{ns}**: {count}" for ns, count in stats['namespaces'].items()])
                embed.add_field(
                    name="📂 By Type",
                    value=namespace_text,
                    inline=False
                )

            # Cost savings estimate
            if stats['hits'] > 0:
                # Assume each cache hit saves ~$0.00023 (one Zyte request)
                estimated_savings = stats['hits'] * 0.00023
                embed.add_field(
                    name="💰 Estimated Savings",
                    value=f"~${estimated_savings:.4f}\n"
                          f"({stats['hits']} API calls avoided!)",
                    inline=False
                )

            embed.set_footer(text="💡 Cache helps reduce API costs by reusing recent data")
            await interaction.followup.send(embed=embed, ephemeral=True)

        elif action == "clear_recruiting":
            # Clear recruiting cache
            cache.clear(namespace='recruiting')

            embed = discord.Embed(
                title="🗑️ Recruiting Cache Cleared",
                description="All cached recruiting data has been removed. Next player lookups will be fresh from the source.",
                color=Colors.SUCCESS
            )
            embed.set_footer(text="Useful when you want fresh data (e.g., during signing day)")
            await interaction.followup.send(embed=embed, ephemeral=True)

        elif action == "clear_all":
            # Clear all cache
            count = cache.get_stats()['cache_size']
            cache.clear()

            embed = discord.Embed(
                title="🗑️ All Cache Cleared",
                description=f"Removed **{count}** cached entries. All future requests will fetch fresh data.",
                color=Colors.SUCCESS
            )
            embed.set_footer(text="Cache will rebuild automatically as commands are used")
            await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="budget", description="View monthly API cost budget and spending")
    async def budget_status(self, interaction: discord.Interaction):
        """View monthly budget status"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        # Check if user is admin
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can view budget!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from ..utils.cost_tracker import get_cost_tracker
        tracker = get_cost_tracker()
        status = await tracker.get_budget_status()

        embed = discord.Embed(
            title="💰 Monthly Budget Status",
            description=f"API costs for {datetime.now().strftime('%B %Y')}",
            color=Colors.PRIMARY
        )

        # AI costs
        ai_percent = status['percentages']['ai']
        ai_emoji = "🟢" if ai_percent < 50 else "🟡" if ai_percent < 80 else "🔴"
        embed.add_field(
            name=f"{ai_emoji} AI (OpenAI/Anthropic)",
            value=f"**${status['costs']['ai']:.4f}** / ${status['budgets']['ai']:.2f}\n"
                  f"**{ai_percent:.1f}%** used • ${status['remaining']['ai']:.2f} left",
            inline=True
        )

        # Zyte costs
        zyte_percent = status['percentages']['zyte']
        zyte_emoji = "🟢" if zyte_percent < 50 else "🟡" if zyte_percent < 80 else "🔴"
        embed.add_field(
            name=f"{zyte_emoji} Zyte API",
            value=f"**${status['costs']['zyte']:.4f}** / ${status['budgets']['zyte']:.2f}\n"
                  f"**{zyte_percent:.1f}%** used • ${status['remaining']['zyte']:.2f} left",
            inline=True
        )

        # Total
        total_percent = status['percentages']['total']
        total_emoji = "🟢" if total_percent < 50 else "🟡" if total_percent < 80 else "🔴"
        embed.add_field(
            name=f"{total_emoji} Total Budget",
            value=f"**${status['costs']['total']:.4f}** / ${status['budgets']['total']:.2f}\n"
                  f"**{total_percent:.1f}%** used • ${status['remaining']['total']:.2f} left",
            inline=True
        )

        # Progress bars
        def progress_bar(percent: float, length: int = 10) -> str:
            filled = int(percent / 100 * length)
            empty = length - filled
            return f"[{'█' * filled}{'░' * empty}]"

        embed.add_field(
            name="📊 Progress",
            value=f"**AI:** {progress_bar(ai_percent)} {ai_percent:.0f}%\n"
                  f"**Zyte:** {progress_bar(zyte_percent)} {zyte_percent:.0f}%\n"
                  f"**Total:** {progress_bar(total_percent)} {total_percent:.0f}%",
            inline=False
        )

        # Budget info
        embed.add_field(
            name="ℹ️ About Budgets",
            value="Budgets are configured in environment variables:\n"
                  "`AI_MONTHLY_BUDGET`, `ZYTE_MONTHLY_BUDGET`, `TOTAL_MONTHLY_BUDGET`\n"
                  "Alerts trigger at 50%, 80%, 90%, and 100% of budget.",
            inline=False
        )

        embed.set_footer(text="💡 Resets monthly • Configure budgets in Render env vars")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="digest", description="View or send weekly summary digest")
    @app_commands.describe(
        action="Action to perform"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="📊 View Now", value="view"),
        app_commands.Choice(name="📧 Send to All Admins", value="send")
    ])
    async def weekly_digest(self, interaction: discord.Interaction, action: str = "view"):
        """View or send the weekly digest"""
        if not interaction.guild:
            await interaction.response.send_message("❌ This only works in servers!", ephemeral=True)
            return

        # Check if user is admin
        is_admin = (
            interaction.user.guild_permissions.administrator or
            (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
        )
        if not is_admin:
            await interaction.response.send_message("❌ Only admins can view digest!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        from ..utils.weekly_digest import get_weekly_digest
        digest = get_weekly_digest(self.bot)

        if action == "view":
            # Show digest to requesting admin only
            await digest.send_manual_digest(interaction)

        elif action == "send":
            # Send to all admins
            await digest.send_digest_to_admins()
            await interaction.followup.send(
                "✅ Weekly digest sent to all admins!",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ AdminCog loaded")
