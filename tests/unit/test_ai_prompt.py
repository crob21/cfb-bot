#!/usr/bin/env python3
"""
Harry answers the question he was asked.

The league prompt used to carry a mandatory "CRITICAL - SCHEDULE FORMATTING RULES"
block on every request, so "why are you wearing corn gear?" came back with this week's
fixtures. It also hardcoded last season's user teams, so Harry claimed to support
Nebraska long after that league ended.
"""

from unittest.mock import MagicMock, patch

from cfb_bot.ai.ai_integration import league_prompt, user_team_names

TEAMS = ['California', 'Duke', 'Arizona State']


def with_teams(teams):
    manager = MagicMock()
    manager.teams = teams
    return patch('cfb_bot.utils.schedule_manager.get_schedule_manager', return_value=manager)


class TestUserTeams:
    def test_teams_come_from_the_live_schedule(self):
        with with_teams(TEAMS):
            assert user_team_names() == TEAMS

    def test_no_schedule_manager_is_survivable(self):
        with patch('cfb_bot.utils.schedule_manager.get_schedule_manager', return_value=None):
            assert user_team_names() == []


class TestLeaguePrompt:
    def _prompt(self, question="why are you wearing corn gear?"):
        with with_teams(TEAMS):
            return league_prompt("You are Harry.", "CHARTER", "SCHEDULE", question)

    def test_tells_harry_to_answer_the_question(self):
        prompt = self._prompt()
        assert "ANSWER THE QUESTION THAT WAS ASKED" in prompt
        assert "Do not volunteer the schedule" in prompt

    def test_schedule_formatting_is_scoped_to_listing_games(self):
        prompt = self._prompt()
        assert "ONLY when listing games" in prompt
        # the old unconditional block is gone
        assert "YOU MUST FOLLOW THESE" not in prompt
        assert "FORMAT AS CLEAN LISTS" not in prompt

    def test_uses_current_teams_not_a_hardcoded_list(self):
        prompt = self._prompt()
        for team in TEAMS:
            assert team in prompt
        assert "Nebraska" not in prompt
        assert "Notre Dame" not in prompt

    def test_keeps_charter_and_schedule_available(self):
        prompt = self._prompt("who plays this week?")
        assert "CHARTER" in prompt and "SCHEDULE" in prompt

    def test_no_teams_configured_does_not_invent_one(self):
        with with_teams([]):
            prompt = league_prompt("You are Harry.", "C", "S", "sup")
        assert "don't claim to support any team" in prompt
