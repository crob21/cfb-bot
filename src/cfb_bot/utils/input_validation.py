#!/usr/bin/env python3
"""
Input validation utilities for Discord commands

Prevents issues from malicious or overly-long inputs:
- Length limits
- Type validation
- Safe string handling
"""

from functools import wraps
from typing import Any, Callable
import discord

from .security import MAX_INPUT_LENGTH


def validate_input_length(max_length: int = MAX_INPUT_LENGTH):
    """
    Decorator to validate string input length for Discord commands
    
    Args:
        max_length: Maximum allowed length (default: MAX_INPUT_LENGTH from security.py)
    
    Usage:
        @validate_input_length()
        async def my_command(self, interaction, query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the interaction object
            interaction = None
            for arg in args:
                if isinstance(arg, discord.Interaction):
                    interaction = arg
                    break
            
            if not interaction:
                # If no interaction found, just run the function
                return await func(*args, **kwargs)
            
            # Check all string kwargs for length
            for key, value in kwargs.items():
                if isinstance(value, str) and len(value) > max_length:
                    await interaction.response.send_message(
                        f"❌ Input too long! '{key}' must be under {max_length} characters. "
                        f"(You provided {len(value)} characters)",
                        ephemeral=True
                    )
                    return
            
            # All inputs valid, run the command
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


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


def is_safe_integer(value: Any, min_val: int = None, max_val: int = None) -> bool:
    """
    Check if a value is a safe integer within bounds
    
    Args:
        value: Value to check
        min_val: Minimum allowed value (optional)
        max_val: Maximum allowed value (optional)
    
    Returns:
        True if value is a safe integer within bounds
    """
    try:
        int_val = int(value)
        
        if min_val is not None and int_val < min_val:
            return False
        
        if max_val is not None and int_val > max_val:
            return False
        
        return True
    except (ValueError, TypeError):
        return False


def validate_discord_mention(mention: str) -> bool:
    """
    Validate that a string is a proper Discord mention
    
    Args:
        mention: String to validate
    
    Returns:
        True if valid Discord mention format
    """
    import re
    # Discord mentions: <@123456789> or <@!123456789>
    pattern = r'^<@!?\d+>$'
    return bool(re.match(pattern, mention))


# Example usage in commands:
#
# from .utils.input_validation import validate_input_length, sanitize_string
#
# @app_commands.command(name="ask")
# @validate_input_length(max_length=500)
# async def ask(self, interaction: discord.Interaction, question: str):
#     question = sanitize_string(question)
#     ...
