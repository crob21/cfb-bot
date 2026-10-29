#!/usr/bin/env python3
"""
Holiday Harry

Harry dresses up for the holidays (league time):
- Halloween week, Oct 25-31: Spooky Halloween Harry 🎃👻, who also reacts to every post
  from certain members (HALLOWEEN_REACTIONS)
- Thanksgiving week, Monday to Sunday around the 4th Thursday of November: Thanksgiving Harry 🦃
- Christmas, Dec 18-26: Christmas Harry 🎄

He stays in character for every reply; only some get the holiday emoji
(HOLIDAY_EMOJI_CHANCE), so they don't wear thin. The reactions happen on every post. Outside those dates he's plain Harry. Nothing to switch on or off; it comes back every year.
"""

import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from ..config import env_float, env_str

LEAGUE_TIMEZONE = ZoneInfo('America/New_York')

# Share of Harry's holiday replies that get the holiday emoji (he's in character for all of them)
HOLIDAY_EMOJI_CHANCE = env_float('HOLIDAY_EMOJI_CHANCE', 0.25)

PUMPKIN = '🎃'
GHOST = '👻'
GRAVESTONE = '🪦'
TURKEY = '🦃'
PIE = '🥧'
TREE = '🎄'
SANTA = '🎅'


@dataclass(frozen=True)
class Holiday:
    name: str
    emoji: tuple  # the first two get added to an emoji reply that has none of them
    persona: str  # the voice, every reply; emoji are asked for separately


HALLOWEEN = Holiday('Halloween', (GHOST, PUMPKIN), f"""
It's Halloween week, so you are Spooky Halloween Harry. Every reply is haunted: ghoulish puns,
graveyard humour and things that go bump in the night, while still answering the question
properly. The Ducks are, naturally, cursed.""")

THANKSGIVING = Holiday('Thanksgiving', (TURKEY, PIE), f"""
It's Thanksgiving week, so you are Thanksgiving Harry. Every reply gets stuffing-and-gravy puns
and a food coma, and you're sarcastically thankful for things (mostly every Ducks loss), while
still answering the question properly.""")

CHRISTMAS = Holiday('Christmas', (TREE, SANTA), f"""
It's Christmas, so you are Christmas Harry. Every reply is festive: carol puns and a bit too
much eggnog, while still answering the question properly. The Ducks are top of the naughty
list and get coal.""")


def thanksgiving_day(year: int) -> date:
    """US Thanksgiving: the fourth Thursday of November."""
    first = date(year, 11, 1)
    return first + timedelta(days=(3 - first.weekday()) % 7 + 21)


def current_holiday(today: Optional[date] = None) -> Optional[Holiday]:
    """The holiday Harry is dressed for today, in league (Eastern) time, or None."""
    today = today or datetime.now(LEAGUE_TIMEZONE).date()
    if today.month == 10 and today.day >= 25:
        return HALLOWEEN
    if today.month == 11:
        thursday = thanksgiving_day(today.year)
        if thursday - timedelta(days=3) <= today <= thursday + timedelta(days=3):
            return THANKSGIVING
    if today.month == 12 and 18 <= today.day <= 26:
        return CHRISTMAS
    return None


def emoji_this_reply(roll: Optional[float] = None) -> bool:
    """Whether this holiday reply gets the holiday emoji: now and then, not every time."""
    return (random.random() if roll is None else roll) < HOLIDAY_EMOJI_CHANCE


def holiday_personality(personality: str, holiday: Holiday, with_emoji: bool) -> str:
    """Harry's persona, in character for the holiday, with or without its emoji this time."""
    if with_emoji:
        emoji = f"Drop in a {holiday.emoji[0]} or {holiday.emoji[1]} emoji."
    else:
        emoji = "No emoji in this reply: the holiday shows in your words."
    return f"{personality}\n{holiday.persona}\n{emoji}"


def festive(text: str, holiday: Holiday) -> str:
    """Make sure a holiday reply has its emoji, even if the AI forgot."""
    if any(e in text for e in holiday.emoji):
        return text
    return f"{text} {''.join(holiday.emoji[:2])}"


# Who gets which reaction on every Halloween week post: name (username, display name or
# server nickname, partial match) or user ID, then the emoji. Comma-separated name:emoji pairs.
DEFAULT_HALLOWEEN_REACTIONS = f'mundie:{PUMPKIN},wustman:{GHOST},jaywill9:{GRAVESTONE}'


def parse_reactions(spec: str) -> dict:
    """'name:emoji,name:emoji' as {name: emoji}, skipping malformed pairs."""
    reactions = {}
    for pair in spec.split(','):
        name, _, emoji = pair.partition(':')
        if name.strip() and emoji.strip():
            reactions[name.strip().lower()] = emoji.strip()
    return reactions


HALLOWEEN_REACTIONS = parse_reactions(env_str('HALLOWEEN_REACTIONS', DEFAULT_HALLOWEEN_REACTIONS))
REACTIONS = {HALLOWEEN: HALLOWEEN_REACTIONS}


def holiday_reaction(author, holiday: Optional[Holiday], reactions: Optional[dict] = None) -> Optional[str]:
    """The emoji this author gets on every post this holiday, or None."""
    if reactions is None:
        reactions = REACTIONS.get(holiday, {})
    if str(author.id) in reactions:
        return reactions[str(author.id)]
    names = [n.lower() for n in (getattr(author, 'name', None), getattr(author, 'global_name', None),
                                 getattr(author, 'display_name', None), getattr(author, 'nick', None))
             if isinstance(n, str) and n]
    for target, emoji in reactions.items():
        if any(target in n for n in names):
            return emoji
    return None
