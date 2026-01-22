#!/usr/bin/env python3
"""
AI Integration for CFB 26 League Bot
This module handles AI-powered responses about the league charter
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional

import aiohttp
from dotenv import load_dotenv

from ..utils.storage import get_storage
from ..security import HTTP_TIMEOUT

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger('CFB26Bot.AI')

class AICharterAssistant:
    """AI-powered assistant for league charter questions"""

    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Charter URL (configurable via environment variable)
        self.charter_url = os.getenv('CHARTER_URL', 'https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit')
        self.charter_content = None

        # Token usage tracking (loaded from storage)
        self.total_openai_tokens = 0
        self.total_anthropic_tokens = 0
        self.total_requests = 0

        # Cost tracking (per 1k tokens - averaged input/output)
        self.openai_cost_per_1k = 0.001  # GPT-3.5-turbo average
        self.anthropic_cost_per_1k = 0.0007  # Claude 3 Haiku average

        # Storage
        self._storage = get_storage()
        self._loaded = False

    async def _load_usage_stats(self):
        """Load usage statistics from persistent storage"""
        if self._loaded:
            return

        try:
            data = await self._storage.load("ai_usage", "global")
            if data:
                self.total_openai_tokens = data.get('openai_tokens', 0)
                self.total_anthropic_tokens = data.get('anthropic_tokens', 0)
                self.total_requests = data.get('total_requests', 0)
                logger.info(f"📊 Loaded AI usage stats: {self.total_requests:,} requests, {self.total_openai_tokens + self.total_anthropic_tokens:,} tokens")
            else:
                logger.info("📊 No existing AI usage stats found - starting fresh")
            self._loaded = True
        except Exception as e:
            logger.warning(f"⚠️ Failed to load AI usage stats: {e}")
            self._loaded = True  # Don't try again

    async def _save_usage_stats(self):
        """Save usage statistics to persistent storage"""
        try:
            data = {
                'openai_tokens': self.total_openai_tokens,
                'anthropic_tokens': self.total_anthropic_tokens,
                'total_requests': self.total_requests
            }
            await self._storage.save("ai_usage", "global", data)
            logger.debug(f"💾 Saved AI usage stats")
        except Exception as e:
            logger.error(f"❌ Failed to save AI usage stats: {e}")

    async def get_charter_content(self) -> Optional[str]:
        """Get charter content for AI context"""
        # Try to get content from local file first
        try:
            charter_file = "data/charter_content.txt"
            if os.path.exists(charter_file):
                with open(charter_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        logger.info(f"📄 Loaded local charter content ({len(content)} characters)")
                        return content
        except Exception as e:
            logger.warning(f"⚠️  Local charter file failed: {e}")

        # Try to get content from Google Docs as fallback
        try:
            from google_docs_integration import GoogleDocsIntegration
            google_docs = GoogleDocsIntegration()
            if google_docs.authenticate():
                content = google_docs.get_document_content()
                if content:
                    return content
        except Exception as e:
            logger.warning(f"⚠️  Google Docs integration failed: {e}")

        # No charter content available
        logger.info("📄 No charter content available - using fallback context")
        return None

    def get_schedule_context(self) -> str:
        """Get schedule context for AI queries, including current week info"""
        context_parts = []

        # Try to get current week/season from the bot's timekeeper_manager
        try:
            # Import bot module to access timekeeper_manager
            from .. import bot as bot_module
            if hasattr(bot_module, 'timekeeper_manager') and bot_module.timekeeper_manager:
                season_info = bot_module.timekeeper_manager.get_season_week()
                if season_info.get('season') and season_info.get('week') is not None:
                    current_week = season_info['week']
                    current_season = season_info['season']
                    week_name = season_info.get('week_name', f"Week {current_week}")
                    phase = season_info.get('phase', 'Unknown')

                    context_parts.append(f"**CURRENT STATUS: Season {current_season}, {week_name} (Week {current_week})**")
                    context_parts.append(f"Phase: {phase}")
                    context_parts.append(f"IMPORTANT: When the user says 'this week' or 'current week', they mean Week {current_week}.")
                    context_parts.append("")
        except Exception as e:
            logger.debug(f"Could not get current week context: {e}")

        # Get full schedule
        try:
            from ..utils.schedule_manager import get_schedule_manager
            schedule_mgr = get_schedule_manager()
            if schedule_mgr:
                context_parts.append(schedule_mgr.get_schedule_context_for_ai())
        except Exception as e:
            logger.warning(f"⚠️ Could not get schedule context: {e}")

        return "\n".join(context_parts)

    async def ask_openai(self, question: str, context: str, max_tokens: int = 500, personality_prompt: str = None, include_league_context: bool = True) -> Optional[str]:
        """Ask OpenAI - optionally includes league charter and schedule context

        Args:
            question: The question to ask
            context: Additional context (charter content, etc.)
            max_tokens: Maximum tokens for response
            personality_prompt: Custom personality prompt
            include_league_context: Whether to include league schedule/charter info (False for non-league servers)
        """
        if not self.openai_api_key:
            logger.warning("⚠️ OpenAI API key not found")
            return None

        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }

        # Use provided personality or default full personality
        personality = personality_prompt or "You are Harry, a friendly but completely insane CFB 26 league assistant. You are extremely sarcastic, witty, and have a dark sense of humor. You have a deep, unhinged hatred of the Oregon Ducks."

        # Build prompt based on whether league context should be included
        if include_league_context:
            # Get schedule context for league servers
            schedule_context = self.get_schedule_context()

            prompt = f"""
            {personality}
            Answer questions based on the league charter AND schedule information provided below in a hilariously sarcastic way.

            League Charter Context:
            {context}

            League Schedule Information:
            {schedule_context}

            Question: {question}

            IMPORTANT INSTRUCTIONS:
            - If you can answer the question based on the charter OR schedule content, provide a direct, helpful answer with maximum sarcasm
            - For schedule questions (matchups, byes, who plays who), use the schedule information above

            CRITICAL - SCHEDULE FORMATTING RULES (YOU MUST FOLLOW THESE):
            1. FORMAT AS CLEAN LISTS, not paragraphs
            2. USER TEAMS MUST BE BOLDED WITH ** - The user teams are: Hawaii, LSU, Michigan St, Nebraska, Notre Dame, Texas
            3. Example correct format:
               🏈 **LSU** @ Kentucky
               🏈 **Nebraska** @ Boise St
               🏈 **Texas** @ Mississippi St
            4. WRONG format (no bold): 🏈 LSU @ Kentucky
            5. Keep sarcasm SHORT in intro/outro, make the schedule data EASY TO READ

            - Do NOT mention "check the full charter" or "charter" unless you truly don't know the answer
            - Be extremely sarcastic and witty, like a completely insane but knowledgeable league member
            - If the information isn't available, say so with sarcasm
            - Keep responses informative but hilariously sarcastic and insane
            """
        else:
            # Generic CFB assistant mode (no league-specific data)
            prompt = f"""
            {personality}
            Answer this question about college football in a hilariously sarcastic way.

            Question: {question}

            IMPORTANT INSTRUCTIONS:
            - Provide helpful, accurate information about college football
            - Be extremely sarcastic and witty, like a completely insane but knowledgeable CFB fan
            - You can discuss teams, players, games, rankings, history, etc.
            - If you don't know something, say so with sarcasm
            - Keep responses informative but hilariously sarcastic
            - Do NOT make up specific league schedules, rosters, or game results
            """

        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': f'{personality} Be hilariously sarcastic and helpful.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': 0.7
        }

        try:
            # Log the full prompt being sent
            logger.info(f"🤖 Asking OpenAI: {question[:100]}...")
            logger.info(f"📝 Full prompt length: {len(prompt)} characters")
            logger.info(f"📄 Context length: {len(context)} characters")

            # Estimate token count (rough approximation: 1 token ≈ 4 characters)
            estimated_tokens = len(prompt) // 4
            logger.info(f"🔢 Estimated input tokens: ~{estimated_tokens}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Extract token usage information
                        usage = result.get('usage', {})
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                        total_tokens = usage.get('total_tokens', 0)

                        # Log detailed usage information
                        logger.info(f"✅ OpenAI response received")
                        logger.info(f"🔢 Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")

                        # Log any rate limit information if available
                        if 'x-ratelimit-remaining-requests' in response.headers:
                            remaining_requests = response.headers.get('x-ratelimit-remaining-requests')
                            logger.info(f"⏱️ Rate limit - Remaining requests: {remaining_requests}")

                        if 'x-ratelimit-remaining-tokens' in response.headers:
                            remaining_tokens = response.headers.get('x-ratelimit-remaining-tokens')
                            logger.info(f"⏱️ Rate limit - Remaining tokens: {remaining_tokens}")

                        if 'x-ratelimit-reset-requests' in response.headers:
                            reset_requests = response.headers.get('x-ratelimit-reset-requests')
                            logger.info(f"⏱️ Rate limit - Requests reset at: {reset_requests}")

                        if 'x-ratelimit-reset-tokens' in response.headers:
                            reset_tokens = response.headers.get('x-ratelimit-reset-tokens')
                            logger.info(f"⏱️ Rate limit - Tokens reset at: {reset_tokens}")

                        # Update token counters
                        self.total_openai_tokens += total_tokens
                        self.total_requests += 1

                        # Save updated stats
                        await self._save_usage_stats()

                        logger.info(f"📊 Total OpenAI tokens used: {self.total_openai_tokens} (across {self.total_requests} requests)")

                        response_text = result['choices'][0]['message']['content'].strip()
                        logger.info(f"📝 Response length: {len(response_text)} characters")

                        return response_text
                    else:
                        error_text = await response.text()
                        logger.error(f"OpenAI API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error calling OpenAI: {e}")
            return None

    async def ask_anthropic(self, question: str, context: str, max_tokens: int = 500, personality_prompt: str = None, include_league_context: bool = True) -> Optional[str]:
        """Ask Anthropic Claude - optionally includes league charter and schedule context

        Args:
            question: The question to ask
            context: Additional context (charter content, etc.)
            max_tokens: Maximum tokens for response
            personality_prompt: Custom personality prompt
            include_league_context: Whether to include league schedule/charter info (False for non-league servers)
        """
        if not self.anthropic_api_key:
            logger.warning("⚠️ Anthropic API key not found")
            return None

        headers = {
            'x-api-key': self.anthropic_api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }

        # Use provided personality or default full personality
        personality = personality_prompt or "You are Harry, a friendly but completely insane CFB 26 league assistant. You are extremely sarcastic, witty, and have a dark sense of humor. You have a deep, unhinged hatred of the Oregon Ducks."

        # Build prompt based on whether league context should be included
        if include_league_context:
            # Get schedule context for league servers
            schedule_context = self.get_schedule_context()

            prompt = f"""
            {personality}
            Answer questions based on the league charter AND schedule information provided below.

            League Charter Context:
            {context}

            League Schedule Information:
            {schedule_context}

            Question: {question}

            IMPORTANT INSTRUCTIONS:
            - If you can answer the question based on the charter OR schedule content, provide a direct, helpful answer with maximum sarcasm
            - For schedule questions (matchups, byes, who plays who), use the schedule information above

            CRITICAL - SCHEDULE FORMATTING RULES (YOU MUST FOLLOW THESE):
            1. FORMAT AS CLEAN LISTS, not paragraphs
            2. USER TEAMS MUST BE BOLDED WITH ** - The user teams are: Hawaii, LSU, Michigan St, Nebraska, Notre Dame, Texas
            3. Example correct format:
               🏈 **LSU** @ Kentucky
               🏈 **Nebraska** @ Boise St
               🏈 **Texas** @ Mississippi St
            4. WRONG format (no bold): 🏈 LSU @ Kentucky
            5. Keep sarcasm SHORT in intro/outro, make the schedule data EASY TO READ

            - Be extremely sarcastic and witty, like a completely insane but knowledgeable league member
            - Keep responses informative but hilariously sarcastic
            """
        else:
            # Generic CFB assistant mode (no league-specific data)
            prompt = f"""
            {personality}
            Answer this question about college football.

            Question: {question}

            IMPORTANT INSTRUCTIONS:
            - Provide helpful, accurate information about college football
            - Be extremely sarcastic and witty, like a completely insane but knowledgeable CFB fan
            - You can discuss teams, players, games, rankings, history, etc.
            - If you don't know something, say so with sarcasm
            - Keep responses informative but hilariously sarcastic
            - Do NOT make up specific league schedules, rosters, or game results
            """

        data = {
            'model': 'claude-3-haiku-20240307',
            'max_tokens': max_tokens,
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }

        try:
            # Log the request details
            logger.info(f"🤖 Asking Anthropic: {question[:100]}...")
            logger.info(f"📝 Full prompt length: {len(prompt)} characters")
            logger.info(f"📄 Context length: {len(context)} characters")

            # Estimate token count (rough approximation: 1 token ≈ 4 characters)
            estimated_tokens = len(prompt) // 4
            logger.info(f"🔢 Estimated input tokens: ~{estimated_tokens}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    'https://api.anthropic.com/v1/messages',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Extract token usage information
                        usage = result.get('usage', {})
                        input_tokens = usage.get('input_tokens', 0)
                        output_tokens = usage.get('output_tokens', 0)

                        # Update token counters
                        total_tokens = input_tokens + output_tokens
                        self.total_anthropic_tokens += total_tokens
                        self.total_requests += 1

                        # Save updated stats
                        await self._save_usage_stats()

                        logger.info(f"✅ Anthropic response received")
                        logger.info(f"🔢 Token usage - Input: {input_tokens}, Output: {output_tokens}")
                        logger.info(f"📊 Total Anthropic tokens used: {self.total_anthropic_tokens} (across {self.total_requests} requests)")

                        response_text = result['content'][0]['text'].strip()
                        logger.info(f"📝 Response length: {len(response_text)} characters")

                        return response_text
                    else:
                        error_text = await response.text()
                        logger.error(f"Anthropic API error: {response.status} - {error_text}")
                        return None
        except Exception as e:
            logger.error(f"Error calling Anthropic: {e}")
            return None

    async def ask_ai(self, question: str, user_info: str = None, include_league_context: bool = True) -> Optional[str]:
        """Ask AI about the charter (tries OpenAI first, then Anthropic)

        Args:
            question: The question to ask
            user_info: User info for logging
            include_league_context: Whether to include league schedule/charter info (False for non-league servers)
        """
        # Load usage stats on first use
        await self._load_usage_stats()

        if user_info:
            logger.info(f"🤖 AI asked by {user_info}: {question[:100]}...")
        else:
            logger.info(f"🤖 AI asked: {question[:100]}...")

        context = await self.get_charter_content()

        # Use empty context if no charter content available
        if not context:
            context = "No charter content available. Please provide general information about CFB 26 league rules, recruiting, transfers, or dynasty management."
            logger.info("📄 Using fallback context (no charter content)")
        else:
            logger.info(f"📄 Using charter context ({len(context)} characters)")

        # Try OpenAI first
        logger.info(f"🔄 Trying OpenAI... (include_league_context={include_league_context})")
        response = await self.ask_openai(question, context, include_league_context=include_league_context)
        if response:
            logger.info("✅ OpenAI response received")
            return response

        # Fallback to Anthropic
        logger.info("🔄 Trying Anthropic...")
        response = await self.ask_anthropic(question, context, include_league_context=include_league_context)
        if response:
            logger.info("✅ Anthropic response received")
        else:
            logger.warning("❌ No AI response from either provider")
        return response

    def get_token_usage(self) -> dict:
        """Get current token usage statistics with cost estimates"""
        openai_cost = (self.total_openai_tokens / 1000) * self.openai_cost_per_1k
        anthropic_cost = (self.total_anthropic_tokens / 1000) * self.anthropic_cost_per_1k
        total_cost = openai_cost + anthropic_cost

        return {
            'total_requests': self.total_requests,
            'openai_tokens': self.total_openai_tokens,
            'anthropic_tokens': self.total_anthropic_tokens,
            'total_tokens': self.total_openai_tokens + self.total_anthropic_tokens,
            'openai_cost': openai_cost,
            'anthropic_cost': anthropic_cost,
            'total_cost': total_cost
        }

    async def get_openai_usage_from_api(self, date: str = None) -> Optional[dict]:
        """Query OpenAI Usage API for official usage statistics for a specific date

        Args:
            date: Date to query (YYYY-MM-DD format). Defaults to today.

        Returns:
            Dictionary with usage data or None if unavailable

        Note: OpenAI Usage API returns daily usage data. For historical data,
              check the OpenAI Dashboard at https://platform.openai.com/usage
        """
        if not self.openai_api_key:
            logger.warning("⚠️ OpenAI API key not found")
            return None

        headers = {
            'Authorization': f'Bearer {self.openai_api_key}',
            'Content-Type': 'application/json'
        }

        # Use provided date or default to today (YYYY-MM-DD format)
        from datetime import datetime
        if not date:
            date = datetime.now().strftime('%Y-%m-%d')

        # OpenAI Usage API takes a single 'date' parameter for daily usage
        params = {
            'date': date
        }

        try:
            logger.info(f"📊 Querying OpenAI Usage API (date: {date})...")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.openai.com/v1/usage',
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Retrieved OpenAI usage data")
                        return data
                    else:
                        error_text = await response.text()
                        logger.warning(f"⚠️ OpenAI Usage API error: {response.status} - {error_text}")
                        return None
        except asyncio.TimeoutError:
            logger.warning("⚠️ OpenAI Usage API timeout")
            return None
        except Exception as e:
            logger.error(f"❌ Error querying OpenAI Usage API: {e}")
            return None

    def log_token_summary(self):
        """Log a summary of token usage with cost estimates"""
        stats = self.get_token_usage()
        logger.info(f"📊 AI Token Usage Summary:")
        logger.info(f"   Total Requests: {stats['total_requests']}")
        logger.info(f"   OpenAI Tokens: {stats['openai_tokens']:,} (${stats['openai_cost']:.4f})")
        logger.info(f"   Anthropic Tokens: {stats['anthropic_tokens']:,} (${stats['anthropic_cost']:.4f})")
        logger.info(f"   Total Tokens: {stats['total_tokens']:,}")
        logger.info(f"   💰 Estimated Total Cost: ${stats['total_cost']:.4f}")

def setup_ai_integration():
    """Setup instructions for AI integration"""
    print("🤖 AI Integration Setup Instructions:")
    print("=" * 50)
    print("Choose your AI provider:")
    print()
    print("1. OpenAI (GPT-3.5/GPT-4)")
    print("   - Go to: https://platform.openai.com/api-keys")
    print("   - Create an API key")
    print("   - Add to .env: OPENAI_API_KEY=your_key_here")
    print()
    print("2. Anthropic (Claude)")
    print("   - Go to: https://console.anthropic.com/")
    print("   - Create an API key")
    print("   - Add to .env: ANTHROPIC_API_KEY=your_key_here")
    print()
    print("3. Both (recommended for reliability)")
    print("   - Set up both APIs")
    print("   - Bot will try OpenAI first, then Anthropic as fallback")
    print()
    print("📝 Note: AI integration is optional. The bot works great without it!")

if __name__ == "__main__":
    setup_ai_integration()
