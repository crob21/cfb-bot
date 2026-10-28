#!/usr/bin/env python3
"""The 247Sports search must honor the position filter for duplicate names."""

from unittest.mock import AsyncMock

import pytest

from cfb_bot.utils.recruiting_scraper import RecruitingScraper

RANKINGS_PAGE = """
<ul>
  <li><a href="/player/joe-smith-111">Joe Smith</a></li>
  <li><a href="/player/joe-smith-222">Joe Smith</a></li>
</ul>
"""

PROFILES = {
    "https://247sports.com/player/joe-smith-111": {"name": "Joe Smith", "position": "QB"},
    "https://247sports.com/player/joe-smith-222": {"name": "Joe Smith", "position": "WR"},
}


def _scraper():
    s = RecruitingScraper.__new__(RecruitingScraper)
    s._fetch_page = AsyncMock(side_effect=lambda url: RANKINGS_PAGE if "Page=" not in url else None)
    s._scrape_player_profile = AsyncMock(side_effect=lambda url, year: PROFILES.get(url))
    return s


@pytest.mark.asyncio
async def test_skips_same_name_at_the_wrong_position():
    url, _ = await _scraper()._search_composite_rankings("Joe Smith", 2027, max_pages=2, position_filter="wr")
    assert url.endswith("joe-smith-222")


@pytest.mark.asyncio
async def test_first_match_wins_without_a_filter():
    url, _ = await _scraper()._search_composite_rankings("Joe Smith", 2027, max_pages=2)
    assert url.endswith("joe-smith-111")


@pytest.mark.asyncio
async def test_no_player_at_that_position_finds_nothing():
    url, _ = await _scraper()._search_composite_rankings("Joe Smith", 2027, max_pages=2, position_filter="RB")
    assert url is None


def test_position_matches():
    assert RecruitingScraper._position_matches({"position": "WR"}, None)
    assert RecruitingScraper._position_matches({"position": "wr"}, "WR")
    assert not RecruitingScraper._position_matches({"position": "QB"}, "WR")
