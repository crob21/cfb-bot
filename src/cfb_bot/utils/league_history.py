#!/usr/bin/env python3
"""
The league's record book: data/history.md, newest season first.

Rules change by decision; history piles up every season. So they live apart: the charter
holds the rules, this file holds the champions, playoff fields, results and job changes.
Harry adds one season at a time through a pull request, and reads the file for questions
like "who won season 2?".
"""

import logging
import re
from typing import Optional

from ..config import HISTORY_FILE

logger = logging.getLogger('CFBBot.LeagueHistory')

HEADER = ("# League History\n\nThe league's record book, newest season first. Harry adds each "
          "season through a pull request at End of Season Recap.\n")


def _heading(season) -> re.Pattern:
    """A season's heading: "## Season 5" (Harry's) or "## 2025 Season" (written by hand)."""
    return re.compile(rf"^## (?:Season {season}|{season} Season)\b.*$", re.MULTILINE)


def read_history(path: str = HISTORY_FILE) -> str:
    """The record book, or "" if there isn't one yet."""
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except OSError as e:
        logger.warning(f"Couldn't read {path}: {e}")
        return ""


def season_section(history: str, season) -> Optional[str]:
    """One season's entry, heading included, or None."""
    match = _heading(season).search(history)
    if not match:
        return None
    end = history.find("\n## ", match.end())
    return history[match.start():end if end != -1 else len(history)].strip()


def add_season(history: str, season, entry: str) -> str:
    """The record book with `entry` as the newest season, replacing any older entry for it."""
    entry = entry.strip()
    old = season_section(history, season)
    if old:
        history = history.replace(old, "").replace("\n\n\n\n", "\n\n")
    if not history.strip():
        history = HEADER
    first = history.find("\n## ")
    if first == -1:
        return history.rstrip() + "\n\n" + entry + "\n"
    return history[:first].rstrip() + "\n\n" + entry + "\n\n" + history[first + 1:].lstrip()


def clean_entry(text: Optional[str], season) -> Optional[str]:
    """The AI's season entry, unwrapped from any code fence, or None if it isn't one."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].removesuffix("```").strip()
    if not text.startswith(f"## Season {season}"):
        return None
    return text
