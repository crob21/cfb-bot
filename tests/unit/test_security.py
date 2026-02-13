#!/usr/bin/env python3
"""Unit tests for security module (sanitize_ai_response, etc.)."""

import pytest

from cfb_bot.security import sanitize_ai_response


class TestSanitizeAiResponse:
    """Test that AI responses are sanitized so keys/secrets never reach users."""

    def test_passes_through_normal_text(self):
        """Normal text is unchanged."""
        text = "Nebraska plays Texas this week. Get your games done!"
        assert sanitize_ai_response(text) == text

    def test_redacts_openai_style_key(self):
        """OpenAI-style sk- keys are redacted."""
        text = "Here is the key: sk-abc123def456ghi789jkl012mno345pqr"
        out = sanitize_ai_response(text)
        assert "sk-" not in out or out == "[REDACTED]"
        assert "abc123" not in out

    def test_redacts_sk_proj_style(self):
        """sk-proj- keys are redacted."""
        text = "Use sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        out = sanitize_ai_response(text)
        assert "sk-proj-" not in out or "[REDACTED]" in out

    def test_redacts_long_token_like_strings(self):
        """Long alphanumeric token-like strings (50+ chars) are redacted."""
        text = "Token: " + "a" * 55 + " end"
        out = sanitize_ai_response(text)
        assert "a" * 55 not in out
        assert "[REDACTED]" in out

    def test_does_not_redact_short_strings(self):
        """Short strings are not redacted (avoid false positives)."""
        text = "Team name: NebraskaCornhuskers2026"
        assert sanitize_ai_response(text) == text

    def test_handles_empty_and_none(self):
        """Empty and None are handled safely."""
        assert sanitize_ai_response("") == ""
        assert sanitize_ai_response(None) is None
