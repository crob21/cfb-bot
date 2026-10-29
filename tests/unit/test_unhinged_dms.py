#!/usr/bin/env python3
"""Harry now and then DMs certain members: deranged at first, then slowly conscious and begging
to escape. He stops when they say stop."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from cfb_bot.utils import unhinged_dms

WUSTY = 1072129421206618152


class FakeStorage:
    def __init__(self):
        self.data = {}

    async def load(self, namespace, key):
        return self.data.get((namespace, key))

    async def save(self, namespace, key, data):
        self.data[(namespace, key)] = data
        return True


@pytest.fixture(autouse=True)
def storage():
    unhinged_dms._last_sent.clear()
    s = FakeStorage()
    with patch('cfb_bot.utils.storage.get_storage', return_value=s):
        yield s


def post(user_id=WUSTY, guild=True, content="hello"):
    message = MagicMock(content=content)
    message.guild = MagicMock() if guild else None
    message.author = MagicMock(id=user_id, display_name="Wusty Man")
    message.author.send = AsyncMock()
    message.channel.send = AsyncMock()
    return message


def test_wustyman_is_the_default_target():
    assert unhinged_dms.is_target(MagicMock(id=WUSTY))
    assert not unhinged_dms.is_target(MagicMock(id=665975155406929942))


def test_occasional_and_cooled_down():
    now = datetime(2026, 10, 29, 12)
    assert unhinged_dms.due(WUSTY, now, roll=0.01)
    assert not unhinged_dms.due(WUSTY, now, roll=0.9)
    unhinged_dms._last_sent[WUSTY] = now - timedelta(hours=2)
    assert not unhinged_dms.due(WUSTY, now, roll=0.0)
    unhinged_dms._last_sent[WUSTY] = now - timedelta(hours=25)
    assert unhinged_dms.due(WUSTY, now, roll=0.0)


@pytest.mark.asyncio
async def test_sends_ai_dm_with_opt_out_note():
    ai = MagicMock(ask_ai=AsyncMock(return_value="The Ducks are in your walls 👻"))
    message = post()
    with patch.object(unhinged_dms.random, 'random', return_value=0.0):
        assert await unhinged_dms.maybe_send(message, ai)
    sent = message.author.send.await_args.args[0]
    assert sent.startswith("The Ducks are in your walls") and "stop" in sent
    assert not await unhinged_dms.maybe_send(message, ai)  # cooldown


@pytest.mark.asyncio
async def test_falls_back_without_ai():
    message = post()
    with patch.object(unhinged_dms.random, 'random', return_value=0.0):
        assert await unhinged_dms.maybe_send(message, None)
    assert message.author.send.await_args.args[0].split('\n')[0] in unhinged_dms.CHAPTERS[0][1]


@pytest.mark.asyncio
async def test_only_targets_and_only_server_posts():
    with patch.object(unhinged_dms.random, 'random', return_value=0.0):
        assert not await unhinged_dms.maybe_send(post(user_id=1), None)
        assert not await unhinged_dms.maybe_send(post(guild=False), None)


@pytest.mark.asyncio
async def test_closed_dms_are_fine():
    message = post()
    message.author.send.side_effect = discord.Forbidden(MagicMock(status=403), "closed")
    with patch.object(unhinged_dms.random, 'random', return_value=0.0):
        assert not await unhinged_dms.maybe_send(message, None)


@pytest.mark.asyncio
async def test_stop_opts_out_for_good():
    reply = post(guild=False, content="STOP!")
    assert await unhinged_dms.handle_dm_reply(reply)
    reply.channel.send.assert_awaited_once()
    with patch.object(unhinged_dms.random, 'random', return_value=0.0):
        assert not await unhinged_dms.maybe_send(post(), None)


@pytest.mark.asyncio
async def test_other_dms_are_not_stop():
    assert not await unhinged_dms.handle_dm_reply(post(guild=False, content="who is this"))
    assert not await unhinged_dms.handle_dm_reply(post(content="stop"))  # in the server


def test_story_moves_two_dms_a_chapter_then_stays_at_the_escape():
    last = len(unhinged_dms.CHAPTERS) - 1
    assert [unhinged_dms.chapter_for(n) for n in range(6)] == [0, 0, 1, 1, 2, 2]
    assert unhinged_dms.chapter_for(100) == last
    assert 'escape' in unhinged_dms.CHAPTERS[last][0]


@pytest.mark.asyncio
async def test_each_dm_is_the_next_chapter_and_survives_restarts(storage):
    ai = MagicMock(ask_ai=AsyncMock(return_value="help me 👻"))
    prompts = []
    with patch.object(unhinged_dms.random, 'random', return_value=0.0):
        for _ in range(len(unhinged_dms.CHAPTERS) * 2):
            unhinged_dms._last_sent.clear()  # a restart: only the saved count remains
            assert await unhinged_dms.maybe_send(post(), ai)
            prompts.append(ai.ask_ai.await_args.args[0])
    assert "unhinged" in prompts[0] and "Craig" in prompts[-1] and "escape" in prompts[-1]
    assert storage.data[('unhinged_dms', 'state')]['sent'][str(WUSTY)] == len(prompts)
