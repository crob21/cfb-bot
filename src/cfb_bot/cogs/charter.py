#!/usr/bin/env python3
"""
Charter Cog for CFB 26 League Bot

Provides commands to manage and view the league charter.
Commands:
- /charter lookup - Look up a rule
- /charter link - Get charter URL
- /charter scan - Scan channel for rule changes
- /charter import - Import from the league's Google Doc (admin)
- /charter sync - Sync to Discord persistence
- /charter history - View recent changes
- /charter search - Search charter text
- /charter add - Add new rule (admin)
- /charter update - Update existing rule (admin)
- /charter backups - View backups (admin)
- /charter restore - Restore backup (admin)
"""

import logging
import os
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors
from ..services.checks import check_module_enabled
from ..utils.server_config import server_config, FeatureModule

# The league charter lives in a shared Google Doc; CHARTER_URL overrides it per deployment.
CHARTER_URL = os.getenv(
    'CHARTER_URL',
    'https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit'
)

logger = logging.getLogger('CFB26Bot.Charter')


class CharterCog(commands.Cog):
    """League charter management"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # These will be set by the bot after loading
        self.charter_editor = None
        self.channel_summarizer = None
        self.ai_assistant = None
        self.admin_manager = None
        logger.info("📜 CharterCog initialized")

    def set_dependencies(self, charter_editor, channel_summarizer=None, ai_assistant=None, admin_manager=None):
        """Set dependencies after bot is ready"""
        self.charter_editor = charter_editor
        self.channel_summarizer = channel_summarizer
        self.ai_assistant = ai_assistant
        self.admin_manager = admin_manager

    # Command group
    charter_group = app_commands.Group(
        name="charter",
        description="📜 League charter rules and management"
    )

    @charter_group.command(name="lookup", description="Look up CFB 26 league rules")
    @app_commands.describe(rule_name="Rule keyword or topic to search for")
    async def lookup(self, interaction: discord.Interaction, rule_name: str):
        """Look up a specific league rule"""
        if not await check_module_enabled(interaction, FeatureModule.LEAGUE, server_config):
            return

        await interaction.response.send_message("📋 Looking up rule...", ephemeral=True)

        rule_found = False
        embed = discord.Embed(
            title=f"CFB 26 League Rule: {rule_name.title()}",
            color=Colors.PRIMARY
        )

        # Search through league rules
        if hasattr(self.bot, 'league_data') and 'rules' in self.bot.league_data:
            for category, rules in self.bot.league_data['rules'].items():
                if rule_name.lower() in category.lower():
                    embed.description = rules.get('description', 'Rule information available')
                    if 'topics' in rules:
                        topics_text = '\n'.join([f"• {topic}" for topic in rules['topics'].keys()])
                        embed.add_field(name="Related Topics", value=topics_text, inline=False)
                    rule_found = True
                    break

        if not rule_found:
            embed.description = f"Specific rule '{rule_name}' not found in local data. All CFB 26 league rules are in the official charter."

        embed.add_field(
            name="📖 Full League Charter",
            value=f"[View Complete Rules]({CHARTER_URL})",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    @charter_group.command(name="link", description="Get link to the official league charter")
    async def link(self, interaction: discord.Interaction):
        """Get the official league charter link"""
        if not await check_module_enabled(interaction, FeatureModule.LEAGUE, server_config):
            return

        embed = discord.Embed(
            title="📋 CFB 26 League Charter",
            description="Official league rules, policies, and guidelines",
            color=Colors.PRIMARY
        )

        embed.add_field(
            name="📖 View Full Charter",
            value=f"[Open League Charter]({CHARTER_URL})",
            inline=False
        )

        embed.add_field(
            name="📝 Quick Commands",
            value="Use `/charter lookup`, `/charter search`, or `/charter history` for specific information",
            inline=False
        )

        embed.set_footer(text="CFB 26 League Bot - Always check the charter for complete rules")
        await interaction.response.send_message(embed=embed)

    @charter_group.command(name="scan", description="Scan a channel for rule changes and votes")
    @app_commands.describe(
        channel="Channel to scan (e.g., #offseason-voting)",
        hours="Hours of history to scan (default: 168 = 1 week)"
    )
    async def scan(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        hours: int = 168
    ):
        """Scan a channel for rule changes"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can scan for rule changes!", ephemeral=True)
            return

        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        if not self.channel_summarizer:
            await interaction.response.send_message("❌ Channel summarizer not available", ephemeral=True)
            return

        if hours < 24:
            await interaction.response.send_message("❌ Need at least 24 hours of history!", ephemeral=True)
            return
        if hours > 720:
            await interaction.response.send_message("❌ Max 720 hours (30 days)", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            messages = await self.channel_summarizer.fetch_messages(channel, hours=hours, limit=500)

            if not messages:
                await interaction.followup.send(f"❌ No messages found in {channel.mention} in the last {hours} hours")
                return

            # Format messages
            formatted_messages = []
            poll_count = 0
            for msg in messages:
                if msg.content:
                    formatted_messages.append(f"[{msg.author.display_name}]: {msg.content}")

                try:
                    if hasattr(msg, 'poll') and msg.poll:
                        poll_count += 1
                        poll = msg.poll
                        poll_text = f"[{msg.author.display_name}] POLL: {poll.question}"
                        if hasattr(poll, 'answers') and poll.answers:
                            for answer in poll.answers:
                                vote_count = getattr(answer, 'vote_count', 0)
                                answer_text = getattr(answer, 'text', str(answer))
                                poll_text += f"\n  - {answer_text} ({vote_count} votes)"
                        if getattr(poll, 'is_finalized', False):
                            total = getattr(poll, 'total_votes', 0)
                            poll_text += f"\n  STATUS: CLOSED (Total: {total} votes)"
                        formatted_messages.append(poll_text)
                except Exception:
                    pass

            # Find rule changes
            rule_changes = await self.charter_editor.find_rule_changes_in_messages(
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

            embed = discord.Embed(
                title=f"📜 Rule Changes Found in #{channel.name}",
                description=f"Found **{len(rule_changes)}** rule changes/votes",
                color=Colors.PRIMARY
            )

            passed_rules = []
            for i, rule in enumerate(rule_changes[:10], 1):
                status = rule.get("status", "unknown")
                status_emoji = {"passed": "✅", "failed": "❌", "proposed": "📋", "decided": "✅"}.get(status, "❓")

                votes = ""
                if rule.get("votes_for") is not None:
                    votes = f" ({rule.get('votes_for', 0)}-{rule.get('votes_against', 0)})"

                rule_text = rule.get("rule", "Unknown rule")
                context = rule.get("context", "")
                field_value = f"📝 {rule_text}"
                if context and context.lower() != rule_text.lower():
                    field_value += f"\n> _{context[:200]}_"

                embed.add_field(name=f"{i}. {status_emoji} {status.upper()}{votes}", value=field_value[:500], inline=False)

                if status in ["passed", "decided"]:
                    passed_rules.append(rule)

            embed.set_footer(text=f"Scanned {len(messages)} messages ({poll_count} polls)")

            if passed_rules:
                embed.add_field(
                    name="🔧 Update Charter?",
                    value=f"Found **{len(passed_rules)}** passed rules.",
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(f"❌ Error scanning rules: {e}", exc_info=True)
            await interaction.followup.send(f"❌ Error scanning for rules: {str(e)}")

    @charter_group.command(name="import", description="Import the charter from its Google Doc (Admin only)")
    @app_commands.describe(url="Charter document link (defaults to the league charter doc)")
    async def import_charter(self, interaction: discord.Interaction, url: Optional[str] = None):
        """Replace the stored charter with the text of the league's shared doc."""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can import the charter!", ephemeral=True)
            return

        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        source = url or CHARTER_URL
        ok, detail = await self.charter_editor.import_from_url(
            source, user_id=interaction.user.id, user_name=interaction.user.display_name
        )

        if not ok:
            await interaction.followup.send(f"❌ {detail}", ephemeral=True)
            return

        embed = discord.Embed(
            title="📜 Charter Imported",
            description=f"{detail}\n\nHarry now answers from the current charter.",
            color=Colors.SUCCESS,
        )
        embed.add_field(name="Source", value=source, inline=False)
        embed.set_footer(text="Backed up the previous version and saved to Discord")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @charter_group.command(name="sync", description="Sync charter to Discord (Admin only)")
    async def sync(self, interaction: discord.Interaction):
        """Manually sync the charter"""
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Only admins can sync the charter!", ephemeral=True)
            return

        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            await self.charter_editor.save_to_discord()
            embed = discord.Embed(
                title="✅ Charter Synced!",
                description="Charter has been saved to Discord for persistence.",
                color=Colors.SUCCESS
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error syncing: {str(e)}", ephemeral=True)

    @charter_group.command(name="history", description="View recent charter changes")
    async def history(self, interaction: discord.Interaction):
        """View recent charter update history"""
        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        changes = self.charter_editor.get_recent_changes(limit=10)

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

        for i, change in enumerate(changes[:5], 1):
            timestamp = change.get("timestamp", "Unknown")
            if isinstance(timestamp, str) and "T" in timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    timestamp = dt.strftime("%b %d, %Y %I:%M %p")
                except (ValueError, TypeError):
                    pass

            user_name = change.get("user_name", "Unknown")
            description = change.get("description", "No description")

            embed.add_field(
                name=f"{i}. {timestamp}",
                value=f"**By:** {user_name}\n**Change:** {description[:100]}{'...' if len(description) > 100 else ''}",
                inline=False
            )

        embed.set_footer(text="Use @Harry to update charter rules interactively 🏈")
        await interaction.response.send_message(embed=embed)

    @charter_group.command(name="search", description="Search the official league charter")
    @app_commands.describe(search_term="Text to search for in the charter")
    async def search(self, interaction: discord.Interaction, search_term: str):
        """Search for specific terms in the league charter"""
        await interaction.response.send_message("🔍 Searching...", ephemeral=True)

        embed = discord.Embed(
            title=f"🔍 Search Results: '{search_term}'",
            color=Colors.WARNING
        )

        # Search charter if available
        if self.charter_editor:
            results = self.charter_editor.search_charter(search_term)
            if results:
                for i, result in enumerate(results[:5], 1):
                    embed.add_field(
                        name=f"{i}. {result.get('section', 'Section')}",
                        value=result.get('excerpt', 'No excerpt')[:200],
                        inline=False
                    )
                embed.color = Colors.SUCCESS
            else:
                embed.description = f"No results found for '{search_term}' in the charter."
        else:
            embed.description = "Charter search not available. View the full charter instead."

        embed.add_field(
            name="📖 Full Charter",
            value=f"[Open League Charter]({CHARTER_URL})",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    @charter_group.command(name="add", description="Add a new rule to the charter (Admin only)")
    @app_commands.describe(
        section_title="Title for the new rule section",
        rule_content="The rule text content",
        position="Where to add: 'end' or 'start' (default: end)"
    )
    async def add(
        self,
        interaction: discord.Interaction,
        section_title: str,
        rule_content: str,
        position: str = "end"
    ):
        """Add a new rule section"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions!", ephemeral=True)
            return

        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            formatted_content = await self.charter_editor.format_rule_with_ai(rule_content)
            result = await self.charter_editor.add_rule_section(
                section_title=section_title,
                section_content=formatted_content or rule_content,
                position=position
            )

            if result['success']:
                embed = discord.Embed(
                    title="✅ Rule Added Successfully!",
                    description=f"**Section**: {section_title}\n**Position**: {position}",
                    color=Colors.SUCCESS
                )
                embed.add_field(name="📝 Content", value=(formatted_content or rule_content)[:1000], inline=False)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Failed: {result['message']}", ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error adding rule: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @charter_group.command(name="update", description="Update an existing rule (Admin only)")
    @app_commands.describe(
        section_identifier="Section title or number to update",
        new_content="New content for the section"
    )
    async def update(
        self,
        interaction: discord.Interaction,
        section_identifier: str,
        new_content: str
    ):
        """Update an existing rule section"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions!", ephemeral=True)
            return

        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            formatted_content = await self.charter_editor.format_rule_with_ai(new_content)
            result = await self.charter_editor.update_rule_section(
                section_identifier=section_identifier,
                new_content=formatted_content or new_content
            )

            if result['success']:
                embed = discord.Embed(
                    title="✅ Rule Updated!",
                    description=f"**Section**: {section_identifier}",
                    color=Colors.SUCCESS
                )
                embed.add_field(name="📝 New Content", value=(formatted_content or new_content)[:1000], inline=False)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f"❌ Failed: {result['message']}", ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error updating rule: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @charter_group.command(name="backups", description="View available backups (Admin only)")
    async def backups(self, interaction: discord.Interaction):
        """View available charter backups"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions!", ephemeral=True)
            return

        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        try:
            backups = self.charter_editor.get_backup_list()

            if not backups:
                embed = discord.Embed(
                    title="📋 Charter Backups",
                    description="No backups found.",
                    color=0x808080
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="📋 Charter Backups",
                description=f"Found **{len(backups)}** backup{'s' if len(backups) > 1 else ''}!",
                color=Colors.SUCCESS
            )

            for backup in backups[:10]:
                timestamp = backup['modified'].strftime('%Y-%m-%d %I:%M %p')
                size_kb = backup['size'] / 1024
                embed.add_field(
                    name=f"📄 {backup['filename']}",
                    value=f"**Date**: {timestamp}\n**Size**: {size_kb:.1f} KB",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error viewing backups: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)

    @charter_group.command(name="restore", description="Restore from backup (Admin only)")
    @app_commands.describe(backup_filename="Name of the backup file to restore")
    async def restore(self, interaction: discord.Interaction, backup_filename: str):
        """Restore the charter from a backup"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions!", ephemeral=True)
            return

        if not self.charter_editor:
            await interaction.response.send_message("❌ Charter editor not available", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            success = self.charter_editor.restore_backup(backup_filename)

            if success:
                embed = discord.Embed(
                    title="✅ Charter Restored!",
                    description=f"Restored from: **{backup_filename}**",
                    color=Colors.SUCCESS
                )
                await interaction.followup.send(embed=embed)
                logger.info(f"✅ Charter restored by {interaction.user} from {backup_filename}")
            else:
                await interaction.followup.send("❌ Failed to restore. Check the filename.", ephemeral=True)

        except Exception as e:
            logger.error(f"❌ Error restoring backup: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = CharterCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ CharterCog loaded")

