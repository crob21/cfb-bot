#!/usr/bin/env python3
"""
Input validation utilities for Discord commands

Prevents issues from malicious or overly-long inputs:
- Length limits
- Type validation
- Safe string handling
"""

from ..security import MAX_INPUT_LENGTH



def sanitize_string(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Sanitize a string input

    Args:
        text: Input text
        max_length: Maximum allowed length

    Returns:
        Sanitized string
    """
    if not isinstance(text, str):
        text = str(text)

    # Remove null bytes
    text = text.replace('\x00', '')

    # Trim whitespace
    text = text.strip()

    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]

    return text
