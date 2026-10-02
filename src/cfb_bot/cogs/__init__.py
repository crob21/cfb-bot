"""
Cogs module for CFB League Bot

Discord.py Cogs are modular extensions that group related commands together.
Each cog can be loaded/unloaded independently using bot.load_extension().

Available cogs:
- HSStatsCog: High school stats from MaxPreps (/hs group)
- CFBDataCog: College football data (/cfb group)
- RecruitingCog: Recruiting data (/recruiting group)
- CharterCog: League charter management (/charter group)
- LeagueCog: League management (/league group)
- AdminCog: Admin commands (/admin group)
- AIChatCog: AI-powered chat commands (/harry, /ask, /summarize)
- CoreCog: Always-available core commands (/help, /version, etc.)

Note: Cogs are loaded dynamically by bot_main.py using bot.load_extension().
      We don't import them here to avoid cascading import errors.
"""

# No imports - cogs are loaded dynamically via bot.load_extension()
__all__ = []
