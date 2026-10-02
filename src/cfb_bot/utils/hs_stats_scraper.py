"""
High School Stats Scraper Module
Scrapes MaxPreps for high school football player stats.

⚠️ DISCLAIMER: Web scraping may violate MaxPreps Terms of Service.
This module is provided for educational/personal use only.
Use responsibly with appropriate rate limiting.
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger('CFBBot.HSStats')

# Try to import scraping libraries
try:
    import httpx
    from bs4 import BeautifulSoup
    HS_SCRAPER_AVAILABLE = True
except ImportError:
    HS_SCRAPER_AVAILABLE = False
    logger.warning("⚠️ httpx or beautifulsoup4 not installed - HS stats scraper disabled")
    logger.warning("   Install with: pip install httpx beautifulsoup4")


class HSStatsScraper:
    """
    Scrapes MaxPreps for high school football player stats.

    Features:
    - Player search by name
    - State/school filtering for common names
    - Stats parsing (passing, rushing, receiving, defense)
    - Result caching (24hr TTL)
    - Rate limiting (1 req/sec)
    """

    BASE_URL = "https://www.maxpreps.com"

    # MaxPreps search patterns - q= is the correct parameter (not query=)
    SEARCH_PATTERNS = [
        "/search?q={query}&type=athletes&sport=football",       # Primary - works!
        "/search/?q={query}&sport=football",                    # Alternative
        "/search?q={query}",                                    # Generic search
    ]

    # User agent to avoid blocks - use a modern Chrome UA
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

    # Rate limiting
    MIN_REQUEST_INTERVAL = 1.0  # seconds between requests

    # Cache settings
    CACHE_TTL = 24 * 60 * 60  # 24 hours in seconds

    # State code mapping (two-letter to full name and vice versa)
    STATE_CODES = {
        'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
        'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
        'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
        'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
        'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
        'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
        'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
        'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
        'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
        'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
        'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
        'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
        'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
    }

    # Reverse mapping (full name to code)
    STATE_NAMES = {v.lower(): k for k, v in STATE_CODES.items()}

    def __init__(self):
        self.is_available = HS_SCRAPER_AVAILABLE
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._last_request_time: float = 0
        self._client: Optional[httpx.AsyncClient] = None

        if not self.is_available:
            logger.warning("⚠️ HS Stats scraper not available - missing dependencies")

    def _normalize_state(self, state: str) -> tuple[str, str]:
        """
        Normalize state input to both code and full name.

        Args:
            state: State code (TN) or full name (Tennessee)

        Returns:
            Tuple of (state_code, state_name) or (None, None) if invalid
        """
        if not state:
            return None, None

        state = state.strip()
        state_upper = state.upper()
        state_lower = state.lower()

        # Check if it's a state code
        if state_upper in self.STATE_CODES:
            return state_upper, self.STATE_CODES[state_upper]

        # Check if it's a state name
        if state_lower in self.STATE_NAMES:
            return self.STATE_NAMES[state_lower], state.title()

        # Try partial match for state name
        for name, code in self.STATE_NAMES.items():
            if state_lower in name or name in state_lower:
                return code, name.title()

        # Return as-is if not recognized (user might have typo)
        logger.warning(f"⚠️ Unrecognized state: {state}")
        return None, state

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self.HEADERS,
                timeout=30.0,
                follow_redirects=True
            )
        return self._client

    async def _rate_limit(self):
        """Enforce rate limiting between requests"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            await asyncio.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    def _get_cache_key(self, name: str, state: str = None, school: str = None) -> str:
        """Generate cache key for a player lookup"""
        key_parts = [name.lower().strip()]
        if state:
            key_parts.append(state.lower().strip())
        if school:
            key_parts.append(school.lower().strip())
        return ":".join(key_parts)

    def _check_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Check if we have a valid cached result"""
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now().timestamp() - cached.get('timestamp', 0) < self.CACHE_TTL:
                logger.info(f"📦 Cache hit for {cache_key}")
                return cached.get('data')
        return None

    def _store_cache(self, cache_key: str, data: Dict[str, Any]):
        """Store result in cache"""
        self._cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now().timestamp()
        }

        # Clean old cache entries (keep last 100)
        if len(self._cache) > 100:
            oldest_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k].get('timestamp', 0)
            )[:50]
            for key in oldest_keys:
                del self._cache[key]

    async def search_player(self, name: str, state: str = None) -> List[Dict[str, Any]]:
        """
        Search MaxPreps for a player by name.

        Args:
            name: Player name (e.g., "Arch Manning")
            state: Optional state to filter results (e.g., "Louisiana", "LA", "Tennessee", "TN")

        Returns:
            List of matching player results with basic info
        """
        if not self.is_available:
            return []

        try:
            await self._rate_limit()
            client = await self._get_client()

            # Normalize state input (handle both "TN" and "Tennessee")
            state_code, state_name = self._normalize_state(state) if state else (None, None)

            # Build search query - use full state name for better search results
            search_query = name
            if state_name:
                search_query += f" {state_name}"

            logger.info(f"🔍 Searching MaxPreps for: {search_query}")

            # Try multiple search URL patterns (MaxPreps updates their site frequently)
            response = None
            for pattern in self.SEARCH_PATTERNS:
                search_url = self.BASE_URL + pattern.format(query=quote_plus(search_query))
                logger.debug(f"🔍 Trying search URL: {search_url}")

                try:
                    response = await client.get(search_url)
                    if response.status_code == 200:
                        logger.info(f"✅ Search URL worked: {search_url}")
                        break
                    else:
                        logger.debug(f"❌ Search URL returned {response.status_code}")
                except Exception as e:
                    logger.debug(f"❌ Search URL failed: {e}")
                    continue

            if not response or response.status_code != 200:
                # Fallback: Try direct athlete URL construction
                # MaxPreps URLs: /la/new-orleans/newman-greenies/athletes/arch-manning/football/
                slug_name = name.lower().replace(' ', '-').replace("'", "")
                direct_url = f"{self.BASE_URL}/athletes/{slug_name}/football/"
                logger.info(f"🔍 Trying direct URL: {direct_url}")

                try:
                    response = await client.get(direct_url)
                    if response.status_code == 200:
                        # Found via direct URL - return as single result
                        return [{
                            'name': name,
                            'school': None,
                            'profile_url': str(response.url)  # Use final URL after redirects
                        }]
                except Exception:
                    pass

                logger.warning(f"❌ All search methods failed for: {search_query}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # Parse search results
            results = []

            # MaxPreps search results - try multiple selectors for their React-based site
            player_cards = soup.select(
                '.athlete-card, .search-result-item, .player-row, '
                '[data-athlete-id], .athlete-result, .search-athlete, '
                'div[class*="athlete"], div[class*="player"], '
                'a[href*="/athletes/"]'
            )

            if not player_cards:
                # Try finding any links to athlete pages
                player_cards = soup.select('a[href*="/athletes/"]')

            for card in player_cards[:10]:  # Limit to top 10 results
                try:
                    # Extract player info
                    player_name = card.get_text(strip=True) if card.name == 'a' else card.select_one('.name, .athlete-name, h3, h4')
                    if player_name and hasattr(player_name, 'get_text'):
                        player_name = player_name.get_text(strip=True)
                    elif not isinstance(player_name, str):
                        player_name = str(player_name) if player_name else None

                    # Get profile URL - try multiple methods
                    profile_url = None
                    if card.name == 'a':
                        profile_url = card.get('href')
                    else:
                        # Fixed typo: /athletes/ not /athlete/
                        link = card.select_one('a[href*="/athletes/"]')
                        if link:
                            profile_url = link.get('href')

                    # Validate the URL looks like a real player profile
                    if profile_url:
                        if not profile_url.startswith('http'):
                            profile_url = self.BASE_URL + profile_url

                        # Skip generic navigation URLs (e.g., /football/athletes/, /athletes/)
                        # Real player URLs have format: /state/city/school/athletes/player-name/
                        # or /athletes/player-name/?careerid=xxx
                        url_path = profile_url.split('?')[0].rstrip('/')  # Remove query params and trailing slash
                        path_parts = url_path.split('/')

                        # Find where /athletes/ is in the path
                        if '/athletes' in url_path:
                            athletes_idx = None
                            for i, part in enumerate(path_parts):
                                if part == 'athletes':
                                    athletes_idx = i
                                    break

                            if athletes_idx is not None:
                                # Check if there's a player name AFTER /athletes/
                                parts_after_athletes = path_parts[athletes_idx + 1:]
                                has_player_name = any(part and part not in ['football', 'stats', ''] for part in parts_after_athletes)

                                if not has_player_name:
                                    logger.debug(f"Skipping generic URL (no player name): {profile_url}")
                                    profile_url = None
                        else:
                            logger.debug(f"Skipping non-athlete URL: {profile_url}")
                            profile_url = None

                    # Extract school/location info
                    school_elem = card.select_one('.school, .team-name, .location')
                    school = school_elem.get_text(strip=True) if school_elem else None

                    if player_name and profile_url:
                        logger.debug(f"Found player: {player_name} -> {profile_url}")
                        results.append({
                            'name': player_name,
                            'school': school,
                            'profile_url': profile_url
                        })

                except Exception as e:
                    logger.debug(f"Error parsing search result: {e}")
                    continue

            logger.info(f"✅ Found {len(results)} search results for {name}")
            return results

        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error searching MaxPreps: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Error searching MaxPreps: {e}", exc_info=True)
            return []

    async def get_player_stats(self, profile_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape stats from a player's MaxPreps profile page.

        Args:
            profile_url: Full URL to player's MaxPreps profile

        Returns:
            Dict with player info and stats
        """
        if not self.is_available:
            return None

        try:
            await self._rate_limit()
            client = await self._get_client()

            # Validate URL before proceeding
            if not profile_url or '/athletes/' not in profile_url:
                logger.error(f"❌ Invalid profile URL: {profile_url}")
                return None

            # Handle query parameters (e.g., ?careerid=xxx)
            # Need to insert /football/stats/ before the query string
            query_string = ''
            if '?' in profile_url:
                profile_url, query_string = profile_url.split('?', 1)
                query_string = '?' + query_string

            # Make sure we're hitting the stats page
            # URL should be like: /state/city/school/athletes/player-name/football/stats/
            if '/stats/' not in profile_url and '/stats' not in profile_url:
                # Add /football/stats/ if needed
                profile_url = profile_url.rstrip('/')
                if '/football' not in profile_url:
                    profile_url += '/football'
                profile_url += '/stats/'

            # Re-add query string
            profile_url += query_string

            logger.info(f"🔍 Fetching stats from: {profile_url}")

            response = await client.get(profile_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract player info
            player_data = {
                'name': None,
                'school': None,
                'location': None,
                'position': None,
                'class_year': None,
                'height': None,
                'weight': None,
                'profile_url': profile_url,
                'seasons': []
            }

            # ==================== EXTRACT FROM OG:TITLE ====================
            # Format variations:
            # - "Gavin Day's Faith Lutheran High School Football Stats" (has school)
            # - "Mason James' High School Football Stats" (no school)
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get('content'):
                title_content = og_title.get('content')

                # Try pattern with school name first
                title_match = re.match(r"^(.+?)'s\s+(.+?)\s+High School\s+Football\s+Stats?", title_content, re.I)
                if title_match:
                    player_data['name'] = title_match.group(1).strip()
                    school_part = title_match.group(2).strip()
                    # Only set school if it's not just empty or generic
                    if school_part and school_part.lower() not in ['', 'high school']:
                        player_data['school'] = school_part
                    logger.debug(f"Extracted from og:title (with school) - Name: {player_data['name']}, School: {player_data['school']}")
                else:
                    # Try pattern without school: "Name's High School Football Stats"
                    title_match = re.match(r"^(.+?)'s?\s+High School\s+Football\s+Stats?", title_content, re.I)
                    if title_match:
                        player_data['name'] = title_match.group(1).strip()
                        logger.debug(f"Extracted from og:title (no school) - Name: {player_data['name']}")
                    else:
                        # Last resort: Just get name before apostrophe
                        title_match = re.match(r"^(.+?)'s?\s+", title_content)
                        if title_match:
                            player_data['name'] = title_match.group(1).strip()

            # Fallback: Try page title
            if not player_data['name']:
                title_elem = soup.select_one('title')
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    # Same patterns as above
                    title_match = re.match(r"^(.+?)'s\s+(.+?)\s+High School\s+Football", title_text, re.I)
                    if title_match:
                        player_data['name'] = title_match.group(1).strip()
                        if not player_data['school']:
                            school_part = title_match.group(2).strip()
                            if school_part:
                                player_data['school'] = school_part
                    else:
                        title_match = re.match(r"^(.+?)'s?\s+High School\s+Football", title_text, re.I)
                        if title_match:
                            player_data['name'] = title_match.group(1).strip()

            # Fallback: Try h1 (might be "Football Stats" but try anyway)
            if not player_data['name']:
                name_elem = soup.select_one('h1')
                if name_elem:
                    name_text = name_elem.get_text(strip=True)
                    # Only use if it looks like a name (not "Football Stats")
                    if name_text and 'Stats' not in name_text and 'Football' not in name_text:
                        player_data['name'] = name_text.strip()

            # Extract location from URL if not already set
            # URL format: /nv/las-vegas/faith-lutheran-crusaders/athletes/...
            url_match = re.search(r'/([a-z]{2})/([^/]+)/([^/]+)/athletes/', profile_url)
            if url_match:
                state = url_match.group(1).upper()
                city = url_match.group(2).replace('-', ' ').title()
                school_from_url = url_match.group(3).replace('-', ' ').title()

                player_data['location'] = f"{city}, {state}"

                # Use school from URL as fallback
                if not player_data['school']:
                    player_data['school'] = school_from_url

            # Position - look for position abbreviations with context
            page_text = soup.get_text()
            # Look for position in player info section
            # MaxPreps format: "V. Football #1 • DB" followed by "Home" or other nav
            # The position is the last item before navigation items
            pos_patterns = [
                # "V. Football #1 • DB" - capture position before Home/Bio/etc
                r'Football\s*#?\d*\s*[•·]\s*(QB|WR|RB|TE|OL|DL|LB|CB|ATH|DB|OT|OG|DE|DT|SS|FS|S|K|P)(?=Home|Bio|Stats|$|[^a-zA-Z])',
                r'[•·]\s*(QB|WR|RB|TE|OL|DL|LB|CB|ATH|DB|OT|OG|DE|DT|SS|FS|S|K|P)(?=Home|Bio|Stats|$|[^a-zA-Z])',
                r'Position[:\s]*(QB|WR|RB|TE|OL|DL|LB|CB|ATH|DB|OT|OG|DE|DT|SS|FS|S|K|P)\b',
            ]
            for pattern in pos_patterns:
                pos_match = re.search(pattern, page_text, re.I)
                if pos_match:
                    player_data['position'] = pos_match.group(1).upper()
                    break

            # Extract height/weight from player info
            # Format: "6'3" • 190 lbs" or "6-3 • 190"
            hw_match = re.search(r"(\d['′]?\d+[\"″]?|\d-\d+)\s*[•·]\s*(\d+)\s*(?:lbs?)?", page_text)
            if hw_match:
                player_data['height'] = hw_match.group(1)
                player_data['weight'] = hw_match.group(2)

            # Extract class year from page (Senior, Junior, etc.)
            # MaxPreps shows class year in header section, format: "Senior • 2026"
            # Look specifically in the athlete info area
            class_patterns = [
                r'(Senior|Junior|Sophomore|Freshman)\s*[•·]\s*(\d{4})',  # Senior • 2026
                r'\b(Senior|Junior|Sophomore|Freshman)\b',  # Just the class
            ]
            for pattern in class_patterns:
                class_match = re.search(pattern, page_text, re.I)
                if class_match:
                    player_data['class_year'] = class_match.group(1).title()
                    break

            # ==================== PARSE TOP STATS SECTION ====================
            # MaxPreps shows summary stats in compact format: "Solo210Tot283"
            top_stats = {}

            # MaxPreps compacts stats without spaces, e.g., "Pts6P/G0.2Tot2Yds13Solo210Tot283"
            # Need to handle: Solo210Tot283 (solo tackles, total tackles)

            # Try combined pattern first for defense stats (most reliable)
            # Pattern: Solo(number)Tot(number) - defense stats are together
            defense_match = re.search(r'Solo(\d+)Tot(\d+)', page_text)
            if defense_match:
                top_stats['solo_tackles'] = defense_match.group(1)
                top_stats['total_tackles'] = defense_match.group(2)
                logger.debug(f"Found defense stats: Solo {top_stats['solo_tackles']}, Tot {top_stats['total_tackles']}")

            # Try other patterns for remaining stats
            # These need word boundaries or context to avoid false matches
            stat_patterns = [
                (r'Pts(\d+)P/G', 'points'),  # Points followed by P/G
                (r'P/G([\d.]+)', 'points_per_game'),
                (r'Sack[s]?\s*(\d+)', 'sacks'),
                (r'(?<![a-zA-Z])Int\s*(\d+)(?![a-zA-Z])', 'interceptions'),  # INT not part of other word
                (r'FF\s*(\d+)', 'forced_fumbles'),
                (r'PD\s*(\d+)', 'passes_defended'),
                (r'TFL\s*(\d+)', 'tackles_for_loss'),
            ]

            for pattern, stat_name in stat_patterns:
                if stat_name not in top_stats:  # Don't overwrite
                    match = re.search(pattern, page_text, re.I)
                    if match:
                        top_stats[stat_name] = match.group(1)

            if top_stats:
                player_data['career_summary'] = top_stats
                logger.debug(f"Found top stats: {top_stats}")

            # ==================== PARSE STATS TABLES ====================
            # Parse all stats tables on the page
            stats_tables = soup.select('table')
            all_seasons = []

            for table in stats_tables:
                season_stats = self._parse_stats_table(table)
                if season_stats:
                    all_seasons.extend(season_stats)

            # Consolidate seasons by year (merge data from different tables)
            seasons_by_year = {}
            career_total = None

            for season in all_seasons:
                if season.get('is_career_total'):
                    if not career_total:
                        career_total = season
                    else:
                        # Merge with existing career total
                        for key in ['passing', 'rushing', 'receiving', 'all_purpose', 'defense']:
                            if season.get(key):
                                career_total[key].update({k: v for k, v in season[key].items() if v})
                else:
                    year_key = season.get('year', '') or season.get('grade', 'unknown')
                    if year_key not in seasons_by_year:
                        seasons_by_year[year_key] = season
                    else:
                        # Merge stats from this table into existing season
                        existing = seasons_by_year[year_key]
                        for key in ['passing', 'rushing', 'receiving', 'all_purpose', 'defense']:
                            if season.get(key):
                                existing[key].update({k: v for k, v in season[key].items() if v})

            # Add individual seasons
            player_data['seasons'] = list(seasons_by_year.values())

            # Add career total as a special season
            if career_total:
                career_total['year'] = 'Career Total'
                career_total['grade'] = 'Career'
                player_data['seasons'].append(career_total)

            # Add top stats to career summary if we have defensive stats
            if top_stats.get('solo_tackles') or top_stats.get('total_tackles'):
                # Create or update career defense stats
                if not career_total:
                    career_total = {
                        'year': 'Career Total',
                        'grade': 'Career',
                        'is_career_total': True,
                        'defense': {}
                    }
                    player_data['seasons'].append(career_total)

                career_total.setdefault('defense', {})
                career_total['defense']['solo_tackles'] = top_stats.get('solo_tackles', '')
                career_total['defense']['total_tackles'] = top_stats.get('total_tackles', '')

            logger.info(f"✅ Scraped stats for {player_data.get('name', 'Unknown')}")
            return player_data

        except httpx.HTTPError as e:
            logger.error(f"❌ HTTP error fetching stats: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching stats: {e}", exc_info=True)
            return None

    def _parse_stats_table(self, table, table_type: str = None) -> List[Dict[str, Any]]:
        """
        Parse a MaxPreps stats table into structured data.

        MaxPreps tables have format:
        - Header row: GD, Team, Year, GP, [stat columns...]
        - Data rows: Sr., Var, 25-26, 14, [values...]
        - Total row: Varsity Total, [totals...]

        Returns list of season stats dicts.
        """
        try:
            seasons = []

            # Get all rows
            rows = table.select('tr')
            if len(rows) < 2:
                return []

            # First row is headers
            header_cells = rows[0].select('th, td')
            headers = [h.get_text(strip=True).lower() for h in header_cells]
            logger.debug(f"Table headers: {headers}")

            # Determine table type from headers
            # MaxPreps tables have different meanings for same column names:
            # - Receiving table: Rec=receptions(count), Yds=yards
            # - All Purpose table: Rec=receiving yards (not count!)
            if not table_type:
                if 'car' in headers or 'carries' in headers:
                    table_type = 'rushing'
                elif 'comp' in headers or 'att' in headers:
                    table_type = 'passing'
                elif 'ir' in headers or 'kr' in headers or 'pr' in headers:
                    # All Purpose table has IR/KR/PR columns
                    table_type = 'all_purpose'
                elif 'rec' in headers and 'yds' in headers and 'avg' in headers and 'td' in headers:
                    # Receiving table has: Rec, Yds, Avg, Y/G, Lng, TD
                    # Distinguished by having both 'rec' AND 'yds' as separate columns
                    table_type = 'receiving'
                elif 'solo' in headers or 'tkl' in headers:
                    table_type = 'defense'
                elif 'rush' in headers and 'pass' in headers and 'rec' in headers:
                    # Total yards table has Rush, Pass, Rec columns (all yards)
                    table_type = 'total_yards'

            # Parse data rows (skip header)
            for row in rows[1:]:
                cells = row.select('td')
                if not cells:
                    continue

                # Build row data dict
                row_data = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row_data[headers[i]] = cell.get_text(strip=True)

                # Skip if this is the header row repeated
                if row_data.get('gd', '').lower() == 'gd':
                    continue

                # Check if this is a totals row
                is_total = any('total' in str(v).lower() for v in row_data.values())

                # Extract year/grade info
                grade = row_data.get('gd', '')  # Sr., Jr., So., Fr.
                year = row_data.get('year', '')  # 25-26, 24-25, etc.
                gp = row_data.get('gp', '')  # Games played

                # Create season entry
                season = {
                    'grade': grade,
                    'year': year,
                    'games': gp,
                    'is_career_total': is_total,
                    'table_type': table_type,
                    'passing': {},
                    'rushing': {},
                    'receiving': {},
                    'all_purpose': {},
                    'defense': {}
                }

                # Parse based on table type
                if table_type == 'rushing':
                    season['rushing'] = {
                        'carries': row_data.get('car', ''),
                        'yards': row_data.get('yds', ''),
                        'avg': row_data.get('avg', ''),
                        'yards_per_game': row_data.get('y/g', ''),
                        'long': row_data.get('lng', ''),
                        'touchdowns': row_data.get('td', ''),
                        '100_yard_games': row_data.get('100+', '')
                    }

                elif table_type == 'passing':
                    season['passing'] = {
                        'completions': row_data.get('comp', row_data.get('cmp', '')),
                        'attempts': row_data.get('att', ''),
                        'yards': row_data.get('yds', ''),
                        'touchdowns': row_data.get('td', ''),
                        'interceptions': row_data.get('int', ''),
                        'passer_rating': row_data.get('rtg', row_data.get('qbr', ''))
                    }

                elif table_type == 'receiving':
                    # Receiving table columns: Rec(count), Yds(yards), Avg, Y/G, Lng, TD
                    season['receiving'] = {
                        'receptions': row_data.get('rec', ''),  # Rec = receptions count
                        'yards': row_data.get('yds', ''),       # Yds = receiving yards
                        'avg': row_data.get('avg', ''),
                        'yards_per_game': row_data.get('y/g', ''),
                        'touchdowns': row_data.get('td', ''),
                        'long': row_data.get('lng', '')
                    }

                elif table_type == 'all_purpose':
                    season['all_purpose'] = {
                        'rush_yards': row_data.get('rush', ''),
                        'rec_yards': row_data.get('rec', ''),
                        'kick_return': row_data.get('kr', ''),
                        'punt_return': row_data.get('pr', ''),
                        'int_return': row_data.get('ir', ''),
                        'total': row_data.get('total', ''),
                        'yards_per_game': row_data.get('y/g', '')
                    }

                elif table_type == 'defense':
                    season['defense'] = {
                        'solo_tackles': row_data.get('solo', ''),
                        'total_tackles': row_data.get('tot', row_data.get('tkl', '')),
                        'tackles_for_loss': row_data.get('tfl', ''),
                        'sacks': row_data.get('sack', row_data.get('sk', '')),
                        'interceptions': row_data.get('int', ''),
                        'passes_defended': row_data.get('pd', row_data.get('pbu', '')),
                        'forced_fumbles': row_data.get('ff', '')
                    }

                elif table_type == 'total_yards':
                    season['all_purpose'] = {
                        'rush_yards': row_data.get('rush', ''),
                        'pass_yards': row_data.get('pass', ''),
                        'rec_yards': row_data.get('rec', ''),
                        'total': row_data.get('total', ''),
                        'yards_per_game': row_data.get('y/g', '')
                    }

                # Only add if we have some data
                has_data = any([
                    any(season['passing'].values()),
                    any(season['rushing'].values()),
                    any(season['receiving'].values()),
                    any(season['all_purpose'].values()),
                    any(season['defense'].values())
                ])

                if has_data:
                    seasons.append(season)

            return seasons

        except Exception as e:
            logger.debug(f"Error parsing stats table: {e}")
            return []

    def _parse_stat_block(self, block) -> Optional[Dict[str, Any]]:
        """Parse a stat block (non-table format) into structured data"""
        try:
            text = block.get_text()
            stats = {
                'year': None,
                'passing': {},
                'rushing': {},
                'receiving': {},
                'defense': {}
            }

            # Try to extract stats using regex patterns
            # Passing: "150/250, 2500 YDS, 25 TD, 5 INT"
            pass_match = re.search(r'(\d+)[/-](\d+)[,\s]+(\d+)\s*(?:YDS|yards)[,\s]+(\d+)\s*TD', text, re.I)
            if pass_match:
                stats['passing'] = {
                    'completions': pass_match.group(1),
                    'attempts': pass_match.group(2),
                    'yards': pass_match.group(3),
                    'touchdowns': pass_match.group(4)
                }

            # Rushing: "150 CAR, 1200 YDS, 15 TD"
            rush_match = re.search(r'(\d+)\s*(?:CAR|carries)[,\s]+(\d+)\s*(?:YDS|yards)[,\s]+(\d+)\s*TD', text, re.I)
            if rush_match:
                stats['rushing'] = {
                    'carries': rush_match.group(1),
                    'yards': rush_match.group(2),
                    'touchdowns': rush_match.group(3)
                }

            # Receiving: "50 REC, 800 YDS, 10 TD"
            rec_match = re.search(r'(\d+)\s*(?:REC|receptions)[,\s]+(\d+)\s*(?:YDS|yards)[,\s]+(\d+)\s*TD', text, re.I)
            if rec_match:
                stats['receiving'] = {
                    'receptions': rec_match.group(1),
                    'yards': rec_match.group(2),
                    'touchdowns': rec_match.group(3)
                }

            has_stats = stats['passing'] or stats['rushing'] or stats['receiving']
            return stats if has_stats else None

        except Exception as e:
            logger.debug(f"Error parsing stat block: {e}")
            return None

    async def lookup_player(self, name: str, state: str = None, school: str = None) -> Optional[Dict[str, Any]]:
        """
        Complete player lookup: search + get stats.

        Args:
            name: Player name
            state: Optional state filter
            school: Optional school filter

        Returns:
            Dict with player info and stats, or None if not found
        """
        if not self.is_available:
            return None

        # Check cache first
        cache_key = self._get_cache_key(name, state, school)
        cached = self._check_cache(cache_key)
        if cached:
            return cached

        # Search for player
        results = await self.search_player(name, state)

        if not results:
            logger.info(f"❌ No results found for {name}")
            return None

        # If school specified, try to match
        best_match = results[0]
        if school:
            school_lower = school.lower()
            for result in results:
                if result.get('school') and school_lower in result['school'].lower():
                    best_match = result
                    break

        # Get full stats
        profile_url = best_match.get('profile_url')
        if not profile_url:
            return None

        player_data = await self.get_player_stats(profile_url)

        if player_data:
            self._store_cache(cache_key, player_data)

        return player_data

    async def lookup_multiple_players(self, players: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Bulk player lookup.

        Args:
            players: List of dicts with 'name', optional 'state', optional 'school'

        Returns:
            List of player data dicts
        """
        if not self.is_available:
            return []

        results = []

        for player_info in players:
            name = player_info.get('name')
            if not name:
                continue

            try:
                data = await self.lookup_player(
                    name=name,
                    state=player_info.get('state'),
                    school=player_info.get('school')
                )

                results.append({
                    'query': player_info,
                    'found': data is not None,
                    'data': data
                })

            except Exception as e:
                logger.error(f"Error looking up {name}: {e}")
                results.append({
                    'query': player_info,
                    'found': False,
                    'error': str(e)
                })

        return results

    def format_player_stats(self, player_data: Dict[str, Any]) -> str:
        """Format player stats for Discord display"""
        if not player_data:
            return "No stats found"

        lines = []

        # Header
        name = player_data.get('name', 'Unknown Player')
        school = player_data.get('school', '')
        location = player_data.get('location', '')
        position = player_data.get('position', '')
        height = player_data.get('height', '')
        weight = player_data.get('weight', '')
        class_year = player_data.get('class_year', '')

        lines.append(f"🏈 **{name}**")

        # School/Location line
        if school:
            school_line = f"🏫 {school}"
            if location:
                school_line += f" ({location})"
            lines.append(school_line)

        # Player info line (position, height, weight, class)
        info_parts = []
        if position:
            info_parts.append(f"**{position}**")
        if height:
            info_parts.append(f"{height}")
        if weight:
            info_parts.append(f"{weight} lbs")
        if class_year:
            info_parts.append(f"{class_year}")
        if info_parts:
            lines.append(f"📍 {' • '.join(info_parts)}")

        lines.append("")

        # Stats by season
        seasons = player_data.get('seasons', [])

        # Separate career total from individual seasons
        career_season = None
        individual_seasons = []
        for season in seasons:
            if season.get('is_career_total') or 'career' in str(season.get('year', '')).lower():
                career_season = season
            else:
                individual_seasons.append(season)

        # Show individual seasons (most recent first, limit to 3)
        if individual_seasons:
            # Sort by year descending
            individual_seasons.sort(key=lambda s: s.get('year', ''), reverse=True)

            for season in individual_seasons[:3]:
                year = season.get('year', '')
                grade = season.get('grade', '')
                games = season.get('games', '')

                # Build season header
                header_parts = []
                if grade and grade not in ['', 'Varsity Total']:
                    header_parts.append(grade)
                if year:
                    header_parts.append(year)
                season_header = f"**{' '.join(header_parts) or 'Season'}**"
                if games:
                    season_header += f" ({games} GP)"
                lines.append(season_header)

                # Add stat lines for this season
                self._add_stat_lines(lines, season)
                lines.append("")

        # Show career totals if available
        if career_season:
            games = career_season.get('games', '')
            career_header = "**📊 Career Totals**"
            if games:
                career_header += f" ({games} GP)"
            lines.append(career_header)
            self._add_stat_lines(lines, career_season)
            lines.append("")

        # If no seasons found, show career summary if available
        if not seasons:
            career_summary = player_data.get('career_summary', {})
            if career_summary:
                lines.append("**📊 Career Summary**")
                if career_summary.get('solo_tackles'):
                    lines.append(f"  🛡️ Solo Tackles: **{career_summary['solo_tackles']}**")
                if career_summary.get('total_tackles'):
                    lines.append(f"  🛡️ Total Tackles: **{career_summary['total_tackles']}**")
                if career_summary.get('interceptions'):
                    lines.append(f"  🏈 Interceptions: **{career_summary['interceptions']}**")
                if career_summary.get('sacks'):
                    lines.append(f"  💥 Sacks: **{career_summary['sacks']}**")
                if career_summary.get('points'):
                    lines.append(f"  🎯 Points: **{career_summary['points']}**")
                lines.append("")
            else:
                lines.append("_No detailed stats available_")

        # Link to profile
        profile_url = player_data.get('profile_url')
        if profile_url:
            lines.append(f"[View Full Profile on MaxPreps]({profile_url})")

        return "\n".join(lines)

    def _add_stat_lines(self, lines: List[str], season: Dict[str, Any]):
        """Add stat lines for a season to the output"""
        # Passing
        passing = season.get('passing', {})
        if passing and any(v for v in passing.values() if v):
            comp = passing.get('completions', '-')
            att = passing.get('attempts', '-')
            yds = passing.get('yards', '-')
            td = passing.get('touchdowns', '-')
            int_val = passing.get('interceptions', '-')
            lines.append(f"  🎯 **Passing:** {comp}/{att} | {yds} YDS | {td} TD | {int_val} INT")

        # Rushing
        rushing = season.get('rushing', {})
        if rushing and any(v for v in rushing.values() if v):
            car = rushing.get('carries', '-')
            yds = rushing.get('yards', '-')
            avg = rushing.get('avg', '')
            td = rushing.get('touchdowns', '-')
            lng = rushing.get('long', '')

            rush_line = f"  🏃 **Rushing:** {car} CAR | {yds} YDS | {td} TD"
            if avg:
                rush_line += f" | {avg} AVG"
            if lng:
                rush_line += f" | LNG {lng}"
            lines.append(rush_line)

        # Receiving - only show if there's meaningful data
        receiving = season.get('receiving', {})
        if receiving:
            rec = receiving.get('receptions', '')
            yds = receiving.get('yards', '')
            td = receiving.get('touchdowns', '')
            avg = receiving.get('avg', '')

            # Only display if there's actual receiving data (not all zeros)
            has_data = (rec and rec not in ['0', '-', '']) or \
                       (yds and yds not in ['0', '-', '']) or \
                       (td and td not in ['0', '-', ''])

            if has_data:
                rec_line = f"  🙌 **Receiving:** {rec or '-'} REC | {yds or '-'} YDS | {td or '-'} TD"
                if avg:
                    rec_line += f" | {avg} AVG"
                lines.append(rec_line)

        # All Purpose Yards
        all_purpose = season.get('all_purpose', {})
        if all_purpose and any(v for v in all_purpose.values() if v):
            total = all_purpose.get('total', '')
            ir = all_purpose.get('int_return', '')
            kr = all_purpose.get('kick_return', '')
            pr = all_purpose.get('punt_return', '')

            if total:
                ap_parts = [f"**{total}** Total"]
                if ir and ir != '0':
                    ap_parts.append(f"{ir} IR")
                if kr and kr != '0':
                    ap_parts.append(f"{kr} KR")
                if pr and pr != '0':
                    ap_parts.append(f"{pr} PR")
                lines.append(f"  🔄 **All Purpose:** {' | '.join(ap_parts)}")

        # Defense
        defense = season.get('defense', {})
        if defense and any(v for v in defense.values() if v):
            solo = defense.get('solo_tackles', '')
            total = defense.get('total_tackles', '')
            sacks = defense.get('sacks', '')
            ints = defense.get('interceptions', '')
            ff = defense.get('forced_fumbles', '')
            pd = defense.get('passes_defended', '')

            def_parts = []
            if solo or total:
                tkl_str = f"{total}" if total else ""
                if solo:
                    tkl_str = f"{solo} Solo/{total}" if total else f"{solo} Solo"
                def_parts.append(f"{tkl_str} TKL")
            if sacks and sacks != '0':
                def_parts.append(f"{sacks} SCK")
            if ints and ints != '0':
                def_parts.append(f"{ints} INT")
            if ff and ff != '0':
                def_parts.append(f"{ff} FF")
            if pd and pd != '0':
                def_parts.append(f"{pd} PD")

            if def_parts:
                lines.append(f"  🛡️ **Defense:** {' | '.join(def_parts)}")

    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()


# Global instance
hs_stats_scraper = HSStatsScraper()
