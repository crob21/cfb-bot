#!/usr/bin/env python3
"""
Security constants for CFB Bot (Harry)

Centralized security settings to prevent issues like:
- Hanging requests
- Memory leaks
- Denial of service
"""

import re

# HTTP Request Timeouts (seconds)
HTTP_TIMEOUT = 30  # Default timeout for all HTTP requests

# Input Validation
MAX_INPUT_LENGTH = 2000  # Maximum characters for user input

# Logging Safety
LOG_MESSAGE_TRUNCATE = 100  # Truncate logged messages to this length
REDACT_PATTERNS = [
    r'http[s]?://[^\s]+',  # URLs
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Emails
    r'(?i)(password|token|key|secret)[\s:=]+[\S]+',  # Secrets
]

def sanitize_ai_response(text: str) -> str:
    """Redact any key/token-like content from AI response before sending to users. Call on every AI reply."""
    if not text or not isinstance(text, str):
        return text
    out = text
    # OpenAI / generic API key patterns
    out = re.sub(r'sk-[a-zA-Z0-9_-]{20,}', '[REDACTED]', out)
    out = re.sub(r'sk-proj-[a-zA-Z0-9_-]{20,}', '[REDACTED]', out)
    # Long token-looking strings (50+ alphanumeric/underscore/dash only - likely keys/tokens)
    def replace_long(m):
        s = m.group(0)
        return '[REDACTED]' if len(s) >= 50 and re.match(r'^[A-Za-z0-9_-]+$', s) else s
    out = re.sub(r'[A-Za-z0-9_-]{50,}', replace_long, out)
    return out
