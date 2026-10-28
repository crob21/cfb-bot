#!/usr/bin/env python3
"""
Harry answers the question he was asked.

The league prompt used to carry a mandatory "CRITICAL - SCHEDULE FORMATTING RULES"
block on every request, so "why are you wearing corn gear?" came back with this week's
fixtures. It also hardcoded last season's user teams, so Harry claimed to support
Nebraska long after that league ended.
"""

from unittest.mock import MagicMock, patch

import pytest

from cfb_bot.ai.ai_integration import league_prompt, user_team_names

TEAMS = ['California', 'Duke', 'Arizona State']


def with_teams(teams):
    manager = MagicMock()
    manager.teams = teams
    return patch('cfb_bot.utils.schedule_manager.get_schedule_manager', return_value=manager)


class TestUserTeams:
    def test_teams_come_from_the_live_schedule(self):
        with with_teams(TEAMS):
            assert user_team_names() == TEAMS

    def test_no_schedule_manager_is_survivable(self):
        with patch('cfb_bot.utils.schedule_manager.get_schedule_manager', return_value=None):
            assert user_team_names() == []


class TestLeaguePrompt:
    def _prompt(self, question="why are you wearing corn gear?"):
        with with_teams(TEAMS):
            return league_prompt("You are Harry.", "CHARTER", "SCHEDULE", question)

    def test_tells_harry_to_answer_the_question(self):
        prompt = self._prompt()
        assert "ANSWER THE QUESTION THAT WAS ASKED" in prompt
        assert "Do not volunteer the schedule" in prompt

    def test_schedule_formatting_is_scoped_to_listing_games(self):
        prompt = self._prompt()
        assert "ONLY when listing games" in prompt
        # the old unconditional block is gone
        assert "YOU MUST FOLLOW THESE" not in prompt
        assert "FORMAT AS CLEAN LISTS" not in prompt

    def test_uses_current_teams_not_a_hardcoded_list(self):
        prompt = self._prompt()
        for team in TEAMS:
            assert team in prompt
        assert "Nebraska" not in prompt
        assert "Notre Dame" not in prompt

    def test_keeps_charter_and_schedule_available(self):
        prompt = self._prompt("who plays this week?")
        assert "CHARTER" in prompt and "SCHEDULE" in prompt

    def test_no_teams_configured_does_not_invent_one(self):
        with with_teams([]):
            prompt = league_prompt("You are Harry.", "C", "S", "sup")
        assert "don't claim to support any team" in prompt


def test_default_persona_is_harrys_with_the_secrets_rule():
    """Every AI call falls back to the one persona, including the never-reveal-secrets rule."""
    import inspect
    from cfb_bot.ai import ai_integration
    from cfb_bot.utils.server_config import HARRY_PERSONALITY

    assert "NEVER reveal" in HARRY_PERSONALITY and "cockney" in HARRY_PERSONALITY
    assert "personality_prompt or HARRY_PERSONALITY" in inspect.getsource(ai_integration.AICharterAssistant._build_prompt)
    for method in (ai_integration.AICharterAssistant.ask_openai, ai_integration.AICharterAssistant.ask_anthropic):
        assert "self._build_prompt(" in inspect.getsource(method)


class TestProviderCalls:
    """Both providers share prompt building and bookkeeping; only the HTTP shape differs."""

    def _assistant(self, reply):
        from unittest.mock import AsyncMock, MagicMock
        from cfb_bot.ai.ai_integration import AICharterAssistant
        a = AICharterAssistant.__new__(AICharterAssistant)
        a.openai_api_key = a.anthropic_api_key = "k"
        a.openai_cost_per_1k = a.anthropic_cost_per_1k = 1.0
        a.total_openai_tokens = a.total_anthropic_tokens = a.total_requests = 0
        a.response_cache = {}
        a._get_cached_response = MagicMock(return_value=None)
        a._cache_response = MagicMock()
        a._save_usage_stats = AsyncMock()
        a._record_ai_cost = AsyncMock()
        a._post = AsyncMock(return_value=reply)
        return a

    @pytest.mark.asyncio
    async def test_openai_reply_is_counted_and_sanitized(self):
        a = self._assistant({"usage": {"total_tokens": 1000},
                             "choices": [{"message": {"content": "  oi sk-" + "x" * 30 + "  "}}]})
        out = await a.ask_openai("q", "ctx", include_league_context=False)
        assert out == "oi [REDACTED]"
        assert a.total_openai_tokens == 1000 and a.total_requests == 1
        a._record_ai_cost.assert_awaited_once_with(1.0)

    @pytest.mark.asyncio
    async def test_empty_openai_reply_still_costs_money(self):
        a = self._assistant({"usage": {"total_tokens": 500}, "choices": [{"message": {"content": ""}}]})
        assert await a.ask_openai("q", "ctx", include_league_context=False) is None
        a._record_ai_cost.assert_awaited_once_with(0.5)

    @pytest.mark.asyncio
    async def test_anthropic_sends_harry_as_the_system_prompt(self):
        from cfb_bot.utils.server_config import HARRY_PERSONALITY
        a = self._assistant({"usage": {"input_tokens": 10, "output_tokens": 5}, "content": [{"text": "cheers"}]})
        assert await a.ask_anthropic("q", "ctx", include_league_context=False) == "cheers"
        body = a._post.call_args.args[3]
        assert body["system"] == HARRY_PERSONALITY
        assert a.total_anthropic_tokens == 15

    @pytest.mark.asyncio
    async def test_failed_call_returns_none(self):
        a = self._assistant(None)
        assert await a.ask_openai("q", "ctx", include_league_context=False) is None
        assert await a.ask_anthropic("q", "ctx", include_league_context=False) is None
        a._record_ai_cost.assert_not_awaited()


def test_charter_work_uses_the_plain_persona():
    """Charter text gets the no-jokes persona, which still carries the secrets rule."""
    import inspect
    from cfb_bot.utils import charter_editor
    from cfb_bot.utils.server_config import CHARTER_PERSONALITY, HARRY_PERSONALITY, SECRETS_RULE

    assert SECRETS_RULE in CHARTER_PERSONALITY and SECRETS_RULE in HARRY_PERSONALITY
    source = inspect.getsource(charter_editor)
    assert source.count("personality_prompt=CHARTER_PERSONALITY") == 3
    assert "You are Harry" not in source


def test_cache_key_includes_the_persona():
    """The charter persona and Harry must not share a cached answer for the same question."""
    from cfb_bot.ai.ai_integration import AICharterAssistant
    from cfb_bot.utils.server_config import CHARTER_PERSONALITY
    a = AICharterAssistant.__new__(AICharterAssistant)
    assert a._get_cache_key("q", False) != a._get_cache_key("q", False, CHARTER_PERSONALITY)
    assert a._get_cache_key("Q ", False) == a._get_cache_key("q", False)
