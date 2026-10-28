#!/usr/bin/env python3
"""
Every module imports.

Several modules are imported lazily inside error handlers, so a broken import there
only fires when something else has already gone wrong, and a broad except hides it.
utils/log_utils.py imported `.security` (which doesn't exist) for its whole life, so
OpenAI/Anthropic error bodies were never logged.
"""

import importlib
import pkgutil

import pytest

import cfb_bot

MODULES = [m.name for m in pkgutil.walk_packages(cfb_bot.__path__, 'cfb_bot.')]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)
