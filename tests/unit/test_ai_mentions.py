#!/usr/bin/env python3
"""
Unit tests for Harry replying to @mentions (AIChatCog.on_message)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


BOT_ID = 999888777


def make_cog(ai_available=True):
    from cfb_bot.cogs.ai_chat import AIChatCog

    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = BOT_ID
    bot.get_cog.return_value = None  # no FunCog targets
    cog = AIChatCog(bot)
    cog.AI_AVAILABLE = ai_available
    cog.ai_assistant = MagicMock()
    cog.ai_assistant.ask_ai = AsyncMock(return_value="Oi! Right then.")
    return cog


def make_message(content=f"<@{BOT_ID}> who do we play?", mentions_bot=True, is_bot=False,
                 mention_everyone=False, guild=True):
    message = MagicMock()
    message.content = content
    message.author.bot = is_bot
    message.author.id = 42
    message.author.display_name = "Craig"
    message.mention_everyone = mention_everyone
    message.guild = MagicMock() if guild else None
    if guild:
        message.guild.id = 1
    message.channel.id = 2
    message.channel.typing = MagicMock(return_value=AsyncMock())
    message.channel.typing.return_value.__aenter__ = AsyncMock()
    message.channel.typing.return_value.__aexit__ = AsyncMock()
    message.reply = AsyncMock()
    bot_user = MagicMock()
    bot_user.id = BOT_ID
    message.mentions = [bot_user] if mentions_bot else []
    return message


def enabled_config(module=True, channel=True):
    config = MagicMock()
    config.is_module_enabled.return_value = module
    config.is_channel_enabled.return_value = channel
    config.get_personality_prompt.return_value = "You are Harry."
    return config


class TestMentionReplies:
    @pytest.mark.asyncio
    async def test_replies_to_mention(self):
        cog, message = make_cog(), make_message()
        # the bot user object in message.mentions must be the same object identity check uses
        message.mentions = [cog.bot.user]
        with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
            await cog.on_message(message)
        message.reply.assert_awaited_once()
        assert message.reply.await_args[0][0] == "Oi! Right then."
        assert cog.ai_assistant.ask_ai.await_args[0][0].endswith("who do we play?")

    @pytest.mark.asyncio
    async def test_ignores_messages_without_mention(self):
        cog = make_cog()
        message = make_message(content="just chatting", mentions_bot=False)
        with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
            await cog.on_message(message)
        cog.ai_assistant.ask_ai.assert_not_awaited()
        message.reply.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_ignores_everyone_ping_and_bots(self):
        for kwargs in ({'mention_everyone': True}, {'is_bot': True}, {'guild': False}):
            cog = make_cog()
            message = make_message(**kwargs)
            message.mentions = [cog.bot.user]
            with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
                await cog.on_message(message)
            cog.ai_assistant.ask_ai.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_respects_module_and_channel_settings(self):
        for config in (enabled_config(module=False), enabled_config(channel=False)):
            cog = make_cog()
            message = make_message()
            message.mentions = [cog.bot.user]
            with patch('cfb_bot.cogs.ai_chat.server_config', config):
                await cog.on_message(message)
            cog.ai_assistant.ask_ai.assert_not_awaited()
            message.reply.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cooldown_blocks_rapid_repeats(self):
        cog = make_cog()
        with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
            for _ in range(3):
                message = make_message()
                message.mentions = [cog.bot.user]
                await cog.on_message(message)
        assert cog.ai_assistant.ask_ai.await_count == 1

    @pytest.mark.asyncio
    async def test_bare_mention_still_gets_a_reply(self):
        cog = make_cog()
        message = make_message(content=f"<@{BOT_ID}>")
        message.mentions = [cog.bot.user]
        with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
            await cog.on_message(message)
        assert "Greet them" in cog.ai_assistant.ask_ai.await_args[0][0]
        message.reply.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_leaves_fun_targets_to_fun_cog(self):
        cog = make_cog()
        fun_cog = MagicMock()
        fun_cog._targets_for_guild.return_value = {42: {}}
        cog.bot.get_cog.return_value = fun_cog
        message = make_message()
        message.mentions = [cog.bot.user]
        with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
            await cog.on_message(message)
        cog.ai_assistant.ask_ai.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_replies_when_ai_unavailable(self):
        cog = make_cog(ai_available=False)
        message = make_message()
        message.mentions = [cog.bot.user]
        with patch('cfb_bot.cogs.ai_chat.server_config', enabled_config()):
            await cog.on_message(message)
        message.reply.assert_awaited_once()
        cog.ai_assistant.ask_ai.assert_not_awaited()
