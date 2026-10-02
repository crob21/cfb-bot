#!/usr/bin/env python3
"""Log messages are plain text — emoji belong in Discord embeds, not in logs."""

import ast
import pathlib
import unicodedata

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
LOG_METHODS = {'debug', 'info', 'warning', 'warn', 'error', 'exception', 'critical'}


def _has_emoji(text):
    return any(
        (unicodedata.category(ch) == 'So' and ord(ch) > 0x2000) or ch in '️ℹ'
        for ch in text
    )


def test_no_emoji_in_log_messages():
    offenders = []
    for path in SRC.rglob("*.py"):
        source = path.read_text()
        for node in ast.walk(ast.parse(source)):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr in LOG_METHODS and node.args):
                continue
            target = node.func.value
            name = target.id if isinstance(target, ast.Name) else getattr(target, 'attr', '')
            if name in ('logger', 'log', 'logging', '_logger'):
                message = ast.get_source_segment(source, node.args[0]) or ''
                if _has_emoji(message):
                    offenders.append(f"{path.relative_to(SRC)}:{node.lineno}")
    assert not offenders, "Emoji in log messages:\n" + "\n".join(offenders)
