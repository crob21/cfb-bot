"""
CFB Bot (Harry) - Comprehensive Discord bot for College Football dynasty leagues

Provides player lookups, recruiting data, high school stats, AI insights, league management,
and interactive charter editing with Harry's signature cockney personality.

Architecture: Cog-based modular design (v3.0)
"""

__version__ = "3.7.0"

# Import the main bot function
# v3.0: Now using cog-based architecture (bot_main.py)
# Original monolithic bot.py is kept as fallback reference
from .bot_main import run as main

__all__ = ["main"]
