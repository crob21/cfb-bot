#!/usr/bin/env python3
"""
Core Cog for CFB 26 League Bot

Provides always-available commands that don't require module checks.
Commands:
- /help - Show all available commands
- /version - Show current bot version
- /changelog - View version history
- /whats_new - See latest features
- /tokens - Show AI token usage
"""

import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors
from ..utils.server_config import server_config, FeatureModule
from ..utils.version_manager import VersionManager

logger = logging.getLogger('CFB26Bot.Core')


class CoreCog(commands.Cog):
    """Always-available core commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.version_manager = VersionManager()
        self.ai_assistant = None
        self.AI_AVAILABLE = False
        logger.info("🏈 CoreCog initialized")

    def set_dependencies(self, ai_assistant=None, AI_AVAILABLE=False):
        """Set dependencies after bot is ready"""
        self.ai_assistant = ai_assistant
        self.AI_AVAILABLE = AI_AVAILABLE

    @app_commands.command(name="help", description="Show all available commands")
    async def help_cmd(self, interaction: discord.Interaction):
        """Show help information - filtered to show only enabled modules"""
        current_version = self.version_manager.get_current_version()

        # Get enabled modules for this server
        guild_id = interaction.guild.id if interaction.guild else 0
        enabled_modules = server_config.get_enabled_modules(guild_id) if guild_id else []

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
                    "`portal` - Transfer portal player\n"
                    "`top` - Top recruits by pos/state\n"
                    "`class` - Team's recruiting class\n"
                    "`commits` - List team's commits\n"
                    "`rankings` - Top 25 team rankings\n"
                    "`source` - Switch On3/247"
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
                    "`players` - Bulk player lookup\n"
                    "`rankings` - AP/Coaches/CFP polls\n"
                    "`schedule` - Team's schedule\n"
                    "`matchup` - Head-to-head history\n"
                    "`transfers` - Portal activity\n"
                    "`draft` - NFL draft picks\n"
                    "`betting` - Game lines/odds\n"
                    "`ratings` - SP+, SRS, Elo"
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
                    "**Season:** `week`, `weeks`, `games`, `find_game`, `byes`\n"
                    "**Timer:** `timer`, `timer_status`, `timer_stop`\n"
                    "**Staff:** `staff`, `pick_commish`\n"
                    "**Admin:** `set_week`, `set_owner`, `set_commish`, `timer_channel`"
                ),
                inline=True
            )
            embed.add_field(
                name="📜 `/charter`",
                value=(
                    "**View:** `lookup`, `search`, `link`, `history`\n"
                    "**Admin:** `scan`, `add`, `update`, `sync`, `backups`, `restore`"
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

        # Admin Group - Always available to admins (but we show it here for reference)
        # Only show if user is admin to avoid clutter? No, prompt asked for ALL commands.
        embed.add_field(
            name="🔧 `/admin` (Restricted)",
            value=(
                "**Config:** `config`, `channels`, `set_channel`\n"
                "**Stats:** `ai`, `zyte`, `cache`, `budget`, `digest`\n"
                "**Manage:** `add`, `remove`, `list` (Bot Admins)\n"
                "**Debug:** `debug`, `sync`"
            ),
            inline=False
        )

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

        # Show disabled modules note
        if disabled_modules:
            embed.add_field(
                name="ℹ️ Additional Features",
                value=f"_{', '.join(disabled_modules)}_ disabled on this server.\nAsk an admin about `/admin config`",
                inline=False
            )

        embed.set_footer(text="Harry 🏈 | Type /group to see subcommands")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="version", description="Show current bot version")
    async def version(self, interaction: discord.Interaction):
        """Show the current version"""
        current_ver = self.version_manager.get_current_version()
        version_info = self.version_manager.get_latest_version_info()

        embed = discord.Embed(
            title=f"🏈 Harry v{current_ver}",
            description=f"{version_info.get('emoji', '🎉')} {version_info.get('title', 'Current Version')}",
            color=Colors.SUCCESS
        )

        embed.add_field(name="📅 Release Date", value=version_info.get('date', 'Unknown'), inline=True)
        embed.add_field(name="📊 Total Versions", value=str(len(self.version_manager.get_all_versions())), inline=True)
        embed.add_field(name="📖 View Details", value="Use `/changelog` to see all changes!", inline=False)

        embed.set_footer(text="Harry's CFB Bot 🏈")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="changelog", description="View version changelog")
    @app_commands.describe(version="Specific version to view (e.g., '1.1.0')")
    async def changelog(self, interaction: discord.Interaction, version: Optional[str] = None):
        """View the changelog"""
        if not version:
            embed = discord.Embed(
                title="📜 Harry's Version History",
                description="Here's all the updates!",
                color=Colors.SUCCESS
            )

            summary = self.version_manager.get_version_summary()
            if len(summary) > 1000:
                summary = summary[:997] + "..."

            embed.add_field(name="📋 All Versions", value=summary, inline=False)
            embed.add_field(name="🔍 View Specific Version", value="Use `/changelog 1.1.0` to see details!", inline=False)
            embed.set_footer(text=f"Current Version: v{self.version_manager.get_current_version()}")
            await interaction.response.send_message(embed=embed)
            return

        # Show specific version details
        embed_data = self.version_manager.format_version_embed_data(version)

        if not embed_data:
            embed = discord.Embed(
                title="❌ Version Not Found",
                description=f"No info about version {version}!\nUse `/changelog` to see all versions.",
                color=Colors.ERROR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title=embed_data['title'],
            description=embed_data['description'],
            color=Colors.SUCCESS
        )

        for field in embed_data['fields']:
            embed.add_field(name=field['name'], value=field['value'], inline=field['inline'])

        current_ver = self.version_manager.get_current_version()
        is_current = version == current_ver
        embed.set_footer(text=f"Version v{version}" + (" (Current)" if is_current else ""))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="whats_new", description="See what's new with Harry!")
    async def whats_new(self, interaction: discord.Interaction):
        """Show the latest features"""
        embed = discord.Embed(
            title="🎉 What's New with Harry! 🎉",
            description="Look at all the brilliant new stuff!",
            color=Colors.SUCCESS
        )

        latest_info = self.version_manager.get_latest_version_info()
        current_ver = self.version_manager.get_current_version()

        embed.add_field(
            name=f"v{current_ver} - {latest_info.get('title', 'Latest Updates')}",
            value=latest_info.get('date', 'Recent'),
            inline=False
        )

        changes = latest_info.get('changes', [])
        if changes:
            changes_text = "\n".join([f"• {c}" for c in changes[:10]])
            if len(changes_text) > 1000:
                changes_text = changes_text[:997] + "..."
            embed.add_field(name="📝 Changes", value=changes_text, inline=False)

        embed.add_field(
            name="📖 Full History",
            value="Use `/changelog` to see all version history!",
            inline=False
        )

        embed.set_footer(text="Harry's CFB Bot 🏈")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tokens", description="Show AI token usage statistics")
    async def tokens(self, interaction: discord.Interaction):
        """Show AI token usage"""
        if self.AI_AVAILABLE and self.ai_assistant:
            stats = self.ai_assistant.get_token_usage()
            embed = discord.Embed(
                title="🔢 AI Token Usage Statistics",
                color=Colors.SUCCESS
            )

            embed.add_field(
                name="📊 Usage Summary",
                value=(
                    f"**Total Requests:** {stats['total_requests']}\n"
                    f"**OpenAI Tokens:** {stats['openai_tokens']:,}\n"
                    f"**Anthropic Tokens:** {stats['anthropic_tokens']:,}\n"
                    f"**Total Tokens:** {stats['total_tokens']:,}"
                ),
                inline=False
            )

            if stats['total_requests'] > 0:
                avg_tokens = stats['total_tokens'] / stats['total_requests']
                embed.add_field(name="📈 Averages", value=f"**Avg per Request:** {avg_tokens:.1f}", inline=False)

            openai_cost = stats['openai_tokens'] * 0.000002
            embed.add_field(
                name="💰 Estimated Costs",
                value=f"**OpenAI Cost:** ~${openai_cost:.4f}",
                inline=False
            )

            embed.set_footer(text="Token usage since bot startup")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ AI integration not available")


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = CoreCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ CoreCog loaded")
