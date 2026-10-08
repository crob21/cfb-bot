#!/usr/bin/env python3
"""
AI model IDs live in config, not in the request bodies.

Harry sat on gpt-3.5-turbo long after it was legacy, and /admin budget priced every
call as if it were — because both the model and its cost were hardcoded in
ai/ai_integration.py.
"""

import importlib
import pathlib
import re

from cfb_bot.config import (ANTHROPIC_COST_PER_1K, ANTHROPIC_MODEL,
                            OPENAI_COST_PER_1K, OPENAI_MODEL)

AI_SOURCE = (pathlib.Path(__file__).resolve().parents[2]
             / "src" / "cfb_bot" / "ai" / "ai_integration.py").read_text()


def test_requests_use_the_configured_models():
    assert re.findall(r"'model': (\w+)", AI_SOURCE) == ['OPENAI_MODEL', 'ANTHROPIC_MODEL']


def test_no_hardcoded_model_ids_in_source():
    offenders = [line.strip() for line in AI_SOURCE.splitlines()
                 if re.search(r"['\"](?:gpt-|claude-|o\d-)[\w.-]+['\"]", line)]
    assert not offenders, f"Hardcoded model IDs: {offenders}"


def test_defaults_are_current_models():
    assert OPENAI_MODEL == 'gpt-4o-mini'
    assert ANTHROPIC_MODEL == 'claude-haiku-4-5'


def test_models_and_costs_are_env_configurable(monkeypatch):
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-5-mini')
    monkeypatch.setenv('OPENAI_COST_PER_1K', '0.0009')
    config = importlib.reload(importlib.import_module('cfb_bot.config'))
    try:
        assert config.OPENAI_MODEL == 'gpt-5-mini'
        assert config.OPENAI_COST_PER_1K == 0.0009
    finally:
        monkeypatch.undo()
        importlib.reload(config)


def test_assistant_prices_calls_with_the_configured_rates():
    from cfb_bot.ai.ai_integration import AICharterAssistant

    assistant = AICharterAssistant()
    assert assistant.openai_cost_per_1k == OPENAI_COST_PER_1K
    assert assistant.anthropic_cost_per_1k == ANTHROPIC_COST_PER_1K
