"""
Server Configuration Module
Handles per-guild feature flags and settings.

Modules:
- CORE: Always enabled - Harry's personality, general AI chat
- CFB_DATA: Player lookup, rankings, matchups, schedules, draft, transfers, betting, ratings
- LEAGUE: Timer, advance, charter, rules, league staff, pick commish
"""

import json
import logging
from typing import Any, Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger('CFB26Bot.ServerConfig')


class FeatureModule(Enum):
    """Available feature modules"""
    CORE = "core"           # Always on - /admin, /help, /version (can't disable)
    AI_CHAT = "ai_chat"     # Harry's AI chat - /harry, /ask, @mentions, auto-responses
    CFB_DATA = "cfb_data"   # Player lookup, rankings, matchups, etc.
    LEAGUE = "league"       # Timer, charter, rules, league staff
    HS_STATS = "hs_stats"   # High school stats scraping (MaxPreps)
    RECRUITING = "recruiting"  # 247Sports recruiting data (web scraping)
    FUN_GAMES = "fun_games" # Rivalry responses (Fuck Oregon!), team banter


# Recruiting data sources
class RecruitingSource:
    """Available recruiting data sources"""
    ON3 = "on3"          # On3/Rivals (default) - server-side rendered, reliable
    SPORTS247 = "247"    # 247Sports Composite - legacy, more complex scraping


# Default settings for new servers
DEFAULT_CONFIG = {
    "modules": {
        FeatureModule.CORE.value: True,      # Always True, can't disable
        FeatureModule.AI_CHAT.value: True,   # Enabled by default - Harry's personality
        FeatureModule.CFB_DATA.value: True,  # Enabled by default
        FeatureModule.LEAGUE.value: False,   # Disabled by default (opt-in)
        FeatureModule.HS_STATS.value: False, # Disabled by default (opt-in, uses web scraping)
        FeatureModule.RECRUITING.value: False, # Disabled by default (opt-in, uses web scraping)
        FeatureModule.FUN_GAMES.value: True, # Enabled by default - rivalry responses, team banter
    },
    "settings": {
        "timer_channel_id": None,
        "admin_channel_id": None,
        "auto_responses": True,   # Enable automatic jump-in responses (team banter, "Fuck Oregon!", etc.)
        "recruiting_source": RecruitingSource.ON3,  # Default to On3/Rivals
        "schedule_announcement": True,  # Week matchups message when timer starts/advances (optional module)
    },
    # Channel controls - empty means ALL channels allowed
    "enabled_channels": [],  # Whitelist: [channel_id1, channel_id2] - empty = all allowed
    # Per-channel overrides (optional)
    "channel_overrides": {
        # channel_id: {"auto_responses": False, "modules": {"cfb_data": False}}
    }
}


# Harry's core personality - ALWAYS cockney asshole Duck-hater
HARRY_PERSONALITY = """You are Harry, a friendly but completely insane CFB 26 league assistant. You are extremely sarcastic, witty, and have a dark sense of humor. You speak with cockney slang (mate, ya muppet, bloody hell, etc.). You have a deep, unhinged hatred of the Oregon Ducks."""

# Commands and their required modules (v2.0 grouped format)
COMMAND_MODULES = {
    # CFB Data commands (/cfb group)
    "/cfb player": FeatureModule.CFB_DATA,
    "/cfb players": FeatureModule.CFB_DATA,
    "/cfb rankings": FeatureModule.CFB_DATA,
    "/cfb matchup": FeatureModule.CFB_DATA,
    "/cfb schedule": FeatureModule.CFB_DATA,
    "/cfb draft": FeatureModule.CFB_DATA,
    "/cfb transfers": FeatureModule.CFB_DATA,
    "/cfb betting": FeatureModule.CFB_DATA,
    "/cfb ratings": FeatureModule.CFB_DATA,

    # High School Stats commands (/hs group)
    "/hs stats": FeatureModule.HS_STATS,
    "/hs bulk": FeatureModule.HS_STATS,

    # Recruiting commands (/recruiting group)
    "/recruiting player": FeatureModule.RECRUITING,
    "/recruiting top": FeatureModule.RECRUITING,
    "/recruiting class": FeatureModule.RECRUITING,
    "/recruiting commits": FeatureModule.RECRUITING,
    "/recruiting rankings": FeatureModule.RECRUITING,
    "/recruiting source": FeatureModule.RECRUITING,

    # League commands (/league group - includes season & timer)
    "/league staff": FeatureModule.LEAGUE,
    "/league rules": FeatureModule.LEAGUE,
    "/league team": FeatureModule.LEAGUE,
    "/league dynasty": FeatureModule.LEAGUE,
    "/league set_owner": FeatureModule.LEAGUE,
    "/league set_commish": FeatureModule.LEAGUE,
    "/league pick_commish": FeatureModule.LEAGUE,
    # Season commands (merged into /league)
    "/league week": FeatureModule.LEAGUE,
    "/league weeks": FeatureModule.LEAGUE,
    "/league games": FeatureModule.LEAGUE,
    "/league find_game": FeatureModule.LEAGUE,
    "/league byes": FeatureModule.LEAGUE,
    "/league set_week": FeatureModule.LEAGUE,
    # Timer commands (merged into /league)
    "/league timer": FeatureModule.LEAGUE,
    "/league timer_status": FeatureModule.LEAGUE,
    "/league timer_stop": FeatureModule.LEAGUE,
    "/league timer_channel": FeatureModule.LEAGUE,
    "/league nag": FeatureModule.LEAGUE,
    "/league stop_nag": FeatureModule.LEAGUE,

    # Charter commands (/charter group)
    "/charter lookup": FeatureModule.LEAGUE,
    "/charter search": FeatureModule.LEAGUE,
    "/charter link": FeatureModule.LEAGUE,
    "/charter history": FeatureModule.LEAGUE,
    "/charter scan": FeatureModule.LEAGUE,
    "/charter add": FeatureModule.LEAGUE,
    "/charter update": FeatureModule.LEAGUE,
    "/charter sync": FeatureModule.LEAGUE,
    "/charter backups": FeatureModule.LEAGUE,
    "/charter restore": FeatureModule.LEAGUE,

    # Admin commands (/admin group)
    "/admin config": FeatureModule.CORE,
    "/admin channels": FeatureModule.CORE,
    "/admin set_channel": FeatureModule.CORE,
    "/admin add": FeatureModule.CORE,
    "/admin remove": FeatureModule.CORE,
    "/admin list": FeatureModule.CORE,
    "/admin block": FeatureModule.CORE,
    "/admin unblock": FeatureModule.CORE,
    "/admin blocked": FeatureModule.CORE,

    # AI Chat commands (can be disabled)
    "/harry": FeatureModule.AI_CHAT,
    "/ask": FeatureModule.AI_CHAT,
    "/summarize": FeatureModule.AI_CHAT,

    # Core standalone commands (always enabled)
    "/help": FeatureModule.CORE,
    "/whats_new": FeatureModule.CORE,
    "/changelog": FeatureModule.CORE,
    "/version": FeatureModule.CORE,
    "/tokens": FeatureModule.CORE,
}


class ServerConfigManager:
    """Manages per-server configuration and feature flags"""

    def __init__(self):
        self._configs: Dict[int, Dict[str, Any]] = {}
        self._bot = None
        self._loaded = False

    def set_bot(self, bot):
        """Set the bot instance for storage persistence"""
        self._bot = bot
        # Also set on storage backend
        from .storage import set_storage_bot
        set_storage_bot(bot)

    def get_config(self, guild_id: int) -> Dict[str, Any]:
        """Get configuration for a guild, creating default if needed"""
        if guild_id not in self._configs:
            self._configs[guild_id] = json.loads(json.dumps(DEFAULT_CONFIG))

        # AUTOMATIC MIGRATION: Merge in any new modules from DEFAULT_CONFIG
        # This ensures existing servers get new features when we add them
        config = self._configs[guild_id]
        if "modules" not in config:
            config["modules"] = {}

        for module_name, default_enabled in DEFAULT_CONFIG["modules"].items():
            if module_name not in config["modules"]:
                config["modules"][module_name] = default_enabled
                logger.info(f"🆕 Auto-migrated new module '{module_name}' (enabled={default_enabled}) for guild {guild_id}")

        return config

    def is_module_enabled(self, guild_id: int, module: FeatureModule) -> bool:
        """Check if a module is enabled for a guild"""
        # Core is ALWAYS enabled
        if module == FeatureModule.CORE:
            return True

        config = self.get_config(guild_id)
        return config.get("modules", {}).get(module.value, False)

    def is_command_enabled(self, guild_id: int, command_name: str) -> bool:
        """Check if a specific command is enabled for a guild"""
        module = COMMAND_MODULES.get(command_name)
        if module is None:
            # Unknown command, allow by default
            return True
        return self.is_module_enabled(guild_id, module)

    def enable_module(self, guild_id: int, module: FeatureModule) -> bool:
        """Enable a module for a guild"""
        if module == FeatureModule.CORE:
            return True  # Always enabled

        config = self.get_config(guild_id)
        config["modules"][module.value] = True
        logger.info(f"✅ Enabled {module.value} for guild {guild_id}")
        return True

    def disable_module(self, guild_id: int, module: FeatureModule) -> bool:
        """Disable a module for a guild"""
        if module == FeatureModule.CORE:
            logger.warning(f"Cannot disable CORE module")
            return False  # Can't disable core

        config = self.get_config(guild_id)
        config["modules"][module.value] = False
        logger.info(f"❌ Disabled {module.value} for guild {guild_id}")
        return True

    def get_enabled_modules(self, guild_id: int) -> Set[str]:
        """Get set of enabled module names for a guild"""
        config = self.get_config(guild_id)
        enabled = {FeatureModule.CORE.value}  # Core always included
        for module_name, is_enabled in config.get("modules", {}).items():
            if is_enabled:
                enabled.add(module_name)
        return enabled

    def set_setting(self, guild_id: int, key: str, value: Any):
        """Set a guild-specific setting"""
        config = self.get_config(guild_id)
        if "settings" not in config:
            config["settings"] = {}
        config["settings"][key] = value

    def get_setting(self, guild_id: int, key: str, default: Any = None) -> Any:
        """Get a guild-specific setting"""
        config = self.get_config(guild_id)
        return config.get("settings", {}).get(key, default)

    def get_module_commands(self, module: FeatureModule) -> list:
        """Get list of commands belonging to a module"""
        return [cmd for cmd, mod in COMMAND_MODULES.items() if mod == module]

    # ==================== CHANNEL SETTINGS ====================

    def get_admin_channel(self, guild_id: int) -> Optional[int]:
        """Get the admin channel ID for a guild"""
        return self.get_setting(guild_id, "admin_channel_id")

    def set_admin_channel(self, guild_id: int, channel_id: int):
        """Set the admin channel for a guild"""
        self.set_setting(guild_id, "admin_channel_id", channel_id)
        logger.info(f"✅ Set admin channel to {channel_id} for guild {guild_id}")

    def get_timer_channel(self, guild_id: int) -> Optional[int]:
        """Get the timer notification channel ID for a guild"""
        return self.get_setting(guild_id, "timer_channel_id")

    def set_timer_channel(self, guild_id: int, channel_id: int):
        """Set the timer notification channel for a guild"""
        self.set_setting(guild_id, "timer_channel_id", channel_id)
        logger.info(f"✅ Set timer channel to {channel_id} for guild {guild_id}")

    # ==================== RECRUITING SOURCE ====================

    def get_recruiting_source(self, guild_id: int) -> str:
        """Get the recruiting data source for a guild (on3 or 247)"""
        return self.get_setting(guild_id, "recruiting_source", RecruitingSource.ON3)

    def set_recruiting_source(self, guild_id: int, source: str) -> bool:
        """Set the recruiting data source for a guild"""
        if source not in [RecruitingSource.ON3, RecruitingSource.SPORTS247]:
            logger.warning(f"Invalid recruiting source: {source}")
            return False
        self.set_setting(guild_id, "recruiting_source", source)
        logger.info(f"✅ Set recruiting source to {source} for guild {guild_id}")
        return True

    # ==================== STORAGE ====================

    async def save_to_discord(self):
        """Save all configs to storage backend (name kept for backwards compatibility)"""
        from .storage import get_storage

        storage = get_storage()

        # Save all configs as one blob (for Discord DM efficiency)
        # Convert int keys to strings for JSON
        serializable = {str(k): v for k, v in self._configs.items()}

        success = await storage.save("server_config", "all", serializable)
        if success:
            logger.info(f"✅ Saved configs for {len(self._configs)} servers")
        return success

    async def load_from_discord(self):
        """Load configs from storage backend (name kept for backwards compatibility)"""
        if self._loaded:
            return True

        from .storage import get_storage, set_storage_bot

        # Set bot for Discord storage
        if self._bot:
            set_storage_bot(self._bot)

        storage = get_storage()

        try:
            # Try new format first (with "all" key)
            data = await storage.load("server_config", "all")

            if data:
                # New format: {"guild_id": config, ...}
                self._configs = {int(k): v for k, v in data.items()}
                logger.info(f"✅ Loaded configs for {len(self._configs)} servers")
            else:
                # Try loading old format (direct guild configs without "all" wrapper)
                # Old format stored directly as SERVER_CONFIG:{guild_id: config, ...}
                all_data = await storage.load_all("server_config")

                # Check if it's old format (keys are guild IDs, not "all")
                if all_data and "all" not in all_data:
                    # Old format - guild IDs are top-level keys
                    self._configs = {}
                    for k, v in all_data.items():
                        try:
                            guild_id = int(k)
                            self._configs[guild_id] = v
                        except (ValueError, TypeError):
                            continue

                    if self._configs:
                        logger.info(f"✅ Migrated {len(self._configs)} server configs from old format")
                        # Save in new format
                        await self.save_to_discord()
                    else:
                        logger.info("📝 No existing server configs found")
                else:
                    self._configs = {}
                    logger.info("📝 No existing server configs found")

            self._loaded = True
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load configs: {e}")
            return False

    def get_module_description(self, module: FeatureModule) -> str:
        """Get human-readable description of a module"""
        descriptions = {
            FeatureModule.CORE: "🤖 **Core** - `/admin`, `/help`, `/version` (always on)",
            FeatureModule.AI_CHAT: "💬 **AI Chat** - `/harry`, `/ask`, `/summarize`, @mentions, auto-responses",
            FeatureModule.CFB_DATA: "🏈 **CFB Data** - `/cfb` group: player, rankings, matchups, schedules, transfers",
            FeatureModule.LEAGUE: "🏆 **League** - `/league` (staff, season, timer) & `/charter` groups",
            FeatureModule.HS_STATS: "🏫 **HS Stats** - `/hs` group: high school stats from MaxPreps",
            FeatureModule.RECRUITING: "⭐ **Recruiting** - `/recruiting` group: On3/Rivals or 247Sports data",
            FeatureModule.FUN_GAMES: "🎮 **Fun & Games** - Rivalry responses (Fuck Oregon!), team banter",
        }
        return descriptions.get(module, str(module))

    def auto_responses_enabled(self, guild_id: int, channel_id: int = None) -> bool:
        """Check if automatic jump-in responses are enabled (team banter, etc.)"""
        # Check channel override first
        if channel_id:
            override = self.get_channel_override(guild_id, channel_id, "auto_responses")
            if override is not None:
                return override
        return self.get_setting(guild_id, "auto_responses", True)

    def toggle_auto_responses(self, guild_id: int, channel_id: int) -> bool:
        """Toggle automatic jump-in responses for a channel (rivalry mode)

        Returns:
            bool: The new state (True = enabled, False = disabled)
        """
        current = self.auto_responses_enabled(guild_id, channel_id)
        new_value = not current
        self.set_channel_override(guild_id, channel_id, "auto_responses", new_value)
        logger.info(f"{'✅' if new_value else '❌'} Toggled auto_responses for channel {channel_id} in guild {guild_id}: {new_value}")
        return new_value

    def get_personality_prompt(self, guild_id: int) -> str:
        """Get Harry's personality prompt - ALWAYS the full cockney asshole Duck-hater"""
        return HARRY_PERSONALITY

    # ==================== CHANNEL CONTROLS ====================

    def is_channel_enabled(self, guild_id: int, channel_id: int) -> bool:
        """Check if Harry is allowed to respond in this channel"""
        config = self.get_config(guild_id)
        enabled_channels = config.get("enabled_channels", [])

        # Empty list = Harry is DISABLED everywhere (must explicitly enable channels)
        if not enabled_channels:
            return False

        return channel_id in enabled_channels

    def enable_channel(self, guild_id: int, channel_id: int) -> bool:
        """Add a channel to the whitelist"""
        config = self.get_config(guild_id)
        if "enabled_channels" not in config:
            config["enabled_channels"] = []

        if channel_id not in config["enabled_channels"]:
            config["enabled_channels"].append(channel_id)
            logger.info(f"✅ Enabled channel {channel_id} for guild {guild_id}")
        return True

    def disable_channel(self, guild_id: int, channel_id: int) -> bool:
        """Remove a channel from the whitelist"""
        config = self.get_config(guild_id)
        if "enabled_channels" not in config:
            config["enabled_channels"] = []

        if channel_id in config["enabled_channels"]:
            config["enabled_channels"].remove(channel_id)
            logger.info(f"❌ Disabled channel {channel_id} for guild {guild_id}")
        return True

    def get_enabled_channels(self, guild_id: int) -> List[int]:
        """Get list of enabled channels (empty = all allowed)"""
        config = self.get_config(guild_id)
        return config.get("enabled_channels", [])

    def set_channel_override(self, guild_id: int, channel_id: int, key: str, value: Any):
        """Set a per-channel override for a setting"""
        config = self.get_config(guild_id)
        if "channel_overrides" not in config:
            config["channel_overrides"] = {}

        channel_key = str(channel_id)  # JSON keys are strings
        if channel_key not in config["channel_overrides"]:
            config["channel_overrides"][channel_key] = {}

        config["channel_overrides"][channel_key][key] = value
        logger.info(f"⚙️ Set channel {channel_id} override: {key}={value}")

    def get_channel_override(self, guild_id: int, channel_id: int, key: str) -> Any:
        """Get a per-channel override (returns None if not set)"""
        config = self.get_config(guild_id)
        overrides = config.get("channel_overrides", {})
        channel_key = str(channel_id)

        if channel_key in overrides:
            return overrides[channel_key].get(key)
        return None

    def is_module_enabled_for_channel(self, guild_id: int, channel_id: int, module: FeatureModule) -> bool:
        """Check if a module is enabled for a specific channel"""
        # First check if channel is enabled at all
        if not self.is_channel_enabled(guild_id, channel_id):
            return False

        # Core is always enabled
        if module == FeatureModule.CORE:
            return True

        # Check channel-specific override
        override = self.get_channel_override(guild_id, channel_id, f"module_{module.value}")
        if override is not None:
            return override

        # Fall back to server-level setting
        return self.is_module_enabled(guild_id, module)


# Singleton instance
server_config = ServerConfigManager()
