#!/usr/bin/env python3
"""
AI_SPEND_LIMIT: past it, Harry makes no AI calls for the rest of the month, and the owner
hears about it once.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.ai.ai_integration import AICharterAssistant


def _assistant():
    with patch('cfb_bot.ai.ai_integration.get_storage'):
        return AICharterAssistant()


@pytest.mark.asyncio
async def test_no_ai_calls_past_the_limit_and_the_owner_is_told_once():
    ai = _assistant()
    tracker = MagicMock(is_ai_over_limit=AsyncMock(return_value=True), ai_spend_limit=10.0)
    reporter = MagicMock(send_notice=AsyncMock())
    with patch('cfb_bot.utils.cost_tracker.get_cost_tracker', return_value=tracker), \
         patch('cfb_bot.utils.error_reporter.get_error_reporter', return_value=reporter), \
         patch('cfb_bot.ai.ai_integration.aiohttp.ClientSession') as session:
        assert await ai._post('OpenAI', 'https://example', {}, {}) is None
        assert await ai._post('Anthropic', 'https://example', {}, {}) is None
    session.assert_not_called()
    reporter.send_notice.assert_awaited_once()
    assert "AI_SPEND_LIMIT" in reporter.send_notice.call_args.args[1]


@pytest.mark.asyncio
async def test_under_the_limit_calls_go_through():
    ai = _assistant()
    tracker = MagicMock(is_ai_over_limit=AsyncMock(return_value=False))
    with patch('cfb_bot.utils.cost_tracker.get_cost_tracker', return_value=tracker):
        assert await ai._over_spend_limit() is False


@pytest.mark.asyncio
async def test_a_broken_limit_check_doesnt_turn_ai_off():
    ai = _assistant()
    with patch('cfb_bot.utils.cost_tracker.get_cost_tracker', side_effect=RuntimeError("storage down")):
        assert await ai._over_spend_limit() is False
