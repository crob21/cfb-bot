#!/usr/bin/env python3
"""
The advance timer's state lives in one JSON message in the owner DM.

It used to also go to os.environ and a local file (neither survives a redeploy) and
fall back to posting the JSON publicly in the timer channel; startup then scanned
every channel of every server for it.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from cfb_bot.utils.timekeeper import TimekeeperManager


class FakeDM:
    def __init__(self, bot_user):
        self.bot_user = bot_user
        self.messages = []  # newest first, like history()

    async def send(self, content):
        msg = MagicMock(id=len(self.messages) + 1, author=self.bot_user, content=content)
        msg.edit = AsyncMock(side_effect=lambda content: setattr(msg, 'content', content))
        msg.delete = AsyncMock(side_effect=lambda: self.messages.remove(msg))
        self.messages.insert(0, msg)
        return msg

    async def fetch_message(self, message_id):
        for m in self.messages:
            if m.id == message_id:
                return m
        raise discord.NotFound(MagicMock(status=404), "gone")

    async def history(self, limit=100):
        for m in list(self.messages)[:limit]:
            yield m


@pytest.fixture
def manager():
    bot = MagicMock()
    bot.user = MagicMock(name="harry")
    dm = FakeDM(bot.user)
    m = TimekeeperManager(bot)
    with patch('cfb_bot.utils.owner_dm.get_owner_dm', AsyncMock(return_value=dm)):
        yield m, dm


@pytest.mark.asyncio
async def test_round_trip(manager):
    m, dm = manager
    state = {'channel_id': 5, 'end_time': '2099-01-01T00:00:00', 'is_active': True}
    assert await m._save_state_to_discord(state)
    m.state_message_id = None  # a fresh process
    assert await m._load_state_from_discord() == state


@pytest.mark.asyncio
async def test_saves_edit_one_message(manager):
    m, dm = manager
    await m._save_state_to_discord({'channel_id': 5, 'end_time': 'a', 'is_active': True})
    await m._save_state_to_discord({'channel_id': 5, 'end_time': 'b', 'is_active': True})
    assert len(dm.messages) == 1 and '"b"' in dm.messages[0].content


@pytest.mark.asyncio
async def test_stopped_timer_stays_stopped(manager):
    m, dm = manager
    await m._save_state_to_discord({'channel_id': 5, 'end_time': 'a', 'is_active': True})
    await m._save_state_to_discord({'channel_id': 5, 'is_active': False})
    m.state_message_id = None
    assert await m._load_state_from_discord() is None


@pytest.mark.asyncio
async def test_other_state_messages_are_left_alone(manager):
    m, dm = manager
    await dm.send('```json\n{"type": "season_week", "season": 5, "week": 3}\n```')
    await m._save_state_to_discord({'channel_id': 5, 'end_time': 'a', 'is_active': True})
    assert len(dm.messages) == 2


@pytest.mark.asyncio
async def test_no_dm_no_save():
    m = TimekeeperManager(MagicMock())
    with patch('cfb_bot.utils.owner_dm.get_owner_dm', AsyncMock(return_value=None)):
        assert not await m._save_state_to_discord({'channel_id': 5})
        assert await m._load_state_from_discord() is None


@pytest.mark.asyncio
async def test_co_commissioner_can_be_set_and_cleared():
    """/league set_commish called a method that didn't exist."""
    m = TimekeeperManager(MagicMock())
    m._save_league_staff_state = AsyncMock()
    assert await m.set_co_commissioner(7, "Rob")
    assert m.get_league_staff()['co_commish_name'] == "Rob" and m.get_league_staff()['has_co_commish']
    assert await m.set_co_commissioner(None)
    assert not m.get_league_staff()['has_co_commish']
    assert m._save_league_staff_state.await_count == 2
