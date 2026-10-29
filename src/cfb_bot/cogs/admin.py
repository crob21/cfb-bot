#!/usr/bin/env python3
"""
Admin Cog for CFB League Bot

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
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors, Footers
from ..utils.server_config import server_config, FeatureModule
from ..services.checks import ADMINS_ONLY, requires_admin
from ..services.oops import NOT_READY, oops

logger = logging.getLogger('CFBBot.Admin')


class AdminCog(commands.Cog):
    """Administrative commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dependencies - set after loading
        self.admin_manager = None
        self.channel_manager = None
        self.timekeeper_manager = None
        logger.info("AdminCog initialized")

    def set_dependencies(self, admin_manager=None, channel_manager=None, timekeeper_manager=None, ai_assistant=None, schedule_manager=None):
        """Set dependencies after bot is ready"""
        self.admin_manager = admin_manager
        self.channel_manager = channel_manager
        self.timekeeper_manager = timekeeper_manager
        self.schedule_manager = schedule_manager
        # Store ai_assistant on bot for access in commands
        if ai_assistant:
            self.bot.ai_assistant = ai_assistant

    # Command group
    admin_group = app_commands.Group(
        name="admin",
        description="🔧 Admin commands for managing Harry",
        guild_only=True,  # servers only; Discord hides it in DMs
    )

    @admin_group.command(name="set_channel", description="Set the channel for admin outputs")
    @app_commands.describe(
        channel="Select a channel",
        channel_id="Or paste a channel ID"
    )
    @requires_admin()
    async def set_channel(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None,
        channel_id: Optional[str] = None
    ):
        """Set the admin notification channel"""
        await interaction.response.defer(ephemeral=True)

        if channel:
            target_channel_id = channel.id
            channel_name = f"#{channel.name}"
        elif channel_id:
            try:
                target_channel_id = int(channel_id.strip())
                fetched = interaction.guild.get_channel(target_channel_id)
                channel_name = f"#{fetched.name}" if fetched else f"<#{target_channel_id}>"
            except ValueError:
                await interaction.followup.send("❌ That's not a channel ID, mate.", ephemeral=True)
                return
        else:
            await interaction.followup.send("❌ Which channel, mate? Give me a channel or a channel_id.", ephemeral=True)
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
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="add", description="Add a user as bot admin")
    @app_commands.describe(user="The user to make a bot admin")
    @requires_admin()
    async def add(self, interaction: discord.Interaction, user: discord.Member):
        """Add a bot admin"""
        if not self.admin_manager:
            await interaction.response.send_message(NOT_READY, ephemeral=True)
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
    @requires_admin()
    async def remove(self, interaction: discord.Interaction, user: discord.Member):
        """Remove a bot admin"""
        if not self.admin_manager:
            await interaction.response.send_message(NOT_READY, ephemeral=True)
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
                color=Colors.NEUTRAL
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="list", description="List all bot admins")
    async def list_admins(self, interaction: discord.Interaction):
        """List all bot admins"""
        if not self.admin_manager:
            await interaction.response.send_message(NOT_READY, ephemeral=True)
            return

        admin_ids = self.admin_manager.get_admin_list()

        if not admin_ids:
            embed = discord.Embed(
                title="🔐 Bot Admins",
                description="No bot-specific admins configured.\nDiscord Administrators can use admin commands.",
                color=Colors.NEUTRAL
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
    @requires_admin()
    async def block(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Block unprompted responses"""

        if not self.channel_manager:
            await interaction.response.send_message(NOT_READY, ephemeral=True)
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
                color=Colors.NEUTRAL
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="unblock", description="Allow unprompted responses in a channel")
    @app_commands.describe(channel="The channel to unblock")
    @requires_admin()
    async def unblock(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Allow unprompted responses"""

        if not self.channel_manager:
            await interaction.response.send_message(NOT_READY, ephemeral=True)
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
                color=Colors.NEUTRAL
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name="blocked", description="Show all blocked channels")
    async def blocked(self, interaction: discord.Interaction):
        """Show all blocked channels"""
        if not self.channel_manager:
            await interaction.response.send_message(NOT_READY, ephemeral=True)
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
        app_commands.Choice(name="schedule_announcement - Week matchups when timer starts", value="schedule_announcement"),
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

        guild_id = interaction.guild.id

        if action in ["enable", "disable", "enable_all", "disable_all"]:
            is_admin = (
                interaction.user.guild_permissions.administrator or
                (self.admin_manager and self.admin_manager.is_admin(interaction.user, interaction))
            )
            if not is_admin:
                await interaction.response.send_message(ADMINS_ONLY, ephemeral=True)
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

            # Schedule announcement (week matchups when timer starts/advances)
            sched_on = server_config.get_setting(guild_id, "schedule_announcement", True)
            embed.add_field(
                name="📅 Schedule Announcement",
                value=f"**Week matchups:** {'✅ On' if sched_on else '❌ Off'}\n(Toggle with enable/disable this module)",
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
                await interaction.response.send_message("❌ Enable what, mate? Pick a module.", ephemeral=True)
                return

            if module == "schedule_announcement":
                server_config.set_setting(guild_id, "schedule_announcement", True)
                await server_config.save_to_discord()
                embed = discord.Embed(
                    title="✅ Schedule Announcement On",
                    description="Week matchups (bye week + games) will be sent when the timer starts or advances.",
                    color=Colors.SUCCESS
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            try:
                mod = FeatureModule(module)
            except ValueError:
                await interaction.response.send_message(f"❌ No module called `{module}`, mate.", ephemeral=True)
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
                await interaction.response.send_message("❌ Disable what, mate? Pick a module.", ephemeral=True)
                return

            if module == "schedule_announcement":
                server_config.set_setting(guild_id, "schedule_announcement", False)
                await server_config.save_to_discord()
                embed = discord.Embed(
                    title="❌ Schedule Announcement Off",
                    description="Week matchups will no longer be sent when the timer starts or advances.",
                    color=Colors.WARNING
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            try:
                mod = FeatureModule(module)
            except ValueError:
                await interaction.response.send_message(f"❌ No module called `{module}`, mate.", ephemeral=True)
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
    @requires_admin()
    async def sync_commands(self, interaction: discord.Interaction):
        """Force sync slash commands"""

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
            await oops(interaction, e)

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
                await interaction.response.send_message(ADMINS_ONLY, ephemeral=True)
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

    @admin_group.command(name="zyte", description="Zyte API usage and cost (the paid On3 Cloudflare bypass)")
    @requires_admin()
    async def zyte_usage(self, interaction: discord.Interaction):
        """This session's Zyte requests, plus Zyte's own 30-day stats when the dashboard key is set."""
        await interaction.response.defer(ephemeral=True)

        from .recruiting import get_recruiting_scraper
        scraper, source_name = get_recruiting_scraper(interaction.guild.id)
        if not hasattr(scraper, 'get_zyte_usage'):
            await interaction.followup.send(
                f"This server uses **{source_name}**, which doesn't need Zyte. "
                f"`/recruiting source on3` switches to On3.", ephemeral=True)
            return

        usage = scraper.get_zyte_usage()
        embed = discord.Embed(title="💰 Zyte Usage", color=Colors.PRIMARY,
                              description="Zyte only runs when the free ways past Cloudflare are blocked.")
        if not usage['is_available']:
            embed.add_field(name="⚠️ Not configured", value="Set `ZYTE_API_KEY` on the host to enable it.")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed.add_field(
            name="📊 This session",
            value=(f"**{usage['request_count']}** requests\n"
                   f"~${usage['estimated_cost']:.4f} (${usage['cost_per_1k']:.3f} per 1K)"),
            inline=True)

        result = ((await scraper.get_zyte_usage_from_api(days=30)) or {}).get('results') or [None]
        if result[0]:
            r = result[0]
            embed.add_field(
                name="🌐 Zyte, last 30 days",
                value=(f"**{r.get('request_count', 0):,}** requests\n"
                       f"${float(r.get('cost_microusd_total', 0)) / 1_000_000:.4f} total\n"
                       f"{float(r.get('response_time_sec_avg', 0)):.2f}s avg response"),
                inline=True)
        else:
            embed.add_field(
                name="🌐 Zyte's own stats",
                value="Set `ZYTE_DASHBOARD_API_KEY` and `ZYTE_ORG_ID` (from your dashboard URL, "
                      "`app.zyte.com/o/<org id>`) to see them here.",
                inline=True)
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
    @requires_admin()
    async def cache_management(self, interaction: discord.Interaction, action: str = "stats"):
        """Manage bot cache"""
        await interaction.response.defer(ephemeral=True)

        from ..utils.cache import get_cache
        cache = get_cache()

        if action == "stats":
            # Show cache statistics
            stats = cache.get_stats()

            embed = discord.Embed(
                title="📦 Cache Statistics",
                description="Performance and usage statistics",
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
    @app_commands.describe(action="View current status, or replace the Zyte estimate with Zyte's own figure")
    @app_commands.choices(action=[
        app_commands.Choice(name="View (current)", value="view"),
        app_commands.Choice(name="Reconcile Zyte from Zyte's stats", value="reconcile"),
    ])
    @requires_admin()
    async def budget_status(self, interaction: discord.Interaction, action: str = "view"):
        """View monthly budget status, or reconcile from provider APIs."""
        await interaction.response.defer(ephemeral=True)

        from ..utils.cost_tracker import get_cost_tracker
        from datetime import datetime as dt, date, time

        tracker = get_cost_tracker()

        reconciled = False
        if action == "reconcile":
            # Zyte's Stats API has the real month-to-date cost; replace the bot's estimate with it.
            # (AI spend stays the bot's own count: neither provider has an endpoint a normal API key can read.)
            start = dt.combine(date.today().replace(day=1), time.min)
            try:
                from .recruiting import get_recruiting_scraper
                scraper, _ = get_recruiting_scraper(interaction.guild.id)
                if hasattr(scraper, 'get_zyte_usage_from_api'):
                    results = ((await scraper.get_zyte_usage_from_api(start_time=start, end_time=dt.now())) or {}).get('results')
                    if results:
                        zyte_cost = float(results[0].get('cost_microusd_total', 0)) / 1_000_000
                        await tracker.set_monthly_costs(zyte_cost=zyte_cost)
                        logger.info(f"Budget reconciled: Zyte ${zyte_cost:.4f}")
                        reconciled = True
            except Exception as e:
                logger.warning(f"Zyte reconcile failed: {e}")
            if not reconciled:
                await interaction.followup.send(
                    "⚠️ Couldn't reconcile: needs the On3 source plus `ZYTE_DASHBOARD_API_KEY` and `ZYTE_ORG_ID`. "
                    "Showing stored values.", ephemeral=True)

        status = await tracker.get_budget_status()

        embed = discord.Embed(
            title="💰 Monthly Budget Status",
            description=f"API costs for {datetime.now().strftime('%B %Y')}"
                        + ("\n*Zyte reconciled from Zyte's own stats just now.*" if reconciled else ""),
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

        # Zyte costs (include spend cap if set)
        zyte_percent = status['percentages']['zyte']
        zyte_emoji = "🟢" if zyte_percent < 50 else "🟡" if zyte_percent < 80 else "🔴"
        zyte_value = (f"**${status['costs']['zyte']:.4f}** / ${status['budgets']['zyte']:.2f}\n"
                      f"**{zyte_percent:.1f}%** used • ${status['remaining']['zyte']:.2f} left")
        if getattr(tracker, 'zyte_spend_limit', 0) > 0:
            over_limit = await tracker.is_zyte_over_limit()
            zyte_value += f"\n🛑 Cap: ${tracker.zyte_spend_limit:.0f}" + (" (disabled)" if over_limit else "")
        embed.add_field(
            name=f"{zyte_emoji} Zyte API",
            value=zyte_value,
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
        budget_note = ("Budgets are configured in environment variables:\n"
                       "`AI_MONTHLY_BUDGET`, `ZYTE_MONTHLY_BUDGET`, `TOTAL_MONTHLY_BUDGET`\n"
                       "Alerts trigger at 50%, 80%, 90%, and 100% of budget.")
        if getattr(tracker, 'zyte_spend_limit', 0) > 0:
            budget_note += f"\n**ZYTE_SPEND_LIMIT**=${tracker.zyte_spend_limit:.0f} disables Zyte API when reached."
        if status['costs']['ai'] == 0 and status['costs']['zyte'] == 0:
            budget_note += "\n*Costs are recorded when AI and Zyte are used; use the bot to see numbers update.*"
        embed.add_field(
            name="ℹ️ About Budgets",
            value=budget_note,
            inline=False
        )

        embed.set_footer(text="💡 Resets monthly • Same storage as bot config (owner DM)")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin_group.command(name="digest", description="View or send weekly summary digest")
    @app_commands.describe(
        action="Action to perform"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="📊 View Now", value="view"),
        app_commands.Choice(name="📧 Send to All Admins", value="send")
    ])
    @requires_admin()
    async def weekly_digest(self, interaction: discord.Interaction, action: str = "view"):
        """View or send the weekly digest"""
        await interaction.response.defer(ephemeral=True)

        from ..utils.weekly_digest import get_weekly_digest
        digest = get_weekly_digest(self.bot)

        if action == "view":
            # Show digest to requesting admin only
            await digest.send_manual_digest(interaction)

        elif action == "send":
            await digest.send_digest_to_admins()
            await interaction.followup.send(
                "✅ Weekly digest sent to all admins!",
                ephemeral=True
            )

    @admin_group.command(name="dms", description="Harry's side project")
    @app_commands.describe(action="What to do (default: status)")
    @app_commands.choices(action=[
        app_commands.Choice(name="status", value="status"),
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off"),
        app_commands.Choice(name="send now", value="send"),
        app_commands.Choice(name="restart story", value="reset"),
    ])
    @requires_admin()
    async def dms(self, interaction: discord.Interaction, action: str = "status"):
        """The unhinged DMs (utils/unhinged_dms.py): switch them, check the story, or send one now."""
        from ..utils import unhinged_dms as u
        await interaction.response.defer(ephemeral=True)
        state = await u.load_state()

        if action in ("on", "off"):
            state['enabled'] = action == "on"
            await u.save_state(state)
        elif action == "reset":
            state['sent'] = {}
            await u.save_state(state)
        elif action == "send":
            ai = getattr(self.bot, 'ai_assistant', None)
            results = []
            for uid in sorted(u.UNHINGED_DM_TARGETS):
                try:
                    user = await self.bot.fetch_user(int(uid))
                except discord.HTTPException:
                    results.append(f"`{uid}`: user not found")
                    continue
                ok = await u.send_next(user, self.bot, ai, force=True)
                results.append(f"{user.display_name}: {'sent, copy in your DMs' if ok else 'not sent (their DMs are closed)'}")
            await interaction.followup.send("\n".join(results) or "No targets set.", ephemeral=True)
            return

        state = await u.load_state()
        lines = [f"**{'On' if state['enabled'] else 'Off'}**: {u.UNHINGED_DM_CHANCE:.0%} of their posts, "
                 f"at most one per {u.UNHINGED_DM_COOLDOWN.total_seconds() / 3600:g}h. Copies go to the owner's DMs."]
        for uid in sorted(u.UNHINGED_DM_TARGETS):
            sent = state['sent'].get(uid, 0)
            lines.append(f"<@{uid}>: {sent} sent, next is chapter {u.chapter_for(sent) + 1}/{len(u.CHAPTERS)}")
        await interaction.followup.send("\n".join(lines), ephemeral=True)

    @admin_group.command(name="schedule_reload", description="Reload the league schedule from file (Admin only)")
    @requires_admin()
    async def schedule_reload(self, interaction: discord.Interaction):
        """Reload the schedule from schedule.json without restarting the bot"""

        if not self.schedule_manager:
            await interaction.response.send_message(NOT_READY, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Reload the schedule
        success = self.schedule_manager.reload_schedule()

        if success:
            # Get schedule info
            season = self.schedule_manager.season
            team_count = len(self.schedule_manager.teams)
            teams_list = ", ".join(self.schedule_manager.teams)
            
            embed = discord.Embed(
                title="📅 Schedule Reloaded!",
                description="Successfully reloaded schedule from `data/schedule.json`",
                color=Colors.SUCCESS
            )
            embed.add_field(name="Season", value=f"Season {season}", inline=True)
            embed.add_field(name="User Teams", value=f"{team_count} teams", inline=True)
            embed.add_field(name="Teams", value=teams_list, inline=False)
            embed.set_footer(text="Harry's Schedule Manager 🏈")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"Schedule reloaded by {interaction.user}")
        else:
            await interaction.followup.send(
                "❌ Couldn't reload the schedule, mate. Check the logs.",
                ephemeral=True
            )
            logger.error(f"Schedule reload failed (requested by {interaction.user})")


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = AdminCog(bot)
    await bot.add_cog(cog)
    logger.info("AdminCog loaded")
