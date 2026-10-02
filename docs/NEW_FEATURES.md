# Harry's Features 🏈

This document outlines all features of Harry, the CFB 27 League Bot.

**Current Version:** 3.7.0
**Last Updated:** January 22, 2026
**Status:** ✅ Production Ready

---

## 🔒 Version 3.7 - Security Hardening & Optimizations!

**NEW: Production-Ready Security + Cost Savings**

### 🛡️ Security Enhancements

- **API Retry Logic:** Exponential backoff (2^attempt seconds)
  - Automatic retry on rate limits (429)
  - Respects Retry-After headers
  - Configurable attempts and backoff
  - `@with_retry` decorator for any function

- **Input Validation:** 2000-character limits on all user inputs
  - `@validate_input_length()` decorator
  - Safe string sanitization
  - Prevents memory issues

- **CORS Protection:** Dashboard security hardened
  - Configurable allowed origins
  - Credentials and methods restricted
  - Set `CORS_ORIGINS` environment variable

### 💰 Cost Optimizations

- **Recruiting Rankings Cache:** 24-hour TTL
  - Instant responses for rankings
  - Significant scraping cost reduction
  - Cache key: `rankings_{source}_{year}_{top}`

- **Zyte Optimization:** Reduced API usage
  - User-agent rotation (4 different UAs)
  - Playwright priority (free)
  - Est. $3-5/mo additional savings

### 🔧 API Improvements

- `api_retry.py` utility module
- `fetch_with_retry()` helper function
- `fetch_with_rate_limit_handling()` for 429s
- All security issues from audit resolved

---

## 🚀 Version 3.6 - Performance & Monitoring!

**NEW: 3x Faster Performance + Optional Monitoring**

### ⚡ Performance Improvements

- **Parallel API Calls:** Player lookups now **3x faster** (15s → 5s)
  - Multi-year stats fetched simultaneously with `asyncio.gather()`
  - No more waiting for sequential API calls!

- **AI Response Caching:** **$15-20/mo savings** on AI costs
  - 1-hour cache for AI responses (40-60% hit rate)
  - Instant responses for repeated questions
  - Automatic cache expiry after 1 hour

### 📊 Monitoring (Optional)

- **Sentry Integration:** Real-time error tracking
  - Automatic exception capture with context
  - Performance transaction tracking
  - Release tracking and user identification
  - Set `SENTRY_DSN` in environment variables to enable

- **Performance Metrics:** Track command performance
  - Execution time for all commands
  - Cache hit/miss rates
  - Error rates per command
  - Automatic warnings for slow commands (>5s)
  - Use `@track_performance` decorator on commands

### 🔧 Technical Details

- `asyncio.gather()` for parallel requests
- MD5-based cache keys for AI responses
- Sentry SDK integration for error tracking
- Command-level performance instrumentation
- Metrics API for optimization insights

---

## 🌀 Version 2.5 - Transfer Portal Detection!

Commands are organized into **6 logical groups** for better discoverability!

### Command Groups

| Group | Description | Example |
|-------|-------------|---------|
| `/recruiting` | Recruits, rankings, commits | `/recruiting player Arch Manning` |
| `/cfb` | College football stats | `/cfb rankings` |
| `/hs` | High school stats | `/hs stats Gavin Day` |
| `/league` | **Staff, season, timer, dynasty** | `/league week`, `/league timer` |
| `/charter` | Rules lookup & editing | `/charter search transfers` |
| `/admin` | Config & bot admins | `/admin config view` |

### Quick Migration Guide

| Old Command | New Command |
|-------------|-------------|
| `/recruit name` | `/recruiting player name` |
| `/top_recruits` | `/recruiting top` |
| `/player name` | `/cfb player name` |
| `/rankings` | `/cfb rankings` |
| `/hs_stats name` | `/hs stats name` |
| `/week` | `/league week` |
| `/advance 48` | `/league timer 48` |
| `/time_status` | `/league timer_status` |
| `/config` | `/admin config` |

---

## 🏈 `/recruiting` - Recruiting Module

Look up recruit profiles with rankings, offers, predictions, visits, and photos!

> **Data Sources:** On3/Rivals (default) or 247Sports Composite. Switch with `/recruiting source`

### Commands

| Command | Description |
|---------|-------------|
| `/recruiting player <name> [year]` | Look up a recruit |
| `/recruiting portal <name> [team]` | 🆕 Transfer portal lookup (On3 + CFB stats!) |
| `/recruiting top [position] [state] [year]` | Top recruits list |
| `/recruiting class <team> [year]` | Team's recruiting class |
| `/recruiting commits <team> [year]` | List all committed recruits (shows 🌀 for transfers) |
| `/recruiting rankings [year] [top]` | Top 25 team rankings |
| `/recruiting source [on3\|247]` | Set data source |

### 🌀 Transfer Portal Detection (NEW in v2.5.0!)

Harry now automatically detects transfer portal players and shows their college history!

**In `/recruiting player`:**
```
🌀 Transfer Portal
• Previous School: SHSU
• College Experience: 2023-2025
• Entered Portal: 1/2/2026
• Portal Rating: 90.63
```

**In `/recruiting commits`:**
- 🌀 emoji marks transfer portal players (detected via H.S. year + TR rating)
- Example: `10. 🌀 4⭐ **Kolt Dieterich** (OT) 90.6 • Riesel`

### 🔄 Transfer Portal Lookup

Combined recruiting data AND college stats for transfer portal players:

```
/recruiting portal Hollywood Smothers
/recruiting portal name:Cam Ward team:Miami
```

**Shows:**
- 📊 On3 rating, rankings, predictions, offers
- 🏈 CFB career stats from previous school
- 🌀 Transfer Portal section with previous school, experience, entry date
- Cross-references nicknames (Hollywood Smothers ↔ Daylan Smothers)

**Also works with natural language:**
> `@Harry tell me about portal player Cam Ward`

### 🔍 Fuzzy Name Matching (NEW!)

Harry now handles typos and case variations:
- ✅ `JOHN SMITH` → `John Smith` (case insensitive)
- ✅ `Gavinn Day` → `Gavin Day` (first name typos)
- ✅ Falls back to last-name-only search

### Example Usage

```
/recruiting player Arch Manning
/recruiting portal Cam Ward
/recruiting top position:QB state:TX
/recruiting class Georgia 2026
/recruiting commits Washington 2026
```

### Recruit Profile Shows:
- Player photo (thumbnail in embed)
- ⭐ Star rating and composite rating
- 🏆 National, position, and state rankings
- 📏 Height, weight, hometown, high school
- ✅ Commitment status with signing date
- 🔮 Predictions (top 5 schools with percentages)
- 📋 Offers list (all schools that offered)
- ✈️ Visit history (official/unofficial with dates)
- 🔗 Link to full On3/Rivals profile

---

## 📊 `/cfb` - CFB Data Module

Access comprehensive college football data powered by CollegeFootballData.com API.

> **Note:** All CFB Data commands automatically default to the current season and week. No need to specify year/week unless you want historical data!

### Player Lookup

**Commands:**
- `/player <name> [team]` - Look up a single player
- `/players <list>` - Bulk lookup (up to 15 players)

Access comprehensive college football data powered by CollegeFootballData.com API.

### Commands

| Command | Description |
|---------|-------------|
| `/cfb player <name> [team]` | Look up a college player |
| `/cfb players <list>` | Bulk player lookup |
| `/cfb rankings [poll] [year] [week]` | AP/Coaches/CFP polls |
| `/cfb matchup <team1> <team2>` | Head-to-head history |
| `/cfb schedule <team> [year]` | Team's schedule |
| `/cfb draft [team] [year]` | NFL draft picks |
| `/cfb transfers <team> [year]` | Portal activity |
| `/cfb betting [team] [year] [week]` | Game lines |
| `/cfb ratings <team> [year]` | SP+/SRS/Elo ratings |

### Example Usage

```
/cfb player Jalen Milroe Alabama
/cfb rankings poll:AP
/cfb matchup Alabama Auburn
/cfb schedule Nebraska 2025
/cfb transfers USC
```

---

## 🏫 `/hs` - High School Stats Module

Look up high school football career stats from MaxPreps for recruiting research.

> **Note:** This module uses web scraping and is disabled by default. Enable with `/admin config enable hs_stats`

### Commands

| Command | Description |
|---------|-------------|
| `/hs stats <name> [state] [school]` | Look up a player |
| `/hs bulk <player_list>` | Bulk lookup |

### Example Usage

```
/hs stats Gavin Day NV
/hs stats "Arch Manning" Louisiana
```

**Natural Language:** `@Harry hs stats Gavin Day NV`

**Shows:**
- 🏈 **Player Info:** Name, school, location (city, state)
- 📍 **Position:** QB, WR, RB, DB, LB, etc.
- 📏 **Physical:** Height, weight, class year (Senior/Junior/etc.)
- 📊 **Career Stats:**
  - **Defense:** Solo tackles, total tackles, sacks, interceptions
  - **Rushing:** Carries, yards, avg, TDs, long run
  - **Passing:** Completions, attempts, yards, TDs, INTs
  - **Receiving:** Receptions, yards, avg, TDs
  - **All-Purpose:** Rush/Rec/KR/PR/IR yards, total
- 📅 **Season Breakdown:** Stats by grade level (Sr/Jr/So/Fr)
- 🔗 **Link:** Direct link to MaxPreps profile

**Example Output:**
```
🏈 Gavin Day
🏫 Faith Lutheran (Las Vegas, NV)
📍 DB • 6'3" • 190 lbs • Senior

Sr. 25-26 (14 GP)
  🔄 All Purpose: 165 Total | 165 IR

Jr. 24-25 (12 GP)
  🔄 All Purpose: 71 Total | 71 IR

📊 Career Totals
  🛡️ Defense: 210 Solo/283 TKL
```


---

## 📜 `/charter` - Charter Management

Interactive charter editing and rule scanning.

### Commands

| Command | Description |
|---------|-------------|
| `/charter lookup <rule>` | Look up a rule |
| `/charter search <term>` | Search the charter |
| `/charter link` | Get charter URL |
| `/charter history` | Recent changes |
| `/charter scan #channel [hours]` | Scan for rule votes |
| `/charter add <title> <content>` | Add new rule (Admin) |
| `/charter update <section> <content>` | Update rule (Admin) |
| `/charter sync` | Sync to Discord (Admin) |
| `/charter backups` | View backups (Admin) |
| `/charter restore <file>` | Restore backup (Admin) |

### Natural Language Updates

Talk to Harry naturally:
```
@Harry update the advance time to 10am EST
@Harry add a rule: no trading during playoffs
```

---

## 🏆 `/league` - League Management

Complete league management: staff, season, timer, and more!

### Staff Commands

| Command | Description |
|---------|-------------|
| `/league staff` | View owner & co-commish |
| `/league set_owner @user` | Set owner (Admin) |
| `/league set_commish @user` | Set co-commish (Admin) |
| `/league pick_commish [hours]` | AI picks commish! 👑 |

### Season Commands

| Command | Description |
|---------|-------------|
| `/league week` | Current season & week |
| `/league weeks` | Full 30-week schedule |
| `/league games [week]` | Week's matchups |
| `/league find_game <team> [week]` | Find team's opponent |
| `/league byes [week]` | Bye teams |
| `/league set_week <season> <week>` | Set week (Admin) |

### Timer Commands

| Command | Description |
|---------|-------------|
| `/league timer [hours]` | Start advance countdown (default 48h) |
| `/league timer_status` | Check countdown progress |
| `/league timer_stop` | Stop the countdown |
| `/league timer_channel #channel` | Set notification channel |
| `/league nag [interval]` | Spam owner to advance 😈 |
| `/league stop_nag` | Stop the chaos |

### Info Commands

| Command | Description |
|---------|-------------|
| `/league team <name>` | Team info |
| `/league rules <topic>` | Recruiting rules |
| `/league dynasty <topic>` | Dynasty rules |

### The Asshole Detector 🚨

Harry rates candidates on:
- **Activity Level** - How often they participate
- **Helpfulness** - Do they help others?
- **Leadership** - Natural leader vibes?
- **Asshole Score** - Are they a dick?
- **Drama Score** - Stir up trouble?
- **Vibes/Humor** - Fun to be around?
- **Reliability** - Follow through?
- **Knowledge** - Know the game?

Includes personalized roasts for each candidate!

---

## ⚙️ `/admin` - Configuration & Admin

### Commands

| Command | Description |
|---------|-------------|
| `/admin config [view\|enable\|disable] [module]` | Module settings |
| `/admin channels [action] [#channel]` | Channel permissions |
| `/admin set_channel #channel` | Set admin notifications channel |
| `/admin add @user` | Add a bot admin |
| `/admin remove @user` | Remove a bot admin |
| `/admin list` | View all bot admins |
| `/admin block #channel` | Block unprompted responses |
| `/admin unblock #channel` | Allow responses |
| `/admin blocked` | Show blocked channels |

### Per-Server Modules

| Module | Description | Default |
|--------|-------------|---------|
| **Core** | Harry's personality, AI chat | Always On |
| **CFB Data** | Player lookup, rankings, etc. | Enabled |
| **Recruiting** | Recruit lookup (On3/247Sports) | Enabled |
| **League** | Timer, charter, dynasty | Disabled |
| **HS Stats** | High school stats (MaxPreps) | Disabled |

### Per-Channel Controls

| Action | Description |
|--------|-------------|
| `enable` | Enable Harry in this channel |
| `disable` | Disable Harry in this channel |
| `disable_all` | Clear whitelist for server |
| `toggle_rivalry` | Toggle rivalry auto-responses |

**Important:** Harry is disabled by default! Use `/admin channels enable` to activate.

### Who Can Be Admin?

1. **Discord Administrator** - Automatic access
2. **Bot Admin List** - Added via command
3. **Hardcoded Admins** - Set in env vars

---

## 📦 Storage System

Harry uses a pluggable storage system for scalability.

### Discord DM Storage (Default)
- **Pros**: Free, no setup, survives deploys
- **Cons**: ~10-20 server limit
- **Config**: `STORAGE_BACKEND=discord` (default)

### Supabase Storage (Scaling)
- **Pros**: Unlimited servers, proper backups
- **Cons**: Requires setup
- **Config**: `STORAGE_BACKEND=supabase`

To switch backends, just change the env var and deploy!

---

## 😄 Harry's Personality

Harry's core personality is **always on**:

- 🎩 **Cockney Accent** - "Oi mate, let me tell ya..."
- 😈 **Snarky Asshole** - Roasts and sarcasm included
- 🦆 **Oregon Hater** - Deep, unhinged hatred of the Ducks

### What's Toggleable?

Only **auto-responses** (unprompted jump-ins) can be toggled:
- "Fuck Oregon!" when someone mentions Ducks
- 🦆 emoji reactions triggering responses
- Random Oregon jokes in timer messages

Use `/channel toggle_rivalry` to control these per-channel.

---

## 📊 Channel Summarization

AI-powered discussion summaries.

**Command:** `/summarize [hours] [focus]`

**Natural Language:** `@Harry what happened in the last 3 hours?`

**Features:**
- Main topics discussed
- Decisions and actions
- Key participants
- Notable moments
- Optional focus filter (e.g., "rules", "recruiting")

---

## 📨 Message Relay

Relay messages between users.

**Usage:** `@Harry tell @User to <message>`

**Examples:**
```
@Harry tell @wustyman to fuck off
@Harry tell @boozerob the game is ready
```

---

## Technical Details

### File Structure
```
src/cfb_bot/
├── bot.py                   # Main Discord bot
├── ai/
│   └── ai_integration.py    # OpenAI/Anthropic
└── utils/
    ├── storage.py           # Storage abstraction
    ├── server_config.py     # Per-server config
    ├── cfb_data.py          # CFB data (CFBD API)
    ├── recruiting_scraper.py # 247Sports scraper
    ├── on3_scraper.py       # On3/Rivals scraper
    ├── hs_stats_scraper.py  # High school stats (MaxPreps)
    ├── timekeeper.py        # Timer & weeks
    ├── charter_editor.py    # Charter management
    ├── summarizer.py        # Channel summaries
    └── version_manager.py   # Version tracking
```

### Dependencies
- `discord.py` - Discord API
- `cfbd` - CollegeFootballData.com API
- `openai` / `anthropic` - AI integration
- `fastapi` - Web dashboard
- `aiohttp` - Async HTTP

---

**Author:** Harry (with assistance from Craig's AI assistant, innit!)
**Version:** 1.18.0
**Last Updated:** January 11, 2026
