#!/usr/bin/env python3
"""
API Retry Logic with Exponential Backoff

Handles transient failures gracefully:
- Network timeouts
- Rate limiting (429)
- Server errors (5xx)
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Optional
import aiohttp

from ..security import API_RETRY_ATTEMPTS, API_RETRY_BACKOFF, HTTP_TIMEOUT

logger = logging.getLogger('CFB26Bot.APIRetry')


class APIRetryError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


def with_retry(
    max_attempts: int = API_RETRY_ATTEMPTS,
    backoff_factor: float = API_RETRY_BACKOFF,
    retry_on: tuple = (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError)
):
    """
    Decorator to add retry logic with exponential backoff to async functions

    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier (delay = backoff_factor ^ attempt)
        retry_on: Tuple of exception types to retry on

    Usage:
        @with_retry(max_attempts=3, backoff_factor=2)
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except retry_on as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(f"❌ {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise APIRetryError(f"Failed after {max_attempts} attempts") from e

                    # Calculate backoff delay: 2^attempt seconds (2s, 4s, 8s...)
                    delay = backoff_factor ** attempt
                    logger.warning(f"⚠️ {func.__name__} attempt {attempt}/{max_attempts} failed: {e}. Retrying in {delay}s...")

                    await asyncio.sleep(delay)

                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(f"❌ {func.__name__} failed with unexpected error: {e}", exc_info=True)
                    raise

            # Should never reach here, but just in case
            raise last_exception

        return wrapper
    return decorator


async def fetch_with_retry(
    url: str,
    method: str = 'GET',
    max_attempts: int = API_RETRY_ATTEMPTS,
    timeout: int = HTTP_TIMEOUT,
    **kwargs
) -> dict:
    """
    Fetch data from an API with automatic retry logic

    Args:
        url: API endpoint URL
        method: HTTP method (GET, POST, etc.)
        max_attempts: Maximum retry attempts
        timeout: Request timeout in seconds
        **kwargs: Additional arguments for aiohttp.ClientSession.request()

    Returns:
        JSON response as dict

    Raises:
        APIRetryError: If all retry attempts fail
    """
    @with_retry(max_attempts=max_attempts)
    async def _fetch():
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.request(method, url, **kwargs) as response:
                # Raise for 4xx/5xx errors
                response.raise_for_status()
                return await response.json()

    return await _fetch()


async def fetch_with_rate_limit_handling(
    url: str,
    method: str = 'GET',
    max_attempts: int = API_RETRY_ATTEMPTS,
    timeout: int = HTTP_TIMEOUT,
    **kwargs
) -> dict:
    """
    Fetch data with automatic rate limit (429) handling

    If a 429 response is received, this will:
    1. Check for 'Retry-After' header
    2. Wait the specified time (or use exponential backoff)
    3. Retry the request

    Args:
        url: API endpoint URL
        method: HTTP method
        max_attempts: Maximum retry attempts
        timeout: Request timeout
        **kwargs: Additional aiohttp arguments

    Returns:
        JSON response as dict
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.request(method, url, **kwargs) as response:

                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = response.headers.get('Retry-After', API_RETRY_BACKOFF ** attempt)
                        retry_after = int(retry_after)

                        if attempt == max_attempts:
                            raise APIRetryError(f"Rate limited after {max_attempts} attempts")

                        logger.warning(f"⏱️ Rate limited. Waiting {retry_after}s before retry {attempt}/{max_attempts}")
                        await asyncio.sleep(retry_after)
                        continue

                    # Raise for other 4xx/5xx errors
                    response.raise_for_status()
                    return await response.json()

        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
            last_exception = e

            if attempt == max_attempts:
                logger.error(f"❌ Request to {url} failed after {max_attempts} attempts: {e}")
                raise APIRetryError(f"Failed after {max_attempts} attempts") from e

            delay = API_RETRY_BACKOFF ** attempt
            logger.warning(f"⚠️ Request failed (attempt {attempt}/{max_attempts}): {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)

    raise last_exception


# Example usage:
#
# from .utils.api_retry import with_retry, fetch_with_retry
#
# @with_retry(max_attempts=3)
# async def get_player_data(player_id):
#     async with aiohttp.ClientSession() as session:
#         async with session.get(f"https://api.example.com/players/{player_id}") as response:
#             return await response.json()
#
# Or use the helper function:
#
# data = await fetch_with_retry("https://api.example.com/players/123")
