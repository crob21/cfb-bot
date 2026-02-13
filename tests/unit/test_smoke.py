#!/usr/bin/env python3
"""
Smoke tests - catch basic import and syntax errors
These run BEFORE detailed unit tests to fail fast on obvious issues.
"""

import pytest


class TestImports:
    """Test that all modules can be imported without errors"""

    def test_import_bot(self):
        """Test that main bot module imports"""
        # Bot migrated to bot_main.py with cogs architecture
        from cfb_bot.bot_main import bot, main
        assert bot is not None
        assert main is not None

    def test_import_all_cogs(self):
        """Test that all cog modules import without errors"""
        from cfb_bot.cogs.cfb_data import CFBDataCog
        from cfb_bot.cogs.recruiting import RecruitingCog
        from cfb_bot.cogs.hs_stats import HSStatsCog
        from cfb_bot.cogs.admin import AdminCog
        from cfb_bot.cogs.core import CoreCog

        assert CFBDataCog is not None
        assert RecruitingCog is not None
        assert HSStatsCog is not None
        assert AdminCog is not None
        assert CoreCog is not None

    def test_import_utils(self):
        """Test that utility modules import"""
        from cfb_bot.utils.cfb_data import cfb_data
        from cfb_bot.utils.on3_scraper import on3_scraper
        from cfb_bot.utils.server_config import server_config
        from cfb_bot.utils.version_manager import CURRENT_VERSION

        assert cfb_data is not None
        assert on3_scraper is not None
        assert server_config is not None
        assert CURRENT_VERSION is not None

    def test_import_services(self):
        """Test that service modules import"""
        from cfb_bot.services.checks import check_module_enabled, check_module_enabled_deferred

        assert check_module_enabled is not None
        assert check_module_enabled_deferred is not None

    def test_import_security_and_cost_tracker(self):
        """Test that security and cost_tracker import (sanitize_ai_response, budget)."""
        from cfb_bot.security import sanitize_ai_response
        from cfb_bot.utils.cost_tracker import get_cost_tracker

        assert sanitize_ai_response is not None
        assert get_cost_tracker is not None


class TestBasicSyntax:
    """Test basic Python syntax and structure"""

    def test_python_version(self):
        """Verify Python version is 3.12+"""
        import sys
        assert sys.version_info >= (3, 12), f"Python 3.12+ required, got {sys.version_info}"

    def test_no_syntax_errors_in_main(self):
        """Test that __main__ has no syntax errors"""
        import runpy
        # Just compile it, don't run it (bot_main.py is the entry point)
        with open('src/cfb_bot/bot_main.py', 'r') as f:
            code = f.read()
            compile(code, 'bot_main.py', 'exec')
