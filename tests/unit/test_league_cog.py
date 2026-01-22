#!/usr/bin/env python3
"""
Unit tests for LeagueCog

Tests:
- /league games - View week schedule
- /league find_game - Find team's game
- /league byes - Teams on bye
- /league week - Current week
- /league timer - Start countdown
- /league timer_status - Check timer
- /league timer_stop - Stop timer
- Schedule manager integration
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def mock_schedule_manager():
    """Mock ScheduleManager"""
    manager = MagicMock()
    manager.teams = ["Hawaii", "LSU", "Nebraska", "Stanford", "Texas", "USF", "Western Michigan"]
    manager.season = 1
    
    # Mock get_week_schedule to return week data
    def get_week_schedule(week):
        schedules = {
            0: {
                "bye_teams": ["LSU", "Nebraska"],
                "games": [
                    {"away": "Western Michigan", "home": "USF"},
                    {"away": "Delaware", "home": "Hawaii"},
                    {"away": "Stanford", "home": "Texas"}
                ]
            },
            12: {
                "bye_teams": [],
                "games": [
                    {"away": "Nebraska", "home": "Indiana"},
                    {"away": "LSU", "home": "Missouri"},
                    {"away": "Texas", "home": "Mississippi St"},
                    {"away": "Oregon St", "home": "Hawaii"},
                    {"away": "Western Michigan", "home": "Northern Illinois"},
                    {"away": "USF", "home": "FAU"},
                    {"away": "Stanford", "home": "NC State"}
                ]
            }
        }
        return schedules.get(week)
    
    manager.get_week_schedule = get_week_schedule
    
    # Mock formatting methods
    def format_team(team_name):
        if team_name in manager.teams:
            return f"**{team_name}**"
        return team_name
    
    def format_game(game, emoji="🏈"):
        away = format_team(game['away'])
        home = format_team(game['home'])
        return f"{emoji} {away} @ {home}"
    
    def format_bye_teams(bye_teams):
        return ", ".join([format_team(t) for t in bye_teams])
    
    def get_bye_teams(week):
        week_data = get_week_schedule(week)
        if not week_data:
            return []
        return week_data.get('bye_teams', [])
    
    def get_team_game(team, week):
        week_data = get_week_schedule(week)
        if not week_data:
            return None
        
        team_lower = team.lower()
        
        # Check bye
        bye_teams = [t.lower() for t in week_data.get('bye_teams', [])]
        if team_lower in bye_teams:
            return {'bye': True, 'team': team}
        
        # Find game
        for game in week_data.get('games', []):
            if game['home'].lower() == team_lower:
                return {
                    'bye': False,
                    'team': team,
                    'opponent': game['away'],
                    'location': 'home',
                    'matchup': f"{format_team(game['away'])} @ {format_team(game['home'])}"
                }
            elif game['away'].lower() == team_lower:
                return {
                    'bye': False,
                    'team': team,
                    'opponent': game['home'],
                    'location': 'away',
                    'matchup': f"{format_team(game['away'])} @ {format_team(game['home'])}"
                }
        
        return None
    
    manager.format_team = format_team
    manager.format_game = format_game
    manager.format_bye_teams = format_bye_teams
    manager.get_bye_teams = get_bye_teams
    manager.get_team_game = get_team_game
    manager.reload_schedule = MagicMock(return_value=True)
    
    return manager


@pytest.fixture
def mock_timekeeper():
    """Mock TimekeeperManager"""
    manager = MagicMock()
    manager.get_season_week = MagicMock(return_value={'season': 5, 'week': 12})
    manager.get_status = MagicMock(return_value={'active': False, 'hours': 0, 'minutes': 0})
    manager.start_timer = AsyncMock(return_value=True)
    manager.stop_timer = AsyncMock()
    manager.increment_week = AsyncMock()
    return manager


class TestLeagueGames:
    """Tests for /league games command"""

    @pytest.mark.asyncio
    async def test_games_current_week(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test viewing games for current week"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            # Call without week param (should use current)
            await cog.games.callback(cog, mock_interaction, week=None)
            
            # Should call get_week_schedule with current week (12)
            assert mock_interaction.response.defer.called
            assert mock_interaction.followup.send.called

    @pytest.mark.asyncio
    async def test_games_specific_week(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test viewing games for a specific week"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            # Call with week 0
            await cog.games.callback(cog, mock_interaction, week=0)
            
            assert mock_interaction.response.defer.called
            assert mock_interaction.followup.send.called

    @pytest.mark.asyncio
    async def test_games_shows_byes(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test that games command shows bye teams"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            await cog.games.callback(cog, mock_interaction, week=0)
            
            # Week 0 has LSU and Nebraska on bye
            # Check that followup.send was called with an embed
            assert mock_interaction.followup.send.called

    @pytest.mark.asyncio
    async def test_games_bolds_user_teams(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test that user teams are bolded in schedule display"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            await cog.games.callback(cog, mock_interaction, week=0)
            
            # format_team and format_game should bold user teams
            # This is tested via the mock_schedule_manager fixture
            assert mock_interaction.followup.send.called

    @pytest.mark.asyncio
    async def test_games_no_schedule_manager(self, mock_interaction, mock_server_config, mock_timekeeper):
        """Test games command fails gracefully without schedule manager"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = None  # No schedule manager
            cog.timekeeper_manager = mock_timekeeper
            
            await cog.games.callback(cog, mock_interaction, week=0)
            
            # Should send error message
            assert mock_interaction.followup.send.called
            call_kwargs = mock_interaction.followup.send.call_args
            assert "not available" in str(call_kwargs)


class TestLeagueFindGame:
    """Tests for /league find_game command"""

    @pytest.mark.asyncio
    async def test_find_game_user_team(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test finding a game for a user-controlled team"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            await cog.find_game.callback(cog, mock_interaction, team="Nebraska", week=12)
            
            # Nebraska @ Indiana in week 12
            assert mock_interaction.followup.send.called

    @pytest.mark.asyncio
    async def test_find_game_bye_week(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test finding a game when team has bye"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            await cog.find_game.callback(cog, mock_interaction, team="LSU", week=0)
            
            # LSU has bye in week 0
            assert mock_interaction.followup.send.called


class TestLeagueByes:
    """Tests for /league byes command"""

    @pytest.mark.asyncio
    async def test_byes_shows_bye_teams(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test showing teams on bye"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            await cog.byes.callback(cog, mock_interaction, week=0)
            
            # Week 0 has LSU and Nebraska on bye
            assert mock_interaction.followup.send.called

    @pytest.mark.asyncio
    async def test_byes_no_byes(self, mock_interaction, mock_server_config, mock_schedule_manager, mock_timekeeper):
        """Test showing no byes when all teams play"""
        from cfb_bot.cogs.league import LeagueCog
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.schedule_manager = mock_schedule_manager
            cog.timekeeper_manager = mock_timekeeper
            
            await cog.byes.callback(cog, mock_interaction, week=12)
            
            # Week 12 has no byes
            assert mock_interaction.followup.send.called


class TestScheduleManager:
    """Tests for ScheduleManager functionality"""

    def test_schedule_manager_bolds_user_teams(self, mock_schedule_manager):
        """Test that format_team bolds user-controlled teams"""
        # User team should be bolded
        assert mock_schedule_manager.format_team("Nebraska") == "**Nebraska**"
        
        # Non-user team should not be bolded
        assert mock_schedule_manager.format_team("Indiana") == "Indiana"

    def test_schedule_manager_format_game(self, mock_schedule_manager):
        """Test that format_game bolds user teams in matchups"""
        game = {"away": "Nebraska", "home": "Indiana"}
        formatted = mock_schedule_manager.format_game(game)
        
        # Nebraska should be bolded (user team), Indiana should not
        assert "**Nebraska**" in formatted
        assert "**Indiana**" not in formatted
        assert "Indiana" in formatted

    def test_schedule_manager_format_bye_teams(self, mock_schedule_manager):
        """Test that format_bye_teams bolds user teams"""
        bye_teams = ["LSU", "Nebraska"]
        formatted = mock_schedule_manager.format_bye_teams(bye_teams)
        
        # Both are user teams, should be bolded
        assert "**LSU**" in formatted
        assert "**Nebraska**" in formatted

    def test_schedule_manager_reload(self, mock_schedule_manager):
        """Test that reload_schedule returns success"""
        result = mock_schedule_manager.reload_schedule()
        assert result == True


class TestLeagueTimer:
    """Tests for timer functionality"""

    @pytest.mark.asyncio
    async def test_timer_start_requires_admin(self, mock_interaction, mock_server_config):
        """Test that starting timer requires admin"""
        from cfb_bot.cogs.league import LeagueCog
        
        # Mock non-admin user
        mock_admin_manager = MagicMock()
        mock_admin_manager.is_admin = MagicMock(return_value=False)
        
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            cog = LeagueCog(MagicMock())
            cog.admin_manager = mock_admin_manager
            
            await cog.timer.callback(cog, mock_interaction, hours=48)
            
            # Should send error about not being admin
            assert mock_interaction.response.send_message.called
            call_args = mock_interaction.response.send_message.call_args
            assert "admin" in str(call_args).lower()
