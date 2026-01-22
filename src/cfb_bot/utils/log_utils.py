#!/usr/bin/env python3
"""
Logging utilities with security sanitization

Prevents sensitive data from appearing in logs:
- Truncates long messages
- Redacts URLs
- Redacts email addresses
- Redacts API keys/tokens/passwords
"""

import re
import logging
from typing import Any

from .security import LOG_MESSAGE_TRUNCATE, REDACT_PATTERNS


def sanitize_for_log(message: Any) -> str:
    """
    Sanitize a message for logging
    
    Args:
        message: Message to sanitize (any type)
    
    Returns:
        Sanitized string safe for logging
    """
    # Convert to string
    if not isinstance(message, str):
        message = str(message)
    
    # Truncate if too long
    if len(message) > LOG_MESSAGE_TRUNCATE:
        message = message[:LOG_MESSAGE_TRUNCATE] + "... (truncated)"
    
    # Redact sensitive patterns
    for pattern in REDACT_PATTERNS:
        message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
    
    return message


def safe_log_message(logger: logging.Logger, level: int, prefix: str, message: Any, **kwargs):
    """
    Log a message with automatic sanitization
    
    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.DEBUG, etc.)
        prefix: Prefix for the log message
        message: Message to log
        **kwargs: Additional log formatting kwargs
    """
    sanitized = sanitize_for_log(message)
    logger.log(level, f"{prefix}{sanitized}", **kwargs)


def safe_log_user_input(logger: logging.Logger, user: str, content: str):
    """
    Safely log user input with sanitization
    
    Args:
        logger: Logger instance
        user: Username
        content: User input content
    """
    sanitized_content = sanitize_for_log(content)
    logger.info(f"📨 User input from {user}: {sanitized_content}")


def safe_log_api_response(logger: logging.Logger, api_name: str, response: Any):
    """
    Safely log API responses with sanitization
    
    Args:
        logger: Logger instance
        api_name: Name of the API
        response: Response content
    """
    sanitized_response = sanitize_for_log(response)
    logger.debug(f"📡 {api_name} response: {sanitized_response}")


def redact_api_key(key: str) -> str:
    """
    Redact an API key for logging
    
    Args:
        key: API key to redact
    
    Returns:
        Redacted key showing only first/last 4 characters
    """
    if not key or len(key) < 8:
        return "[REDACTED]"
    
    return f"{key[:4]}...{key[-4:]}"


# Example usage:
# from .log_utils import sanitize_for_log, safe_log_user_input
#
# logger.info(f"Message: {sanitize_for_log(user_message)}")
# safe_log_user_input(logger, user.name, message.content)
