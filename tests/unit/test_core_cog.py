#!/usr/bin/env python3
"""
Unit tests for CoreCog

Tests:
- /help command shows appropriate modules based on config
- /version command displays version info
- /changelog command shows version history
- /whats_new command shows latest features
- /tokens command shows AI token usage
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestHelpCommand:
    """Tests for /help command"""

    @pytest.mark.asyncio
    async def test_help_shows_all_enabled_modules(self, mock_interaction, mock_server_config):
        """Help should show all modules when all are enabled"""
        from cfb_bot.cogs.core import CoreCog

        with patch('cfb_bot.cogs.core.server_config', mock_server_config):
            cog = CoreCog(MagicMock())
            await cog.help_cmd.callback(cog, mock_interaction)

            # Should have called send_message
            mock_interaction.response.send_message.assert_called_once()

            # Get the embed from the call
            call_kwargs = mock_interaction.response.send_message.call_args
            embed = call_kwargs.kwargs.get('embed') or call_kwargs.args[0]

            # Verify title
            assert "Harry" in embed.title
            assert "Command Reference" in embed.title

    @pytest.mark.asyncio
    async def test_help_hides_disabled_modules(self, mock_interaction, disabled_modules_config):
        """Help should show disabled modules note when some are off"""
        from cfb_bot.cogs.core import CoreCog

        with patch('cfb_bot.cogs.core.server_config', disabled_modules_config):
            cog = CoreCog(MagicMock())
            await cog.help_cmd.callback(cog, mock_interaction)

            mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_always_shows_core_commands(self, mock_interaction, mock_server_config):
        """Help should always show always-available commands"""
        from cfb_bot.cogs.core import CoreCog

        # Even with all modules disabled, core commands should show
        mock_server_config.get_enabled_modules = MagicMock(return_value=["core"])

        with patch('cfb_bot.cogs.core.server_config', mock_server_config):
            cog = CoreCog(MagicMock())
            await cog.help_cmd.callback(cog, mock_interaction)

            call_kwargs = mock_interaction.response.send_message.call_args
            embed = call_kwargs.kwargs.get('embed') or call_kwargs.args[0]

            # Should have "Always Available" field
            field_names = [f.name for f in embed.fields]
            assert any("Always Available" in name for name in field_names)


class TestVersionCommand:
    """Tests for /version command"""

    @pytest.mark.asyncio
    async def test_version_shows_current_version(self, mock_interaction):
        """Version should display current version"""
        from cfb_bot.cogs.core import CoreCog

        cog = CoreCog(MagicMock())

        # Mock version manager
        cog.version_manager.get_current_version = MagicMock(return_value="2.5.1")
        cog.version_manager.get_latest_version_info = MagicMock(return_value={
            "title": "Test Release",
            "date": "January 11, 2026",
            "emoji": "🎉"
        })
        cog.version_manager.get_all_versions = MagicMock(return_value=["2.5.1", "2.5.0", "2.4.0"])

        await cog.version.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_called_once()
        call_kwargs = mock_interaction.response.send_message.call_args
        embed = call_kwargs.kwargs.get('embed') or call_kwargs.args[0]

        assert "2.5.1" in embed.title


class TestChangelogCommand:
    """Tests for /changelog command"""

    @pytest.mark.asyncio
    async def test_changelog_no_version_shows_summary(self, mock_interaction):
        """Changelog with no version should show summary"""
        from cfb_bot.cogs.core import CoreCog

        cog = CoreCog(MagicMock())
        cog.version_manager.get_version_summary = MagicMock(return_value="v2.5.1 - Latest\nv2.5.0 - Previous")
        cog.version_manager.get_current_version = MagicMock(return_value="2.5.1")

        await cog.changelog.callback(cog, mock_interaction, version=None)

        mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_changelog_specific_version(self, mock_interaction):
        """Changelog with version should show that version's details"""
        from cfb_bot.cogs.core import CoreCog

        cog = CoreCog(MagicMock())
        cog.version_manager.format_version_embed_data = MagicMock(return_value={
            "title": "v2.5.0",
            "description": "Transfer Portal Detection!",
            "fields": [
                {"name": "📝 Changes", "value": "- Added portal detection", "inline": False}
            ]
        })
        cog.version_manager.get_current_version = MagicMock(return_value="2.5.1")

        await cog.changelog.callback(cog, mock_interaction, version="2.5.0")

        mock_interaction.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_changelog_invalid_version(self, mock_interaction):
        """Changelog with invalid version should show error"""
        from cfb_bot.cogs.core import CoreCog

        cog = CoreCog(MagicMock())
        cog.version_manager.format_version_embed_data = MagicMock(return_value=None)

        await cog.changelog.callback(cog, mock_interaction, version="99.99.99")

        mock_interaction.response.send_message.assert_called_once()
        call_kwargs = mock_interaction.response.send_message.call_args

        # Should be ephemeral error
        assert call_kwargs.kwargs.get('ephemeral') == True


class TestWhatsNewCommand:
    """Tests for /whats_new command"""

    @pytest.mark.asyncio
    async def test_whats_new_shows_latest(self, mock_interaction):
        """Whats new should show latest version info"""
        from cfb_bot.cogs.core import CoreCog

        cog = CoreCog(MagicMock())
        cog.version_manager.get_latest_version_info = MagicMock(return_value={
            "title": "Transfer Portal Detection! 🌀",
            "date": "January 10, 2026",
            "changes": [
                "Added transfer portal detection for individual players",
                "Added portal indicator in team commits",
                "UI improvements"
            ]
        })
        cog.version_manager.get_current_version = MagicMock(return_value="2.5.0")

        await cog.whats_new.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_called_once()


class TestTokensCommand:
    """Tests for /tokens command"""

    @pytest.mark.asyncio
    async def test_tokens_with_ai_available(self, mock_interaction):
        """Tokens should show stats when AI is available"""
        from cfb_bot.cogs.core import CoreCog

        cog = CoreCog(MagicMock())
        cog.AI_AVAILABLE = True
        cog.ai_assistant = MagicMock()
        cog.ai_assistant.get_token_usage = MagicMock(return_value={
            "total_requests": 100,
            "openai_tokens": 50000,
            "anthropic_tokens": 30000,
            "total_tokens": 80000
        })

        await cog.tokens.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_called_once()
        call_kwargs = mock_interaction.response.send_message.call_args
        embed = call_kwargs.kwargs.get('embed') or call_kwargs.args[0]

        assert "Token Usage" in embed.title

    @pytest.mark.asyncio
    async def test_tokens_without_ai(self, mock_interaction):
        """Tokens should show error when AI not available"""
        from cfb_bot.cogs.core import CoreCog

        cog = CoreCog(MagicMock())
        cog.AI_AVAILABLE = False
        cog.ai_assistant = None

        await cog.tokens.callback(cog, mock_interaction)

        mock_interaction.response.send_message.assert_called_once()
        call_args = mock_interaction.response.send_message.call_args
        from cfb_bot.services.oops import NO_AI
        assert NO_AI in str(call_args)
