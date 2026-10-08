#!/usr/bin/env python3
"""
Unit tests for the @requires_admin / @requires_module command decorators
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.services.checks import requires_admin, requires_module
from cfb_bot.utils.server_config import FeatureModule


def make_interaction():
    interaction = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.guild.id = 1
    interaction.channel.id = 2
    return interaction


class AdminCog:
    def __init__(self, allowed=True):
        self.admin_manager = MagicMock()
        self.admin_manager.is_admin = MagicMock(return_value=allowed)

    @requires_admin("no chance")
    async def cmd(self, interaction, value: int = 1):
        """A command"""
        return f"ran {value}"


class LeagueStyleCog:
    def __init__(self, allowed=True):
        self.admin_manager = MagicMock()
        self._allowed = allowed

    def _is_league_admin(self, interaction):
        return self._allowed

    @requires_admin()
    async def cmd(self, interaction):
        return "ran"


class TestRequiresAdmin:
    @pytest.mark.asyncio
    async def test_runs_for_admins_and_passes_arguments(self):
        assert await AdminCog().cmd(make_interaction(), value=7) == "ran 7"

    @pytest.mark.asyncio
    async def test_refuses_non_admins_with_the_given_message(self):
        interaction = make_interaction()
        assert await AdminCog(allowed=False).cmd(interaction) is None
        interaction.response.send_message.assert_awaited_once_with("no chance", ephemeral=True)

    @pytest.mark.asyncio
    async def test_refuses_when_admin_manager_is_missing(self):
        cog = AdminCog()
        cog.admin_manager = None
        interaction = make_interaction()
        assert await cog.cmd(interaction) is None
        interaction.response.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_prefers_the_cogs_own_league_admin_check(self):
        assert await LeagueStyleCog(allowed=True).cmd(make_interaction()) == "ran"
        assert await LeagueStyleCog(allowed=False).cmd(make_interaction()) is None

    def test_keeps_the_command_signature_for_discord(self):
        import inspect
        assert AdminCog.cmd.__name__ == 'cmd'
        assert list(inspect.signature(AdminCog.cmd).parameters) == ['self', 'interaction', 'value']


class ModuleCog:
    @requires_module(FeatureModule.LEAGUE)
    async def cmd(self, interaction):
        return "ran"


class TestRequiresModule:
    @pytest.mark.asyncio
    async def test_runs_when_module_enabled(self):
        config = MagicMock()
        config.is_module_enabled.return_value = True
        config.get_enabled_channels.return_value = []
        with patch('cfb_bot.services.checks.sys.modules', {ModuleCog.cmd.__module__: MagicMock(server_config=config)}):
            assert await ModuleCog().cmd(make_interaction()) == "ran"

    @pytest.mark.asyncio
    async def test_refuses_when_module_disabled(self):
        config = MagicMock()
        config.is_module_enabled.return_value = False
        interaction = make_interaction()
        with patch('cfb_bot.services.checks.sys.modules', {ModuleCog.cmd.__module__: MagicMock(server_config=config)}):
            assert await ModuleCog().cmd(interaction) is None
        interaction.response.send_message.assert_awaited_once()
