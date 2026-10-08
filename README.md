# Harry 🏈

[![Tests](https://github.com/crob21/cfb-bot/actions/workflows/test.yml/badge.svg)](https://github.com/crob21/cfb-bot/actions/workflows/test.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![discord.py 2.x](https://img.shields.io/badge/discord.py-2.x-5865F2.svg)](https://discordpy.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**A Discord bot for College Football dynasty leagues, with a cockney bastard bolted on front.**

Harry runs your advance timer, knows your schedule, looks up recruits, reads your charter, and insults anyone who deserves it. He hates the Oregon Ducks with his whole chest.

```
BoozeRob (ASU) — 1:57 PM
   @Harry why are you wearing corn gear?

Harry 🤖 — 1:58 PM
   The league's got bugger all to say about corn gear, so rock the maize
   if it tickles yer fancy, mate. But if anyone shows up in Oregon duck
   tat, I'll lose my bloody mind — toss the feathers, ya muppet.
```

**87 slash commands across 7 command groups.** Turn on what your league needs, leave the rest off.

---

## Why Harry

**He knows your league, not just football.** Upload your schedule and he answers from it — who you play, who's on bye, what week it is. Point him at your charter and he'll quote the rules at people instead of making them up.

**He keeps the league moving.** A 48-hour advance timer with escalating reminders, and when the commissioner posts `@everyone advanced`, Harry advances the week and restarts the clock. No one has to remember anything.

**He's cheap to run.** Free hosting tier, free storage (config lives in the bot owner's DMs), and AI costs fractions of a cent per question with a monthly budget and alerts.

**He has a personality problem.** This is a feature. `/fun target` sics him on a league-mate until you call him off.

---

## Features

### 🏈 CFB Data (`/cfb`)
Real data from [CollegeFootballData.com](https://collegefootballdata.com/) — player lookups (single or bulk), AP/Coaches/CFP rankings, rivalry matchup history, team schedules and results, transfer portal, offense/defense team stats, SP+/SRS/Elo ratings, and NFL draft picks by school.

### ⭐ Recruiting (`/recruiting`)
On3/Rivals **or** 247Sports Composite, switchable per server. Recruit lookups with position filters for duplicate names, team recruiting classes, commit lists, team rankings, and transfer portal cross-reference. Cloudflare-blocked pages fall back through Playwright → cloudscraper → plain HTTP.

### 🏫 High School Stats (`/hs`)
MaxPreps stats for a player, or a whole list at once with `/hs bulk`.

### ⏰ League (`/league`)
- **Advance timer** — countdown with 24h / 12h / 6h / 1h warnings. Post `@everyone advanced` in the timer channel and Harry advances the week and restarts the clock.
- **Schedule** — `/league games`, `find_game`, `byes`. Upload a season with `/league upload_schedule`, or type one week with `/league set_week_games`. Your teams are **bolded** everywhere they appear.
- **Week tracking** — the real 27-step dynasty calendar, not a guess.
- **Staff** — owner and co-commish, including `/league pick_commish`, where Harry reads the chat and nominates someone.

### 🤖 AI (`/harry`, `/ask`, `/summarize`)
Ask Harry anything — or just **@mention him**, no slash command needed. He answers with your charter and current week in context. `/summarize` catches you up on a channel you ignored for a week. Works with OpenAI or Anthropic; models are a config setting, not a code change.

### 📜 Charter (`/charter`)
The charter lives in the repo as [`data/charter.md`](data/charter.md). Link it, search it, edit it in natural language, and keep version history with backups and restore.

**Harry can propose rule changes, but never land them.** `/charter propose` has him redraft the charter against your instruction — using the league's *current* teams and week, so stale details get corrected — then open a **pull request** you review and merge. Two gates: only Discord IDs in `CHARTER_EDITOR_IDS` may propose, and there is no merge call anywhere in that code path.

### ⚙️ Admin (`/admin`)
Per-server module toggles, channel whitelisting, bot admins, API usage and cost tracking, cache control, monthly budget alerts, and command sync.

### 😄 Fun (`/fun`)
`/fun target` picks a victim and Harry trolls them in that channel — add `everywhere:true` to make it server-wide. Engage mode lets him argue back when they bite. Rivalry auto-responses fire on team keywords, because someone has to say it when a Duck is mentioned.

---

## The dynasty calendar

Harry tracks all 27 advances of a season, so "what week is it?" always has a real answer:

| Steps | Phase | |
|---|---|---|
| 1 | Preseason | |
| 2–16 | Regular Season | Week 0 through Week 14 |
| 17–22 | Postseason | Conference Championship, Bowl Weeks 1–4 (CFP QF/SF), National Championship |
| 23–27 | Offseason | Staff Moves, Transfer Portal (open/close), National Signing Day, Training Results |

Advancing past Training Results rolls over to Preseason of the next season.

---

## Quick start

**You need:** Python 3.11+ (3.13 recommended) and a [Discord bot token](https://discord.com/developers/applications).

```bash
git clone https://github.com/crob21/cfb-bot.git
cd cfb-bot

pip install -r requirements.txt
playwright install chromium          # only if you want recruiting scraping

cp config/env.example .env           # add DISCORD_BOT_TOKEN
python main.py
```

Then in Discord:

```
/admin set_channel        # where Harry is allowed to talk
/admin config             # turn on the modules you want
/league timer_channel     # where advance timers live
/league upload_schedule   # attach your season JSON
```

Harry is **off by default in every channel** — he only speaks where you let him.

---

## Configuration

Only the bot token is required. Everything else unlocks a feature.

| Variable | Required | What it does |
|---|---|---|
| `DISCORD_BOT_TOKEN` | **Yes** | The bot token |
| `OPENAI_API_KEY` | No | AI features (`/harry`, `/ask`, @mentions, AI insults) |
| `ANTHROPIC_API_KEY` | No | AI fallback when OpenAI fails or runs dry |
| `CFB_DATA_API_KEY` | No | [CollegeFootballData.com](https://collegefootballdata.com/key) — all `/cfb` commands |
| `ZYTE_API_KEY` | No | [Zyte](https://www.zyte.com/) — recruiting scraping through Cloudflare |
| `BOT_ADMIN_IDS` | No | Comma-separated Discord user IDs for bot admins |
| `GAME_NAME` | No | The game your league plays (default `CFB 27`) |
| `CHARTER_EDITOR_IDS` | No | Discord IDs allowed to run `/charter propose` (empty = nobody) |
| `GITHUB_TOKEN` / `GITHUB_REPO` | No | Lets Harry open charter pull requests |
| `OPENAI_MODEL` | No | Default `gpt-5-mini` — swap models without touching code |
| `ANTHROPIC_MODEL` | No | Default `claude-haiku-4-5` |
| `AI_MONTHLY_BUDGET` | No | Spend before alerts fire (default `10`) |
| `TIMER_CHANNEL_ID` / `DEV_CHANNEL_ID` | No | Default advance channel and startup-status channel |

More in [`config/env.example`](config/env.example) — charter URL, Zyte dashboard stats, spend caps, cost estimates.

> **Leave a variable out entirely to use its default.** A variable that exists but is empty counts as set.

### Per-server, per-channel
Every command group maps to a module you toggle with `/admin config`. On by default: **core**, **ai_chat**, **cfb_data**, **fun_games**. Opt-in: **league**, **hs_stats**, **recruiting**. Channels are whitelisted with `/admin channels`, and `/admin block` stops unprompted chatter while leaving @mentions working.

---

## Commands

| Group | What's in it |
|---|---|
| `/cfb` | player, players, rankings, matchup, schedule, transfers, teamstats, ratings, betting, draft |
| `/recruiting` | player, top, class, commits, rankings, portal, source |
| `/hs` | stats, bulk |
| `/league` | timer, timer_status, timers, side_timer, games, schedule, week, weeks, find_game, byes, staff, set_week, upload_schedule, set_week_games, pick_commish, … |
| `/charter` | lookup, search, add, update, propose, history, backups, restore, link, scan, sync, import |
| `/harry`, `/ask`, `/summarize` | AI — or just @mention him |
| `/fun` | target, untarget, target_all, untarget_all, roast, status, timeout, toggle_engage |
| `/admin` | config, channels, set_channel, block/unblock, add/remove admins, ai, zyte, cache, budget, digest, sync |

**Full reference:** [docs/COMMANDS.md](docs/COMMANDS.md)

---

## How it's built

discord.py 2.x, cog-based. Each command group is a cog; dependencies are injected after startup. Commands declare their requirements as decorators (`@requires_admin`, `@requires_module`), so a command can't forget a permission check.

```
cfb-bot/
├── main.py                     # entry point
├── src/cfb_bot/
│   ├── bot_main.py             # bot setup, cog loading, @everyone advance handling
│   ├── cogs/                   # one per command group (core, ai_chat, cfb_data,
│   │                           #   recruiting, hs_stats, league, charter, admin, fun)
│   ├── ai/                     # OpenAI + Anthropic integration, prompt building
│   ├── utils/                  # timekeeper, schedule, storage, scrapers, cache, config
│   └── services/               # permission checks, embed builders
├── src/dashboard/              # optional FastAPI web dashboard
├── config/                     # env.example, render.yaml
├── data/                       # charter, schedule, rules
├── docs/                       # COMMANDS.md, CHANGELOG.md, SETUP.md
└── tests/                      # 235 unit tests + 17 startup integration tests
```

**Storage with no database:** config and state live as edited messages in the bot owner's DMs. Free, and it survives redeploys. Each namespace is one Discord message (2,000 chars); if one outgrows that, Harry DMs the owner rather than silently dropping the change.

---

## Development

```bash
pytest tests/unit/ -v                                      # fast, no network
pytest tests/unit/ --cov=src/cfb_bot --cov-report=term-missing
pytest tests/integration/test_bot_startup.py -v            # startup smoke tests

python main.py                                             # run the bot
python run_dashboard.py                                    # optional web dashboard
```

Unit tests never touch the network or Discord. CI runs them on every push and pull request.

---

## Deployment

**Render** — create a Worker, or use [`config/render.yaml`](config/render.yaml). Start command `python3 -u main.py` (unbuffered, so logs stream). Set env vars in the dashboard; nothing secret lives in the repo. Include `playwright install chromium` in the build if you want recruiting scraping.

**Railway or anywhere else** — start with `python main.py` and set `DISCORD_BOT_TOKEN`.

---

## Docs

- [Command reference](docs/COMMANDS.md) — every command, every option
- [Changelog](docs/CHANGELOG.md) — full release history (`/changelog` shows recent ones in Discord)
- [Setup & contributing](docs/SETUP.md)

## License

MIT — see [LICENSE](LICENSE).

---

*Made with 🏈 for dynasty leagues. Don't mention the bloody Ducks. 🦆💩*
