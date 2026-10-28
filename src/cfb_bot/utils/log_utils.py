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
from typing import Any

from ..security import LOG_MESSAGE_TRUNCATE, REDACT_PATTERNS


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
