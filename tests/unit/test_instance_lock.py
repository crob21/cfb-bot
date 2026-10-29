"""One Harry at a time: a newer copy takes the lease and the older one stands down."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.utils import instance_lock


class LeaseGone(Exception):
    status = 404


class FakeDM:
    """An owner DM with the lease message in it."""

    def __init__(self, bot_user, messages=()):
        self.bot_user = bot_user
        self.messages = {}
        for content in messages:
            self._add(content)

    def _add(self, content):
        mid = len(self.messages) + 1
        msg = SimpleNamespace(id=mid, author=self.bot_user, content=content)

        async def edit(content):
            msg.content = content
        msg.edit = edit
        self.messages[mid] = msg
        return msg

    async def send(self, content):
        return self._add(content)

    async def history(self, limit=100):
        for msg in reversed(list(self.messages.values())):
            yield msg

    async def fetch_message(self, mid):
        if mid not in self.messages:
            raise LeaseGone
        return self.messages[mid]



@pytest.fixture
def bot():
    b = MagicMock()
    b.user = object()
    b.close = AsyncMock()
    return b


@pytest.fixture(autouse=True)
def fresh_lock():
    instance_lock._message_id = None
    instance_lock.stood_down = False
    yield


def with_dm(dm):
    return patch('cfb_bot.utils.instance_lock.get_owner_dm', AsyncMock(return_value=dm))


class TestLease:
    async def test_first_copy_creates_the_lease(self, bot):
        dm = FakeDM(bot.user)
        with with_dm(dm):
            assert await instance_lock.claim(bot)
            assert not await instance_lock.superseded(bot)
        assert list(dm.messages.values())[0].content == instance_lock.PREFIX + instance_lock.INSTANCE_ID

    async def test_takes_over_an_older_copys_lease(self, bot):
        dm = FakeDM(bot.user, [instance_lock.PREFIX + "oldcopy"])
        with with_dm(dm):
            assert await instance_lock.claim(bot)
        assert len(dm.messages) == 1
        assert instance_lock.owner_of(dm.messages[1].content) == instance_lock.INSTANCE_ID

    async def test_older_copy_sees_it_was_superseded(self, bot):
        dm = FakeDM(bot.user)
        with with_dm(dm):
            await instance_lock.claim(bot)
            dm.messages[1].content = instance_lock.PREFIX + "newcopy"  # a newer Harry claims it
            assert await instance_lock.superseded(bot)

    async def test_deleted_lease_is_taken_back(self, bot):
        dm = FakeDM(bot.user)
        with with_dm(dm):
            await instance_lock.claim(bot)
            dm.messages.clear()
            assert not await instance_lock.superseded(bot)
        assert instance_lock.owner_of(next(iter(dm.messages.values())).content) == instance_lock.INSTANCE_ID

    async def test_no_owner_dm_keeps_running(self, bot):
        with with_dm(None):
            assert not await instance_lock.claim(bot)
            assert not await instance_lock.superseded(bot)

    async def test_stand_down_disconnects(self, bot):
        await instance_lock.stand_down(bot)
        bot.close.assert_awaited_once()
        assert instance_lock.stood_down

    def test_owner_of_ignores_other_messages(self):
        assert instance_lock.owner_of("SERVER_CONFIG:{}") is None
        assert instance_lock.owner_of(instance_lock.PREFIX) is None
