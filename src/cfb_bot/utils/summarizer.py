#!/usr/bin/env python3
"""
Channel Summarizer Module for CFB League Bot
Fetches and summarizes channel messages using AI
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import discord

from ..config import GAME_NAME

logger = logging.getLogger('CFBBot.Summarizer')

class ChannelSummarizer:
    """Handles fetching and summarizing channel messages"""

    def __init__(self, ai_assistant=None):
        self.ai_assistant = ai_assistant

    async def fetch_messages(
        self,
        channel: discord.TextChannel,
        hours: int = 24,
        limit: int = 500
    ) -> List[discord.Message]:
        """
        Fetch messages from a channel within the specified time period

        Args:
            channel: The Discord channel to fetch from
            hours: Number of hours to look back
            limit: Maximum number of messages to fetch

        Returns:
            List of discord.Message objects
        """
        logger.info(f"Fetching messages from #{channel.name} (last {hours} hours)")

        # Calculate the time threshold - use UTC aware datetime
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

        logger.info(f"Looking for messages after: {time_threshold}")

        messages = []
        try:
            message_count = 0
            async for message in channel.history(limit=limit):
                message_count += 1

                # Check if message is within time range
                if message.created_at < time_threshold:
                    # Older than our threshold, stop looking
                    break

                # Skip bot messages unless they're important
                if message.author.bot:
                    continue

                messages.append(message)

            logger.info(f"Scanned {message_count} total messages, found {len(messages)} user messages")

            logger.info(f"Fetched {len(messages)} messages from #{channel.name}")
            return messages

        except discord.Forbidden:
            logger.error(f"No permission to read message history in #{channel.name}")
            # Return empty list - caller will handle the message
            return []
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            return []

    def format_messages_for_summary(self, messages: List[discord.Message]) -> str:
        """
        Format messages into a readable text for AI summarization

        Args:
            messages: List of Discord messages

        Returns:
            Formatted string of messages
        """
        if not messages:
            return ""

        # Sort messages by timestamp (oldest first)
        messages.sort(key=lambda m: m.created_at)

        formatted = []
        for msg in messages:
            timestamp = msg.created_at.strftime('%Y-%m-%d %H:%M')
            author = msg.author.display_name
            content = msg.content

            # Include attachment info
            if msg.attachments:
                content += f" [Attachments: {len(msg.attachments)} file(s)]"

            # Include reaction count if significant
            if msg.reactions:
                total_reactions = sum(r.count for r in msg.reactions)
                if total_reactions > 3:
                    content += f" [{total_reactions} reactions]"

            formatted.append(f"[{timestamp}] {author}: {content}")

        return "\n".join(formatted)

    async def summarize_messages(
        self,
        messages: List[discord.Message],
        focus: Optional[str] = None
    ) -> Optional[str]:
        """
        Use AI to summarize the messages

        Args:
            messages: List of Discord messages
            focus: Optional focus area for the summary

        Returns:
            AI-generated summary string
        """
        if not messages:
            return "No messages found in the specified time period, mate!"

        if not self.ai_assistant:
            # Fallback to basic summary without AI
            return self._basic_summary(messages)

        # Format messages for AI
        formatted_text = self.format_messages_for_summary(messages)

        # Create the AI prompt
        focus_text = f" with a focus on {focus}" if focus else ""
        focus_instruction = f"\n\n**IMPORTANT:** Focus specifically on discussions related to '{focus}' - filter out irrelevant conversations and highlight only messages that pertain to this topic." if focus else ""

        prompt = f"""You are Harry, a friendly but completely insane {GAME_NAME} league assistant. You are extremely sarcastic, witty, and have a dark sense of humor.

Please summarize the following Discord channel conversation{focus_text}. Be concise but capture the key points, decisions, discussions, and any important information. Keep your sarcastic personality but make the summary actually useful.{focus_instruction}

Format the summary with:
- **Main Topics**: What were the key discussion points?
- **Decisions/Actions**: Any decisions made or actions taken?
- **Key Participants**: Who were the main contributors?
- **Notable Moments**: Any funny, important, or interesting moments?

Channel Messages:
{formatted_text}

Provide a helpful summary with maximum sarcasm and wit, but don't be a tosser about it - make it actually useful!"""

        try:
            focus_log = f" (focus: {focus})" if focus else ""
            logger.info(f"Requesting AI summary for {len(messages)} messages{focus_log}")
            summary = await self.ai_assistant.ask_ai(prompt, "Channel Summarizer")

            if summary:
                logger.info("AI summary generated successfully")
                return summary
            else:
                logger.warning("AI summary failed, using basic summary")
                return self._basic_summary(messages)

        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return self._basic_summary(messages)

    def _basic_summary(self, messages: List[discord.Message]) -> str:
        """
        Generate a basic summary without AI

        Args:
            messages: List of Discord messages

        Returns:
            Basic summary string
        """
        if not messages:
            return "No messages found, mate!"

        # Count unique participants
        participants = set(msg.author.display_name for msg in messages)

        # Count messages per user
        message_counts = {}
        for msg in messages:
            author = msg.author.display_name
            message_counts[author] = message_counts.get(author, 0) + 1

        # Find most active user
        most_active = max(message_counts.items(), key=lambda x: x[1])

        # Get time range
        oldest = min(messages, key=lambda m: m.created_at)
        newest = max(messages, key=lambda m: m.created_at)

        summary = f"""📊 **Basic Channel Summary**

**Time Period**: {oldest.created_at.strftime('%b %d, %I:%M %p')} - {newest.created_at.strftime('%b %d, %I:%M %p')}

**Activity**:
• Total messages: {len(messages)}
• Participants: {len(participants)} users
• Most active: {most_active[0]} ({most_active[1]} messages)

**Top Contributors**:
"""

        # Add top 5 contributors
        sorted_contributors = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for contributor, count in sorted_contributors:
            summary += f"• {contributor}: {count} messages\n"

        summary += "\n*Note: AI summarization not available - this is a basic stats summary.*"

        return summary

    async def get_channel_summary(
        self,
        channel: discord.TextChannel,
        hours: int = 24,
        focus: Optional[str] = None,
        limit: int = 500
    ) -> str:
        """
        Complete workflow: fetch messages and generate summary

        Args:
            channel: The Discord channel
            hours: Number of hours to look back
            focus: Optional focus area
            limit: Max messages to fetch

        Returns:
            Summary string
        """
        logger.info(f"Starting summary for #{channel.name} (last {hours} hours)")

        messages = await self.fetch_messages(channel, hours, limit)

        if not messages:
            return f"Blimey! I couldn't find any messages in #{channel.name} from the last {hours} hours, mate. Everyone's been quiet as a mouse!"

        # Generate summary
        summary = await self.summarize_messages(messages, focus)

        return summary if summary else "Sorry mate, couldn't generate a summary right now. Try again later!"
