#!/usr/bin/env python3
"""
Unit tests for AdminCog

Tests:
- /admin set_channel - Set admin channel
- /admin add - Add bot admin
- /admin remove - Remove bot admin
- /admin list - List admins
- /admin block - Block channel
- /admin unblock - Unblock channel
- /admin blocked - Show blocked channels
- /admin config - Configure modules
- /admin sync - Sync commands
- /admin channels - Manage channel whitelist
- /admin debug - Debug tools
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestAdminSetChannel:
    """Tests for /admin set_channel command"""

    @pytest.mark.asyncio
    async def test_set_channel_requires_admin(self, mock_interaction, mock_server_config):
        """Non-admin cannot set admin channel"""
        from cfb_bot.cogs.admin import AdminCog

        cog = AdminCog(MagicMock())
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = False

        # Call the callback directly for testing
        await cog.set_channel.callback(cog, mock_interaction, channel=MagicMock())

        mock_interaction.response.send_message.assert_called_once()
        call_kwargs = mock_interaction.response.send_message.call_args
        assert call_kwargs.kwargs.get('ephemeral') == True
        assert "admin" in str(call_kwargs.args[0]).lower()

    @pytest.mark.asyncio
    async def test_set_channel_success(self, mock_interaction, mock_server_config):
        """Admin can set admin channel"""
        from cfb_bot.cogs.admin import AdminCog

        mock_channel = MagicMock()
        mock_channel.id = 123456
        mock_channel.name = "admin-logs"

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = MagicMock()
            cog.admin_manager.is_admin.return_value = True

            await cog.set_channel.callback(cog, mock_interaction, channel=mock_channel)

            mock_server_config.set_admin_channel.assert_called_once()
            mock_server_config.save_to_discord.assert_called_once()


class TestAdminAddRemove:
    """Tests for /admin add and /admin remove"""

    @pytest.mark.asyncio
    async def test_add_admin(self, mock_interaction):
        """Test adding a bot admin"""
        from cfb_bot.cogs.admin import AdminCog

        cog = AdminCog(MagicMock())
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = True
        cog.admin_manager.add_admin.return_value = True

        new_admin = MagicMock()
        new_admin.id = 999
        new_admin.display_name = "New Admin"

        await cog.add.callback(cog, mock_interaction, user=new_admin)

        cog.admin_manager.add_admin.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_remove_admin(self, mock_interaction):
        """Test removing a bot admin"""
        from cfb_bot.cogs.admin import AdminCog

        cog = AdminCog(MagicMock())
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = True
        cog.admin_manager.remove_admin.return_value = True

        old_admin = MagicMock()
        old_admin.id = 999
        old_admin.display_name = "Old Admin"

        await cog.remove.callback(cog, mock_interaction, user=old_admin)

        cog.admin_manager.remove_admin.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_add_already_admin(self, mock_interaction):
        """Test adding someone who is already admin"""
        from cfb_bot.cogs.admin import AdminCog

        cog = AdminCog(MagicMock())
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = True
        cog.admin_manager.add_admin.return_value = False  # Already admin

        user = MagicMock()
        user.display_name = "Already Admin"

        await cog.add.callback(cog, mock_interaction, user=user)

        # Should send "already admin" message
        call_kwargs = mock_interaction.response.send_message.call_args
        embed = call_kwargs.kwargs.get('embed')
        assert "Already" in embed.title


class TestAdminConfig:
    """Tests for /admin config command"""

    @pytest.mark.asyncio
    async def test_config_view(self, mock_interaction, mock_server_config):
        """Test viewing config"""
        from cfb_bot.cogs.admin import AdminCog

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = None

            await cog.config.callback(cog, mock_interaction, action="view")

            mock_interaction.response.defer.assert_called_once()
            mock_interaction.followup.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_enable_requires_admin(self, mock_interaction, mock_server_config):
        """Test enabling module requires admin"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user.guild_permissions.administrator = False

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = None

            await cog.config.callback(cog, mock_interaction, action="enable", module="recruiting")

            call_kwargs = mock_interaction.response.send_message.call_args
            assert call_kwargs.kwargs.get('ephemeral') == True

    @pytest.mark.asyncio
    async def test_config_enable_module(self, mock_interaction, mock_server_config, mock_admin_user):
        """Test enabling a module as admin"""
        from cfb_bot.cogs.admin import AdminCog
        from cfb_bot.utils.server_config import FeatureModule

        mock_interaction.user = mock_admin_user

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = MagicMock()
            cog.admin_manager.is_admin.return_value = True

            await cog.config.callback(cog, mock_interaction, action="enable", module="cfb_data")

            mock_server_config.enable_module.assert_called_once()
            mock_server_config.save_to_discord.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_cannot_disable_core(self, mock_interaction, mock_server_config, mock_admin_user):
        """Test that core module cannot be disabled"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = MagicMock()
            cog.admin_manager.is_admin.return_value = True

            await cog.config.callback(cog, mock_interaction, action="disable", module="core")

            # Should NOT call disable_module for core
            mock_server_config.disable_module.assert_not_called()


class TestAdminChannels:
    """Tests for /admin channels command"""

    @pytest.mark.asyncio
    async def test_channels_view(self, mock_interaction, mock_server_config):
        """Test viewing channel status"""
        from cfb_bot.cogs.admin import AdminCog

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = None

            await cog.channels.callback(cog, mock_interaction, action=None)

            mock_interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_channels_enable(self, mock_interaction, mock_server_config, mock_admin_user):
        """Test enabling Harry in a channel"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = MagicMock()
            cog.admin_manager.is_admin.return_value = True

            await cog.channels.callback(cog, mock_interaction, action="enable")

            mock_server_config.enable_channel.assert_called_once()

    @pytest.mark.asyncio
    async def test_channels_toggle_rivalry(self, mock_interaction, mock_server_config, mock_admin_user):
        """Test toggling rivalry auto-responses"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user
        mock_server_config.toggle_auto_responses.return_value = True  # Now ON

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(MagicMock())
            cog.admin_manager = MagicMock()
            cog.admin_manager.is_admin.return_value = True

            await cog.channels.callback(cog, mock_interaction, action="toggle_rivalry")

            mock_server_config.toggle_auto_responses.assert_called_once()


class TestAdminSync:
    """Tests for /admin sync command"""

    @pytest.mark.asyncio
    async def test_sync_requires_admin(self, mock_interaction):
        """Test sync requires admin"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user.guild_permissions.administrator = False

        cog = AdminCog(MagicMock())
        cog.admin_manager = None

        await cog.sync_commands.callback(cog, mock_interaction)

        call_kwargs = mock_interaction.response.send_message.call_args
        assert call_kwargs.kwargs.get('ephemeral') == True

    @pytest.mark.asyncio
    async def test_sync_guild_success(self, mock_interaction, mock_admin_user, mock_bot):
        """Test syncing to guild"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user
        mock_interaction.guild = MagicMock()

        cog = AdminCog(mock_bot)
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = True
        mock_bot.tree.sync.return_value = ["cmd1", "cmd2", "cmd3"]

        await cog.sync_commands.callback(cog, mock_interaction)

        mock_bot.tree.sync.assert_called_once()


class TestAdminBlockChannel:
    """Tests for /admin block and /admin unblock"""

    @pytest.mark.asyncio
    async def test_block_channel(self, mock_interaction, mock_channel, mock_admin_user):
        """Test blocking a channel"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user

        cog = AdminCog(MagicMock())
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = True
        cog.channel_manager = MagicMock()
        cog.channel_manager.block_channel.return_value = True

        await cog.block.callback(cog, mock_interaction, channel=mock_channel)

        cog.channel_manager.block_channel.assert_called_once_with(mock_channel.id)

    @pytest.mark.asyncio
    async def test_unblock_channel(self, mock_interaction, mock_channel, mock_admin_user):
        """Test unblocking a channel"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user

        cog = AdminCog(MagicMock())
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = True
        cog.channel_manager = MagicMock()
        cog.channel_manager.unblock_channel.return_value = True

        await cog.unblock.callback(cog, mock_interaction, channel=mock_channel)

        cog.channel_manager.unblock_channel.assert_called_once_with(mock_channel.id)


class TestAdminDebug:
    """Tests for /admin debug command"""

    @pytest.mark.asyncio
    async def test_debug_requires_admin(self, mock_interaction):
        """Test debug requires admin"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user.guild_permissions.administrator = False

        cog = AdminCog(MagicMock())
        cog.admin_manager = None

        # Handle case where command wrapper isn't applied in test env
        if hasattr(cog.debug, 'callback'):
            await cog.debug.callback(cog, mock_interaction, tool="info")
        else:
            await cog.debug(mock_interaction, tool="info")

        call_kwargs = mock_interaction.response.send_message.call_args
        assert call_kwargs.kwargs.get('ephemeral') == True

    @pytest.mark.asyncio
    async def test_debug_info(self, mock_interaction, mock_server_config, mock_admin_user, mock_bot):
        """Test debug info tool"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user
        mock_bot.latency = 0.05
        mock_bot.guilds = [MagicMock(), MagicMock()]
        mock_bot.users = [MagicMock(), MagicMock(), MagicMock()]
        # mock created_at for uptime check
        mock_bot.user.created_at.timestamp.return_value = 1600000000

        with patch('cfb_bot.cogs.admin.server_config', mock_server_config):
            cog = AdminCog(mock_bot)
            cog.admin_manager = MagicMock()
            cog.admin_manager.is_admin.return_value = True

            if hasattr(cog.debug, 'callback'):
                await cog.debug.callback(cog, mock_interaction, tool="info")
            else:
                await cog.debug(mock_interaction, tool="info")

            mock_interaction.response.defer.assert_called_once()
            mock_interaction.followup.send.assert_called_once()

            # Check embed content
            call_kwargs = mock_interaction.followup.send.call_args
            embed = call_kwargs.kwargs.get('embed')
            assert "System Debug Info" in embed.title
            # Check fields exist (partial match due to emojis)
            field_names = [f.name for f in embed.fields]
            assert any("System" in name for name in field_names)
            assert any("Bot" in name for name in field_names)

    @pytest.mark.asyncio
    async def test_debug_test_url_invalid(self, mock_interaction, mock_admin_user):
        """Test debug test_url with invalid URL"""
        from cfb_bot.cogs.admin import AdminCog

        mock_interaction.user = mock_admin_user

        cog = AdminCog(MagicMock())
        cog.admin_manager = MagicMock()
        cog.admin_manager.is_admin.return_value = True

        if hasattr(cog.debug, 'callback'):
            await cog.debug.callback(cog, mock_interaction, tool="test_url", url="ftp://example.com")
        else:
            await cog.debug(mock_interaction, tool="test_url", url="ftp://example.com")

        mock_interaction.followup.send.assert_called_with("❌ URL must start with http:// or https://", ephemeral=True)
