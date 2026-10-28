#!/usr/bin/env python3
"""
AI Integration for CFB League Bot
This module handles AI-powered responses about the league charter
"""

import asyncio
import logging
import os
from typing import Optional

import aiohttp
from dotenv import load_dotenv

from ..utils.halloween import is_halloween, spookify, spooky_personality
from ..utils.server_config import HARRY_PERSONALITY
from ..utils.storage import get_storage
from ..security import HTTP_TIMEOUT, sanitize_ai_response

from ..config import (ANTHROPIC_COST_PER_1K, ANTHROPIC_MODEL, GAME_NAME,
                      OPENAI_COST_PER_1K, OPENAI_MODEL)

# Load environment variables
load_dotenv()

logger = logging.getLogger('CFBBot.AI')

# Reasoning models bill thinking against the completion cap; give the answer room,
# but don't let a long request (a charter rewrite) turn into a huge, slow, costly call.
REASONING_TOKEN_HEADROOM = 4
REASONING_TOKEN_CEILING = 16000


def openai_request_body(model: str, system: str, prompt: str, max_tokens: int) -> dict:
    """
    Build the OpenAI chat-completions body for a model.

    The GPT-5 and o-series models renamed max_tokens to max_completion_tokens and only
    accept the default temperature, so sending the older parameters 400s every call.
    """
    body = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt},
        ],
    }
    newer_model = model.startswith(('gpt-5', 'o1', 'o3', 'o4'))
    if newer_model:
        # These models spend tokens on internal reasoning out of the same budget, so a
        # tight cap gets used up before any visible text and the reply comes back blank.
        # Keep reasoning light and leave room for the answer.
        body['max_completion_tokens'] = min(
            max(max_tokens * REASONING_TOKEN_HEADROOM, 2000), REASONING_TOKEN_CEILING)
        body['reasoning_effort'] = 'low'
    else:
        body['max_tokens'] = max_tokens
        body['temperature'] = 0.7
    return body


def user_team_names() -> list:
    """The league's user-controlled teams, from the live schedule (not a stale literal)."""
    try:
        from ..utils.schedule_manager import get_schedule_manager
        schedule_mgr = get_schedule_manager()
        return list(schedule_mgr.teams) if schedule_mgr else []
    except Exception as e:
        logger.debug(f"Could not read user teams: {e}")
        return []


def league_prompt(personality: str, charter: str, schedule: str, question: str) -> str:
    """
    Prompt for a league server.

    Harry used to get a mandatory "schedule formatting" block on every question, so he
    answered "why are you wearing corn gear?" with this week's fixtures. The schedule
    rules now apply only when he's actually listing games.
    """
    teams = user_team_names()
    teams_line = (", ".join(teams) if teams
                  else "(none configured - don't claim to support any team)")
    return f"""
            {personality}

            ANSWER THE QUESTION THAT WAS ASKED. Keep it short - a couple of sentences unless
            they asked for a list. Do not volunteer the schedule, the charter, or this week's
            games unless the question calls for it.

            The league's user-controlled teams RIGHT NOW: {teams_line}
            That list is authoritative. The charter below may still name teams and coaches
            from past seasons - never present those as current.

            Question: {question}

            Reference material (use ONLY what the question needs, ignore the rest):

            League Charter:
            {charter}

            League Schedule:
            {schedule}

            Guidelines:
            - Be extremely sarcastic and witty, like a completely insane but knowledgeable league member
            - If the answer isn't in the material above, say so with sarcasm; don't invent games,
              rosters or results
            - Don't mention "the charter" unless you genuinely can't answer
            - ONLY when listing games: one per line, user teams bolded, e.g.
              🏈 **{teams[0] if teams else 'YourTeam'}** @ Opponent
            """


class AICharterAssistant:
    """AI-powered assistant for league charter questions"""

    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        # Charter URL (configurable via environment variable)

        # Token usage tracking (loaded from storage)
        self.total_openai_tokens = 0
        self.total_anthropic_tokens = 0
        self.total_requests = 0

        # Cost tracking (per 1k tokens - averaged input/output), from config.py
        self.openai_cost_per_1k = OPENAI_COST_PER_1K
        self.anthropic_cost_per_1k = ANTHROPIC_COST_PER_1K

        # Storage
        self._storage = get_storage()
        self._loaded = False
        
        # Response cache (question hash -> response, timestamp)
        self._response_cache = {}
        self._cache_ttl = 3600  # 1 hour cache TTL

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
                logger.info(f"Loaded AI usage stats: {self.total_requests:,} requests, {self.total_openai_tokens + self.total_anthropic_tokens:,} tokens")
            else:
                logger.info("No existing AI usage stats found - starting fresh")
            self._loaded = True
        except Exception as e:
            logger.warning(f"Failed to load AI usage stats: {e}")
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
            logger.debug("Saved AI usage stats")
        except Exception as e:
            logger.error(f"Failed to save AI usage stats: {e}")

    async def _record_ai_cost(self, amount: float):
        """Record AI cost with the cost tracker for /admin budget and alerts."""
        if amount <= 0:
            return
        try:
            from ..utils.cost_tracker import get_cost_tracker
            await get_cost_tracker().record_cost('ai', amount)
            logger.info(f"Recorded ${amount:.4f} AI cost for /admin budget")
        except Exception as e:
            logger.warning(f"Failed to record AI cost for budget (/admin budget will not update): {e}")

    async def get_charter_content(self) -> Optional[str]:
        """Get charter content for AI context"""
        # Try to get content from local file first
        try:
            from ..config import CHARTER_FILE, CHARTER_FILE_LEGACY
            charter_file = CHARTER_FILE if os.path.exists(CHARTER_FILE) else CHARTER_FILE_LEGACY
            if os.path.exists(charter_file):
                with open(charter_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        logger.info(f"Loaded local charter content ({len(content)} characters)")
                        return content
        except Exception as e:
            logger.warning(f"Local charter file failed: {e}")

        # No charter content available
        logger.info("No charter content available - using fallback context")
        return None

    @staticmethod
    def _timer_context(timekeeper) -> list:
        """
        Lines describing the live advance countdown.

        Without these Harry falls back to the charter's written cadence ("Tuesday and
        Friday at 9am"), which is the policy, not the deadline people actually face.
        """
        try:
            from ..utils.timekeeper import format_est_time

            channel = timekeeper.get_advance_channel()
            status = timekeeper.get_status(channel) if channel else {'active': False}

            if not status.get('active'):
                return ["**ADVANCE TIMER: not running right now.** Nobody is on the clock.", ""]

            deadline = format_est_time(status.get('end_time'), '%A, %B %d at %I:%M %p')
            return [
                f"**ADVANCE TIMER: {status['hours']}h {status['minutes']}m left** "
                f"(deadline {deadline}).",
                "IMPORTANT: For 'when is the advance / how long have we got', use this live "
                "countdown. The charter's advance cadence is league policy, not the current deadline.",
                "",
            ]
        except Exception as e:
            logger.debug(f"Could not get timer context: {e}")
            return []

    def get_schedule_context(self) -> str:
        """Get schedule context for AI queries, including current week info"""
        context_parts = []

        # Current week/season from the live timekeeper in bot_main
        try:
            from .. import bot_main as bot_module
            from ..utils.timekeeper import TOTAL_WEEKS_PER_SEASON
            if hasattr(bot_module, 'timekeeper_manager') and bot_module.timekeeper_manager:
                season_info = bot_module.timekeeper_manager.get_season_week()
                if season_info.get('season') and season_info.get('week') is not None:
                    current_week = season_info['week']
                    current_season = season_info['season']
                    week_name = season_info.get('week_name', f"Week {current_week}")
                    phase = season_info.get('phase', 'Unknown')

                    game_week = season_info.get('game_week')

                    context_parts.append(f"**CURRENT STATUS: Season {current_season}, {week_name} (step {current_week} of {TOTAL_WEEKS_PER_SEASON})**")
                    context_parts.append(f"Phase: {phase}")
                    if game_week is not None:
                        context_parts.append(f"IMPORTANT: When the user says 'this week' or 'current week', they mean Week {game_week} in the schedule below.")
                    else:
                        context_parts.append(f"IMPORTANT: It is currently {week_name} ({phase}), so there are no regular-season schedule games this week.")
                    context_parts.append("")

                context_parts.extend(self._timer_context(bot_module.timekeeper_manager))
        except Exception as e:
            logger.debug(f"Could not get current week context: {e}")

        # Get full schedule
        try:
            from ..utils.schedule_manager import get_schedule_manager
            schedule_mgr = get_schedule_manager()
            if schedule_mgr:
                context_parts.append(schedule_mgr.get_schedule_context_for_ai())
        except Exception as e:
            logger.warning(f"Could not get schedule context: {e}")

        return "\n".join(context_parts)

    def _get_cache_key(self, question: str, include_league_context: bool) -> str:
        """Generate cache key from question"""
        import hashlib
        # Normalize question (lowercase, strip whitespace)
        normalized = question.lower().strip()
        # Add context flag to key
        cache_str = f"{normalized}:{include_league_context}"
        return hashlib.md5(cache_str.encode()).hexdigest()

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached response if available and not expired"""
        import time
        if cache_key in self._response_cache:
            cached_response, timestamp = self._response_cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.info("Cache hit for question (saved ~$0.001)")
                return cached_response
            else:
                # Expired, remove from cache
                del self._response_cache[cache_key]
        return None

    def clear_response_cache(self) -> None:
        """Forget cached answers, e.g. after a new schedule upload, so Harry doesn't repeat stale ones."""
        self._response_cache.clear()

    def _cache_response(self, cache_key: str, response: str):
        """Cache a response"""
        import time
        self._response_cache[cache_key] = (response, time.time())
        logger.debug(f"Cached response (key: {cache_key[:8]}...)")

    def _build_prompt(self, question: str, context: str, personality_prompt: Optional[str],
                      include_league_context: bool) -> tuple:
        """Harry's persona plus the question, with league charter/schedule when asked for."""
        # Harry's one persona (includes the never-reveal-secrets rule)
        personality = personality_prompt or HARRY_PERSONALITY
        if include_league_context:
            return personality, league_prompt(personality, context, self.get_schedule_context(), question)
        # Generic CFB assistant mode (no league-specific data)
        return personality, f"""
            {personality}
            Answer this question about college football.

            Question: {question}

            IMPORTANT INSTRUCTIONS:
            - Provide helpful, accurate information about college football
            - Be extremely sarcastic and witty, like a completely insane but knowledgeable CFB fan
            - You can discuss teams, players, games, rankings, history, etc.
            - If you don't know something, say so with sarcasm
            - Do NOT make up specific league schedules, rosters, or game results
            """

    async def _post(self, provider: str, url: str, headers: dict, body: dict) -> Optional[dict]:
        """POST to a provider and return its JSON, or None (logged) on any failure."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=body,
                                        timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT)) as response:
                    if response.status == 200:
                        return await response.json()
                    from ..utils.log_utils import sanitize_for_log
                    logger.error(f"{provider} API error: {response.status} - {sanitize_for_log(await response.text())}")
        except Exception as e:
            logger.error(f"Error calling {provider}: {e}")
        return None

    async def _record_usage(self, provider: str, tokens: int, cost_per_1k: float):
        """Count a billed request toward /admin budget and alerts, even if it came back empty."""
        self.total_requests += 1
        await self._save_usage_stats()
        await self._record_ai_cost((tokens / 1000) * cost_per_1k)
        logger.info(f"{provider} used {tokens} tokens")

    def _finish(self, cache_key: str, text: str) -> str:
        """Sanitize and cache a reply."""
        text = sanitize_ai_response(text)  # never send keys/secrets to users (sneaky prompts)
        self._cache_response(cache_key, text)
        return text

    async def ask_openai(self, question: str, context: str, max_tokens: int = 500, personality_prompt: str = None, include_league_context: bool = True) -> Optional[str]:
        """Ask OpenAI. max_tokens caps the answer - raise it for long output like a charter rewrite."""
        cache_key = self._get_cache_key(question, include_league_context)
        cached = self._get_cached_response(cache_key)
        if cached:
            return sanitize_ai_response(cached)
        if not self.openai_api_key:
            logger.warning("OpenAI API key not found")
            return None

        personality, prompt = self._build_prompt(question, context, personality_prompt, include_league_context)
        data = openai_request_body(
            OPENAI_MODEL,
            f'{personality} Be hilariously sarcastic and helpful.',
            prompt,
            max_tokens,
        )
        logger.info(f"Asking OpenAI: {question[:100]}... (prompt ~{len(prompt) // 4} tokens)")
        result = await self._post('OpenAI', 'https://api.openai.com/v1/chat/completions',
                                  {'Authorization': f'Bearer {self.openai_api_key}', 'Content-Type': 'application/json'},
                                  data)
        if not result:
            return None

        usage = result.get('usage', {})
        self.total_openai_tokens += usage.get('total_tokens', 0)
        await self._record_usage('OpenAI', usage.get('total_tokens', 0), self.openai_cost_per_1k)

        choice = result['choices'][0]
        text = (choice['message'].get('content') or '').strip()
        if not text:
            # Usually a reasoning model using the whole completion budget
            # before writing anything; say so instead of failing silently.
            logger.error(
                f"OpenAI returned no text (model={OPENAI_MODEL}, "
                f"finish_reason={choice.get('finish_reason')}, "
                f"completion_tokens={usage.get('completion_tokens', 0)}, "
                f"reasoning_tokens={usage.get('completion_tokens_details', {}).get('reasoning_tokens', 0)}) - "
                f"raise the token cap or lower reasoning_effort"
            )
            return None

        return self._finish(cache_key, text)

    async def ask_anthropic(self, question: str, context: str, max_tokens: int = 500, personality_prompt: str = None, include_league_context: bool = True) -> Optional[str]:
        """Ask Anthropic. Same contract as ask_openai."""
        cache_key = self._get_cache_key(question, include_league_context)
        cached = self._get_cached_response(cache_key)
        if cached:
            return sanitize_ai_response(cached)
        if not self.anthropic_api_key:
            logger.warning("Anthropic API key not found")
            return None

        personality, prompt = self._build_prompt(question, context, personality_prompt, include_league_context)
        data = {
            'model': ANTHROPIC_MODEL,
            'max_tokens': max_tokens,
            'system': personality,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        logger.info(f"Asking Anthropic: {question[:100]}... (prompt ~{len(prompt) // 4} tokens)")
        result = await self._post('Anthropic', 'https://api.anthropic.com/v1/messages',
                                  {'x-api-key': self.anthropic_api_key, 'Content-Type': 'application/json',
                                   'anthropic-version': '2023-06-01'},
                                  data)
        if not result:
            return None

        usage = result.get('usage', {})
        tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
        self.total_anthropic_tokens += tokens
        await self._record_usage('Anthropic', tokens, self.anthropic_cost_per_1k)
        return self._finish(cache_key, result['content'][0]['text'].strip())

    async def ask_ai(self, question: str, user_info: str = None, include_league_context: bool = True, max_tokens: int = 500,
                     personality_prompt: Optional[str] = None) -> Optional[str]:
        """Ask AI about the charter (tries OpenAI first, then Anthropic)

        Args:
            question: The question to ask
            user_info: User info for logging
            include_league_context: Whether to include league schedule/charter info (False for non-league servers)
            personality_prompt: Persona override (default: Harry); keep SECRETS_RULE in any override
        """
        # Load usage stats on first use
        await self._load_usage_stats()

        # Halloween week haunts Harry's own voice; persona overrides (charter work) stay plain
        spooky = personality_prompt is None and is_halloween()
        if spooky:
            personality_prompt = spooky_personality(HARRY_PERSONALITY)

        if user_info:
            logger.info(f"AI asked by {user_info}: {question[:100]}...")
        else:
            logger.info(f"AI asked: {question[:100]}...")

        context = await self.get_charter_content()

        # Use empty context if no charter content available
        if not context:
            context = f"No charter content available. Please provide general information about {GAME_NAME} league rules, recruiting, transfers, or dynasty management."
            logger.info("Using fallback context (no charter content)")
        else:
            logger.info(f"Using charter context ({len(context)} characters)")

        # Try OpenAI first
        logger.info(f"Trying OpenAI... (include_league_context={include_league_context})")
        response = await self.ask_openai(question, context, max_tokens=max_tokens, personality_prompt=personality_prompt,
                                         include_league_context=include_league_context)
        if response:
            logger.info("OpenAI response received")
            return spookify(response) if spooky else response

        # Fallback to Anthropic
        logger.info("Trying Anthropic...")
        response = await self.ask_anthropic(question, context, max_tokens=max_tokens, personality_prompt=personality_prompt,
                                            include_league_context=include_league_context)
        if response:
            logger.info("Anthropic response received")
            return spookify(response) if spooky else response
        logger.warning("No AI response from either provider")
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
            logger.warning("OpenAI API key not found")
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
            logger.info(f"Querying OpenAI Usage API (date: {date})...")
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.openai.com/v1/usage',
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Retrieved OpenAI usage data")
                        return data
                    else:
                        error_text = await response.text()
                        from ..utils.log_utils import sanitize_for_log
                        logger.warning(f"OpenAI Usage API error: {response.status} - {sanitize_for_log(error_text)}")
                        return None
        except asyncio.TimeoutError:
            logger.warning("OpenAI Usage API timeout")
            return None
        except Exception as e:
            logger.error(f"Error querying OpenAI Usage API: {e}")
            return None

    async def get_openai_cost_for_current_month(self) -> Optional[float]:
        """Fetch OpenAI usage for each day in the current month and return estimated cost (USD).

        Uses the OpenAI Usage API (one request per day). Cost is estimated from token counts
        using openai_cost_per_1k. Returns None if API key missing or API errors.
        """
        if not self.openai_api_key:
            return None
        from datetime import date, timedelta
        today = date.today()
        first = today.replace(day=1)
        total_tokens = 0
        day = first
        while day <= today:
            data = await self.get_openai_usage_from_api(date=day.strftime('%Y-%m-%d'))
            if data and data.get('data'):
                for entry in data['data']:
                    total_tokens += entry.get('n_context_tokens_total', 0) + entry.get('n_generated_tokens_total', 0)
            day += timedelta(days=1)
        if total_tokens == 0:
            return 0.0
        return (total_tokens / 1000) * self.openai_cost_per_1k


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
