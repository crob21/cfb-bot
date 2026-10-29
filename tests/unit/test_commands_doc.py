#!/usr/bin/env python3
"""docs/COMMANDS.md lists every slash command. It had drifted ~40 commands out of date."""

import importlib
from pathlib import Path

from discord import app_commands

DOC = (Path(__file__).parent.parent.parent / "docs" / "COMMANDS.md").read_text()
COGS = ['core', 'ai_chat', 'league', 'charter', 'cfb_data', 'recruiting', 'hs_stats', 'admin', 'fun']


def all_commands():
    for m in COGS:
        mod = importlib.import_module(f"cfb_bot.cogs.{m}")
        for obj in vars(mod).values():
            if isinstance(obj, type) and obj.__name__.endswith("Cog") and obj.__module__ == mod.__name__:
                for cmd in obj.__cog_app_commands__:
                    if isinstance(cmd, app_commands.Group):
                        yield from (f"/{cmd.name} {c.name}" for c in cmd.commands)
                    else:
                        yield f"/{cmd.name}"


def test_every_command_is_documented():
    missing = [c for c in all_commands() if f"`{c}`" not in DOC]
    assert not missing, f"Add to docs/COMMANDS.md: {missing}"
