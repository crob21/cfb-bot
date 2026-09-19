#!/usr/bin/env python3
"""
Unit tests for monitoring modules

Tests performance metrics
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.cfb_bot.monitoring.performance_metrics import (PerformanceMetrics,
                                                        get_metrics,
                                                        track_performance)


class TestPerformanceMetrics:
    """Test suite for PerformanceMetrics class"""

    def test_init(self):
        """Test metrics initialization"""
        metrics = PerformanceMetrics()
        assert metrics._command_times == {}
        assert metrics._command_counts == {}
        assert metrics._error_counts == {}
        assert metrics._cache_hits == 0
        assert metrics._cache_misses == 0

    def test_record_command(self):
        """Test recording command execution"""
        metrics = PerformanceMetrics()

        metrics.record_command("test_cmd", 1.5)
        metrics.record_command("test_cmd", 2.0)

        assert metrics._command_counts["test_cmd"] == 2
        assert len(metrics._command_times["test_cmd"]) == 2
        assert metrics._command_times["test_cmd"] == [1.5, 2.0]

    def test_record_error(self):
        """Test recording command errors"""
        metrics = PerformanceMetrics()

        metrics.record_error("test_cmd")
        metrics.record_error("test_cmd")

        assert metrics._error_counts["test_cmd"] == 2

    def test_record_cache_operations(self):
        """Test recording cache hits/misses"""
        metrics = PerformanceMetrics()

        metrics.record_cache_hit()
        metrics.record_cache_hit()
        metrics.record_cache_miss()

        assert metrics._cache_hits == 2
        assert metrics._cache_misses == 1

    def test_get_command_stats(self):
        """Test getting stats for a specific command"""
        metrics = PerformanceMetrics()

        metrics.record_command("test_cmd", 1.0)
        metrics.record_command("test_cmd", 2.0)
        metrics.record_command("test_cmd", 3.0)
        metrics.record_error("test_cmd")

        stats = metrics.get_command_stats("test_cmd")

        assert stats is not None
        assert stats['count'] == 3
        assert stats['avg_time'] == 2.0
        assert stats['min_time'] == 1.0
        assert stats['max_time'] == 3.0
        assert stats['error_count'] == 1
        assert abs(stats['error_rate'] - 0.333) < 0.01

    def test_get_command_stats_nonexistent(self):
        """Test getting stats for non-existent command"""
        metrics = PerformanceMetrics()

        stats = metrics.get_command_stats("nonexistent")

        assert stats is None

    def test_get_all_stats(self):
        """Test getting all stats"""
        metrics = PerformanceMetrics()

        metrics.record_command("cmd1", 1.0)
        metrics.record_command("cmd2", 2.0)
        metrics.record_cache_hit()
        metrics.record_cache_miss()

        stats = metrics.get_all_stats()

        assert 'uptime_seconds' in stats
        assert stats['total_commands'] == 2
        assert stats['total_errors'] == 0
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 1
        assert stats['cache_hit_rate'] == 0.5
        assert 'commands' in stats
        assert 'cmd1' in stats['commands']
        assert 'cmd2' in stats['commands']

    def test_get_slowest_commands(self):
        """Test getting slowest commands"""
        metrics = PerformanceMetrics()

        metrics.record_command("fast_cmd", 0.5)
        metrics.record_command("medium_cmd", 2.0)
        metrics.record_command("slow_cmd", 5.0)

        slowest = metrics.get_slowest_commands(limit=2)

        assert len(slowest) == 2
        assert slowest[0][0] == "slow_cmd"
        assert slowest[0][1] == 5.0
        assert slowest[1][0] == "medium_cmd"
        assert slowest[1][1] == 2.0

    def test_slow_command_warning(self, caplog):
        """Test that slow commands trigger warnings"""
        import logging

        metrics = PerformanceMetrics()

        with caplog.at_level(logging.WARNING):
            metrics.record_command("slow_cmd", 6.0)

        assert "Slow command" in caplog.text
        assert "slow_cmd" in caplog.text
        assert "6.00s" in caplog.text

    def test_cache_hit_rate_zero_division(self):
        """Test cache hit rate with no cache operations"""
        metrics = PerformanceMetrics()

        stats = metrics.get_all_stats()

        assert stats['cache_hit_rate'] == 0


@pytest.mark.asyncio
class TestTrackPerformanceDecorator:
    """Test suite for track_performance decorator"""

    async def test_track_performance_success(self):
        """Test decorator tracks successful command"""
        metrics = PerformanceMetrics()

        @track_performance("test_command")
        async def dummy_command():
            await asyncio.sleep(0.1)
            return "success"

        # Patch the global metrics instance
        with patch('src.cfb_bot.monitoring.performance_metrics._metrics', metrics):
            result = await dummy_command()

        assert result == "success"
        assert metrics._command_counts["test_command"] == 1
        assert len(metrics._command_times["test_command"]) == 1
        assert metrics._command_times["test_command"][0] >= 0.1

    async def test_track_performance_error(self):
        """Test decorator tracks errors"""
        metrics = PerformanceMetrics()

        @track_performance("test_command")
        async def failing_command():
            raise ValueError("Test error")

        # Patch the global metrics instance
        with patch('src.cfb_bot.monitoring.performance_metrics._metrics', metrics):
            with pytest.raises(ValueError):
                await failing_command()

        assert metrics._command_counts["test_command"] == 1
        assert metrics._error_counts["test_command"] == 1

    async def test_track_performance_auto_name(self):
        """Test decorator auto-detects function name"""
        metrics = PerformanceMetrics()

        @track_performance()
        async def my_function():
            return "done"

        with patch('src.cfb_bot.monitoring.performance_metrics._metrics', metrics):
            await my_function()

        assert metrics._command_counts["my_function"] == 1


import asyncio
