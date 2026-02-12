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
from typing import Dict, Optional, Tuple

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

        # Guild-scoped: {guild_id: {user_id: {'timeout': ..., 'last_triggered': ..., 'engage': bool}}}
        self.targets: Dict[int, Dict[int, Dict]] = {}

        # Track Harry's troll messages for reply detection: {message_id: (guild_id, user_id)}
        self.troll_messages: Dict[int, Tuple[int, int]] = {}

        # Track processed interactions to prevent duplicates: {interaction_id: timestamp}
        self._processed_interactions: Dict[int, float] = {}

        logger.info("🎭 FunCog initialized")

    def set_dependencies(self, admin_manager=None, ai_assistant=None):
        """Set dependencies after bot is ready"""
        self.admin_manager = admin_manager
        self.ai_assistant = ai_assistant

    def _targets_for_guild(self, guild_id: int) -> Dict[int, Dict]:
        """Get the targets dict for a guild (per-server targeting)."""
        return self.targets.setdefault(guild_id, {})

    def _is_duplicate_interaction(self, interaction: discord.Interaction) -> bool:
        """Check if we've already processed this interaction (prevents duplicate commands)"""
        interaction_id = interaction.id
        current_time = time.time()

        # Check if we've seen this interaction in the last 5 seconds
        if interaction_id in self._processed_interactions:
            time_since = current_time - self._processed_interactions[interaction_id]
            if time_since < 5:
                logger.warning(f"⚠️ Duplicate interaction detected (ID: {interaction_id}, {time_since:.2f}s ago)")
                return True

        # Mark this interaction as processed
        self._processed_interactions[interaction_id] = current_time

        # Cleanup old entries (keep last 100)
        if len(self._processed_interactions) > 100:
            oldest_keys = sorted(self._processed_interactions.keys(),
                               key=lambda k: self._processed_interactions[k])[:50]
            for key in oldest_keys:
                del self._processed_interactions[key]

        return False

    # Command group
    fun_group = app_commands.Group(
        name="fun",
        description="🎭 Secret fun commands (Admin only)"
    )

    @fun_group.command(name="target", description="🎯 Start trolling a user (Admin only)")
    @app_commands.describe(
        user="The unfortunate soul to target",
        timeout="Minutes between messages (default: 30)",
        engage="Should Harry argue back if they respond? (default: True)"
    )
    async def target(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        timeout: int = 30,
        engage: bool = True
    ):
        """Enable trolling for a specific user"""
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

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

        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command only works in a server!", ephemeral=True)
            return

        guild_targets = self._targets_for_guild(interaction.guild_id)
        guild_targets[user.id] = {
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
                       f"Harry will respond to their messages with creative greetings and argue if they fight back!",
            color=0xff6b6b
        )
        embed.set_footer(text="Use /fun toggle_engage to disable | /fun status to check")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @fun_group.command(name="untarget", description="🛑 Stop trolling a user (Admin only)")
    @app_commands.describe(user="The user to stop trolling")
    async def untarget(self, interaction: discord.Interaction, user: discord.Member):
        """Disable trolling for a specific user"""
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command only works in a server!", ephemeral=True)
            return

        guild_targets = self._targets_for_guild(interaction.guild_id)
        if user.id in guild_targets:
            guild_targets.pop(user.id)
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
                f"❌ {user.display_name} isn't being targeted in this server!",
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
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

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

        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command only works in a server!", ephemeral=True)
            return

        guild_targets = self._targets_for_guild(interaction.guild_id)
        if user.id in guild_targets:
            old_timeout = guild_targets[user.id]['timeout']
            guild_targets[user.id]['timeout'] = timeout

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
                f"❌ {user.display_name} isn't being targeted in this server! Use `/fun target` first.",
                ephemeral=True
            )

    @fun_group.command(name="toggle_engage", description="🔥 Toggle argument mode for a user (Admin only)")
    @app_commands.describe(user="The targeted user")
    async def toggle_engage(self, interaction: discord.Interaction, user: discord.Member):
        """Toggle whether Harry will argue back if they respond"""
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command only works in a server!", ephemeral=True)
            return

        guild_targets = self._targets_for_guild(interaction.guild_id)
        if user.id not in guild_targets:
            await interaction.response.send_message(
                f"❌ {user.display_name} isn't being targeted in this server! Use `/fun target` first.",
                ephemeral=True
            )
            return

        # Toggle engage mode
        target_info = guild_targets[user.id]
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
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command only works in a server!", ephemeral=True)
            return

        guild_targets = self._targets_for_guild(interaction.guild_id)
        if not guild_targets:
            embed = discord.Embed(
                title="📋 Trolling Status",
                description="No active targets in **this server**.\n\nUse `/fun target` to start trolling someone!",
                color=Colors.WARNING
            )
        else:
            embed = discord.Embed(
                title="📋 Active Targets (this server)",
                description=f"Currently trolling **{len(guild_targets)}** user(s) in this server:",
                color=0xff6b6b
            )

            for user_id, info in guild_targets.items():
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

        embed.set_footer(text="Targeting is per-server only | Harry's Secret Trolling System")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @fun_group.command(name="target_all", description="🎯 Start trolling multiple users at once (Admin only)")
    @app_commands.describe(
        users="Users to target (space-separated mentions: @user1 @user2 @user3)",
        timeout="Minutes between messages (default: 30)",
        engage="Should Harry argue back if they respond? (default: True)"
    )
    async def target_all(
        self,
        interaction: discord.Interaction,
        users: str,
        timeout: int = 30,
        engage: bool = True
    ):
        """Enable trolling for multiple users at once"""
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

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

        guild_targets = self._targets_for_guild(interaction.guild_id)

        # Add all mentioned users (this server only)
        added = []
        skipped = []

        for user_id_str in user_ids:
            user_id = int(user_id_str)

            # Try to get member
            try:
                member = await interaction.guild.fetch_member(user_id)
            except Exception:
                skipped.append(f"<@{user_id}> (not found)")
                continue

            # Skip bots
            if member.bot:
                skipped.append(f"{member.display_name} (bot)")
                continue

            guild_targets[user_id] = {
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

        embed.set_footer(text="Use /fun toggle_engage to disable | /fun untarget to stop")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @fun_group.command(name="roast", description="🔥 Roast a user immediately (Admin only)")
    @app_commands.describe(user="The user to roast")
    async def roast(self, interaction: discord.Interaction, user: discord.Member):
        """Roast a user immediately"""
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        if user.bot:
            await interaction.response.send_message("❌ I don't roast my own kind, mate!", ephemeral=True)
            return

        # Defer response as AI might take a second
        await interaction.response.defer()

        try:
            if self.ai_assistant:
                # Use AI for a fresh roast
                prompt = f"""Generate a short, brutal, British slang-heavy roast for {user.display_name}.
Make it vulgar, offensive, and funny. Max 2 sentences. End with an emoji.
Do NOT start with "Oh," or "Look," - start directly with the roast."""
                
                insult = await self.ai_assistant.ask_question(prompt, include_charter=False)
                
                # Mention them at the start if not included
                if user.mention not in insult:
                    insult = f"{user.mention} {insult}"
            else:
                insult = self._generate_dynamic_insult(user.mention)

            await interaction.followup.send(insult)
            logger.info(f"🔥 {interaction.user.display_name} roasted {user.display_name}")

        except Exception as e:
            logger.error(f"❌ Roast failed: {e}")
            await interaction.followup.send(self._generate_dynamic_insult(user.mention))

    @fun_group.command(name="untarget_all", description="🛑 Stop trolling ALL users (Admin only)")
    async def untarget_all(self, interaction: discord.Interaction):
        """Disable trolling for all users at once"""
        # Check for duplicate interactions
        if self._is_duplicate_interaction(interaction):
            return

        # Admin check
        if not self.admin_manager or not self.admin_manager.is_admin(interaction.user, interaction):
            await interaction.response.send_message("❌ Nice try, but no.", ephemeral=True)
            return

        if not interaction.guild_id:
            await interaction.response.send_message("❌ This command only works in a server!", ephemeral=True)
            return

        guild_targets = self._targets_for_guild(interaction.guild_id)
        if not guild_targets:
            await interaction.response.send_message("❌ No active targets in this server to remove!", ephemeral=True)
            return

        count = len(guild_targets)
        target_names = [info['target_name'] for info in guild_targets.values()]
        guild_targets.clear()

        logger.info(f"🛑 {interaction.user.display_name} disabled trolling for all {count} users")

        embed = discord.Embed(
            title="🛑 All Targets Released (this server)",
            description=f"Removed **{count} users** from trolling list in this server.\n\n"
                       f"They can live in peace here... for now.",
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

        # Only act in servers (not DMs)
        if not message.guild:
            return

        guild_targets = self._targets_for_guild(message.guild.id)

        # PRIORITY 1: Check if this is a reply to Harry's troll message (argument mode)
        if message.reference and message.reference.message_id:
            await self._handle_argument_reply(message, guild_targets)
            return  # Don't process as regular message if it's a reply

        # PRIORITY 1.5: Targeted user said "Harry" or @mentioned Harry → respond EVERY time (no timeout)
        bot_mentioned = self.bot.user in message.mentions
        message_lower = (message.content or "").lower()
        said_harry = "harry" in message_lower

        if message.author.id in guild_targets and (bot_mentioned or said_harry):
            target_info = guild_targets[message.author.id]
            try:
                insult = self._generate_dynamic_insult(message.author.mention)
                sent_message = await message.channel.send(insult)
                if target_info.get('engage'):
                    self.troll_messages[sent_message.id] = (message.guild.id, message.author.id)
                logger.info(f"🎭 Harry responded to mention from {message.author.display_name} (no timeout)")
            except Exception as e:
                logger.error(f"❌ Failed to send mention response: {e}")
            return

        # PRIORITY 1.6: Targeted user insulting (other keywords) + engage mode → argument with limit
        if message.author.id in guild_targets:
            target_info = guild_targets[message.author.id]
            if target_info.get('engage'):
                insult_keywords = ['fuck', 'shit', 'bot', 'ass', 'damn', 'hell', 'stupid', 'dumb', 'suck']
                has_insult = any(k in message_lower for k in insult_keywords)
                if has_insult and target_info.get('argument_count', 0) < 5:
                    await self._handle_direct_insult(message, target_info)
                    return

        # PRIORITY 2: Organic troll (they just posted) — timeout applies
        if message.author.id not in guild_targets:
            return

        target_info = guild_targets[message.author.id]

        # REACTION TROLLING (25% chance to react with an emoji)
        if random.random() < 0.25:
            try:
                annoying_emojis = ["💩", "🤡", "👶", "🤢", "🤏", "🤥", "🖕", "🥱", "🚮", "🤨"]
                await message.add_reaction(random.choice(annoying_emojis))
                logger.info(f"🎭 Reacted to targeted user {message.author.display_name}")
            except Exception as e:
                logger.error(f"❌ Failed to add reaction: {e}")

        current_time = time.time()
        time_since_last = current_time - target_info['last_triggered']
        timeout_seconds = target_info['timeout'] * 60

        if time_since_last < timeout_seconds:
            return

        target_info['last_triggered'] = current_time

        try:
            troll_message = self._generate_dynamic_insult(message.author.mention)
            sent_message = await message.channel.send(troll_message)

            if target_info.get('engage'):
                self.troll_messages[sent_message.id] = (message.guild.id, message.author.id)
            logger.info(f"🎭 Organic troll: {message.author.display_name} in #{message.channel.name}")

            if len(self.troll_messages) > 100:
                oldest_keys = list(self.troll_messages.keys())[:50]
                for key in oldest_keys:
                    del self.troll_messages[key]
                logger.debug(f"🧹 Cleaned up {len(oldest_keys)} old troll message IDs")

        except Exception as e:
            logger.error(f"❌ Failed to send troll message: {e}")

    async def _handle_direct_insult(self, message: discord.Message, target_info: Dict):
        """Handle when targeted user insults Harry directly (not a reply)"""
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

            logger.info(f"🔥 Harry responded to direct insult from {message.author.display_name} (count: {target_info['argument_count']})")

        except Exception as e:
            logger.error(f"❌ Failed to respond to insult: {e}")

    async def _handle_argument_reply(self, message: discord.Message, guild_targets: Dict[int, Dict]):
        """Handle replies to Harry's troll messages (argument mode). guild_targets is for message.guild."""
        replied_to_id = message.reference.message_id

        # Check if they replied to a troll message
        if replied_to_id not in self.troll_messages:
            return

        stored_guild_id, target_user_id = self.troll_messages[replied_to_id]

        # Only count replies in the same server where we sent the troll
        if message.guild.id != stored_guild_id:
            return

        # Verify the replier is the targeted user
        if message.author.id != target_user_id:
            return

        # Check if engage mode is on for this user (in this server)
        if target_user_id not in guild_targets:
            return

        target_info = guild_targets[target_user_id]
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

    def _generate_dynamic_insult(self, mention: str) -> str:
        """Generate a random insult from phrases + swear words + objects (new combo each time)."""
        phrases = [
            "Fuck you", "Oi", "Look at this", "Absolute", "What a", "You're a",
            "Shut your face", "Piss off", "Sod off", "Get lost", "Hey", "Oh look",
            "Listen here", "Cry more", "Try harder", "Fuck off", "Yeah right",
            "You absolute", "Check out this", "State of this", "Imagine being a",
            "Holy shit it's", "Everybody look at", "Christ alive,", "Do one",
            "Get stuffed", "Jog on", "Wind your neck in",
        ]
        swears = [
            "fucking", "shit", "bloody", "sodding", "goddamn", "damn",
            "wank", "bellend", "twat", "muppet", "pillock", "plonker",
            "cockwomble", "thundercunt", "shitgibbon", "spunkbubble",
            "fudgepacking", "tosspot", "numpty", "minging", "gormless",
            "clapped", "noncey", "daft", "useless",
        ]
        objects = [
            "muppet", "donut", "pillock", "waste of space", "chocolate teapot",
            "bag of rocks", "wet wipe", "absolute weapon", "wanker", "bellend",
            "twat", "plonker", "numpty", "melon", "div",
            "knobhead", "dickhead", "tosser", "berk", "prat",
            "nincompoop", "dipstick", "ninny", "wazzock",
            "broken condom", "failed abortion", "inbred cabbage",
            "sentient wank sock", "moldy cum rag", "village idiot",
            "oxygen thief", "damp towel", "ham sandwich", "window licker",
            "mouth breather", "fart in a jar", "stale biscuit",
        ]
        emojis = ["🖕", "💩", "🤬", "😈", "😂", "🗑️", "🔥", "🤡", "🤢", "🤏", "💀"]

        p = random.choice(phrases)
        s = random.choice(swears)
        o = random.choice(objects)
        e = random.choice(emojis)

        # Avoid "Fuck you you" when mention is "you" (used for comebacks)
        if mention.strip().lower() == "you":
            templates = [
                f"{p}, you {s} {o}! {e}",
                f"You're a {s} {o}. {p}! {e}",
                f"What a {s} {o}. {p}! {e}",
                f"Oi! You {s} {o}. {p}! {e}",
                f"Look at you, the {s} {o}. {e}",
                f"{p} you {s} {o}! {e}",
            ]
        else:
            templates = [
                f"{p} {mention}, you {s} {o}! {e}",
                f"{mention} {p} you {s} {o}! {e}",
                f"Oi {mention}! You're a {s} {o}. {e}",
                f"{p} {mention}. What a {s} {o}! {e}",
                f"Look at {mention}, the {s} {o}. {e}",
                f"{p} you {s} {o}, {mention}! {e}",
                f"{mention} — you {s} {o}. {p}! {e}",
                f"What a {s} {o}. {p} {mention}! {e}",
            ]
        return random.choice(templates)

    def _get_fallback_comeback(self, user_message: str) -> str:
        """Fallback comeback if AI isn't available; 50% dynamic insult, 50% fixed."""
        if random.random() < 0.5:
            return self._generate_dynamic_insult("you")
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
