#!/usr/bin/env python3
"""
Unit tests for the owner-DM error reporter
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from cfb_bot.utils.error_reporter import MAX_DMS_PER_HOUR, ErrorReporter


def make_error(message="boom", kind=RuntimeError):
    try:
        raise kind(message)
    except Exception as e:
        return e


@pytest.fixture
def reporter():
    r = ErrorReporter(bot=MagicMock())
    r._owner_dm = AsyncMock(return_value=AsyncMock())
    return r


class TestReporting:
    @pytest.mark.asyncio
    async def test_sends_dm_with_context_and_traceback(self, reporter):
        assert await reporter.report(make_error("scraper died"), "/recruiting top")
        sent = reporter._owner_dm.return_value.send.call_args[0][0]
        assert "/recruiting top" in sent
        assert "RuntimeError: scraper died" in sent

    @pytest.mark.asyncio
    async def test_repeat_of_same_error_is_collapsed(self, reporter):
        assert await reporter.report(make_error(), "/cfb player")
        assert not await reporter.report(make_error(), "/cfb player")
        assert reporter._owner_dm.return_value.send.await_count == 1

    @pytest.mark.asyncio
    async def test_different_errors_both_reported(self, reporter):
        assert await reporter.report(make_error("one"), "/cfb player")
        assert await reporter.report(make_error("two", ValueError), "/cfb player")
        assert reporter._owner_dm.return_value.send.await_count == 2

    @pytest.mark.asyncio
    async def test_repeat_count_included_after_window(self, reporter):
        await reporter.report(make_error(), "/cfb player")
        await reporter.report(make_error(), "/cfb player")  # collapsed, counted
        key = next(iter(reporter._seen))
        reporter._seen[key]['first_sent'] = datetime.now() - timedelta(minutes=30)
        await reporter.report(make_error(), "/cfb player")
        assert "Happened 2 times" in reporter._owner_dm.return_value.send.call_args[0][0]

    @pytest.mark.asyncio
    async def test_hourly_cap_stops_flooding(self, reporter):
        for i in range(MAX_DMS_PER_HOUR + 5):
            await reporter.report(make_error(f"error {i}"), "/cfb player")
        assert reporter._owner_dm.return_value.send.await_count == MAX_DMS_PER_HOUR

    @pytest.mark.asyncio
    async def test_secrets_are_redacted(self, reporter):
        await reporter.report(make_error("auth failed key=sk-abcdefghijklmnopqrstuvwxyz012345"), "/harry")
        assert "sk-abcdefghijklmnopqrstuvwxyz012345" not in reporter._owner_dm.return_value.send.call_args[0][0]

    @pytest.mark.asyncio
    async def test_never_raises_when_dm_fails(self, reporter):
        reporter._owner_dm.return_value.send.side_effect = Exception("DMs closed")
        assert not await reporter.report(make_error(), "/cfb player")

    @pytest.mark.asyncio
    async def test_no_bot_means_no_report(self):
        assert not await ErrorReporter(bot=None).report(make_error(), "/cfb player")
