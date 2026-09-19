#!/usr/bin/env python3
"""
The bot owner's DM channel.

Harry stores state, backups and error reports as messages in a DM to the bot owner, so
almost every persistence path needs this channel. Four modules each had their own copy
of this lookup; they all call here now.
"""

import logging
from typing import Optional

logger = logging.getLogger('CFB26Bot.OwnerDM')


async def get_owner_dm(bot) -> Optional[object]:
    """Return the bot owner's DM channel, creating it if needed. None if unavailable."""
    if not bot:
        return None
    try:
        app_info = await bot.application_info()
        owner = getattr(app_info, 'owner', None)
        if not owner:
            logger.warning("⚠️ Could not determine bot owner")
            return None
        return owner.dm_channel or await owner.create_dm()
    except Exception as e:
        logger.debug(f"Could not open bot owner DM: {e}")
        return None


async def get_owner_id(bot) -> Optional[int]:
    """Return the bot owner's user ID, or None if it can't be determined."""
    if not bot:
        return None
    try:
        app_info = await bot.application_info()
        return app_info.owner.id if app_info.owner else None
    except Exception as e:
        logger.debug(f"Could not determine bot owner id: {e}")
        return None
