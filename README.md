# CFB Rules Bot 🏈

A Discord bot for College Football 26 Online Dynasty League that provides league rule information, AI-powered responses, player lookups, interactive charter management, and fun rivalry interactions.

**Current Version:** 3.7.0  
**Harry** - Your cockney, Oregon-hating assistant

## Features

### ⚡ Performance & Monitoring (NEW in 3.6)
- **3x Faster Player Lookups** - Parallel API calls reduce wait times (15s → 5s)
- **AI Response Caching** - 40-60% cache hit rate saves $15-20/mo
- **Optional Sentry Integration** - Real-time error tracking and performance monitoring
- **Command Metrics** - Track execution times, cache rates, and bottlenecks
- **Automatic Optimization** - Warns on slow commands, identifies performance issues

### 🏈 CFB Data Module
- **Player Lookup** - `/player` or bulk `/players` for recruiting info, stats, transfers
- **Rankings** - `/rankings` for AP, Coaches, CFP polls
- **Matchup History** - `/matchup` for all-time records between rivals
- **Team Schedules** - `/cfb_schedule` for game results and upcoming games
- **NFL Draft** - `/draft_picks` for draft history by school
- **Transfer Portal** - `/transfers` for incoming/outgoing transfers
- **Betting Lines** - `/betting` for spreads and over/unders (auto-detects current week/postseason)
- **Advanced Stats** - `/team_ratings` for SP+, SRS, Elo ratings

### 🏫 High School Stats Module (NEW)
- **HS Player Lookup** - `/hs_stats` for MaxPreps high school stats
- **Bulk HS Lookup** - `/hs_stats_bulk` for recruiting lists
- **Web Scraping** - Pulls directly from MaxPreps

### ⏰ League Management
- **Advance Timer** - Server-wide countdown with automatic reminders
- **Dynasty Week System** - Full 30-week season tracking
- **Charter Management** - Interactive updates via natural language
- **League Staff** - Track commissioner and co-commissioner
- **Schedule Integration** - Matchups, byes, user team highlighting

### 🤖 AI-Powered Features
- **Natural Language** - Ask Harry anything conversationally
- **Channel Summaries** - AI-powered discussion recaps
- **Co-Commish Picker** - Analyzes chat for recommendations (with asshole detector!)
- **Rule Scanning** - Scan voting channels for passed rules

### ⚙️ Configuration & Administration
- **Per-Server Config** - Enable/disable modules per Discord server
- **Per-Channel Controls** - Whitelist channels where Harry responds
- **Web Dashboard** - Visual management at `/dashboard`
- **Bot Admin System** - Separate admin permissions for bot features
- **Auto-Response Toggle** - Control Harry's unprompted jump-ins

### 😄 Personality
- Cockney accent (always on)
- Snarky asshole attitude (always on)
- Deep, unhinged hatred of Oregon Ducks 🦆💩 (always on)

## Quick Start

### Prerequisites

- Python 3.11+ (3.13 recommended)
- Discord Bot Token
- OpenAI API Key (optional, for AI features)
- CollegeFootballData.com API Key (optional, for CFB data)

### Installation

   ```bash
# Clone the repository
   git clone https://github.com/crob21/cfb-rules-bot.git
   cd cfb-rules-bot

# Install dependencies
   pip install -r requirements.txt

# Set up environment variables
   cp config/env.example .env
   # Edit .env with your API keys

# Run the bot
   python main.py
   ```

## Configuration

### Environment Variables

```env
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token_here

# Optional (for AI features)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional (for monitoring - Sentry error tracking)
SENTRY_DSN=your_sentry_dsn_here
ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1

# Optional (for CFB data)
CFB_DATA_API_KEY=your_cfb_data_api_key_here

# Storage Backend (discord or supabase)
STORAGE_BACKEND=discord

# For Supabase (when scaling beyond ~10 servers)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### Per-Server Configuration

Harry supports per-server feature toggling:

| Module | Description | Default |
|--------|-------------|---------|
| **Core** | Harry's personality, AI chat, bot management | Always On |
| **CFB Data** | Player lookup, rankings, schedules, etc. | Enabled |
| **League** | Timer, charter, rules, dynasty features | Disabled |
| **HS Stats** | High school stats from MaxPreps | Disabled |

Use `/config` to manage modules or the web dashboard at `/dashboard`.

### Per-Channel Configuration

Harry is **disabled by default** in all channels. Use `/channel` to manage:

```
/channel enable        - Enable Harry in current channel
/channel disable       - Disable Harry in current channel
/channel view          - See current channel status
/channel toggle_rivalry - Toggle rivalry auto-responses (jump-ins)
```

## Commands

### CFB Data
| Command | Description |
|---------|-------------|
| `/player <name> [team]` | Look up any CFB player |
| `/players <list>` | Bulk lookup (up to 15 players) |
| `/rankings [poll]` | Get AP, Coaches, or CFP rankings |
| `/matchup <team1> <team2>` | All-time series history |
| `/cfb_schedule <team> [year]` | Team schedule and results |
| `/draft_picks <team> [year]` | NFL draft picks by school |
| `/transfers <team>` | Transfer portal activity |
| `/betting <team1> <team2>` | Betting lines and odds |
| `/team_ratings <team>` | SP+, SRS, Elo ratings |

### League Management
| Command | Description |
|---------|-------------|
| `/advance [hours]` | Start countdown (default 48h) - Admin |
| `/time_status` | Check countdown progress |
| `/stop_countdown` | Stop the timer - Admin |
| `/week` | Show current dynasty week |
| `/set_season_week <s> <w>` | Set season/week - Admin |
| `/charter` | Link to league charter |
| `/scan_rules #channel` | Scan for rule changes - Admin |
| `/league_staff` | View owner/co-commish |
| `/pick_commish` | AI recommends new co-commish |

### Configuration
| Command | Description |
|---------|-------------|
| `/config [module]` | View/toggle server modules |
| `/channel <action>` | Manage per-channel settings |
| `/add_bot_admin @user` | Add a bot admin |
| `/list_bot_admins` | List current bot admins |
| `/set_timer_channel #ch` | Set notification channel |

### General
| Command | Description |
|---------|-------------|
| `/harry <question>` | Ask Harry (league context) |
| `/ask <question>` | Ask Harry (general) |
| `/help_cfb` | Show all commands |
| `/whats_new` | Latest features |
| `/version` | Current version |

## Storage Architecture

Harry uses a pluggable storage system:

### Discord DM Storage (Default)
- **Pros**: Free, no setup, survives deploys
- **Cons**: 2000 char limit (~10-20 servers max)
- **Best for**: Small deployments

### Supabase Storage (Scaling)
- **Pros**: Unlimited servers, proper backups, queryable
- **Cons**: Requires setup (free tier available)
- **Best for**: 10+ servers

To switch, set `STORAGE_BACKEND=supabase` and configure Supabase credentials.

## Project Structure

```
cfb-rules-bot/
├── main.py                     # Entry point
├── run_dashboard.py            # Dashboard server
├── src/cfb_bot/               
│   ├── bot.py                  # Main Discord bot
│   ├── ai/                     # AI integration
│   └── utils/
│       ├── storage.py          # Storage abstraction
│       ├── server_config.py    # Per-server config
│       ├── cfb_data.py         # CFB data lookups (CFBD API)
│       ├── hs_stats_scraper.py # High school stats (MaxPreps)
│       ├── timekeeper.py       # Timer & weeks
│       ├── charter_editor.py   # Charter management
│       └── version_manager.py  # Version tracking
├── src/dashboard/              # Web dashboard
│   ├── app.py                  # FastAPI app
│   ├── routes.py               # API routes
│   └── templates/              # HTML templates
├── config/
│   └── env.example             # Environment template
├── data/                       # Data files
└── docs/                       # Documentation
```

## Deployment

### Render (Recommended)

1. Connect GitHub repository to Render
2. Create Web Service with:
   - **Build**: `pip install -r requirements.txt`
   - **Start**: `python main.py`
3. Add environment variables
4. Deploy!

### Railway

1. Connect GitHub to Railway
2. Add environment variables
3. Deploy automatically

## Development

```bash
# Run tests
python -m pytest tests/

# Run locally
python main.py

# Run dashboard separately
python run_dashboard.py
```

## License

MIT License - see [LICENSE](LICENSE)

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md) for version history.

---

**Made with 🏈 for the CFB 26 League**

*Harry is always here to help - just don't mention those bloody Oregon Ducks! 🦆💩*
