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

logger = logging.getLogger('CFB26Bot.Storage')


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
            
            # Check Discord message limit
            if len(content) > 1900:
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
            
            # Create new message
            message = await dm.send(content)
            self._message_ids[namespace] = message.id
            logger.info(f"✅ Created {namespace} in Discord DM")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save {namespace} to Discord: {e}")
            return False
    
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


class SupabaseStorage(StorageBackend):
    """
    Store data in Supabase (PostgreSQL).
    
    PLACEHOLDER - Implement when ready to scale.
    
    Setup:
    1. Create Supabase project (free tier)
    2. Create table: configs (namespace TEXT, key TEXT, data JSONB, PRIMARY KEY (namespace, key))
    3. Set SUPABASE_URL and SUPABASE_KEY env vars
    """
    
    def __init__(self):
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        self._client = None
        
        if self.url and self.key:
            logger.info("✅ Supabase credentials found")
            # TODO: Initialize Supabase client
            # from supabase import create_client
            # self._client = create_client(self.url, self.key)
        else:
            logger.warning("⚠️ Supabase not configured (SUPABASE_URL/SUPABASE_KEY missing)")
    
    @property
    def is_available(self) -> bool:
        return self._client is not None
    
    async def save(self, namespace: str, key: str, data: Dict[str, Any]) -> bool:
        """Save data to Supabase"""
        if not self.is_available:
            logger.error("Supabase not available")
            return False
        
        # TODO: Implement
        # await self._client.table('configs').upsert({
        #     'namespace': namespace,
        #     'key': key,
        #     'data': data
        # }).execute()
        raise NotImplementedError("Supabase storage not yet implemented")
    
    async def load(self, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        """Load data from Supabase"""
        if not self.is_available:
            return None
        
        # TODO: Implement
        raise NotImplementedError("Supabase storage not yet implemented")
    
    async def load_all(self, namespace: str) -> Dict[str, Dict[str, Any]]:
        """Load all data for a namespace from Supabase"""
        if not self.is_available:
            return {}
        
        # TODO: Implement
        raise NotImplementedError("Supabase storage not yet implemented")
    
    async def delete(self, namespace: str, key: str) -> bool:
        """Delete data from Supabase"""
        if not self.is_available:
            return False
        
        # TODO: Implement
        raise NotImplementedError("Supabase storage not yet implemented")


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
        
        if backend == 'supabase':
            _storage_instance = SupabaseStorage()
            if not _storage_instance.is_available:
                logger.warning("⚠️ Supabase not available, falling back to Discord")
                _storage_instance = DiscordDMStorage()
        else:
            _storage_instance = DiscordDMStorage()
        
        logger.info(f"📦 Using storage backend: {type(_storage_instance).__name__}")
    
    return _storage_instance


def set_storage_bot(bot):
    """Set the bot instance for storage (needed for Discord backend)"""
    storage = get_storage()
    if isinstance(storage, DiscordDMStorage):
        storage.set_bot(bot)

