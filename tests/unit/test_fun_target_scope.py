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


class TestFunModuleToggle:
    """Turning Fun & Games off in /admin config must silence /fun and the trolling."""

    @pytest.mark.asyncio
    async def test_commands_refuse_when_module_off(self, mock_interaction):
        from unittest.mock import patch
        cog = make_cog()
        off = MagicMock()
        off.is_module_enabled.return_value = False
        with patch('cfb_bot.cogs.fun.server_config', off):
            await cog.roast.callback(cog, mock_interaction, MagicMock())
        mock_interaction.response.send_message.assert_awaited_once()
        assert not cog.ai_assistant.method_calls  # never got as far as roasting

    @pytest.mark.asyncio
    async def test_listener_ignores_targets_when_module_off(self):
        from unittest.mock import patch
        cog = make_cog()
        cog._targets_for_guild = MagicMock()
        message = make_message(TROLL_CHANNEL)
        message.author.bot = False
        off = MagicMock()
        off.is_module_enabled.return_value = False
        with patch('cfb_bot.cogs.fun.server_config', off):
            await cog.on_message(message)
        cog._targets_for_guild.assert_not_called()


class TestAIRoasts:
    """/fun roast and argument comebacks call the real AI method (ask_question never existed)."""

    @pytest.mark.asyncio
    async def test_roast_uses_ask_ai(self, mock_interaction, mock_server_config):
        from unittest.mock import AsyncMock, patch
        cog = make_cog()
        cog.ai_assistant.ask_ai = AsyncMock(return_value="ya muppet 💀")
        cog._is_duplicate_interaction = MagicMock(return_value=False)
        target = MagicMock(bot=False, mention="<@1>")
        with patch('cfb_bot.cogs.fun.server_config', mock_server_config):
            await cog.roast.callback(cog, mock_interaction, target)
        cog.ai_assistant.ask_ai.assert_awaited_once()
        assert mock_interaction.followup.send.call_args.args[0] == "<@1> ya muppet 💀"

    @pytest.mark.asyncio
    async def test_comeback_falls_back_when_ai_is_silent(self):
        from unittest.mock import AsyncMock
        cog = make_cog()
        cog.ai_assistant.ask_ai = AsyncMock(return_value=None)
        cog._get_fallback_comeback = MagicMock(return_value="canned")
        assert await cog._generate_ai_comeback("you suck", "Bob") == "canned"
