#!/usr/bin/env python3
"""
Weekly digest system - sends summary reports to admins
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import discord

from .storage import get_storage
from .cache import get_cache

logger = logging.getLogger('CFB26Bot.WeeklyDigest')


class WeeklyDigest:
    """Generate and send weekly summary reports"""

    def __init__(self, bot):
        self.bot = bot
        self._storage = get_storage()

    async def should_send_digest(self) -> bool:
        """Check if it's time to send the weekly digest"""
        data = await self._storage.load("weekly_digest", "schedule") or {}
        last_sent = data.get('last_sent')

        if not last_sent:
            return True  # Never sent before

        last_sent_date = datetime.fromisoformat(last_sent)
        days_since = (datetime.now() - last_sent_date).days

        # Send every 7 days
        return days_since >= 7

    async def mark_digest_sent(self):
        """Mark the digest as sent"""
        await self._storage.save("weekly_digest", "schedule", {
            'last_sent': datetime.now().isoformat()
        })

    async def generate_digest(self) -> discord.Embed:
        """Generate the weekly digest embed"""
        # Get data from the past 7 days
        cache = get_cache()
        cache_stats = cache.get_stats()

        # Get cost data
        from .cost_tracker import get_cost_tracker
        tracker = get_cost_tracker()
        costs = await tracker.get_monthly_costs()
        budget_status = await tracker.get_budget_status()

        # Create embed
        embed = discord.Embed(
            title="📊 Weekly Bot Digest",
            description=f"Summary for week of {(datetime.now() - timedelta(days=7)).strftime('%B %d')} - {datetime.now().strftime('%B %d, %Y')}",
            color=discord.Color.blue()
        )

        # Cache performance
        if cache_stats['total_requests'] > 0:
            savings = cache_stats['hits'] * 0.00023
            embed.add_field(
                name="💾 Cache Performance",
                value=f"**Hit Rate:** {cache_stats['hit_rate']:.1f}%\n"
                      f"**Hits:** {cache_stats['hits']:,}\n"
                      f"**Savings:** ~${savings:.4f}",
                inline=True
            )

        # Cost summary
        embed.add_field(
            name="💰 Costs This Month",
            value=f"**AI:** ${costs['ai']:.4f}\n"
                  f"**Zyte:** ${costs['zyte']:.4f}\n"
                  f"**Total:** ${costs['total']:.4f}",
            inline=True
        )

        # Budget status
        total_percent = budget_status['percentages']['total']
        status_emoji = "🟢" if total_percent < 50 else "🟡" if total_percent < 80 else "🔴"
        embed.add_field(
            name=f"{status_emoji} Budget Status",
            value=f"**{total_percent:.1f}%** of monthly budget used\n"
                  f"**${budget_status['remaining']['total']:.2f}** remaining",
            inline=True
        )

        # AI usage (if available)
        if hasattr(self.bot, 'ai_assistant') and self.bot.ai_assistant:
            ai_stats = self.bot.ai_assistant.get_token_usage()
            if ai_stats['total_requests'] > 0:
                embed.add_field(
                    name="🤖 AI Usage",
                    value=f"**Requests:** {ai_stats['total_requests']:,}\n"
                          f"**Tokens:** {ai_stats['total_tokens']:,}\n"
                          f"**Cost:** ${ai_stats['total_cost']:.4f}",
                    inline=True
                )

        # Add timestamp
        embed.set_footer(text=f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        embed.timestamp = datetime.now()

        return embed

    async def send_digest_to_admins(self):
        """Send the weekly digest to all bot admins"""
        try:
            embed = await self.generate_digest()

            # Get admin IDs from environment variable or bot owner
            import os
            admin_ids_str = os.getenv('BOT_ADMIN_IDS', '')
            admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]

            # If no admin IDs configured, send to bot owner
            if not admin_ids:
                try:
                    app_info = await self.bot.application_info()
                    admin_ids = [app_info.owner.id]
                    logger.info("📧 No BOT_ADMIN_IDS configured, sending to bot owner")
                except Exception as e:
                    logger.error(f"❌ Could not get bot owner: {e}")
                    return

            sent_count = 0

            for admin_id in admin_ids:
                try:
                    user = await self.bot.fetch_user(admin_id)
                    await user.send(embed=embed)
                    sent_count += 1
                    logger.info(f"📧 Sent weekly digest to admin {admin_id}")
                except discord.Forbidden:
                    logger.warning(f"⚠️ Cannot DM admin {admin_id} (DMs disabled)")
                except discord.NotFound:
                    logger.warning(f"⚠️ Admin {admin_id} not found")
                except Exception as e:
                    logger.error(f"❌ Error sending digest to {admin_id}: {e}")

            logger.info(f"✅ Weekly digest sent to {sent_count} admin(s)")

            # Mark as sent
            await self.mark_digest_sent()

        except Exception as e:
            logger.error(f"❌ Error generating/sending weekly digest: {e}")

    async def send_manual_digest(self, interaction: discord.Interaction):
        """Send digest manually via command"""
        try:
            embed = await self.generate_digest()
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"❌ Error generating manual digest: {e}")
            await interaction.followup.send(
                f"❌ Error generating digest: {str(e)}",
                ephemeral=True
            )


# Global instance
_digest_instance: Optional[WeeklyDigest] = None


def get_weekly_digest(bot) -> WeeklyDigest:
    """Get the global weekly digest instance"""
    global _digest_instance

    if _digest_instance is None:
        _digest_instance = WeeklyDigest(bot)
        logger.info("📊 Weekly digest initialized")

    return _digest_instance
