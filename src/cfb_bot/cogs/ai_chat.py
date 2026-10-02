#!/usr/bin/env python3
"""
AI Chat Cog for CFB League Bot

Provides AI-powered chat commands.
Commands:
- /harry - Ask Harry about college football and league rules
- /ask - General AI questions
- /summarize - Summarize channel activity
"""

import logging
from typing import Optional

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

        if self.AI_AVAILABLE and self.ai_assistant:
            try:
                await interaction.response.send_message("🤔 Harry is thinking...", ephemeral=True)

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
            embed.description = "I'm having some technical difficulties right now. Try again in a bit!"
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

        if self.AI_AVAILABLE and self.ai_assistant:
            try:
                await interaction.response.send_message("🤔 Thinking...", ephemeral=True)

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


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    cog = AIChatCog(bot)
    await bot.add_cog(cog)
    logger.info("AIChatCog loaded")

