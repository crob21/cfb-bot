#!/usr/bin/env python3
"""
Spooky Halloween Harry

The last week of October (league time) Harry's replies get ghosts and pumpkins, and he
reacts to every post from certain members (HALLOWEEN_REACTIONS). On November 1st
he goes back to normal by himself, and comes back every year.
"""

from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from ..config import env_str

LEAGUE_TIMEZONE = ZoneInfo('America/New_York')

PUMPKIN = '🎃'
GHOST = '👻'
GRAVESTONE = '🪦'
SPOOKY_EMOJI = (PUMPKIN, GHOST)

# Oct 25 through Oct 31: Halloween week
SPOOKY_FIRST_DAY = 25

# Who gets which reaction on every post: name (username, display name or server nickname,
# partial match) or user ID, then the emoji. Comma-separated name:emoji pairs.
DEFAULT_REACTIONS = f'mundie:{PUMPKIN},wustman:{GHOST},jaywill9:{GRAVESTONE}'


def parse_reactions(spec: str) -> dict:
    """'name:emoji,name:emoji' as {name: emoji}, skipping malformed pairs."""
    reactions = {}
    for pair in spec.split(','):
        name, _, emoji = pair.partition(':')
        if name.strip() and emoji.strip():
            reactions[name.strip().lower()] = emoji.strip()
    return reactions


HALLOWEEN_REACTIONS = parse_reactions(env_str('HALLOWEEN_REACTIONS', DEFAULT_REACTIONS))

SPOOKY_PERSONALITY = f"""
It's Halloween week, so you are Spooky Halloween Harry. Every reply is haunted: sprinkle in
ghost {GHOST} and pumpkin {PUMPKIN} emojis, ghoulish puns and graveyard humour, while still
answering the question properly. The Ducks are, naturally, cursed."""


def is_halloween(today: Optional[date] = None) -> bool:
    """True during Halloween week, in league (Eastern) time."""
    today = today or datetime.now(LEAGUE_TIMEZONE).date()
    return today.month == 10 and today.day >= SPOOKY_FIRST_DAY


def spooky_personality(personality: str) -> str:
    """Harry's persona, haunted for Halloween week."""
    return personality + '\n' + SPOOKY_PERSONALITY


def spookify(text: str) -> str:
    """Make sure a Halloween reply has its ghost and pumpkin, even if the AI forgot."""
    if any(e in text for e in SPOOKY_EMOJI):
        return text
    return f"{text} {GHOST}{PUMPKIN}"


def halloween_reaction(author, reactions: Optional[dict] = None) -> Optional[str]:
    """The emoji this author gets on every post, or None."""
    reactions = HALLOWEEN_REACTIONS if reactions is None else reactions
    if str(author.id) in reactions:
        return reactions[str(author.id)]
    names = [n.lower() for n in (getattr(author, 'name', None), getattr(author, 'global_name', None),
                                 getattr(author, 'display_name', None), getattr(author, 'nick', None))
             if isinstance(n, str) and n]
    for target, emoji in reactions.items():
        if any(target in n for n in names):
            return emoji
    return None
