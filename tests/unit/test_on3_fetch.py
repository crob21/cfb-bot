"""On3's fetch chain: a block or error moves on to the next method, a 404 stops."""

import base64
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.utils import on3_scraper as mod

GOOD = "<html><body>on3 recruit page</body></html>"
BLOCKED = "<html><body>Just a moment...</body></html>"


@pytest.fixture
def scraper():
    s = mod.On3Scraper.__new__(mod.On3Scraper)
    s._rate_limit = AsyncMock()
    s._user_agents = ['ua']
    s._user_agent_index = 0
    s._headers = {}
    s._is_blocked = False
    s._zyte_request_count = 0
    s._zyte_cost_per_1k = 0.233
    s._fetch_playwright = AsyncMock(return_value=None)
    s._fetch_cloudscraper = AsyncMock(return_value=None)
    s._fetch_zyte = AsyncMock(return_value=None)
    s._fetch_httpx = AsyncMock(return_value=None)
    return s


class TestChain:
    async def test_first_success_wins(self, scraper):
        scraper._fetch_playwright.return_value = GOOD
        assert await scraper._fetch_page("u") == GOOD
        scraper._fetch_cloudscraper.assert_not_awaited()

    async def test_a_block_moves_on_to_zyte(self, scraper):
        scraper._fetch_zyte.return_value = GOOD
        assert await scraper._fetch_page("u") == GOOD

    async def test_an_error_moves_on(self, scraper):
        scraper._fetch_cloudscraper.side_effect = ConnectionError("reset")
        scraper._fetch_zyte.return_value = GOOD
        assert await scraper._fetch_page("u") == GOOD

    async def test_httpx_after_zyte_fails(self, scraper):
        scraper._fetch_zyte.side_effect = RuntimeError("zyte down")
        scraper._fetch_httpx.return_value = GOOD
        assert await scraper._fetch_page("u") == GOOD

    async def test_404_stops(self, scraper):
        scraper._fetch_playwright.return_value = mod.PAGE_MISSING
        assert await scraper._fetch_page("u") is None
        scraper._fetch_zyte.assert_not_awaited()

    async def test_all_fail(self, scraper):
        assert await scraper._fetch_page("u") is None


class TestPageResult:
    @pytest.fixture
    def s(self):
        s = mod.On3Scraper.__new__(mod.On3Scraper)
        s._is_blocked = False
        return s

    def test_ok(self, s):
        assert s._page_result('x', 200, GOOD) == GOOD

    def test_block_page(self, s):
        assert s._page_result('x', 200, BLOCKED) is None

    def test_forbidden_marks_blocked(self, s):
        assert s._page_result('x', 403, '') is None
        assert s._is_blocked

    def test_missing(self, s):
        assert s._page_result('x', 404, '') is mod.PAGE_MISSING


class TestZyte:
    async def test_zyte_page_isnt_block_checked_and_cost_is_recorded(self):
        s = mod.On3Scraper.__new__(mod.On3Scraper)
        s._is_blocked = False
        s._zyte_request_count = 0
        s._zyte_cost_per_1k = 0.233
        page = "<html>on3 with cloudflare scripts</html>"
        s._zyte_client = SimpleNamespace(get=AsyncMock(
            return_value={"httpResponseBody": base64.b64encode(page.encode()).decode()}))
        tracker = MagicMock(is_zyte_over_limit=AsyncMock(return_value=False), record_cost=AsyncMock())
        with patch('cfb_bot.utils.cost_tracker.get_cost_tracker', return_value=tracker):
            assert await s._fetch_zyte("u") == page
        tracker.record_cost.assert_awaited_once()

    async def test_zyte_skipped_over_spend_limit(self):
        s = mod.On3Scraper.__new__(mod.On3Scraper)
        s._zyte_client = SimpleNamespace(get=AsyncMock())
        tracker = MagicMock(is_zyte_over_limit=AsyncMock(return_value=True))
        with patch('cfb_bot.utils.cost_tracker.get_cost_tracker', return_value=tracker):
            assert await s._fetch_zyte("u") is None
        s._zyte_client.get.assert_not_awaited()


class TestPlaywright:
    async def test_page_closed_even_when_goto_throws(self):
        s = mod.On3Scraper.__new__(mod.On3Scraper)
        page = MagicMock(goto=AsyncMock(side_effect=TimeoutError()), close=AsyncMock())
        s._browser = object()
        s._browser_context = MagicMock(new_page=AsyncMock(return_value=page))
        with patch.object(mod, 'PLAYWRIGHT_AVAILABLE', True), pytest.raises(TimeoutError):
            await s._fetch_playwright("u")
        page.close.assert_awaited_once()
