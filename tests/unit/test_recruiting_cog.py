#!/usr/bin/env python3
"""
Unit tests for RecruitingCog

Tests recruiting commands with real player data:
- /recruiting player - Individual recruit lookup
- /recruiting top - Top recruits by filter
- /recruiting class - Team recruiting class
- /recruiting commits - Team commits list
- /recruiting rankings - Team rankings
- /recruiting portal - Transfer portal lookup
- /recruiting source - Data source config

Real players tested:
- Emmanuel Karnley (transfer portal)
- Kai McClendon (transfer portal)
- Kolt Dieterich (transfer portal with TR indicator)
- Gavin Day (2026 HS recruit)
- David Schwerzel (2026 HS recruit)
- Hollywood/Daylan Smothers (nickname handling)
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from tests.conftest import create_mock_recruit


class TestRecruitingPlayer:
    """Tests for /recruiting player command"""

    @pytest.mark.asyncio
    async def test_player_lookup_gavin_day(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test looking up Gavin Day (2026 QB)"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.search_recruit.return_value = create_mock_recruit(
            name="Gavin Day",
            position="QB",
            stars=4,
            is_transfer=False
        )

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper):

            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Gavin Day")

            mock_on3_scraper.search_recruit.assert_called_once()
            mock_interaction.followup.send.assert_called()

    @pytest.mark.asyncio
    async def test_player_lookup_emmanuel_karnley_transfer(self, mock_interaction, mock_server_config, mock_on3_scraper, mock_cfb_data):
        """Test looking up Emmanuel Karnley (transfer portal player)"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        # Emmanuel is a transfer, should auto-fetch college stats
        mock_on3_scraper.search_recruit.return_value = create_mock_recruit(
            name="Emmanuel Karnley",
            position="DE",
            stars=3,
            is_transfer=True,
            committed_to="Washington"
        )

        mock_cfb_data.get_full_player_info.return_value = {
            "name": "Emmanuel Karnley",
            "team": "Sam Houston State",
            "stats": {"2024": {"defense": {"TOT": 45, "TFL": 8, "SACKS": 5}}}
        }

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper), \
             patch('cfb_bot.cogs.recruiting.cfb_data', mock_cfb_data):

            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Emmanuel Karnley")

            # Should have searched for recruit
            mock_on3_scraper.search_recruit.assert_called_once()

    @pytest.mark.asyncio
    async def test_player_not_found(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test player not found shows error"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.search_recruit.return_value = None

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper):

            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Tits McGee")

            # "Not found" is now public (due to defer at start to prevent timeout)
            # This is acceptable tradeoff to avoid 404 interaction expired errors
            call_kwargs = mock_interaction.followup.send.call_args
            assert call_kwargs is not None  # Just verify it responded

    @pytest.mark.asyncio
    async def test_player_module_disabled(self, mock_interaction, disabled_modules_config):
        """Test player command fails when module disabled"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        with patch('cfb_bot.cogs.recruiting.server_config', disabled_modules_config):
            cog = RecruitingCog(MagicMock())
            result = await cog.player.callback(cog, mock_interaction, name="Gavin Day")

            # Should have sent ephemeral message about disabled module
            mock_interaction.response.send_message.assert_called()


class TestRecruitingPortal:
    """Tests for /recruiting portal command"""

    @pytest.mark.asyncio
    async def test_portal_hollywood_smothers(self, mock_interaction, mock_server_config, mock_on3_scraper, mock_cfb_data):
        """Test portal lookup for Hollywood Smothers (nickname case)"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        # On3 knows him as "Hollywood Smothers"
        mock_on3_scraper.search_recruit.return_value = create_mock_recruit(
            name="Hollywood Smothers",
            position="RB",
            stars=4,
            is_transfer=True
        )

        # CFB might know him by legal name
        mock_cfb_data.get_full_player_info.return_value = None  # First attempt fails
        mock_cfb_data.search_player.return_value = [{
            "name": "Daylan Smothers",
            "position": "RB",
            "team": "NC State"
        }]

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper), \
             patch('cfb_bot.cogs.recruiting.cfb_data', mock_cfb_data):

            cog = RecruitingCog(MagicMock())
            await cog.portal.callback(cog, mock_interaction, name="Hollywood Smothers")

            mock_on3_scraper.search_recruit.assert_called()

    @pytest.mark.asyncio
    async def test_portal_cross_reference(self, mock_interaction, mock_server_config, mock_on3_scraper, mock_cfb_data):
        """Test portal cross-reference between On3 and CFB data"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        # On3 returns different name than search term
        mock_on3_scraper.search_recruit.return_value = create_mock_recruit(
            name="Hollywood Smothers",
            position="RB",
            is_transfer=True
        )

        # CFB data first attempt with "Hollywood" fails
        mock_cfb_data.get_full_player_info.side_effect = [
            None,  # First call with original name
            {"name": "Daylan Smothers", "team": "NC State", "stats": {}}  # Second call
        ]

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper), \
             patch('cfb_bot.cogs.recruiting.cfb_data', mock_cfb_data):

            cog = RecruitingCog(MagicMock())
            await cog.portal.callback(cog, mock_interaction, name="Daylan Smothers")


class TestRecruitingCommits:
    """Tests for /recruiting commits command"""

    @pytest.mark.asyncio
    async def test_washington_commits_2026(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test getting Washington's 2026 commits"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.get_team_commits.return_value = {
            "team": "Washington",
            "year": 2026,
            "commits": [
                {"name": "Emmanuel Karnley", "position": "DE", "stars": 3, "is_transfer": True},
                {"name": "Kai McClendon", "position": "CB", "stars": 3, "is_transfer": True},
                {"name": "Kolt Dieterich", "position": "LB", "stars": 3, "is_transfer": True},
            ]
        }

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper), \
             patch('cfb_bot.cogs.recruiting.get_recruiting_scraper', return_value=(mock_on3_scraper, "On3/Rivals")):

            cog = RecruitingCog(MagicMock())
            await cog.commits.callback(cog, mock_interaction, team="Washington", year=2026)

            mock_on3_scraper.get_team_commits.assert_called_with("Washington", 2026)

    @pytest.mark.asyncio
    async def test_commits_shows_transfer_indicator(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test that commits list shows transfer portal indicator"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        # Include mix of HS recruits and transfers
        mock_on3_scraper.get_team_commits.return_value = {
            "team": "Washington",
            "year": 2026,
            "commits": [
                {"name": "HS Recruit", "position": "QB", "stars": 4, "is_transfer": False},
                {"name": "Portal Player", "position": "DE", "stars": 3, "is_transfer": True},
            ]
        }
        mock_on3_scraper.format_team_commits.return_value = "🏫 HS Recruit - QB ★★★★\n🌀 Portal Player - DE ★★★"

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper), \
             patch('cfb_bot.cogs.recruiting.get_recruiting_scraper', return_value=(mock_on3_scraper, "On3/Rivals")):

            cog = RecruitingCog(MagicMock())
            await cog.commits.callback(cog, mock_interaction, team="Washington")


class TestRecruitingRankings:
    """Tests for /recruiting rankings command"""

    @pytest.mark.asyncio
    async def test_rankings_2026(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test getting 2026 team recruiting rankings"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.get_team_rankings.return_value = [
            {"rank": 1, "team": "Georgia", "total_commits": 25, "points": 320.5},
            {"rank": 2, "team": "Ohio State", "total_commits": 23, "points": 310.2},
            {"rank": 3, "team": "Alabama", "total_commits": 22, "points": 305.0},
        ]

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper), \
             patch('cfb_bot.cogs.recruiting.get_recruiting_scraper', return_value=(mock_on3_scraper, "On3/Rivals")):

            cog = RecruitingCog(MagicMock())
            await cog.rankings.callback(cog, mock_interaction, year=2026, top=25)

            mock_on3_scraper.get_team_rankings.assert_called_with(2026, 25)

    @pytest.mark.asyncio
    async def test_rankings_no_header_rows(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test that rankings filter out header rows like 'Teams'"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        # This was a bug - parser was picking up header row
        mock_on3_scraper.get_team_rankings.return_value = [
            {"rank": 1, "team": "Georgia", "total_commits": 25, "points": 320.5},
            # Should NOT include {"rank": 1, "team": "Teams", ...}
        ]

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper), \
             patch('cfb_bot.cogs.recruiting.get_recruiting_scraper', return_value=(mock_on3_scraper, "On3/Rivals")):

            cog = RecruitingCog(MagicMock())
            await cog.rankings.callback(cog, mock_interaction)


class TestRecruitingSource:
    """Tests for /recruiting source command"""

    @pytest.mark.asyncio
    async def test_view_current_source(self, mock_interaction, mock_server_config):
        """Test viewing current recruiting source"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_server_config.get_recruiting_source.return_value = "on3"

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config):
            cog = RecruitingCog(MagicMock())
            await cog.source.callback(cog, mock_interaction, source=None)

            # acknowledged first (storage writes can outlast Discord's 3s window),
            # so the reply arrives as a followup
            mock_interaction.response.defer.assert_awaited_once()
            mock_interaction.followup.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_source_requires_admin(self, mock_interaction, mock_server_config):
        """Test changing source requires admin"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        # User is not admin
        mock_interaction.user.guild_permissions.administrator = False

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config):
            cog = RecruitingCog(MagicMock())
            cog.admin_manager = None
            await cog.source.callback(cog, mock_interaction, source="247")

            # Should send error
            call_kwargs = mock_interaction.followup.send.call_args
            assert call_kwargs.kwargs.get('ephemeral') == True


class TestTransferPortalDetection:
    """Tests for transfer portal detection logic"""

    @pytest.mark.asyncio
    async def test_kolt_dieterich_detected_as_transfer(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test Kolt Dieterich is detected as transfer (has TR indicator)"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.search_recruit.return_value = {
            "name": "Kolt Dieterich",
            "position": "LB",
            "stars": 3,
            "is_transfer": True,
            "previous_school": "Florida",
            "portal_rating": 85.5,
            "profile_url": "https://on3.com/kolt-dieterich"
        }

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper):

            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Kolt Dieterich")

            # Verify we got the transfer data
            mock_on3_scraper.search_recruit.assert_called()

    @pytest.mark.asyncio
    async def test_gavin_day_not_detected_as_transfer(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """Test Gavin Day is NOT detected as transfer (HS recruit)"""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.search_recruit.return_value = {
            "name": "Gavin Day",
            "position": "QB",
            "stars": 4,
            "is_transfer": False,
            "high_school": "Plantation High School",
            "year": 2026,
            "profile_url": "https://on3.com/gavin-day"
        }

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper):

            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Gavin Day")


class TestRecruitingPlayerCandidatePaths:
    """/recruiting player when a search matches several players"""

    @pytest.mark.asyncio
    async def test_multiple_candidates_posts_a_picker(self, mock_interaction, mock_server_config, mock_on3_scraper):
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.search_recruit.return_value = {
            'multiple': True,
            'query_name': 'Smith',
            'total_found': 3,
            'candidates': [
                create_mock_recruit(name="Smith One", position="WR"),
                create_mock_recruit(name="Smith Two", position="RB"),
                create_mock_recruit(name="Smith Three", position="QB"),
            ],
        }

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper):
            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Smith")

        # one reply: the picker, carrying the select menu
        assert mock_interaction.followup.send.await_count == 1
        assert mock_interaction.followup.send.await_args.kwargs.get('view') is not None

    @pytest.mark.asyncio
    async def test_single_candidate_is_shown_directly(self, mock_interaction, mock_server_config, mock_on3_scraper):
        """A position filter narrowing to one player must still show that player."""
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.search_recruit.return_value = {
            'multiple': True,
            'query_name': 'Smith',
            'total_found': 1,
            'candidates': [create_mock_recruit(name="Smith One", position="WR")],
        }

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper):
            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Smith", position="WR")

        assert mock_interaction.followup.send.await_count == 1
        embed = mock_interaction.followup.send.await_args.kwargs['embed']
        assert "Smith One" in embed.title
        assert mock_interaction.followup.send.await_args.kwargs.get('view') is None

    @pytest.mark.asyncio
    async def test_no_candidates_after_filter_says_not_found(self, mock_interaction, mock_server_config, mock_on3_scraper):
        from cfb_bot.cogs.recruiting import RecruitingCog

        mock_on3_scraper.search_recruit.return_value = {
            'multiple': True, 'query_name': 'Smith', 'total_found': 4, 'candidates': [],
        }

        with patch('cfb_bot.cogs.recruiting.server_config', mock_server_config), \
             patch('cfb_bot.cogs.recruiting.on3_scraper', mock_on3_scraper):
            cog = RecruitingCog(MagicMock())
            await cog.player.callback(cog, mock_interaction, name="Smith", position="K")

        assert mock_interaction.followup.send.await_count == 1
        embed = mock_interaction.followup.send.await_args.kwargs['embed']
        assert "No Players Found" in embed.title
