#!/usr/bin/env python3
"""
Simple caching system for expensive API calls
"""

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

logger = logging.getLogger('CFB26Bot.Cache')


class SimpleCache:
    """In-memory cache with TTL support"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'saves': 0
        }

    def get(self, key: str, namespace: str = 'default') -> Optional[Any]:
        """Get value from cache if not expired"""
        cache_key = f"{namespace}:{key}"

        if cache_key in self._cache:
            entry = self._cache[cache_key]

            # Check if expired
            if datetime.now() < entry['expires_at']:
                self._stats['hits'] += 1
                logger.debug(f"Cache HIT: {cache_key}")
                return entry['value']
            else:
                # Expired, remove it
                del self._cache[cache_key]
                self._stats['evictions'] += 1
                logger.debug(f"Cache EXPIRED: {cache_key}")

        self._stats['misses'] += 1
        logger.debug(f"Cache MISS: {cache_key}")
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600, namespace: str = 'default'):
        """Set value in cache with TTL"""
        cache_key = f"{namespace}:{key}"

        self._cache[cache_key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl_seconds),
            'created_at': datetime.now()
        }

        self._stats['saves'] += 1
        logger.debug(f"Cache SET: {cache_key} (TTL: {ttl_seconds}s)")

    def delete(self, key: str, namespace: str = 'default'):
        """Delete value from cache"""
        cache_key = f"{namespace}:{key}"

        if cache_key in self._cache:
            del self._cache[cache_key]
            logger.debug(f"Cache DELETE: {cache_key}")

    def clear(self, namespace: Optional[str] = None):
        """Clear cache for a namespace or all cache"""
        if namespace:
            # Clear specific namespace
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(f"{namespace}:")]
            for key in keys_to_delete:
                del self._cache[key]
            logger.info(f"Cache cleared for namespace: {namespace} ({len(keys_to_delete)} entries)")
        else:
            # Clear all
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared completely ({count} entries)")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._stats['hits'] + self._stats['misses']
        hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            **self._stats,
            'total_requests': total_requests,
            'hit_rate': hit_rate,
            'cache_size': len(self._cache),
            'namespaces': self._get_namespace_stats()
        }

    def _get_namespace_stats(self) -> Dict[str, int]:
        """Get count of entries per namespace"""
        namespaces: Dict[str, int] = {}

        for key in self._cache.keys():
            namespace = key.split(':', 1)[0]
            namespaces[namespace] = namespaces.get(namespace, 0) + 1

        return namespaces

    def cleanup_expired(self):
        """Remove all expired entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self._cache.items()
            if now >= entry['expires_at']
        ]

        for key in expired_keys:
            del self._cache[key]
            self._stats['evictions'] += 1

        if expired_keys:
            logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")

        return len(expired_keys)


# Global cache instance
_cache_instance: Optional[SimpleCache] = None


def get_cache() -> SimpleCache:
    """Get the global cache instance"""
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = SimpleCache()
        logger.info("📦 Cache initialized")

    return _cache_instance

