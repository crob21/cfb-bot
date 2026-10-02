"""
Storage Abstraction Layer

Provides a consistent interface for storing bot configuration data.
Currently supports Discord DMs, with easy swapping to database storage later.

Usage:
    from .storage import get_storage
    
    storage = get_storage()  # Returns configured storage backend
    await storage.save("server_config", guild_id, data)
    data = await storage.load("server_config", guild_id)
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# One namespace = one Discord message, and Discord caps a message at 2000 characters
DISCORD_MESSAGE_LIMIT = 2000
SAVE_WARN_THRESHOLD = 1700

logger = logging.getLogger('CFBBot.Storage')


class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    async def save(self, namespace: str, key: str, data: Dict[str, Any]) -> bool:
        """
        Save data to storage.
        
        Args:
            namespace: Category of data (e.g., "server_config", "timer_state")
            key: Unique identifier (e.g., guild_id)
            data: Dictionary of data to store
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def load(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        """
        Load data from storage.
        
        Args:
            namespace: Category of data
            key: Unique identifier
            
        Returns:
            Dictionary of data, or None if not found
        """
        pass
    
    @abstractmethod
    async def load_all(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        """
        Load all data for a namespace.
        
        Args:
            namespace: Category of data
            
        Returns:
            Dictionary of key -> data mappings
        """
        pass
    
    @abstractmethod
    async def delete(self, namespace: str, key: str) -> bool:
        """
        Delete data from storage.
        
        Args:
            namespace: Category of data
            key: Unique identifier
            
        Returns:
            True if successful, False otherwise
        """
        pass


class DiscordDMStorage(StorageBackend):
    """
    Store data in Discord DMs to the bot owner.
    
    Format: NAMESPACE:KEY:JSON_DATA
    Example: SERVER_CONFIG:123456789:{"modules": {...}}
    
    Pros: Free, persists across deploys, no external deps
    Cons: 2000 char limit, slow API calls, hard to debug
    """
    
    def __init__(self, bot=None, owner_id: int = None):
        self.bot = bot
        self.owner_id = owner_id or (int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None)
        self._cache: Dict[str, Dict[str, Any]] = {}  # namespace -> {key -> data}
        self._message_ids: Dict[str, int] = {}  # namespace -> message_id
    
    def set_bot(self, bot):
        """Set the bot instance (needed for Discord API calls)"""
        self.bot = bot
    
    async def _get_dm_channel(self):
        """Get DM channel with bot owner"""
        if not self.bot:
            logger.error("Bot not set for DiscordDMStorage")
            return None
        
        if self.owner_id:
            try:
                owner = await self.bot.fetch_user(self.owner_id)
                return owner.dm_channel or await owner.create_dm()
            except Exception as e:
                logger.error(f"Failed to get DM channel for {self.owner_id}: {e}")
                return None

        from .owner_dm import get_owner_dm
        return await get_owner_dm(self.bot)
    
    async def save(self, namespace: str, key: str, data: Dict[str, Any]) -> bool:
        """Save data to Discord DM"""
        # Update cache
        if namespace not in self._cache:
            self._cache[namespace] = {}
        self._cache[namespace][key] = data
        
        # Save entire namespace to Discord
        return await self._save_namespace(namespace)
    
    async def _save_namespace(self, namespace: str) -> bool:
        """Save all data for a namespace to a single Discord message"""
        dm = await self._get_dm_channel()
        if not dm:
            return False
        
        try:
            all_data = self._cache.get(namespace, {})
            json_data = json.dumps(all_data)
            content = f"{namespace.upper()}:{json_data}"

            # A namespace lives in ONE Discord message. Past the limit the save fails and
            # the change is lost on the next restart, so say so loudly instead of warning.
            if len(content) > DISCORD_MESSAGE_LIMIT:
                logger.error(
                    f"❌ {namespace} is {len(content)} chars — too big for one Discord message "
                    f"(limit {DISCORD_MESSAGE_LIMIT}). NOT saved; changes will be lost on restart."
                )
                await self._warn_owner(
                    f"⚠️ **Settings not saved — `{namespace}` is too big**",
                    f"{len(content)} chars vs the {DISCORD_MESSAGE_LIMIT} limit for one Discord message.\n"
                    f"Recent changes to `{namespace}` will be lost when Harry restarts.",
                )
                return False
            if len(content) > SAVE_WARN_THRESHOLD:
                logger.warning(f"⚠️ {namespace} data approaching Discord limit: {len(content)} chars")
            
            # Find existing message or create new
            msg_id = self._message_ids.get(namespace)
            
            if msg_id:
                try:
                    message = await dm.fetch_message(msg_id)
                    await message.edit(content=content)
                    logger.info(f"✅ Updated {namespace} in Discord DM")
                    return True
                except Exception:
                    pass  # Message not found, create new
            
            # Search for existing message
            async for message in dm.history(limit=100):
                if message.author == self.bot.user and message.content.startswith(f"{namespace.upper()}:"):
                    await message.edit(content=content)
                    self._message_ids[namespace] = message.id
                    logger.info(f"✅ Updated {namespace} in Discord DM")
                    return True
            
            message = await dm.send(content)
            self._message_ids[namespace] = message.id
            logger.info(f"✅ Created {namespace} in Discord DM")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save {namespace} to Discord: {e}")
            await self._warn_owner(
                f"⚠️ **Settings not saved — `{namespace}`**",
                f"`{e}`\nRecent changes to `{namespace}` will be lost when Harry restarts.",
            )
            return False

    async def _warn_owner(self, title: str, body: str) -> None:
        """Tell the bot owner a save failed — a silent failure reverts on the next restart."""
        try:
            from .error_reporter import get_error_reporter
            await get_error_reporter(self.bot).send_notice(title, body)
        except Exception as e:
            logger.debug(f"Could not warn owner about save failure: {e}")
    
    async def load(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        """Load data from Discord DM"""
        # Check cache first
        if namespace in self._cache and key in self._cache[namespace]:
            return self._cache[namespace][key]
        
        # Load from Discord
        await self._load_namespace(namespace)
        return self._cache.get(namespace, {}).get(key)
    
    async def load_all(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        """Load all data for a namespace"""
        if namespace not in self._cache:
            await self._load_namespace(namespace)
        return self._cache.get(namespace, {})
    
    async def _load_namespace(self, namespace: str) -> bool:
        """Load all data for a namespace from Discord"""
        dm = await self._get_dm_channel()
        if not dm:
            return False
        
        try:
            async for message in dm.history(limit=100):
                if message.author == self.bot.user and message.content.startswith(f"{namespace.upper()}:"):
                    json_str = message.content[len(namespace) + 1:]  # Remove "NAMESPACE:"
                    data = json.loads(json_str)
                    self._cache[namespace] = data
                    self._message_ids[namespace] = message.id
                    logger.info(f"✅ Loaded {namespace} from Discord ({len(data)} entries)")
                    return True
            
            # Not found, initialize empty
            self._cache[namespace] = {}
            logger.info(f"📝 No existing {namespace} found in Discord")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load {namespace} from Discord: {e}")
            return False
    
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete data from storage"""
        if namespace in self._cache and key in self._cache[namespace]:
            del self._cache[namespace][key]
            return await self._save_namespace(namespace)
        return True


# ==================== FACTORY ====================

# Active storage backend (change this to swap storage)
_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """
    Get the configured storage backend.
    
    To swap storage backends, change this function or set STORAGE_BACKEND env var.
    """
    global _storage_instance
    
    if _storage_instance is None:
        backend = os.getenv('STORAGE_BACKEND', 'discord').lower()
        if backend != 'discord':
            logger.warning(f"⚠️ STORAGE_BACKEND={backend} isn't supported — using Discord DM storage")
        _storage_instance = DiscordDMStorage()

        logger.info(f"📦 Using storage backend: {type(_storage_instance).__name__}")
    
    return _storage_instance


def set_storage_bot(bot):
    """Set the bot instance for storage (needed for Discord backend)"""
    storage = get_storage()
    if isinstance(storage, DiscordDMStorage):
        storage.set_bot(bot)

