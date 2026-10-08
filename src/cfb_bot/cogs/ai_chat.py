#!/usr/bin/env python3
"""
AI Chat Cog for CFB League Bot

Provides AI-powered chat commands.
Commands:
- /harry - Ask Harry about college football and league rules
- /ask - General AI questions
- /summarize - Summarize channel activity

Also answers when someone @mentions Harry in a channel he's enabled in.
"""

import logging
import re
import time
from typing import Dict, Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..config import GAME_NAME, Colors
from ..utils.server_config import server_config, FeatureModule
from ..utils.input_validation import sanitize_string, MAX_INPUT_LENGTH

logger = logging.getLogger('CFBBot.AIChat')


class AIChatCog(commands.Cog):
    """AI-powered chat commands"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Dependencies - set after loading
        self.ai_assistant = None
        self.channel_summarizer = None
        self.AI_AVAILABLE = False
        # user_id -> last mention reply time, to stop one person spamming the AI
        self._mention_cooldowns: Dict[int, float] = {}
        logger.info("AIChatCog initialized")

    def set_dependencies(self, ai_assistant=None, channel_summarizer=None, AI_AVAILABLE=False):
        """Set dependencies after bot is ready"""
        self.ai_assistant = ai_assistant
        self.channel_summarizer = channel_summarizer
        self.AI_AVAILABLE = AI_AVAILABLE

    @app_commands.command(name="harry", description="Ask Harry about college football")
    @app_commands.describe(question="Your question about college football or league rules")
    async def harry(self, interaction: discord.Interaction, question: str):
        """Ask Harry about college football or league rules"""
        # Validate and sanitize input
        if len(question) > MAX_INPUT_LENGTH:
            await interaction.response.send_message(
                f"❌ Question too long! Must be under {MAX_INPUT_LENGTH} characters. "
                f"(You provided {len(question)} characters)",
                ephemeral=True
            )
            return
        
        question = sanitize_string(question)
        
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

        # Acknowledge first: an interaction must be answered within 3 seconds or its
        # token dies, and every path below ends in followup.send().
        await interaction.response.send_message("🤔 Harry is thinking...", ephemeral=True)

        if self.AI_AVAILABLE and self.ai_assistant:
            try:
                logger.info(f"/harry from {interaction.user}: '{question}'")

                personality = server_config.get_personality_prompt(guild_id)

                # Make AI response
                if league_enabled:
                    conversational_question = f"{personality} Answer this question about {GAME_NAME} league rules: {question}"
                else:
                    conversational_question = f"{personality} Answer this question about college football: {question}"

                response = await self.ai_assistant.ask_ai(
                    conversational_question,
                    f"{interaction.user} ({interaction.user.id})",
                    include_league_context=league_enabled
                )

                if response:
                    embed.description = response
                    embed.add_field(name="💬 Responding to:", value=f"*{question}*", inline=False)
                    if league_enabled:
                        embed.add_field(name="💡 Need More Info?", value="Ask me anything about league rules!", inline=False)
                else:
                    embed.description = "Sorry, I couldn't get a response right now. Try again!"
                    embed.add_field(name="💬 Responding to:", value=f"*{question}*", inline=False)

            except Exception as e:
                embed.description = f"Oops! Something went wrong: {str(e)}"
                embed.add_field(name="💬 Responding to:", value=f"*{question}*", inline=False)
        else:
            logger.error("/harry ran with no AI configured - set OPENAI_API_KEY or ANTHROPIC_API_KEY")
            embed.description = ("My brain's not plugged in — no AI key is configured. "
                                 "An admin needs to set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.")
            embed.add_field(name="💬 Responding to:", value=f"*{question}*", inline=False)

        # Only add charter link if LEAGUE module is enabled
        if league_enabled:
            embed.add_field(
                name="📖 Full League Charter",
                value="[Open Charter](https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit)",
                inline=False
            )

        embed.set_footer(text="Harry's CFB Assistant 🏈")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ask", description="Ask Harry general questions (not league-specific)")
    @app_commands.describe(question="Your general question")
    async def ask(self, interaction: discord.Interaction, question: str):
        """Ask AI general questions"""
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
            title="💬 Harry's Response",
            color=Colors.PRIMARY
        )

        # Acknowledge first (see /harry) so the token survives a slow or missing AI
        await interaction.response.send_message("🤔 Thinking...", ephemeral=True)

        if self.AI_AVAILABLE and self.ai_assistant:
            try:
                logger.info(f"/ask from {interaction.user}: '{question}'")

                personality = server_config.get_personality_prompt(guild_id)
                response = await self.ai_assistant.ask_ai(
                    f"{personality} Answer this question: {question}",
                    f"{interaction.user} ({interaction.user.id})",
                    include_league_context=False
                )

                if response:
                    embed.description = response
                else:
                    embed.description = "Sorry, I couldn't get a response right now."

                embed.add_field(name="💬 Responding to:", value=f"*{question}*", inline=False)

            except Exception as e:
                embed.description = f"Oops! Something went wrong: {str(e)}"
                embed.add_field(name="💬 Responding to:", value=f"*{question}*", inline=False)
        else:
            embed.description = "I'm having some technical difficulties right now."
            embed.add_field(name="💬 Responding to:", value=f"*{question}*", inline=False)

        embed.set_footer(text="Harry's AI Assistant 🤖")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="summarize", description="Summarize channel activity for a time period")
    @app_commands.describe(
        hours="Hours of history to look back (default: 24, max: 168)",
        focus="Optional focus area for the summary (e.g., 'rules', 'voting')"
    )
    async def summarize(
        self,
        interaction: discord.Interaction,
        hours: int = 24,
        focus: Optional[str] = None
    ):
        """Summarize channel activity"""
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

        if not self.channel_summarizer:
            await interaction.response.send_message("❌ Channel summarizer not available", ephemeral=True)
            return

        try:
            await interaction.response.defer()

            # Validate hours
            if hours < 1:
                hours = 1
            elif hours > 168:
                hours = 168

            focus_text = focus.strip() if focus else None

            # Send "working" message
            focus_description = f" focusing on **{focus_text}**" if focus_text else ""
            embed = discord.Embed(
                title="📊 Generating Summary...",
                description=f"Looking through the last **{hours} hours** of messages{focus_description}...",
                color=Colors.WARNING
            )
            await interaction.followup.send(embed=embed)

            # Generate the summary
            logger.info(f"Summary requested by {interaction.user} for #{interaction.channel.name} ({hours} hours)")
            summary = await self.channel_summarizer.get_channel_summary(
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

            embed.add_field(name="📍 Channel", value=f"#{interaction.channel.name}", inline=True)
            embed.add_field(name="⏰ Time Period", value=f"Last {hours} hour{'s' if hours > 1 else ''}", inline=True)
            if focus_text:
                embed.add_field(name="🎯 Focus", value=focus_text, inline=True)

            embed.set_footer(text=f"Harry's Channel Summary 🏈 | Requested by {interaction.user.display_name}")
            await interaction.followup.send(embed=embed)

        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ Permission Denied",
                description="I don't have permission to read message history in this channel!",
                color=Colors.ERROR
            )
            await interaction.followup.send(embed=embed)
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            embed = discord.Embed(
                title="❌ Summary Failed",
                description=f"Something went wrong: `{str(e)}`",
                color=Colors.ERROR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


    # ==================== @MENTION REPLIES ====================

    MENTION_COOLDOWN_SECONDS = 10

    def _is_fun_target(self, message: discord.Message) -> bool:
        """True if FunCog is already trolling this user — it answers their mentions itself."""
        fun_cog = self.bot.get_cog('FunCog')
        if not fun_cog or not hasattr(fun_cog, '_targets_for_guild'):
            return False
        try:
            return message.author.id in fun_cog._targets_for_guild(message.guild.id)
        except Exception:
            return False

    def _strip_mentions(self, message: discord.Message) -> str:
        """The message text with the bot's own mention removed."""
        content = message.content or ""
        content = re.sub(rf"<@!?{self.bot.user.id}>", " ", content)
        return content.strip()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Answer when someone @mentions Harry."""
        if message.author.bot or not message.guild or not self.bot.user:
            return
        # @everyone/@here isn't talking to Harry, and role pings aren't in message.mentions
        if message.mention_everyone or self.bot.user not in message.mentions:
            return
        if self._is_fun_target(message):
            return

        guild_id = message.guild.id
        if not server_config.is_module_enabled(guild_id, FeatureModule.AI_CHAT):
            return
        # Same channel whitelist /harry uses (`/admin channels`)
        if not server_config.is_channel_enabled(guild_id, message.channel.id):
            return

        question = self._strip_mentions(message)
        if len(question) > MAX_INPUT_LENGTH:
            await message.reply(
                f"That's a bit much, mate — keep it under {MAX_INPUT_LENGTH} characters.",
                mention_author=False,
            )
            return

        now = time.time()
        last = self._mention_cooldowns.get(message.author.id, 0)
        if now - last < self.MENTION_COOLDOWN_SECONDS:
            return
        self._mention_cooldowns[message.author.id] = now
        if len(self._mention_cooldowns) > 500:  # keep the dict from growing forever
            cutoff = now - self.MENTION_COOLDOWN_SECONDS
            self._mention_cooldowns = {
                uid: ts for uid, ts in self._mention_cooldowns.items() if ts > cutoff
            }

        if not (self.AI_AVAILABLE and self.ai_assistant):
            await message.reply("Had a few too many — my brain's not working. Try again later.", mention_author=False)
            return

        question = sanitize_string(question) if question else "Someone pinged you without saying anything. Greet them."
        league_enabled = server_config.is_module_enabled(guild_id, FeatureModule.LEAGUE)
        personality = server_config.get_personality_prompt(guild_id)
        topic = f"{GAME_NAME} league rules" if league_enabled else "college football"
        # Don't tell him he was "mentioned" — he opens every reply narrating it
        # ("Oi, BoozeRob mentioned me..."). He's just in a conversation.
        prompt = (
            f"{personality} You're chatting in Discord and {message.author.display_name} "
            f"just said this to you. Reply straight to them, briefly - a couple of sentences. "
            f"Never narrate that you were mentioned or pinged. "
            f"What they said, answer it (about {topic} if relevant): {question}"
        )

        logger.info(f"@mention from {message.author} in #{message.channel}: '{question[:100]}'")

        try:
            async with message.channel.typing():
                response = await self.ai_assistant.ask_ai(
                    prompt,
                    f"{message.author} ({message.author.id})",
                    include_league_context=league_enabled,
                )
        except Exception as e:
            logger.error(f"Failed to answer @mention: {e}")
            response = None

        if not response:
            response = "Can't get a word out right now, mate. Try me again in a bit."

        # Discord caps messages at 2000 characters
        await message.reply(response[:1990], mention_author=False)


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = AIChatCog(bot)
    await bot.add_cog(cog)
    logger.info("AIChatCog loaded")

