#!/usr/bin/env python3
"""
Configuration constants for CFB League Bot

Contains colors, footers, and shared constants used across all cogs.
"""

import logging
import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Bot Configuration
# =============================================================================

def env_str(name: str, default: str) -> str:
    """
    Environment variable as a string, treating blank as unset.

    Hosts like Render keep a variable you added but left empty, and os.getenv then
    returns '' instead of the default — which once left Harry asking for a model
    named empty string.
    """
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


def env_float(name: str, default: float) -> float:
    """Environment variable as a float, falling back on blank or unparseable values."""
    value = os.getenv(name)
    if not value or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        logging.getLogger('CFBBot.Config').warning(
            f"{name}={value!r} is not a number - using {default}"
        )
        return default


# Discord token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# The game the league plays. Everything Harry says or prompts with reads this, so a new
# season's game is a GAME_NAME env change on the host — no code change needed.
GAME_NAME = env_str('GAME_NAME', 'CFB 27')

# AI models. Both are env-configurable so a model swap is a host setting, not a code
# change. OpenAI is tried first, Anthropic is the fallback (see ai/ai_integration.py).
OPENAI_MODEL = env_str('OPENAI_MODEL', 'gpt-5-mini')
ANTHROPIC_MODEL = env_str('ANTHROPIC_MODEL', 'claude-haiku-4-5')

# Rough blended $/1k tokens for each model, used by /admin ai and /admin budget.
# Update alongside the model, or override on the host if pricing changes.
OPENAI_COST_PER_1K = env_float('OPENAI_COST_PER_1K', 0.0009)
ANTHROPIC_COST_PER_1K = env_float('ANTHROPIC_COST_PER_1K', 0.002)

# Admin channel for notifications
ADMIN_CHANNEL_ID = 1417663211292852244

# Bot intents configuration
BOT_PREFIX = "!"  # Not used but kept for compatibility


# =============================================================================
# Discord Embed Colors
# =============================================================================

class Colors:
    """Discord embed colors for consistent theming"""
    PRIMARY = 0x1e90ff    # Dodger blue - main bot color
    SUCCESS = 0x00ff00    # Green - success messages
    ERROR = 0xff0000      # Red - error messages
    WARNING = 0xffa500    # Orange - warnings
    ADMIN = 0xffaa00      # Golden - admin logs
    HS_STATS = 0x2ecc71   # Emerald - HS stats module
    RECRUITING = 0xffd700 # Gold - recruiting module


# =============================================================================
# Standard Footer Texts
# =============================================================================

class Footers:
    """Standard footer texts for embeds"""
    CFB_DATA = "Harry's CFB Data 🏈 | Data from CollegeFootballData.com"
    PLAYER_LOOKUP = "Harry's Player Lookup 🏈 | Data from CollegeFootballData.com"
    HS_STATS = "Harry's HS Stats 🏈 | Data scraped from MaxPreps"
    CONFIG = "Harry's Server Config 🏈"
    RECRUITING = "Harry's Recruiting 🏈"
    PORTAL = "Harry's Portal Tracker 🔄"
    # League-specific footer (only when LEAGUE module enabled)
    LEAGUE = f"Harry - Your {GAME_NAME} League Assistant 🏈"
    # Generic footer (when LEAGUE module disabled)
    DEFAULT = "Harry - Your CFB Assistant 🏈"


# =============================================================================
# Emojis used throughout the bot
# =============================================================================

class Emojis:
    """Commonly used emojis"""
    CHECKMARK = "✅"
    CROSS = "❌"
    WARNING = "⚠️"
    STAR = "⭐"
    FOOTBALL = "🏈"
    TROPHY = "🏆"
    TIMER = "⏰"
    CALENDAR = "📅"
    CHART = "📊"
    SCHOOL = "🏫"
    TRANSFER = "🔄"
