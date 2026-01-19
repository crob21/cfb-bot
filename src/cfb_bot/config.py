#!/usr/bin/env python3
"""
Configuration constants for CFB 26 League Bot

Contains colors, footers, and shared constants used across all cogs.
"""

import os
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception:
    pass  # Ignore errors loading .env (e.g. permission denied in tests)

# =============================================================================
# Bot Configuration
# =============================================================================

# Discord token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

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
    LEAGUE = "Harry - Your CFB 26 League Assistant 🏈"
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
