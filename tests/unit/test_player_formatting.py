#!/usr/bin/env python3
"""
Snapshot tests for player response formatting (utils/cfb_data.py).

format_player_response was one 378-line function; it's now an orchestrator over
_player_identity_lines / _player_transfer_lines / _player_stats_lines /
_player_recruiting_lines. These snapshots pin the output so the split (and any
later edit) can't quietly change what Discord shows.
"""

import pytest

from cfb_bot.utils.cfb_data import cfb_data

CASES = [
    {},
    None,
    {'player': {'name': 'Jaden Rashada', 'team': 'Georgia', 'position': 'QB', 'height': 75,
                'weight': 200, 'year': 'SO', 'jersey': 5, 'homeCity': 'Pittsburg',
                'homeState': 'CA', 'homeCountry': 'USA'}},
    {'player': {'firstName': 'Kai', 'lastName': 'Trump', 'team': 'Miami', 'position': 'RB',
                'height': "6'1", 'homeCity': 'Berlin', 'homeCountry': 'Germany'},
     'transfer': {'origin': 'Texas', 'destination': 'Miami', 'eligibility': 'Immediate'},
     'stats': {2025: {'passing': {'COMPLETIONS': '200', 'ATT': 300, 'YDS': '2500', 'TD': 20, 'INT': '5', 'LONG': 60},
                      'rushing': {'CAR': 50, 'YDS': 300, 'TD': 3, 'LONG': 22},
                      'receiving': {'REC': 10, 'YDS': 150, 'TD': 1}},
               2024: {'defensive': {'TOT': 40, 'SOLO': 25, 'SACKS': 3.5, 'INT': 2}}},
     'recruiting': {'stars': 4, 'rating': 0.9712, 'ranking': 45, 'positionRank': 5, 'stateRank': 3,
                    'year': 2024, 'school': 'Miami', 'city': 'Berlin', 'state': None, 'country': 'Germany',
                    'high_school': 'Berlin International', 'height': 73, 'weight': 190,
                    'position': 'RB', 'early_signing': True, 'early_enroll': False}},
    {'player': {'name': 'No Stats Guy', 'team': 'Rutgers'}, 'stats': {}, 'recruiting': {'stars': 0}},]

EXPECTED = [
    "Couldn't find that player, mate. Check the spelling or try another name.",
    "Couldn't find that player, mate. Check the spelling or try another name.",
    "🏈 **Jaden Rashada** - Georgia\n**Position:** QB | **#**5 | **Year:** SO | **6'3\"** | **200lbs**\n📍 Pittsburg, CA\n\n📊 *No stats available*",
    "🏈 **Kai Trump** - Miami\n**Position:** RB | **6'1**\n📍 Berlin, Germany\n\n🔄 **Transfer:** Texas → Miami\n   Eligibility: Immediate\n\n📊 **2025 Season:**\n   🏈 200/300 (66.7%) | 2500 YDS (8.3 YPA) | 20 TD | 5 INT | 60 Long\n   🏃 50 CAR | 300 YDS (6.0 YPC) | 3 TD | 22 Long\n   🎯 10 REC | 150 YDS (15.0 YPR) | 1 TD\n\n\n🎯 **Recruiting (2024 Class):** ⭐⭐⭐⭐ (0.9712)\n   **Rankings:** #45 National | #5 RB | #3 State\n   **Signed With:** Miami\n   **Hometown:** Berlin, Germany\n   **High School:** Berlin International\n   **Recruiting Vitals:** 6'1\" | 190lbs\n   **Status:** Early Signing Period",
    "🏈 **No Stats Guy** - Rutgers\n**Position:** Unknown\n\n📊 *No stats available*\n\n🎯 **Recruiting (N/A Class):** N/R"
]


@pytest.mark.parametrize("player_info,expected", zip(CASES, EXPECTED))
def test_format_player_response(player_info, expected):
    assert cfb_data.format_player_response(player_info) == expected


def test_section_helpers_are_independent():
    """Each helper returns only its own lines, and nothing for missing data."""
    assert cfb_data._player_transfer_lines(None) == []
    assert cfb_data._player_recruiting_lines(None) == []
    assert cfb_data._player_identity_lines({'name': 'Solo', 'team': 'Cal'})[0].endswith('**Solo** - Cal')
    assert cfb_data._season_stat_lines({}) == []
