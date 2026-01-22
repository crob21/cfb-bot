#!/usr/bin/env python3
"""
Error tracking integration with Sentry

Provides centralized error tracking and monitoring:
- Automatic exception capture
- Performance monitoring
- Release tracking
- User context
"""

import logging
import os
from typing import Optional

logger = logging.getLogger('CFB26Bot.Sentry')

# Global Sentry client
_sentry_sdk = None
_sentry_enabled = False


def init_sentry():
    """Initialize Sentry error tracking"""
    global _sentry_sdk, _sentry_enabled
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        logger.info("ℹ️ Sentry DSN not configured - error tracking disabled")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.aiohttp import AioHttpIntegration
        
        # Get version info
        try:
            from ..utils.version_manager import VersionManager
            version_mgr = VersionManager()
            release_version = version_mgr.get_current_version()
        except Exception:
            release_version = "unknown"
        
        # Configure logging integration
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=os.getenv('ENVIRONMENT', 'production'),
            release=f"cfb-rules-bot@{release_version}",
            
            # Integrations
            integrations=[
                logging_integration,
                AioHttpIntegration(),
            ],
            
            # Performance monitoring
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),  # 10% of transactions
            
            # Error sampling
            sample_rate=1.0,  # Capture all errors
            
            # Additional options
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send PII by default
        )
        
        _sentry_sdk = sentry_sdk
        _sentry_enabled = True
        
        logger.info(f"✅ Sentry initialized (release: {release_version})")
        return True
        
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed - run: pip install sentry-sdk")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {e}")
        return False


def capture_exception(exception: Exception, context: dict = None):
    """
    Capture an exception in Sentry
    
    Args:
        exception: The exception to capture
        context: Additional context dict
    """
    if not _sentry_enabled or not _sentry_sdk:
        return
    
    try:
        if context:
            with _sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                _sentry_sdk.capture_exception(exception)
        else:
            _sentry_sdk.capture_exception(exception)
    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {e}")


def capture_message(message: str, level: str = "info", context: dict = None):
    """
    Capture a message in Sentry
    
    Args:
        message: Message to capture
        level: Message level (debug, info, warning, error, fatal)
        context: Additional context dict
    """
    if not _sentry_enabled or not _sentry_sdk:
        return
    
    try:
        if context:
            with _sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_context(key, value)
                _sentry_sdk.capture_message(message, level=level)
        else:
            _sentry_sdk.capture_message(message, level=level)
    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {e}")


def set_user_context(user_id: str, username: str = None):
    """
    Set user context for Sentry events
    
    Args:
        user_id: Discord user ID
        username: Discord username (optional)
    """
    if not _sentry_enabled or not _sentry_sdk:
        return
    
    try:
        _sentry_sdk.set_user({
            "id": user_id,
            "username": username
        })
    except Exception as e:
        logger.error(f"Failed to set user context: {e}")


def set_tag(key: str, value: str):
    """
    Set a tag for Sentry events
    
    Args:
        key: Tag key
        value: Tag value
    """
    if not _sentry_enabled or not _sentry_sdk:
        return
    
    try:
        _sentry_sdk.set_tag(key, value)
    except Exception as e:
        logger.error(f"Failed to set tag: {e}")


def start_transaction(name: str, op: str = "function") -> Optional[object]:
    """
    Start a performance transaction
    
    Args:
        name: Transaction name
        op: Operation type
    
    Returns:
        Transaction object (use with 'with' statement)
    """
    if not _sentry_enabled or not _sentry_sdk:
        return None
    
    try:
        return _sentry_sdk.start_transaction(name=name, op=op)
    except Exception as e:
        logger.error(f"Failed to start transaction: {e}")
        return None


# Example usage:
#
# from .monitoring.sentry_integration import init_sentry, capture_exception, start_transaction
#
# # At bot startup:
# init_sentry()
#
# # In command handlers:
# try:
#     # ... command logic ...
# except Exception as e:
#     capture_exception(e, context={'command': 'player', 'user': str(interaction.user)})
#     raise
#
# # For performance monitoring:
# with start_transaction(name="/cfb player", op="command"):
#     # ... command logic ...
