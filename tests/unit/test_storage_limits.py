#!/usr/bin/env python3
"""
Tests for the Discord-DM storage size guard.

Each namespace lives in one Discord message (2000 char cap). Past it the save fails and
the change silently reverts on the next restart — so the owner gets told.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from cfb_bot.utils.storage import (DISCORD_MESSAGE_LIMIT, SAVE_WARN_THRESHOLD,
                                   DiscordDMStorage)


@pytest.fixture
def storage():
    s = DiscordDMStorage(bot=MagicMock())
    s._get_dm_channel = AsyncMock(return_value=AsyncMock())
    s._warn_owner = AsyncMock()
    return s


def payload_of(chars: int) -> dict:
    return {"guild": {"blob": "x" * chars}}


class TestSizeGuard:
    @pytest.mark.asyncio
    async def test_oversize_namespace_is_not_saved(self, storage):
        storage._cache["server_config"] = payload_of(DISCORD_MESSAGE_LIMIT + 100)

        assert not await storage._save_namespace("server_config")
        storage._get_dm_channel.return_value.send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_oversize_namespace_warns_the_owner(self, storage):
        storage._cache["server_config"] = payload_of(DISCORD_MESSAGE_LIMIT + 100)

        await storage._save_namespace("server_config")

        storage._warn_owner.assert_awaited_once()
        title, body = storage._warn_owner.await_args[0]
        assert "server_config" in title
        assert "lost when Harry restarts" in body

    @pytest.mark.asyncio
    async def test_normal_payload_saves(self, storage):
        storage._cache["server_config"] = payload_of(100)
        dm = storage._get_dm_channel.return_value
        dm.history = MagicMock(return_value=_empty_history())

        assert await storage._save_namespace("server_config")
        dm.send.assert_awaited_once()
        storage._warn_owner.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_failure_warns_the_owner(self, storage):
        storage._cache["server_config"] = payload_of(100)
        dm = storage._get_dm_channel.return_value
        dm.history = MagicMock(return_value=_empty_history())
        dm.send.side_effect = Exception("403 Forbidden")

        assert not await storage._save_namespace("server_config")
        storage._warn_owner.assert_awaited_once()

    def test_warn_threshold_is_below_the_hard_limit(self):
        assert SAVE_WARN_THRESHOLD < DISCORD_MESSAGE_LIMIT


def _empty_history():
    class _H:
        def __aiter__(self):
            async def gen():
                return
                yield  # pragma: no cover
            return gen()
    return _H()
