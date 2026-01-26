#!/usr/bin/env python3
"""
Version Manager for CFB 26 League Bot
Tracks versions and changelog
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger('CFB26Bot.Version')

# Current version
CURRENT_VERSION = "3.8.0"

# Changelog - organized by version
CHANGELOG: Dict[str, Dict] = {
    "3.8.0": {
        "date": "2026-01-26",
        "title": "Smart Duplicate Name Handling 🎯",
        "emoji": "🎯",
        "features": [
            {
                "category": "Position Filtering",
                "emoji": "🔍",
                "changes": [
                    "NEW: Position filter for duplicate player names",
                    "/recruiting player position:WR filters by position",
                    "13 position choices: QB, RB, WR, TE, OT, OG, C, EDGE, DL, LB, CB, S, ATH",
                    "Example: /recruiting player name:Elijah Brown position:WR",
                    "Works with both On3/Rivals and 247Sports"
                ]
            },
            {
                "category": "Multiple Candidate Selection",
                "emoji": "🎮",
                "changes": [
                    "NEW: Interactive player selection for duplicate names",
                    "Harry detects when multiple players match a name",
                    "Shows up to 5 candidates with key details (position, class, school, rating)",
                    "Discord select menu to choose the right player",
                    "Full profile loads instantly after selection",
                    "3-minute timeout for selection"
                ]
            },
            {
                "category": "UX Improvements",
                "emoji": "✨",
                "changes": [
                    "Position filter included in cache key (separate cache per position)",
                    "Position mismatch warnings logged for transparency",
                    "Suggestions in 'not found' message to use position filter",
                    "Smart fallback: exact matches → fuzzy matches → position filter"
                ]
            }
        ]
    },
    "3.7.0": {
        "date": "2026-01-22",
        "title": "Security Hardening & Optimizations 🔒",
        "emoji": "🔒",
        "features": [
            {
                "category": "Security Enhancements",
                "emoji": "🛡️",
                "changes": [
                    "API retry logic with exponential backoff (2^attempt)",
                    "Automatic retry on 429 rate limits with Retry-After",
                    "Input validation decorators (2000-char limit)",
                    "CORS middleware for dashboard (configurable origins)",
                    "All high-priority security issues resolved"
                ]
            },
            {
                "category": "Cost Optimizations",
                "emoji": "💰",
                "changes": [
                    "Recruiting rankings cached (24-hour TTL)",
                    "User-agent rotation to reduce Zyte usage",
                    "Smart fallback: Playwright → Cloudscraper → Zyte",
                    "Est. $3-5/mo additional savings on scraping"
                ]
            },
            {
                "category": "API Improvements",
                "emoji": "🔧",
                "changes": [
                    "@with_retry decorator for any async function",
                    "fetch_with_retry() helper for easy API calls",
                    "Handles network timeouts, connection errors",
                    "Configurable retry attempts and backoff"
                ]
            }
        ]
    },
    "3.6.0": {
        "date": "2026-01-22",
        "title": "Performance & Monitoring 🚀",
        "emoji": "🚀",
        "features": [
            {
                "category": "Performance Optimizations",
                "emoji": "⚡",
                "changes": [
                    "3x faster player lookups with parallel API calls",
                    "Multi-year stats now fetched simultaneously (15s → 5s)",
                    "AI response caching with 1-hour TTL",
                    "40-60% cache hit rate saves ~$15-20/mo",
                    "Instant responses for repeated AI questions"
                ]
            },
            {
                "category": "Monitoring Integration",
                "emoji": "📊",
                "changes": [
                    "Optional Sentry integration for error tracking",
                    "Performance metrics for all commands",
                    "Command execution time tracking",
                    "Cache hit/miss rate monitoring",
                    "Automatic warnings for slow commands (>5s)",
                    "Real-time error capture with user context"
                ]
            },
            {
                "category": "Technical Improvements",
                "emoji": "🔧",
                "changes": [
                    "asyncio.gather() for parallel API requests",
                    "MD5-based cache keys for AI responses",
                    "@track_performance decorator for instrumentation",
                    "Sentry transaction tracking support",
                    "Performance bottleneck identification"
                ]
            }
        ]
    },
    "3.5.0": {
        "date": "2026-01-13",
        "title": "Weekly Digest Reporting 📊",
        "emoji": "📊",
        "features": [
            {
                "category": "Automated Reporting",
                "emoji": "📧",
                "changes": [
                    "Weekly digest automatically sent to all admins",
                    "Checks daily at midnight for 7-day interval",
                    "Sends via DM to each admin",
                    "Includes cache performance, costs, budget status"
                ]
            },
            {
                "category": "Digest Commands",
                "emoji": "🎯",
                "changes": [
                    "/admin digest (view) - Preview digest instantly",
                    "/admin digest (send) - Manually trigger to all admins",
                    "Shows cache hit rate and cost savings",
                    "Displays AI usage stats",
                    "Budget status with color indicators"
                ]
            },
            {
                "category": "Weekly Summary",
                "emoji": "📈",
                "changes": [
                    "Cache performance (hit rate, savings)",
                    "Monthly costs (AI, Zyte, Total)",
                    "Budget status with visual indicators",
                    "AI usage (requests, tokens, cost)",
                    "Timestamp and date range"
                ]
            }
        ]
    },
    "3.4.0": {
        "date": "2026-01-13",
        "title": "Cost Tracking & Budgets 💰",
        "emoji": "💰",
        "features": [
            {
                "category": "Budget Management",
                "emoji": "📊",
                "changes": [
                    "Added /admin budget command to track monthly spending",
                    "Set budget limits for AI, Zyte, and total costs",
                    "Visual progress bars show percentage used",
                    "Color-coded indicators (green/yellow/red)",
                    "Shows remaining budget for each service"
                ]
            },
            {
                "category": "Cost Alerts",
                "emoji": "⚠️",
                "changes": [
                    "Automatic alerts at 50%, 80%, 90%, and 100% of budget",
                    "Alerts logged for each service (AI, Zyte, Total)",
                    "One alert per threshold per month",
                    "Prevents surprise bills"
                ]
            },
            {
                "category": "Configuration",
                "emoji": "⚙️",
                "changes": [
                    "AI_MONTHLY_BUDGET env var (default: $10)",
                    "ZYTE_MONTHLY_BUDGET env var (default: $5)",
                    "TOTAL_MONTHLY_BUDGET env var (default: $15)",
                    "Budgets reset monthly automatically"
                ]
            }
        ]
    },
    "3.3.0": {
        "date": "2026-01-13",
        "title": "Recruiting Data Cache 💾",
        "emoji": "💾",
        "features": [
            {
                "category": "Cost Optimization",
                "emoji": "💰",
                "changes": [
                    "Added intelligent caching system for recruiting player lookups",
                    "Player data cached for 24 hours (saves $$$ on API calls!)",
                    "Cache automatically invalidates when data expires",
                    "Added /admin cache command to view stats and manage cache",
                    "Shows estimated cost savings from cache hits",
                    "Can clear recruiting cache or all cache manually"
                ]
            },
            {
                "category": "Performance",
                "emoji": "🚀",
                "changes": [
                    "Instant responses for cached player lookups",
                    "Tracks cache hit rate for monitoring efficiency",
                    "Per-namespace cache organization (recruiting, etc.)",
                    "Automatic cleanup of expired entries"
                ]
            }
        ]
    },
    "3.2.0": {
        "date": "2026-01-13",
        "title": "API-Based Usage Tracking 🌐",
        "emoji": "🌐",
        "features": [
            {
                "category": "Enhanced Usage Tracking",
                "emoji": "📊",
                "changes": [
                    "Added official OpenAI Usage API integration",
                    "Added official Zyte Stats API integration",
                    "Multiple view options: Bot tracked, API official, or both side-by-side",
                    "/admin ai view:local - Bot-tracked stats (persisted)",
                    "/admin ai view:api - Official OpenAI API stats (last 30 days)",
                    "/admin ai view:both - Compare both data sources",
                    "/admin zyte view:local - Session stats from bot",
                    "/admin zyte view:api - Official Zyte API stats (last 30 days)",
                    "/admin zyte view:both - Compare both data sources"
                ]
            }
        ]
    },
    "3.1.0": {
        "date": "2026-01-13",
        "title": "AI Usage Tracking 🤖",
        "emoji": "🤖",
        "features": [
            {
                "category": "AI Monitoring",
                "emoji": "📊",
                "changes": [
                    "Added /admin ai command to track token usage and costs",
                    "Persistent tracking - stats survive bot restarts",
                    "Real-time monitoring of OpenAI (GPT-3.5) and Anthropic (Claude) API usage",
                    "Cost estimates and monthly projections",
                    "Separate tracking for each AI provider",
                    "Stored in Discord DMs for free persistence"
                ]
            }
        ]
    },
    "3.0.1": {
        "date": "2026-01-12",
        "title": "Cloudflare Bypass & Admin Enhancements 🎭",
        "emoji": "🎭",
        "features": [
            {
                "category": "Cloudflare Bypass",
                "emoji": "🌐",
                "changes": [
                    "Added Playwright headless browser for bulletproof scraping",
                    "Fallback chain: Playwright → Cloudscraper → httpx",
                    "No more On3 blocks!"
                ]
            },
            {
                "category": "247Sports Enhancements",
                "emoji": "📊",
                "changes": [
                    "Added offers, predictions, visits to 247Sports scraper",
                    "Added player images from 247Sports",
                    "Now matches On3 output format exactly"
                ]
            },
            {
                "category": "Admin Commands",
                "emoji": "⚙️",
                "changes": [
                    "/admin config enable_all - Enable all modules at once",
                    "/admin config disable_all - Disable all modules at once",
                    "Startup notification now only in dev channel with full status"
                ]
            }
        ]
    },
    "3.0.0": {
        "date": "2026-01-12",
        "title": "Cog Architecture 🏗️",
        "emoji": "🏗️",
        "features": [
            {
                "category": "Complete Refactor",
                "emoji": "🏗️",
                "changes": [
                    "Migrated from monolithic bot.py to cog-based architecture",
                    "8 modular cogs: Core, AI Chat, Recruiting, CFB Data, HS Stats, League, Charter, Admin",
                    "Better performance and maintainability",
                    "Comprehensive test suite with 59 passing tests"
                ]
            }
        ]
    },
    "2.5.1": {
        "date": "2026-01-11",
        "title": "UI Polish 💅",
        "emoji": "💅",
        "features": [
            {
                "category": "Recruiting Player",
                "emoji": "⭐",
                "changes": [
                    "Profile link now appears AFTER college stats (not before)",
                    "Better flow for transfer portal players"
                ]
            },
            {
                "category": "Command Cleanup",
                "emoji": "🧹",
                "changes": [
                    "/recruiting portal now suggests /recruiting player",
                    "Hidden from /help since /recruiting player does same thing"
                ]
            }
        ]
    },
    "2.5.0": {
        "date": "2026-01-11",
        "title": "Transfer Portal Detection! 🌀",
        "emoji": "🌀",
        "features": [
            {
                "category": "Transfer Portal Detection",
                "emoji": "🌀",
                "changes": [
                    "/recruiting player now shows 🌀 Transfer Portal section for portal players",
                    "Scrapes previous school, college experience, portal entry date, portal rating",
                    "/recruiting commits shows 🌀 indicator for transfer players",
                    "Detects transfers via H.S. graduation year + TR (Transfer Rating) indicator"
                ]
            },
            {
                "category": "Player Photos",
                "emoji": "📸",
                "changes": [
                    "/recruiting portal now shows player photo thumbnail"
                ]
            },
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed /recruiting rankings showing 0 teams",
                    "Fixed header rows appearing as 'Teams' in rankings",
                    "Updated On3 page parser for their new HTML structure"
                ]
            }
        ]
    },
    "2.4.0": {
        "date": "2026-01-11",
        "title": "Transfer Portal Command & Fuzzy Search!",
        "emoji": "🔄",
        "features": [
            {
                "category": "New /recruiting portal Command",
                "emoji": "🔄",
                "changes": [
                    "Combined recruiting data + college stats for transfers!",
                    "Shows On3 rating, predictions, offers + CFB career stats",
                    "Cross-references names between On3/CFB (handles nicknames)",
                    "Natural language: '@Harry tell me about portal player John Smith'"
                ]
            },
            {
                "category": "Fuzzy Name Matching",
                "emoji": "🔍",
                "changes": [
                    "Typos in first names now work! (Gavinn → Gavin)",
                    "Case insensitive search (JOHN SMITH → John Smith)",
                    "Falls back to last-name-only search for better matching",
                    "Prevents false positives with strict name validation"
                ]
            },
            {
                "category": "UI Improvements",
                "emoji": "✨",
                "changes": [
                    "/recruiting commits: wider display, 30 players, shows city",
                    "Shows 🏫 HS or 🔄 Transfer indicator on commits",
                    "CFB player stats: spacing between seasons",
                    "'Not found' messages now ephemeral (only you see them)"
                ]
            }
        ]
    },
    "2.3.1": {
        "date": "2026-01-11",
        "title": "Bug Fixes & UI Consistency",
        "emoji": "🔧",
        "features": [
            {
                "category": "Fixed",
                "emoji": "✅",
                "changes": [
                    "Fixed `/admin channels` timeout (now defers properly)",
                    "Fixed `/changelog` crashing when field > 1024 chars",
                    "Auto-responses now show '💤 Off' when AI Chat disabled",
                    "Consistent status display in `/admin config` and `/admin channels`"
                ]
            }
        ]
    },
    "2.2.0": {
        "date": "2026-01-10",
        "title": "AI Chat Toggle - Control Harry's Personality!",
        "emoji": "💬",
        "features": [
            {
                "category": "New AI_CHAT Module",
                "emoji": "🤖",
                "changes": [
                    "New toggleable `ai_chat` module for Harry's AI features",
                    "Disable `/harry`, `/ask`, `/summarize` per-server",
                    "Disable @Harry mentions and auto-responses",
                    "Keep recruiting/data features while silencing the chat"
                ]
            },
            {
                "category": "Usage",
                "emoji": "⚙️",
                "changes": [
                    "`/admin config disable ai_chat` - Silence Harry's chat",
                    "`/admin config enable ai_chat` - Enable Harry's chat",
                    "Core commands (`/help`, `/admin`) always available",
                    "Perfect for servers that only want data features!"
                ]
            }
        ]
    },
    "2.1.0": {
        "date": "2026-01-10",
        "title": "League Consolidation - Season & Timer Merged!",
        "emoji": "🏆",
        "features": [
            {
                "category": "Simplified Structure",
                "emoji": "📦",
                "changes": [
                    "Merged `/season` and `/timer` into `/league` group",
                    "All league management now under ONE command group!",
                    "Reduced from 8 groups to 6 groups",
                    "`/league` now has 19 commands covering everything"
                ]
            },
            {
                "category": "New /league Commands",
                "emoji": "🏆",
                "changes": [
                    "**Season:** `week`, `weeks`, `games`, `find_game`, `byes`, `set_week`",
                    "**Timer:** `timer`, `timer_status`, `timer_stop`, `timer_channel`",
                    "**Staff:** `staff`, `set_owner`, `set_commish`, `pick_commish`",
                    "**Fun:** `nag`, `stop_nag` 😈"
                ]
            },
            {
                "category": "Migration Guide",
                "emoji": "🔄",
                "changes": [
                    "`/season current` → `/league week`",
                    "`/season schedule` → `/league weeks`",
                    "`/timer start` → `/league timer`",
                    "`/timer status` → `/league timer_status`",
                    "`/timer stop` → `/league timer_stop`"
                ]
            }
        ]
    },
    "2.0.0": {
        "date": "2026-01-10",
        "title": "🚀 Command Reorganization - Grouped Commands!",
        "emoji": "🎉",
        "features": [
            {
                "category": "BREAKING: Command Structure",
                "emoji": "⚠️",
                "changes": [
                    "All 63 commands reorganized into logical groups!",
                    "Type `/group` to see all subcommands (e.g., `/recruiting`, `/cfb`)",
                    "Better discoverability - related commands are now together",
                    "Old commands like `/recruit` are now `/recruiting player`"
                ]
            },
            {
                "category": "Command Groups",
                "emoji": "📂",
                "changes": [
                    "`/recruiting` - Recruits, rankings, commits, class data",
                    "`/cfb` - College football stats, rankings, schedules",
                    "`/hs` - High school stats from MaxPreps",
                    "`/league` - Staff, season, timer, dynasty (consolidated)",
                    "`/charter` - Rules lookup, search, editing",
                    "`/admin` - Config, channels, bot admins"
                ]
            },
            {
                "category": "Updated Help",
                "emoji": "❓",
                "changes": [
                    "New `/help` command (renamed from `/help_cfb`)",
                    "Shows all command groups with subcommands",
                    "Quick reference for the new structure"
                ]
            }
        ]
    },
    "1.18.0": {
        "date": "2026-01-10",
        "title": "Team Commits List - See Who's Committed!",
        "emoji": "📋",
        "features": [
            {
                "category": "New Command",
                "emoji": "✨",
                "changes": [
                    "NEW: `/team_commits <team> [year]` - List all committed recruits for a team!",
                    "Shows each commit with: name, position, rating, stars, status (Signed/Committed)",
                    "High school and location for top recruits",
                    "Sorted by rating (highest first)",
                    "Link to full class on On3/Rivals",
                    "Example: `/team_commits Washington 2026` shows all 25 commits"
                ]
            },
            {
                "category": "Technical",
                "emoji": "⚙️",
                "changes": [
                    "New `get_team_commits()` method in On3Scraper",
                    "Dynamically finds team slug from rankings page",
                    "Parses position, height, weight, high school, location",
                    "Extracts industry rating and calculates star count",
                    "Currently On3/Rivals only (247Sports doesn't have commits list page)"
                ]
            }
        ]
    },
    "1.17.7": {
        "date": "2026-01-10",
        "title": "Fixed Recruiting Class Command for On3",
        "emoji": "📋",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed /recruiting_class not finding teams on On3",
                    "On3 uses listitem elements, not table rows",
                    "Now parses rank, commits, star breakdown, avg rating, NIL, and score",
                    "Washington 2026 class now shows: #15, 25 commits, 88.76 avg, $69K NIL"
                ]
            }
        ]
    },
    "1.17.6": {
        "date": "2026-01-10",
        "title": "Transfer Portal Support & Multi-Result Warnings",
        "emoji": "🔄",
        "features": [
            {
                "category": "On3/Rivals Improvements",
                "emoji": "⭐",
                "changes": [
                    "Transfer portal players now findable via /recruit",
                    "Scraper falls back to broader search when class year filter returns no results",
                    "Transfer status automatically detected and shown",
                    "Emmanuel Karnley (UW transfer) and similar players now work"
                ]
            },
            {
                "category": "HS Stats Improvements",
                "emoji": "🏫",
                "changes": [
                    "Warning shown when multiple players match a name",
                    "Displays other matching players so you know to add state filter",
                    "Tip to narrow results with /hs_stats name:X state:XX"
                ]
            }
        ]
    },
    "1.17.5": {
        "date": "2026-01-10",
        "title": "Enhanced HS Stats - Career Stats from MaxPreps",
        "emoji": "🏫",
        "features": [
            {
                "category": "HS Stats Improvements",
                "emoji": "📊",
                "changes": [
                    "Improved MaxPreps career stats parsing for all stat types",
                    "Fixed player name/school extraction from og:title metadata",
                    "Career defensive stats: solo tackles, total tackles, sacks, INTs",
                    "All-purpose yards including INT/kick/punt returns per season",
                    "Rushing, receiving, passing stats with per-game averages",
                    "Position detection (QB, WR, RB, DB, LB, etc.)",
                    "Physical info: height, weight, class year",
                    "Individual season breakdowns by grade level (Sr/Jr/So/Fr)",
                    "Career totals consolidated across all tables"
                ]
            },
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed regex bug that caused 'Tot283' to parse as '2' instead of '283'",
                    "Fixed position detection for 'V. Football #1 • DB' format",
                    "Removed duplicate import of 're' module",
                    "Empty receiving stats (all zeros) are now hidden"
                ]
            }
        ]
    },
    "1.17.4": {
        "date": "2026-01-10",
        "title": "On3/Rivals Recruiting Data - Offers, Predictions, Visits & Photos",
        "emoji": "🏈",
        "features": [
            {
                "category": "On3/Rivals Integration",
                "emoji": "⭐",
                "changes": [
                    "NEW: On3/Rivals recruiting scraper as alternative to 247Sports",
                    "Offers list - shows all schools that have offered",
                    "Predictions - shows RPM percentages for each school",
                    "Visits - shows official and unofficial visit history",
                    "Commitment status with signing dates",
                    "Industry composite ratings",
                    "Server-side rendered pages = reliable scraping"
                ]
            },
            {
                "category": "Recruit Data Enhancements",
                "emoji": "📊",
                "changes": [
                    "Player photos now displayed in Discord embed thumbnail!",
                    "Full profile data: stars, rating, national/position/state rank",
                    "Physical info: height, weight, hometown, high school",
                    "Top 5 predictions with percentages",
                    "Up to 8 offers displayed",
                    "Visit history with dates and types (Official/Unofficial)"
                ]
            }
        ]
    },
    "1.17.3": {
        "date": "2026-01-10",
        "title": "Private Admin Channel Support",
        "emoji": "🔒",
        "features": [
            {
                "category": "Improvements",
                "emoji": "⬆️",
                "changes": [
                    "/set_admin_channel now accepts channel_id for private channels",
                    "Use: /set_admin_channel channel_id:1459372492387778704",
                    "Works for channels Harry can't see in the picker"
                ]
            }
        ]
    },
    "1.17.2": {
        "date": "2026-01-10",
        "title": "Deep Search & Admin Channel",
        "emoji": "🔎",
        "features": [
            {
                "category": "New Features",
                "emoji": "✨",
                "changes": [
                    "/recruit now has `deep_search:True` option to search ALL ~3000 ranked recruits",
                    "Standard search covers top 1000 (~10 seconds)",
                    "Deep search covers all ~3100 recruits (~30 seconds)",
                    "/set_admin_channel - Set a private channel for bot updates & errors"
                ]
            }
        ]
    },
    "1.17.1": {
        "date": "2026-01-10",
        "title": "Recruiting Search Expansion",
        "emoji": "🔍",
        "features": [
            {
                "category": "Improvements",
                "emoji": "⬆️",
                "changes": [
                    "Expanded recruit search from top 150 to top 1000 recruits",
                    "Reduced rate limit delay (0.5s) for faster searches (~10s for top 1000)",
                    "Added progress logging for deep searches",
                    "Auto-stops at end of rankings instead of fixed page limit",
                    "Most recruits people look up are in top 500 (~5 seconds)"
                ]
            }
        ]
    },
    "1.17.0": {
        "date": "2026-01-10",
        "title": "247Sports Recruiting Module",
        "emoji": "⭐",
        "features": [
            {
                "category": "New Features",
                "emoji": "⭐",
                "changes": [
                    "NEW MODULE: 247Sports Recruiting data (web scraping)",
                    "/recruit <name> - Look up individual recruit's composite ranking",
                    "/top_recruits - Get top recruits, filter by position or state",
                    "/recruiting_class <team> - Get team's recruiting class details",
                    "/recruiting_rankings - Top 25 team recruiting rankings",
                    "Composite ratings combining 247, Rivals, ESPN, On3",
                    "Star ratings, national/position/state rankings",
                    "Commitment tracking",
                    "Enable with: /config enable recruiting"
                ]
            }
        ]
    },
    "1.16.4": {
        "date": "2026-01-10",
        "title": "Bulk Lookup Detection Fix",
        "emoji": "🔧",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed bulk lookup not triggering for 'Tell me about:' and similar phrases",
                    "Added more bulk indicators: 'tell me about:', 'about these', 'look up:', etc.",
                    "Improved player line detection - no longer requires parentheses",
                    "Detects 'Name Position Team' format (e.g., Sam Huard QB USC)",
                    "Detects 3-word lines as potential player entries",
                    "Added logging to show bulk lookup trigger reason"
                ]
            }
        ]
    },
    "1.16.3": {
        "date": "2026-01-10",
        "title": "Bulk Lookup Parser Fix",
        "emoji": "🔧",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed bulk player lookup not recognizing 'Name Position Team' format",
                    "Parser now handles: Sam Huard QB USC, Armon Parker DL Washington",
                    "Added Pattern 4: Name Position Team (without parentheses)",
                    "Added Pattern 5: Name Team (FirstName LastName School)",
                    "Improved parser logging for debugging"
                ]
            }
        ]
    },
    "1.16.2": {
        "date": "2026-01-10",
        "title": "League Context Isolation",
        "emoji": "🔒",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "CRITICAL: Fixed AI leaking league schedule data to non-league servers",
                    "AI prompts now respect LEAGUE module status per server",
                    "Non-league servers no longer see schedule/charter context in AI responses",
                    "Added include_league_context parameter to all AI methods",
                    "League-specific AI features properly isolated from general CFB assistant mode"
                ]
            }
        ]
    },
    "1.16.1": {
        "date": "2026-01-10",
        "title": "Guild Debugging & Logging",
        "emoji": "🔍",
        "features": [
            {
                "category": "Improvements",
                "emoji": "🔍",
                "changes": [
                    "Added detailed guild listing on startup (shows each server name, ID, member count)",
                    "Added on_guild_join event to log when bot joins new servers",
                    "Added on_guild_remove event to log when bot is removed from servers",
                    "Auto-syncs commands to newly joined guilds",
                    "Better debugging for missing guild connections"
                ]
            }
        ]
    },
    "1.16.0": {
        "date": "2026-01-09",
        "title": "League Module Separation",
        "emoji": "🏈",
        "features": [
            {
                "category": "Module Separation",
                "emoji": "🏈",
                "changes": [
                    "League-specific features now gated behind LEAGUE module",
                    "Charter links only show when LEAGUE is enabled",
                    "Generic CFB assistant mode when LEAGUE is disabled",
                    "Footer dynamically changes based on server config",
                    "Reaction responses adapt to LEAGUE status",
                    "/harry command works for general CFB without LEAGUE",
                    "/rule command now requires LEAGUE module"
                ]
            }
        ]
    },
    "1.15.3": {
        "date": "2026-01-09",
        "title": "Interaction Timeout Fix",
        "emoji": "⚡",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "⚡",
                "changes": [
                    "Fixed 'Unknown interaction' timeout errors on CFB data commands",
                    "All API commands now defer() FIRST before module checks",
                    "Added check_module_enabled_deferred() for post-defer validation",
                    "Prevents Discord's 3-second response window from expiring"
                ]
            }
        ]
    },
    "1.15.2": {
        "date": "2026-01-09",
        "title": "Timer Notification Fix",
        "emoji": "🐛",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed 'Error in countdown monitoring: 24' bug",
                    "JSON dict keys are strings - now converts to ints after load",
                    "Improved error logging to show exception type"
                ]
            }
        ]
    },
    "1.15.1": {
        "date": "2026-01-09",
        "title": "Code Cleanup & Optimization",
        "emoji": "🧹",
        "features": [
            {
                "category": "Code Quality",
                "emoji": "🧹",
                "changes": [
                    "Added Colors class with constants for consistent theming",
                    "Added Footers class for standard footer texts",
                    "Replaced 132 hardcoded color values with constants",
                    "Replaced 39 hardcoded footer strings with constants",
                    "Fixed indentation issues in reaction handlers",
                    "Improved code maintainability and consistency"
                ]
            }
        ]
    },
    "1.15.0": {
        "date": "2026-01-09",
        "title": "High School Stats Scraper",
        "emoji": "🏫",
        "features": [
            {
                "category": "MaxPreps Scraper",
                "emoji": "🏫",
                "changes": [
                    "NEW: /hs_stats - Look up high school football player stats",
                    "NEW: /hs_stats_bulk - Bulk lookup for multiple HS players",
                    "NEW: @Harry HS stats support (e.g., 'HS stats for Arch Manning')",
                    "Web scraping from MaxPreps with caching (24hr)",
                    "Rate limiting to be respectful of MaxPreps servers",
                    "Parses passing, rushing, receiving, and defensive stats"
                ]
            },
            {
                "category": "Module Configuration",
                "emoji": "⚙️",
                "changes": [
                    "HS_STATS module OFF by default (opt-in feature)",
                    "Enable with /module enable hs_stats",
                    "Requires httpx and beautifulsoup4 packages"
                ]
            }
        ]
    },
    "1.14.0": {
        "date": "2026-01-09",
        "title": "Admin Channel & Notifications",
        "emoji": "🔧",
        "features": [
            {
                "category": "Admin Channel",
                "emoji": "🔧",
                "changes": [
                    "NEW: /set_admin_channel to configure admin output channel",
                    "Bot startup notifications sent to admin channel",
                    "Timer restore messages use configured admin channel",
                    "Error reports sent to admin channel",
                    "Config change logs (module enable/disable)"
                ]
            },
            {
                "category": "Ephemeral Responses",
                "emoji": "👁️",
                "changes": [
                    "All admin/config commands now user-only (ephemeral)",
                    "/config, /channel, /list_bot_admins - only you see them",
                    "Keeps admin clutter out of public channels"
                ]
            },
            {
                "category": "Config Improvements",
                "emoji": "⚙️",
                "changes": [
                    "/config now shows admin channel, enabled channels, rivalry status",
                    "League settings only shown when League module is enabled",
                    "Renamed toggle_auto to toggle_rivalry for clarity"
                ]
            }
        ]
    },
    "1.13.0": {
        "date": "2026-01-09",
        "title": "Storage Abstraction Layer",
        "emoji": "📦",
        "features": [
            {
                "category": "Scalable Storage",
                "emoji": "📦",
                "changes": [
                    "NEW: Storage abstraction layer for future-proofing",
                    "Easy swap between Discord DM and database storage",
                    "STORAGE_BACKEND env var to switch backends",
                    "Placeholder for Supabase (PostgreSQL) integration"
                ]
            },
            {
                "category": "How to Scale Later",
                "emoji": "🚀",
                "changes": [
                    "1. Create Supabase project (free tier works!)",
                    "2. Set SUPABASE_URL and SUPABASE_KEY env vars",
                    "3. Set STORAGE_BACKEND=supabase",
                    "4. Deploy - configs auto-migrate!"
                ]
            }
        ]
    },
    "1.12.0": {
        "date": "2026-01-09",
        "title": "Per-Channel Controls",
        "emoji": "📺",
        "features": [
            {
                "category": "Channel Management",
                "emoji": "📺",
                "changes": [
                    "NEW: /channel command to manage where Harry responds",
                    "Channel whitelist - enable specific channels only",
                    "Per-channel auto-response toggles",
                    "Harry stays silent in non-whitelisted channels"
                ]
            },
            {
                "category": "Channel Commands",
                "emoji": "⚙️",
                "changes": [
                    "/channel view - See current channel settings",
                    "/channel enable - Add channel to whitelist",
                    "/channel disable - Remove from whitelist",
                    "/channel enable_all - Clear whitelist (allow all)",
                    "/channel toggle_auto - Toggle auto-responses per channel"
                ]
            }
        ]
    },
    "1.11.0": {
        "date": "2026-01-09",
        "title": "Auto Response Toggle",
        "emoji": "💬",
        "features": [
            {
                "category": "Auto Responses Toggle",
                "emoji": "💬",
                "changes": [
                    "NEW: Toggle automatic jump-in responses (team banter)",
                    "Harry's cockney personality and Oregon hate are ALWAYS ON",
                    "Only controls 'Fuck Oregon!' style auto-responses",
                    "Oregon player lookup snark always shows (part of personality)"
                ]
            },
            {
                "category": "Simplified Settings",
                "emoji": "⚙️",
                "changes": [
                    "Removed separate cockney/rivalry toggles",
                    "Single 'Auto Responses' toggle in dashboard",
                    "Harry is always a cockney asshole Duck-hater 🦆"
                ]
            }
        ]
    },
    "1.10.0": {
        "date": "2026-01-08",
        "title": "Smart Player Suggestions",
        "emoji": "💡",
        "features": [
            {
                "category": "Bulk Player Lookup",
                "emoji": "🔍",
                "changes": [
                    "NEW: 'Did you mean?' suggestions for players not found",
                    "FCS school detection - warns when querying limited-data schools",
                    "Automatic retry without team filter if initial search fails",
                    "Shows similar players from last name / first name searches",
                    "Helpful reasons explaining why a player wasn't found"
                ]
            },
            {
                "category": "FCS Coverage",
                "emoji": "🏈",
                "changes": [
                    "Added FCS conference and school database",
                    "Detects Mercer, ETSU, and other FCS schools",
                    "Warns users about limited CFBD data coverage for FCS"
                ]
            }
        ]
    },
    "1.9.1": {
        "date": "2026-01-08",
        "title": "Bulk Lookup Type Fix",
        "emoji": "🔧",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed 'can only concatenate str to str' error in bulk player lookup",
                    "API sometimes returns stats as strings - now properly converted to integers",
                    "Defensive stat calculations now work correctly across all player types"
                ]
            }
        ]
    },
    "1.9.0": {
        "date": "2026-01-08",
        "title": "Web Dashboard",
        "emoji": "🌐",
        "features": [
            {
                "category": "Web Dashboard",
                "emoji": "🌐",
                "changes": [
                    "NEW: Full web dashboard for managing Harry!",
                    "Login with Discord OAuth",
                    "Visual toggle for modules (CFB Data, League)",
                    "Manage bot admins with clicks",
                    "Beautiful dark theme UI"
                ]
            },
            {
                "category": "Dashboard Features",
                "emoji": "⚙️",
                "changes": [
                    "Server selector for multi-server management",
                    "Enable/disable modules per server",
                    "Add/remove bot admins visually",
                    "See available commands per module"
                ]
            },
            {
                "category": "Technical",
                "emoji": "🔧",
                "changes": [
                    "FastAPI backend with async support",
                    "Discord OAuth2 integration",
                    "Session-based authentication",
                    "RESTful API for config management"
                ]
            }
        ]
    },
    "1.8.1": {
        "date": "2026-01-08",
        "title": "Bulk Player Lookup",
        "emoji": "📋",
        "features": [
            {
                "category": "Bulk Player Lookup",
                "emoji": "📋",
                "changes": [
                    "NEW: Look up multiple players at once!",
                    "/players command for slash interface",
                    "Natural language: just paste a list to @Harry",
                    "Supports various formats: Name (Team Pos), Name from Team, etc.",
                    "Parallel lookups for speed (up to 15 players)",
                    "Compact display with key stats and recruiting info"
                ]
            }
        ]
    },
    "1.8.0": {
        "date": "2026-01-08",
        "title": "Per-Server Feature Configuration",
        "emoji": "⚙️",
        "features": [
            {
                "category": "Server Configuration",
                "emoji": "⚙️",
                "changes": [
                    "NEW: `/config` - Enable/disable features per server",
                    "Modules: Core (always on), CFB Data, League",
                    "Settings persist across bot restarts",
                    "Admins can customize Harry for their server"
                ]
            },
            {
                "category": "Module: Core (Always On)",
                "emoji": "🤖",
                "changes": [
                    "Harry's personality - always available!",
                    "General AI chat and questions",
                    "/ask, /help, /whats_new, /changelog",
                    "Bot admin management"
                ]
            },
            {
                "category": "Module: CFB Data",
                "emoji": "🏈",
                "changes": [
                    "Player lookup, rankings, matchups",
                    "Schedules, draft, transfers, betting, ratings",
                    "Enable: `/config enable cfb_data`",
                    "Enabled by default on new servers"
                ]
            },
            {
                "category": "Module: League Features",
                "emoji": "🏆",
                "changes": [
                    "Timer, advance, charter, rules",
                    "League staff, pick commish, dynasty schedule",
                    "Enable: `/config enable league`",
                    "Disabled by default (opt-in for dynasty servers)"
                ]
            }
        ]
    },
    "1.7.0": {
        "date": "2026-01-08",
        "title": "Full CFB Data Suite",
        "emoji": "🏈",
        "features": [
            {
                "category": "Team Rankings",
                "emoji": "📊",
                "changes": [
                    "NEW: /rankings - Get AP, Coaches, CFP rankings",
                    "Check specific team: '@Harry where is Ohio State ranked?'",
                    "Top 25 poll display for all major polls"
                ]
            },
            {
                "category": "Matchup History",
                "emoji": "🏈",
                "changes": [
                    "NEW: /matchup - All-time records between rivals",
                    "'@Harry Alabama vs Auburn history'",
                    "Shows win/loss record and last 5 games"
                ]
            },
            {
                "category": "Team Schedules",
                "emoji": "📅",
                "changes": [
                    "NEW: /cfb_schedule - Full season schedule & results",
                    "'@Harry when does Nebraska play next?'",
                    "Shows W/L, scores, home/away for completed games"
                ]
            },
            {
                "category": "NFL Draft",
                "emoji": "🏈",
                "changes": [
                    "NEW: /draft_picks - NFL draft picks by college",
                    "'@Harry who got drafted from Georgia?'",
                    "Shows round, pick, position, and NFL team"
                ]
            },
            {
                "category": "Transfer Portal",
                "emoji": "🔄",
                "changes": [
                    "NEW: /transfers - Portal activity by team",
                    "'@Harry USC transfers'",
                    "Shows incoming AND outgoing transfers with ratings"
                ]
            },
            {
                "category": "Betting Lines",
                "emoji": "💰",
                "changes": [
                    "NEW: /betting - Game spreads and O/U",
                    "'@Harry who's favored in Bama vs Georgia?'",
                    "Shows spread and over/under for games"
                ]
            },
            {
                "category": "Advanced Ratings",
                "emoji": "📈",
                "changes": [
                    "NEW: /team_ratings - SP+, SRS, Elo ratings",
                    "'@Harry how good is Texas?'",
                    "Shows offensive/defensive rankings, SRS, Elo"
                ]
            },
            {
                "category": "Natural Language",
                "emoji": "💬",
                "changes": [
                    "All features work with natural @Harry questions!",
                    "Auto-detects query type (player, rankings, matchup, etc.)",
                    "Same cockney personality throughout"
                ]
            }
        ]
    },
    "1.6.1": {
        "date": "2026-01-08",
        "title": "Enhanced Player Lookup with Official API",
        "emoji": "🏈",
        "features": [
            {
                "category": "Official CFBD Library",
                "emoji": "📚",
                "changes": [
                    "Refactored to use official cfbd Python library",
                    "More reliable API calls with proper error handling",
                    "Better type safety and cleaner code",
                    "Access to all CFBD endpoints"
                ]
            },
            {
                "category": "Transfer Portal",
                "emoji": "🔄",
                "changes": [
                    "NEW: Shows transfer info for portal players!",
                    "See origin → destination team",
                    "Eligibility status displayed",
                    "Automatically detects if player transferred"
                ]
            },
            {
                "category": "Enhanced Recruiting",
                "emoji": "⭐",
                "changes": [
                    "National ranking, position rank, state rank",
                    "Full recruiting class data",
                    "Searches multiple recruiting years automatically"
                ]
            },
            {
                "category": "Natural Language",
                "emoji": "💬",
                "changes": [
                    "40+ different ways to ask about a player",
                    "Handles team patterns: from/at/plays for/comma",
                    "Strips Discord mentions automatically"
                ]
            }
        ]
    },
    "1.6.0": {
        "date": "2026-01-08",
        "title": "Player Lookup Feature",
        "emoji": "🏈",
        "features": [
            {
                "category": "Player Lookup",
                "emoji": "🔍",
                "changes": [
                    "NEW: /player command to look up any CFB player!",
                    "Get vitals: position, height, weight, year, hometown",
                    "View season stats: tackles, TFL, sacks, yards, TDs",
                    "See recruiting info: star rating, national ranking",
                    "Natural language: '@Harry what do you know about X from Alabama?'"
                ]
            },
            {
                "category": "Integration",
                "emoji": "🔗",
                "changes": [
                    "Powered by CollegeFootballData.com API",
                    "Search by name or name + team",
                    "Supports all positions: QB, RB, WR, DT, LB, etc.",
                    "(And yes, I'll still mock Oregon players)"
                ]
            }
        ]
    },
    "1.5.1": {
        "date": "2026-01-02",
        "title": "Schedule Display & Admin Notifications",
        "emoji": "📅",
        "features": [
            {
                "category": "Schedule Display",
                "emoji": "🏈",
                "changes": [
                    "Matchups now show on /advance and @everyone advanced",
                    "User teams are **bolded** in all schedule outputs",
                    "AI responses format schedules as clean lists",
                    "Bye teams included in advance announcements"
                ]
            },
            {
                "category": "Admin Notifications",
                "emoji": "🔔",
                "changes": [
                    "Timer restore message shows version info",
                    "Quick preview of latest changes on restart",
                    "Helps admins see what changed after deploy"
                ]
            }
        ]
    },
    "1.5.0": {
        "date": "2025-12-31",
        "title": "Discord Charter Persistence & Poll Support",
        "emoji": "📜",
        "features": [
            {
                "category": "Charter Persistence",
                "emoji": "💾",
                "changes": [
                    "Charter now saves to Discord - survives deployments!",
                    "Automatic sync on any charter update",
                    "/sync_charter command to manually push to Discord",
                    "Falls back to file if no Discord version exists",
                    "Charter stored in bot owner's DM (invisible to users)"
                ]
            },
            {
                "category": "Discord Poll Support",
                "emoji": "🗳️",
                "changes": [
                    "/scan_rules now detects Discord polls!",
                    "Extracts poll questions and vote counts",
                    "Shows winning answer for closed polls",
                    "Analyzes both text messages and polls"
                ]
            },
            {
                "category": "Pick Commish Improvements",
                "emoji": "👑",
                "changes": [
                    "Added channel selection: /pick_commish #channel",
                    "DO NOT PICK and BIGGEST ASSHOLE are now separate",
                    "Asshole score based on actual toxic behavior, not ranking"
                ]
            }
        ]
    },
    "1.4.1": {
        "date": "2025-12-31",
        "title": "Code Quality & Settings Persistence",
        "emoji": "🔧",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed all bare 'except:' blocks with specific exception types",
                    "Notification channel now persists across bot restarts",
                    "/set_timer_channel setting is saved to Discord"
                ]
            },
            {
                "category": "Code Quality",
                "emoji": "🔧",
                "changes": [
                    "Added get_notification_channel() helper for consistent channel lookup",
                    "Refactored exception handling for better error tracking",
                    "Updated README with v1.4.0 features"
                ]
            }
        ]
    },
    "1.4.0": {
        "date": "2025-12-31",
        "title": "Server-Wide Timer & Ephemeral Messages",
        "emoji": "📢",
        "features": [
            {
                "category": "Server-Wide Timer Notifications",
                "emoji": "📢",
                "changes": [
                    "Timer notifications now always go to #general",
                    "One timer for the whole server (not per-channel)",
                    "Includes: Advance start, 24h/12h/6h/1h warnings, TIME'S UP",
                    "/set_timer_channel to change notification channel",
                    "Schedule announcements also go to timer channel"
                ]
            },
            {
                "category": "Ephemeral Admin Messages",
                "emoji": "👁️",
                "changes": [
                    "Admin confirmations now only visible to the admin",
                    "/stop_countdown success → ephemeral",
                    "/set_season_week success → ephemeral",
                    "/set_league_owner success → ephemeral",
                    "/set_co_commish success → ephemeral",
                    "/advance confirmation → ephemeral (announcement goes to #general)",
                    "Timer Restored → goes to admin channel only"
                ]
            }
        ]
    },
    "1.3.0": {
        "date": "2025-12-31",
        "title": "Interactive Charter & Co-Commish Picker",
        "emoji": "👑",
        "features": [
            {
                "category": "Interactive Charter Updates",
                "emoji": "📝",
                "changes": [
                    "Update charter by talking to Harry naturally!",
                    "Example: '@Harry update the advance time to 10am'",
                    "Example: '@Harry add a rule: no trading during playoffs'",
                    "Before/after preview with ✅/❌ confirmation",
                    "Automatic backup before any change",
                    "Changelog tracks who changed what and when",
                    "/charter_history command to view recent changes"
                ]
            },
            {
                "category": "Rule Scanning",
                "emoji": "🔍",
                "changes": [
                    "/scan_rules command to find rule changes in voting channels",
                    "Natural language: '@Harry scan #voting for rule changes'",
                    "AI identifies passed/failed/proposed rules",
                    "Shows vote counts when available",
                    "React with 📝 to generate charter updates",
                    "Apply all passed rules to charter with one click"
                ]
            },
            {
                "category": "Co-Commissioner Picker",
                "emoji": "👑",
                "changes": [
                    "/pick_commish command for AI-powered recommendations",
                    "Analyzes chat activity and participation",
                    "🚨 ASSHOLE DETECTOR - rates toxic behavior!",
                    "Scores: Activity, Helpfulness, Leadership, Drama, Vibes",
                    "Ranks ALL participants with personalized roasts",
                    "Calls out biggest asshole who should NEVER be commish"
                ]
            },
            {
                "category": "League Staff Tracking",
                "emoji": "👔",
                "changes": [
                    "/league_staff - View current owner and co-commissioner",
                    "/set_league_owner - Set the league owner",
                    "/set_co_commish - Set the co-commissioner",
                    "Special option: 'We don't fucking have one' for co-commish",
                    "Persists across bot restarts"
                ]
            },
            {
                "category": "Code Quality",
                "emoji": "🔧",
                "changes": [
                    "Fixed all bare 'except:' blocks with specific exceptions",
                    "Added cleanup task for expired pending requests",
                    "Memory leak prevention for processed messages",
                    "Python 3.13 compatibility improvements"
                ]
            }
        ]
    },
    "1.2.0": {
        "date": "2025-12-29",
        "title": "CFB 26 Dynasty Week System",
        "emoji": "🏈",
        "features": [
            {
                "category": "Dynasty Week Counter",
                "emoji": "📅",
                "changes": [
                    "Added full CFB 26 Dynasty season week structure (30 weeks total)",
                    "Regular Season: Week 0 (Season Kickoff) through Week 15",
                    "Post-Season: Conference Championships, Bowl Weeks 1-4, End of Season Recap",
                    "Offseason: Portal Weeks 1-4, National Signing Day, Training Results",
                    "Offseason: Encourage Transfers, Preseason",
                    "Season phase tracking (Regular Season, Post-Season, Offseason)"
                ]
            },
            {
                "category": "Week Actions & Notes",
                "emoji": "📋",
                "changes": [
                    "Each week now shows available actions (staff moves, job offers, etc.)",
                    "Important notes displayed (last chance reminders, deadlines)",
                    "Bowl weeks show hiring/firing windows",
                    "Offseason weeks show portal and recruiting actions",
                    "/time_status shows upcoming week actions"
                ]
            },
            {
                "category": "Improved Display",
                "emoji": "✨",
                "changes": [
                    "Week transitions now show proper CFB 26 week names",
                    "Season phase displayed alongside week info",
                    "/time_status shows current and next week with actions",
                    "/set_season_week shows proper week name, phase, and actions",
                    "Times Up message displays phase and week progression"
                ]
            }
        ]
    },
    "1.1.1": {
        "date": "2025-11-04",
        "title": "Bug Fixes & Improvements",
        "emoji": "🐛",
        "features": [
            {
                "category": "Bug Fixes",
                "emoji": "🐛",
                "changes": [
                    "Fixed summarizer timezone compatibility issue (discord.utils.utc → timezone.utc)",
                    "Channel summarization now works with all discord.py versions",
                    "Guild-specific command sync for instant updates (5 seconds vs 1 hour)",
                    "Commands now appear immediately in configured servers"
                ]
            },
            {
                "category": "Security & Permissions",
                "emoji": "🔐",
                "changes": [
                    "Advance timer commands now require admin permissions",
                    "/advance restricted to admins only",
                    "/stop_countdown now uses bot admin system",
                    "Added hardcoded admin support for permanent admins",
                    "Both Discord Administrators and Bot Admins can manage timers"
                ]
            },
            {
                "category": "Configuration",
                "emoji": "⚙️",
                "changes": [
                    "Added support for multiple guild instant sync",
                    "Configured two servers for instant command updates",
                    "Improved admin permission checking across all commands"
                ]
            },
            {
                "category": "Documentation",
                "emoji": "📖",
                "changes": [
                    "Updated help command with admin-only labels",
                    "Clarified which commands require admin access",
                    "Updated README with permission requirements"
                ]
            }
        ]
    },
    "1.1.0": {
        "date": "2025-11-04",
        "title": "Major Feature Update",
        "emoji": "🎉",
        "features": [
            {
                "category": "Advance Timer",
                "emoji": "⏰",
                "changes": [
                    "Added 48-hour countdown timer with custom duration support",
                    "Automatic notifications at 24h, 12h, 6h, and 1h remaining",
                    "'TIME'S UP! LET'S ADVANCE!' announcement when countdown ends",
                    "Progress bar with color-coded urgency levels",
                    "Commands: `/advance [hours]`, `/time_status`, `/stop_countdown`"
                ]
            },
            {
                "category": "Channel Summarization",
                "emoji": "📊",
                "changes": [
                    "AI-powered channel message summarization",
                    "Customizable time periods (1-168 hours)",
                    "Optional focus on specific topics",
                    "Shows main topics, decisions, participants, and notable moments",
                    "Fallback to basic stats when AI unavailable",
                    "Command: `/summarize [hours] [focus]`"
                ]
            },
            {
                "category": "Charter Management",
                "emoji": "📝",
                "changes": [
                    "Direct charter editing from Discord",
                    "Add new rules with AI-assisted formatting",
                    "Update existing rule sections",
                    "Automatic backups before every change",
                    "View and restore from backup history",
                    "Commands: `/add_rule`, `/update_rule`, `/view_charter_backups`, `/restore_charter_backup`"
                ]
            },
            {
                "category": "Bot Admin System",
                "emoji": "🔐",
                "changes": [
                    "Manage bot admins directly through Discord",
                    "Add/remove users as bot admins",
                    "List all current bot admins",
                    "Discord Administrators have automatic bot admin access",
                    "Commands: `/add_bot_admin`, `/remove_bot_admin`, `/list_bot_admins`"
                ]
            },
            {
                "category": "Other Improvements",
                "emoji": "✨",
                "changes": [
                    "Added `/whats_new` command to showcase latest features",
                    "Added `/changelog` command for version history",
                    "Better error handling across all features",
                    "Improved logging for debugging",
                    "Maintained cockney personality throughout!"
                ]
            }
        ]
    },
    "1.0.0": {
        "date": "2025-10-15",
        "title": "Initial Release",
        "emoji": "🚀",
        "features": [
            {
                "category": "Core Features",
                "emoji": "🏈",
                "changes": [
                    "AI-powered responses about league rules",
                    "League charter access and search",
                    "Team information lookup",
                    "Rivalry responses and fun interactions",
                    "Slash commands for easy interaction",
                    "Smart filtering for league-related questions"
                ]
            },
            {
                "category": "AI Integration",
                "emoji": "🤖",
                "changes": [
                    "OpenAI GPT-3.5 integration",
                    "Anthropic Claude support",
                    "Context-aware responses",
                    "Token usage tracking",
                    "Sarcastic personality (Harry's trademark!)"
                ]
            },
            {
                "category": "Commands",
                "emoji": "⚡",
                "changes": [
                    "/harry - Ask questions conversationally",
                    "/ask - AI-powered rule answers",
                    "/charter - Link to official charter",
                    "/rules - League rules information",
                    "/search - Search charter content",
                    "/tokens - View AI usage statistics"
                ]
            }
        ]
    }
}

class VersionManager:
    """Manages version information and changelog"""

    def __init__(self):
        self.current_version = CURRENT_VERSION
        self.changelog = CHANGELOG

    def get_current_version(self) -> str:
        """Get the current version string"""
        return self.current_version

    def get_version_info(self, version: str) -> Optional[Dict]:
        """Get information about a specific version"""
        return self.changelog.get(version)

    def get_all_versions(self) -> List[str]:
        """Get list of all versions"""
        return sorted(self.changelog.keys(), reverse=True)

    def get_latest_version_info(self) -> Dict:
        """Get information about the latest version"""
        return self.changelog.get(self.current_version, {})

    def format_version_embed_data(self, version: str) -> Optional[Dict]:
        """
        Format version data for Discord embed

        Returns:
            Dict with title, description, and fields for embed
        """
        version_info = self.get_version_info(version)
        if not version_info:
            return None

        embed_data = {
            "title": f"{version_info['emoji']} Version {version} - {version_info['title']}",
            "description": f"Released: {version_info['date']}",
            "fields": []
        }

        for feature_group in version_info.get('features', []):
            category = feature_group.get('category', 'Features')
            emoji = feature_group.get('emoji', '•')
            changes = feature_group.get('changes', [])

            # Format changes as bullet points
            changes_text = '\n'.join([f"• {change}" for change in changes])

            embed_data["fields"].append({
                "name": f"{emoji} {category}",
                "value": changes_text,
                "inline": False
            })

        return embed_data

    def get_version_summary(self) -> str:
        """Get a summary of all versions"""
        versions = self.get_all_versions()
        summary_lines = []

        for version in versions:
            info = self.changelog.get(version, {})
            emoji = info.get('emoji', '📌')
            title = info.get('title', 'Update')
            date = info.get('date', 'Unknown')
            summary_lines.append(f"{emoji} **v{version}** - {title} ({date})")

        return '\n'.join(summary_lines)

    def compare_versions(self, from_version: str, to_version: str) -> List[str]:
        """
        Get all changes between two versions

        Returns:
            List of change descriptions
        """
        all_versions = self.get_all_versions()

        try:
            from_idx = all_versions.index(from_version)
            to_idx = all_versions.index(to_version)

            # Get versions between (inclusive)
            if from_idx > to_idx:
                from_idx, to_idx = to_idx, from_idx

            versions_between = all_versions[to_idx:from_idx+1]

            all_changes = []
            for version in versions_between:
                version_info = self.changelog.get(version, {})
                for feature_group in version_info.get('features', []):
                    changes = feature_group.get('changes', [])
                    all_changes.extend(changes)

            return all_changes

        except ValueError:
            return []
