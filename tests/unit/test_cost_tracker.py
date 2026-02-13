#!/usr/bin/env python3
"""Unit tests for cost_tracker (set_monthly_costs, is_zyte_over_limit)."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime


@pytest.fixture
def mock_storage():
    """Storage that returns/saves in memory for current month."""
    data = {}

    async def load(namespace, key):
        return data.get(key)

    async def save(namespace, key, value):
        data[key] = value

    storage = MagicMock()
    storage.load = AsyncMock(side_effect=load)
    storage.save = AsyncMock(side_effect=save)
    return storage


@pytest.mark.asyncio
async def test_set_monthly_costs_overwrites(mock_storage):
    """set_monthly_costs overwrites current month AI and Zyte cost."""
    with patch("cfb_bot.utils.cost_tracker.get_storage", return_value=mock_storage):
        from cfb_bot.utils.cost_tracker import CostTracker

        tracker = CostTracker()

        result = await tracker.set_monthly_costs(ai_cost=1.5, zyte_cost=0.25)
        assert result["ai"] == 1.5
        assert result["zyte"] == 0.25
        assert result["total"] == 1.75

        costs = await tracker.get_monthly_costs()
        assert costs["ai"] == 1.5
        assert costs["zyte"] == 0.25


@pytest.mark.asyncio
async def test_is_zyte_over_limit_false_when_under(mock_storage):
    """is_zyte_over_limit returns False when under limit."""
    with patch("cfb_bot.utils.cost_tracker.get_storage", return_value=mock_storage):
        from cfb_bot.utils.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.zyte_spend_limit = 20.0

        await tracker.set_monthly_costs(zyte_cost=5.0)
        assert await tracker.is_zyte_over_limit() is False


@pytest.mark.asyncio
async def test_is_zyte_over_limit_true_when_at_or_over(mock_storage):
    """is_zyte_over_limit returns True when at or over limit."""
    with patch("cfb_bot.utils.cost_tracker.get_storage", return_value=mock_storage):
        from cfb_bot.utils.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.zyte_spend_limit = 20.0

        await tracker.set_monthly_costs(zyte_cost=20.0)
        assert await tracker.is_zyte_over_limit() is True

        await tracker.set_monthly_costs(zyte_cost=25.0)
        assert await tracker.is_zyte_over_limit() is True


@pytest.mark.asyncio
async def test_is_zyte_over_limit_zero_disabled(mock_storage):
    """When zyte_spend_limit is 0, is_zyte_over_limit is always False."""
    with patch("cfb_bot.utils.cost_tracker.get_storage", return_value=mock_storage):
        from cfb_bot.utils.cost_tracker import CostTracker

        tracker = CostTracker()
        tracker.zyte_spend_limit = 0

        await tracker.set_monthly_costs(zyte_cost=100.0)
        assert await tracker.is_zyte_over_limit() is False
