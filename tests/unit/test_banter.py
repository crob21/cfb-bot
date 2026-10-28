#!/usr/bin/env python3
"""
Team banter and the troll's insult detector match whole words, longest name first.

Both used plain substring checks in dict order: "Oregon State" got the Oregon line,
every mention of league team Michigan State got "Go Blue!", "millions" got "Go Lions!",
and a targeted user saying "hello" (hell) or "class" (ass) started an argument.
"""

import pytest

from cfb_bot.cogs.fun import INSULT_WORDS, rivalry_response


@pytest.mark.parametrize("text,expected", [
    ("Fuck it, Oregon again", "Fuck Oregon! 🦆💩"),
    ("Oregon State is up next", "BEAVS!"),
    ("Michigan just lost", "Go Blue! 💙"),
    ("roll on alabama", "Roll Tide! 🐘"),
])
def test_rivals_get_their_line(text, expected):
    assert rivalry_response(text) == expected


@pytest.mark.parametrize("text", [
    "Michigan State plays Duke this week",  # a league team, not Michigan
    "made millions on that trade",          # not the Lions
    "both of us",                           # not 'uw'... or anything
    "Georgia Tech at home",
    "",
    None,
])
def test_no_banter(text):
    assert rivalry_response(text) is None


@pytest.mark.parametrize("text", ["hello mate", "first class recruiting", "pass rush", "both teams", "shell"])
def test_ordinary_words_are_not_insults(text):
    assert not INSULT_WORDS.search(text)


@pytest.mark.parametrize("text", ["you suck", "stupid bot", "fucking hell", "what a dumb ass"])
def test_insults_are_insults(text):
    assert INSULT_WORDS.search(text)


def test_long_questions_fit_an_embed_field():
    from cfb_bot.cogs.ai_chat import _echo
    assert len(_echo("x" * 2000)) <= 1024
    assert _echo("hi") == "*hi*"


@pytest.mark.asyncio
async def test_whats_new_lists_the_latest_changes():
    """Releases nest changes under 'features'; /whats_new used to look for a 'changes' key and show none."""
    from unittest.mock import AsyncMock, MagicMock
    from cfb_bot.cogs.core import CoreCog
    from cfb_bot.utils.version_manager import CHANGELOG, CURRENT_VERSION
    cog = CoreCog(MagicMock())
    interaction = MagicMock()
    interaction.response.send_message = AsyncMock()
    await cog.whats_new.callback(cog, interaction)
    embed = interaction.response.send_message.call_args.kwargs['embed']
    changes = next(f.value for f in embed.fields if f.name == "📝 Changes")
    first = CHANGELOG[CURRENT_VERSION]['features'][0]['changes'][0]
    assert first[:40] in changes
