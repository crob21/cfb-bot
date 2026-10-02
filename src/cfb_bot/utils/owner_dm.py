#!/usr/bin/env python3
"""
The bot owner's DM channel.

Harry stores state, backups and error reports as messages in a DM to the bot owner, so
almost every persistence path needs this channel. Four modules each had their own copy
of this lookup; they all call here now.
"""

import logging
from typing import Optional

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


