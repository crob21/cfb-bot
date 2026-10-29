"""Holiday Harry: when he's dressed up, his festive replies, and who gets which reaction."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from cfb_bot.utils.holidays import (CHRISTMAS, GHOST, GRAVESTONE, HALLOWEEN, PUMPKIN, THANKSGIVING,
                                    current_holiday, emoji_this_reply, festive, holiday_reaction, parse_reactions,
                                    thanksgiving_day)


def member(name, id=1, display_name=None, global_name=None, nick=None):
    return SimpleNamespace(id=id, name=name, display_name=display_name or name,
                           global_name=global_name, nick=nick)


class TestCalendar:
    @pytest.mark.parametrize("year, day", [(2026, 26), (2027, 25), (2028, 23), (2029, 22)])
    def test_thanksgiving_is_the_fourth_thursday(self, year, day):
        assert thanksgiving_day(year) == date(year, 11, day)

    @pytest.mark.parametrize("day, holiday", [
        (date(2026, 10, 24), None),
        (date(2026, 10, 25), HALLOWEEN),
        (date(2026, 10, 31), HALLOWEEN),
        (date(2026, 11, 1), None),
        (date(2026, 11, 22), None),           # Sunday before Thanksgiving week
        (date(2026, 11, 23), THANKSGIVING),   # Monday
        (date(2026, 11, 26), THANKSGIVING),   # Thanksgiving
        (date(2026, 11, 29), THANKSGIVING),   # Sunday after
        (date(2026, 11, 30), None),
        (date(2026, 12, 17), None),
        (date(2026, 12, 18), CHRISTMAS),
        (date(2026, 12, 25), CHRISTMAS),
        (date(2026, 12, 26), CHRISTMAS),
        (date(2026, 12, 27), None),
        (date(2027, 3, 31), None),
    ])
    def test_holiday_on(self, day, holiday):
        assert current_holiday(day) is holiday


class TestEmojiNowAndThen:
    def test_some_replies_get_emoji(self):
        assert emoji_this_reply(roll=0.1)

    def test_most_replies_dont(self):
        assert not emoji_this_reply(roll=0.9)


class TestFestive:
    def test_adds_the_holiday_emoji_when_missing(self):
        assert festive("Fuck Oregon!", HALLOWEEN) == f"Fuck Oregon! {GHOST}{PUMPKIN}"
        assert festive("Fuck Oregon!", THANKSGIVING) == "Fuck Oregon! 🦃🥧"
        assert festive("Fuck Oregon!", CHRISTMAS) == "Fuck Oregon! 🎄🎅"

    def test_leaves_an_already_festive_reply_alone(self):
        assert festive(f"Boo {PUMPKIN}", HALLOWEEN) == f"Boo {PUMPKIN}"


class TestReactions:
    def test_halloween_league_reactions(self):
        assert holiday_reaction(member("Mundie"), HALLOWEEN) == PUMPKIN
        assert holiday_reaction(member("wustman"), HALLOWEEN) == GHOST
        assert holiday_reaction(member("jaywill9"), HALLOWEEN) == GRAVESTONE

    def test_matches_nickname_and_partial_names(self):
        assert holiday_reaction(member("someone", nick="Big Mundie"), HALLOWEEN) == PUMPKIN
        assert holiday_reaction(member("xX_wustman_Xx"), HALLOWEEN) == GHOST

    def test_everyone_else_gets_nothing(self):
        assert holiday_reaction(member("craig"), HALLOWEEN) is None

    def test_no_reactions_outside_halloween(self):
        assert holiday_reaction(member("Mundie"), THANKSGIVING) is None
        assert holiday_reaction(member("Mundie"), CHRISTMAS) is None
        assert holiday_reaction(member("Mundie"), None) is None

    def test_matches_user_id(self):
        assert holiday_reaction(member("anon", id=42), HALLOWEEN, {"42": "🦇"}) == "🦇"

    def test_parse_skips_malformed_pairs(self):
        assert parse_reactions("a:🎃, nope ,:👻,b:") == {"a": "🎃"}


class TestHolidayAI:
    @pytest.fixture
    def assistant(self):
        from cfb_bot.ai.ai_integration import AICharterAssistant
        a = AICharterAssistant.__new__(AICharterAssistant)
        a._load_usage_stats = AsyncMock()
        a.get_charter_content = AsyncMock(return_value="charter")
        a.ask_openai = AsyncMock(return_value="Bloody Ducks")
        a.ask_anthropic = AsyncMock(return_value=None)
        return a

    def persona(self, assistant):
        return assistant.ask_openai.call_args.kwargs['personality_prompt']

    @pytest.mark.parametrize("holiday, emoji", [(HALLOWEEN, "👻🎃"), (THANKSGIVING, "🦃🥧"), (CHRISTMAS, "🎄🎅")])
    async def test_emoji_reply(self, assistant, holiday, emoji):
        with patch('cfb_bot.ai.ai_integration.current_holiday', return_value=holiday), \
             patch('cfb_bot.ai.ai_integration.emoji_this_reply', return_value=True):
            reply = await assistant.ask_ai("who's winning?")
        assert reply == f"Bloody Ducks {emoji}"
        assert holiday.persona in self.persona(assistant)

    @pytest.mark.parametrize("holiday", [HALLOWEEN, THANKSGIVING, CHRISTMAS])
    async def test_stays_in_character_without_emoji(self, assistant, holiday):
        with patch('cfb_bot.ai.ai_integration.current_holiday', return_value=holiday), \
             patch('cfb_bot.ai.ai_integration.emoji_this_reply', return_value=False):
            reply = await assistant.ask_ai("who's winning?")
        assert reply == "Bloody Ducks"
        assert holiday.persona in self.persona(assistant)
        assert "No emoji" in self.persona(assistant)

    async def test_charter_persona_stays_plain(self, assistant):
        with patch('cfb_bot.ai.ai_integration.current_holiday', return_value=CHRISTMAS), \
             patch('cfb_bot.ai.ai_integration.emoji_this_reply', return_value=True):
            reply = await assistant.ask_ai("write a rule", personality_prompt="plain")
        assert reply == "Bloody Ducks"
        assert self.persona(assistant) == "plain"

    async def test_plain_harry_the_rest_of_the_year(self, assistant):
        with patch('cfb_bot.ai.ai_integration.current_holiday', return_value=None):
            assert await assistant.ask_ai("who's winning?") == "Bloody Ducks"
        assert self.persona(assistant) is None
