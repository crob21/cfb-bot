# CFB Bot (Harry) 🏈

A comprehensive Discord bot for College Football dynasty leagues. Player lookups, recruiting data, high school stats, AI-powered insights, league management, interactive charter editing—and Harry's signature cockney personality.

**Harry** – Your cockney, Oregon-hating assistant.

## Features

### 🏈 CFB Data (`/cfb`)
- **Player lookup** – `/cfb player`, bulk `/cfb players`
- **Rankings** – AP, Coaches, CFP polls
- **Matchup history** – `/cfb matchup` for rivalry records
- **Schedules** – `/cfb schedule`, results and upcoming games
- **Transfer portal** – `/cfb transfers`
- **Team stats** – `/cfb teamstats` for offense & defense
- **Ratings** – SP+, SRS, Elo via `/cfb ratings`
- **Draft** – `/cfb draft_picks` by school

### ⭐ Recruiting (`/recruiting`)
- **Player lookup** – On3/Rivals or 247Sports; position filter for duplicate names
- **Rankings** – Team recruiting classes
- **Commits** – `/recruiting commits` by team
- **Portal** – Transfer portal cross-reference
- **Source** – Switch On3 vs 247 per server

### 🏫 High School Stats (`/hs`)
- **Player lookup** – `/hs stats` from MaxPreps
- **Bulk lookup** – `/hs bulk` for lists

### ⏰ League (`/league`)
- **Advance timer** – Countdown with 24h / 12h / 6h / 1h reminders
- **Schedule** – `/league games`, `/league find_game`, `/league byes`
- **Week** – Current season/week, full week list
- **Staff** – Owner, co-commish; `/league pick_commish` for AI suggestion
- **Charter** – Link and natural-language updates

### 🤖 AI (`/harry`, `/ask`, `/summarize`)
- **Harry** – League-aware Q&A
- **Summarize** – Channel recaps
- **Co-commish picker** – Analyzes chat for recommendations

### ⚙️ Admin (`/admin`)
- **Config** – Enable/disable modules per server
- **Channels** – Set admin channel, block/unblock AI
- **Admins** – Add/remove bot admins
- **Usage** – `/admin ai`, `/admin zyte` for API usage and costs
- **Cache** – Stats and clear recruiting cache
- **Budget** – Monthly limits and alerts
- **Sync** – Force slash-command sync

### 😄 Personality
- Cockney accent and snarky attitude
- Deep, unhinged hatred of Oregon 🦆💩
- Rivalry auto-responses (configurable per channel)

---

## Quick Start

### Prerequisites
- Python 3.11+ (3.13 recommended)
- [Discord Bot Token](https://discord.com/developers/applications)
- Optional: OpenAI or Anthropic key (AI), CollegeFootballData.com key (CFB data), Zyte key (recruiting scraping)

### Install & run

```bash
git clone https://github.com/crob21/cfb-bot.git
cd cfb-bot

pip install -r requirements.txt

cp config/env.example .env
# Edit .env with DISCORD_BOT_TOKEN and any optional keys

python main.py
```

## Configuration

### Environment variables

| Variable | Required | Description |
|--------|----------|-------------|
| `DISCORD_BOT_TOKEN` | Yes | Discord bot token |
| `OPENAI_API_KEY` | No | AI (Harry); or use `ANTHROPIC_API_KEY` |
| `CFB_DATA_API_KEY` | No | [CollegeFootballData.com](https://collegefootballdata.com/key) – player/stats/rankings |
| `ZYTE_API_KEY` | No | [Zyte](https://www.zyte.com/) – recruiting (Cloudflare bypass) |
| `ZYTE_DASHBOARD_API_KEY` | No | Zyte dashboard API key (for `/admin zyte` official stats) |
| `ZYTE_ORG_ID` | No | Zyte org ID from dashboard URL (`app.zyte.com/o/123456` → `123456`) |
| `ZYTE_SPEND_LIMIT` | No | Cap in USD (e.g. `20`); Zyte API calls stop when monthly spend reaches this (0 = no cap) |
| `BOT_ADMIN_IDS` | No | Comma-separated Discord user IDs for bot admins |
| `TIMER_CHANNEL_ID` | No | Default advance/timer channel until `/league timer_channel` is set |
| `DEV_CHANNEL_ID` | No | Channel for Harry's startup status post |

See `config/env.example` for the full list (charter URL, dashboard, budgets, etc.).

### Per-server and per-channel
- **Modules** – Use `/admin config` to enable/disable CFB Data, Recruiting, League, HS Stats, etc. per server.
- **Channels** – Harry is off by default; use `/admin set_channel` and channel enable/block as needed.

---

## Commands overview

| Group | Description |
|-------|-------------|
| `/cfb` | Player, rankings, schedule, matchup, transfers, teamstats, ratings, draft |
| `/recruiting` | Player, top, class, commits, rankings, portal, source |
| `/hs` | Stats, bulk |
| `/league` | Timer, timer_status, games, week, weeks, find_game, byes, staff, set_week, pick_commish, … |
| `/charter` | View, edit, link |
| `/harry` | Ask Harry (league context) |
| `/admin` | Config, set_channel, add/remove admins, ai, zyte, cache, budget, sync, … |

**Full command reference:** [docs/COMMANDS.md](docs/COMMANDS.md)

---

## Project structure

```
cfb-bot/
├── main.py                 # Entry point (calls cfb_bot.main)
├── src/cfb_bot/
│   ├── bot_main.py         # Cog-based bot; loads all cogs
│   ├── cogs/               # Slash command modules
│   │   ├── core.py         # /help, /version, /changelog, /whats_new, /tokens
│   │   ├── ai_chat.py      # /harry, /ask, /summarize
│   │   ├── cfb_data.py     # /cfb
│   │   ├── recruiting.py   # /recruiting
│   │   ├── hs_stats.py     # /hs
│   │   ├── league.py       # /league
│   │   ├── charter.py      # /charter
│   │   ├── admin.py        # /admin
│   │   └── fun.py          # /fun (admin-only)
│   ├── ai/                 # AI integration (OpenAI, Anthropic)
│   ├── utils/              # Storage, config, timekeeper, cache, cfb_data, scrapers
│   └── services/           # Checks, embeds
├── src/dashboard/          # Optional web dashboard (FastAPI)
├── config/
│   ├── env.example
│   └── render.yaml         # Render deployment config
├── data/                   # Charter, schedule, rules (optional local data)
├── tests/
└── docs/                   # COMMANDS.md, CHANGELOG, setup guides
```

---

## Deployment

### Render
- Connect the repo and create a **Worker** (or use `config/render.yaml`).
- **Start command:** `python3 -u main.py` (unbuffered so logs stream; see `config/render.yaml`).
- Set env vars in the Render dashboard (no secrets in repo).

### Railway / other
- Start: `python main.py` (or `python3 -u main.py` for unbuffered logs).
- Set `DISCORD_BOT_TOKEN` and any optional keys.

---

## Development

```bash
# Run unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ -v --cov=src/cfb_bot --cov-report=term-missing

# Run bot locally
python main.py

# Dashboard (optional)
python run_dashboard.py
```

---

## Storage

Config and state live as messages in the bot owner's DMs — free, and they survive redeploys. Each namespace is one Discord message (2,000 characters); if one outgrows that, Harry DMs the owner instead of silently losing the change.

---

## Docs

- [Full command reference](docs/COMMANDS.md)
- [Changelog](docs/CHANGELOG.md)
- [Setup & contributing](docs/SETUP.md)

---

## License

MIT – see [LICENSE](LICENSE).

---

*Made with 🏈 for dynasty leagues. Don’t mention the bloody Ducks. 🦆💩*
