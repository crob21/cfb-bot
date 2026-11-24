#!/usr/bin/env python3
"""
The bot owner's DM channel, and finding Harry's saved messages in it.

Harry stores state, backups and error reports as messages in a DM to the bot owner, so
almost every persistence path needs this channel.

Saved messages are edited in place, so they never move: error reports, alerts and nags pile
up on top of them. A lookup that only reads the newest messages eventually stops finding them
and quietly falls back to defaults. So every saved message is pinned, and lookups read the
pins first, then scan back SCAN_LIMIT messages for anything saved before pinning existed.
"""

import logging
from typing import Callable, List, Optional

logger = logging.getLogger('CFBBot.OwnerDM')

# Startup restores ~10 kinds of state through this DM; each lookup was an HTTP call
_cached_dm = None


async def get_owner_dm(bot) -> Optional[object]:
    """Return the bot owner's DM channel, creating it if needed. None if unavailable."""
    global _cached_dm
    if not bot:
        return None
    if _cached_dm is not None:
        return _cached_dm
    try:
        app_info = await bot.application_info()
        owner = getattr(app_info, 'owner', None)
        if not owner:
            logger.warning("Could not determine bot owner")
            return None
        _cached_dm = owner.dm_channel or await owner.create_dm()
        return _cached_dm
    except Exception as e:
        logger.debug(f"Could not open bot owner DM: {e}")
        return None




SCAN_LIMIT = 500  # how far back to look for a saved message that isn't pinned yet


async def _pinned(bot, dm) -> list:
    try:
        return [m for m in await dm.pins() if m.author == bot.user]
    except Exception as e:
        logger.warning(f"Could not read the owner DM's pins: {e}")
        return []


async def saved_messages(bot, dm) -> List[object]:
    """All of Harry's messages in the owner DM: pinned ones first, then the newest SCAN_LIMIT."""
    pinned = await _pinned(bot, dm)
    seen = {m.id for m in pinned}
    rest = [m async for m in dm.history(limit=SCAN_LIMIT) if m.author == bot.user and m.id not in seen]
    return pinned + rest


async def find_saved(bot, dm, match: Callable[[object], bool]):
    """The first saved message `match` accepts (pinning it if it wasn't), or None.

    Only scans history when nothing pinned matches.
    """
    found = next((m for m in await _pinned(bot, dm) if match(m)), None)
    if found is None:
        history = dm.history(limit=SCAN_LIMIT)
        try:
            async for message in history:
                if message.author == bot.user and match(message):
                    found = message
                    break
        finally:
            close = getattr(history, 'aclose', None)  # stopping early leaves the reader open
            if close:
                await close()
    if found is not None:
        await keep(found)
    return found


async def keep(message) -> None:
    """Pin a saved message so lookups always find it. A failed pin is logged, not raised."""
    if getattr(message, 'pinned', False):
        return
    try:
        await message.pin()
    except Exception as e:
        # Discord allows 50 pins per channel; past that the history scan still finds it
        logger.warning(f"Could not pin a saved message in the owner DM: {e}")
