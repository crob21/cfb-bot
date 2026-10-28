#!/usr/bin/env python3
"""
When a command breaks: Harry's line for the user, the traceback for the bot owner.

Raw exception text never goes to Discord. It reads badly in Harry's voice and can
leak internals (URLs, file paths, API error bodies).
"""

import logging

import discord

logger = logging.getLogger('CFBBot.Oops')

OOPS = "❌ That went wrong, mate. The bot owner's been told."


def _where(interaction: discord.Interaction) -> str:
    command = getattr(interaction, 'command', None)
    return f"/{command.qualified_name}" if command else "a command"


async def report(interaction: discord.Interaction, error: BaseException) -> None:
    """DM the bot owner about an error (deduplicated and rate-capped by the reporter)."""
    from ..utils.error_reporter import get_error_reporter
    try:
        await get_error_reporter().report(error, _where(interaction))
    except Exception as e:
        logger.warning(f"Could not report error from {_where(interaction)}: {e}")


async def oops(interaction: discord.Interaction, error: BaseException) -> None:
    """Report the error and tell the user, whether or not the interaction was deferred."""
    await report(interaction, error)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(OOPS, ephemeral=True)
        else:
            await interaction.response.send_message(OOPS, ephemeral=True)
    except Exception:
        pass  # Interaction may have expired; the owner already has the report


# Shown when a dependency hasn't been wired up yet, which in practice means the bot is
# still starting up. Nothing the user did, nothing they can fix.
NOT_READY = "❌ Give us a sec, mate. I'm still waking up. Try again in a minute."

SERVERS_ONLY = "❌ Servers only, mate. Not in DMs."

NO_AI = "❌ My brain's not plugged in, mate. No AI is configured."
