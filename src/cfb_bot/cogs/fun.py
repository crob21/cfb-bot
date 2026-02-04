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
import random
import re
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

        # Tracking structure: {user_id: {'timeout': minutes, 'last_triggered': timestamp, 'engage': bool}}
        self.targets: Dict[int, Dict] = {}

        # Track Harry's troll messages for reply detection: {message_id: user_id}
        self.troll_messages: Dict[int, int] = {}

        logger.info("🎭 FunCog initialized")

    def set_dependencies(self, admin_manager=None, ai_assistant=None):
        """Set dependencies after bot is ready"""
        self.admin_manager = admin_manager
        self.ai_assistant = ai_assistant

    # Command group
    fun_group = app_commands.Group(
        name="fun",
        description="🎭 Secret fun commands (Admin only)"
    )

    @fun_group.command(name="target", description="🎯 Start trolling a user (Admin only)")
    @app_commands.describe(
        user="The unfortunate soul to target",
        timeout="Minutes between messages (default: 30)",
        engage="Should Harry argue back if they respond? (default: False)"
    )
    async def target(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        timeout: int = 30,
        engage: bool = False
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

        # Add to targets
        self.targets[user.id] = {
            'timeout': timeout,
            'last_triggered': 0,  # Allow immediate first message
            'target_name': user.display_name,
            'enabled_by': interaction.user.id,
            'enabled_by_name': interaction.user.display_name,
            'engage': engage,
            'argument_count': 0  # Track how many times Harry has argued back
        }

        logger.info(f"🎯 {interaction.user.display_name} enabled trolling for {user.display_name} (timeout: {timeout}m, engage: {engage})")

        engage_text = "🔥 **Engage mode: ON** - Harry will argue if they respond!" if engage else "💤 **Engage mode: OFF**"

        embed = discord.Embed(
            title="🎯 Target Acquired",
            description=f"**{user.display_name}** is now being trolled!\n\n"
                       f"⏱️ **Timeout:** {timeout} minutes\n"
                       f"{engage_text}\n"
                       f"🤫 **Silent mode:** They won't know it's intentional\n\n"
                       f"Harry will respond to their messages with creative greetings.",
            color=0xff6b6b
        )
        embed.set_footer(text="Use /fun toggle_engage to change | /fun status to check")

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

    @fun_group.command(name="toggle_engage", description="🔥 Toggle argument mode for a user (Admin only)")
    @app_commands.describe(user="The targeted user")
    async def toggle_engage(self, interaction: discord.Interaction, user: discord.Member):
        """Toggle whether Harry will argue back if they respond"""
        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        # Check if user is targeted
        if user.id not in self.targets:
            await interaction.response.send_message(
                f"❌ {user.display_name} isn't being targeted! Use `/fun target` first.",
                ephemeral=True
            )
            return

        # Toggle engage mode
        target_info = self.targets[user.id]
        old_state = target_info.get('engage', False)
        new_state = not old_state
        target_info['engage'] = new_state
        target_info['argument_count'] = 0  # Reset counter when toggling

        logger.info(f"🔥 {interaction.user.display_name} toggled engage mode for {user.display_name}: {old_state} → {new_state}")

        status_emoji = "🔥" if new_state else "💤"
        status_text = "ON - Harry will argue back!" if new_state else "OFF - No arguments"

        embed = discord.Embed(
            title=f"{status_emoji} Engage Mode {'Activated' if new_state else 'Deactivated'}",
            description=f"**{user.display_name}** engage mode: **{status_text}**\n\n"
                       f"{'Harry will now use AI to generate contextual comebacks when they reply!' if new_state else 'Harry will ignore their responses.'}",
            color=0xff0000 if new_state else 0x808080
        )
        embed.set_footer(text="Argument counter reset to 0 | Max 5 arguments per user")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

                engage_status = "🔥 ON" if info.get('engage') else "💤 OFF"
                arg_count = info.get('argument_count', 0)

                status_text = (
                    f"⏱️ **Timeout:** {info['timeout']} minutes\n"
                    f"🕐 **Last triggered:** {time_since}m ago\n"
                    f"⏳ **Next available:** {time_until}m\n"
                    f"🔥 **Engage mode:** {engage_status}\n"
                    f"💬 **Arguments:** {arg_count}/5\n"
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
        timeout="Minutes between messages (default: 30)",
        engage="Should Harry argue back if they respond? (default: False)"
    )
    async def target_all(
        self,
        interaction: discord.Interaction,
        users: str,
        timeout: int = 30,
        engage: bool = False
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
                'enabled_by_name': interaction.user.display_name,
                'engage': engage,
                'argument_count': 0
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

        logger.info(f"🎯 {interaction.user.display_name} enabled trolling for {len(added)} users (timeout: {timeout}m, engage: {engage})")

        engage_text = "🔥 **Engage mode: ON** - Harry will argue if they respond!" if engage else "💤 **Engage mode: OFF**"

        embed = discord.Embed(
            title="🎯 Multiple Targets Acquired",
            description=f"**{len(added)} users** are now being trolled!\n\n"
                       f"⏱️ **Timeout:** {timeout} minutes\n"
                       f"{engage_text}\n"
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
        """Listen for messages from targeted users and handle both trolling and arguments"""
        # Ignore bots
        if message.author.bot:
            return

        # PRIORITY 1: Check if this is a reply to Harry's troll message (argument mode)
        if message.reference and message.reference.message_id:
            await self._handle_argument_reply(message)
            return  # Don't process as regular message if it's a reply

        # PRIORITY 2: Check if user is targeted for trolling
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

            troll_message = random.choice(troll_messages)
            sent_message = await message.channel.send(troll_message)

            # Track this troll message for reply detection (if engage mode is on)
            if target_info.get('engage'):
                self.troll_messages[sent_message.id] = message.author.id
                logger.info(f"🎭 Trolled {message.author.display_name} (engage mode ON) in #{message.channel.name}")
            else:
                logger.info(f"🎭 Trolled {message.author.display_name} in #{message.channel.name}")

            # Cleanup old troll messages to prevent memory leak (keep last 100)
            if len(self.troll_messages) > 100:
                # Remove oldest 50 entries
                oldest_keys = list(self.troll_messages.keys())[:50]
                for key in oldest_keys:
                    del self.troll_messages[key]
                logger.debug(f"🧹 Cleaned up {len(oldest_keys)} old troll message IDs")

        except Exception as e:
            logger.error(f"❌ Failed to send troll message: {e}")

    async def _handle_argument_reply(self, message: discord.Message):
        """Handle replies to Harry's troll messages (argument mode)"""
        replied_to_id = message.reference.message_id

        # Check if they replied to a troll message
        if replied_to_id not in self.troll_messages:
            return

        target_user_id = self.troll_messages[replied_to_id]

        # Verify the replier is the targeted user
        if message.author.id != target_user_id:
            return

        # Check if engage mode is on for this user
        if target_user_id not in self.targets:
            return

        target_info = self.targets[target_user_id]
        if not target_info.get('engage'):
            return

        # Limit argument escalation (max 5 back-and-forth)
        if target_info.get('argument_count', 0) >= 5:
            logger.info(f"🛑 Argument limit reached for {message.author.display_name}")
            return

        # Generate AI comeback if available
        try:
            their_message = message.content

            # Use AI if available
            if self.ai_assistant:
                comeback = await self._generate_ai_comeback(their_message, message.author.display_name)
            else:
                # Fallback: Use predefined comebacks
                comeback = self._get_fallback_comeback(their_message)

            await message.channel.send(comeback)

            # Increment argument counter
            target_info['argument_count'] = target_info.get('argument_count', 0) + 1

            logger.info(f"🔥 Harry argued back with {message.author.display_name} (count: {target_info['argument_count']})")

        except Exception as e:
            logger.error(f"❌ Failed to generate comeback: {e}")

    async def _generate_ai_comeback(self, user_message: str, user_name: str) -> str:
        """Generate contextual AI comeback"""
        try:
            prompt = f"""You are Harry, an extremely vulgar and rude British football bot who just told {user_name} "Fuck you" and they responded with: "{user_message}"

Generate a SHORT, BRUTAL comeback that:
- Is EXTREMELY rude and vulgar (use fuck, shit, cunt, wanker, bellend, twat, etc. liberally)
- Is British slang-heavy (mate, ya muppet, bollocks, piss off, sod off, etc.)
- References what they said and roasts them for it
- Is deliberately offensive and insulting
- Is 1-2 sentences max
- Ends with an emoji

Example comebacks:
- "Oh fuck off, you whiny little bitch. Nobody gives a shit about your feelings, mate. 🖕"
- "Cry harder, you absolute bellend! 😂"
- "Listen here you fucking muppet, your opinion is worth less than dog shit. 💩"
- "What a load of bollocks! Shut your fucking mouth, wanker. 🤐"
- "You're dumber than a bag of fucking rocks, mate. 💀"

Your BRUTAL comeback (max 200 chars):"""

            # Use AI to generate response
            response = await self.ai_assistant.ask_question(prompt, include_charter=False)

            # Trim if too long
            if len(response) > 200:
                response = response[:197] + "..."

            return response

        except Exception as e:
            logger.error(f"❌ AI comeback failed: {e}")
            return self._get_fallback_comeback(user_message)

    def _get_fallback_comeback(self, user_message: str) -> str:
        """Get a fallback comeback if AI isn't available"""
        fallbacks = [
            "Oh fuck off, you whiny little bitch. 🖕",
            "Cry more, you absolute bellend! 😂",
            "Listen here you fucking muppet, shut your mouth. 🤐",
            "What a load of bollocks! Piss off, wanker! 💩",
            "You're dumber than a bag of fucking rocks, mate. 💀",
            "Aww, did I hurt your feelings? Fucking good! 😈",
            "You're a proper twat, aren't ya? 🎯",
            "Is that the best you've got, you useless cunt? 😴",
            "Mate, you're an embarrassment. Sod off! 🔥",
            "Oh no, are you gonna cry now? Fucking pathetic! 😭",
            "Try harder, that was shit! 💩",
            "You're about as useful as a chocolate teapot, ya muppet! 🍫",
            "Shut your fucking gob before I do it for you! 🤬",
            "You talk a lot of shite for someone so fucking stupid! 🗑️",
            "Get absolutely fucked, you wanker! 🖕",
        ]

        return random.choice(fallbacks)


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = FunCog(bot)
    await bot.add_cog(cog)
    logger.info("✅ FunCog loaded")
