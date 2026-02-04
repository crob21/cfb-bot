#!/usr/bin/env python3
"""
Fun Cog for CFB 26 League Bot

Secret admin commands for... creative moderation.
Commands:
- /fun target - Start trolling a user (admin only, silent)
- /fun untarget - Stop trolling a user (admin only)
- /fun timeout - Set timeout between troll messages (admin only)
- /fun status - Check who's being trolled (admin only)
"""

import logging
import time
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import Colors

logger = logging.getLogger('CFB26Bot.Fun')


class FunCog(commands.Cog):
    """Fun & trolling commands (admin only)"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.admin_manager = None

        # Tracking structure: {user_id: {'timeout': minutes, 'last_triggered': timestamp}}
        self.targets: Dict[int, Dict] = {}

        logger.info("🎭 FunCog initialized")

    def set_dependencies(self, admin_manager=None):
        """Set dependencies after bot is ready"""
        self.admin_manager = admin_manager

    # Command group
    fun_group = app_commands.Group(
        name="fun",
        description="🎭 Secret fun commands (Admin only)"
    )

    @fun_group.command(name="target", description="🎯 Start trolling a user (Admin only)")
    @app_commands.describe(
        user="The unfortunate soul to target",
        timeout="Minutes between messages (default: 30)"
    )
    async def target(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        timeout: int = 30
    ):
        """Enable trolling for a specific user"""
        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        # Validation
        if timeout < 1:
            await interaction.response.send_message("❌ Timeout must be at least 1 minute!", ephemeral=True)
            return

        if timeout > 1440:  # 24 hours
            await interaction.response.send_message("❌ Timeout can't exceed 1440 minutes (24 hours)!", ephemeral=True)
            return

        if user.bot:
            await interaction.response.send_message("❌ Can't target bots, mate!", ephemeral=True)
            return

        # Don't target yourself (but allow it for testing)
        # if user.id == interaction.user.id:
        #     await interaction.response.send_message("❌ Don't target yourself, ya muppet!", ephemeral=True)
        #     return

        # Add to targets
        self.targets[user.id] = {
            'timeout': timeout,
            'last_triggered': 0,  # Allow immediate first message
            'target_name': user.display_name,
            'enabled_by': interaction.user.id,
            'enabled_by_name': interaction.user.display_name
        }

        logger.info(f"🎯 {interaction.user.display_name} enabled trolling for {user.display_name} (timeout: {timeout}m)")

        embed = discord.Embed(
            title="🎯 Target Acquired",
            description=f"**{user.display_name}** is now being trolled!\n\n"
                       f"⏱️ **Timeout:** {timeout} minutes\n"
                       f"🤫 **Silent mode:** They won't know it's intentional\n\n"
                       f"Harry will respond to their messages with creative greetings.",
            color=0xff6b6b
        )
        embed.set_footer(text="Use /fun untarget to stop | /fun status to check")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @fun_group.command(name="untarget", description="🛑 Stop trolling a user (Admin only)")
    @app_commands.describe(user="The user to stop trolling")
    async def untarget(self, interaction: discord.Interaction, user: discord.Member):
        """Disable trolling for a specific user"""
        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        # Remove from targets
        if user.id in self.targets:
            target_info = self.targets.pop(user.id)
            logger.info(f"🛑 {interaction.user.display_name} disabled trolling for {user.display_name}")

            embed = discord.Embed(
                title="🛑 Target Released",
                description=f"**{user.display_name}** is no longer being trolled.\n\n"
                           f"They can live in peace... for now.",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"❌ {user.display_name} isn't being targeted!",
                ephemeral=True
            )

    @fun_group.command(name="timeout", description="⏱️ Adjust timeout for a user (Admin only)")
    @app_commands.describe(
        user="The targeted user",
        timeout="New timeout in minutes"
    )
    async def set_timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        timeout: int
    ):
        """Adjust the timeout for a targeted user"""
        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        # Validation
        if timeout < 1 or timeout > 1440:
            await interaction.response.send_message(
                "❌ Timeout must be between 1 and 1440 minutes (24 hours)!",
                ephemeral=True
            )
            return

        # Update timeout
        if user.id in self.targets:
            old_timeout = self.targets[user.id]['timeout']
            self.targets[user.id]['timeout'] = timeout

            logger.info(f"⏱️ {interaction.user.display_name} changed timeout for {user.display_name}: {old_timeout}m → {timeout}m")

            embed = discord.Embed(
                title="⏱️ Timeout Adjusted",
                description=f"**{user.display_name}**'s timeout updated:\n\n"
                           f"**{old_timeout} minutes** → **{timeout} minutes**",
                color=Colors.PRIMARY
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                f"❌ {user.display_name} isn't being targeted! Use `/fun target` first.",
                ephemeral=True
            )

    @fun_group.command(name="status", description="📋 Check trolling status (Admin only)")
    async def status(self, interaction: discord.Interaction):
        """View all currently targeted users"""
        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        if not self.targets:
            embed = discord.Embed(
                title="📋 Trolling Status",
                description="No active targets.\n\nUse `/fun target` to start trolling someone!",
                color=Colors.WARNING
            )
        else:
            embed = discord.Embed(
                title="📋 Active Targets",
                description=f"Currently trolling **{len(self.targets)}** user(s):",
                color=0xff6b6b
            )
            
            for user_id, info in self.targets.items():
                # Calculate time since last message
                time_since = int((time.time() - info['last_triggered']) / 60)
                time_until = max(0, info['timeout'] - time_since)
                
                status_text = (
                    f"⏱️ **Timeout:** {info['timeout']} minutes\n"
                    f"🕐 **Last triggered:** {time_since}m ago\n"
                    f"⏳ **Next available:** {time_until}m\n"
                    f"👤 **Enabled by:** {info.get('enabled_by_name', 'Unknown')}"
                )
                
                embed.add_field(
                    name=f"🎯 {info['target_name']}",
                    value=status_text,
                    inline=False
                )
        
        embed.set_footer(text="This is completely hidden from targets | Harry's Secret Trolling System")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @fun_group.command(name="target_all", description="🎯 Start trolling multiple users at once (Admin only)")
    @app_commands.describe(
        users="Users to target (space-separated mentions: @user1 @user2 @user3)",
        timeout="Minutes between messages (default: 30)"
    )
    async def target_all(
        self,
        interaction: discord.Interaction,
        users: str,
        timeout: int = 30
    ):
        """Enable trolling for multiple users at once"""
        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        # Validation
        if timeout < 1 or timeout > 1440:
            await interaction.response.send_message(
                "❌ Timeout must be between 1 and 1440 minutes (24 hours)!",
                ephemeral=True
            )
            return

        # Parse mentions from the string
        import re
        mention_pattern = r'<@!?(\d+)>'
        user_ids = re.findall(mention_pattern, users)
        
        if not user_ids:
            await interaction.response.send_message(
                "❌ No valid user mentions found!\n\n"
                "**Usage:** `/fun target_all users:@user1 @user2 @user3 timeout:30`",
                ephemeral=True
            )
            return

        # Get guild members
        if not interaction.guild:
            await interaction.response.send_message("❌ This command only works in servers!", ephemeral=True)
            return

        # Add all mentioned users
        added = []
        skipped = []
        
        for user_id_str in user_ids:
            user_id = int(user_id_str)
            
            # Try to get member
            try:
                member = await interaction.guild.fetch_member(user_id)
            except:
                skipped.append(f"<@{user_id}> (not found)")
                continue
            
            # Skip bots
            if member.bot:
                skipped.append(f"{member.display_name} (bot)")
                continue
            
            # Add to targets
            self.targets[user_id] = {
                'timeout': timeout,
                'last_triggered': 0,
                'target_name': member.display_name,
                'enabled_by': interaction.user.id,
                'enabled_by_name': interaction.user.display_name
            }
            added.append(member.display_name)
        
        # Build response
        if not added:
            await interaction.response.send_message(
                "❌ No users were added!\n\n" + 
                (f"**Skipped:** {', '.join(skipped)}" if skipped else ""),
                ephemeral=True
            )
            return
        
        logger.info(f"🎯 {interaction.user.display_name} enabled trolling for {len(added)} users (timeout: {timeout}m)")
        
        embed = discord.Embed(
            title="🎯 Multiple Targets Acquired",
            description=f"**{len(added)} users** are now being trolled!\n\n"
                       f"⏱️ **Timeout:** {timeout} minutes\n"
                       f"🤫 **Silent mode:** They won't know it's intentional",
            color=0xff6b6b
        )
        
        embed.add_field(
            name="✅ Added",
            value="\n".join([f"• {name}" for name in added]),
            inline=False
        )
        
        if skipped:
            embed.add_field(
                name="⏭️ Skipped",
                value="\n".join([f"• {name}" for name in skipped]),
                inline=False
            )
        
        embed.set_footer(text="Use /fun untarget to stop | /fun status to check")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @fun_group.command(name="untarget_all", description="🛑 Stop trolling ALL users (Admin only)")
    async def untarget_all(self, interaction: discord.Interaction):
        """Disable trolling for all users at once"""
        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        if not self.targets:
            await interaction.response.send_message("❌ No active targets to remove!", ephemeral=True)
            return

        count = len(self.targets)
        target_names = [info['target_name'] for info in self.targets.values()]
        self.targets.clear()
        
        logger.info(f"🛑 {interaction.user.display_name} disabled trolling for all {count} users")
        
        embed = discord.Embed(
            title="🛑 All Targets Released",
            description=f"Removed **{count} users** from trolling list.\n\n"
                       f"They can all live in peace... for now.",
            color=0x00ff00
        )
        
        if len(target_names) <= 10:
            embed.add_field(
                name="Released Users",
                value="\n".join([f"• {name}" for name in target_names]),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages from targeted users"""
        # Ignore bots
        if message.author.bot:
            return

        # Check if user is targeted
        if message.author.id not in self.targets:
            return

        # Get target info
        target_info = self.targets[message.author.id]

        # Check timeout
        current_time = time.time()
        time_since_last = current_time - target_info['last_triggered']
        timeout_seconds = target_info['timeout'] * 60

        if time_since_last < timeout_seconds:
            # Still in timeout period
            return

        # Update last triggered time
        target_info['last_triggered'] = current_time

        # Send the troll message
        try:
            troll_messages = [
                f"Fuck you {message.author.mention} 🖕",
                f"Oi {message.author.mention}, fuck you! 🖕",
                f"Hey {message.author.mention}... fuck you 🖕",
                f"{message.author.mention} Fuck. You. 🖕",
                f"Fuck you specifically, {message.author.mention} 🖕",
                f"Oh look, it's {message.author.mention}. Fuck you! 🖕",
            ]

            # Pick a random message
            import random
            troll_message = random.choice(troll_messages)

            await message.channel.send(troll_message)

            logger.info(f"🎭 Trolled {message.author.display_name} in #{message.channel.name}")

        except Exception as e:
            logger.error(f"❌ Failed to send troll message: {e}")


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = FunCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ FunCog loaded")
