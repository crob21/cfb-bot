#!/usr/bin/env python3
"""
Unit tests for the CFB 26 dynasty week table in utils/timekeeper.py
"""

from unittest.mock import AsyncMock

import pytest

from cfb_bot.utils.timekeeper import (CFB_DYNASTY_WEEKS, FIRST_WEEK, LAST_WEEK,
                                      TOTAL_WEEKS_PER_SEASON, get_game_week,
                                      get_next_week,
                                      get_week_name, get_week_phase,
                                      is_valid_week, migrate_legacy_week)

EXPECTED = [
    (1, "Preseason", "Preseason"),
    *[(n + 2, "Regular Season", f"Week {n}") for n in range(15)],
    (17, "Postseason", "Conference Championship"),
    (18, "Postseason", "Bowl Week 1"),
    (19, "Postseason", "Bowl Week 2 / CFP Quarterfinals"),
    (20, "Postseason", "Bowl Week 3 / CFP Semifinals"),
    (21, "Postseason", "Bowl Week 4"),
    (22, "Postseason", "National Championship"),
    (23, "Offseason", "Staff Moves"),
    (24, "Offseason", "Transfer Portal Stage 1 (Open)"),
    (25, "Offseason", "Transfer Portal Stage 2 (Close)"),
    (26, "Offseason", "National Signing Day"),
    (27, "Offseason", "Training Results"),
]


class TestWeekTable:
    def test_matches_dynasty_structure(self):
        assert sorted(CFB_DYNASTY_WEEKS) == list(range(1, 28))
        assert TOTAL_WEEKS_PER_SEASON == 27
        assert (FIRST_WEEK, LAST_WEEK) == (1, 27)
        for step, phase, name in EXPECTED:
            assert get_week_name(step) == name
            assert get_week_phase(step) == phase

    def test_game_week_only_for_regular_season(self):
        assert get_game_week(1) is None
        assert get_game_week(2) == 0
        assert get_game_week(16) == 14
        assert all(get_game_week(s) is None for s in range(17, 28))
        assert get_game_week(None) is None

    def test_next_week_wraps(self):
        assert get_next_week(1) == 2
        assert get_next_week(26) == 27
        assert get_next_week(27) == 1

    def test_is_valid_week(self):
        assert not is_valid_week(0)
        assert is_valid_week(1)
        assert is_valid_week(27)
        assert not is_valid_week(28)

    def test_legacy_migration(self):
        assert migrate_legacy_week(0) == 1
        assert migrate_legacy_week(5) == 7  # Week 5
        assert get_week_name(migrate_legacy_week(14)) == "Conference Championship"
        assert get_week_name(migrate_legacy_week(25)) == "Training Results"
        assert migrate_legacy_week(None) is None


class TestIncrementWeek:
    @pytest.mark.asyncio
    async def test_rolls_over_after_training_results(self):
        from cfb_bot.utils.timekeeper import TimekeeperManager

        manager = TimekeeperManager.__new__(TimekeeperManager)
        manager.season = 3
        manager.week = 27
        manager._save_season_week_state = AsyncMock()

        await manager.increment_week()
        assert (manager.season, manager.week) == (4, 1)

        await manager.increment_week()
        assert (manager.season, manager.week) == (4, 2)
        assert get_week_name(manager.week) == "Week 0"

    @pytest.mark.asyncio
    async def test_set_season_week_rejects_invalid_step(self):
        from cfb_bot.utils.timekeeper import TimekeeperManager

        manager = TimekeeperManager.__new__(TimekeeperManager)
        manager._save_season_week_state = AsyncMock()
        assert not await manager.set_season_week(1, 0)
        assert not await manager.set_season_week(1, 28)
        assert await manager.set_season_week(1, 17)
        assert manager.week == 17


class TestAdvanceTrigger:
    ADVANCE_CHANNEL = 111

    def _msg(self, content="@everyone advanced", channel_id=ADVANCE_CHANNEL, everyone=True, roles=()):
        from unittest.mock import MagicMock
        msg = MagicMock()
        msg.content = content
        msg.channel.id = channel_id
        msg.mention_everyone = everyone
        msg.role_mentions = list(roles)
        return msg

    def test_triggers_in_advance_channel(self):
        from cfb_bot.utils.timekeeper import is_advance_trigger
        assert is_advance_trigger(self._msg(), self.ADVANCE_CHANNEL)
        assert is_advance_trigger(self._msg("We ADVANCED! @everyone"), self.ADVANCE_CHANNEL)
        assert is_advance_trigger(self._msg(everyone=False, roles=["League"]), self.ADVANCE_CHANNEL)

    def test_ignores_other_channels_and_threads(self):
        from cfb_bot.utils.timekeeper import is_advance_trigger
        assert not is_advance_trigger(self._msg(channel_id=222), self.ADVANCE_CHANNEL)
        assert not is_advance_trigger(self._msg(), None)

    def test_requires_ping_and_whole_word(self):
        from cfb_bot.utils.timekeeper import is_advance_trigger
        assert not is_advance_trigger(self._msg(everyone=False), self.ADVANCE_CHANNEL)
        assert not is_advance_trigger(self._msg("@everyone advancedstats are up"), self.ADVANCE_CHANNEL)
        assert not is_advance_trigger(self._msg("@everyone advance soon"), self.ADVANCE_CHANNEL)


class TestStopAllTimers:
    @pytest.mark.asyncio
    async def test_stops_timers_in_every_channel(self):
        from unittest.mock import MagicMock
        from cfb_bot.utils.timekeeper import TimekeeperManager

        manager = TimekeeperManager.__new__(TimekeeperManager)
        running_a, running_b, idle = MagicMock(), MagicMock(), MagicMock()
        for t, active in ((running_a, True), (running_b, True), (idle, False)):
            t.is_active = active
            t.stop_countdown = AsyncMock(return_value=active)
        manager.timers = {1: running_a, 2: running_b, 3: idle}

        assert await manager.stop_all_timers() == 2
        running_a.stop_countdown.assert_awaited_once()
        running_b.stop_countdown.assert_awaited_once()
        idle.stop_countdown.assert_not_awaited()


class TestNotificationThresholds:
    @pytest.mark.asyncio
    async def test_short_timer_skips_warnings_longer_than_duration(self):
        from unittest.mock import MagicMock, patch
        from cfb_bot.utils.timekeeper import AdvanceTimer

        timer = AdvanceTimer(MagicMock(), MagicMock())
        timer.save_state = AsyncMock()
        with patch('asyncio.create_task', side_effect=lambda coro: coro.close() or MagicMock()):
            await timer.start_countdown(10)
        assert timer.notifications_sent == {24: True, 12: True, 6: False, 1: False}

    @pytest.mark.asyncio
    async def test_only_most_urgent_warning_sent_when_several_crossed(self):
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock, patch
        from cfb_bot.utils.timekeeper import AdvanceTimer

        timer = AdvanceTimer(MagicMock(), MagicMock())
        timer.is_active = True
        timer.start_time = datetime.now() - timedelta(hours=43)
        timer.end_time = datetime.now() + timedelta(hours=5)  # restored with 24/12/6 all unsent
        timer.save_state = AsyncMock()
        sent = []

        async def fake_notify(hours):
            sent.append(hours)
            timer.is_active = False  # end the loop after one pass

        timer._send_notification = fake_notify
        with patch('cfb_bot.utils.timekeeper.asyncio.sleep', AsyncMock()):
            await timer._monitor_countdown()
        assert sent == [6]
        assert timer.notifications_sent == {24: True, 12: True, 6: True, 1: False}


class TestTimerStatePersistence:
    def test_settings_message_is_not_treated_as_timer_state(self):
        from cfb_bot.utils.timekeeper import _is_timer_state_message
        assert not _is_timer_state_message('```json\n{"notification_channel_id": 5, "type": "bot_settings"}\n```')
        assert not _is_timer_state_message('```json\n{"season": 1, "week": 3, "type": "season_week"}\n```')
        assert _is_timer_state_message('```json\n{"channel_id": 5, "is_active": false}\n```')
        assert _is_timer_state_message('```json\n{"channel_id": 5, "end_time": "2026-01-01T00:00:00"}\n```')


class TestAdvancePending:
    @pytest.mark.asyncio
    async def test_starting_timer_clears_pending_flag(self):
        from unittest.mock import MagicMock
        from cfb_bot.utils.timekeeper import TimekeeperManager

        manager = TimekeeperManager(MagicMock())
        manager._save_season_week_state = AsyncMock()
        manager.advance_pending = True
        timer = MagicMock()
        timer.start_countdown = AsyncMock(return_value=True)
        manager.get_timer = MagicMock(return_value=timer)

        assert await manager.start_timer(MagicMock(), 48)
        assert manager.advance_pending is False
        manager._save_season_week_state.assert_awaited_once()

    def test_duplicate_advance_window(self):
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock
        from cfb_bot.utils.timekeeper import TimekeeperManager

        manager = TimekeeperManager(MagicMock())
        assert not manager.is_duplicate_advance()
        manager.last_manual_advance_at = datetime.now() - timedelta(minutes=1)
        assert manager.is_duplicate_advance()
        manager.last_manual_advance_at = datetime.now() - timedelta(minutes=10)
        assert not manager.is_duplicate_advance()


class TestPrevWeek:
    def test_prev_week_wraps(self):
        from cfb_bot.utils.timekeeper import get_prev_week
        assert get_prev_week(3) == 2   # Week 1 -> Week 0
        assert get_prev_week(2) == 1   # Week 0 -> Preseason
        assert get_prev_week(1) == 27  # Preseason -> previous season's Training Results


class TestCharterImportHelpers:
    def test_google_doc_exports_markdown_then_text(self):
        from cfb_bot.utils.charter_editor import CharterEditor
        urls = CharterEditor.export_urls(
            "https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/edit?usp=sharing"
        )
        assert urls == [
            "https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/export?format=markdown",
            "https://docs.google.com/document/d/1lX28DlMmH0P77aficBA_1Vo9ykEm_bAroSTpwMhWr_8/export?format=txt",
        ]

    def test_other_urls_pass_through(self):
        from cfb_bot.utils.charter_editor import CharterEditor
        assert CharterEditor.export_urls("https://example.com/charter.txt") == ["https://example.com/charter.txt"]

    def test_cleanup_strips_bom_crlf_and_escapes(self):
        from cfb_bot.utils.charter_editor import CharterEditor
        cleaned = CharterEditor.clean_exported_text("﻿# **Charter**\r\n\n* 1\\. Rules \\- ok \\> fine  \n")
        assert cleaned == "# **Charter**\n\n* 1. Rules - ok > fine"


class TestWeekEmbedBuilder:
    """Both advance paths share one matchups embed builder"""

    def _manager(self, schedule):
        from cfb_bot.utils.schedule_manager import ScheduleManager
        m = ScheduleManager()
        m.load_from_dict({"season": 2, "teams": ["California"], "schedule": schedule})
        return m

    def test_returns_none_without_data(self):
        assert self._manager({}).build_week_embed(3) is None

    def test_includes_games_and_byes_with_user_teams_bolded(self):
        m = self._manager({"3": {"bye_teams": ["Duke"], "games": [{"away": "California", "home": "Oklahoma State"}]}})
        embed = m.build_week_embed(3)
        assert embed.title == "📅 Week 3 Matchups"
        fields = {f.name: f.value for f in embed.fields}
        assert fields["🛋️ Bye Week"] == "Duke"
        assert fields["🎮 This Week's Games"] == "🏈 **California** @ Oklahoma State"
