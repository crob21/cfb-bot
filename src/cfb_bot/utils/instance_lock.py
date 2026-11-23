#!/usr/bin/env python3
"""
One Harry at a time.

Two copies of the bot on the same token both answer every message (a deploy where the old
copy hangs on, or a forgotten second host). Each copy writes its ID into one message in the
owner DM when it starts, and rereads it every CHECK_SECONDS. When a newer copy has taken
over, the older one disconnects and stands by without exiting, so a host that restarts
exited processes doesn't bring it back to fight over the message.
"""

import logging
import uuid
from typing import Optional

from .owner_dm import find_saved, get_owner_dm, keep

logger = logging.getLogger('CFBBot.Instance')

PREFIX = 'HARRY_INSTANCE:'
CHECK_SECONDS = 15

INSTANCE_ID = uuid.uuid4().hex[:12]

_message_id: Optional[int] = None
stood_down = False


def owner_of(content: str) -> Optional[str]:
    """The instance ID in a lease message, or None if it isn't one."""
    if not content.startswith(PREFIX):
        return None
    return content[len(PREFIX):].strip() or None


async def claim(bot) -> bool:
    """Make this copy the live Harry. False if the owner DM isn't reachable."""
    global _message_id
    dm = await get_owner_dm(bot)
    if not dm:
        logger.warning("Could not claim the instance lease (no owner DM)")
        return False
    content = PREFIX + INSTANCE_ID
    try:
        message = await find_saved(bot, dm, lambda m: owner_of(m.content))
        if message:
            await message.edit(content=content)
        else:
            message = await dm.send(content)
            await keep(message)
        _message_id = message.id
    except Exception as e:
        logger.warning(f"Could not claim the instance lease: {e}")
        return False
    logger.info(f"This copy of Harry is {INSTANCE_ID}")
    return True


async def superseded(bot) -> bool:
    """True when a newer copy of Harry has taken over. Unreachable or unknown means no."""
    if _message_id is None:
        return False
    dm = await get_owner_dm(bot)
    if not dm:
        return False
    try:
        message = await dm.fetch_message(_message_id)
    except Exception as e:
        # Deleted lease: take it back. Anything else (a network blip): keep running.
        if getattr(e, 'status', None) == 404:
            await claim(bot)
        return False
    current = owner_of(message.content)
    return current is not None and current != INSTANCE_ID


async def stand_down(bot) -> None:
    """Disconnect from Discord; main() keeps the process idle afterwards."""
    global stood_down
    stood_down = True
    logger.warning(f"A newer copy of Harry took over - {INSTANCE_ID} is standing down")
    await bot.close()
