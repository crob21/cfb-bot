# Changelog

Full release history for Harry. The bot's `/changelog` command shows the most recent releases;
this file keeps everything. Generated from `src/cfb_bot/utils/version_manager.py`.

## 3.17.0 — Harry Answers When You @ Him 💬 (2026-10-08)

### AI Chat
- NEW: @mention Harry in a channel and he answers, no slash command needed
- Works in channels enabled with /admin channels, when the ai_chat module is on
- A bare @mention gets a greeting; one reply per person every 10 seconds
- Users targeted by /fun target still get their insults instead

### Trolling
- FIX: /fun target now only trolls in the channel it was run in (threads count as their parent)
- NEW: everywhere:true on /fun target and /fun target_all keeps the old server-wide behavior
- Channels blocked with /admin block are never trolled
- /fun status shows where each target is being trolled

## 3.16.2 — Quieter Logs, Shorter Changelog 🧹 (2026-10-02)

### Fixes
- FIX: /changelog sorted versions alphabetically, so 3.9.0 listed above 3.16.x and the newest releases could be cut off

### Cleanup
- Log messages are plain text — emoji stay in Discord embeds, out of the logs (647 lines)
- The bot keeps the last 10 releases; the full history (68 releases) lives in docs/CHANGELOG.md
- docs/CHANGELOG.md was stuck at v1.16.2 — now complete and checked by a test

## 3.16.1 — Lint & Tidy 🧽 (2026-10-02)

### Under the Hood
- Startup opens the owner DM once instead of ~10 times
- Recruiting lookups no longer extract and discard a full page of text
- Startup status shows the real version even if the version manager fails to load
- Removed ~100 unused imports, variables, empty f-strings and comments that restated the code

## 3.16.0 — Harry Knows It's CFB 27 🏈 (2026-10-02)

### League
- Harry's personality, AI prompts, titles and footers now say CFB 27
- The game name lives in one setting (GAME_NAME) — next year is an env change, not a code change
- A test fails if anyone hardcodes a game year again

### Cleanup
- Logger names are version-free (CFBBot.*) so they never go stale
- Removed the unused rules-updater script and the Google Docs setup guide for the deleted integration

## 3.15.2 — Loose Ends 🧹 (2026-10-02)

### Cleanup
- Advance and dev channels can be set with TIMER_CHANNEL_ID / DEV_CHANNEL_ID
- Removed the Supabase storage stub — the docs walked people through setting it up, but it never worked
- Removed the unused performance-metrics module, data/penalties.json, and leftover Sentry docs
- Schedule season now matches the league (Season 4)

## 3.15.1 — Settings Save Guard 💾 (2026-10-02)

### Reliability
- Settings too big for one Discord message are no longer sent and lost — Harry DMs the owner instead
- Any failed settings save now DMs the owner (it used to be a log line nobody saw)
- 18 new tests cover the @everyone advanced flow end to end

## 3.15.0 — Side League Timers ⏱️ (2026-10-02)

### Advance Timer
- CHANGE: The countdown running out no longer advances the week — it just nags
- The week moves only when you post '@everyone advanced'
- TIME'S UP now says which week you're still on

### Side Leagues
- NEW: /league side_timer league:Madden hours:24 — named countdown for another league
- NEW: /league side_timer_stop league:Madden
- Side timers announce in their own channel and never touch the dynasty week
- They survive redeploys and show in /league timer_status and /league timers
- /league nag and stop_nag merged into /league nag action:start|stop (Discord caps a group at 25 commands)

### Polish
- /league week now shows what the step is for (portal opens, signing day, etc.)
- FIX: /league timer no longer claims it replaced side-league timers it leaves running
- Dropped another ~120 lines of unreferenced helpers

## 3.14.1 — Timer No Longer Eats a Week ⏰ (2026-10-02)

### Advance Timer
- FIX: /league timer never advances the week — it only sets the countdown
- The week moves on '@everyone advanced' or when the countdown runs out
- The reply now names the week (unchanged) and any timer it replaced
- The countdown embed posts in the advance channel, wherever you run the command

## 3.14.0 — Code Scrub & Charter Persistence 🧹 (2026-09-19)

### Fixes
- FIX: Charter edits survive redeploys — the Discord copy is now restored to disk at startup
- FIX: /league nag and /league stop_nag actually nag (the command claimed success and did nothing)
- Both advance paths share one matchups embed builder, so they can't drift apart

### Cleanup
- Removed ~1,000 lines of unreferenced code (dead charter AI-update pipeline, unused query parsers, orphan helpers)
- Removed the broken Google Docs integration — /charter import replaces it
- Dropped 7 unused dependencies (google-api x3, sentry-sdk, openai, anthropic, requests, playwright-stealth)

### Error Reports
- NEW: Harry DMs the bot owner when a command or event errors out
- Repeats collapse into one DM per 15 min, capped at 12 DMs/hour
- Keys and tokens are redacted from tracebacks before sending
- AI budget alerts now DM the owner too (they only logged before)
- Removed the unused Sentry integration in favour of this

### Simplification
- One owner-DM helper instead of four copies
- One save/load pair for season/week, settings and staff state (-144 lines)
- Deleted three stale docs that still described the pre-cog layout

## 3.13.0 — Full Schedule View & Live Charter 📜 (2026-09-19)

### Schedule
- NEW: /league schedule — the whole season at a glance
- NEW: /league schedule team:<name> — one team's full season
- Current week is marked in both views
- FIX: Advance message now reads 'Week 0 → Week 1' (was showing the next week instead)
- Matchup announcements now log why they were skipped

### Charter
- NEW: /charter import — pull the latest charter from the league Google Doc (admin)
- Imports as markdown so headings and bullets survive, with plain text as backup
- Charter refreshed to the current CFB 27 version
- Charter link is configurable with the CHARTER_URL env var

## 3.12.0 — Correct Dynasty Week Schedule 📅 (2026-09-16)

### Season/Week Fixes
- FIX: Week table now matches the real 27-step CFB 26 dynasty season
- Preseason (1), Regular Season Weeks 0-14 (2-16), Postseason (17-22), Offseason (23-27)
- Postseason: Conference Championship, Bowl Weeks 1-4 (CFP QF/SF), National Championship
- Offseason: Staff Moves, Transfer Portal Open/Close, National Signing Day, Training Results
- /league set_week now takes the step number (1-27) shown in /league weeks
- /league games, find_game, byes map the current step to the right schedule week (0-14)
- Saved week from the old 26-stage table is migrated automatically on startup

### Advance Timer
- FIX: Only one advance timer — /league timer always runs it in the advance channel
- FIX: '@everyone advanced' and /league timer stop stray timers in other channels (no double advances)
- 'advanced' must be a whole word, posted directly in the advance channel (not threads)
- /league timer_status and timer_stop work from any channel
- FIX: A Discord reconnect no longer spins up a second timer (duplicate warnings / double advance)
- FIX: '@everyone advanced' after TIME'S UP no longer advances the week a second time
- FIX: Two people posting 'advanced' within 3 minutes only advance once
- FIX: Short or restored timers no longer spam 24h/12h warnings that don't apply

### Saved Settings
- FIX: Saving the timer no longer deletes the saved timer channel (it was reverting to #general)
- FIX: A stopped timer can't be resurrected from an older saved message on restart
- Saved week/staff/channel/schedule data is found even when the owner DM has lots of messages

### League Permissions
- FIX: Server Administrators can only run league admin commands in the league's home server
- Bot admins (BOT_ADMIN_IDS) can still manage the league from anywhere
- League admin commands now respect the League module being disabled on a server

## 3.11.0 — Upload Schedules from Discord 📤 (2026-09-05)

### Schedule Management
- NEW: /league upload_schedule — upload a full schedule JSON file (admin)
- NEW: /league set_week_games — set one week's games/byes by typing them (admin)
- NEW: /league schedule_template — shows the expected JSON format
- No more editing files in git — update the schedule live from Discord
- Uploads persist as a Discord backup, surviving redeploys

### Help & Docs
- /help now lists the new schedule + timer management commands

## 3.10.0 — Timer Manager 🎛️ (2026-09-05)

### Advance Timers
- NEW: /league timers lists every active advance timer (admin only)
- Shows channel, server, and time remaining for each
- Interactive menu to stop timers one by one
- List refreshes after each stop; menu is locked to the invoking admin

## 3.9.0 — Week Fixes, Timer Guard & Bot Audit 🛠️ (2026-09-05)

### Season/Week Fixes
- FIX: /league week/weeks/set_week now use one canonical week table
- Corrected to the real 26-stage dynasty schedule (Weeks 0-25)
- Regular Season 0-14, Postseason/Bowls 15-19, Offseason 20-25
- Season rolls over from stage 25 back to Preseason (Week 0)
- set_week now validates the 0-25 range

### Advance Timer
- FIX: '@everyone advanced' only restarts the timer in the configured channel
- No longer hijacks the timer from other channels/servers

### Harry's Personality
- NEW: 50 hand-written cockney insults for targeted users
- Mixed with the existing generator across all targeting paths and /fun roast

### Bot Audit & Hardening
- FIX: AI now reads the live current week (was pointing at dead legacy module)
- Removed the unused 333KB legacy bot.py monolith
- Upgraded AI model to Claude Haiku 4.5
- Bumped aiohttp off a version with known CVEs
- Hardened .gitignore (token.pickle, .venv)

## 3.8.0 — Smart Duplicate Name Handling 🎯 (2026-01-26)

### Position Filtering
- NEW: Position filter for duplicate player names
- /recruiting player position:WR filters by position
- 13 position choices: QB, RB, WR, TE, OT, OG, C, EDGE, DL, LB, CB, S, ATH
- Example: /recruiting player name:Elijah Brown position:WR
- Works with both On3/Rivals and 247Sports

### Multiple Candidate Selection
- NEW: Interactive player selection for duplicate names
- Harry detects when multiple players match a name
- Shows up to 5 candidates with key details (position, class, school, rating)
- Discord select menu to choose the right player
- Full profile loads instantly after selection
- 3-minute timeout for selection

### UX Improvements
- Position filter included in cache key (separate cache per position)
- Position mismatch warnings logged for transparency
- Suggestions in 'not found' message to use position filter
- Smart fallback: exact matches → fuzzy matches → position filter

## 3.7.0 — Security Hardening & Optimizations 🔒 (2026-01-22)

### Security Enhancements
- API retry logic with exponential backoff (2^attempt)
- Automatic retry on 429 rate limits with Retry-After
- Input validation decorators (2000-char limit)
- CORS middleware for dashboard (configurable origins)
- All high-priority security issues resolved

### Cost Optimizations
- Recruiting rankings cached (24-hour TTL)
- User-agent rotation to reduce Zyte usage
- Smart fallback: Playwright → Cloudscraper → Zyte
- Est. $3-5/mo additional savings on scraping

### API Improvements
- @with_retry decorator for any async function
- fetch_with_retry() helper for easy API calls
- Handles network timeouts, connection errors
- Configurable retry attempts and backoff

## 3.6.0 — Performance & Monitoring 🚀 (2026-01-22)

### Performance Optimizations
- 3x faster player lookups with parallel API calls
- Multi-year stats now fetched simultaneously (15s → 5s)
- AI response caching with 1-hour TTL
- 40-60% cache hit rate saves ~$15-20/mo
- Instant responses for repeated AI questions

### Monitoring Integration
- Optional Sentry integration for error tracking
- Performance metrics for all commands
- Command execution time tracking
- Cache hit/miss rate monitoring
- Automatic warnings for slow commands (>5s)
- Real-time error capture with user context

### Technical Improvements
- asyncio.gather() for parallel API requests
- MD5-based cache keys for AI responses
- @track_performance decorator for instrumentation
- Sentry transaction tracking support
- Performance bottleneck identification

## 3.5.0 — Weekly Digest Reporting 📊 (2026-01-13)

### Automated Reporting
- Weekly digest automatically sent to all admins
- Checks daily at midnight for 7-day interval
- Sends via DM to each admin
- Includes cache performance, costs, budget status

### Digest Commands
- /admin digest (view) - Preview digest instantly
- /admin digest (send) - Manually trigger to all admins
- Shows cache hit rate and cost savings
- Displays AI usage stats
- Budget status with color indicators

### Weekly Summary
- Cache performance (hit rate, savings)
- Monthly costs (AI, Zyte, Total)
- Budget status with visual indicators
- AI usage (requests, tokens, cost)
- Timestamp and date range

## 3.4.0 — Cost Tracking & Budgets 💰 (2026-01-13)

### Budget Management
- Added /admin budget command to track monthly spending
- Set budget limits for AI, Zyte, and total costs
- Visual progress bars show percentage used
- Color-coded indicators (green/yellow/red)
- Shows remaining budget for each service

### Cost Alerts
- Automatic alerts at 50%, 80%, 90%, and 100% of budget
- Alerts logged for each service (AI, Zyte, Total)
- One alert per threshold per month
- Prevents surprise bills

### Configuration
- AI_MONTHLY_BUDGET env var (default: $10)
- ZYTE_MONTHLY_BUDGET env var (default: $5)
- TOTAL_MONTHLY_BUDGET env var (default: $15)
- Budgets reset monthly automatically

## 3.3.0 — Recruiting Data Cache 💾 (2026-01-13)

### Cost Optimization
- Added intelligent caching system for recruiting player lookups
- Player data cached for 24 hours (saves $$$ on API calls!)
- Cache automatically invalidates when data expires
- Added /admin cache command to view stats and manage cache
- Shows estimated cost savings from cache hits
- Can clear recruiting cache or all cache manually

### Performance
- Instant responses for cached player lookups
- Tracks cache hit rate for monitoring efficiency
- Per-namespace cache organization (recruiting, etc.)
- Automatic cleanup of expired entries

## 3.2.0 — API-Based Usage Tracking 🌐 (2026-01-13)

### Enhanced Usage Tracking
- Added official OpenAI Usage API integration
- Added official Zyte Stats API integration
- Multiple view options: Bot tracked, API official, or both side-by-side
- /admin ai view:local - Bot-tracked stats (persisted)
- /admin ai view:api - Official OpenAI API stats (last 30 days)
- /admin ai view:both - Compare both data sources
- /admin zyte view:local - Session stats from bot
- /admin zyte view:api - Official Zyte API stats (last 30 days)
- /admin zyte view:both - Compare both data sources

## 3.1.0 — AI Usage Tracking 🤖 (2026-01-13)

### AI Monitoring
- Added /admin ai command to track token usage and costs
- Persistent tracking - stats survive bot restarts
- Real-time monitoring of OpenAI (GPT-3.5) and Anthropic (Claude) API usage
- Cost estimates and monthly projections
- Separate tracking for each AI provider
- Stored in Discord DMs for free persistence

## 3.0.1 — Cloudflare Bypass & Admin Enhancements 🎭 (2026-01-12)

### Cloudflare Bypass
- Added Playwright headless browser for bulletproof scraping
- Fallback chain: Playwright → Cloudscraper → httpx
- No more On3 blocks!

### 247Sports Enhancements
- Added offers, predictions, visits to 247Sports scraper
- Added player images from 247Sports
- Now matches On3 output format exactly

### Admin Commands
- /admin config enable_all - Enable all modules at once
- /admin config disable_all - Disable all modules at once
- Startup notification now only in dev channel with full status

## 3.0.0 — Cog Architecture 🏗️ (2026-01-12)

### Complete Refactor
- Migrated from monolithic bot.py to cog-based architecture
- 8 modular cogs: Core, AI Chat, Recruiting, CFB Data, HS Stats, League, Charter, Admin
- Better performance and maintainability
- Comprehensive test suite with 59 passing tests

## 2.5.1 — UI Polish 💅 (2026-01-11)

### Recruiting Player
- Profile link now appears AFTER college stats (not before)
- Better flow for transfer portal players

### Command Cleanup
- /recruiting portal now suggests /recruiting player
- Hidden from /help since /recruiting player does same thing

## 2.5.0 — Transfer Portal Detection! 🌀 (2026-01-11)

### Transfer Portal Detection
- /recruiting player now shows 🌀 Transfer Portal section for portal players
- Scrapes previous school, college experience, portal entry date, portal rating
- /recruiting commits shows 🌀 indicator for transfer players
- Detects transfers via H.S. graduation year + TR (Transfer Rating) indicator

### Player Photos
- /recruiting portal now shows player photo thumbnail

### Bug Fixes
- Fixed /recruiting rankings showing 0 teams
- Fixed header rows appearing as 'Teams' in rankings
- Updated On3 page parser for their new HTML structure

## 2.4.0 — Transfer Portal Command & Fuzzy Search! (2026-01-11)

### New /recruiting portal Command
- Combined recruiting data + college stats for transfers!
- Shows On3 rating, predictions, offers + CFB career stats
- Cross-references names between On3/CFB (handles nicknames)
- Natural language: '@Harry tell me about portal player John Smith'

### Fuzzy Name Matching
- Typos in first names now work! (Gavinn → Gavin)
- Case insensitive search (JOHN SMITH → John Smith)
- Falls back to last-name-only search for better matching
- Prevents false positives with strict name validation

### UI Improvements
- /recruiting commits: wider display, 30 players, shows city
- Shows 🏫 HS or 🔄 Transfer indicator on commits
- CFB player stats: spacing between seasons
- 'Not found' messages now ephemeral (only you see them)

## 2.3.1 — Bug Fixes & UI Consistency (2026-01-11)

### Fixed
- Fixed `/admin channels` timeout (now defers properly)
- Fixed `/changelog` crashing when field > 1024 chars
- Auto-responses now show '💤 Off' when AI Chat disabled
- Consistent status display in `/admin config` and `/admin channels`

## 2.2.0 — AI Chat Toggle - Control Harry's Personality! (2026-01-10)

### New AI_CHAT Module
- New toggleable `ai_chat` module for Harry's AI features
- Disable `/harry`, `/ask`, `/summarize` per-server
- Disable @Harry mentions and auto-responses
- Keep recruiting/data features while silencing the chat

### Usage
- `/admin config disable ai_chat` - Silence Harry's chat
- `/admin config enable ai_chat` - Enable Harry's chat
- Core commands (`/help`, `/admin`) always available
- Perfect for servers that only want data features!

## 2.1.0 — League Consolidation - Season & Timer Merged! (2026-01-10)

### Simplified Structure
- Merged `/season` and `/timer` into `/league` group
- All league management now under ONE command group!
- Reduced from 8 groups to 6 groups
- `/league` now has 19 commands covering everything

### New /league Commands
- **Season:** `week`, `weeks`, `games`, `find_game`, `byes`, `set_week`
- **Timer:** `timer`, `timer_status`, `timer_stop`, `timer_channel`
- **Staff:** `staff`, `set_owner`, `set_commish`, `pick_commish`
- **Fun:** `nag`, `stop_nag` 😈

### Migration Guide
- `/season current` → `/league week`
- `/season schedule` → `/league weeks`
- `/timer start` → `/league timer`
- `/timer status` → `/league timer_status`
- `/timer stop` → `/league timer_stop`

## 2.0.0 — 🚀 Command Reorganization - Grouped Commands! (2026-01-10)

### BREAKING: Command Structure
- All 63 commands reorganized into logical groups!
- Type `/group` to see all subcommands (e.g., `/recruiting`, `/cfb`)
- Better discoverability - related commands are now together
- Old commands like `/recruit` are now `/recruiting player`

### Command Groups
- `/recruiting` - Recruits, rankings, commits, class data
- `/cfb` - College football stats, rankings, schedules
- `/hs` - High school stats from MaxPreps
- `/league` - Staff, season, timer, dynasty (consolidated)
- `/charter` - Rules lookup, search, editing
- `/admin` - Config, channels, bot admins

### Updated Help
- New `/help` command (renamed from `/help_cfb`)
- Shows all command groups with subcommands
- Quick reference for the new structure

## 1.18.0 — Team Commits List - See Who's Committed! (2026-01-10)

### New Command
- NEW: `/team_commits <team> [year]` - List all committed recruits for a team!
- Shows each commit with: name, position, rating, stars, status (Signed/Committed)
- High school and location for top recruits
- Sorted by rating (highest first)
- Link to full class on On3/Rivals
- Example: `/team_commits Washington 2026` shows all 25 commits

### Technical
- New `get_team_commits()` method in On3Scraper
- Dynamically finds team slug from rankings page
- Parses position, height, weight, high school, location
- Extracts industry rating and calculates star count
- Currently On3/Rivals only (247Sports doesn't have commits list page)

## 1.17.7 — Fixed Recruiting Class Command for On3 (2026-01-10)

### Bug Fixes
- Fixed /recruiting_class not finding teams on On3
- On3 uses listitem elements, not table rows
- Now parses rank, commits, star breakdown, avg rating, NIL, and score
- Washington 2026 class now shows: #15, 25 commits, 88.76 avg, $69K NIL

## 1.17.6 — Transfer Portal Support & Multi-Result Warnings (2026-01-10)

### On3/Rivals Improvements
- Transfer portal players now findable via /recruit
- Scraper falls back to broader search when class year filter returns no results
- Transfer status automatically detected and shown
- Emmanuel Karnley (UW transfer) and similar players now work

### HS Stats Improvements
- Warning shown when multiple players match a name
- Displays other matching players so you know to add state filter
- Tip to narrow results with /hs_stats name:X state:XX

## 1.17.5 — Enhanced HS Stats - Career Stats from MaxPreps (2026-01-10)

### HS Stats Improvements
- Improved MaxPreps career stats parsing for all stat types
- Fixed player name/school extraction from og:title metadata
- Career defensive stats: solo tackles, total tackles, sacks, INTs
- All-purpose yards including INT/kick/punt returns per season
- Rushing, receiving, passing stats with per-game averages
- Position detection (QB, WR, RB, DB, LB, etc.)
- Physical info: height, weight, class year
- Individual season breakdowns by grade level (Sr/Jr/So/Fr)
- Career totals consolidated across all tables

### Bug Fixes
- Fixed regex bug that caused 'Tot283' to parse as '2' instead of '283'
- Fixed position detection for 'V. Football #1 • DB' format
- Removed duplicate import of 're' module
- Empty receiving stats (all zeros) are now hidden

## 1.17.4 — On3/Rivals Recruiting Data - Offers, Predictions, Visits & Photos (2026-01-10)

### On3/Rivals Integration
- NEW: On3/Rivals recruiting scraper as alternative to 247Sports
- Offers list - shows all schools that have offered
- Predictions - shows RPM percentages for each school
- Visits - shows official and unofficial visit history
- Commitment status with signing dates
- Industry composite ratings
- Server-side rendered pages = reliable scraping

### Recruit Data Enhancements
- Player photos now displayed in Discord embed thumbnail!
- Full profile data: stars, rating, national/position/state rank
- Physical info: height, weight, hometown, high school
- Top 5 predictions with percentages
- Up to 8 offers displayed
- Visit history with dates and types (Official/Unofficial)

## 1.17.3 — Private Admin Channel Support (2026-01-10)

### Improvements
- /set_admin_channel now accepts channel_id for private channels
- Use: /set_admin_channel channel_id:1459372492387778704
- Works for channels Harry can't see in the picker

## 1.17.2 — Deep Search & Admin Channel (2026-01-10)

### New Features
- /recruit now has `deep_search:True` option to search ALL ~3000 ranked recruits
- Standard search covers top 1000 (~10 seconds)
- Deep search covers all ~3100 recruits (~30 seconds)
- /set_admin_channel - Set a private channel for bot updates & errors

## 1.17.1 — Recruiting Search Expansion (2026-01-10)

### Improvements
- Expanded recruit search from top 150 to top 1000 recruits
- Reduced rate limit delay (0.5s) for faster searches (~10s for top 1000)
- Added progress logging for deep searches
- Auto-stops at end of rankings instead of fixed page limit
- Most recruits people look up are in top 500 (~5 seconds)

## 1.17.0 — 247Sports Recruiting Module (2026-01-10)

### New Features
- NEW MODULE: 247Sports Recruiting data (web scraping)
- /recruit <name> - Look up individual recruit's composite ranking
- /top_recruits - Get top recruits, filter by position or state
- /recruiting_class <team> - Get team's recruiting class details
- /recruiting_rankings - Top 25 team recruiting rankings
- Composite ratings combining 247, Rivals, ESPN, On3
- Star ratings, national/position/state rankings
- Commitment tracking
- Enable with: /config enable recruiting

## 1.16.4 — Bulk Lookup Detection Fix (2026-01-10)

### Bug Fixes
- Fixed bulk lookup not triggering for 'Tell me about:' and similar phrases
- Added more bulk indicators: 'tell me about:', 'about these', 'look up:', etc.
- Improved player line detection - no longer requires parentheses
- Detects 'Name Position Team' format (e.g., Sam Huard QB USC)
- Detects 3-word lines as potential player entries
- Added logging to show bulk lookup trigger reason

## 1.16.3 — Bulk Lookup Parser Fix (2026-01-10)

### Bug Fixes
- Fixed bulk player lookup not recognizing 'Name Position Team' format
- Parser now handles: Sam Huard QB USC, Armon Parker DL Washington
- Added Pattern 4: Name Position Team (without parentheses)
- Added Pattern 5: Name Team (FirstName LastName School)
- Improved parser logging for debugging

## 1.16.2 — League Context Isolation (2026-01-10)

### Bug Fixes
- CRITICAL: Fixed AI leaking league schedule data to non-league servers
- AI prompts now respect LEAGUE module status per server
- Non-league servers no longer see schedule/charter context in AI responses
- Added include_league_context parameter to all AI methods
- League-specific AI features properly isolated from general CFB assistant mode

## 1.16.1 — Guild Debugging & Logging (2026-01-10)

### Improvements
- Added detailed guild listing on startup (shows each server name, ID, member count)
- Added on_guild_join event to log when bot joins new servers
- Added on_guild_remove event to log when bot is removed from servers
- Auto-syncs commands to newly joined guilds
- Better debugging for missing guild connections

## 1.16.0 — League Module Separation (2026-01-09)

### Module Separation
- League-specific features now gated behind LEAGUE module
- Charter links only show when LEAGUE is enabled
- Generic CFB assistant mode when LEAGUE is disabled
- Footer dynamically changes based on server config
- Reaction responses adapt to LEAGUE status
- /harry command works for general CFB without LEAGUE
- /rule command now requires LEAGUE module

## 1.15.3 — Interaction Timeout Fix (2026-01-09)

### Bug Fixes
- Fixed 'Unknown interaction' timeout errors on CFB data commands
- All API commands now defer() FIRST before module checks
- Added check_module_enabled_deferred() for post-defer validation
- Prevents Discord's 3-second response window from expiring

## 1.15.2 — Timer Notification Fix (2026-01-09)

### Bug Fixes
- Fixed 'Error in countdown monitoring: 24' bug
- JSON dict keys are strings - now converts to ints after load
- Improved error logging to show exception type

## 1.15.1 — Code Cleanup & Optimization (2026-01-09)

### Code Quality
- Added Colors class with constants for consistent theming
- Added Footers class for standard footer texts
- Replaced 132 hardcoded color values with constants
- Replaced 39 hardcoded footer strings with constants
- Fixed indentation issues in reaction handlers
- Improved code maintainability and consistency

## 1.15.0 — High School Stats Scraper (2026-01-09)

### MaxPreps Scraper
- NEW: /hs_stats - Look up high school football player stats
- NEW: /hs_stats_bulk - Bulk lookup for multiple HS players
- NEW: @Harry HS stats support (e.g., 'HS stats for Arch Manning')
- Web scraping from MaxPreps with caching (24hr)
- Rate limiting to be respectful of MaxPreps servers
- Parses passing, rushing, receiving, and defensive stats

### Module Configuration
- HS_STATS module OFF by default (opt-in feature)
- Enable with /module enable hs_stats
- Requires httpx and beautifulsoup4 packages

## 1.14.0 — Admin Channel & Notifications (2026-01-09)

### Admin Channel
- NEW: /set_admin_channel to configure admin output channel
- Bot startup notifications sent to admin channel
- Timer restore messages use configured admin channel
- Error reports sent to admin channel
- Config change logs (module enable/disable)

### Ephemeral Responses
- All admin/config commands now user-only (ephemeral)
- /config, /channel, /list_bot_admins - only you see them
- Keeps admin clutter out of public channels

### Config Improvements
- /config now shows admin channel, enabled channels, rivalry status
- League settings only shown when League module is enabled
- Renamed toggle_auto to toggle_rivalry for clarity

## 1.13.0 — Storage Abstraction Layer (2026-01-09)

### Scalable Storage
- NEW: Storage abstraction layer for future-proofing
- Easy swap between Discord DM and database storage
- STORAGE_BACKEND env var to switch backends
- Placeholder for Supabase (PostgreSQL) integration

### How to Scale Later
- 1. Create Supabase project (free tier works!)
- 2. Set SUPABASE_URL and SUPABASE_KEY env vars
- 3. Set STORAGE_BACKEND=supabase
- 4. Deploy - configs auto-migrate!

## 1.12.0 — Per-Channel Controls (2026-01-09)

### Channel Management
- NEW: /channel command to manage where Harry responds
- Channel whitelist - enable specific channels only
- Per-channel auto-response toggles
- Harry stays silent in non-whitelisted channels

### Channel Commands
- /channel view - See current channel settings
- /channel enable - Add channel to whitelist
- /channel disable - Remove from whitelist
- /channel enable_all - Clear whitelist (allow all)
- /channel toggle_auto - Toggle auto-responses per channel

## 1.11.0 — Auto Response Toggle (2026-01-09)

### Auto Responses Toggle
- NEW: Toggle automatic jump-in responses (team banter)
- Harry's cockney personality and Oregon hate are ALWAYS ON
- Only controls 'Fuck Oregon!' style auto-responses
- Oregon player lookup snark always shows (part of personality)

### Simplified Settings
- Removed separate cockney/rivalry toggles
- Single 'Auto Responses' toggle in dashboard
- Harry is always a cockney asshole Duck-hater 🦆

## 1.10.0 — Smart Player Suggestions (2026-01-08)

### Bulk Player Lookup
- NEW: 'Did you mean?' suggestions for players not found
- FCS school detection - warns when querying limited-data schools
- Automatic retry without team filter if initial search fails
- Shows similar players from last name / first name searches
- Helpful reasons explaining why a player wasn't found

### FCS Coverage
- Added FCS conference and school database
- Detects Mercer, ETSU, and other FCS schools
- Warns users about limited CFBD data coverage for FCS

## 1.9.1 — Bulk Lookup Type Fix (2026-01-08)

### Bug Fixes
- Fixed 'can only concatenate str to str' error in bulk player lookup
- API sometimes returns stats as strings - now properly converted to integers
- Defensive stat calculations now work correctly across all player types

## 1.9.0 — Web Dashboard (2026-01-08)

### Web Dashboard
- NEW: Full web dashboard for managing Harry!
- Login with Discord OAuth
- Visual toggle for modules (CFB Data, League)
- Manage bot admins with clicks
- Beautiful dark theme UI

### Dashboard Features
- Server selector for multi-server management
- Enable/disable modules per server
- Add/remove bot admins visually
- See available commands per module

### Technical
- FastAPI backend with async support
- Discord OAuth2 integration
- Session-based authentication
- RESTful API for config management

## 1.8.1 — Bulk Player Lookup (2026-01-08)

### Bulk Player Lookup
- NEW: Look up multiple players at once!
- /players command for slash interface
- Natural language: just paste a list to @Harry
- Supports various formats: Name (Team Pos), Name from Team, etc.
- Parallel lookups for speed (up to 15 players)
- Compact display with key stats and recruiting info

## 1.8.0 — Per-Server Feature Configuration (2026-01-08)

### Server Configuration
- NEW: `/config` - Enable/disable features per server
- Modules: Core (always on), CFB Data, League
- Settings persist across bot restarts
- Admins can customize Harry for their server

### Module: Core (Always On)
- Harry's personality - always available!
- General AI chat and questions
- /ask, /help, /whats_new, /changelog
- Bot admin management

### Module: CFB Data
- Player lookup, rankings, matchups
- Schedules, draft, transfers, betting, ratings
- Enable: `/config enable cfb_data`
- Enabled by default on new servers

### Module: League Features
- Timer, advance, charter, rules
- League staff, pick commish, dynasty schedule
- Enable: `/config enable league`
- Disabled by default (opt-in for dynasty servers)

## 1.7.0 — Full CFB Data Suite (2026-01-08)

### Team Rankings
- NEW: /rankings - Get AP, Coaches, CFP rankings
- Check specific team: '@Harry where is Ohio State ranked?'
- Top 25 poll display for all major polls

### Matchup History
- NEW: /matchup - All-time records between rivals
- '@Harry Alabama vs Auburn history'
- Shows win/loss record and last 5 games

### Team Schedules
- NEW: /cfb_schedule - Full season schedule & results
- '@Harry when does Nebraska play next?'
- Shows W/L, scores, home/away for completed games

### NFL Draft
- NEW: /draft_picks - NFL draft picks by college
- '@Harry who got drafted from Georgia?'
- Shows round, pick, position, and NFL team

### Transfer Portal
- NEW: /transfers - Portal activity by team
- '@Harry USC transfers'
- Shows incoming AND outgoing transfers with ratings

### Betting Lines
- NEW: /betting - Game spreads and O/U
- '@Harry who's favored in Bama vs Georgia?'
- Shows spread and over/under for games

### Advanced Ratings
- NEW: /team_ratings - SP+, SRS, Elo ratings
- '@Harry how good is Texas?'
- Shows offensive/defensive rankings, SRS, Elo

### Natural Language
- All features work with natural @Harry questions!
- Auto-detects query type (player, rankings, matchup, etc.)
- Same cockney personality throughout

## 1.6.1 — Enhanced Player Lookup with Official API (2026-01-08)

### Official CFBD Library
- Refactored to use official cfbd Python library
- More reliable API calls with proper error handling
- Better type safety and cleaner code
- Access to all CFBD endpoints

### Transfer Portal
- NEW: Shows transfer info for portal players!
- See origin → destination team
- Eligibility status displayed
- Automatically detects if player transferred

### Enhanced Recruiting
- National ranking, position rank, state rank
- Full recruiting class data
- Searches multiple recruiting years automatically

### Natural Language
- 40+ different ways to ask about a player
- Handles team patterns: from/at/plays for/comma
- Strips Discord mentions automatically

## 1.6.0 — Player Lookup Feature (2026-01-08)

### Player Lookup
- NEW: /player command to look up any CFB player!
- Get vitals: position, height, weight, year, hometown
- View season stats: tackles, TFL, sacks, yards, TDs
- See recruiting info: star rating, national ranking
- Natural language: '@Harry what do you know about X from Alabama?'

### Integration
- Powered by CollegeFootballData.com API
- Search by name or name + team
- Supports all positions: QB, RB, WR, DT, LB, etc.
- (And yes, I'll still mock Oregon players)

## 1.5.1 — Schedule Display & Admin Notifications (2026-01-02)

### Schedule Display
- Matchups now show on /advance and @everyone advanced
- User teams are **bolded** in all schedule outputs
- AI responses format schedules as clean lists
- Bye teams included in advance announcements

### Admin Notifications
- Timer restore message shows version info
- Quick preview of latest changes on restart
- Helps admins see what changed after deploy

## 1.5.0 — Discord Charter Persistence & Poll Support (2025-12-31)

### Charter Persistence
- Charter now saves to Discord - survives deployments!
- Automatic sync on any charter update
- /sync_charter command to manually push to Discord
- Falls back to file if no Discord version exists
- Charter stored in bot owner's DM (invisible to users)

### Discord Poll Support
- /scan_rules now detects Discord polls!
- Extracts poll questions and vote counts
- Shows winning answer for closed polls
- Analyzes both text messages and polls

### Pick Commish Improvements
- Added channel selection: /pick_commish #channel
- DO NOT PICK and BIGGEST ASSHOLE are now separate
- Asshole score based on actual toxic behavior, not ranking

## 1.4.1 — Code Quality & Settings Persistence (2025-12-31)

### Bug Fixes
- Fixed all bare 'except:' blocks with specific exception types
- Notification channel now persists across bot restarts
- /set_timer_channel setting is saved to Discord

### Code Quality
- Added get_notification_channel() helper for consistent channel lookup
- Refactored exception handling for better error tracking
- Updated README with v1.4.0 features

## 1.4.0 — Server-Wide Timer & Ephemeral Messages (2025-12-31)

### Server-Wide Timer Notifications
- Timer notifications now always go to #general
- One timer for the whole server (not per-channel)
- Includes: Advance start, 24h/12h/6h/1h warnings, TIME'S UP
- /set_timer_channel to change notification channel
- Schedule announcements also go to timer channel

### Ephemeral Admin Messages
- Admin confirmations now only visible to the admin
- /stop_countdown success → ephemeral
- /set_season_week success → ephemeral
- /set_league_owner success → ephemeral
- /set_co_commish success → ephemeral
- /advance confirmation → ephemeral (announcement goes to #general)
- Timer Restored → goes to admin channel only

## 1.3.0 — Interactive Charter & Co-Commish Picker (2025-12-31)

### Interactive Charter Updates
- Update charter by talking to Harry naturally!
- Example: '@Harry update the advance time to 10am'
- Example: '@Harry add a rule: no trading during playoffs'
- Before/after preview with ✅/❌ confirmation
- Automatic backup before any change
- Changelog tracks who changed what and when
- /charter_history command to view recent changes

### Rule Scanning
- /scan_rules command to find rule changes in voting channels
- Natural language: '@Harry scan #voting for rule changes'
- AI identifies passed/failed/proposed rules
- Shows vote counts when available
- React with 📝 to generate charter updates
- Apply all passed rules to charter with one click

### Co-Commissioner Picker
- /pick_commish command for AI-powered recommendations
- Analyzes chat activity and participation
- 🚨 ASSHOLE DETECTOR - rates toxic behavior!
- Scores: Activity, Helpfulness, Leadership, Drama, Vibes
- Ranks ALL participants with personalized roasts
- Calls out biggest asshole who should NEVER be commish

### League Staff Tracking
- /league_staff - View current owner and co-commissioner
- /set_league_owner - Set the league owner
- /set_co_commish - Set the co-commissioner
- Special option: 'We don't fucking have one' for co-commish
- Persists across bot restarts

### Code Quality
- Fixed all bare 'except:' blocks with specific exceptions
- Added cleanup task for expired pending requests
- Memory leak prevention for processed messages
- Python 3.13 compatibility improvements

## 1.2.0 — CFB 26 Dynasty Week System (2025-12-29)

### Dynasty Week Counter
- Added full CFB 26 Dynasty season week structure (30 weeks total)
- Regular Season: Week 0 (Season Kickoff) through Week 15
- Post-Season: Conference Championships, Bowl Weeks 1-4, End of Season Recap
- Offseason: Portal Weeks 1-4, National Signing Day, Training Results
- Offseason: Encourage Transfers, Preseason
- Season phase tracking (Regular Season, Post-Season, Offseason)

### Week Actions & Notes
- Each week now shows available actions (staff moves, job offers, etc.)
- Important notes displayed (last chance reminders, deadlines)
- Bowl weeks show hiring/firing windows
- Offseason weeks show portal and recruiting actions
- /time_status shows upcoming week actions

### Improved Display
- Week transitions now show proper CFB 26 week names
- Season phase displayed alongside week info
- /time_status shows current and next week with actions
- /set_season_week shows proper week name, phase, and actions
- Times Up message displays phase and week progression

## 1.1.1 — Bug Fixes & Improvements (2025-11-04)

### Bug Fixes
- Fixed summarizer timezone compatibility issue (discord.utils.utc → timezone.utc)
- Channel summarization now works with all discord.py versions
- Guild-specific command sync for instant updates (5 seconds vs 1 hour)
- Commands now appear immediately in configured servers

### Security & Permissions
- Advance timer commands now require admin permissions
- /advance restricted to admins only
- /stop_countdown now uses bot admin system
- Added hardcoded admin support for permanent admins
- Both Discord Administrators and Bot Admins can manage timers

### Configuration
- Added support for multiple guild instant sync
- Configured two servers for instant command updates
- Improved admin permission checking across all commands

### Documentation
- Updated help command with admin-only labels
- Clarified which commands require admin access
- Updated README with permission requirements

## 1.1.0 — Major Feature Update (2025-11-04)

### Advance Timer
- Added 48-hour countdown timer with custom duration support
- Automatic notifications at 24h, 12h, 6h, and 1h remaining
- 'TIME'S UP! LET'S ADVANCE!' announcement when countdown ends
- Progress bar with color-coded urgency levels
- Commands: `/advance [hours]`, `/time_status`, `/stop_countdown`

### Channel Summarization
- AI-powered channel message summarization
- Customizable time periods (1-168 hours)
- Optional focus on specific topics
- Shows main topics, decisions, participants, and notable moments
- Fallback to basic stats when AI unavailable
- Command: `/summarize [hours] [focus]`

### Charter Management
- Direct charter editing from Discord
- Add new rules with AI-assisted formatting
- Update existing rule sections
- Automatic backups before every change
- View and restore from backup history
- Commands: `/add_rule`, `/update_rule`, `/view_charter_backups`, `/restore_charter_backup`

### Bot Admin System
- Manage bot admins directly through Discord
- Add/remove users as bot admins
- List all current bot admins
- Discord Administrators have automatic bot admin access
- Commands: `/add_bot_admin`, `/remove_bot_admin`, `/list_bot_admins`

### Other Improvements
- Added `/whats_new` command to showcase latest features
- Added `/changelog` command for version history
- Better error handling across all features
- Improved logging for debugging
- Maintained cockney personality throughout!

## 1.0.0 — Initial Release (2025-10-15)

### Core Features
- AI-powered responses about league rules
- League charter access and search
- Team information lookup
- Rivalry responses and fun interactions
- Slash commands for easy interaction
- Smart filtering for league-related questions

### AI Integration
- OpenAI GPT-3.5 integration
- Anthropic Claude support
- Context-aware responses
- Token usage tracking
- Sarcastic personality (Harry's trademark!)

### Commands
- /harry - Ask questions conversationally
- /ask - AI-powered rule answers
- /charter - Link to official charter
- /rules - League rules information
- /search - Search charter content
- /tokens - View AI usage statistics
