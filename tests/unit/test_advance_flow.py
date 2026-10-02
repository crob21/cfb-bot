#!/usr/bin/env python3
"""
End-to-end tests for the "@everyone advanced" flow in bot_main.

Every advance bug so far lived here: double increments, the week arrow pointing at the
wrong week, /league timer eating a week, and matchups silently not posting. These drive
_handle_advance with a fake message so those regressions fail in CI, not in Discord.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot import bot_main
from cfb_bot.utils.timekeeper import is_advance_trigger

ADVANCE_CHANNEL_ID = 1261662233109205146


def make_message(content="@everyone advanced", channel_id=ADVANCE_CHANNEL_ID, everyone=True, roles=()):
    message = MagicMock()
    message.content = content
    message.author = MagicMock()
    message.author.bot = False
    message.mention_everyone = everyone
    message.role_mentions = list(roles)
    message.channel = MagicMock()
    message.channel.id = channel_id
    message.channel.send = AsyncMock()
    message.guild = MagicMock()
    message.guild.id = 1261662233109205144
    message.reply = AsyncMock()
    return message


@pytest.fixture
def manager():
    """A timekeeper on Season 4, Week 6 (step 8) with a running countdown."""
    import asyncio

    m = MagicMock()
    m.advance_lock = asyncio.Lock()
    m.is_duplicate_advance = MagicMock(return_value=False)
    m.get_all_active_timers = MagicMock(return_value=[{'channel_id': ADVANCE_CHANNEL_ID, 'label': None}])
    m.stop_all_timers = AsyncMock(return_value=1)
    m.start_timer = AsyncMock(return_value=True)
    m.get_status = MagicMock(return_value={'active': True, 'end_time': None, 'hours': 48, 'minutes': 0})

    state = {'step': 8}

    def season_week():
        from cfb_bot.utils.timekeeper import get_week_info
        info = get_week_info(state['step'])
        return {
            'season': 4,
            'week': state['step'],
            'week_name': info['name'],
            'phase': info['phase'],
            'game_week': info['game_week'],
        }

    async def increment():
        state['step'] += 1

    m.get_season_week = MagicMock(side_effect=season_week)
    m.increment_week = AsyncMock(side_effect=increment)
    m._state = state
    return m


@pytest.fixture
def schedule():
    s = MagicMock()
    s.build_week_embed = MagicMock(return_value=MagicMock())
    return s


@pytest.fixture
def wired(manager, schedule, monkeypatch):
    monkeypatch.setattr(bot_main, 'timekeeper_manager', manager)
    monkeypatch.setattr(bot_main, 'schedule_manager', schedule)
    monkeypatch.setattr(bot_main.server_config, 'get_setting', MagicMock(return_value=True))
    return manager, schedule


class TestTriggerRecognition:
    def test_fires_on_everyone_advanced_in_advance_channel(self):
        assert is_advance_trigger(make_message(), ADVANCE_CHANNEL_ID)

    def test_ignores_other_channels(self):
        assert not is_advance_trigger(make_message(channel_id=999), ADVANCE_CHANNEL_ID)

    def test_ignores_chatter_without_a_ping(self):
        assert not is_advance_trigger(make_message(everyone=False), ADVANCE_CHANNEL_ID)

    def test_ignores_the_word_inside_another_word(self):
        assert not is_advance_trigger(make_message("@everyone advancedstats are up"), ADVANCE_CHANNEL_ID)


class TestAdvance:
    @pytest.mark.asyncio
    async def test_advances_exactly_one_step(self, wired):
        manager, _ = wired
        await bot_main._handle_advance(make_message())
        assert manager.increment_week.await_count == 1
        assert manager._state['step'] == 9  # Week 6 -> Week 7

    @pytest.mark.asyncio
    async def test_stops_every_running_timer_first(self, wired):
        manager, _ = wired
        await bot_main._handle_advance(make_message())
        manager.stop_all_timers.assert_awaited_once()
        manager.start_timer.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_announcement_reads_previous_to_current(self, wired):
        """The embed used to read "Week 7 → Week 8" right after advancing into Week 7."""
        message = make_message()
        await bot_main._handle_advance(message)

        embed = message.channel.send.call_args_list[0].kwargs['embed']  # countdown, not matchups
        assert "Week 6 → **Week 7**" in embed.description
        assert "Week 8" not in embed.description

    @pytest.mark.asyncio
    async def test_duplicate_post_does_not_advance_again(self, wired):
        manager, _ = wired
        manager.is_duplicate_advance.return_value = True

        message = make_message()
        await bot_main._handle_advance(message)

        manager.increment_week.assert_not_awaited()
        manager.start_timer.assert_not_awaited()
        assert "Already got it" in message.reply.call_args[0][0]


class TestMatchupAnnouncement:
    @pytest.mark.asyncio
    async def test_posts_matchups_for_the_new_week(self, wired):
        _, schedule = wired
        message = make_message()
        await bot_main._handle_advance(message)

        schedule.build_week_embed.assert_called_once_with(7)  # step 9 == Week 7
        assert message.channel.send.await_count == 2  # countdown + matchups

    @pytest.mark.asyncio
    async def test_skips_when_announcement_setting_is_off(self, wired, monkeypatch):
        _, schedule = wired
        monkeypatch.setattr(bot_main.server_config, 'get_setting', MagicMock(return_value=False))

        await bot_main._handle_advance(make_message())
        schedule.build_week_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_outside_the_regular_season(self, wired):
        manager, schedule = wired
        manager._state['step'] = 16  # advancing into step 17, Conference Championship

        await bot_main._handle_advance(make_message())
        schedule.build_week_embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_survives_a_week_with_no_schedule_data(self, wired):
        _, schedule = wired
        schedule.build_week_embed.return_value = None

        await bot_main._handle_advance(make_message())  # must not raise
        assert schedule.build_week_embed.called


class TestSeasonRollover:
    @pytest.mark.asyncio
    async def test_training_results_rolls_into_preseason(self, wired):
        manager, _ = wired
        manager._state['step'] = 27  # Training Results

        async def increment_with_rollover():
            manager._state['step'] = 1

        manager.increment_week.side_effect = increment_with_rollover

        message = make_message()
        await bot_main._handle_advance(message)

        embed = message.channel.send.call_args_list[0].kwargs['embed']
        assert "Training Results → **Preseason**" in embed.description
