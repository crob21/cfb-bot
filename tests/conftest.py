#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for CFB League Bot tests.

This file provides:
- Mock Discord objects (Bot, Interaction, User, Guild, Channel)
- Server config fixtures
- Test player data
- Common test utilities
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ==================== EVENT LOOP ====================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== MOCK DISCORD OBJECTS ====================

@pytest.fixture
def mock_user():
    """Create a mock Discord user"""
    user = MagicMock()
    user.id = 123456789
    user.name = "TestUser"
    user.display_name = "Test User"
    user.bot = False
    user.mention = "<@123456789>"
    user.guild_permissions = MagicMock()
    user.guild_permissions.administrator = False
    return user


@pytest.fixture
def mock_admin_user(mock_user):
    """Create a mock Discord admin user"""
    mock_user.guild_permissions.administrator = True
    return mock_user


@pytest.fixture
def mock_guild():
    """Create a mock Discord guild (server)"""
    guild = MagicMock()
    guild.id = 987654321
    guild.name = "Test CFB League"
    guild.get_channel = MagicMock(return_value=None)
    return guild


@pytest.fixture
def mock_channel():
    """Create a mock Discord text channel"""
    channel = MagicMock()
    channel.id = 111222333
    channel.name = "general"
    channel.mention = "<#111222333>"
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def mock_interaction(mock_user, mock_guild, mock_channel):
    """Create a mock Discord interaction for slash commands"""
    interaction = MagicMock()
    interaction.user = mock_user
    interaction.guild = mock_guild
    interaction.channel = mock_channel
    interaction.response = MagicMock()
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()
    return interaction


@pytest.fixture
def mock_bot():
    """Create a mock Discord bot"""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 999888777
    bot.user.name = "Harry"
    bot.guilds = []
    bot.cogs = {}
    bot.tree = MagicMock()
    bot.tree.sync = AsyncMock(return_value=[])
    bot.fetch_user = AsyncMock()
    bot.get_channel = MagicMock(return_value=None)
    return bot


# ==================== SERVER CONFIG FIXTURES ====================

@pytest.fixture
def mock_server_config():
    """Create a mock server config manager"""
    config = MagicMock()

    # Default: all modules enabled
    config.is_module_enabled = MagicMock(return_value=True)
    config.is_channel_enabled = MagicMock(return_value=True)
    config.get_enabled_modules = MagicMock(return_value=[
        "core", "ai_chat", "cfb_data", "league", "hs_stats", "recruiting"
    ])
    config.get_enabled_channels = MagicMock(return_value=[111222333])
    config.get_admin_channel = MagicMock(return_value=111222333)
    config.get_personality_prompt = MagicMock(return_value="You are Harry, a sarcastic cockney assistant.")
    config.get_recruiting_source = MagicMock(return_value="on3")
    config.auto_responses_enabled = MagicMock(return_value=True)
    config.save_to_discord = AsyncMock()

    return config


@pytest.fixture
def disabled_modules_config(mock_server_config):
    """Server config with modules disabled"""
    mock_server_config.is_module_enabled = MagicMock(return_value=False)
    mock_server_config.get_enabled_modules = MagicMock(return_value=["core"])
    return mock_server_config


# ==================== REAL PLAYER TEST DATA ====================
# Players we've used in actual testing

TEST_RECRUITS = {
    # Transfer portal players
    "emmanuel_karnley": {
        "name": "Emmanuel Karnley",
        "search_term": "Emmanuel Karnley",
        "expected_position": "DE",
        "is_transfer": True,
        "committed_to": "Washington",
        "notes": "Transfer from SHSU"
    },
    "kai_mcclendon": {
        "name": "Kai McClendon",
        "search_term": "Kai McClendon",
        "expected_position": "CB",
        "is_transfer": True,
        "committed_to": "Washington",
        "notes": "Transfer portal player"
    },
    "kolt_dieterich": {
        "name": "Kolt Dieterich",
        "search_term": "Kolt Dieterich",
        "expected_position": "LB",
        "is_transfer": True,
        "committed_to": "Washington",
        "notes": "Transfer portal player with TR indicator"
    },

    # High school recruits
    "gavin_day": {
        "name": "Gavin Day",
        "search_term": "Gavin Day",
        "expected_position": "QB",
        "is_transfer": False,
        "year": 2026,
        "notes": "2026 QB recruit"
    },
    "david_schwerzel": {
        "name": "David Schwerzel",
        "search_term": "David Schwerzel",
        "expected_position": "OT",
        "is_transfer": False,
        "year": 2026,
        "notes": "2026 OT recruit"
    },

    # Nickname test case
    "hollywood_smothers": {
        "name": "Hollywood Smothers",
        "search_term": "Hollywood Smothers",
        "alternate_name": "Daylan Smothers",
        "expected_position": "RB",
        "is_transfer": True,
        "notes": "Goes by 'Hollywood' on On3, legal name is Daylan"
    },
}

TEST_CFB_PLAYERS = {
    # College players for CFB data lookup
    "travis_hunter": {
        "name": "Travis Hunter",
        "team": "Colorado",
        "position": "WR"
    },
    "cam_ward": {
        "name": "Cam Ward",
        "team": "Miami",
        "position": "QB"
    },
}

TEST_HS_PLAYERS = {
    # High school players for MaxPreps lookup
    "arch_manning": {
        "name": "Arch Manning",
        "state": "LA",
        "school": "Isidore Newman",
        "position": "QB"
    },
    "gavin_day": {
        "name": "Gavin Day",
        "state": "FL",
        "position": "QB"
    },
    "mason_james": {
        "name": "Mason James",
        "state": None,  # Common name, should test multiple results
        "position": None
    }
}

TEST_TEAMS = {
    "washington": {
        "name": "Washington",
        "conference": "Big Ten",
        "url_slug": "washington-huskies"
    },
    "ohio_state": {
        "name": "Ohio State",
        "conference": "Big Ten",
        "url_slug": "ohio-state-buckeyes"
    },
    "oregon": {
        "name": "Oregon",
        "conference": "Big Ten",
        "url_slug": "oregon-ducks",
        "notes": "Harry hates the Ducks! 🦆"
    },
}


@pytest.fixture
def test_recruits():
    """Get test recruit data"""
    return TEST_RECRUITS


@pytest.fixture
def test_cfb_players():
    """Get test CFB player data"""
    return TEST_CFB_PLAYERS


@pytest.fixture
def test_hs_players():
    """Get test high school player data"""
    return TEST_HS_PLAYERS


@pytest.fixture
def test_teams():
    """Get test team data"""
    return TEST_TEAMS


# ==================== MOCK SCRAPERS ====================

@pytest.fixture
def mock_on3_scraper():
    """Create a mock On3 scraper"""
    scraper = MagicMock()
    scraper.search_recruit = AsyncMock()
    scraper.get_team_commits = AsyncMock()
    scraper.get_team_rankings = AsyncMock()
    scraper.get_top_recruits = AsyncMock()
    scraper.format_recruit = MagicMock(return_value="Formatted recruit data")
    scraper.format_team_commits = MagicMock(return_value="Formatted commits")
    scraper._get_current_recruiting_year = MagicMock(return_value=2026)
    return scraper


@pytest.fixture
def mock_cfb_data():
    """Create a mock CFB data client"""
    client = MagicMock()
    client.is_available = True
    client.get_full_player_info = AsyncMock()
    client.search_player = AsyncMock()
    client.get_rankings = AsyncMock()
    client.get_team_schedule = AsyncMock()
    client.format_player_response = MagicMock(return_value="Formatted player data")
    return client


@pytest.fixture
def mock_hs_stats_scraper():
    """Create a mock MaxPreps scraper"""
    scraper = MagicMock()
    scraper.is_available = True
    scraper.search_player = AsyncMock()
    scraper.lookup_player = AsyncMock()
    scraper.lookup_multiple_players = AsyncMock()
    scraper.format_player_stats = MagicMock(return_value="Formatted HS stats")
    return scraper


# ==================== HELPER FUNCTIONS ====================

def create_mock_recruit(
    name: str,
    position: str = "QB",
    stars: int = 4,
    rating: float = 92.5,
    is_transfer: bool = False,
    committed_to: Optional[str] = None
) -> Dict[str, Any]:
    """Helper to create mock recruit data"""
    return {
        "name": name,
        "position": position,
        "stars": stars,
        "rating": rating,
        "national_rank": 50,
        "position_rank": 5,
        "state_rank": 3,
        "height": "6-2",
        "weight": "195",
        "high_school": "Test High School",
        "city": "Test City",
        "state": "TX",
        "year": 2026,
        "is_transfer": is_transfer,
        "committed_to": committed_to,
        "offers": ["Alabama", "Georgia", "Ohio State"],
        "top_predictions": [
            {"team": "Alabama", "prediction": "85%"},
            {"team": "Georgia", "prediction": "10%"}
        ],
        "profile_url": f"https://www.on3.com/db/{name.lower().replace(' ', '-')}/",
        "image_url": "https://example.com/player.jpg"
    }


def create_mock_cfb_player(
    name: str,
    team: str = "Washington",
    position: str = "QB",
    jersey: int = 12
) -> Dict[str, Any]:
    """Helper to create mock CFB player data"""
    return {
        "name": name,
        "team": team,
        "position": position,
        "jersey": jersey,
        "stats": {
            "2024": {
                "passing": {"YDS": 3500, "TD": 30, "INT": 8},
                "rushing": {"CAR": 50, "YDS": 200, "TD": 3}
            },
            "2023": {
                "passing": {"YDS": 2800, "TD": 24, "INT": 10}
            }
        }
    }


def create_mock_hs_player(
    name: str,
    school: str = "Test High School",
    position: str = "QB",
    state: str = "TX"
) -> Dict[str, Any]:
    """Helper to create mock HS player data"""
    return {
        "name": name,
        "school": school,
        "position": position,
        "state": state,
        "seasons": [
            {
                "year": "2024",
                "passing": {"yards": 3200, "touchdowns": 35, "interceptions": 5},
                "rushing": {"yards": 400, "touchdowns": 8}
            }
        ],
        "career": {
            "passing": {"yards": 8500, "touchdowns": 90},
            "rushing": {"yards": 1200, "touchdowns": 20}
        }
    }
