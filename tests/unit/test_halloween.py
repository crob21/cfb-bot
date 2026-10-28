"""Spooky Halloween Harry: the week he's on, his haunted replies, and who gets which reaction."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cfb_bot.utils import halloween
from cfb_bot.utils.halloween import (
    GHOST,
    GRAVESTONE,
    PUMPKIN,
    halloween_reaction,
    is_halloween,
    parse_reactions,
    spookify,
)


def member(name, id=1, display_name=None, global_name=None, nick=None):
    return SimpleNamespace(id=id, name=name, display_name=display_name or name,
                           global_name=global_name, nick=nick)


class TestHalloweenWeek:
    @pytest.mark.parametrize("day", [date(2026, 10, 25), date(2026, 10, 28), date(2026, 10, 31)])
    def test_on_halloween_week(self, day):
        assert is_halloween(day)

    @pytest.mark.parametrize("day", [date(2026, 10, 24), date(2026, 11, 1), date(2026, 3, 31)])
    def test_off_the_rest_of_the_year(self, day):
        assert not is_halloween(day)


class TestSpookify:
    def test_adds_ghost_and_pumpkin_when_missing(self):
        assert spookify("Fuck Oregon!") == f"Fuck Oregon! {GHOST}{PUMPKIN}"

    def test_leaves_an_already_spooky_reply_alone(self):
        assert spookify(f"Boo {PUMPKIN}") == f"Boo {PUMPKIN}"


class TestReactions:
    def test_default_league_reactions(self):
        assert halloween_reaction(member("Mundie")) == PUMPKIN
        assert halloween_reaction(member("wustman")) == GHOST
        assert halloween_reaction(member("jaywill9")) == GRAVESTONE

    def test_matches_nickname_and_partial_names(self):
        assert halloween_reaction(member("someone", nick="Big Mundie")) == PUMPKIN
        assert halloween_reaction(member("xX_wustman_Xx")) == GHOST

    def test_everyone_else_gets_nothing(self):
        assert halloween_reaction(member("craig")) is None

    def test_matches_user_id(self):
        assert halloween_reaction(member("anon", id=42), {"42": "🦇"}) == "🦇"

    def test_parse_skips_malformed_pairs(self):
        assert parse_reactions("a:🎃, nope ,:👻,b:") == {"a": "🎃"}


class TestSpookyAI:
    @pytest.fixture
    def assistant(self):
        from cfb_bot.ai.ai_integration import AICharterAssistant
        a = AICharterAssistant.__new__(AICharterAssistant)
        a._load_usage_stats = AsyncMock()
        a.get_charter_content = AsyncMock(return_value="charter")
        a.ask_openai = AsyncMock(return_value="Bloody Ducks")
        a.ask_anthropic = AsyncMock(return_value=None)
        return a

    async def test_halloween_haunts_harry(self, assistant):
        with patch('cfb_bot.ai.ai_integration.is_halloween', return_value=True):
            reply = await assistant.ask_ai("who's winning?")
        assert reply == f"Bloody Ducks {GHOST}{PUMPKIN}"
        assert halloween.SPOOKY_PERSONALITY in assistant.ask_openai.call_args.kwargs['personality_prompt']

    async def test_charter_persona_stays_plain(self, assistant):
        with patch('cfb_bot.ai.ai_integration.is_halloween', return_value=True):
            reply = await assistant.ask_ai("write a rule", personality_prompt="plain")
        assert reply == "Bloody Ducks"
        assert assistant.ask_openai.call_args.kwargs['personality_prompt'] == "plain"

    async def test_normal_harry_after_halloween(self, assistant):
        with patch('cfb_bot.ai.ai_integration.is_halloween', return_value=False):
            assert await assistant.ask_ai("who's winning?") == "Bloody Ducks"
