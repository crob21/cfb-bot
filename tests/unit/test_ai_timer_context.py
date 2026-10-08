#!/usr/bin/env python3
"""
Harry should know what the countdown actually says.

Asked about advances he quoted the charter's written cadence ("Tuesday and Friday at
9am"), because the live timer was never in his context. The cadence is league policy;
the countdown is the deadline people are actually on.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from cfb_bot.ai.ai_integration import AICharterAssistant


def timekeeper(active=True, hours=14, minutes=3):
    manager = MagicMock()
    manager.get_advance_channel.return_value = MagicMock()
    manager.get_status.return_value = (
        {'active': True, 'hours': hours, 'minutes': minutes,
         'end_time': datetime.now() + timedelta(hours=hours)}
        if active else {'active': False}
    )
    return manager


class TestTimerContext:
    def test_running_timer_gives_remaining_time_and_deadline(self):
        lines = AICharterAssistant._timer_context(timekeeper())
        joined = "\n".join(lines)
        assert "14h 3m left" in joined
        assert "deadline" in joined
        assert "live countdown" in joined

    def test_stopped_timer_says_so(self):
        joined = "\n".join(AICharterAssistant._timer_context(timekeeper(active=False)))
        assert "not running" in joined
        assert "left" not in joined

    def test_no_advance_channel_is_survivable(self):
        manager = MagicMock()
        manager.get_advance_channel.return_value = None
        assert "not running" in "\n".join(AICharterAssistant._timer_context(manager))

    def test_a_broken_timekeeper_does_not_break_the_prompt(self):
        manager = MagicMock()
        manager.get_advance_channel.side_effect = RuntimeError("boom")
        assert AICharterAssistant._timer_context(manager) == []
