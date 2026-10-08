#!/usr/bin/env python3
"""
Environment variables must never take the bot down.

A variable added on Render but left empty is "set" to '', so os.getenv returns ''
instead of the default. OPENAI_COST_PER_1K='' crashed float() at import and the bot
crash-looped; OPENAI_MODEL='' asked OpenAI for a model named empty string.
"""

import importlib

import pytest

from cfb_bot.config import env_float, env_str


class TestEnvHelpers:
    def test_blank_and_whitespace_fall_back(self, monkeypatch):
        monkeypatch.setenv('HARRY_TEST_STR', '')
        assert env_str('HARRY_TEST_STR', 'default') == 'default'
        monkeypatch.setenv('HARRY_TEST_STR', '   ')
        assert env_str('HARRY_TEST_STR', 'default') == 'default'

    def test_unset_falls_back(self, monkeypatch):
        monkeypatch.delenv('HARRY_TEST_STR', raising=False)
        assert env_str('HARRY_TEST_STR', 'default') == 'default'

    def test_real_values_are_used_and_trimmed(self, monkeypatch):
        monkeypatch.setenv('HARRY_TEST_STR', '  gpt-5  ')
        assert env_str('HARRY_TEST_STR', 'default') == 'gpt-5'

    def test_float_handles_blank_and_garbage(self, monkeypatch):
        monkeypatch.setenv('HARRY_TEST_NUM', '')
        assert env_float('HARRY_TEST_NUM', 1.5) == 1.5
        monkeypatch.setenv('HARRY_TEST_NUM', 'banana')
        assert env_float('HARRY_TEST_NUM', 1.5) == 1.5
        monkeypatch.setenv('HARRY_TEST_NUM', '0.004')
        assert env_float('HARRY_TEST_NUM', 1.5) == 0.004


class TestConfigImport:
    @pytest.mark.parametrize("name", [
        'GAME_NAME', 'OPENAI_MODEL', 'ANTHROPIC_MODEL',
        'OPENAI_COST_PER_1K', 'ANTHROPIC_COST_PER_1K',
    ])
    def test_config_imports_with_the_variable_blank(self, name, monkeypatch):
        """This is the crash loop: config must import and keep its defaults."""
        monkeypatch.setenv(name, '')
        config = importlib.reload(importlib.import_module('cfb_bot.config'))
        try:
            assert config.OPENAI_MODEL == 'gpt-5-mini'
            assert config.ANTHROPIC_MODEL == 'claude-haiku-4-5'
            assert config.OPENAI_COST_PER_1K == 0.0009
            assert config.ANTHROPIC_COST_PER_1K == 0.002
            assert config.GAME_NAME == 'CFB 27'
        finally:
            monkeypatch.undo()
            importlib.reload(config)
