#!/usr/bin/env python3
"""
/admin no_reactions: a listed member reacts to someone else's post, and Harry takes it off.
Their own posts, and everyone else's reactions, are left alone.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from cfb_bot.cogs import admin as admin_module
from cfb_bot.cogs.admin import AdminCog, no_reaction_users

GUILD, LISTED, OTHER = 1, 42, 7


def _cog():
    cog = AdminCog(MagicMock())
    channel = MagicMock()
    message = MagicMock(remove_reaction=AsyncMock())
    channel.get_partial_message.return_value = message
    cog.bot.get_channel.return_value = channel
    return cog, message


def _payload(user_id=LISTED, author_id=OTHER, guild_id=GUILD):
    return MagicMock(guild_id=guild_id, user_id=user_id, message_author_id=author_id,
                     channel_id=5, message_id=6, emoji="😂")


@pytest.fixture
def listed():
    with patch.object(admin_module.server_config, 'get_setting', return_value=[LISTED]):
        yield


@pytest.mark.asyncio
async def test_removes_a_listed_members_reaction_on_someone_elses_post(listed):
    cog, message = _cog()
    await cog.on_raw_reaction_add(_payload())
    message.remove_reaction.assert_awaited_once()
    emoji, member = message.remove_reaction.call_args.args
    assert emoji == "😂" and member.id == LISTED


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [_payload(user_id=OTHER), _payload(author_id=LISTED), _payload(guild_id=None)])
async def test_leaves_everything_else_alone(listed, payload):
    cog, message = _cog()
    await cog.on_raw_reaction_add(payload)
    message.remove_reaction.assert_not_called()


@pytest.mark.asyncio
async def test_missing_permission_is_logged_not_raised(listed):
    cog, message = _cog()
    message.remove_reaction.side_effect = discord.Forbidden(MagicMock(status=403), "Missing Permissions")
    await cog.on_raw_reaction_add(_payload())  # no exception


@pytest.mark.asyncio
async def test_the_command_toggles_and_saves():
    cog, _ = _cog()
    cog.admin_manager = MagicMock()
    cog.admin_manager.is_admin.return_value = True
    settings = {}
    interaction = MagicMock(guild=MagicMock(id=GUILD))
    interaction.response.send_message = AsyncMock()
    user = MagicMock(id=LISTED, mention="<@42>")
    with patch.object(admin_module.server_config, 'get_setting', side_effect=lambda g, k, d=None: settings.get(k, d)), \
         patch.object(admin_module.server_config, 'set_setting', side_effect=lambda g, k, v: settings.__setitem__(k, v)), \
         patch.object(admin_module.server_config, 'save_to_discord', AsyncMock()) as save:
        await AdminCog.no_reactions.callback(cog, interaction, user)
        assert no_reaction_users(GUILD) == [LISTED]
        await AdminCog.no_reactions.callback(cog, interaction, user)
        assert no_reaction_users(GUILD) == []
    assert save.await_count == 2


@pytest.mark.asyncio
async def test_non_admins_cant_toggle():
    cog, _ = _cog()
    cog.admin_manager = MagicMock()
    cog.admin_manager.is_admin.return_value = False
    interaction = MagicMock(guild=MagicMock(id=GUILD))
    interaction.user.guild_permissions.administrator = False
    interaction.response.send_message = AsyncMock()
    with patch.object(admin_module.server_config, 'set_setting') as set_setting:
        await AdminCog.no_reactions.callback(cog, interaction, MagicMock(id=LISTED))
    set_setting.assert_not_called()
