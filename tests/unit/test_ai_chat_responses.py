#!/usr/bin/env python3
"""
/harry and /ask must acknowledge the interaction before any followup.

With no AI configured, both commands skipped the initial response and went straight
to followup.send(). Discord kills an unacknowledged interaction token after 3 seconds,
so the reply failed with `404 Unknown Webhook` and the user saw nothing at all.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def make_interaction():
    interaction = MagicMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup.send = AsyncMock()
    interaction.guild.id = 1
    interaction.channel.id = 2
    interaction.user.id = 42
    return interaction


def enabled_config():
    config = MagicMock()
    config.is_module_enabled.return_value = True
    config.is_channel_enabled.return_value = True
    config.get_personality_prompt.return_value = "You are Harry."
    return config


def make_cog(ai_available):
    from cfb_bot.cogs.ai_chat import AIChatCog

    cog = AIChatCog(MagicMock())
    cog.AI_AVAILABLE = ai_available
    cog.ai_assistant = MagicMock() if ai_available else None
    if ai_available:
        cog.ai_assistant.ask_ai = AsyncMock(return_value="Oi!")
    return cog


@pytest.mark.parametrize("command", ["harry", "ask"])
@pytest.mark.parametrize("ai_available", [True, False])
@pytest.mark.asyncio
async def test_interaction_is_acknowledged_before_followup(command, ai_available):
    cog = make_cog(ai_available)
    interaction = make_interaction()

    with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
        await getattr(cog, command).callback(cog, interaction, question="sup")

    # acknowledged first, then the answer — never a bare followup
    interaction.response.send_message.assert_awaited_once()
    interaction.followup.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_ai_key_is_explained_not_apologized_for():
    cog = make_cog(ai_available=False)
    interaction = make_interaction()

    with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
        await cog.harry.callback(cog, interaction, question="sup")

    embed = interaction.followup.send.await_args.kwargs['embed']
    assert "OPENAI_API_KEY" in embed.description
