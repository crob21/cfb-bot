#!/usr/bin/env python3
"""
On3/Rivals Recruiting Scraper

Scrapes recruiting data from On3/Rivals including:
- Player rankings and ratings
- Team recruiting class rankings
- Commitment tracking

Note: This uses web scraping since On3 has no public API.
Site structure changes may require updates to this module.

On3 data is server-side rendered, making it reliable to scrape.
"""

import asyncio
import logging
import os
import random
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

# Playwright for Cloudflare bypass (best option)
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Cloudflare bypass fallback
try:
    import cloudscraper
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    CLOUDSCRAPER_AVAILABLE = False

# Zyte API for premium scraping (guaranteed bypass)
ZYTE_AVAILABLE = False
ZYTE_IMPORT_ERROR = None
try:
    from zyte_api import AsyncZyteAPI as ZyteAPIClient  # v0.8+ uses AsyncZyteAPI
    ZYTE_AVAILABLE = True
except ImportError as e:
    ZYTE_IMPORT_ERROR = f"ImportError: {e}"
except Exception as e:
    ZYTE_IMPORT_ERROR = f"Exception: {e}"

# Fuzzy matching for player name typos
try:
    from rapidfuzz import fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False

logger = logging.getLogger('CFB26Bot.On3Recruiting')


class On3Scraper:
    """Scraper for On3/Rivals recruiting data"""

    BASE_URL = "https://www.on3.com"

    # Search URL - searches by name with class year filter
    SEARCH_URL = "https://www.on3.com/rivals/search/?searchText={name}&minClassYear={year}"
    # Broader search without class year filter (for transfer portal)
    SEARCH_URL_ALL = "https://www.on3.com/rivals/search/?searchText={name}"

    # Rankings pages
    PLAYER_RANKINGS_URL = "https://www.on3.com/rivals/rankings/player/football/{year}/"
    TEAM_RANKINGS_URL = "https://www.on3.com/rivals/rankings/industry-team/football/{year}/"
    POSITION_RANKINGS_URL = "https://www.on3.com/rivals/rankings/player/football/{year}/?position={position}"
    STATE_RANKINGS_URL = "https://www.on3.com/rivals/rankings/player/football/{year}/?state={state}"

    # Player profile URL pattern
    PLAYER_PROFILE_URL = "https://www.on3.com/rivals/{slug}/"

    # Position mapping
    POSITIONS = {
        'QB': 'qb', 'RB': 'rb', 'WR': 'wr', 'TE': 'te',
        'OT': 'ot', 'OG': 'iOL', 'C': 'iOL', 'OL': 'ot', 'IOL': 'iOL',
        'EDGE': 'edge', 'DT': 'dl', 'DE': 'edge', 'DL': 'dl',
        'LB': 'lb', 'CB': 'cb', 'S': 's', 'ATH': 'ath'
    }

    # State abbreviations
    STATES = {
        'AL': 'alabama', 'AK': 'alaska', 'AZ': 'arizona', 'AR': 'arkansas',
        'CA': 'california', 'CO': 'colorado', 'CT': 'connecticut', 'DE': 'delaware',
        'FL': 'florida', 'GA': 'georgia', 'HI': 'hawaii', 'ID': 'idaho',
        'IL': 'illinois', 'IN': 'indiana', 'IA': 'iowa', 'KS': 'kansas',
        'KY': 'kentucky', 'LA': 'louisiana', 'ME': 'maine', 'MD': 'maryland',
        'MA': 'massachusetts', 'MI': 'michigan', 'MN': 'minnesota', 'MS': 'mississippi',
        'MO': 'missouri', 'MT': 'montana', 'NE': 'nebraska', 'NV': 'nevada',
        'NH': 'new-hampshire', 'NJ': 'new-jersey', 'NM': 'new-mexico', 'NY': 'new-york',
        'NC': 'north-carolina', 'ND': 'north-dakota', 'OH': 'ohio', 'OK': 'oklahoma',
        'OR': 'oregon', 'PA': 'pennsylvania', 'RI': 'rhode-island', 'SC': 'south-carolina',
        'SD': 'south-dakota', 'TN': 'tennessee', 'TX': 'texas', 'UT': 'utah',
        'VT': 'vermont', 'VA': 'virginia', 'WA': 'washington', 'WV': 'west-virginia',
        'WI': 'wisconsin', 'WY': 'wyoming', 'DC': 'district-of-columbia'
    }

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(hours=1)  # Cache for 1 hour
        self._cache_max_size = 500  # Max cache entries before cleanup
        self._last_request = datetime.min
        self._rate_limit_delay_min = 1.0  # Minimum 1 second between requests
        self._rate_limit_delay_max = 2.5  # Maximum 2.5 seconds (randomized)
        self._is_blocked = False  # Track if we're currently blocked

        # Playwright browser (best for Cloudflare)
        self._playwright = None
        self._browser = None
        self._browser_context = None

        # Cloudscraper fallback
        if CLOUDSCRAPER_AVAILABLE:
            self._scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'darwin',
                    'desktop': True
                }
            )
        else:
            self._scraper = None

        # Zyte API (premium fallback - guaranteed to work)
        self._zyte_client = None
        self._zyte_request_count = 0  # Track Zyte API usage
        self._zyte_cost_per_1k = 0.233  # Cost per 1,000 requests

        if ZYTE_AVAILABLE:
            logger.info(f"🔍 Zyte API library available (AsyncZyteAPI imported successfully)")
            zyte_api_key = os.getenv('ZYTE_API_KEY')
            logger.info(f"🔍 Environment variable check: ZYTE_API_KEY={'SET' if zyte_api_key else 'NOT SET'}")
            if zyte_api_key:
                try:
                    self._zyte_client = ZyteAPIClient(api_key=zyte_api_key)
                    logger.info("✅ Zyte API initialized (premium Cloudflare bypass available)")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize Zyte API: {e}", exc_info=True)
            else:
                logger.warning("⚠️ ZYTE_API_KEY environment variable not set - premium bypass unavailable")
        else:
            if ZYTE_IMPORT_ERROR:
                logger.warning(f"⚠️ zyte-api import failed: {ZYTE_IMPORT_ERROR}")
            else:
                logger.warning("⚠️ zyte-api library not installed - premium bypass unavailable")

        # HTTP headers for fallback httpx client
        # Rotate user agents to reduce detection
        self._user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]
        self._user_agent_index = 0

        self._headers = {
            'User-Agent': self._user_agents[0],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        # Log scraping method
        if PLAYWRIGHT_AVAILABLE:
            logger.info("✅ Playwright available - will use headless browser for Cloudflare bypass")
        elif CLOUDSCRAPER_AVAILABLE:
            logger.info("⚠️ Using cloudscraper (Playwright not available)")
        else:
            logger.warning("⚠️ Using httpx only - may encounter Cloudflare blocks")

    def _get_current_recruiting_year(self) -> int:
        """Get the current recruiting class year"""
        now = datetime.now()
        # Recruiting classes are for the following year until February
        if now.month >= 2:
            return now.year + 1
        return now.year

    def _rating_to_stars(self, rating: float) -> int:
        """Convert On3 rating to star value (consistent thresholds)"""
        if rating >= 98:
            return 5
        elif rating >= 90:
            return 4
        elif rating >= 80:
            return 3
        elif rating >= 70:
            return 2
        else:
            return 1

    async def _init_browser(self):
        """Initialize Playwright browser if not already running"""
        if not PLAYWRIGHT_AVAILABLE:
            return False

        if self._browser:
            return True  # Already initialized

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                ]
            )
            self._browser_context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            logger.info("🌐 Playwright browser initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize Playwright: {e}")
            return False

    async def _close_browser(self):
        """Clean up Playwright browser"""
        try:
            if self._browser_context:
                await self._browser_context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("🌐 Playwright browser closed")
        except Exception as e:
            logger.warning(f"⚠️ Error closing browser: {e}")
        finally:
            self._browser = None
            self._browser_context = None
            self._playwright = None

    async def _rate_limit(self):
        """Enforce rate limiting between requests with randomized delays"""
        now = datetime.now()
        elapsed = (now - self._last_request).total_seconds()

        # Use randomized delay to appear more human-like
        delay = random.uniform(self._rate_limit_delay_min, self._rate_limit_delay_max)

        # If we were recently blocked, add extra delay
        if self._is_blocked:
            delay += random.uniform(2.0, 5.0)
            logger.info(f"⏳ Adding extra delay due to previous block ({delay:.1f}s)")

        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_request = datetime.now()

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if still valid"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < self._cache_ttl:
                logger.debug(f"Cache hit for {key}")
                return data
        return None

    def _set_cached(self, key: str, data: Any):
        """Cache data with timestamp, with automatic cleanup"""
        # Cleanup old entries if cache is getting large
        if len(self._cache) >= self._cache_max_size:
            self._cleanup_cache()
        self._cache[key] = (data, datetime.now())

    def _cleanup_cache(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self._cache.items()
            if now - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page with rate limiting and Cloudflare bypass (Playwright > Cloudscraper > httpx)"""
        await self._rate_limit()

        # Rotate user agent to reduce detection
        self._user_agent_index = (self._user_agent_index + 1) % len(self._user_agents)
        self._headers['User-Agent'] = self._user_agents[self._user_agent_index]

        try:
            logger.info(f"🔍 Fetching: {url}")

            # PRIORITY 1: Use Playwright (best for Cloudflare)
            if PLAYWRIGHT_AVAILABLE:
                # Initialize browser if needed
                if not self._browser:
                    await self._init_browser()

                if self._browser_context:
                    try:
                        page = await self._browser_context.new_page()

                        # Navigate to URL with timeout
                        response = await page.goto(url, timeout=15000, wait_until='domcontentloaded')

                        if response and response.status == 200:
                            # Wait a bit for any JS to execute
                            await page.wait_for_timeout(1000)

                            html = await page.content()
                            await page.close()

                            # Check for blocking
                            if self._check_if_blocked(html):
                                logger.error(f"🚫 BLOCKED by On3 even with Playwright!")
                                return None

                            logger.debug(f"✅ Playwright fetch successful")
                            return html
                        elif response and response.status == 404:
                            await page.close()
                            logger.warning(f"⚠️ Page not found: {url}")
                            return None
                        else:
                            await page.close()
                            status = response.status if response else "unknown"
                            logger.warning(f"⚠️ Playwright returned status {status}, trying fallback...")
                            # Fall through to cloudscraper
                    except Exception as e:
                        logger.warning(f"⚠️ Playwright error: {e}, trying fallback...")
                        # Fall through to cloudscraper

            # PRIORITY 2: Use cloudscraper if Playwright failed/unavailable
            if self._scraper and CLOUDSCRAPER_AVAILABLE:
                # Run sync cloudscraper in thread pool to keep async
                response = await asyncio.to_thread(self._scraper.get, url, timeout=15)

                if response.status_code == 200:
                    html = response.text
                    # Check for blocking indicators
                    if self._check_if_blocked(html):
                        logger.warning(f"⚠️ BLOCKED by On3 with cloudscraper, trying Zyte...")
                        # Don't return None yet - fall through to Zyte
                    else:
                        logger.debug(f"✅ Cloudscraper fetch successful")
                        return html
                elif response.status_code == 403:
                    logger.warning(f"⚠️ BLOCKED (403 Forbidden) with cloudscraper, trying Zyte...")
                    self._is_blocked = True
                    # Fall through to Zyte
                elif response.status_code == 429:
                    logger.warning(f"⚠️ RATE LIMITED (429) with cloudscraper, trying Zyte...")
                    self._is_blocked = True
                    # Fall through to Zyte
                elif response.status_code == 404:
                    logger.warning(f"⚠️ Page not found: {url}")
                    return None
                else:
                    logger.warning(f"⚠️ HTTP {response.status_code} with cloudscraper, trying Zyte...")
                    # Fall through to Zyte

            # PRIORITY 3: Use Zyte API (premium, guaranteed bypass)
            if self._zyte_client:
                try:
                    # Increment usage counter
                    self._zyte_request_count += 1
                    estimated_cost = (self._zyte_request_count * self._zyte_cost_per_1k) / 1000

                    logger.info(f"💰 Using Zyte API for: {url}")
                    logger.info(f"💳 Zyte usage: {self._zyte_request_count} requests | Est. cost: ${estimated_cost:.4f}")

                    # Make async request to Zyte
                    response = await self._zyte_client.get({
                        "url": url,
                        "httpResponseBody": True,
                        "httpResponseHeaders": True
                    })

                    # Decode the response
                    import base64
                    html = base64.b64decode(response["httpResponseBody"]).decode('utf-8')

                    if html and '<html' in html.lower():
                        logger.info(f"✅ Zyte API fetch successful (bypassed Cloudflare)")
                        self._is_blocked = False  # Clear blocked status
                        return html
                    else:
                        logger.error(f"❌ Zyte returned invalid HTML")
                        # Fall through to httpx as last resort

                except Exception as e:
                    logger.error(f"❌ Zyte API error: {e}")
                    # Fall through to httpx as last resort

            # PRIORITY 4: Fallback to httpx (will likely be blocked)
            else:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    response = await client.get(url, headers=self._headers)

                    if response.status_code == 200:
                        html = response.text
                        if self._check_if_blocked(html):
                            logger.error(f"🚫 BLOCKED by On3! Install Playwright: pip install playwright && playwright install chromium")
                            return None
                        logger.debug(f"✅ httpx fetch successful")
                        return html
                    elif response.status_code == 403:
                        logger.error(f"🚫 BLOCKED (403 Forbidden)")
                        self._is_blocked = True
                        return None
                    elif response.status_code == 429:
                        logger.error(f"🚫 RATE LIMITED (429)")
                        self._is_blocked = True
                        return None
                    elif response.status_code == 404:
                        logger.warning(f"⚠️ Page not found: {url}")
                        return None
                    else:
                        logger.error(f"❌ HTTP {response.status_code}")
                        return None

        except Exception as e:
            logger.error(f"❌ Error fetching {url}: {e}")
            return None

    def _check_if_blocked(self, html: str) -> bool:
        """Check if the response indicates we've been blocked"""
        block_indicators = [
            'captcha',
            'blocked',
            'access denied',
            'please verify you are human',
            'too many requests',
            'rate limit',
            'cloudflare',
            'challenge-platform',
            'just a moment',  # Cloudflare waiting page
        ]
        html_lower = html.lower()
        for indicator in block_indicators:
            if indicator in html_lower:
                logger.warning(f"⚠️ Block indicator found: '{indicator}'")
                self._is_blocked = True  # Set flag for increased delays
                return True

        # If we got valid content, clear the blocked flag
        if '<html' in html_lower and 'on3' in html_lower:
            self._is_blocked = False
        return False

    def is_blocked(self) -> bool:
        """Check if On3 is currently blocking requests"""
        return self._is_blocked

    def clear_block_status(self):
        """Manually clear the blocked status (e.g., after waiting)"""
        self._is_blocked = False
        logger.info("✅ Block status cleared - will try normal request timing")

    def get_zyte_usage(self) -> Dict[str, Any]:
        """Get Zyte API usage statistics (current session)"""
        estimated_cost = (self._zyte_request_count * self._zyte_cost_per_1k) / 1000
        return {
            'request_count': self._zyte_request_count,
            'estimated_cost': estimated_cost,
            'cost_per_1k': self._zyte_cost_per_1k,
            'is_available': self._zyte_client is not None
        }

    async def get_zyte_usage_from_api(self, days: int = 30) -> Optional[Dict[str, Any]]:
        """Query Zyte Stats API for official usage statistics

        Args:
            days: Number of days to look back (default 30)

        Returns:
            Dictionary with usage data or None if unavailable

        Note: Requires ZYTE_DASHBOARD_API_KEY (different from ZYTE_API_KEY!) and ZYTE_ORG_ID.
              Get your dashboard API key from: https://app.zyte.com/o/YOUR_ORG_ID/settings/apikeys
        """
        # Stats API requires the DASHBOARD API key (different from regular API key!)
        dashboard_api_key = os.getenv('ZYTE_DASHBOARD_API_KEY')
        org_id = os.getenv('ZYTE_ORG_ID')

        if not dashboard_api_key:
            logger.debug("⚠️ Zyte Stats API not configured - ZYTE_DASHBOARD_API_KEY missing")
            logger.debug("   Get your dashboard API key from: https://app.zyte.com/o/YOUR_ORG_ID/settings/apikeys")
            return None

        if not org_id:
            logger.debug("⚠️ Zyte Stats API not configured - ZYTE_ORG_ID missing")
            return None

        try:
            from datetime import datetime, timedelta

            # Calculate date range (ISO 8601 datetime format required)
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)

            # Zyte Stats API uses ISO 8601 datetime format
            params = {
                'organization_id': org_id,
                'start_time': start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'end_time': end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            }

            logger.info(f"📊 Querying Zyte Stats API (org_id: {org_id}, {days} days)...")
            logger.debug(f"   API endpoint: https://zyte-api-stats.zyte.com/api/stats")
            logger.debug(f"   Params: {params}")

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://zyte-api-stats.zyte.com/api/stats',
                    params=params,
                    auth=(dashboard_api_key, ''),  # HTTP Basic Auth with dashboard API key
                    timeout=10.0
                )

                logger.info(f"   Response status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Retrieved Zyte usage data")
                    return data
                elif response.status_code == 401:
                    logger.error(f"❌ Zyte Stats API: Authentication failed - check ZYTE_API_KEY")
                    logger.error(f"   Response: {response.text}")
                    return None
                elif response.status_code == 404:
                    logger.error(f"❌ Zyte Stats API: Organization not found - check ZYTE_ORG_ID ({org_id})")
                    logger.error(f"   Response: {response.text}")
                    return None
                else:
                    logger.warning(f"⚠️ Zyte Stats API error: {response.status_code}")
                    logger.warning(f"   Response: {response.text}")
                    return None

        except httpx.TimeoutException:
            logger.error(f"❌ Zyte Stats API timeout (10s)")
            return None
        except Exception as e:
            logger.error(f"❌ Error querying Zyte Stats API: {e}")
            logger.exception("Full traceback:")
            return None

    def reset_zyte_usage(self):
        """Reset Zyte usage counter (for tracking periods)"""
        old_count = self._zyte_request_count
        old_cost = (old_count * self._zyte_cost_per_1k) / 1000
        self._zyte_request_count = 0
        logger.info(f"🔄 Zyte usage reset: {old_count} requests (${old_cost:.4f}) → 0 requests ($0.00)")
        return old_count, old_cost

    async def search_recruit(
        self,
        name: str,
        year: Optional[int] = None,
        max_pages: int = 20,  # Kept for API compatibility, not used in On3
        position: Optional[str] = None  # Filter by position for duplicate names
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a recruit by name

        Args:
            name: Player name to search
            year: Recruiting class year (defaults to current)
            max_pages: Ignored for On3 (kept for API compatibility)
            position: Optional position filter (e.g., 'WR', 'QB') for duplicate names

        Returns:
            Recruit info dictionary with profile data or None
        """
        if not year:
            year = self._get_current_recruiting_year()

        cache_key = f"on3:recruit:{name.lower()}:{year}"
        cached = self._get_cached(cache_key)
        if cached:
            logger.info(f"📦 Cache hit for '{name}' (year {year})")
            return cached

        logger.info(f"🔍 Searching On3 for: '{name}' (default year: {year})")

        # Build search strategies:
        # 1. Full name with class year (high school recruits)
        # 2. Full name without year (transfer portal)
        # 3. Last name only with year (handles first name typos)
        # 4. Last name only without year (transfers with first name typos)
        name_parts = name.strip().split()
        last_name = name_parts[-1] if name_parts else name

        search_urls = [
            (self.SEARCH_URL.format(name=quote_plus(name), year=year), f"class {year}", name),
            (self.SEARCH_URL_ALL.format(name=quote_plus(name)), "all players (including transfers)", name),
        ]

        # Add last-name-only searches if name has multiple parts
        if len(name_parts) >= 2:
            search_urls.extend([
                (self.SEARCH_URL.format(name=quote_plus(last_name), year=year), f"class {year} (last name)", name),
                (self.SEARCH_URL_ALL.format(name=quote_plus(last_name)), "all players (last name)", name),
            ])

        profile_url = None
        player_name = None
        is_transfer = False

        for search_url, search_type, search_name in search_urls:
            logger.info(f"🔍 Trying search: {search_type}")
            html = await self._fetch_page(search_url)

            if not html:
                logger.warning(f"⚠️ No HTML returned for {search_type} search")
                continue

            try:
                soup = BeautifulSoup(html, 'html.parser')

                # Find player links in search results
                # On3 uses links like /rivals/gavin-day-248989/
                # Use broader selector and filter manually (BeautifulSoup $= can be unreliable)
                all_links = soup.select('a[href*="/rivals/"]')
                player_links = [link for link in all_links if link.get('href', '').endswith('/')]
                logger.debug(f"Found {len(player_links)} player links in search results ({search_type})")

                name_lower = name.lower()
                name_parts = name_lower.split()

                logger.info(f"📋 Found {len(player_links)} player links to check for '{name}'")

                # Track best fuzzy match
                best_fuzzy_match = None
                best_fuzzy_score = 0

                # Track matches with position filtering
                exact_matches = []  # (href, link_text, is_transfer)
                fuzzy_matches = []  # (href, link_text, score, is_transfer)

                for link in player_links:
                    link_text = link.get_text(strip=True)
                    href = link.get('href', '')

                    # Skip non-player links
                    if '/rivals/search' in href or '/rivals/rankings' in href or '/rivals/join' in href:
                        continue

                    # Match if the link contains a player-like slug pattern
                    if not re.search(r'/rivals/[\w-]+-\d+/', href):
                        continue

                    # Log each candidate link for debugging
                    logger.debug(f"  📎 Candidate: '{link_text}' -> {href}")

                    link_text_lower = link_text.lower()

                    # Check for exact match - flexible matching (case insensitive)
                    exact_match = all(
                        any(part in word or word.startswith(part) for word in link_text_lower.split())
                        for part in name_parts
                    )

                    if exact_match:
                        # Track if this came from the broader search (likely transfer portal)
                        is_transfer_flag = (search_type == "all players (including transfers)")
                        exact_matches.append((href, link_text, is_transfer_flag))
                        logger.debug(f"✅ Exact match candidate: {link_text} -> {href}")

                    # Fuzzy matching for typos (e.g., "Daylon" vs "Daylan")
                    if FUZZY_AVAILABLE and not exact_match:
                        # Split into parts to check first AND last name
                        search_parts = name_lower.split()
                        result_parts = link_text_lower.split()

                        # Only consider if both have at least 2 parts (first + last)
                        if len(search_parts) >= 2 and len(result_parts) >= 2:
                            # Check first name similarity
                            first_score = fuzz.ratio(search_parts[0], result_parts[0])
                            # Check last name similarity
                            last_score = fuzz.ratio(search_parts[-1], result_parts[-1])

                            # BOTH first AND last name must be reasonably similar (>= 70%)
                            # This prevents "Emmanuel Karnley" matching "Emmanuel Poag"
                            if first_score >= 70 and last_score >= 70:
                                # Overall score is average of both
                                score = (first_score + last_score) // 2

                                if score >= 75:  # 75% overall threshold
                                    is_transfer_flag = (search_type == "all players (including transfers)")
                                    fuzzy_matches.append((href, link_text, score, is_transfer_flag))
                                    logger.debug(f"🔍 Fuzzy candidate: {link_text} (first:{first_score}%, last:{last_score}%, avg:{score}%)")

                # Now filter by position if specified
                chosen_match = None
                if exact_matches or fuzzy_matches:
                    # Prefer exact matches over fuzzy
                    candidates = exact_matches if exact_matches else []

                    # If position filter is specified, try to find match with that position
                    if position and candidates:
                        logger.info(f"🎯 Filtering {len(candidates)} matches by position: {position}")
                        # We need to fetch each candidate's profile to check position
                        # For now, just pick the first exact match (position check comes after profile fetch)
                        # TODO: Could optimize by checking position in search results if available

                    if candidates:
                        href, link_text, is_transfer_flag = candidates[0]
                        chosen_match = (href, link_text, is_transfer_flag)
                    elif fuzzy_matches:
                        # Pick best fuzzy match
                        fuzzy_matches.sort(key=lambda x: x[2], reverse=True)
                        href, link_text, score, is_transfer_flag = fuzzy_matches[0]
                        chosen_match = (href, link_text, is_transfer_flag)
                        logger.info(f"✅ Using fuzzy match ({score}%): {link_text}")

                if chosen_match:
                    href, link_text, is_transfer_flag = chosen_match
                    profile_url = href
                    player_name = link_text
                    is_transfer = is_transfer_flag

                    if not profile_url.startswith('http'):
                        profile_url = self.BASE_URL + profile_url

                    logger.info(f"✅ Selected profile: {player_name} -> {profile_url}")
                    break  # Found a match, stop searching

            except Exception as e:
                logger.error(f"Error parsing search results: {e}")
                continue

        if not profile_url:
            logger.info(f"❌ No profile found for {name} ({year})")
            return None

        # If we have multiple exact matches, fetch all their profiles and return as list
        all_candidates = exact_matches if exact_matches else []
        if len(all_candidates) > 1:
            total_found = len(all_candidates)
            logger.info(f"🔍 Found {total_found} players named '{name}' - fetching up to 5 profiles")
            candidates = []
            for href, link_text, is_transfer_flag in all_candidates[:5]:  # Limit to 5 to avoid Discord limits
                candidate_url = href if href.startswith('http') else self.BASE_URL + href
                recruit = await self._scrape_player_profile(candidate_url, year)
                if recruit:
                    if is_transfer_flag:
                        recruit['is_transfer'] = True
                        recruit['status'] = recruit.get('status') or 'Transfer'
                    candidates.append(recruit)
            
            # Filter by position if specified
            if position and candidates:
                position_upper = position.upper()
                filtered = [c for c in candidates if (c.get('position') or '').upper() == position_upper]
                if filtered:
                    logger.info(f"🎯 Filtered to {len(filtered)} candidate(s) with position {position}")
                    candidates = filtered
                else:
                    logger.warning(f"⚠️ No candidates found with position {position}, showing all")

            if len(candidates) > 1:
                # Return multiple candidates for user to choose
                return {
                    "multiple": True,
                    "candidates": candidates,
                    "query_name": name,
                    "total_found": total_found  # How many total before limiting to 5
                }
            elif candidates:
                # Only one profile successfully loaded (or filtered to one)
                recruit = candidates[0]
                self._set_cached(cache_key, recruit)
                return recruit

        # Scrape the profile page for full details
        recruit = await self._scrape_player_profile(profile_url, year)

        if recruit:
            # Mark if this is a transfer portal player
            if is_transfer:
                recruit['is_transfer'] = True
                recruit['status'] = recruit.get('status') or 'Transfer'

            # Check position filter if specified
            if position:
                recruit_pos = (recruit.get('position') or '').upper()
                if recruit_pos != position.upper():
                    logger.warning(f"⚠️ Position mismatch: Found {player_name} but position is {recruit_pos}, not {position}")
                    logger.info(f"💡 Tip: This might be a different player with the same name")
                    # Still return the recruit, but log the warning

            self._set_cached(cache_key, recruit)

        return recruit

    async def _scrape_player_profile(self, profile_url: str, year: int) -> Optional[Dict[str, Any]]:
        """
        Scrape a player's full On3/Rivals profile page

        Args:
            profile_url: Full URL to player profile
            year: Recruiting class year

        Returns:
            Detailed recruit data dictionary
        """
        html = await self._fetch_page(profile_url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()

            recruit = {
                'name': None,
                'year': year,
                'stars': None,
                'rating': None,
                'rating_on3': None,
                'national_rank': None,
                'position_rank': None,
                'state_rank': None,
                'position': None,
                'height': None,
                'weight': None,
                'city': None,
                'state': None,
                'high_school': None,
                'committed_to': None,
                'commitment_date': None,
                'status': 'Uncommitted',
                'nil_value': None,
                'offers': [],           # List of schools that offered
                'top_predictions': [],  # Top predictions with percentages
                'visits': [],           # Official/unofficial visits
                'image_url': None,      # Player profile photo
                'profile_url': profile_url,
                'source': 'On3/Rivals',
                # Transfer portal fields
                'is_transfer': False,
                'previous_school': None,
                'college_experience': None,
                'portal_rating': None,
                'portal_entry_date': None
            }

            # Player name - from h1 or title (get this first for image fallback)
            name_elem = soup.select_one('h1')
            if name_elem:
                recruit['name'] = name_elem.get_text(strip=True)

            # Try to get player image from og:image meta tag (most reliable)
            og_image = soup.select_one('meta[property="og:image"]')
            if og_image and og_image.get('content'):
                recruit['image_url'] = og_image.get('content')
            elif recruit.get('name'):
                # Fallback: look for player photo in gallery using first name
                first_name = recruit['name'].split()[0] if recruit['name'] else ''
                if first_name:
                    player_imgs = soup.select(f'img[alt*="{first_name}"]')
                    for img in player_imgs:
                        src = img.get('src', '')
                        # Skip small thumbnails and avatars
                        if 'on3static' in src and 'avatar' not in src.lower() and 'logo' not in src.lower():
                            recruit['image_url'] = src
                            break

            # Try to extract data from structured elements
            # On3 uses definition lists and compact text (no spaces)

            # Height - On3 format: "Ht6-3" or "Height6-3"
            height_match = re.search(r'(?:Ht|Height)\s*[:\s]?([\d]+-[\d.]+)', page_text)
            if height_match:
                recruit['height'] = height_match.group(1)

            # Weight - On3 format: "Wt190" or "Weight190"
            weight_match = re.search(r'(?:Wt|Weight)\s*[:\s]?(\d{2,3})', page_text)
            if weight_match:
                recruit['weight'] = weight_match.group(1)

            # Position - On3 format: "PosS" or "PosCB"
            pos_match = re.search(r'(?:Pos|Position)\s*[:\s]?(QB|RB|WR|TE|OT|OG|C|DL|DT|DE|EDGE|LB|CB|S|ATH|IOL|OL)', page_text)
            if pos_match:
                recruit['position'] = pos_match.group(1)

            # High School - look for high school name
            hs_match = re.search(r'High School([A-Za-z\s\-\.\']+?)(?:\s*\(|Hometown|$)', page_text)
            if hs_match:
                recruit['high_school'] = hs_match.group(1).strip()

            # Hometown - format: (City, ST)
            hometown_match = re.search(r'\(([A-Za-z\s\-\.\']+),\s*([A-Z]{2})\)', page_text)
            if hometown_match:
                recruit['city'] = hometown_match.group(1).strip()
                recruit['state'] = hometown_match.group(2)

            # Class year - On3 format: "Class2026" or just "2026"
            class_match = re.search(r'(?:Class|H\.S\.)\s*[:\s]?(\d{4})', page_text)
            if class_match:
                recruit['year'] = int(class_match.group(1))

            # Rating - On3 format: numbers like "91.84" (no word boundaries needed)
            # Pattern matches after state code like "NV91.84" followed by rank digits
            rating_match = re.search(r'[A-Z]{2}(\d{2}\.\d{2})\d{1,4}', page_text)
            if rating_match:
                recruit['rating'] = float(rating_match.group(1))
                recruit['rating_on3'] = recruit['rating']
            else:
                # Fallback: simple decimal pattern
                rating_match = re.search(r'(\d{2}\.\d{2})', page_text)
                if rating_match:
                    recruit['rating'] = float(rating_match.group(1))
                    recruit['rating_on3'] = recruit['rating']

            # Stars - derive from rating or look for "X Stars" link text
            stars_link = soup.select_one('a[href*="rankings"][href*="industry"]')
            if stars_link:
                stars_text = stars_link.get_text(strip=True)
                stars_match = re.search(r'(\d)\s*[Ss]tars?', stars_text)
                if stars_match:
                    recruit['stars'] = int(stars_match.group(1))

            # If no stars found, estimate from rating
            if not recruit['stars'] and recruit['rating']:
                recruit['stars'] = self._rating_to_stars(recruit['rating'])

            # National rank - On3 format: "Natl189" (the number right after state)
            # Better: look for the link to rankings page with the rank number
            rank_links = soup.select('a[href*="/rivals/rankings/"]')
            for link in rank_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')
                # National rank link usually just has a number
                if link_text.isdigit() and 'industry-player' in href and 'position' not in href and 'state' not in href:
                    recruit['national_rank'] = int(link_text)
                    break

            # Position rank
            if recruit['position']:
                pos_rank_match = re.search(rf"(?:Pos|{recruit['position']})\s*[:\s#]*(\d+)", page_text)
                if pos_rank_match:
                    recruit['position_rank'] = int(pos_rank_match.group(1))

            # State rank
            if recruit['state']:
                state_rank_match = re.search(rf"(?:St|{recruit['state']})\s*[:\s#]*(\d+)", page_text)
                if state_rank_match:
                    recruit['state_rank'] = int(state_rank_match.group(1))

            # NIL value - On3 shows this as $X.XM or $XXXk
            nil_match = re.search(r'\$(\d+(?:\.\d+)?[MKmk])', page_text)
            if nil_match:
                recruit['nil_value'] = nil_match.group(0)

            # Commitment status - look for school images/links or status text
            if 'Signed' in page_text:
                recruit['status'] = 'Signed'
            elif 'Committed' in page_text:
                recruit['status'] = 'Committed'
            elif 'Enrolled' in page_text:
                recruit['status'] = 'Enrolled'

            # Try to find committed school from college links
            # Look for the first college link that's part of status/commitment info
            player_name_lower = recruit.get('name', '').lower()
            college_links = soup.select('a[href*="/college/"]')
            for link in college_links:
                href = link.get('href', '')
                # Skip generic college links, look for specific team pages
                if '/football/' in href or href.endswith('/'):
                    # Get school name from image alt text first (more reliable)
                    school_name = None
                    img = link.select_one('img')
                    if img and img.get('alt'):
                        alt_text = img.get('alt', '')
                        # Clean up alt text - remove "Avatar", "logo", etc.
                        school_name = alt_text.replace(' Avatar', '').replace(' logo', '').replace('Visit ', '').strip()

                    # Fallback to link text only if it's short (school names, not headlines)
                    if not school_name:
                        link_text = link.get_text(strip=True)
                        # Only use if it looks like a school name (short, no "commits to", etc.)
                        if link_text and len(link_text) < 30 and 'commit' not in link_text.lower() and 'star' not in link_text.lower():
                            school_name = link_text

                    # Filter out generic names, headlines, and THE PLAYER'S OWN NAME
                    if school_name and len(school_name) > 2 and len(school_name) < 50:
                        school_name_lower = school_name.lower()
                        # Skip if it's the player's name or contains their name
                        if player_name_lower and (player_name_lower in school_name_lower or school_name_lower in player_name_lower):
                            continue
                        # Skip common player name patterns (first last format)
                        if len(school_name.split()) == 2 and school_name.split()[0][0].isupper() and school_name.split()[1][0].isupper():
                            # Could be a person's name - check if it looks like a school
                            known_school_words = ['state', 'university', 'college', 'tech', 'a&m', 'ole miss', 'notre dame', 'usc', 'ucla', 'ohio', 'michigan', 'alabama', 'georgia', 'texas', 'florida', 'oregon', 'washington', 'clemson', 'oklahoma', 'lsu', 'auburn', 'tennessee', 'penn', 'iowa', 'wisconsin', 'minnesota', 'indiana', 'purdue', 'illinois', 'nebraska', 'colorado', 'arizona', 'utah', 'stanford', 'cal', 'berkeley', 'baylor', 'tcu', 'kansas', 'missouri', 'arkansas', 'kentucky', 'vanderbilt', 'south carolina', 'mississippi', 'carolina']
                            if not any(word in school_name_lower for word in known_school_words):
                                continue
                        if school_name not in ['College', 'NCAA', 'Avatar', 'Teams', 'All Teams']:
                            recruit['committed_to'] = school_name
                            if recruit['status'] == 'Uncommitted':
                                recruit['status'] = 'Committed'
                            break

            # Parse commitment date
            commit_date_match = re.search(r'Commitment Date\s*(\d{1,2}/\d{1,2}/\d{2,4})', page_text)
            if commit_date_match:
                recruit['commitment_date'] = commit_date_match.group(1)

            # ==================== PARSE TOP TEAMS (OFFERS & PREDICTIONS) ====================
            # On3 doesn't use standard tables for Top Teams - extract from page text
            # Pattern: "SchoolNameSigned/Offered[Date]Percentage%"

            # First, get list of college links to know which schools are mentioned
            college_names = []
            college_links = soup.select('a[href*="/college/"]')
            for link in college_links:
                name = link.get_text(strip=True)
                # Also check image alt text
                img = link.select_one('img')
                if img and img.get('alt'):
                    alt_name = img.get('alt', '').replace(' Avatar', '').replace(' logo', '').strip()
                    if alt_name and alt_name not in college_names and len(alt_name) > 2:
                        college_names.append(alt_name)
                if name and name not in college_names and len(name) > 2 and name not in ['Teams', 'All Teams', 'Avatar']:
                    college_names.append(name)

            # Now find offers and predictions from page text
            # Pattern: "SchoolName(Signed|Offered|Committed)[Date]Percentage%"
            for school in college_names:
                # Look for this school in the page text with status
                school_pattern = re.compile(
                    rf'{re.escape(school)}(Signed|Offered|Committed)(\d{{1,2}}/\d{{1,2}}/\d{{2,4}})?(\d{{1,3}}\.?\d*%|<1%)?',
                    re.IGNORECASE
                )
                match = school_pattern.search(page_text)
                if match:
                    status = match.group(1)
                    # date = match.group(2)  # Not used currently
                    prediction = match.group(3)

                    # Add to offers
                    if school not in recruit['offers']:
                        recruit['offers'].append(school)

                    # Add to predictions (top 5)
                    if prediction and len(recruit['top_predictions']) < 5:
                        recruit['top_predictions'].append({
                            'team': school,
                            'prediction': prediction,
                            'status': status.title()
                        })

            # ==================== PARSE VISITS ====================
            # Look for Visit Center section
            visit_section = soup.find(text=re.compile(r'Visit Center', re.I))
            if visit_section:
                # Find the parent container and look for visit table
                visit_container = visit_section.find_parent(['div', 'section', 'generic'])
                if visit_container:
                    visit_rows = visit_container.select('tr, [role="row"]')

                    for row in visit_rows:
                        row_text = row.get_text()

                        # Skip header rows
                        if 'School' in row_text and 'Date' in row_text and 'Visit Type' in row_text:
                            continue

                        cells = row.select('td, [role="cell"]')
                        if len(cells) >= 3:
                            # Get school name
                            school_cell = cells[0]
                            school_name = school_cell.get_text(strip=True)

                            # Clean up school name (remove "Avatar" prefix if present)
                            school_name = re.sub(r'^.*Avatar\s*', '', school_name).strip()

                            # Get date
                            date_cell = cells[1]
                            visit_date = date_cell.get_text(strip=True)

                            # Get visit type
                            type_cell = cells[2]
                            visit_type = type_cell.get_text(strip=True)

                            if school_name and visit_date:
                                recruit['visits'].append({
                                    'school': school_name,
                                    'date': visit_date,
                                    'type': visit_type
                                })

            # Fallback: try to parse visits from page text patterns
            if not recruit['visits']:
                # Pattern: "SCHOOL DATE Official/Unofficial"
                visit_pattern = re.compile(
                    r'([A-Z]{2,5})\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+(Official|Unofficial)',
                    re.IGNORECASE
                )
                for match in visit_pattern.finditer(page_text):
                    recruit['visits'].append({
                        'school': match.group(1),
                        'date': match.group(2),
                        'type': match.group(3)
                    })

            # ==================== TRANSFER PORTAL DETECTION ====================
            # Check for "Transfer Portal" section which indicates a college transfer
            # On3 shows: "Transfer Portal (SHSU)" with previous school, experience years
            # IMPORTANT: Must find "Transfer Portal" in player's context, not sidebars
            # AND must have actual portal-specific data (not just enrollment dates)

            is_portal_player = False
            prev_school = None
            college_exp = None
            portal_rating = None
            portal_entry = None

            # PRIMARY CHECK: "Transfer Portal (SCHOOL)" pattern - DEFINITIVE
            prev_school_match = re.search(r'Transfer Portal\s*\(([^)]+)\)', page_text)
            if prev_school_match:
                is_portal_player = True
                prev_school = prev_school_match.group(1)

            # SECONDARY CHECK: "Transfer Portal Rating" - DEFINITIVE
            portal_rating_match = re.search(r'Transfer Portal Rating\s*(\d{2}\.\d{2})', page_text)
            if portal_rating_match:
                is_portal_player = True
                portal_rating = float(portal_rating_match.group(1))

            # TERTIARY CHECK: "Entered" date ONLY if near "Transfer Portal" text
            # (Not just any "Entered" date - that could be enrollment date)
            if 'Transfer Portal' in page_text:
                # Look for "Transfer Portal...Entered" within ~200 chars
                portal_section_match = re.search(r'Transfer Portal.{0,200}?Entered\s*[-–]\s*(\d{1,2}/\d{1,2}/\d{2,4})', page_text, re.DOTALL)
                if portal_section_match:
                    is_portal_player = True
                    portal_entry = portal_section_match.group(1)

            # Only process additional fields if confirmed as portal player
            if is_portal_player:
                recruit['is_transfer'] = True
                recruit['previous_school'] = prev_school
                recruit['portal_rating'] = portal_rating
                recruit['portal_entry_date'] = portal_entry

                # Get college experience years
                exp_match = re.search(r'Experience\s*(\d{4})\s*[-–]\s*(\d{4})', page_text)
                if exp_match:
                    recruit['college_experience'] = f"{exp_match.group(1)}-{exp_match.group(2)}"

                # Try additional patterns for previous school if not found
                if not recruit['previous_school']:
                    prev_match2 = re.search(r'(?:Previous|Prev\.?)\s*School[:\s]+([A-Za-z\s&]+?)(?:\s*\||\s*$|\s*\d)', page_text)
                    if prev_match2:
                        recruit['previous_school'] = prev_match2.group(1).strip()

            logger.info(f"✅ Scraped profile: {recruit['name']} ({recruit['position']}) - {recruit['stars']}⭐ | {len(recruit['offers'])} offers, {len(recruit['visits'])} visits" + (" | 🌀 PORTAL" if recruit.get('is_transfer') else ""))
            return recruit

        except Exception as e:
            logger.error(f"❌ Error parsing player profile: {e}", exc_info=True)
            return None

    async def get_top_recruits(
        self,
        year: Optional[int] = None,
        position: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Get top recruits with optional filters

        Args:
            year: Recruiting class year
            position: Filter by position (QB, WR, etc.)
            state: Filter by state (TX, CA, etc.)
            limit: Number of recruits to return

        Returns:
            List of recruit dictionaries
        """
        if not year:
            year = self._get_current_recruiting_year()

        # Determine which URL to use
        if position:
            pos_mapped = self.POSITIONS.get(position.upper(), position.lower())
            url = self.POSITION_RANKINGS_URL.format(year=year, position=pos_mapped)
            cache_key = f"on3:top_recruits:{year}:pos:{pos_mapped}"
        elif state:
            state_mapped = self.STATES.get(state.upper(), state.lower())
            url = self.STATE_RANKINGS_URL.format(year=year, state=state_mapped)
            cache_key = f"on3:top_recruits:{year}:state:{state_mapped}"
        else:
            url = self.PLAYER_RANKINGS_URL.format(year=year)
            cache_key = f"on3:top_recruits:{year}:all"

        cached = self._get_cached(cache_key)
        if cached:
            return cached[:limit]

        html = await self._fetch_page(url)
        if not html:
            return []

        try:
            soup = BeautifulSoup(html, 'html.parser')
            recruits = []

            # On3 rankings use table rows
            rows = soup.select('tr, [role="row"]')

            for row in rows:
                if len(recruits) >= limit:
                    break

                # Find player link
                player_link = row.select_one('a[href*="/rivals/"][href$="/"]')
                if not player_link:
                    continue

                href = player_link.get('href', '')
                if '/rivals/rankings' in href or '/rivals/search' in href:
                    continue

                player_name = player_link.get_text(strip=True)
                if not player_name:
                    continue

                row_text = row.get_text()

                recruit = {
                    'name': player_name,
                    'year': year,
                    'stars': None,
                    'rating': None,
                    'national_rank': len(recruits) + 1,
                    'position_rank': None,
                    'state_rank': None,
                    'position': None,
                    'height': None,
                    'weight': None,
                    'city': None,
                    'state': None,
                    'high_school': None,
                    'committed_to': None,
                    'status': 'Uncommitted',
                    'profile_url': self.BASE_URL + href if not href.startswith('http') else href,
                    'source': 'On3/Rivals'
                }

                # Extract position
                pos_match = re.search(r'\b(QB|RB|WR|TE|OT|OG|C|DL|DT|DE|EDGE|LB|CB|S|ATH|IOL|OL)\b', row_text)
                if pos_match:
                    recruit['position'] = pos_match.group(1)

                # Extract rating
                rating_match = re.search(r'\b(\d{2}\.\d{2})\b', row_text)
                if rating_match:
                    recruit['rating'] = float(rating_match.group(1))

                # Extract stars
                stars_match = re.search(r'(\d)\s*[Ss]tars?', row_text)
                if stars_match:
                    recruit['stars'] = int(stars_match.group(1))
                elif recruit['rating']:
                    # Use consistent star thresholds across all methods
                    recruit['stars'] = self._rating_to_stars(recruit['rating'])

                # Extract height/weight
                height_match = re.search(r'(\d-\d+(?:\.\d)?)', row_text)
                if height_match:
                    recruit['height'] = height_match.group(1)

                weight_match = re.search(r'/\s*(\d{2,3})\b', row_text)
                if weight_match:
                    recruit['weight'] = weight_match.group(1)

                # Extract hometown
                hometown_match = re.search(r'\(([A-Za-z\s\-\.\']+),\s*([A-Z]{2})\)', row_text)
                if hometown_match:
                    recruit['city'] = hometown_match.group(1).strip()
                    recruit['state'] = hometown_match.group(2)

                # Check commitment
                if 'Signed' in row_text:
                    recruit['status'] = 'Signed'
                elif 'Committed' in row_text:
                    recruit['status'] = 'Committed'

                # Find committed school
                school_img = row.select_one('img[alt*="Avatar"], img[alt*="logo"]')
                if school_img:
                    alt = school_img.get('alt', '')
                    if alt and 'Avatar' in alt:
                        school = alt.replace(' Avatar', '').replace(' logo', '')
                        if school:
                            recruit['committed_to'] = school

                recruits.append(recruit)

            self._set_cached(cache_key, recruits)
            logger.info(f"✅ Found {len(recruits)} top recruits from On3")
            return recruits[:limit]

        except Exception as e:
            logger.error(f"❌ Error parsing top recruits: {e}", exc_info=True)
            return []

    async def get_team_recruiting_class(
        self,
        team: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a team's recruiting class

        Args:
            team: Team name
            year: Recruiting class year

        Returns:
            Team recruiting class info
        """
        if not year:
            year = self._get_current_recruiting_year()

        cache_key = f"on3:team_class:{team.lower()}:{year}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        url = self.TEAM_RANKINGS_URL.format(year=year)
        html = await self._fetch_page(url)

        if not html:
            return None

        try:
            soup = BeautifulSoup(html, 'html.parser')
            page_text = soup.get_text()

            # Find team in rankings
            team_lower = team.lower()

            # Look for team rows - On3 uses listitem elements, not table rows
            rows = soup.select('listitem, li, tr, [role="row"]')
            logger.debug(f"Found {len(rows)} potential team rows")

            for row in rows:
                row_text = row.get_text()

                if team_lower not in row_text.lower():
                    continue

                team_data = {
                    'team': team,
                    'year': year,
                    'rank': None,
                    'total_commits': None,
                    'avg_rating': None,
                    '5_stars': 0,
                    '4_stars': 0,
                    '3_stars': 0,
                    'points': None,
                    'avg_nil': None,
                    'source': 'On3/Rivals'
                }

                # Try to extract team name properly
                team_link = row.select_one('a[href*="/college/"]')
                if team_link:
                    team_data['team'] = team_link.get_text(strip=True)

                # On3 structure: h6 for rank, p tags for stars/commits, h6 for rating/NIL
                # Rank - first h6 or heading in the row
                headings = row.select('h6, [role="heading"]')
                if headings:
                    first_heading_text = headings[0].get_text(strip=True)
                    if first_heading_text.isdigit():
                        team_data['rank'] = int(first_heading_text)

                    # Average rating - usually a heading with format XX.XX
                    for h in headings:
                        h_text = h.get_text(strip=True)
                        if re.match(r'^\d{2}\.\d{2}$', h_text):
                            team_data['avg_rating'] = float(h_text)
                        elif h_text.startswith('$'):
                            team_data['avg_nil'] = h_text

                # Star counts and total - look for paragraphs with numbers
                paragraphs = row.select('p')
                numbers = []
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if p_text.isdigit():
                        numbers.append(int(p_text))
                    elif re.match(r'^\d+\.\d+$', p_text):
                        # This might be the score
                        team_data['points'] = float(p_text)

                # On3 shows: 5-star, 4-star, 3-star, total (in that order)
                if len(numbers) >= 4:
                    team_data['5_stars'] = numbers[0]
                    team_data['4_stars'] = numbers[1]
                    team_data['3_stars'] = numbers[2]
                    team_data['total_commits'] = numbers[3]
                elif len(numbers) >= 1:
                    # At least get the last number as total
                    team_data['total_commits'] = numbers[-1]

                # Fallback: try regex on full text
                if not team_data['rank']:
                    rank_match = re.search(r'^(\d+)\b', row_text.strip())
                    if rank_match:
                        team_data['rank'] = int(rank_match.group(1))

                if not team_data['avg_rating']:
                    avg_match = re.search(r'(\d{2}\.\d{2})', row_text)
                    if avg_match:
                        team_data['avg_rating'] = float(avg_match.group(1))

                self._set_cached(cache_key, team_data)
                logger.info(f"✅ Found team class: {team_data['team']} (Rank #{team_data['rank']})")
                return team_data

            logger.info(f"❌ Team not found: {team}")
            return None

        except Exception as e:
            logger.error(f"❌ Error parsing team class: {e}", exc_info=True)
            return None

    async def get_team_commits(
        self,
        team: str,
        year: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a team's committed recruits list

        Args:
            team: Team name (e.g., 'Washington', 'Ohio State')
            year: Recruiting class year

        Returns:
            Dict with team info and list of commits
        """
        if not year:
            year = self._get_current_recruiting_year()

        cache_key = f"on3:team_commits:{team.lower()}:{year}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # First, find the team's slug from the rankings page
        rankings_url = self.TEAM_RANKINGS_URL.format(year=year)
        html = await self._fetch_page(rankings_url)

        if not html:
            return None

        try:
            soup = BeautifulSoup(html, 'html.parser')
            team_lower = team.lower()

            # Find the link to the team's commits page
            commits_url = None
            team_name_found = None

            # Look for all links that contain the commits URL pattern
            all_links = soup.select('a[href*="/industry-comparison-commits/"]')

            for link in all_links:
                link_text = link.get_text(strip=True)
                href = link.get('href', '')

                if team_lower in link_text.lower():
                    commits_url = href
                    team_name_found = link_text
                    if not commits_url.startswith('http'):
                        commits_url = self.BASE_URL + commits_url
                    logger.info(f"✅ Found commits URL for {team_name_found}: {commits_url}")
                    break

            if not commits_url:
                logger.info(f"❌ No commits page found for: {team}")
                return None

            # Fetch the commits page
            commits_html = await self._fetch_page(commits_url)
            if not commits_html:
                return None

            commits_soup = BeautifulSoup(commits_html, 'html.parser')

            # Parse team summary info
            result = {
                'team': team_name_found or team,
                'year': year,
                'commits_url': commits_url,
                'commits': [],
                'total_commits': 0,
                'avg_rating': None,
                'rank': None,
                'source': 'On3/Rivals'
            }

            # Get team rank from page
            rank_elem = commits_soup.select_one('definition:contains("th"), [class*="Rank"]')
            rank_text = commits_soup.get_text()
            rank_match = re.search(r'Current Rank\s*(\d+)', rank_text)
            if rank_match:
                result['rank'] = int(rank_match.group(1))

            # Get average rating
            rating_match = re.search(r'Current Rating\s*([\d.]+)', rank_text)
            if rating_match:
                result['avg_rating'] = float(rating_match.group(1))

            # Get total commits count
            commits_match = re.search(r'Commits:\s*"?(\d+)"?', rank_text)
            if commits_match:
                result['total_commits'] = int(commits_match.group(1))

            # Parse individual commits from table rows
            rows = commits_soup.select('row, tr, [role="row"]')
            logger.debug(f"Found {len(rows)} potential commit rows")

            for row in rows:
                row_text = row.get_text()

                # Skip header rows
                if 'Player' in row_text and 'Status' in row_text and 'Industry Rating' in row_text:
                    continue

                # Look for player link
                player_link = row.select_one('a[href*="/rivals/"][href$="/"]')
                if not player_link:
                    continue

                # Skip non-player links
                href = player_link.get('href', '')
                if '/rankings/' in href or '/search/' in href or '/join/' in href:
                    continue

                player_name = player_link.get_text(strip=True)
                if not player_name or player_name in ['Player', 'Status', 'Industry Rating']:
                    continue

                commit = {
                    'name': player_name,
                    'profile_url': self.BASE_URL + href if not href.startswith('http') else href,
                    'position': None,
                    'height': None,
                    'weight': None,
                    'high_school': None,
                    'location': None,
                    'rating': None,
                    'stars': 0,
                    'national_rank': None,
                    'position_rank': None,
                    'state_rank': None,
                    'status': None,
                    'status_date': None,
                    'is_transfer': False,
                    'previous_school': None
                }

                # Position - look for common position abbreviations
                # Pattern: "Position AbbreviationOTHeight" (no spaces)
                pos_match = re.search(r'Position Abbreviation([A-Z]{1,4})(?:Height|Weight|/)', row_text)
                if pos_match:
                    commit['position'] = pos_match.group(1)
                else:
                    # Fallback: look for position in specific context (H.S. YYYY/POS/)
                    # Avoid matching "S" from "Status" by excluding single S
                    pos_fallback = re.search(r'H\.S\.\s*\d{4}[\s/]*([A-Z]{2,4})[\s/]*Height', row_text)
                    if pos_fallback:
                        commit['position'] = pos_fallback.group(1)
                    else:
                        # Last resort: look for multi-char positions only
                        pos_last = re.search(r'\b(QB|RB|WR|TE|OT|OG|IOL|EDGE|DL|DT|DE|LB|CB|ATH)\b', row_text)
                        if pos_last:
                            commit['position'] = pos_last.group(1)

                # Height and weight
                hw_match = re.search(r'Height\s*([\d]+-[\d]+)/\s*Weight\s*"?(\d+)"?', row_text)
                if hw_match:
                    commit['height'] = hw_match.group(1)
                    commit['weight'] = hw_match.group(2)

                # High school and location
                hs_link = row.select_one('a[href*="/high-school/"]')
                if hs_link:
                    commit['high_school'] = hs_link.get_text(strip=True)
                    # Location is usually right after in parentheses
                    hs_parent = hs_link.parent
                    if hs_parent:
                        loc_match = re.search(r'\(([^)]+)\)', hs_parent.get_text())
                        if loc_match:
                            commit['location'] = loc_match.group(1)

                # Industry rating - look for pattern like "96.58"
                rating_pattern = re.search(r'Industry Rating.*?(\d{2}\.\d{2})', row_text)
                if not rating_pattern:
                    # Try just the number pattern after ratings context
                    ratings_cell = row.select_one('[class*="Rating"], [class*="rating"]')
                    if ratings_cell:
                        r_match = re.search(r'(\d{2}\.\d{2})', ratings_cell.get_text())
                        if r_match:
                            commit['rating'] = float(r_match.group(1))
                else:
                    commit['rating'] = float(rating_pattern.group(1))

                # If no rating found, try to find any XX.XX pattern
                if not commit['rating']:
                    any_rating = re.findall(r'\b(\d{2}\.\d{2})\b', row_text)
                    if any_rating:
                        # First one is usually industry rating
                        commit['rating'] = float(any_rating[0])

                # Calculate stars from rating
                if commit['rating']:
                    commit['stars'] = self._rating_to_stars(commit['rating'])

                # Rankings - Natl., Pos., St.
                natl_match = re.search(r'Natl\.\s*(\d+)', row_text)
                if natl_match:
                    commit['national_rank'] = int(natl_match.group(1))

                pos_rank_match = re.search(r'Pos\.\s*(\d+)', row_text)
                if pos_rank_match:
                    commit['position_rank'] = int(pos_rank_match.group(1))

                state_rank_match = re.search(r'St\.\s*(\d+)', row_text)
                if state_rank_match:
                    commit['state_rank'] = int(state_rank_match.group(1))

                # Status (Signed/Committed) and date
                if 'Signed' in row_text:
                    commit['status'] = 'Signed'
                elif 'Committed' in row_text:
                    commit['status'] = 'Committed'

                date_match = re.search(r'Status Date\s*([\d/]+)', row_text)
                if date_match:
                    commit['status_date'] = date_match.group(1)

                # Transfer detection from team commits page:
                # 1. Check for "TR" indicator after rating (Transfer Rating)
                # 2. Check if H.S. year is earlier than recruiting class year
                if re.search(r'\d{2}\.\d{2}\s*TR\b', row_text) or re.search(r'\bTR\b', row_text):
                    commit['is_transfer'] = True

                # Also check H.S. year - if it's earlier than the recruiting class, it's a transfer
                hs_year_match = re.search(r'H\.S\.\s*(\d{4})', row_text)
                if hs_year_match:
                    hs_year = int(hs_year_match.group(1))
                    commit['hs_class_year'] = hs_year
                    # If their HS year is earlier than recruiting class, they're a transfer
                    if hs_year < year:
                        commit['is_transfer'] = True

                result['commits'].append(commit)

            # Update total if we didn't get it from page text
            if not result['total_commits']:
                result['total_commits'] = len(result['commits'])

            # Sort commits by rating (highest first)
            result['commits'].sort(key=lambda x: x.get('rating') or 0, reverse=True)

            self._set_cached(cache_key, result)
            logger.info(f"✅ Found {len(result['commits'])} commits for {result['team']}")
            return result

        except Exception as e:
            logger.error(f"❌ Error getting team commits: {e}", exc_info=True)
            return None

    async def get_team_rankings(self, year: Optional[int] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Get top team recruiting class rankings

        Args:
            year: Recruiting class year
            limit: Number of teams to return

        Returns:
            List of team recruiting class data
        """
        if not year:
            year = self._get_current_recruiting_year()

        cache_key = f"on3:team_rankings:{year}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached[:limit]

        url = self.TEAM_RANKINGS_URL.format(year=year)
        html = await self._fetch_page(url)

        if not html:
            return []

        try:
            soup = BeautifulSoup(html, 'html.parser')
            teams = []

            # On3 uses listitem/li elements, not table rows
            rows = soup.select('listitem, li, tr, [role="row"]')
            logger.debug(f"Found {len(rows)} potential team rows")

            for row in rows:
                if len(teams) >= limit:
                    break

                # Look for team links with commits URL pattern
                team_link = row.select_one('a[href*="/industry-comparison-commits/"]')
                if not team_link:
                    # Fallback to college links
                    team_link = row.select_one('a[href*="/college/"]')
                if not team_link:
                    continue

                team_name = team_link.get_text(strip=True)
                if not team_name or len(team_name) < 2:
                    continue

                # Skip header/navigation elements
                skip_names = ['teams', 'team', 'school', 'college', 'rank', 'commits', 'rating', 'points']
                if team_name.lower() in skip_names:
                    continue

                row_text = row.get_text()

                team_data = {
                    'team': team_name,
                    'year': year,
                    'rank': len(teams) + 1,
                    'total_commits': None,
                    'avg_rating': None,
                    'points': None,
                    'source': 'On3/Rivals'
                }

                # Average rating (format: 92.45)
                avg_match = re.search(r'(\d{2}\.\d{2})', row_text)
                if avg_match:
                    team_data['avg_rating'] = float(avg_match.group(1))

                # Commits count
                commits_match = re.search(r'(\d{1,2})\s*(?:commits?|total)', row_text, re.IGNORECASE)
                if commits_match:
                    team_data['total_commits'] = int(commits_match.group(1))

                teams.append(team_data)

            self._set_cached(cache_key, teams)
            logger.info(f"✅ Found {len(teams)} team rankings from On3")
            return teams[:limit]

        except Exception as e:
            logger.error(f"❌ Error parsing team rankings: {e}", exc_info=True)
            return []

    def format_recruit(self, recruit: Dict[str, Any]) -> str:
        """Format a single recruit for display"""
        if not recruit:
            return "❌ Recruit not found"

        lines = []

        # Name and basic info
        name = recruit.get('name', 'Unknown')
        stars = recruit.get('stars')
        star_display = '⭐' * stars if stars else ''
        position = recruit.get('position', '')
        year = recruit.get('year', '')

        lines.append(f"**{name}** {star_display}")
        if position:
            lines.append(f"📍 **{position}** | Class of **{year}**")
        lines.append("")

        # Ratings section
        lines.append("**📊 Ratings**")
        if recruit.get('rating'):
            lines.append(f"• On3/Rivals: **{recruit['rating']}**")
        lines.append("")

        # Rankings section
        lines.append("**🏆 Rankings**")
        rank_lines = []

        natl = recruit.get('national_rank')
        if natl:
            rank_lines.append(f"• National: **#{natl}**")

        pos_rank = recruit.get('position_rank')
        if pos_rank:
            rank_lines.append(f"• {position}: **#{pos_rank}**")

        state = recruit.get('state', '')
        state_rank = recruit.get('state_rank')
        if state_rank:
            rank_lines.append(f"• {state}: **#{state_rank}**")

        if rank_lines:
            lines.extend(rank_lines)
        else:
            lines.append("• _Rankings not available_")
        lines.append("")

        # Physical & Location
        lines.append("**📏 Profile**")
        physical = []
        if recruit.get('height'):
            physical.append(f"**{recruit['height']}**")
        if recruit.get('weight'):
            physical.append(f"**{recruit['weight']} lbs**")
        if physical:
            lines.append(f"• Size: {' / '.join(physical)}")

        if recruit.get('city') and recruit.get('state'):
            lines.append(f"• Hometown: {recruit['city']}, {recruit['state']}")
        if recruit.get('high_school'):
            lines.append(f"• High School: {recruit['high_school']}")

        # NIL value if available
        if recruit.get('nil_value'):
            lines.append(f"• NIL Value: **{recruit['nil_value']}**")
        lines.append("")

        # Transfer Portal section (if applicable)
        if recruit.get('is_transfer'):
            lines.append("**🌀 Transfer Portal**")
            if recruit.get('previous_school'):
                lines.append(f"• Previous School: **{recruit['previous_school']}**")
            if recruit.get('college_experience'):
                lines.append(f"• College Experience: **{recruit['college_experience']}**")
            if recruit.get('portal_entry_date'):
                lines.append(f"• Entered Portal: **{recruit['portal_entry_date']}**")
            if recruit.get('portal_rating'):
                lines.append(f"• Portal Rating: **{recruit['portal_rating']}**")
            lines.append("")

        # Commitment status
        if recruit.get('committed_to'):
            status = recruit.get('status', 'Committed')
            commit_date = recruit.get('commitment_date')
            if commit_date:
                lines.append(f"✅ **{status} to {recruit['committed_to']}** ({commit_date})")
            else:
                lines.append(f"✅ **{status} to {recruit['committed_to']}**")
        else:
            lines.append("🔮 **Uncommitted**")

        # Predictions (if uncommitted or has predictions)
        predictions = recruit.get('top_predictions', [])
        if predictions:
            lines.append("")
            lines.append("**🔮 Predictions**")
            for pred in predictions[:5]:  # Top 5
                team = pred.get('team', 'Unknown')
                pct = pred.get('prediction', '?')
                status = pred.get('status', '')
                status_emoji = "✅" if status == 'Signed' else "📝" if status == 'Committed' else ""
                lines.append(f"• {team}: **{pct}** {status_emoji}")

        # Offers
        offers = recruit.get('offers', [])
        if offers:
            lines.append("")
            offer_count = len(offers)
            lines.append(f"**📋 Offers ({offer_count})**")
            # Show first 8 offers, truncate if more
            display_offers = offers[:8]
            lines.append(f"• {', '.join(display_offers)}")
            if offer_count > 8:
                lines.append(f"• _...and {offer_count - 8} more_")

        # Visits
        visits = recruit.get('visits', [])
        if visits:
            lines.append("")
            lines.append("**✈️ Visits**")
            for visit in visits[:5]:  # Top 5 visits
                school = visit.get('school', 'Unknown')
                date = visit.get('date', '?')
                vtype = visit.get('type', '')
                type_emoji = "🏛️" if vtype == 'Official' else "👀"
                lines.append(f"• {type_emoji} {school} - {date} ({vtype})")

        # Note: Profile URL is added separately in bot.py to appear after college stats

        return '\n'.join(lines)

    def format_team_class(self, team_data: Dict[str, Any]) -> str:
        """Format team recruiting class for display"""
        if not team_data:
            return "❌ Team not found"

        lines = []

        team = team_data.get('team', 'Unknown')
        rank = team_data.get('rank', '?')
        year = team_data.get('year', '')

        lines.append(f"**{team}** - #{rank} Nationally ({year})")
        lines.append("")

        if team_data.get('total_commits'):
            lines.append(f"👥 **{team_data['total_commits']}** Commits")

        if team_data.get('avg_rating'):
            lines.append(f"📊 Avg Rating: **{team_data['avg_rating']:.2f}**")

        if team_data.get('avg_nil'):
            lines.append(f"💰 Avg NIL: **{team_data['avg_nil']}**")

        if team_data.get('points'):
            lines.append(f"🏆 Score: **{team_data['points']:.2f}**")

        stars = []
        if team_data.get('5_stars'):
            stars.append(f"⭐⭐⭐⭐⭐ {team_data['5_stars']}")
        if team_data.get('4_stars'):
            stars.append(f"⭐⭐⭐⭐ {team_data['4_stars']}")
        if team_data.get('3_stars'):
            stars.append(f"⭐⭐⭐ {team_data['3_stars']}")

        if stars:
            lines.append("")
            lines.append("**Star Breakdown:**")
            lines.extend(stars)

        return '\n'.join(lines)

    def format_team_commits(self, data: Dict[str, Any], limit: int = 25) -> str:
        """Format team commits list for display"""
        if not data:
            return "❌ Team not found"

        lines = []

        team = data.get('team', 'Unknown')
        year = data.get('year', '')
        rank = data.get('rank', '?')
        total = data.get('total_commits', 0)
        avg_rating = data.get('avg_rating')

        # Header
        lines.append(f"**{team}** - #{rank} Nationally ({year})")
        lines.append(f"👥 **{total}** Commits")
        if avg_rating:
            lines.append(f"📊 Avg Rating: **{avg_rating:.2f}**")
        lines.append("")

        commits = data.get('commits', [])

        if not commits:
            lines.append("_No commits found_")
            return '\n'.join(lines)

        # Show commits (limited)
        lines.append("**Committed Players:**")

        for i, c in enumerate(commits[:limit], 1):
            name = c.get('name', 'Unknown')
            pos = c.get('position', '?')
            rating = c.get('rating')
            stars = c.get('stars', 0)

            # Location info
            loc = c.get('location', '')
            loc_short = loc.split(',')[0].strip() if loc else ''  # Just city
            high_school = c.get('high_school', '')

            # HS vs Transfer indicator - detected from H.S. year and TR indicator
            is_transfer = c.get('is_transfer', False)
            player_type = "🌀" if is_transfer else ""  # Only show portal indicator for transfers

            # Compact star display
            star_str = f"{stars}⭐" if stars else ""

            # Build line - more compact format with location
            rating_str = f"{rating:.1f}" if rating else ""
            status = c.get('status', '')
            status_emoji = "✅" if status == 'Signed' else "📝" if status == 'Committed' else ""

            # Format: 1. 🌀 4⭐ Kodi Greene (OT) 96.5 • Santa Ana ✅
            loc_part = f" • {loc_short}" if loc_short else ""
            portal_str = f"{player_type} " if player_type else ""
            lines.append(f"`{i:2d}.` {portal_str}{star_str} **{name}** ({pos}) {rating_str}{loc_part} {status_emoji}")

        # Show truncation message if needed
        if len(commits) > limit:
            lines.append(f"")
            lines.append(f"_...and {len(commits) - limit} more commits_")

        # Legend
        lines.append("")
        lines.append("_🌀 = Portal | ✅ = Signed | 📝 = Committed_")

        # Link to full page
        if data.get('commits_url'):
            lines.append(f"[View Full Class on On3/Rivals]({data['commits_url']})")

        return '\n'.join(lines)

    def format_top_recruits(self, recruits: List[Dict[str, Any]], title: str = "Top Recruits") -> str:
        """Format list of top recruits"""
        if not recruits:
            return "❌ No recruits found"

        lines = [f"**{title}**", ""]

        for i, r in enumerate(recruits, 1):
            stars = '⭐' * r.get('stars', 0) if r.get('stars') else ''
            name = r.get('name', 'Unknown')
            pos = r.get('position', '')
            commit = r.get('committed_to', '')

            if commit:
                lines.append(f"`{i:2d}.` {stars} **{name}** ({pos}) → {commit}")
            else:
                lines.append(f"`{i:2d}.` {stars} **{name}** ({pos})")

        return '\n'.join(lines)

    async def cleanup(self):
        """Clean up resources (call on bot shutdown)"""
        await self._close_browser()

    def __del__(self):
        """Cleanup when object is destroyed"""
        # Note: Can't use async in __del__, so just log
        if self._browser:
            logger.warning("⚠️ On3Scraper deleted without cleanup - browser may still be running")


# Global instance
on3_scraper = On3Scraper()
