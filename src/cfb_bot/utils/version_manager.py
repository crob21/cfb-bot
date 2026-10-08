#!/usr/bin/env python3
"""
Version Manager for CFB League Bot
Tracks versions and changelog
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger('CFBBot.Version')


def version_key(version: str) -> tuple:
    """Sort key for 'major.minor.patch' strings."""
    return tuple(int(part) for part in version.split('.'))

# Current version
CURRENT_VERSION = "3.17.1"

# Recent releases, newest first. /changelog reads these; the full history is in
# docs/CHANGELOG.md. Add new releases at the top.
CHANGELOG: Dict[str, Dict] = {
    "3.17.1": {
        "date": "2026-10-08",
        "title": "Harry Gets a Better Brain 🧠",
        "emoji": "🧠",
        "features": [
            {
                "category": "AI",
                "emoji": "🧠",
                "changes": [
                    "Upgraded OpenAI from the legacy gpt-3.5-turbo to gpt-5-mini — a far better brain",
                    "Request parameters adapt to the model family (GPT-5 and o-series renamed max_tokens)",
                    "NEW: OPENAI_MODEL and ANTHROPIC_MODEL env vars — swapping models is a host setting now",
                    "FIX: /admin ai and /admin budget priced every call as gpt-3.5-turbo, overstating spend",
                    "Cost estimates are env-configurable too (OPENAI_COST_PER_1K, ANTHROPIC_COST_PER_1K)"
                ]
            }
        ]
    },
    "3.17.0": {
        "date": "2026-10-08",
        "title": "Harry Answers When You @ Him 💬",
        "emoji": "💬",
        "features": [
            {
                "category": "AI Chat",
                "emoji": "💬",
                "changes": [
                    "NEW: @mention Harry in a channel and he answers, no slash command needed",
                    "Works in channels enabled with /admin channels, when the ai_chat module is on",
                    "A bare @mention gets a greeting; one reply per person every 10 seconds",
                    "Users targeted by /fun target still get their insults instead"
                ]
            },
            {
                "category": "Trolling",
                "emoji": "🎯",
                "changes": [
                    "FIX: /fun target now only trolls in the channel it was run in (threads count as their parent)",
                    "NEW: everywhere:true on /fun target and /fun target_all keeps the old server-wide behavior",
                    "Channels blocked with /admin block are never trolled",
                    "/fun status shows where each target is being trolled"
                ]
            },
            {
                "category": "Under the Hood",
                "emoji": "🧹",
                "changes": [
                    "FIX: /admin cache clear now clears the recruiting and HS stats caches too",
                    "Admin and module checks are decorators, so a command can't skip one",
                    "Deleted an unused retry module and unused week fields",
                    "Split the two longest functions (378 and 277 lines) into named sections"
                ]
            }
        ]
    },
    "3.16.2": {
        "date": "2026-10-02",
        "title": "Quieter Logs, Shorter Changelog 🧹",
        "emoji": "🧹",
        "features": [
            {
                "category": "Fixes",
                "emoji": "🔧",
                "changes": [
                    "FIX: /changelog sorted versions alphabetically, so 3.9.0 listed above 3.16.x and the newest releases could be cut off"
                ]
            },
            {
                "category": "Cleanup",
                "emoji": "🧹",
                "changes": [
                    "Log messages are plain text — emoji stay in Discord embeds, out of the logs (647 lines)",
                    "The bot keeps the last 10 releases; the full history (68 releases) lives in docs/CHANGELOG.md",
                    "docs/CHANGELOG.md was stuck at v1.16.2 — now complete and checked by a test"
                ]
            }
        ]
    },
    "3.16.1": {
        "date": "2026-10-02",
        "title": "Lint & Tidy 🧽",
        "emoji": "🧽",
        "features": [
            {
                "category": "Under the Hood",
                "emoji": "🧽",
                "changes": [
                    "Startup opens the owner DM once instead of ~10 times",
                    "Recruiting lookups no longer extract and discard a full page of text",
                    "Startup status shows the real version even if the version manager fails to load",
                    "Removed ~100 unused imports, variables, empty f-strings and comments that restated the code"
                ]
            }
        ]
    },
    "3.16.0": {
        "date": "2026-10-02",
        "title": "Harry Knows It's CFB 27 🏈",
        "emoji": "🏈",
        "features": [
            {
                "category": "League",
                "emoji": "🏈",
                "changes": [
                    "Harry's personality, AI prompts, titles and footers now say CFB 27",
                    "The game name lives in one setting (GAME_NAME) — next year is an env change, not a code change",
                    "A test fails if anyone hardcodes a game year again"
                ]
            },
            {
                "category": "Cleanup",
                "emoji": "🧹",
                "changes": [
                    "Logger names are version-free (CFBBot.*) so they never go stale",
                    "Removed the unused rules-updater script and the Google Docs setup guide for the deleted integration"
                ]
            }
        ]
    },
    "3.15.2": {
        "date": "2026-10-02",
        "title": "Loose Ends 🧹",
        "emoji": "🧹",
        "features": [
            {
                "category": "Cleanup",
                "emoji": "🧹",
                "changes": [
                    "Advance and dev channels can be set with TIMER_CHANNEL_ID / DEV_CHANNEL_ID",
                    "Removed the Supabase storage stub — the docs walked people through setting it up, but it never worked",
                    "Removed the unused performance-metrics module, data/penalties.json, and leftover Sentry docs",
                    "Schedule season now matches the league (Season 4)"
                ]
            }
        ]
    },
    "3.15.1": {
        "date": "2026-10-02",
        "title": "Settings Save Guard 💾",
        "emoji": "💾",
        "features": [
            {
                "category": "Reliability",
                "emoji": "💾",
                "changes": [
                    "Settings too big for one Discord message are no longer sent and lost — Harry DMs the owner instead",
                    "Any failed settings save now DMs the owner (it used to be a log line nobody saw)",
                    "18 new tests cover the @everyone advanced flow end to end"
                ]
            }
        ]
    },
    "3.15.0": {
        "date": "2026-10-02",
        "title": "Side League Timers ⏱️",
        "emoji": "⏱️",
        "features": [
            {
                "category": "Advance Timer",
                "emoji": "⏰",
                "changes": [
                    "CHANGE: The countdown running out no longer advances the week — it just nags",
                    "The week moves only when you post '@everyone advanced'",
                    "TIME'S UP now says which week you're still on"
                ]
            },
            {
                "category": "Side Leagues",
                "emoji": "🎮",
                "changes": [
                    "NEW: /league side_timer league:Madden hours:24 — named countdown for another league",
                    "NEW: /league side_timer_stop league:Madden",
                    "Side timers announce in their own channel and never touch the dynasty week",
                    "They survive redeploys and show in /league timer_status and /league timers",
                    "/league nag and stop_nag merged into /league nag action:start|stop (Discord caps a group at 25 commands)"
                ]
            },
            {
                "category": "Polish",
                "emoji": "🧼",
                "changes": [
                    "/league week now shows what the step is for (portal opens, signing day, etc.)",
                    "FIX: /league timer no longer claims it replaced side-league timers it leaves running",
                    "Dropped another ~120 lines of unreferenced helpers"
                ]
            }
        ]
    },
    "3.14.1": {
        "date": "2026-10-02",
        "title": "Timer No Longer Eats a Week ⏰",
        "emoji": "⏰",
        "features": [
            {
                "category": "Advance Timer",
                "emoji": "⏰",
                "changes": [
                    "FIX: /league timer never advances the week — it only sets the countdown",
                    "The week moves on '@everyone advanced' or when the countdown runs out",
                    "The reply now names the week (unchanged) and any timer it replaced",
                    "The countdown embed posts in the advance channel, wherever you run the command"
                ]
            }
        ]
    },
    "3.14.0": {
        "date": "2026-09-19",
        "title": "Code Scrub & Charter Persistence 🧹",
        "emoji": "🧹",
        "features": [
            {
                "category": "Fixes",
                "emoji": "🔧",
                "changes": [
                    "FIX: Charter edits survive redeploys — the Discord copy is now restored to disk at startup",
                    "FIX: /league nag and /league stop_nag actually nag (the command claimed success and did nothing)",
                    "Both advance paths share one matchups embed builder, so they can't drift apart"
                ]
            },
            {
                "category": "Cleanup",
                "emoji": "🧹",
                "changes": [
                    "Removed ~1,000 lines of unreferenced code (dead charter AI-update pipeline, unused query parsers, orphan helpers)",
                    "Removed the broken Google Docs integration — /charter import replaces it",
                    "Dropped 7 unused dependencies (google-api x3, sentry-sdk, openai, anthropic, requests, playwright-stealth)"
                ]
            },
            {
                "category": "Error Reports",
                "emoji": "📩",
                "changes": [
                    "NEW: Harry DMs the bot owner when a command or event errors out",
                    "Repeats collapse into one DM per 15 min, capped at 12 DMs/hour",
                    "Keys and tokens are redacted from tracebacks before sending",
                    "AI budget alerts now DM the owner too (they only logged before)",
                    "Removed the unused Sentry integration in favour of this"
                ]
            },
            {
                "category": "Simplification",
                "emoji": "🧼",
                "changes": [
                    "One owner-DM helper instead of four copies",
                    "One save/load pair for season/week, settings and staff state (-144 lines)",
                    "Deleted three stale docs that still described the pre-cog layout"
                ]
            }
        ]
    },
    "3.13.0": {
        "date": "2026-09-19",
        "title": "Full Schedule View & Live Charter 📜",
        "emoji": "📜",
        "features": [
            {
                "category": "Schedule",
                "emoji": "📅",
                "changes": [
                    "NEW: /league schedule — the whole season at a glance",
                    "NEW: /league schedule team:<name> — one team's full season",
                    "Current week is marked in both views",
                    "FIX: Advance message now reads 'Week 0 → Week 1' (was showing the next week instead)",
                    "Matchup announcements now log why they were skipped"
                ]
            },
            {
                "category": "Charter",
                "emoji": "📜",
                "changes": [
                    "NEW: /charter import — pull the latest charter from the league Google Doc (admin)",
                    "Imports as markdown so headings and bullets survive, with plain text as backup",
                    "Charter refreshed to the current CFB 27 version",
                    "Charter link is configurable with the CHARTER_URL env var"
                ]
            }
        ]
    },
    "3.12.0": {
        "date": "2026-09-16",
        "title": "Correct Dynasty Week Schedule 📅",
        "emoji": "📅",
        "features": [
            {
                "category": "Season/Week Fixes",
                "emoji": "📅",
                "changes": [
                    "FIX: Week table now matches the real 27-step CFB 26 dynasty season",
                    "Preseason (1), Regular Season Weeks 0-14 (2-16), Postseason (17-22), Offseason (23-27)",
                    "Postseason: Conference Championship, Bowl Weeks 1-4 (CFP QF/SF), National Championship",
                    "Offseason: Staff Moves, Transfer Portal Open/Close, National Signing Day, Training Results",
                    "/league set_week now takes the step number (1-27) shown in /league weeks",
                    "/league games, find_game, byes map the current step to the right schedule week (0-14)",
                    "Saved week from the old 26-stage table is migrated automatically on startup"
                ]
            },
            {
                "category": "Advance Timer",
                "emoji": "⏰",
                "changes": [
                    "FIX: Only one advance timer — /league timer always runs it in the advance channel",
                    "FIX: '@everyone advanced' and /league timer stop stray timers in other channels (no double advances)",
                    "'advanced' must be a whole word, posted directly in the advance channel (not threads)",
                    "/league timer_status and timer_stop work from any channel",
                    "FIX: A Discord reconnect no longer spins up a second timer (duplicate warnings / double advance)",
                    "FIX: '@everyone advanced' after TIME'S UP no longer advances the week a second time",
                    "FIX: Two people posting 'advanced' within 3 minutes only advance once",
                    "FIX: Short or restored timers no longer spam 24h/12h warnings that don't apply"
                ]
            },
            {
                "category": "Saved Settings",
                "emoji": "💾",
                "changes": [
                    "FIX: Saving the timer no longer deletes the saved timer channel (it was reverting to #general)",
                    "FIX: A stopped timer can't be resurrected from an older saved message on restart",
                    "Saved week/staff/channel/schedule data is found even when the owner DM has lots of messages"
                ]
            },
            {
                "category": "League Permissions",
                "emoji": "🔒",
                "changes": [
                    "FIX: Server Administrators can only run league admin commands in the league's home server",
                    "Bot admins (BOT_ADMIN_IDS) can still manage the league from anywhere",
                    "League admin commands now respect the League module being disabled on a server"
                ]
            }
        ]
    },
    "3.11.0": {
        "date": "2026-09-05",
        "title": "Upload Schedules from Discord 📤",
        "emoji": "📤",
        "features": [
            {
                "category": "Schedule Management",
                "emoji": "📅",
                "changes": [
                    "NEW: /league upload_schedule — upload a full schedule JSON file (admin)",
                    "NEW: /league set_week_games — set one week's games/byes by typing them (admin)",
                    "NEW: /league schedule_template — shows the expected JSON format",
                    "No more editing files in git — update the schedule live from Discord",
                    "Uploads persist as a Discord backup, surviving redeploys"
                ]
            },
            {
                "category": "Help & Docs",
                "emoji": "📖",
                "changes": [
                    "/help now lists the new schedule + timer management commands"
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
        """Versions newest first, compared numerically (3.16.1 is newer than 3.9.0)."""
        return sorted(self.changelog.keys(), key=version_key, reverse=True)

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

