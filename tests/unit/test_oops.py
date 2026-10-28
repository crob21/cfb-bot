#!/usr/bin/env python3
"""Broken commands get Harry's line; the traceback goes to the bot owner, never to Discord."""

import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.services.oops import OOPS, oops

SRC = Path(__file__).resolve().parents[2] / "src" / "cfb_bot"

# Showing the user their own file's JSON error is the point of that message
ALLOWED = {"Couldn't parse JSON"}


def _interaction(deferred: bool):
    interaction = MagicMock()
    interaction.command.qualified_name = "cfb player"
    interaction.response.is_done.return_value = deferred
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.mark.asyncio
@pytest.mark.parametrize("deferred", [True, False])
async def test_oops_reports_and_replies_without_the_exception(deferred):
    reporter = MagicMock(report=AsyncMock())
    interaction = _interaction(deferred)
    with patch('cfb_bot.utils.error_reporter.get_error_reporter', return_value=reporter):
        await oops(interaction, RuntimeError("https://internal/secret-path 500"))

    reporter.report.assert_awaited_once()
    assert reporter.report.call_args.args[1] == "/cfb player"
    sent = interaction.followup.send if deferred else interaction.response.send_message
    sent.assert_awaited_once_with(OOPS, ephemeral=True)


def test_no_exception_text_in_user_facing_messages():
    offenders = []
    for path in SRC.rglob("*.py"):
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            if re.search(r"\{(str\()?e\)?\}", line) and re.search(r"send|description=|❌|Oops", line) \
                    and not re.search(r"logger\.|log\.|raise ", line) and not any(a in line for a in ALLOWED):
                offenders.append(f"{path.relative_to(SRC)}:{lineno}: {line.strip()}")
    assert not offenders, "Use services.oops.oops() instead of showing exceptions:\n" + "\n".join(offenders)
