#!/usr/bin/env python3
"""
Finding Harry's saved messages in the owner DM.

Saved messages are edited in place, so newer DMs (error reports, alerts, nags) pile up on top
of them. They're pinned so a lookup always finds them, however much has been said since.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cfb_bot.utils import owner_dm
from cfb_bot.utils.owner_dm import find_saved, keep, saved_messages

BOT = MagicMock(name="harry")


def _msg(content, pinned=False, author=BOT, id_=None):
    m = MagicMock(content=content, pinned=pinned, author=author, id=id_ or id(content))
    m.pin = AsyncMock()
    return m


def _dm(pins=(), history=()):
    dm = MagicMock()
    dm.pins = AsyncMock(return_value=list(pins))
    dm.scanned = 0

    def history_fn(limit=None):
        async def gen():
            for m in list(history)[:limit]:
                dm.scanned += 1
                yield m
        return gen()
    dm.history = history_fn
    return dm


def _bot():
    bot = MagicMock()
    bot.user = BOT
    return bot


@pytest.mark.asyncio
async def test_a_pinned_message_is_found_without_scanning_history():
    saved = _msg("SERVER_CONFIG:{}", pinned=True)
    dm = _dm(pins=[saved], history=[_msg("noise")] * 50)
    assert await find_saved(_bot(), dm, lambda m: m.content.startswith("SERVER_CONFIG:")) is saved
    assert dm.scanned == 0
    saved.pin.assert_not_called()


@pytest.mark.asyncio
async def test_an_old_unpinned_message_is_found_past_100_newer_ones_and_pinned():
    saved = _msg("SERVER_CONFIG:{}")
    noise = [_msg(f"error report {i}", id_=i + 1) for i in range(300)]
    dm = _dm(history=noise + [saved])
    assert await find_saved(_bot(), dm, lambda m: m.content.startswith("SERVER_CONFIG:")) is saved
    saved.pin.assert_awaited_once()


@pytest.mark.asyncio
async def test_other_peoples_messages_never_match():
    dm = _dm(history=[_msg("SERVER_CONFIG:{}", author=MagicMock(name="craig"))])
    assert await find_saved(_bot(), dm, lambda m: m.content.startswith("SERVER_CONFIG:")) is None


@pytest.mark.asyncio
async def test_nothing_found_is_none():
    assert await find_saved(_bot(), _dm(history=[_msg("noise")]), lambda m: False) is None


@pytest.mark.asyncio
async def test_saved_messages_lists_pins_first_without_duplicates():
    a, b = _msg("A", pinned=True, id_=1), _msg("B", id_=2)
    dm = _dm(pins=[a], history=[b, a])
    assert await saved_messages(_bot(), dm) == [a, b]


@pytest.mark.asyncio
async def test_unreadable_pins_fall_back_to_history():
    saved = _msg("SERVER_CONFIG:{}")
    dm = _dm(history=[saved])
    dm.pins = AsyncMock(side_effect=RuntimeError("boom"))
    assert await find_saved(_bot(), dm, lambda m: m.content.startswith("SERVER_CONFIG:")) is saved


@pytest.mark.asyncio
async def test_a_full_pin_list_is_logged_not_raised():
    message = _msg("X")
    message.pin = AsyncMock(side_effect=RuntimeError("Maximum number of pins reached (50)"))
    await keep(message)  # no exception


def test_every_owner_dm_lookup_goes_through_the_pinned_helpers():
    """No module scans the owner DM's recent history itself any more."""
    import inspect
    from cfb_bot.utils import charter_editor, instance_lock, schedule_manager, storage, timekeeper
    for module in (charter_editor, instance_lock, schedule_manager, storage, timekeeper):
        source = inspect.getsource(module)
        assert "dm.history(" not in source and "dm_channel.history(" not in source, module.__name__
    assert owner_dm.SCAN_LIMIT >= 500
