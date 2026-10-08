#!/usr/bin/env python3
"""
Unit tests for channel-scoped /fun target (FunCog._trolling_allowed_here)
"""

from unittest.mock import MagicMock

import pytest

TROLL_CHANNEL = 100
OTHER_CHANNEL = 200


def make_cog(blocked=()):
    from cfb_bot.cogs.fun import FunCog

    cog = FunCog(MagicMock())
    channel_manager = MagicMock()
    channel_manager.is_channel_blocked = lambda cid: cid in blocked
    cog.set_dependencies(admin_manager=MagicMock(), ai_assistant=MagicMock(), channel_manager=channel_manager)
    return cog


def make_message(channel_id, parent_id=None):
    message = MagicMock()
    message.channel.id = channel_id
    message.channel.parent_id = parent_id
    return message


class TestTargetScope:
    def test_trolls_in_the_channel_it_was_set_in(self):
        cog = make_cog()
        assert cog._trolling_allowed_here(make_message(TROLL_CHANNEL), {'channel_id': TROLL_CHANNEL})

    def test_stays_out_of_other_channels(self):
        cog = make_cog()
        assert not cog._trolling_allowed_here(make_message(OTHER_CHANNEL), {'channel_id': TROLL_CHANNEL})

    def test_threads_count_as_their_parent_channel(self):
        cog = make_cog()
        thread = make_message(555, parent_id=TROLL_CHANNEL)
        assert cog._trolling_allowed_here(thread, {'channel_id': TROLL_CHANNEL})

    def test_everywhere_targets_work_in_any_channel(self):
        cog = make_cog()
        assert cog._trolling_allowed_here(make_message(OTHER_CHANNEL), {'channel_id': None})

    def test_legacy_target_without_channel_is_server_wide(self):
        cog = make_cog()
        assert cog._trolling_allowed_here(make_message(OTHER_CHANNEL), {'timeout': 30})

    def test_blocked_channels_are_never_trolled(self):
        cog = make_cog(blocked={TROLL_CHANNEL})
        assert not cog._trolling_allowed_here(make_message(TROLL_CHANNEL), {'channel_id': TROLL_CHANNEL})
        assert not cog._trolling_allowed_here(make_message(TROLL_CHANNEL), {'channel_id': None})

    def test_works_without_a_channel_manager(self):
        from cfb_bot.cogs.fun import FunCog

        cog = FunCog(MagicMock())
        assert cog._trolling_allowed_here(make_message(TROLL_CHANNEL), {'channel_id': TROLL_CHANNEL})


class TestListenerRespectsScope:
    @pytest.mark.asyncio
    async def test_listener_ignores_target_in_other_channel(self):
        cog = make_cog()
        cog.targets = {1: {42: {'timeout': 30, 'last_triggered': 0, 'engage': True, 'channel_id': TROLL_CHANNEL}}}

        message = MagicMock()
        message.author.bot = False
        message.author.id = 42
        message.guild.id = 1
        message.channel.id = OTHER_CHANNEL
        message.channel.parent_id = None
        message.reference = None
        message.content = "harry you muppet"
        message.mentions = []
        message.channel.send = MagicMock()
        message.add_reaction = MagicMock()

        await cog.on_message(message)

        message.channel.send.assert_not_called()
        message.add_reaction.assert_not_called()
