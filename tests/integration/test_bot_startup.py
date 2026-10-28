#!/usr/bin/env python3
"""
Bot Startup Integration Test

This test validates that the cog-based bot architecture works:
1. Bot can be instantiated
2. All cogs can be loaded
3. Command groups are registered
4. No import errors or circular dependencies

This does NOT connect to Discord - it just validates the code structure.

Run with: pytest tests/integration/test_bot_startup.py -v
"""

import pytest
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestBotStartup:
    """Test that the bot can start and load all cogs"""

    def test_import_bot_main(self):
        """Test that bot_main.py can be imported without errors"""
        # This catches import errors, circular dependencies, etc.
        try:
            from cfb_bot import bot_main
            assert bot_main is not None
            assert hasattr(bot_main, 'bot')
            assert hasattr(bot_main, 'load_cogs')
            assert hasattr(bot_main, 'COG_EXTENSIONS')
        except ImportError as e:
            pytest.fail(f"Failed to import bot_main: {e}")

    def test_cog_extensions_defined(self):
        """Test that all cog extensions are defined"""
        from cfb_bot.bot_main import COG_EXTENSIONS

        expected_cogs = [
            'cfb_bot.cogs.core',
            'cfb_bot.cogs.ai_chat',
            'cfb_bot.cogs.recruiting',
            'cfb_bot.cogs.cfb_data',
            'cfb_bot.cogs.hs_stats',
            'cfb_bot.cogs.league',
            'cfb_bot.cogs.charter',
            'cfb_bot.cogs.admin',
        ]

        for cog in expected_cogs:
            assert cog in COG_EXTENSIONS, f"Missing cog: {cog}"

    def test_import_all_cogs(self):
        """Test that all cog modules can be imported"""
        cogs_to_test = [
            ('cfb_bot.cogs.core', 'CoreCog'),
            ('cfb_bot.cogs.ai_chat', 'AIChatCog'),
            ('cfb_bot.cogs.recruiting', 'RecruitingCog'),
            ('cfb_bot.cogs.cfb_data', 'CFBDataCog'),
            ('cfb_bot.cogs.hs_stats', 'HSStatsCog'),
            ('cfb_bot.cogs.league', 'LeagueCog'),
            ('cfb_bot.cogs.charter', 'CharterCog'),
            ('cfb_bot.cogs.admin', 'AdminCog'),
        ]

        for module_name, class_name in cogs_to_test:
            try:
                module = __import__(module_name, fromlist=[class_name])
                cog_class = getattr(module, class_name)
                assert cog_class is not None, f"{class_name} not found in {module_name}"
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")
            except AttributeError as e:
                pytest.fail(f"{class_name} not found in {module_name}: {e}")

    def test_cog_has_setup_function(self):
        """Test that all cogs have the required setup() function"""
        cog_modules = [
            'cfb_bot.cogs.core',
            'cfb_bot.cogs.ai_chat',
            'cfb_bot.cogs.recruiting',
            'cfb_bot.cogs.cfb_data',
            'cfb_bot.cogs.hs_stats',
            'cfb_bot.cogs.league',
            'cfb_bot.cogs.charter',
            'cfb_bot.cogs.admin',
        ]

        for module_name in cog_modules:
            module = __import__(module_name, fromlist=['setup'])
            assert hasattr(module, 'setup'), f"{module_name} missing setup() function"
            assert asyncio.iscoroutinefunction(module.setup), f"{module_name}.setup() must be async"

    def test_config_imports(self):
        """Test that config module imports correctly"""
        try:
            from cfb_bot.config import Colors, Footers

            # Verify Colors has expected attributes
            assert hasattr(Colors, 'PRIMARY')
            assert hasattr(Colors, 'SUCCESS')
            assert hasattr(Colors, 'ERROR')
            assert hasattr(Colors, 'WARNING')

            # Verify Footers has expected attributes
            assert hasattr(Footers, 'CFB_DATA')

        except ImportError as e:
            pytest.fail(f"Failed to import config: {e}")

    def test_services_imports(self):
        """Test that services module imports correctly"""
        try:
            from cfb_bot.services.checks import check_module_enabled, check_module_enabled_deferred

            assert asyncio.iscoroutinefunction(check_module_enabled)
            assert asyncio.iscoroutinefunction(check_module_enabled_deferred)

        except ImportError as e:
            pytest.fail(f"Failed to import services: {e}")

    def test_server_config_imports(self):
        """Test that server_config imports correctly"""
        try:
            from cfb_bot.utils.server_config import server_config, FeatureModule

            # Verify FeatureModule enum
            assert hasattr(FeatureModule, 'CORE')
            assert hasattr(FeatureModule, 'AI_CHAT')
            assert hasattr(FeatureModule, 'CFB_DATA')
            assert hasattr(FeatureModule, 'LEAGUE')
            assert hasattr(FeatureModule, 'HS_STATS')
            assert hasattr(FeatureModule, 'RECRUITING')

        except ImportError as e:
            pytest.fail(f"Failed to import server_config: {e}")


class TestCogInstantiation:
    """Test that cogs can be instantiated with a mock bot"""

    def test_instantiate_core_cog(self):
        """Test CoreCog can be instantiated"""
        from unittest.mock import MagicMock
        from cfb_bot.cogs.core import CoreCog

        mock_bot = MagicMock()
        cog = CoreCog(mock_bot)

        assert cog is not None
        assert cog.bot == mock_bot

    def test_instantiate_all_cogs(self):
        """Test all cogs can be instantiated"""
        from unittest.mock import MagicMock

        cogs_to_test = [
            ('cfb_bot.cogs.core', 'CoreCog'),
            ('cfb_bot.cogs.ai_chat', 'AIChatCog'),
            ('cfb_bot.cogs.recruiting', 'RecruitingCog'),
            ('cfb_bot.cogs.cfb_data', 'CFBDataCog'),
            ('cfb_bot.cogs.hs_stats', 'HSStatsCog'),
            ('cfb_bot.cogs.league', 'LeagueCog'),
            ('cfb_bot.cogs.charter', 'CharterCog'),
            ('cfb_bot.cogs.admin', 'AdminCog'),
        ]

        mock_bot = MagicMock()

        for module_name, class_name in cogs_to_test:
            module = __import__(module_name, fromlist=[class_name])
            cog_class = getattr(module, class_name)

            try:
                cog = cog_class(mock_bot)
                assert cog is not None, f"Failed to instantiate {class_name}"
                assert cog.bot == mock_bot, f"{class_name} didn't store bot reference"
            except Exception as e:
                pytest.fail(f"Failed to instantiate {class_name}: {e}")


class TestCommandGroups:
    """Test that command groups are properly defined"""

    def test_recruiting_group_exists(self):
        """Test recruiting command group is defined"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        assert hasattr(RecruitingCog, 'recruiting_group')

    def test_cfb_group_exists(self):
        """Test cfb command group is defined"""
        from cfb_bot.cogs.cfb_data import CFBDataCog

        assert hasattr(CFBDataCog, 'cfb_group')

    def test_hs_group_exists(self):
        """Test hs command group is defined"""
        from cfb_bot.cogs.hs_stats import HSStatsCog

        assert hasattr(HSStatsCog, 'hs_group')

    def test_league_group_exists(self):
        """Test league command group is defined"""
        from cfb_bot.cogs.league import LeagueCog

        assert hasattr(LeagueCog, 'league_group')

    def test_charter_group_exists(self):
        """Test charter command group is defined"""
        from cfb_bot.cogs.charter import CharterCog

        assert hasattr(CharterCog, 'charter_group')

    def test_admin_group_exists(self):
        """Test admin command group is defined"""
        from cfb_bot.cogs.admin import AdminCog

        assert hasattr(AdminCog, 'admin_group')


class TestDependencyInjection:
    """Test that set_dependencies methods exist and work"""

    def test_cogs_have_set_dependencies(self):
        """Test cogs that need dependencies have set_dependencies method"""
        from unittest.mock import MagicMock

        cogs_with_dependencies = [
            ('cfb_bot.cogs.core', 'CoreCog'),
            ('cfb_bot.cogs.ai_chat', 'AIChatCog'),
            ('cfb_bot.cogs.league', 'LeagueCog'),
            ('cfb_bot.cogs.charter', 'CharterCog'),
            ('cfb_bot.cogs.admin', 'AdminCog'),
        ]

        mock_bot = MagicMock()

        for module_name, class_name in cogs_with_dependencies:
            module = __import__(module_name, fromlist=[class_name])
            cog_class = getattr(module, class_name)
            cog = cog_class(mock_bot)

            assert hasattr(cog, 'set_dependencies'), \
                f"{class_name} missing set_dependencies method"

    def test_set_dependencies_doesnt_crash(self):
        """Test calling set_dependencies with None values doesn't crash"""
        from unittest.mock import MagicMock
        from cfb_bot.cogs.league import LeagueCog

        mock_bot = MagicMock()
        cog = LeagueCog(mock_bot)

        # Should not raise exception
        cog.set_dependencies(
            timekeeper_manager=None,
            admin_manager=None,
            schedule_manager=None,
            channel_summarizer=None,
            ai_assistant=None,
            AI_AVAILABLE=False
        )
