#!/usr/bin/env python3
"""
Each server's settings are their own saved message. They used to share one, which Discord's
2,000-character cap would have filled at four or five servers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.utils.server_config import ServerConfigManager


class FakeStorage:
    def __init__(self, data=None):
        self.data = data or {}  # namespace -> {key -> value}
        self.saves = []

    async def load(self, namespace, key):
        return self.data.get(namespace, {}).get(key)

    async def save(self, namespace, key, value):
        self.saves.append(namespace)
        self.data.setdefault(namespace, {})[key] = value
        return True


def _manager(guild_ids=()):
    manager = ServerConfigManager()
    manager._bot = MagicMock(guilds=[MagicMock(id=g) for g in guild_ids])
    return manager


async def _load(manager, storage):
    with patch('cfb_bot.utils.storage.get_storage', return_value=storage), \
         patch('cfb_bot.utils.storage.set_storage_bot'):
        assert await manager.load_from_discord()


@pytest.mark.asyncio
async def test_the_old_shared_message_is_split_into_one_per_server():
    storage = FakeStorage({"server_config": {"all": {"1": {"modules": {"league": True}}, "2": {"modules": {}}}}})
    manager = _manager()
    await _load(manager, storage)
    assert manager._configs[1]["modules"]["league"] is True
    assert sorted(storage.saves) == ["server_config_1", "server_config_2"]
    assert "server_config" in storage.data  # the old message is left as a backup


@pytest.mark.asyncio
async def test_each_servers_own_message_wins_over_the_old_shared_one():
    storage = FakeStorage({
        "server_config": {"all": {"1": {"modules": {"league": False}}}},
        "server_config_1": {"config": {"modules": {"league": True}}},
        "server_config_3": {"config": {"modules": {"fun_games": False}}},
    })
    manager = _manager(guild_ids=[3])
    await _load(manager, storage)
    assert manager._configs[1]["modules"]["league"] is True
    assert manager._configs[3]["modules"]["fun_games"] is False
    assert storage.saves == []  # nothing new to write


@pytest.mark.asyncio
async def test_a_save_only_writes_the_servers_that_changed():
    storage = FakeStorage({"server_config_1": {"config": {"settings": {}}},
                           "server_config_2": {"config": {"settings": {}}}})
    manager = _manager(guild_ids=[1, 2])
    await _load(manager, storage)
    manager.set_setting(2, "auto_responses", False)
    with patch('cfb_bot.utils.storage.get_storage', return_value=storage):
        assert await manager.save_to_discord()
        assert await manager.save_to_discord()  # nothing changed the second time
    assert storage.saves == ["server_config_2"]


@pytest.mark.asyncio
async def test_a_failed_save_is_retried_next_time():
    storage = FakeStorage()
    storage.save = AsyncMock(side_effect=[False, True])
    manager = _manager()
    manager._loaded = True
    manager.set_setting(1, "auto_responses", False)
    with patch('cfb_bot.utils.storage.get_storage', return_value=storage):
        assert not await manager.save_to_discord()
        assert await manager.save_to_discord()
    assert storage.save.await_count == 2
