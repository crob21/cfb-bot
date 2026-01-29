"""
CFB Data Module
Comprehensive College Football Data integration using CollegeFootballData.com API.

Features:
- Player lookups and stats
- Team rankings (AP, Coaches, CFP)
- Team schedules and game results
- Matchup history between teams
- NFL Draft picks by school
- Transfer portal data
- Betting lines
- Advanced ratings (SP+, SRS, Elo)
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


def get_current_cfb_season() -> int:
    """
    Get the current CFB season year.

    CFB seasons run Aug-Jan, so:
    - Jan-July: Previous year's season (Jan 2026 = 2025 season)
    - Aug-Dec: Current year's season (Sept 2025 = 2025 season)
    """
    now = datetime.now()
    if now.month < 8:  # Before August = previous year's season
        return now.year - 1
    return now.year

logger = logging.getLogger(__name__)

# Try to import cfbd library
try:
    import cfbd
    from cfbd.rest import ApiException
    CFBD_AVAILABLE = True
except ImportError:
    CFBD_AVAILABLE = False
    logger.warning("⚠️ cfbd library not installed - player lookup disabled")


class CFBDataLookup:
    """
    Comprehensive CFB data lookups from CollegeFootballData.com API.

    Features:
    - Player search and stats
    - Team rosters and info
    - Rankings (AP, Coaches, CFP)
    - Matchup history
    - Game schedules and results
    - NFL Draft picks
    - Transfer portal
    - Betting lines
    - Advanced stats (SP+, SRS, Elo)
    """

    # FCS Conferences - these have limited data coverage in CFBD
    FCS_CONFERENCES = {
        'big sky', 'big south', 'caa', 'colonial athletic', 'ivy league', 'ivy',
        'meac', 'mid-eastern', 'missouri valley', 'mvfc', 'northeast', 'nec',
        'ohio valley', 'ovc', 'patriot', 'pioneer', 'southern', 'socon',
        'southland', 'swac', 'southwestern athletic', 'united athletic', 'uac'
    }

    # Known FCS Schools (partial list of common ones)
    FCS_SCHOOLS = {
        # Big Sky
        'montana', 'montana state', 'eastern washington', 'weber state', 'sacramento state',
        'uc davis', 'northern arizona', 'idaho state', 'portland state', 'cal poly',
        # CAA
        'delaware', 'villanova', 'james madison', 'richmond', 'william & mary',
        'towson', 'elon', 'rhode island', 'maine', 'new hampshire', 'stony brook',
        # Ivy League
        'harvard', 'yale', 'princeton', 'penn', 'columbia', 'brown', 'dartmouth', 'cornell',
        # MEAC
        'north carolina a&t', 'nc a&t', 'howard', 'morgan state', 'norfolk state',
        'south carolina state', 'delaware state', 'bethune-cookman',
        # Missouri Valley (MVFC)
        'north dakota state', 'ndsu', 'south dakota state', 'sdsu', 'northern iowa',
        'illinois state', 'indiana state', 'missouri state', 'southern illinois',
        'youngstown state', 'south dakota', 'north dakota',
        # Ohio Valley
        'southeast missouri', 'semo', 'ut martin', 'tennessee state', 'tennessee tech',
        'eastern illinois', 'murray state', 'austin peay', 'lindenwood',
        # Patriot League
        'lehigh', 'lafayette', 'bucknell', 'colgate', 'fordham', 'georgetown', 'holy cross',
        # Southern (SoCon)
        'furman', 'chattanooga', 'etsu', 'east tennessee', 'east tennessee state',
        'mercer', 'wofford', 'the citadel', 'citadel', 'western carolina', 'samford', 'vmi',
        # Southland
        'mcneese', 'nicholls', 'nicholls state', 'southeastern louisiana',
        'houston christian', 'incarnate word', 'lamar',
        # SWAC
        'jackson state', 'southern', 'grambling', 'alcorn state', 'alabama a&m',
        'alabama state', 'prairie view', 'arkansas pine bluff', 'texas southern',
        # Big South / OVC / Others
        'gardner-webb', 'charleston southern', 'presbyterian', 'campbell',
        'north alabama', 'kennesaw state', 'monmouth', 'sacred heart',
        'central connecticut', 'duquesne', 'long island', 'liu', 'wagner',
        'robert morris', 'bryant', 'merrimack', 'st. francis', 'stonehill',
        # Independent FCS
        'tarleton', 'tarleton state', 'dixie state', 'utah tech'
    }

    def __init__(self):
        self.api_key = os.getenv('CFB_DATA_API_KEY')
        self._api_client = None

        # API instances
        self._players_api = None
        self._stats_api = None
        self._recruiting_api = None
        self._teams_api = None
        self._games_api = None
        self._rankings_api = None
        self._betting_api = None
        self._ratings_api = None
        self._draft_api = None
        
        # Simple cache to avoid repeated API calls (reduces rate limiting)
        self._search_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._cache_expiry: Dict[str, float] = {}
        self._cache_ttl = 300  # 5 minutes cache

        if not CFBD_AVAILABLE:
            logger.warning("⚠️ cfbd library not available - CFB data disabled")
            return

        if not self.api_key:
            logger.warning("⚠️ CFB_DATA_API_KEY not found - CFB data disabled")
            return

        # Configure the API client
        try:
            configuration = cfbd.Configuration(
                access_token=self.api_key
            )
            self._api_client = cfbd.ApiClient(configuration)

            # Initialize all API instances
            self._players_api = cfbd.PlayersApi(self._api_client)
            self._stats_api = cfbd.StatsApi(self._api_client)
            self._recruiting_api = cfbd.RecruitingApi(self._api_client)
            self._teams_api = cfbd.TeamsApi(self._api_client)
            self._games_api = cfbd.GamesApi(self._api_client)
            self._rankings_api = cfbd.RankingsApi(self._api_client)
            self._betting_api = cfbd.BettingApi(self._api_client)
            self._ratings_api = cfbd.RatingsApi(self._api_client)
            self._draft_api = cfbd.DraftApi(self._api_client)

            logger.info("✅ CFBD API configured successfully with all endpoints")
        except Exception as e:
            logger.error(f"❌ Failed to configure CFBD API: {e}")
            self._api_client = None

    @property
    def is_available(self) -> bool:
        """Check if the API is available"""
        return CFBD_AVAILABLE and self._api_client is not None

    def is_fcs_school(self, team: str) -> bool:
        """Check if a school is likely FCS (limited data coverage)"""
        if not team:
            return False
        team_lower = team.lower().strip()
        return team_lower in self.FCS_SCHOOLS

    def get_not_found_reason(self, name: str, team: Optional[str]) -> str:
        """Determine why a player wasn't found and return helpful message"""
        if team and self.is_fcs_school(team):
            return f"⚠️ {team} is an FCS school - CFBD has limited FCS data"
        return "❓ Player not in database - check spelling or try without team"

    async def find_similar_players(self, name: str, team: Optional[str] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Find players with similar names for "Did you mean?" suggestions.

        Tries:
        1. First name only search
        2. Last name only search
        3. Partial name match across all teams
        """
        if not self.is_available:
            return []

        suggestions = []
        seen_ids = set()

        # Parse name into parts
        name_parts = name.strip().split()
        first_name = name_parts[0] if name_parts else name
        last_name = name_parts[-1] if len(name_parts) > 1 else name

        try:
            # Try last name search (usually more unique)
            if len(last_name) >= 3:
                results = await asyncio.to_thread(
                    self._players_api.search_players,
                    search_term=last_name,
                    year=2025
                )
                for p in (results or [])[:5]:
                    pid = getattr(p, 'id', None)
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        p_name = f"{getattr(p, 'first_name', '')} {getattr(p, 'last_name', '')}".strip()
                        suggestions.append({
                            'name': p_name,
                            'team': getattr(p, 'team', 'Unknown'),
                            'position': getattr(p, 'position', '?'),
                            'id': pid
                        })

            # Try first name if we don't have enough suggestions
            if len(suggestions) < limit and len(first_name) >= 3:
                results = await asyncio.to_thread(
                    self._players_api.search_players,
                    search_term=first_name,
                    year=2025
                )
                for p in (results or [])[:5]:
                    pid = getattr(p, 'id', None)
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        p_name = f"{getattr(p, 'first_name', '')} {getattr(p, 'last_name', '')}".strip()
                        suggestions.append({
                            'name': p_name,
                            'team': getattr(p, 'team', 'Unknown'),
                            'position': getattr(p, 'position', '?'),
                            'id': pid
                        })

        except Exception as e:
            logger.debug(f"Error finding similar players: {e}")

        return suggestions[:limit]

    async def search_player(self, name: str, team: Optional[str] = None, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for players by name using official API

        Args:
            name: Player name to search for
            team: Optional team name to filter by
            year: Season year (optional)

        Returns:
            List of matching players
        """
        if not self.is_available:
            logger.warning("Player lookup not available")
            return []

        # Check cache first
        import time
        cache_key = f"search:{name.lower()}:{team or ''}:{year or ''}"
        if cache_key in self._search_cache:
            if time.time() < self._cache_expiry.get(cache_key, 0):
                logger.info(f"📦 Cache hit for '{name}'")
                return self._search_cache[cache_key]
            else:
                # Expired, remove from cache
                del self._search_cache[cache_key]
                del self._cache_expiry[cache_key]

        # Try current and recent years - 2025 data may not be available yet
        years_to_try = [year] if year else [2024, 2023, 2025, 2022]
        retry_delay = 2  # Start with 2 second delay, increase on consecutive 429s
        consecutive_429s = 0

        for try_year in years_to_try:
            try:
                logger.info(f"🔍 Searching CFBD for '{name}' (year={try_year}, team={team})")

                # Run sync API call in thread pool
                kwargs = {'search_term': name, 'year': try_year}
                if team:
                    kwargs['team'] = team

                results = await asyncio.to_thread(
                    self._players_api.search_players,
                    **kwargs
                )

                if results:
                    # Convert to dicts
                    players = [self._player_to_dict(p) for p in results]
                    logger.info(f"✅ Found {len(players)} players for year {try_year}")
                    # Cache the result
                    self._search_cache[cache_key] = players
                    self._cache_expiry[cache_key] = time.time() + self._cache_ttl
                    return players
                else:
                    logger.info(f"No results for year {try_year}, trying next...")
                    consecutive_429s = 0  # Reset on successful call

            except ApiException as e:
                logger.error(f"❌ CFBD API error: {e.status} - {e.reason}")
                if e.status == 401:
                    logger.error("Authentication failed - check your API key")
                    return []
                elif e.status == 429:
                    consecutive_429s += 1
                    # Exponential backoff: 2s, 4s, 8s, max 30s
                    wait_time = min(retry_delay * (2 ** (consecutive_429s - 1)), 30)
                    logger.warning(f"⏳ Rate limited ({consecutive_429s}x), waiting {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    
                    # After 3 consecutive 429s, give up (API quota likely exhausted)
                    if consecutive_429s >= 3:
                        logger.error("❌ Too many rate limits - API quota may be exhausted")
                        # Cache empty result to avoid hammering API
                        self._search_cache[cache_key] = []
                        self._cache_expiry[cache_key] = time.time() + 60  # Cache for 1 min
                        return []
                    continue  # Try same year again
            except Exception as e:
                logger.error(f"❌ Error searching for player: {e}", exc_info=True)

        # Cache empty result
        self._search_cache[cache_key] = []
        self._cache_expiry[cache_key] = time.time() + self._cache_ttl
        return []

    def _player_to_dict(self, player) -> Dict[str, Any]:
        """Convert cfbd PlayerSearchResult to dict"""
        return {
            'id': getattr(player, 'id', None),
            'name': getattr(player, 'name', None),
            'firstName': getattr(player, 'first_name', None),
            'lastName': getattr(player, 'last_name', None),
            'team': getattr(player, 'team', None),
            'position': getattr(player, 'position', None),
            'height': getattr(player, 'height', None),
            'weight': getattr(player, 'weight', None),
            'year': getattr(player, 'year', None),
            'jersey': getattr(player, 'jersey', None),
            'homeCity': getattr(player, 'home_city', None),
            'homeState': getattr(player, 'home_state', None),
            'homeCountry': getattr(player, 'home_country', None),
        }

    async def get_roster(self, team: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get full roster for a team

        Args:
            team: Team name
            year: Season year (optional)

        Returns:
            List of players on roster
        """
        if not self.is_available:
            return []

        years_to_try = [year] if year else [2025, 2024, 2023]

        for try_year in years_to_try:
            try:
                logger.info(f"🔍 Fetching roster for {team} ({try_year})")

                results = await asyncio.to_thread(
                    self._teams_api.get_roster,
                    team=team,
                    year=try_year
                )

                if results:
                    roster = [self._roster_player_to_dict(p) for p in results]
                    logger.info(f"✅ Found {len(roster)} players on {team} roster")
                    return roster

            except ApiException as e:
                logger.error(f"❌ CFBD API error: {e.status} - {e.reason}")
            except Exception as e:
                logger.error(f"❌ Error fetching roster: {e}", exc_info=True)

        return []

    def _roster_player_to_dict(self, player) -> Dict[str, Any]:
        """Convert cfbd RosterPlayer to dict"""
        return {
            'id': getattr(player, 'id', None),
            'name': f"{getattr(player, 'first_name', '')} {getattr(player, 'last_name', '')}".strip(),
            'firstName': getattr(player, 'first_name', None),
            'lastName': getattr(player, 'last_name', None),
            'team': getattr(player, 'team', None),
            'position': getattr(player, 'position', None),
            'height': getattr(player, 'height', None),
            'weight': getattr(player, 'weight', None),
            'year': getattr(player, 'year', None),
            'jersey': getattr(player, 'jersey', None),
            'homeCity': getattr(player, 'home_city', None),
            'homeState': getattr(player, 'home_state', None),
            'homeCountry': getattr(player, 'home_country', None),
        }

    async def get_player_stats(self, player_name: str, team: str, year: int = 2024) -> Optional[Dict[str, Any]]:
        """
        Get season stats for a specific player

        Args:
            player_name: Player name to search for
            team: Team name
            year: Season year

        Returns:
            Player stats dictionary
        """
        if not self.is_available:
            return None

        logger.info(f"🔍 Fetching stats for {player_name} on {team} ({year})")

        try:
            # Get all player stats for the team
            results = await asyncio.to_thread(
                self._stats_api.get_player_season_stats,
                year=year,
                team=team
            )

            if results:
                logger.info(f"✅ Found {len(results)} stat entries for {team}")

                # Filter for the specific player (case-insensitive partial match)
                player_stats = [
                    s for s in results
                    if player_name.lower() in getattr(s, 'player', '').lower()
                ]

                if player_stats:
                    logger.info(f"✅ Found {len(player_stats)} stat entries for {player_name}")
                    return self._parse_stats(player_stats)
                else:
                    logger.info(f"No stats found for {player_name} in team stats")

            return None

        except ApiException as e:
            logger.error(f"❌ CFBD API error: {e.status} - {e.reason}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching player stats: {e}", exc_info=True)
            return None

    async def get_recruiting_info(self, player_name: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get recruiting info for a player

        Args:
            player_name: Player name to search
            year: Recruiting class year (optional)

        Returns:
            Recruiting info dictionary
        """
        if not self.is_available:
            return None

        # Try multiple recruiting classes
        years_to_try = [year] if year else [2025, 2024, 2023, 2022]

        for try_year in years_to_try:
            try:
                logger.info(f"🔍 Searching recruiting data for '{player_name}' ({try_year})")

                results = await asyncio.to_thread(
                    self._recruiting_api.get_recruits,
                    year=try_year
                )

                if results:
                    # Search for matching name (partial, case-insensitive)
                    for recruit in results:
                        recruit_name = getattr(recruit, 'name', '')
                        if player_name.lower() in recruit_name.lower():
                            logger.info(f"✅ Found recruiting info for {recruit_name}")
                            return {
                                'name': recruit_name,
                                'school': getattr(recruit, 'committed_to', None),
                                'position': getattr(recruit, 'position', None),
                                'stars': getattr(recruit, 'stars', None),
                                'rating': getattr(recruit, 'rating', None),
                                'ranking': getattr(recruit, 'ranking', None),
                                'stateRank': getattr(recruit, 'state_rank', None),
                                'positionRank': getattr(recruit, 'position_rank', None),
                                'city': getattr(recruit, 'city', None),
                                'state': getattr(recruit, 'state_province', None),
                                'country': getattr(recruit, 'country', None),
                                'height': getattr(recruit, 'height', None),
                                'weight': getattr(recruit, 'weight', None),
                                'year': try_year,
                                'high_school': getattr(recruit, 'high_school', None),
                                'early_signing': getattr(recruit, 'early_signing', None),
                                'early_enroll': getattr(recruit, 'early_enroll', None),
                            }

            except ApiException as e:
                logger.warning(f"Recruiting API error for {try_year}: {e.status}")
            except Exception as e:
                logger.error(f"❌ Error fetching recruiting info: {e}", exc_info=True)

        return None

    async def get_transfer_portal(self, year: int = 2024) -> List[Dict[str, Any]]:
        """
        Get transfer portal data for a year

        Args:
            year: Transfer portal year

        Returns:
            List of transfer portal entries
        """
        if not self.is_available:
            return []

        try:
            logger.info(f"🔍 Fetching transfer portal data ({year})")

            results = await asyncio.to_thread(
                self._players_api.get_transfer_portal,
                year=year
            )

            if results:
                transfers = []
                for t in results:
                    transfers.append({
                        'name': f"{getattr(t, 'first_name', '')} {getattr(t, 'last_name', '')}".strip(),
                        'position': getattr(t, 'position', None),
                        'origin': getattr(t, 'origin', None),
                        'destination': getattr(t, 'destination', None),
                        'transferDate': getattr(t, 'transfer_date', None),
                        'rating': getattr(t, 'rating', None),
                        'stars': getattr(t, 'stars', None),
                        'eligibility': getattr(t, 'eligibility', None),
                    })
                logger.info(f"✅ Found {len(transfers)} transfer portal entries")
                return transfers

        except ApiException as e:
            logger.error(f"❌ CFBD API error: {e.status} - {e.reason}")
        except Exception as e:
            logger.error(f"❌ Error fetching transfer portal: {e}", exc_info=True)

        return []

    async def search_transfer(self, player_name: str, year: int = 2024) -> Optional[Dict[str, Any]]:
        """
        Search for a player in the transfer portal

        Args:
            player_name: Player name to search
            year: Transfer portal year

        Returns:
            Transfer info or None
        """
        transfers = await self.get_transfer_portal(year)

        for t in transfers:
            if player_name.lower() in t.get('name', '').lower():
                logger.info(f"✅ Found transfer info for {t.get('name')}")
                return t

        # Try previous year
        if year > 2022:
            transfers = await self.get_transfer_portal(year - 1)
            for t in transfers:
                if player_name.lower() in t.get('name', '').lower():
                    logger.info(f"✅ Found transfer info for {t.get('name')} ({year-1})")
                    return t

        return None

    def _parse_stats(self, raw_stats: List) -> Dict[str, Any]:
        """
        Parse raw stats into a cleaner format

        Args:
            raw_stats: Raw stats from API

        Returns:
            Parsed stats dictionary
        """
        parsed = {
            'passing': {},
            'rushing': {},
            'receiving': {},
            'defense': {},
            'kicking': {},
            'punting': {},
            'returns': {},
        }

        for stat_entry in raw_stats:
            category = getattr(stat_entry, 'category', '').lower()
            stat_type = getattr(stat_entry, 'stat_type', '')
            stat_value = getattr(stat_entry, 'stat', 0)

            if 'pass' in category:
                parsed['passing'][stat_type] = stat_value
            elif 'rush' in category:
                parsed['rushing'][stat_type] = stat_value
            elif 'receiv' in category:
                parsed['receiving'][stat_type] = stat_value
            elif category in ['defense', 'defensive', 'tackles', 'interceptions', 'fumbles']:
                parsed['defense'][stat_type] = stat_value
            elif 'kick' in category and 'return' not in category:
                parsed['kicking'][stat_type] = stat_value
            elif 'punt' in category and 'return' not in category:
                parsed['punting'][stat_type] = stat_value
            elif 'return' in category:
                parsed['returns'][stat_type] = stat_value

        return parsed

    async def get_full_player_info(self, name: str, team: Optional[str] = None, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive player info including vitals, stats, recruiting, and transfer info

        Args:
            name: Player name
            team: Optional team name
            year: Season year (optional)

        Returns:
            Full player info dictionary or None if not found
        """
        if not self.is_available:
            logger.warning("Player lookup not available - no API configured")
            return None

        logger.info(f"🔍 Looking up player: {name}" + (f" from {team}" if team else ""))

        # Search for the player
        players = await self.search_player(name, team, year)

        if not players and team:
            # Try without team filter
            logger.info("No results with team filter, trying without...")
            players = await self.search_player(name, year=year)

        if not players:
            logger.info(f"❌ No players found matching '{name}'")
            return None

        logger.info(f"✅ Found {len(players)} potential matches")

        # Get the best match
        player = None
        if team:
            team_lower = team.lower()
            for p in players:
                if team_lower in (p.get('team') or '').lower():
                    player = p
                    logger.info(f"✅ Matched player to team: {p.get('name')} - {p.get('team')}")
                    break

        if not player:
            player = players[0]
            logger.info(f"✅ Using first result: {player.get('name')} - {player.get('team')}")

        # Get additional info in parallel
        player_name = player.get('name', name)
        player_team = player.get('team', team or '')

        # Fetch stats, recruiting, and transfer info concurrently
        stats = None
        recruiting = None
        transfer = None

        tasks = []

        if player_team:
            # Stats for ALL available years - PARALLEL FETCH
            async def get_all_stats():
                all_stats = {}
                years_to_check = [2025, 2024, 2023, 2022, 2021]
                
                # Create parallel tasks for all years
                year_tasks = [
                    self.get_player_stats(player_name, player_team, year)
                    for year in years_to_check
                ]
                
                # Fetch all years in parallel
                logger.info(f"🚀 Fetching stats for {len(years_to_check)} years in parallel...")
                year_results = await asyncio.gather(*year_tasks, return_exceptions=True)
                
                # Process results
                for year, result in zip(years_to_check, year_results):
                    if isinstance(result, Exception):
                        logger.debug(f"⚠️ Error fetching {year}: {result}")
                    elif result and any(v for v in result.values() if v):
                        logger.info(f"✅ Found stats for {year} season")
                        all_stats[year] = result
                
                return all_stats if all_stats else None

            tasks.append(('stats', get_all_stats()))

        tasks.append(('recruiting', self.get_recruiting_info(player_name)))
        tasks.append(('transfer', self.search_transfer(player_name)))

        # Run all tasks concurrently
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

        for i, (task_name, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Error in {task_name}: {result}")
            elif task_name == 'stats':
                stats = result
            elif task_name == 'recruiting':
                recruiting = result
            elif task_name == 'transfer':
                transfer = result

        return {
            'player': player,
            'stats': stats,
            'recruiting': recruiting,
            'transfer': transfer,
        }

    def format_player_response(self, player_info: Dict[str, Any]) -> str:
        """
        Format player info into a nice Discord response

        Args:
            player_info: Full player info from get_full_player_info

        Returns:
            Formatted string for Discord
        """
        if not player_info:
            return "Couldn't find that player, mate. Check the spelling or try another name."

        player = player_info.get('player', {})
        stats = player_info.get('stats')
        recruiting = player_info.get('recruiting')
        transfer = player_info.get('transfer')

        # Basic info
        name = player.get('name') or f"{player.get('firstName', '')} {player.get('lastName', '')}".strip()
        team = player.get('team', 'Unknown')
        position = player.get('position', 'Unknown')

        # Physical attributes
        height = player.get('height')
        weight = player.get('weight')
        year_str = player.get('year', '')
        jersey = player.get('jersey')

        # Format height
        if height:
            if isinstance(height, (int, float)) and height > 12:
                feet = int(height) // 12
                inches = int(height) % 12
                height_fmt = f"{feet}'{inches}\""
            else:
                height_fmt = str(height)
        else:
            height_fmt = None

        weight_fmt = f"{weight}lbs" if weight else None

        # Build response
        response_parts = []

        # Header
        response_parts.append(f"🏈 **{name}** - {team}")

        # Vitals line
        vitals = []
        if position:
            vitals.append(f"**Position:** {position}")
        if jersey:
            vitals.append(f"**#**{jersey}")
        if year_str:
            vitals.append(f"**Year:** {year_str}")
        if height_fmt:
            vitals.append(f"**{height_fmt}**")
        if weight_fmt:
            vitals.append(f"**{weight_fmt}**")

        if vitals:
            response_parts.append(" | ".join(vitals))

        # Hometown
        hometown = player.get('homeCity', '')
        home_state = player.get('homeState', '')
        home_country = player.get('homeCountry', '')
        
        location_parts = []
        if hometown:
            location_parts.append(hometown)
        if home_state:
            location_parts.append(home_state)
        # Only show country if it's not USA (or empty/null)
        if home_country and home_country.upper() not in ['USA', 'US', 'UNITED STATES']:
            location_parts.append(home_country)
        
        if location_parts:
            location = ', '.join(location_parts)
            response_parts.append(f"📍 {location}")

        response_parts.append("")

        # Transfer info (if applicable)
        if transfer:
            origin = transfer.get('origin', 'Unknown')
            destination = transfer.get('destination', 'Unknown')
            response_parts.append(f"🔄 **Transfer:** {origin} → {destination}")
            if transfer.get('eligibility'):
                response_parts.append(f"   Eligibility: {transfer.get('eligibility')}")
            response_parts.append("")

        # Stats section (multi-year)
        if stats and isinstance(stats, dict):
            has_any_stats = False

            # Sort years descending (most recent first)
            for year in sorted(stats.keys(), reverse=True):
                year_stats = stats[year]
                year_has_stats = False
                year_parts = []

                # Helper function to safely convert stat values to int/float
                def safe_int(val, default=0):
                    """Convert value to int, handling strings and None"""
                    if val is None or val == '':
                        return default
                    try:
                        return int(float(val))  # Handle both "15" and "15.0"
                    except (ValueError, TypeError):
                        return default
                
                def safe_float(val, default=0.0):
                    """Convert value to float, handling strings and None"""
                    if val is None or val == '':
                        return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                # Passing
                passing = year_stats.get('passing', {})
                if passing:
                    comp = safe_int(passing.get('COMPLETIONS', passing.get('completions', 0)))
                    att = safe_int(passing.get('ATT', passing.get('attempts', 0)))
                    yards = safe_int(passing.get('YDS', passing.get('yards', 0)))
                    tds = safe_int(passing.get('TD', passing.get('touchdowns', 0)))
                    ints = safe_int(passing.get('INT', passing.get('interceptions', 0)))
                    long = safe_int(passing.get('LONG', passing.get('LNG', 0)))
                    
                    if any([comp, yards, tds]):
                        # Calculate completion % and YPA
                        comp_pct = f"{(comp/att*100):.1f}%" if att > 0 else "0.0%"
                        ypa = f"{yards/att:.1f}" if att > 0 else "0.0"
                        
                        pass_parts = [f"{comp}/{att} ({comp_pct})", f"{yards} YDS ({ypa} YPA)", f"{tds} TD", f"{ints} INT"]
                        if long:
                            pass_parts.append(f"{long} Long")
                        year_parts.append(f"🏈 {' | '.join(pass_parts)}")
                        year_has_stats = True

                # Rushing
                rushing = year_stats.get('rushing', {})
                if rushing:
                    carries = safe_int(rushing.get('CAR', rushing.get('carries', 0)))
                    yards = safe_int(rushing.get('YDS', rushing.get('yards', 0)))
                    tds = safe_int(rushing.get('TD', rushing.get('touchdowns', 0)))
                    long = safe_int(rushing.get('LONG', rushing.get('LNG', 0)))
                    
                    if any([carries, yards, tds]):
                        ypc = f"{yards/carries:.1f}" if carries > 0 else "0.0"
                        rush_parts = [f"{carries} CAR", f"{yards} YDS ({ypc} YPC)", f"{tds} TD"]
                        if long:
                            rush_parts.append(f"{long} Long")
                        year_parts.append(f"🏃 {' | '.join(rush_parts)}")
                        year_has_stats = True

                # Receiving
                receiving = year_stats.get('receiving', {})
                if receiving:
                    rec = safe_int(receiving.get('REC', receiving.get('receptions', 0)))
                    yards = safe_int(receiving.get('YDS', receiving.get('yards', 0)))
                    tds = safe_int(receiving.get('TD', receiving.get('touchdowns', 0)))
                    long = safe_int(receiving.get('LONG', receiving.get('LNG', 0)))
                    
                    if any([rec, yards, tds]):
                        ypr = f"{yards/rec:.1f}" if rec > 0 else "0.0"
                        rec_parts = [f"{rec} REC", f"{yards} YDS ({ypr} YPR)", f"{tds} TD"]
                        if long:
                            rec_parts.append(f"{long} Long")
                        year_parts.append(f"🎯 {' | '.join(rec_parts)}")
                        year_has_stats = True

                # Defense
                defense = year_stats.get('defense', {})
                if defense:
                    tackles = safe_int(defense.get('TOT', defense.get('SOLO', defense.get('tackles', 0))))
                    solo = safe_int(defense.get('SOLO', 0))
                    tfl = safe_float(defense.get('TFL', 0))
                    sacks = safe_float(defense.get('SACKS', defense.get('SK', 0)))
                    ints = safe_int(defense.get('INT', 0))
                    pd = safe_int(defense.get('PD', 0))  # Pass Deflections
                    qb_hur = safe_int(defense.get('QBH', defense.get('QB HUR', 0)))  # QB Hurries
                    ff = safe_int(defense.get('FF', 0))  # Forced Fumbles
                    fr = safe_int(defense.get('FR', 0))  # Fumble Recoveries
                    
                    if any([tackles, solo, tfl, sacks, ints, pd, qb_hur, ff, fr]):
                        stat_parts = []
                        if tackles:
                            stat_parts.append(f"{tackles} TKL")
                        if solo:
                            stat_parts.append(f"{solo} Solo")
                        if tfl:
                            stat_parts.append(f"{tfl:.1f} TFL" if isinstance(tfl, float) and tfl % 1 != 0 else f"{int(tfl)} TFL")
                        if sacks:
                            stat_parts.append(f"{sacks:.1f} Sacks" if isinstance(sacks, float) and sacks % 1 != 0 else f"{int(sacks)} Sacks")
                        if qb_hur:
                            stat_parts.append(f"{qb_hur} QBH")
                        if ints:
                            stat_parts.append(f"{ints} INT")
                        if pd:
                            stat_parts.append(f"{pd} PD")
                        if ff:
                            stat_parts.append(f"{ff} FF")
                        if fr:
                            stat_parts.append(f"{fr} FR")
                        year_parts.append(f"🛡️ {' | '.join(stat_parts)}")
                        year_has_stats = True

                # Kicking
                kicking = year_stats.get('kicking', {})
                if kicking:
                    fgm = safe_int(kicking.get('FGM', 0))
                    fga = safe_int(kicking.get('FGA', 0))
                    xpm = safe_int(kicking.get('XPM', 0))
                    long_fg = safe_int(kicking.get('LONG', kicking.get('LNG', 0)))
                    if any([fgm, fga, xpm]):
                        kick_parts = [f"{fgm}/{fga} FG"]
                        if xpm:
                            kick_parts.append(f"{xpm} XP")
                        if long_fg:
                            kick_parts.append(f"{long_fg} Long")
                        year_parts.append(f"🦵 {' | '.join(kick_parts)}")
                        year_has_stats = True

                # Punting
                punting = year_stats.get('punting', {})
                if punting:
                    punts = safe_int(punting.get('NO', punting.get('PUNTS', 0)))
                    punt_yds = safe_int(punting.get('YDS', punting.get('YARDS', 0)))
                    avg = safe_float(punting.get('AVG', 0))
                    tb = safe_int(punting.get('TB', 0))  # Touchbacks
                    in20 = safe_int(punting.get('IN 20', punting.get('IN20', 0)))
                    long_punt = safe_int(punting.get('LONG', punting.get('LNG', 0)))
                    
                    if any([punts, punt_yds, avg]):
                        punt_parts = []
                        if punts:
                            punt_parts.append(f"{punts} Punts")
                        if punt_yds:
                            punt_parts.append(f"{punt_yds} YDS")
                        if avg:
                            punt_parts.append(f"{avg:.1f} AVG")
                        if in20:
                            punt_parts.append(f"{in20} In20")
                        if long_punt:
                            punt_parts.append(f"{long_punt} Long")
                        year_parts.append(f"🥾 {' | '.join(punt_parts)}")
                        year_has_stats = True

                # Returns
                returns = year_stats.get('returns', {})
                if returns:
                    kr = safe_int(returns.get('KR', 0))  # Kick Returns
                    kr_yds = safe_int(returns.get('KR YDS', returns.get('KRYDS', 0)))
                    kr_td = safe_int(returns.get('KR TD', returns.get('KRTD', 0)))
                    pr = safe_int(returns.get('PR', 0))  # Punt Returns
                    pr_yds = safe_int(returns.get('PR YDS', returns.get('PRYDS', 0)))
                    pr_td = safe_int(returns.get('PR TD', returns.get('PRTD', 0)))
                    
                    if any([kr, kr_yds, kr_td, pr, pr_yds, pr_td]):
                        return_parts = []
                        if kr or kr_yds:
                            kr_avg = f"{kr_yds/kr:.1f}" if kr and kr > 0 else "0.0"
                            kr_part = f"KR: {kr} RET | {kr_yds} YDS ({kr_avg} AVG)"
                            if kr_td:
                                kr_part += f" | {kr_td} TD"
                            return_parts.append(kr_part)
                        if pr or pr_yds:
                            pr_avg = f"{pr_yds/pr:.1f}" if pr and pr > 0 else "0.0"
                            pr_part = f"PR: {pr} RET | {pr_yds} YDS ({pr_avg} AVG)"
                            if pr_td:
                                pr_part += f" | {pr_td} TD"
                            return_parts.append(pr_part)
                        if return_parts:
                            year_parts.append(f"⚡ {' | '.join(return_parts)}")
                            year_has_stats = True

                if year_has_stats:
                    response_parts.append(f"📊 **{year} Season:**")
                    for part in year_parts:
                        response_parts.append(f"   {part}")
                    response_parts.append("")  # Blank line between seasons
                    has_any_stats = True

            if not has_any_stats:
                response_parts.append("📊 *No stats recorded*")
        else:
            response_parts.append("📊 *No stats available*")

        # Recruiting info
        if recruiting:
            response_parts.append("")
            stars = recruiting.get('stars', 0)
            rating = recruiting.get('rating', 0)
            ranking = recruiting.get('ranking')
            pos_rank = recruiting.get('positionRank')
            state_rank = recruiting.get('stateRank')
            recruit_year = recruiting.get('year')
            committed_school = recruiting.get('school')
            recruit_city = recruiting.get('city')
            recruit_state = recruiting.get('state')
            recruit_height = recruiting.get('height')
            recruit_weight = recruiting.get('weight')
            recruit_position = recruiting.get('position')

            star_display = "⭐" * stars if stars else "N/R"

            # Header with stars and rating
            if rating:
                response_parts.append(f"🎯 **Recruiting ({recruit_year or 'N/A'} Class):** {star_display} ({rating:.4f})")
            else:
                response_parts.append(f"🎯 **Recruiting ({recruit_year or 'N/A'} Class):** {star_display}")

            # Rankings
            ranks = []
            if ranking:
                ranks.append(f"#{ranking} National")
            if pos_rank:
                ranks.append(f"#{pos_rank} {recruit_position or 'Pos'}")
            if state_rank:
                ranks.append(f"#{state_rank} {recruit_state or 'State'}")

            if ranks:
                response_parts.append(f"   **Rankings:** {' | '.join(ranks)}")

            # Committed School
            if committed_school:
                response_parts.append(f"   **Signed With:** {committed_school}")

            # Hometown (from recruiting profile)
            recruit_location = []
            if recruit_city:
                recruit_location.append(recruit_city)
            if recruit_state:
                recruit_location.append(recruit_state)
            
            # Add country if international (non-USA)
            recruit_country = recruiting.get('country', '')
            if recruit_country and recruit_country.upper() not in ['USA', 'US', 'UNITED STATES', '']:
                recruit_location.append(recruit_country)
            
            if recruit_location:
                response_parts.append(f"   **Hometown:** {', '.join(recruit_location)}")

            # High School
            high_school = recruiting.get('high_school')
            if high_school:
                response_parts.append(f"   **High School:** {high_school}")

            # Physical measurements (from recruiting profile)
            recruit_vitals = []
            if recruit_height:
                # Format height if it's in inches
                if isinstance(recruit_height, (int, float)) and recruit_height > 12:
                    feet = int(recruit_height) // 12
                    inches = int(recruit_height) % 12
                    recruit_vitals.append(f"{feet}'{inches}\"")
                else:
                    recruit_vitals.append(str(recruit_height))
            
            if recruit_weight:
                recruit_vitals.append(f"{recruit_weight}lbs")

            if recruit_vitals:
                response_parts.append(f"   **Recruiting Vitals:** {' | '.join(recruit_vitals)}")

            # Early Signing/Enrollment status
            early_info = []
            if recruiting.get('early_signing'):
                early_info.append("Early Signing Period")
            if recruiting.get('early_enroll'):
                early_info.append("Early Enrollee")
            
            if early_info:
                response_parts.append(f"   **Status:** {' | '.join(early_info)}")

        return "\n".join(response_parts)

    # ==================== TEAM FEATURES ====================

    async def get_team_info(self, team: str) -> Optional[Dict[str, Any]]:
        """Get basic team information"""
        if not self.is_available:
            return None

        try:
            results = await asyncio.to_thread(
                self._teams_api.get_teams,
                conference=None
            )

            if results:
                team_lower = team.lower()
                for t in results:
                    if (team_lower in getattr(t, 'school', '').lower() or
                        team_lower in getattr(t, 'mascot', '').lower()):
                        return {
                            'school': getattr(t, 'school', None),
                            'mascot': getattr(t, 'mascot', None),
                            'abbreviation': getattr(t, 'abbreviation', None),
                            'conference': getattr(t, 'conference', None),
                            'division': getattr(t, 'division', None),
                            'color': getattr(t, 'color', None),
                            'alt_color': getattr(t, 'alt_color', None),
                            'logos': getattr(t, 'logos', []),
                        }
            return None
        except Exception as e:
            logger.error(f"Error getting team info: {e}")
            return None

    async def get_rankings(self, year: int = None, week: Optional[int] = None, latest_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get team rankings (AP, Coaches, CFP)

        Args:
            year: Season year (default: current season)
            week: Specific week (if None and latest_only=True, gets most recent)
            latest_only: If True, only return the most recent week's rankings

        Returns list of polls with their rankings
        """
        if not self.is_available:
            return []

        # Default to current season
        if year is None:
            year = get_current_cfb_season()

        try:
            logger.info(f"🔍 Fetching rankings for {year}" + (f" week {week}" if week else " (latest)"))

            kwargs = {'year': year}
            if week:
                kwargs['week'] = week

            results = await asyncio.to_thread(
                self._rankings_api.get_rankings,
                **kwargs
            )

            if results:
                # Find the latest week if not specified
                if latest_only and not week:
                    max_week = max(getattr(pw, 'week', 0) for pw in results)
                    results = [pw for pw in results if getattr(pw, 'week', 0) == max_week]
                    logger.info(f"📅 Using latest week: {max_week}")

                rankings = []
                for poll_week in results:
                    week_num = getattr(poll_week, 'week', None)
                    for poll in getattr(poll_week, 'polls', []):
                        poll_name = getattr(poll, 'poll', 'Unknown')
                        poll_ranks = []
                        for rank in getattr(poll, 'ranks', []):
                            poll_ranks.append({
                                'rank': getattr(rank, 'rank', None),
                                'school': getattr(rank, 'school', None),
                                'conference': getattr(rank, 'conference', None),
                                'firstPlaceVotes': getattr(rank, 'first_place_votes', None),
                                'points': getattr(rank, 'points', None),
                            })
                        rankings.append({
                            'week': week_num,
                            'poll': poll_name,
                            'ranks': poll_ranks
                        })
                logger.info(f"✅ Found {len(rankings)} poll(s)")
                return rankings
            return []
        except ApiException as e:
            logger.error(f"❌ Rankings API error: {e.status}")
            return []
        except Exception as e:
            logger.error(f"Error fetching rankings: {e}")
            return []

    async def get_team_ranking(self, team: str, year: int = None) -> Optional[Dict[str, Any]]:
        """Get a specific team's ranking across all polls"""
        if year is None:
            year = get_current_cfb_season()
        rankings = await self.get_rankings(year)

        if not rankings:
            return None

        team_lower = team.lower()
        team_rankings = {}

        for poll in rankings:
            poll_name = poll.get('poll', 'Unknown')
            for rank in poll.get('ranks', []):
                if team_lower in rank.get('school', '').lower():
                    team_rankings[poll_name] = {
                        'rank': rank.get('rank'),
                        'points': rank.get('points'),
                        'firstPlaceVotes': rank.get('firstPlaceVotes'),
                    }
                    break

        if team_rankings:
            return {
                'team': team,
                'year': year,
                'rankings': team_rankings
            }
        return None

    async def get_matchup_history(self, team1: str, team2: str) -> Optional[Dict[str, Any]]:
        """Get historical matchup data between two teams"""
        if not self.is_available:
            return None

        try:
            logger.info(f"🔍 Fetching matchup history: {team1} vs {team2}")

            result = await asyncio.to_thread(
                self._teams_api.get_matchup,
                team1=team1,
                team2=team2
            )

            if result:
                games = []
                for game in getattr(result, 'games', []):
                    games.append({
                        'date': getattr(game, 'date', None),
                        'season': getattr(game, 'season', None),
                        'week': getattr(game, 'week', None),
                        'homeTeam': getattr(game, 'home_team', None),
                        'homeScore': getattr(game, 'home_score', None),
                        'awayTeam': getattr(game, 'away_team', None),
                        'awayScore': getattr(game, 'away_score', None),
                        'winner': getattr(game, 'winner', None),
                    })

                return {
                    'team1': getattr(result, 'team1', team1),
                    'team2': getattr(result, 'team2', team2),
                    'team1Wins': getattr(result, 'team1_wins', 0),
                    'team2Wins': getattr(result, 'team2_wins', 0),
                    'ties': getattr(result, 'ties', 0),
                    'games': games[-10:],  # Last 10 games
                }
            return None
        except ApiException as e:
            logger.error(f"❌ Matchup API error: {e.status}")
            return None
        except Exception as e:
            logger.error(f"Error fetching matchup: {e}")
            return None

    async def get_team_schedule(self, team: str, year: int = None) -> List[Dict[str, Any]]:
        """Get a team's schedule/results for a season"""
        if not self.is_available:
            return []

        if year is None:
            year = get_current_cfb_season()

        try:
            logger.info(f"🔍 Fetching schedule for {team} ({year})")

            results = await asyncio.to_thread(
                self._games_api.get_games,
                year=year,
                team=team
            )

            if results:
                games = []
                for game in results:
                    games.append({
                        'week': getattr(game, 'week', None),
                        'date': getattr(game, 'start_date', None),
                        'homeTeam': getattr(game, 'home_team', None),
                        'homeScore': getattr(game, 'home_points', None),
                        'awayTeam': getattr(game, 'away_team', None),
                        'awayScore': getattr(game, 'away_points', None),
                        'venue': getattr(game, 'venue', None),
                        'completed': getattr(game, 'completed', False),
                    })
                logger.info(f"✅ Found {len(games)} games")
                return games
            return []
        except ApiException as e:
            logger.error(f"❌ Schedule API error: {e.status}")
            return []
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            return []

    async def get_draft_picks(self, team: Optional[str] = None, year: int = None) -> Dict[str, Any]:
        """
        Get NFL draft picks, optionally filtered by college team.

        Returns:
            Dict with 'picks' list and optional 'suggestions' if no matches found
        """
        if not self.is_available:
            return {'picks': [], 'suggestions': []}

        # Default to current calendar year (draft happens in April)
        if year is None:
            year = datetime.now().year

        try:
            logger.info(f"🔍 Fetching draft picks" + (f" from {team}" if team else "") + f" ({year})")

            # First, get all draft picks for the year
            results = await asyncio.to_thread(
                self._draft_api.get_draft_picks,
                year=year
            )

            if results:
                picks = []
                all_colleges = set()

                # Normalize search term (remove common mascot names)
                search_term = self._normalize_team_name(team) if team else None
                logger.info(f"🔍 Normalized search: '{team}' -> '{search_term}'")

                for pick in results:
                    college = getattr(pick, 'college_team', None) or ''

                    # Track all colleges for suggestions
                    if college:
                        all_colleges.add(college)

                    # If team filter specified, use smart matching
                    if search_term:
                        if not self._team_matches(search_term, college):
                            continue

                    # Add matching pick to results
                    picks.append({
                        'round': getattr(pick, 'round', None),
                        'pick': getattr(pick, 'pick', None),
                        'overall': getattr(pick, 'overall', None),
                        'nflTeam': getattr(pick, 'nfl_team', None),
                        'name': getattr(pick, 'name', None),
                        'position': getattr(pick, 'position', None),
                        'college': college,
                    })

                # Debug: log matching info
                if search_term:
                    # Show all colleges that might match
                    potential_matches = [c for c in all_colleges if search_term.lower() in c.lower() or c.lower().startswith(search_term.lower())]
                    logger.info(f"🔍 Potential colleges for '{search_term}': {potential_matches}")

                    # Show which ones our matcher would accept
                    actual_matches = [c for c in all_colleges if self._team_matches(search_term, c)]
                    logger.info(f"🔍 _team_matches accepts: {actual_matches}")

                logger.info(f"✅ Found {len(picks)} draft picks" + (f" from {team}" if team else ""))

                # If no picks found but team was specified, find similar college names
                suggestions = []
                if not picks and search_term and all_colleges:
                    suggestions = self._find_similar_teams(team, list(all_colleges))

                return {'picks': picks, 'suggestions': suggestions}

            logger.warning(f"⚠️ No draft results returned for year {year}")
            return {'picks': [], 'suggestions': []}
        except ApiException as e:
            logger.error(f"❌ Draft API error: {e.status} - {e.body}")
            return {'picks': [], 'suggestions': []}
        except Exception as e:
            logger.error(f"Error fetching draft picks: {e}", exc_info=True)
            return {'picks': [], 'suggestions': []}

    def _normalize_team_name(self, team: str) -> str:
        """
        Normalize team name by removing common mascot suffixes.
        'Washington Huskies' -> 'Washington'
        'Ohio State Buckeyes' -> 'Ohio State'
        """
        if not team:
            return team

        # Common mascot names to strip
        mascots = [
            'huskies', 'ducks', 'buckeyes', 'wolverines', 'trojans', 'bulldogs',
            'tigers', 'crimson tide', 'sooners', 'longhorns', 'aggies', 'seminoles',
            'hurricanes', 'gators', 'volunteers', 'wildcats', 'bears', 'cougars',
            'cardinals', 'bruins', 'beavers', 'sun devils', 'buffaloes', 'utes',
            'rebels', 'razorbacks', 'fighting irish', 'nittany lions', 'spartans',
            'hawkeyes', 'cornhuskers', 'badgers', 'golden gophers', 'boilermakers',
            'hoosiers', 'illini', 'terrapins', 'scarlet knights', 'mountaineers',
            'jayhawks', 'cyclones', 'red raiders', 'horned frogs', 'cowboys',
            'golden eagles', 'panthers', 'knights', 'owls', 'mustangs', 'thundering herd'
        ]

        team_lower = team.lower().strip()

        for mascot in mascots:
            if team_lower.endswith(' ' + mascot):
                return team[:-(len(mascot) + 1)].strip()

        return team.strip()

    def _get_current_cfb_week_and_type(self, year: int) -> tuple:
        """
        Estimate the current CFB week and season type based on the date.

        Returns:
            tuple: (week_number or None, season_type: 'regular', 'postseason', or None)

        CFB season typically:
        - Week 0: Last week of August
        - Week 1-15: Regular season (Sept-Nov)
        - Postseason weeks (12-team CFP era, 2024+):
          - Week 1: First Round (Dec 20-21, campus sites)
          - Week 2: Quarterfinals (Dec 31 - Jan 1, NY6 bowls)
          - Week 3: Semifinals (Jan 9-10)
          - Week 4: Championship (Jan 20)
        """
        now = datetime.now()

        # January is postseason (playoffs/championship)
        if now.month == 1:
            if now.day <= 2:
                # Jan 1-2: Quarterfinals weekend (Rose, Sugar, etc.)
                return (2, 'postseason')
            elif now.day <= 10:
                # Jan 3-10: Semifinals weekend
                return (3, 'postseason')
            elif now.day <= 21:
                # Jan 11-21: Championship weekend
                return (4, 'postseason')
            # Late January = offseason, show week 1 preview for next year
            return (1, 'regular')

        # February-July = Offseason
        if now.month >= 2 and now.month < 8:
            return (1, 'regular')

        # If we're querying a different year than current, return week 1
        if now.year != year:
            return (1, 'regular')

        # August - Week 0 or preseason
        if now.month == 8:
            if now.day >= 24:
                return (0, 'regular')  # Week 0 games
            return (1, 'regular')

        # September weeks 1-4
        elif now.month == 9:
            return (min(1 + (now.day - 1) // 7, 4), 'regular')

        # October weeks 5-9
        elif now.month == 10:
            return (min(5 + (now.day - 1) // 7, 9), 'regular')

        # November weeks 10-14
        elif now.month == 11:
            return (min(10 + (now.day - 1) // 7, 14), 'regular')

        # December - conference championships and bowls/playoffs
        elif now.month == 12:
            if now.day <= 7:
                return (15, 'regular')  # Conference championship week
            elif now.day <= 14:
                return (16, 'regular')  # Army-Navy, early bowls
            elif now.day <= 22:
                # CFP First Round (Dec 20-21)
                return (1, 'postseason')
            else:
                # Late December - Quarterfinals prep or early bowls
                return (1, 'postseason')

        return (1, 'regular')

    def _team_matches(self, search_term: str, college: str) -> bool:
        """
        Smart team matching for draft picks.
        Handles variations like 'Miami' matching 'Miami (FL)' or 'Miami (Ohio)'
        """
        if not college:
            return False

        search_lower = search_term.lower().strip()
        college_lower = college.lower().strip()

        # Exact match (case-insensitive)
        if search_lower == college_lower:
            return True

        # Check if search term matches the base name (before any parenthetical)
        # e.g., "Miami" matches "Miami (FL)" or "Miami (Ohio)"
        college_base = college_lower.split('(')[0].strip()
        if search_lower == college_base:
            return True

        # Check if college starts with search term followed by space or (
        # e.g., "Miami" matches "Miami Hurricanes" or "Miami (FL)"
        if college_lower.startswith(search_lower + ' ') or college_lower.startswith(search_lower + '('):
            # But exclude "State" suffix to avoid Washington matching Washington State
            if ' state' not in college_lower or search_lower.endswith(' state'):
                return True

        # For multi-word searches, check if college starts with the search term
        search_words = search_lower.split()
        if len(search_words) > 1:
            if college_lower.startswith(search_lower):
                return True

        return False

    def _find_similar_teams(self, query: str, team_list: List[str], limit: int = 5) -> List[str]:
        """Find teams with similar names using fuzzy matching"""
        try:
            from difflib import SequenceMatcher

            query_lower = query.lower()
            scored = []

            for team in team_list:
                team_lower = team.lower()
                # Check for partial match first
                if query_lower in team_lower or team_lower in query_lower:
                    scored.append((team, 0.95))
                else:
                    # Use fuzzy matching
                    ratio = SequenceMatcher(None, query_lower, team_lower).ratio()
                    if ratio > 0.4:  # Threshold for relevance
                        scored.append((team, ratio))

            # Sort by score descending
            scored.sort(key=lambda x: x[1], reverse=True)
            return [team for team, _ in scored[:limit]]

        except Exception as e:
            logger.error(f"Error finding similar teams: {e}")
            return []

    async def get_team_transfers(self, team: str, year: int = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get transfer portal activity for a team (incoming and outgoing)"""
        if not self.is_available:
            return {'incoming': [], 'outgoing': []}

        if year is None:
            year = datetime.now().year

        try:
            logger.info(f"🔍 Fetching transfers for {team} ({year})")

            results = await asyncio.to_thread(
                self._players_api.get_transfer_portal,
                year=year
            )

            incoming = []
            outgoing = []
            team_lower = team.lower()

            if results:
                for t in results:
                    transfer = {
                        'name': f"{getattr(t, 'first_name', '')} {getattr(t, 'last_name', '')}".strip(),
                        'position': getattr(t, 'position', None),
                        'origin': getattr(t, 'origin', None),
                        'destination': getattr(t, 'destination', None),
                        'stars': getattr(t, 'stars', None),
                        'rating': getattr(t, 'rating', None),
                        'eligibility': getattr(t, 'eligibility', None),
                    }

                    origin = (getattr(t, 'origin', '') or '').lower()
                    dest = (getattr(t, 'destination', '') or '').lower()

                    if team_lower in origin:
                        outgoing.append(transfer)
                    if team_lower in dest:
                        incoming.append(transfer)

            logger.info(f"✅ Found {len(incoming)} incoming, {len(outgoing)} outgoing transfers")
            return {'incoming': incoming, 'outgoing': outgoing}
        except ApiException as e:
            logger.error(f"❌ Transfer API error: {e.status}")
            return {'incoming': [], 'outgoing': []}
        except Exception as e:
            logger.error(f"Error fetching transfers: {e}")
            return {'incoming': [], 'outgoing': []}

    async def get_betting_lines(self, team: Optional[str] = None, year: int = None, week: Optional[int] = None, season_type: str = None) -> tuple:
        """
        Get betting lines for games. If no week specified, gets current/upcoming week.

        Returns:
            tuple: (lines_list, query_info_dict)
        """
        if not self.is_available:
            return [], {}

        if year is None:
            year = get_current_cfb_season()

        original_week = week
        original_season_type = season_type

        # Auto-detect current week and season type if not specified
        if week is None and season_type is None:
            week, season_type = self._get_current_cfb_week_and_type(year)

        # Track what we're querying
        query_info = {
            'year': year,
            'week': week if week else 'none',
            'season_type': season_type if season_type else 'regular',
            'auto_detected': original_week is None and original_season_type is None
        }

        try:
            week_info = f"Week {week}" if week else "postseason"
            logger.info(f"🔍 Fetching betting lines" + (f" for {team}" if team else "") + f" ({year} {week_info}, type={season_type})")

            kwargs = {'year': year}
            if team:
                kwargs['team'] = team
            # Note: CFBD API may not support week filtering for postseason
            # Only pass week for regular season queries
            if week and season_type != 'postseason':
                kwargs['week'] = week
            if season_type:
                kwargs['season_type'] = season_type

            logger.info(f"📊 API kwargs: {kwargs}")

            results = await asyncio.to_thread(
                self._betting_api.get_lines,
                **kwargs
            )

            if results:
                lines = []
                today = datetime.now().date()

                # For postseason, filter to only show upcoming games
                filtered_count = 0
                skipped_count = 0

                for game in results:
                    # Check if game has already been played
                    start_date_str = getattr(game, 'start_date', None)
                    game_date = None
                    if start_date_str:
                        try:
                            # Parse ISO format date string
                            if 'T' in str(start_date_str):
                                game_date = datetime.fromisoformat(str(start_date_str).replace('Z', '+00:00')).date()
                            else:
                                game_date = datetime.strptime(str(start_date_str)[:10], '%Y-%m-%d').date()
                        except Exception as e:
                            logger.warning(f"⚠️ Could not parse date '{start_date_str}': {e}")

                    # For postseason, only show upcoming games (today or future)
                    # For regular season, show all games
                    if season_type == 'postseason' and game_date and game_date < today:
                        skipped_count += 1
                        continue

                    game_lines = []
                    for line in getattr(game, 'lines', []):
                        game_lines.append({
                            'provider': getattr(line, 'provider', None),
                            'spread': getattr(line, 'spread', None),
                            'overUnder': getattr(line, 'over_under', None),
                            'homeML': getattr(line, 'home_moneyline', None),
                            'awayML': getattr(line, 'away_moneyline', None),
                        })

                    lines.append({
                        'homeTeam': getattr(game, 'home_team', None),
                        'homeScore': getattr(game, 'home_score', None),
                        'awayTeam': getattr(game, 'away_team', None),
                        'awayScore': getattr(game, 'away_score', None),
                        'week': getattr(game, 'week', None),
                        'seasonType': getattr(game, 'season_type', season_type),
                        'startDate': str(start_date_str) if start_date_str else None,
                        'lines': game_lines,
                    })
                    filtered_count += 1

                if skipped_count > 0:
                    logger.info(f"📊 Filtered out {skipped_count} past games, showing {filtered_count} upcoming")
                logger.info(f"✅ Found {len(lines)} games with lines")
                return lines, query_info
            return [], query_info
        except ApiException as e:
            logger.error(f"❌ Betting API error: {e.status}")
            return [], query_info
        except Exception as e:
            logger.error(f"Error fetching betting lines: {e}")
            return [], query_info

    async def get_team_ratings(self, team: str, year: int = None) -> Optional[Dict[str, Any]]:
        """Get advanced ratings for a team (SP+, SRS, Elo, FPI)"""
        if not self.is_available:
            return None

        if year is None:
            year = get_current_cfb_season()

        ratings = {}

        # SP+ Ratings
        try:
            sp_results = await asyncio.to_thread(
                self._ratings_api.get_sp,
                year=year,
                team=team
            )
            if sp_results:
                for r in sp_results:
                    ratings['sp'] = {
                        'rating': getattr(r, 'rating', None),
                        'ranking': getattr(r, 'ranking', None),
                        'offense': {
                            'rating': getattr(getattr(r, 'offense', None), 'rating', None) if hasattr(r, 'offense') else None,
                            'ranking': getattr(getattr(r, 'offense', None), 'ranking', None) if hasattr(r, 'offense') else None,
                        },
                        'defense': {
                            'rating': getattr(getattr(r, 'defense', None), 'rating', None) if hasattr(r, 'defense') else None,
                            'ranking': getattr(getattr(r, 'defense', None), 'ranking', None) if hasattr(r, 'defense') else None,
                        },
                    }
                    break
        except Exception as e:
            logger.warning(f"Could not fetch SP+ ratings: {e}")

        # SRS Ratings
        try:
            srs_results = await asyncio.to_thread(
                self._ratings_api.get_srs,
                year=year,
                team=team
            )
            if srs_results:
                for r in srs_results:
                    ratings['srs'] = {
                        'rating': getattr(r, 'rating', None),
                        'ranking': getattr(r, 'ranking', None),
                    }
                    break
        except Exception as e:
            logger.warning(f"Could not fetch SRS ratings: {e}")

        # Elo Ratings
        try:
            elo_results = await asyncio.to_thread(
                self._ratings_api.get_elo,
                year=year,
                team=team
            )
            if elo_results:
                for r in elo_results:
                    ratings['elo'] = {
                        'rating': getattr(r, 'elo', None),
                    }
                    break
        except Exception as e:
            logger.warning(f"Could not fetch Elo ratings: {e}")

        if ratings:
            logger.info(f"✅ Found ratings for {team}: {list(ratings.keys())}")
            return {
                'team': team,
                'year': year,
                'ratings': ratings
            }
        return None

    async def get_team_season_stats(self, team: str, year: int = None) -> Optional[Dict[str, Any]]:
        """Get team's season statistics (offense and defense)"""
        if not self.is_available:
            return None

        if year is None:
            year = get_current_cfb_season()

        try:
            logger.info(f"🔍 Fetching season stats for {team} ({year})")
            
            stats_results = await asyncio.to_thread(
                self._stats_api.get_team_season_stats,
                year=year,
                team=team
            )
            
            if not stats_results:
                logger.warning(f"No stats found for {team} ({year})")
                return None
            
            # Parse stats into organized structure
            parsed_stats = {
                'team': team,
                'year': year,
                'offense': {},
                'defense': {}
            }
            
            for stat in stats_results:
                stat_name = getattr(stat, 'stat_name', None)
                stat_value = getattr(stat, 'stat_value', None)
                
                if not stat_name or stat_value is None:
                    continue
                
                # Categorize stats
                if any(x in stat_name.lower() for x in ['rushing', 'passing', 'total offense', 'yards per play', 'yards per game', 'first downs', 'third down', 'fourth down', 'possession time', 'turnovers lost']):
                    parsed_stats['offense'][stat_name] = stat_value
                elif any(x in stat_name.lower() for x in ['tackles', 'sacks', 'interceptions', 'passes defended', 'total defense', 'rushing defense', 'passing defense', 'yards per play allowed', 'yards per game allowed', 'turnovers gained']):
                    parsed_stats['defense'][stat_name] = stat_value
            
            if parsed_stats['offense'] or parsed_stats['defense']:
                logger.info(f"✅ Found {len(parsed_stats['offense'])} offense stats, {len(parsed_stats['defense'])} defense stats for {team}")
                return parsed_stats
            
            return None
            
        except ApiException as e:
            if e.status == 404:
                logger.warning(f"Team '{team}' not found in {year}")
            else:
                logger.error(f"API error fetching stats for {team}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching stats for {team}: {e}", exc_info=True)
            return None

    # ==================== FORMATTERS ====================

    def format_rankings(self, rankings: List[Dict], poll_filter: Optional[str] = None, top_n: int = 25) -> tuple[List[Dict], Optional[int]]:
        """
        Format rankings for Discord as structured data for embed fields.

        Returns:
            Tuple of (List of field dicts, week number)
        """
        if not rankings:
            return [], None

        fields = []
        week_num = None

        # Priority order for polls
        poll_priority = ['AP Top 25', 'Coaches Poll', 'Playoff Committee Rankings', 'AP']

        # Sort polls by priority
        sorted_rankings = sorted(rankings, key=lambda p: (
            poll_priority.index(p.get('poll', '')) if p.get('poll', '') in poll_priority else 99,
            p.get('poll', '')
        ))

        for poll in sorted_rankings:
            poll_name = poll.get('poll', 'Unknown')
            if poll_filter and poll_filter.lower() not in poll_name.lower():
                continue

            # Track week number
            if week_num is None:
                week_num = poll.get('week')

            ranks_list = []
            for rank in poll.get('ranks', [])[:top_n]:
                r = rank.get('rank', '?')
                school = rank.get('school', 'Unknown')
                ranks_list.append(f"`{r:>2}.` {school}")

            if ranks_list:
                fields.append({
                    'name': f"📊 {poll_name}",
                    'value': "\n".join(ranks_list)
                })

        return fields, week_num

    def format_team_ranking(self, team_ranking: Dict) -> str:
        """Format a team's ranking across polls"""
        if not team_ranking:
            return "Team not ranked"

        team = team_ranking.get('team', 'Unknown')
        year = team_ranking.get('year', 2025)
        rankings = team_ranking.get('rankings', {})

        if not rankings:
            return f"**{team}** is not ranked in any major poll ({year})"

        parts = [f"📊 **{team}** Rankings ({year})"]
        for poll, data in rankings.items():
            rank = data.get('rank', '?')
            parts.append(f"• **{poll}:** #{rank}")

        return "\n".join(parts)

    def format_matchup(self, matchup: Dict) -> str:
        """Format matchup history for Discord"""
        if not matchup:
            return "No matchup data found"

        t1 = matchup.get('team1', 'Team 1')
        t2 = matchup.get('team2', 'Team 2')
        t1_wins = matchup.get('team1Wins', 0)
        t2_wins = matchup.get('team2Wins', 0)
        ties = matchup.get('ties', 0)

        parts = [
            f"🏈 **{t1} vs {t2}**",
            f"**All-Time Record:** {t1} leads {t1_wins}-{t2_wins}" + (f"-{ties}" if ties else ""),
            "",
            "**Recent Games:**"
        ]

        for game in matchup.get('games', [])[-5:]:  # Last 5
            season = game.get('season', '?')
            home = game.get('homeTeam', '?')
            away = game.get('awayTeam', '?')
            home_score = game.get('homeScore', '?')
            away_score = game.get('awayScore', '?')
            winner = game.get('winner', '')

            parts.append(f"• {season}: {away} {away_score} @ {home} {home_score}")

        return "\n".join(parts)

    def format_schedule(self, games: List[Dict], team: str) -> str:
        """Format team schedule for Discord"""
        if not games:
            return f"No schedule found for {team}"

        parts = [f"📅 **{team} Schedule**", ""]

        for game in games:
            week = game.get('week', '?')
            home = game.get('homeTeam', '?')
            away = game.get('awayTeam', '?')
            home_score = game.get('homeScore')
            away_score = game.get('awayScore')
            completed = game.get('completed', False)

            # Determine opponent and location
            is_home = team.lower() in home.lower()
            opponent = away if is_home else home
            location = "vs" if is_home else "@"

            if completed and home_score is not None:
                team_score = home_score if is_home else away_score
                opp_score = away_score if is_home else home_score
                result = "W" if (is_home and home_score > away_score) or (not is_home and away_score > home_score) else "L"
                parts.append(f"Wk {week}: {result} {location} {opponent} ({team_score}-{opp_score})")
            else:
                parts.append(f"Wk {week}: {location} {opponent}")

        return "\n".join(parts)

    def format_draft_picks(self, result: Dict[str, Any], team: Optional[str] = None) -> str:
        """Format draft picks for Discord"""
        picks = result.get('picks', [])
        suggestions = result.get('suggestions', [])

        if not picks:
            parts = [f"No draft picks found" + (f" from **{team}**" if team else "")]

            # Add suggestions if available
            if suggestions:
                parts.append("")
                parts.append("🔍 **Did you mean one of these schools?**")
                for suggestion in suggestions[:5]:
                    parts.append(f"• {suggestion}")

            return "\n".join(parts)

        parts = [f"🏈 **NFL Draft Picks**" + (f" from {team}" if team else ""), ""]

        for pick in picks[:15]:  # Limit to 15
            rd = pick.get('round', '?')
            overall = pick.get('overall', '?')
            name = pick.get('name', 'Unknown')
            pos = pick.get('position', '?')
            nfl_team = pick.get('nflTeam', '?')
            college = pick.get('college', '')

            college_str = f" ({college})" if college and not team else ""
            parts.append(f"Rd {rd} (#{overall}): **{name}** {pos} → {nfl_team}{college_str}")

        return "\n".join(parts)

    def format_transfers(self, transfers: Dict, team: str) -> str:
        """Format transfer portal activity for Discord"""
        incoming = transfers.get('incoming', [])
        outgoing = transfers.get('outgoing', [])

        if not incoming and not outgoing:
            return f"No transfer portal activity found for {team}"

        parts = [f"🔄 **{team} Transfer Portal**", ""]

        if incoming:
            parts.append(f"**Incoming ({len(incoming)}):**")
            for t in incoming[:10]:
                name = t.get('name', 'Unknown')
                pos = t.get('position', '?')
                origin = t.get('origin', '?')
                stars = "⭐" * (t.get('stars') or 0)
                parts.append(f"• {name} ({pos}) from {origin} {stars}")
            parts.append("")

        if outgoing:
            parts.append(f"**Outgoing ({len(outgoing)}):**")
            for t in outgoing[:10]:
                name = t.get('name', 'Unknown')
                pos = t.get('position', '?')
                dest = t.get('destination') or 'TBD'
                parts.append(f"• {name} ({pos}) → {dest}")

        return "\n".join(parts)

    def format_betting_lines(self, lines: List[Dict], query_info: Dict = None) -> str:
        """Format betting lines for Discord"""
        if not lines:
            return "No betting lines available"

        parts = ["💰 **Betting Lines**"]

        # Show query debug info if provided
        if query_info:
            year = query_info.get('year', '?')
            week = query_info.get('week', 'auto')
            season_type = query_info.get('season_type', 'auto')
            parts.append(f"_Query: {year} | Week: {week} | Type: {season_type}_")

        parts.append("")

        for game in lines[:10]:
            home = game.get('homeTeam', '?')
            away = game.get('awayTeam', '?')
            week = game.get('week', '?')
            season_type = game.get('seasonType', 'regular')

            # Format week/round indicator based on season type
            if season_type == 'postseason':
                # Map playoff weeks to round names
                round_names = {
                    1: "First Round",
                    2: "Quarterfinals",
                    3: "Semifinals",
                    4: "Championship",
                    5: "Championship",
                }
                week_str = round_names.get(week, f"Playoff Rd {week}")
            else:
                week_str = f"Wk {week}"

            # Get first available line
            game_lines = game.get('lines', [])
            if game_lines:
                line = game_lines[0]
                spread = line.get('spread')
                ou = line.get('overUnder')

                spread_str = f"{spread:+.1f}" if spread else "N/A"
                ou_str = f"O/U {ou}" if ou else ""

                parts.append(f"**{away} @ {home}** ({week_str})")
                parts.append(f"   Spread: {home} {spread_str} | {ou_str}")

        return "\n".join(parts)

    def format_ratings(self, ratings: Dict) -> str:
        """Format advanced ratings for Discord"""
        if not ratings:
            return "No ratings available"

        team = ratings.get('team', 'Unknown')
        year = ratings.get('year', 2025)
        data = ratings.get('ratings', {})

        parts = [f"📈 **{team}** Advanced Ratings ({year})", ""]

        if 'sp' in data:
            sp = data['sp']
            parts.append(f"**SP+ Rating:** {sp.get('rating', 'N/A'):.1f}" if sp.get('rating') else "**SP+:** N/A")
            if sp.get('ranking'):
                parts.append(f"   Overall Rank: #{sp.get('ranking')}")
            if sp.get('offense', {}).get('ranking'):
                parts.append(f"   Offense Rank: #{sp['offense']['ranking']}")
            if sp.get('defense', {}).get('ranking'):
                parts.append(f"   Defense Rank: #{sp['defense']['ranking']}")

        if 'srs' in data:
            srs = data['srs']
            parts.append(f"**SRS:** {srs.get('rating', 'N/A'):.2f}" if srs.get('rating') else "")

        if 'elo' in data:
            elo = data['elo']
            parts.append(f"**Elo:** {elo.get('rating', 'N/A'):.0f}" if elo.get('rating') else "")

        return "\n".join(parts)

    def format_team_stats(self, stats_data: Dict) -> str:
        """Format team season statistics for Discord"""
        if not stats_data:
            return "No statistics available"

        team = stats_data.get('team', 'Unknown')
        year = stats_data.get('year', 2025)
        offense = stats_data.get('offense', {})
        defense = stats_data.get('defense', {})

        parts = [f"📊 **{team}** Season Statistics ({year})", ""]

        # Helper to format stat value
        def fmt_stat(val):
            try:
                f = float(val)
                # Check if it's a whole number or needs decimals
                if f == int(f):
                    return str(int(f))
                return f"{f:.1f}"
            except (ValueError, TypeError):
                return str(val)

        # === OFFENSE ===
        if offense:
            parts.append("**🏈 OFFENSE**")
            
            # Total Offense
            if 'totalYards' in offense:
                parts.append(f"• Total Yards: **{fmt_stat(offense['totalYards'])}**")
            if 'yardsPerGame' in offense:
                parts.append(f"• Yards/Game: **{fmt_stat(offense['yardsPerGame'])}**")
            if 'yardsPerPlay' in offense:
                parts.append(f"• Yards/Play: **{fmt_stat(offense['yardsPerPlay'])}**")
            
            # Passing
            if 'passYards' in offense or 'passCompletions' in offense:
                parts.append("")
                parts.append("_Passing_")
            if 'passYards' in offense:
                parts.append(f"• Pass Yards: {fmt_stat(offense['passYards'])}")
            if 'passCompletions' in offense and 'passAttempts' in offense:
                comp = fmt_stat(offense['passCompletions'])
                att = fmt_stat(offense['passAttempts'])
                try:
                    pct = (float(offense['passCompletions']) / float(offense['passAttempts'])) * 100
                    parts.append(f"• Completions: {comp}/{att} ({pct:.1f}%)")
                except (ValueError, ZeroDivisionError):
                    parts.append(f"• Completions: {comp}/{att}")
            if 'passTDs' in offense:
                parts.append(f"• Pass TDs: {fmt_stat(offense['passTDs'])}")
            if 'interceptions' in offense:
                parts.append(f"• INTs: {fmt_stat(offense['interceptions'])}")
            
            # Rushing
            if 'rushYards' in offense or 'rushAttempts' in offense:
                parts.append("")
                parts.append("_Rushing_")
            if 'rushYards' in offense:
                parts.append(f"• Rush Yards: {fmt_stat(offense['rushYards'])}")
            if 'rushAttempts' in offense and 'rushYards' in offense:
                try:
                    ypc = float(offense['rushYards']) / float(offense['rushAttempts'])
                    parts.append(f"• Rush Attempts: {fmt_stat(offense['rushAttempts'])} ({ypc:.1f} YPC)")
                except (ValueError, ZeroDivisionError):
                    parts.append(f"• Rush Attempts: {fmt_stat(offense['rushAttempts'])}")
            if 'rushTDs' in offense:
                parts.append(f"• Rush TDs: {fmt_stat(offense['rushTDs'])}")
            
            # Other
            if 'firstDowns' in offense:
                parts.append("")
                parts.append(f"• First Downs: {fmt_stat(offense['firstDowns'])}")
            if 'thirdDownConversions' in offense and 'thirdDownAttempts' in offense:
                conv = fmt_stat(offense['thirdDownConversions'])
                att = fmt_stat(offense['thirdDownAttempts'])
                try:
                    pct = (float(offense['thirdDownConversions']) / float(offense['thirdDownAttempts'])) * 100
                    parts.append(f"• 3rd Down: {conv}/{att} ({pct:.1f}%)")
                except (ValueError, ZeroDivisionError):
                    parts.append(f"• 3rd Down: {conv}/{att}")
            if 'fourthDownConversions' in offense and 'fourthDownAttempts' in offense:
                conv = fmt_stat(offense['fourthDownConversions'])
                att = fmt_stat(offense['fourthDownAttempts'])
                try:
                    pct = (float(offense['fourthDownConversions']) / float(offense['fourthDownAttempts'])) * 100
                    parts.append(f"• 4th Down: {conv}/{att} ({pct:.1f}%)")
                except (ValueError, ZeroDivisionError):
                    parts.append(f"• 4th Down: {conv}/{att}")
            if 'turnovers' in offense:
                parts.append(f"• Turnovers: {fmt_stat(offense['turnovers'])}")

        # === DEFENSE ===
        if defense:
            parts.append("")
            parts.append("**🛡️ DEFENSE**")
            
            # Total Defense
            if 'totalYardsAllowed' in defense:
                parts.append(f"• Total Yards Allowed: **{fmt_stat(defense['totalYardsAllowed'])}**")
            if 'yardsPerGameAllowed' in defense:
                parts.append(f"• Yards/Game Allowed: **{fmt_stat(defense['yardsPerGameAllowed'])}**")
            if 'yardsPerPlayAllowed' in defense:
                parts.append(f"• Yards/Play Allowed: **{fmt_stat(defense['yardsPerPlayAllowed'])}**")
            
            # Pass Defense
            if 'passYardsAllowed' in defense:
                parts.append("")
                parts.append("_Pass Defense_")
                parts.append(f"• Pass Yards Allowed: {fmt_stat(defense['passYardsAllowed'])}")
            if 'passCompletionsAllowed' in defense and 'passAttemptsAllowed' in defense:
                comp = fmt_stat(defense['passCompletionsAllowed'])
                att = fmt_stat(defense['passAttemptsAllowed'])
                try:
                    pct = (float(defense['passCompletionsAllowed']) / float(defense['passAttemptsAllowed'])) * 100
                    parts.append(f"• Completions Allowed: {comp}/{att} ({pct:.1f}%)")
                except (ValueError, ZeroDivisionError):
                    parts.append(f"• Completions Allowed: {comp}/{att}")
            
            # Rush Defense
            if 'rushYardsAllowed' in defense:
                parts.append("")
                parts.append("_Rush Defense_")
                parts.append(f"• Rush Yards Allowed: {fmt_stat(defense['rushYardsAllowed'])}")
            if 'rushAttemptsAllowed' in defense and 'rushYardsAllowed' in defense:
                try:
                    ypc = float(defense['rushYardsAllowed']) / float(defense['rushAttemptsAllowed'])
                    parts.append(f"• Rush Attempts Allowed: {fmt_stat(defense['rushAttemptsAllowed'])} ({ypc:.1f} YPC)")
                except (ValueError, ZeroDivisionError):
                    parts.append(f"• Rush Attempts Allowed: {fmt_stat(defense['rushAttemptsAllowed'])}")
            
            # Defensive Stats
            if 'sacks' in defense:
                parts.append("")
                parts.append(f"• Sacks: {fmt_stat(defense['sacks'])}")
            if 'tacklesForLoss' in defense:
                parts.append(f"• Tackles for Loss: {fmt_stat(defense['tacklesForLoss'])}")
            if 'interceptions' in defense:
                parts.append(f"• Interceptions: {fmt_stat(defense['interceptions'])}")
            if 'passesDeflected' in defense:
                parts.append(f"• Passes Defended: {fmt_stat(defense['passesDeflected'])}")
            if 'fumblesRecovered' in defense:
                parts.append(f"• Fumbles Recovered: {fmt_stat(defense['fumblesRecovered'])}")
            if 'turnoversGained' in defense:
                parts.append(f"• Turnovers Gained: {fmt_stat(defense['turnoversGained'])}")
            
            # 3rd Down Defense
            if 'thirdDownConversionsAllowed' in defense and 'thirdDownAttemptsAllowed' in defense:
                conv = fmt_stat(defense['thirdDownConversionsAllowed'])
                att = fmt_stat(defense['thirdDownAttemptsAllowed'])
                try:
                    pct = (float(defense['thirdDownConversionsAllowed']) / float(defense['thirdDownAttemptsAllowed'])) * 100
                    parts.append(f"• 3rd Down: {conv}/{att} ({pct:.1f}%)")
                except (ValueError, ZeroDivisionError):
                    parts.append(f"• 3rd Down: {conv}/{att}")

        if not offense and not defense:
            return f"No statistics available for {team} ({year})"

        return "\n".join(parts)

    def parse_player_query(self, query: str) -> Dict[str, Optional[str]]:
        """
        Parse a natural language query for player info

        Args:
            query: Natural language query like "@Harry what do you know about James Smith from Alabama"

        Returns:
            Dictionary with 'name' and 'team' keys
        """
        query = query.strip()

        # Remove Discord mentions (format: <@123456789> or <@!123456789>)
        query = re.sub(r'<@!?\d+>', '', query)

        # Remove any remaining @ mentions (like @Harry)
        query = re.sub(r'@\w+', '', query)

        query = query.lower().strip()

        logger.info(f"🔍 Parsing player query: '{query}'")

        # Remove common prefixes (order matters - longer/more specific first)
        prefixes_to_remove = [
            # Question formats
            "what do you know about",
            "what can you tell me about",
            "what are the stats for",
            "what are the stats on",
            "do you have info on",
            "do you have any info on",
            "can you tell me about",
            "can you look up",
            "can you find",
            "could you look up",
            "any info on",
            "got any info on",
            # Command formats
            "tell me about",
            "give me info on",
            "give me stats for",
            "give me stats on",
            "get me stats for",
            "get me stats on",
            "get me info on",
            "pull up",
            "pull stats for",
            "show me stats for",
            "show me stats on",
            "show me info on",
            "show me",
            "look up",
            "lookup",
            "find me",
            "find",
            # Simple formats
            "information on",
            "info on",
            "stats for",
            "stats on",
            "player info for",
            "player stats for",
            "player info",
            "player stats",
            "who is",
            "who's",
            "player",
        ]

        for prefix in prefixes_to_remove:
            if query.startswith(prefix):
                query = query[len(prefix):].strip()
                logger.info(f"🔍 After removing '{prefix}': '{query}'")
                break  # Only remove one prefix

        # Handle team patterns (check in order of specificity)
        team = None
        team_patterns = [
            " who plays for ",
            " that plays for ",
            " playing for ",
            " plays for ",
            " from ",
            " at ",
            " on ",
            ", ",  # "James Smith, Alabama"
        ]

        for pattern in team_patterns:
            if pattern in query:
                parts = query.split(pattern, 1)
                query = parts[0].strip()
                team = parts[1].strip()
                logger.info(f"🔍 Found team pattern '{pattern.strip()}': name='{query}', team='{team}'")
                break

        # Clean up team name (remove common prefixes and trailing punctuation)
        if team:
            team_prefixes = ["the ", "team "]
            for tp in team_prefixes:
                if team.startswith(tp):
                    team = team[len(tp):]
            team = team.rstrip('?.!').strip()

        # Title case the name and clean up
        name = query.title().strip()
        if team:
            team = team.title().strip()

        logger.info(f"✅ Parsed player query: name='{name}', team='{team}'")

        return {
            'name': name,
            'team': team
        }

    def parse_cfb_query(self, query: str) -> Dict[str, Any]:
        """
        Parse a natural language CFB query and determine the type.

        Returns dict with:
        - 'type': One of 'player', 'rankings', 'matchup', 'schedule', 'draft',
                  'transfers', 'betting', 'ratings', or None if not recognized
        - Additional fields depending on type
        """
        query = query.strip()

        # Remove Discord mentions
        query = re.sub(r'<@!?\d+>', '', query)
        query = query.strip()

        # Remove bot name prefix
        query_lower = query.lower()
        for prefix in ['harry', 'harry,', '@harry']:
            if query_lower.startswith(prefix):
                query = query[len(prefix):].strip()
                query_lower = query.lower()

        # Rankings patterns
        ranking_patterns = [
            r'(?:where is|what.s|how is)\s+(.+?)\s+ranked',
            r'(.+?)\s+(?:ranking|rankings?|rank)',
            r'(?:top 25|ap poll|coaches poll|cfp rankings?)',
            r'show me (?:the )?(?:top 25|rankings)',
        ]

        for pattern in ranking_patterns:
            match = re.search(pattern, query_lower)
            if match:
                team = match.group(1).strip() if match.lastindex else None
                return {'type': 'rankings', 'team': team.title() if team else None}

        # Matchup patterns (team vs team)
        matchup_patterns = [
            r'(.+?)\s+(?:vs?\.?|versus|against)\s+(.+?)(?:\s+(?:all.?time|history|record))?$',
            r'(?:history|record|matchup)\s+(?:between|of|for)\s+(.+?)\s+(?:vs?\.?|and|versus)\s+(.+?)$',
        ]

        for pattern in matchup_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {
                    'type': 'matchup',
                    'team1': match.group(1).strip().title(),
                    'team2': match.group(2).strip().rstrip('?.!').title()
                }

        # Schedule patterns
        schedule_patterns = [
            r'(?:when does|when do|when is)\s+(.+?)\s+play',
            r'(.+?)\s+(?:schedule|games?|next game)',
            r'(?:show me|get|what.s)\s+(.+?)\s+schedule',
        ]

        for pattern in schedule_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {'type': 'schedule', 'team': match.group(1).strip().title()}

        # Draft patterns
        draft_patterns = [
            r'(?:who got|who was|who.s been)\s+drafted\s+from\s+(.+)',
            r'(?:nfl )?draft\s+picks?\s+(?:from\s+)?(.+)',
            r'(.+?)\s+(?:nfl )?draft\s+picks?',
        ]

        for pattern in draft_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {'type': 'draft', 'team': match.group(1).strip().title()}

        # Transfer portal patterns
        transfer_patterns = [
            r'(?:who.s in|show me)\s+(?:the )?transfer portal\s+from\s+(.+)',
            r'(.+?)\s+transfer(?:s|\s+portal)',
            r'transfer portal\s+(?:for\s+)?(.+)',
        ]

        for pattern in transfer_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {'type': 'transfers', 'team': match.group(1).strip().title()}

        # Betting patterns
        betting_patterns = [
            r'(?:who.s favored|odds|spread|line|betting)\s+(?:for|in|on)?\s+(.+?)\s+(?:vs?\.?|versus|@|at)\s+(.+)',
            r'(.+?)\s+(?:vs?\.?|@)\s+(.+?)\s+(?:odds|spread|line)',
        ]

        for pattern in betting_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {
                    'type': 'betting',
                    'team1': match.group(1).strip().title(),
                    'team2': match.group(2).strip().rstrip('?.!').title()
                }

        # Ratings patterns (SP+, advanced stats)
        ratings_patterns = [
            r'(?:sp\+|srs|elo|fpi|rating)\s+(?:for\s+)?(.+)',
            r'(.+?)\s+(?:sp\+|srs|elo|advanced stats|ratings?)',
            r'how good is\s+(.+)',
        ]

        for pattern in ratings_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {'type': 'ratings', 'team': match.group(1).strip().title()}

        # Roster patterns
        roster_patterns = [
            r'(?:show me|get|what.s)\s+(.+?)(?:.s)?\s+roster',
            r'(.+?)\s+roster',
        ]

        for pattern in roster_patterns:
            match = re.search(pattern, query_lower)
            if match:
                return {'type': 'roster', 'team': match.group(1).strip().title()}

        # If no pattern matched but query mentions a team, might be a player query
        # Fall through to player query handling in bot.py
        return {'type': None}

    # ==================== BULK PLAYER LOOKUP ====================

    def parse_player_list(self, text: str) -> List[Dict[str, Optional[str]]]:
        """
        Parse a list of players in various formats.

        Supported formats:
        - James Smith (Bama DT)
        - Braden Atkinson (Mercer QB)
        - Vandrevius Jacobs (WR - Cocks)
        - Dre'Lon Miller (WR Colorado)
        - Isaiah Horton, Alabama, WR
        - James Smith from Alabama

        Returns list of dicts with 'name', 'team', 'position'
        """
        players = []

        # Split by newlines, commas at line level, or semicolons
        lines = re.split(r'[\n;]|(?:,\s*(?=[A-Z][a-z]+\s+[A-Z]))', text.strip())

        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue

            # Remove bullet points, numbers, dashes at start
            line = re.sub(r'^[\-\*•\d\.\)]+\s*', '', line)

            player = {'name': None, 'team': None, 'position': None}

            # Pattern 1: Name (Team Position) or Name (Position - Team) or Name (Position Team)
            match = re.match(r'^([A-Za-z\'\-\s]+?)\s*\(([^)]+)\)\s*$', line)
            if match:
                player['name'] = match.group(1).strip()
                parens = match.group(2).strip()

                # Parse the parenthetical - could be "Bama DT", "DT - Cocks", "WR Colorado", etc.
                # Common positions
                positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'OT', 'OG', 'C', 'DL', 'DT', 'DE', 'LB', 'CB', 'S', 'DB', 'K', 'P', 'LS', 'ATH']

                # Check for "Position - Team" or "Team Position" or "Position Team"
                for pos in positions:
                    if pos in parens.upper():
                        player['position'] = pos
                        # Remove position and delimiters to get team
                        team_part = re.sub(rf'\b{pos}\b', '', parens, flags=re.IGNORECASE)
                        team_part = re.sub(r'[\-\s]+', ' ', team_part).strip()
                        if team_part:
                            player['team'] = team_part
                        break
                else:
                    # No position found, assume it's all team
                    player['team'] = parens

                players.append(player)
                continue

            # Pattern 2: Name, Team, Position or Name from Team
            if ',' in line:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    player['name'] = parts[0]
                    player['team'] = parts[1]
                    if len(parts) >= 3:
                        player['position'] = parts[2].upper()
                    players.append(player)
                    continue

            # Pattern 3: Name from Team
            match = re.match(r'^([A-Za-z\'\-\s]+?)\s+(?:from|at|@)\s+(.+)$', line, re.IGNORECASE)
            if match:
                player['name'] = match.group(1).strip()
                player['team'] = match.group(2).strip()
                players.append(player)
                continue

            # Pattern 4: Name Position Team (e.g., "Sam Huard QB USC", "Armon Parker DL Washington")
            positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'OT', 'OG', 'C', 'DL', 'DT', 'DE', 'LB', 'CB', 'S', 'DB', 'K', 'P', 'LS', 'ATH', 'EDGE']
            position_pattern = '|'.join(positions)
            match = re.match(rf'^([A-Za-z\'\-\s]+?)\s+({position_pattern})\s+(.+)$', line, re.IGNORECASE)
            if match:
                player['name'] = match.group(1).strip()
                player['position'] = match.group(2).upper().strip()
                player['team'] = match.group(3).strip()
                players.append(player)
                continue

            # Pattern 5: Name Team (two words, last word is team - e.g., "John Smith Alabama")
            # Only if it looks like FirstName LastName Team
            words = line.split()
            if len(words) == 3 and all(re.match(r'^[A-Za-z\'\-]+$', w) for w in words):
                # Assume first two words are name, last is team
                player['name'] = ' '.join(words[:2])
                player['team'] = words[2]
                players.append(player)
                continue

            # Pattern 6: Just a name (fallback)
            if re.match(r'^[A-Za-z\'\-\s]+$', line) and len(line.split()) >= 2:
                player['name'] = line.strip()
                players.append(player)

        # Clean up and title case
        for p in players:
            if p['name']:
                p['name'] = p['name'].title().strip()
            if p['team']:
                p['team'] = p['team'].title().strip()

        logger.info(f"✅ Parsed {len(players)} players from list")
        for p in players:
            logger.info(f"   📋 Parsed: name='{p.get('name')}', team='{p.get('team')}', pos='{p.get('position')}'")
        return players

    async def lookup_multiple_players(self, player_list: List[Dict[str, Optional[str]]]) -> List[Dict[str, Any]]:
        """
        Look up multiple players in parallel.
        For players not found, includes reason and similar player suggestions.

        Args:
            player_list: List of dicts with 'name' and optional 'team'

        Returns:
            List of results, each with:
            - 'query': original query dict
            - 'result': player info or None
            - 'error': error message if any
            - 'reason': why player wasn't found (if not found)
            - 'suggestions': similar players (if not found)
        """
        if not self.is_available:
            return []

        async def lookup_one(player_query: Dict) -> Dict[str, Any]:
            name = player_query.get('name')
            team = player_query.get('team')

            if not name:
                return {'query': player_query, 'result': None, 'error': 'No name provided'}

            try:
                # First, try with team specified
                result = await self.get_full_player_info(name, team)

                if result:
                    return {'query': player_query, 'result': result, 'error': None}

                # Not found - try without team filter if team was specified
                if team:
                    result = await self.get_full_player_info(name, None)
                    if result:
                        return {'query': player_query, 'result': result, 'error': None}

                # Still not found - get reason and suggestions
                reason = self.get_not_found_reason(name, team)
                suggestions = await self.find_similar_players(name, team, limit=3)

                return {
                    'query': player_query,
                    'result': None,
                    'error': None,
                    'reason': reason,
                    'suggestions': suggestions
                }

            except Exception as e:
                logger.error(f"Error looking up {name}: {e}")
                return {'query': player_query, 'result': None, 'error': str(e)}

        # Look up all players in parallel (but limit concurrency)
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent requests

        async def lookup_with_limit(player_query):
            async with semaphore:
                return await lookup_one(player_query)

        tasks = [lookup_with_limit(p) for p in player_list]
        results = await asyncio.gather(*tasks)

        found = sum(1 for r in results if r.get('result'))
        logger.info(f"✅ Bulk lookup complete: {found}/{len(player_list)} players found")

        return results

    def format_bulk_player_response(self, results: List[Dict[str, Any]]) -> str:
        """Format bulk player lookup results for Discord"""
        if not results:
            return "No players to look up!"

        parts = []
        found_count = 0
        not_found = []

        for r in results:
            query = r.get('query', {})
            result = r.get('result')
            name = query.get('name', 'Unknown')
            team = query.get('team', '')

            if result:
                found_count += 1
                player = result.get('player', {})
                # API returns 'stats' not 'all_stats'
                all_stats = result.get('stats') or result.get('all_stats') or {}
                recruiting = result.get('recruiting')

                # Build compact player line - API returns 'name' or 'firstName'/'lastName'
                p_name = player.get('name') or f"{player.get('firstName', '')} {player.get('lastName', '')}".strip()
                if not p_name:
                    p_name = name  # Fall back to query name
                p_team = player.get('team', 'N/A')
                p_pos = player.get('position', '?')
                p_year = player.get('year', '')

                # Height/weight
                height = player.get('height')
                weight = player.get('weight')
                size = ""
                if height and height > 12:
                    feet = int(height) // 12
                    inches = int(height) % 12
                    size = f"{feet}'{inches}\""
                if weight:
                    size += f" {weight}lbs" if size else f"{weight}lbs"

                # Header line
                parts.append(f"**{p_name}** - {p_team} ({p_pos})")

                # Vitals line
                vitals = []
                if p_year:
                    vitals.append(p_year)
                if size:
                    vitals.append(size)
                if vitals:
                    parts.append(f"   {' | '.join(vitals)}")

                # Stats summary
                if all_stats:
                    # Stats might be year-keyed dict OR flat category dict
                    if all_stats and isinstance(next(iter(all_stats.keys()), None), int):
                        # Year-keyed: {2025: {'passing': {}}, 2024: {...}}
                        latest_year = max(all_stats.keys())
                        stats_data = all_stats[latest_year]
                    else:
                        # Flat: {'passing': {}, 'rushing': {}}
                        stats_data = all_stats
                        latest_year = 2025

                    stat_line = self._format_compact_stats(stats_data, latest_year)
                    if stat_line:
                        parts.append(f"   {stat_line}")

                # Recruiting (compact)
                if recruiting:
                    stars = "⭐" * (recruiting.get('stars') or 0)
                    rating = recruiting.get('rating')
                    if stars or rating:
                        rec_line = f"   🎯 {stars}"
                        if rating:
                            rec_line += f" ({rating:.3f})"
                        parts.append(rec_line)

                parts.append("")  # Blank line between players
            else:
                # Player not found - store with reason and suggestions
                not_found.append({
                    'name': name,
                    'team': team,
                    'reason': r.get('reason', '❓ Player not found'),
                    'suggestions': r.get('suggestions', [])
                })

        # Add not found section with reasons and suggestions
        if not_found:
            parts.append("**❌ Not Found:**")
            for nf in not_found:
                nf_name = nf['name']
                nf_team = nf['team']
                nf_reason = nf['reason']
                nf_suggestions = nf['suggestions']

                # Player name and team
                parts.append(f"• **{nf_name}**" + (f" ({nf_team})" if nf_team else ""))

                # Reason why not found
                parts.append(f"   {nf_reason}")

                # Similar player suggestions
                if nf_suggestions:
                    suggestion_strs = []
                    for s in nf_suggestions[:3]:
                        s_name = s.get('name', 'Unknown')
                        s_team = s.get('team', '?')
                        s_pos = s.get('position', '?')
                        suggestion_strs.append(f"{s_name} ({s_team}, {s_pos})")
                    parts.append(f"   💡 Did you mean: {', '.join(suggestion_strs)}")

                parts.append("")  # Blank line between not-found entries

        # Summary
        summary = f"📊 **Found {found_count}/{len(results)} players**"

        return summary + "\n\n" + "\n".join(parts)

    def _get_stat(self, stats_dict: Dict, *keys) -> int:
        """Get a stat value, trying multiple key variations (case-insensitive)"""
        for key in keys:
            val = None
            # Try exact key
            if key in stats_dict:
                val = stats_dict[key]
            # Try lowercase
            elif key.lower() in stats_dict:
                val = stats_dict[key.lower()]
            # Try uppercase
            elif key.upper() in stats_dict:
                val = stats_dict[key.upper()]

            if val is not None:
                # Ensure we always return an int - API might return strings
                try:
                    return int(float(val)) if val else 0
                except (ValueError, TypeError):
                    return 0
        return 0

    def _format_compact_stats(self, stats: Dict, year: int) -> str:
        """Format stats compactly for bulk display"""
        # Passing
        passing = stats.get('passing', {})
        if passing:
            yards = self._get_stat(passing, 'YDS', 'yards', 'YARDS')
            tds = self._get_stat(passing, 'TD', 'touchdowns', 'TDS')
            if yards or tds:
                return f"📊 {year}: {yards} pass yds, {tds} TD"

        # Rushing
        rushing = stats.get('rushing', {})
        if rushing:
            yards = self._get_stat(rushing, 'YDS', 'yards', 'YARDS')
            tds = self._get_stat(rushing, 'TD', 'touchdowns', 'TDS')
            if yards or tds:
                return f"📊 {year}: {yards} rush yds, {tds} TD"

        # Receiving
        receiving = stats.get('receiving', {})
        if receiving:
            rec = self._get_stat(receiving, 'REC', 'receptions', 'RECEPTIONS')
            yards = self._get_stat(receiving, 'YDS', 'yards', 'YARDS')
            tds = self._get_stat(receiving, 'TD', 'touchdowns', 'TDS')
            if rec or yards:
                return f"📊 {year}: {rec} rec, {yards} yds, {tds} TD"

        # Defense
        defense = stats.get('defense', {})
        if defense:
            solo = self._get_stat(defense, 'SOLO', 'solo', 'TOT', 'total')
            ast = self._get_stat(defense, 'AST', 'ast', 'assists')
            tackles = solo + ast
            tfl = self._get_stat(defense, 'TFL', 'tfl', 'tackles_for_loss')
            sacks = self._get_stat(defense, 'SACKS', 'sacks', 'SK', 'sk')
            if tackles or tfl or sacks:
                return f"📊 {year}: {tackles} tkl, {tfl} TFL, {sacks} sacks"

        return ""


# Backward compatibility alias
PlayerLookup = CFBDataLookup

# Singleton instance
cfb_data = CFBDataLookup()
player_lookup = cfb_data  # Backwards compatibility alias
