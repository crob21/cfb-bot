#!/usr/bin/env python3
"""
Command performance metrics tracking

Tracks response times and performance for all commands:
- Command execution time
- API call durations
- Cache hit rates
- Error rates
"""

import logging
import time
from collections import defaultdict
from typing import Dict, Optional
from functools import wraps

logger = logging.getLogger('CFB26Bot.Metrics')


class PerformanceMetrics:
    """Track command performance metrics"""
    
    def __init__(self):
        # Command timing (command_name -> list of execution times)
        self._command_times: Dict[str, list] = defaultdict(list)
        
        # Command counts
        self._command_counts: Dict[str, int] = defaultdict(int)
        
        # Error counts
        self._error_counts: Dict[str, int] = defaultdict(int)
        
        # Cache metrics
        self._cache_hits = 0
        self._cache_misses = 0
        
        # Start time
        self._start_time = time.time()
    
    def record_command(self, command_name: str, execution_time: float):
        """
        Record a command execution
        
        Args:
            command_name: Name of the command
            execution_time: Execution time in seconds
        """
        self._command_times[command_name].append(execution_time)
        self._command_counts[command_name] += 1
        
        # Log slow commands (>5s)
        if execution_time > 5.0:
            logger.warning(f"⚠️ Slow command: {command_name} took {execution_time:.2f}s")
    
    def record_error(self, command_name: str):
        """Record a command error"""
        self._error_counts[command_name] += 1
    
    def record_cache_hit(self):
        """Record a cache hit"""
        self._cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        self._cache_misses += 1
    
    def get_command_stats(self, command_name: str) -> Optional[Dict]:
        """
        Get stats for a specific command
        
        Returns:
            Dict with avg_time, count, error_count
        """
        if command_name not in self._command_times:
            return None
        
        times = self._command_times[command_name]
        return {
            'count': self._command_counts[command_name],
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'error_count': self._error_counts.get(command_name, 0),
            'error_rate': self._error_counts.get(command_name, 0) / self._command_counts[command_name]
        }
    
    def get_all_stats(self) -> Dict:
        """Get all performance stats"""
        stats = {
            'uptime_seconds': time.time() - self._start_time,
            'total_commands': sum(self._command_counts.values()),
            'total_errors': sum(self._error_counts.values()),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) if (self._cache_hits + self._cache_misses) > 0 else 0,
            'commands': {}
        }
        
        for command_name in self._command_times.keys():
            stats['commands'][command_name] = self.get_command_stats(command_name)
        
        return stats
    
    def get_slowest_commands(self, limit: int = 5) -> list:
        """Get the slowest commands by average time"""
        command_avgs = []
        for command_name, times in self._command_times.items():
            if times:
                avg = sum(times) / len(times)
                command_avgs.append((command_name, avg, len(times)))
        
        command_avgs.sort(key=lambda x: x[1], reverse=True)
        return command_avgs[:limit]
    
    def log_summary(self):
        """Log a summary of performance metrics"""
        stats = self.get_all_stats()
        
        logger.info(f"📊 Performance Summary:")
        logger.info(f"   Uptime: {stats['uptime_seconds'] / 3600:.1f} hours")
        logger.info(f"   Total commands: {stats['total_commands']}")
        logger.info(f"   Total errors: {stats['total_errors']}")
        logger.info(f"   Cache hit rate: {stats['cache_hit_rate']:.1%}")
        
        slowest = self.get_slowest_commands(3)
        if slowest:
            logger.info(f"   Slowest commands:")
            for cmd, avg, count in slowest:
                logger.info(f"      {cmd}: {avg:.2f}s avg ({count} calls)")


# Global metrics instance
_metrics = PerformanceMetrics()


def get_metrics() -> PerformanceMetrics:
    """Get the global metrics instance"""
    return _metrics


def track_performance(command_name: str = None):
    """
    Decorator to track command performance
    
    Usage:
        @track_performance("player_lookup")
        async def player_command(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Auto-detect command name from function if not provided
            cmd_name = command_name or func.__name__
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                _metrics.record_command(cmd_name, execution_time)
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                _metrics.record_command(cmd_name, execution_time)
                _metrics.record_error(cmd_name)
                raise
        
        return wrapper
    return decorator


# Example usage:
#
# from .monitoring.performance_metrics import track_performance, get_metrics
#
# @app_commands.command(name="player")
# @track_performance("cfb_player")
# async def player(self, interaction, name: str):
#     # ... command logic ...
#
# # Get metrics:
# metrics = get_metrics()
# stats = metrics.get_all_stats()
