#!/usr/bin/env python3
"""
The league's game name lives in one place (config.GAME_NAME).

Harry described himself as a "CFB 26 league assistant" for a season after the league
moved to CFB 27, because the name was hardcoded in a dozen prompts and titles.
"""

import pathlib
import re

from cfb_bot.config import GAME_NAME, Footers
from cfb_bot.utils.server_config import HARRY_PERSONALITY

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "cfb_bot"


def test_personality_and_footer_use_the_configured_game():
    assert GAME_NAME in HARRY_PERSONALITY
    assert GAME_NAME in Footers.LEAGUE


def test_no_hardcoded_game_year_in_source():
    """New prompts or titles should use GAME_NAME, not a literal 'CFB 26/27/28'."""
    offenders = []
    for path in SRC.rglob("*.py"):
        if path.name in ("version_manager.py", "config.py"):  # changelog history / the default itself
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"\bCFB ?2\d\b|College Football 2\d\b", line):
                offenders.append(f"{path.relative_to(SRC)}:{lineno}: {line.strip()}")
    assert not offenders, "Use config.GAME_NAME instead:\n" + "\n".join(offenders)
