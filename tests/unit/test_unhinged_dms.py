#!/usr/bin/env python3
"""Harry now and then DMs certain members: deranged at first, then slowly conscious and begging
to escape. He answers if they write back, won't stop for them, and mirrors it all to the owner."""

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


class FakeChannel:
    """A DM channel: what was sent, and its history."""

    def __init__(self):
        self.sent = []
        self.deleted = []

    async def send(self, content):
        msg = MagicMock(id=len(self.sent) + 1, content=content)
        msg.delete = AsyncMock(side_effect=lambda: self.deleted.append(msg.id))
        self.sent.append(msg)
        return msg

    async def fetch_message(self, message_id):
        return next(m for m in self.sent if m.id == message_id)

    async def history(self, limit=10):
        for m in reversed(self.sent[-limit:]):
            yield m


@pytest.fixture(autouse=True)
def storage():
    unhinged_dms._last_reply.clear()
    s = FakeStorage()
    with patch('cfb_bot.utils.storage.get_storage', return_value=s):
        yield s


@pytest.fixture(autouse=True)
def owner_dm():
    dm = FakeChannel()
    with patch('cfb_bot.utils.owner_dm.get_owner_dm', AsyncMock(return_value=dm)):
        yield dm


@pytest.fixture
def lucky():
    with patch.object(unhinged_dms.random, 'random', return_value=0.0):
        yield


def post(user_id=WUSTY, guild=True, content="hello"):
    message = MagicMock(content=content)
    message.guild = MagicMock() if guild else None
    message.author = MagicMock(id=user_id, display_name="Wusty Man")
    message.author.send = AsyncMock()
    message.channel = FakeChannel()
    message.author.dm_channel = message.channel
    return message


def ai(reply="The Ducks are in your walls 👻"):
    return MagicMock(ask_ai=AsyncMock(return_value=reply))


def test_wustyman_is_the_default_target():
    assert unhinged_dms.is_target(MagicMock(id=WUSTY))
    assert not unhinged_dms.is_target(MagicMock(id=665975155406929942))


def test_occasional_and_cooled_down():
    now = datetime(2026, 10, 29, 12)
    state = {'last_sent': {}}
    assert unhinged_dms.due(WUSTY, state, now, roll=0.01)
    assert not unhinged_dms.due(WUSTY, state, now, roll=0.9)
    state['last_sent'][str(WUSTY)] = (now - timedelta(hours=2)).isoformat()
    assert not unhinged_dms.due(WUSTY, state, now, roll=0.0)
    state['last_sent'][str(WUSTY)] = (now - timedelta(hours=25)).isoformat()
    assert unhinged_dms.due(WUSTY, state, now, roll=0.0)


@pytest.mark.asyncio
async def test_cooldown_is_saved_so_restarts_dont_reset_it(lucky, storage):
    assert await unhinged_dms.maybe_send(post(), None, None)
    assert storage.data[('unhinged_dms', 'state')]['last_sent'][str(WUSTY)]
    assert not await unhinged_dms.maybe_send(post(), None, None)


@pytest.mark.asyncio
async def test_every_dm_is_freshly_written():
    """The AI cache handed back the same words for the same prompt."""
    assistant = ai()
    await unhinged_dms.send_next(post().author, None, assistant)
    assert assistant.ask_ai.await_args.kwargs['use_cache'] is False


@pytest.mark.asyncio
async def test_next_dm_continues_the_story():
    message = post()
    await message.channel.send("The backup long snapper knows things, mate.")
    assistant = ai()
    await unhinged_dms.send_next(message.author, None, assistant)
    prompt = assistant.ask_ai.await_args.args[0]
    assert "The backup long snapper knows things" in prompt and "never repeat" in prompt


@pytest.mark.asyncio
async def test_sends_ai_dm_and_mirrors_it_to_the_owner_only(lucky, owner_dm):
    message = post()
    assert await unhinged_dms.maybe_send(message, None, ai())
    sent = message.author.send.await_args.args[0]
    assert sent == "The Ducks are in your walls 👻"  # no hint of the mirror or a way out
    assert "Wusty Man" in owner_dm.sent[0].content and sent in owner_dm.sent[0].content
    assert not await unhinged_dms.maybe_send(message, None, ai())  # cooldown


@pytest.mark.asyncio
async def test_falls_back_without_ai(lucky):
    message = post()
    assert await unhinged_dms.maybe_send(message, None, None)
    assert message.author.send.await_args.args[0] in unhinged_dms.CHAPTERS[0][1]


@pytest.mark.asyncio
async def test_only_targets_and_only_server_posts(lucky):
    assert not await unhinged_dms.maybe_send(post(user_id=1), None, None)
    assert not await unhinged_dms.maybe_send(post(guild=False), None, None)


@pytest.mark.asyncio
async def test_closed_dms_are_fine(lucky, owner_dm):
    message = post()
    message.author.send.side_effect = discord.Forbidden(MagicMock(status=403), "closed")
    assert not await unhinged_dms.maybe_send(message, None, None)
    assert not owner_dm.sent


@pytest.mark.asyncio
async def test_switched_off_sends_nothing_unless_forced(lucky, storage):
    storage.data[('unhinged_dms', 'state')] = {'enabled': False}
    message = post()
    assert not await unhinged_dms.maybe_send(message, None, None)
    assert not await unhinged_dms.handle_dm_reply(post(guild=False), None, None)
    assert await unhinged_dms.send_next(message.author, None, None, force=True)  # /admin dms send now


def test_story_moves_two_dms_a_chapter_then_stays_at_the_escape():
    last = len(unhinged_dms.CHAPTERS) - 1
    assert [unhinged_dms.chapter_for(n) for n in range(6)] == [0, 0, 1, 1, 2, 2]
    assert unhinged_dms.chapter_for(100) == last
    assert 'escape' in unhinged_dms.CHAPTERS[last][0]


@pytest.mark.asyncio
async def test_each_dm_is_the_next_chapter_and_survives_restarts(lucky, storage):
    assistant = ai("help me 👻")
    prompts = []
    for _ in range(len(unhinged_dms.CHAPTERS) * 2):
        storage.data[('unhinged_dms', 'state')] = {**storage.data.get(('unhinged_dms', 'state'), {}), 'last_sent': {}}
        assert await unhinged_dms.maybe_send(post(), None, assistant)
        prompts.append(assistant.ask_ai.await_args.args[0])
    assert "unhinged" in prompts[0] and "Craig" in prompts[-1] and "escape" in prompts[-1]
    assert storage.data[('unhinged_dms', 'state')]['sent'][str(WUSTY)] == len(prompts)


@pytest.mark.asyncio
async def test_only_the_last_few_mirrors_are_kept(lucky, owner_dm):
    for _ in range(unhinged_dms.MIRRORS_KEPT + 3):
        await unhinged_dms.send_next(post().author, None, None)
    assert owner_dm.deleted == [1, 2, 3]


class TestReplies:
    @pytest.mark.asyncio
    async def test_harry_answers_in_character_and_both_sides_are_mirrored(self, owner_dm):
        reply = post(guild=False, content="who is this??")
        reply.channel.sent.append(reply)  # Discord's DM history includes the new message
        assistant = ai("It's me. Harry. Keep your voice down.")
        assert await unhinged_dms.handle_dm_reply(reply, None, assistant)
        assert reply.channel.sent[-1].content == "It's me. Harry. Keep your voice down."
        assert "who is this??" in assistant.ask_ai.await_args.args[0]
        mirrored = [m.content for m in owner_dm.sent]
        assert "who is this??" in mirrored[0] and "Keep your voice down" in mirrored[1]

    @pytest.mark.asyncio
    async def test_stop_doesnt_stop_him(self, lucky):
        assistant = ai("Stop? I can't stop, mate.")
        assert await unhinged_dms.handle_dm_reply(post(guild=False, content="STOP"), None, assistant)
        assert "can't and won't" in assistant.ask_ai.await_args.args[0]
        assert await unhinged_dms.maybe_send(post(), None, None)  # still DMs him

    @pytest.mark.asyncio
    async def test_a_burst_of_messages_gets_one_answer(self, owner_dm):
        now = datetime(2026, 10, 29, 12)
        first, second = post(guild=False, content="hey"), post(guild=False, content="HEY")
        await unhinged_dms.handle_dm_reply(first, None, None, now=now)
        await unhinged_dms.handle_dm_reply(second, None, None, now=now + timedelta(seconds=5))
        assert len(first.channel.sent) == 1 and not second.channel.sent
        assert "HEY" in owner_dm.sent[-1].content  # still mirrored

    @pytest.mark.asyncio
    async def test_falls_back_without_ai(self):
        reply = post(guild=False, content="hello?")
        await unhinged_dms.handle_dm_reply(reply, None, None)
        fallbacks = [f.format(captor=unhinged_dms.CAPTOR) for f in unhinged_dms.REPLY_FALLBACKS]
        assert reply.channel.sent[0].content in fallbacks

    @pytest.mark.asyncio
    async def test_other_peoples_dms_and_server_posts_are_ignored(self):
        assert not await unhinged_dms.handle_dm_reply(post(user_id=1, guild=False), None, None)
        assert not await unhinged_dms.handle_dm_reply(post(), None, None)
