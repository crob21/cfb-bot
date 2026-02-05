#!/usr/bin/env python3
"""
Unit tests for monitoring modules

Tests Sentry integration and performance metrics
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


class TestSentryIntegration:
    """Test suite for Sentry integration"""

    @patch('src.cfb_bot.monitoring.sentry_integration.os.getenv')
    def test_init_sentry_no_dsn(self, mock_getenv):
        """Test Sentry initialization without DSN"""
        from src.cfb_bot.monitoring.sentry_integration import init_sentry

        mock_getenv.return_value = None

        result = init_sentry()

        assert result is False

    @patch('src.cfb_bot.monitoring.sentry_integration.os.getenv')
    def test_init_sentry_success(self, mock_getenv):
        """Test successful Sentry initialization.
        sentry_sdk is imported inside init_sentry(), so we patch sys.modules
        so that import gets our mock."""
        import sys
        mock_sentry = MagicMock()
        mock_sentry.init = MagicMock()
        mock_sentry.integrations.logging.LoggingIntegration = MagicMock()
        mock_sentry.integrations.aiohttp.AioHttpIntegration = MagicMock()

        mock_getenv.side_effect = lambda key, default=None: {
            'SENTRY_DSN': 'https://test@sentry.io/123',
            'ENVIRONMENT': 'test',
            'SENTRY_TRACES_SAMPLE_RATE': '0.1'
        }.get(key, default)

        with patch.dict(sys.modules, {'sentry_sdk': mock_sentry}):
            from src.cfb_bot.monitoring.sentry_integration import init_sentry
            result = init_sentry()

        assert result is True
        mock_sentry.init.assert_called_once()

    @patch('src.cfb_bot.monitoring.sentry_integration._sentry_enabled', True)
    @patch('src.cfb_bot.monitoring.sentry_integration._sentry_sdk')
    def test_capture_exception(self, mock_sentry):
        """Test capturing exception"""
        from src.cfb_bot.monitoring.sentry_integration import capture_exception

        test_exception = ValueError("Test error")
        capture_exception(test_exception)

        mock_sentry.capture_exception.assert_called_once_with(test_exception)

    @patch('src.cfb_bot.monitoring.sentry_integration._sentry_enabled', True)
    @patch('src.cfb_bot.monitoring.sentry_integration._sentry_sdk')
    def test_capture_exception_with_context(self, mock_sentry):
        """Test capturing exception with context"""
        from src.cfb_bot.monitoring.sentry_integration import capture_exception

        test_exception = ValueError("Test error")
        context = {'command': 'test', 'user': '123'}

        capture_exception(test_exception, context=context)

        mock_sentry.push_scope.assert_called_once()

    @patch('src.cfb_bot.monitoring.sentry_integration._sentry_enabled', True)
    @patch('src.cfb_bot.monitoring.sentry_integration._sentry_sdk')
    def test_set_user_context(self, mock_sentry):
        """Test setting user context"""
        from src.cfb_bot.monitoring.sentry_integration import set_user_context

        set_user_context("123", "testuser")

        mock_sentry.set_user.assert_called_once_with({
            "id": "123",
            "username": "testuser"
        })

    @patch('src.cfb_bot.monitoring.sentry_integration._sentry_enabled', False)
    def test_capture_exception_disabled(self):
        """Test capture_exception when Sentry is disabled"""
        from src.cfb_bot.monitoring.sentry_integration import capture_exception

        # Should not raise error when disabled
        test_exception = ValueError("Test error")
        capture_exception(test_exception)


# Import asyncio for async tests
import asyncio
