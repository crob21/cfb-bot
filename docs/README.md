# 📚 CFB Bot (Harry) Documentation

> **Harry** - Your cockney, Oregon-hating CFB assistant

[![Version](https://img.shields.io/badge/Version-3.7.0-blue.svg)](../src/cfb_bot/utils/version_manager.py)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Discord.py](https://img.shields.io/badge/Discord.py-2.3+-purple.svg)](https://discordpy.readthedocs.io)

## 📖 Documentation Index

### Getting Started
- **[SETUP.md](SETUP.md)** - Complete setup guide from scratch
- **[AI_SETUP.md](AI_SETUP.md)** - AI integration setup (OpenAI/Anthropic)
- **[GOOGLE_DOCS_SETUP.md](GOOGLE_DOCS_SETUP.md)** - Google Docs integration

### Features
- **[NEW_FEATURES.md](NEW_FEATURES.md)** - Complete feature documentation
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and changes

### Development
- **[VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)** - How to update versions
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
- **[TIMER_PERSISTENCE_TESTING.md](TIMER_PERSISTENCE_TESTING.md)** - Testing guide

## ✨ Feature Overview

### 🏈 CFB Data Module
| Feature | Command | Description |
|---------|---------|-------------|
| Player Lookup | `/player` | Look up any CFB player |
| Bulk Lookup | `/players` | Look up multiple players |
| Rankings | `/rankings` | AP, Coaches, CFP polls |
| Matchup History | `/matchup` | All-time series records |
| Schedules | `/cfb_schedule` | Team schedules & results |
| NFL Draft | `/draft_picks` | Draft history by school |
| Transfer Portal | `/transfers` | Portal activity |
| Betting | `/betting` | Spreads and O/U |
| Ratings | `/team_ratings` | SP+, SRS, Elo |

### 🏫 HS Stats Module
| Feature | Command | Description |
|---------|---------|-------------|
| HS Player Lookup | `/hs_stats` | MaxPreps high school stats |
| HS Bulk Lookup | `/hs_stats_bulk` | Bulk HS player lookup |

### ⏰ League Management
| Feature | Command | Description |
|---------|---------|-------------|
| Advance Timer | `/advance` | Start countdown |
| Timer Status | `/time_status` | Check progress |
| Dynasty Week | `/week` | Current week info |
| Charter | `/charter` | Link to charter |
| Rule Scanning | `/scan_rules` | Find rule changes |
| League Staff | `/league_staff` | View commissioners |
| Co-Commish Picker | `/pick_commish` | AI recommendations |

### ⚙️ Configuration
| Feature | Command | Description |
|---------|---------|-------------|
| Server Config | `/config` | Module management |
| Channel Config | `/channel` | Per-channel settings |
| Bot Admins | `/add_bot_admin` | Admin management |
| Timer Channel | `/set_timer_channel` | Set notifications |

## 🏗️ Architecture

### Storage Backends

Harry uses a pluggable storage system:

```
┌─────────────────┐
│  ServerConfig   │
│  Manager        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Storage      │
│   Abstraction   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐  ┌────────┐
│Discord │  │Supabase│
│  DMs   │  │  (DB)  │
└────────┘  └────────┘
```

**Discord DM Storage** (Default)
- Free, no setup
- Good for <10 servers
- Set: `STORAGE_BACKEND=discord`

**Supabase Storage** (Scaling)
- Unlimited servers
- Proper backups
- Set: `STORAGE_BACKEND=supabase`

### Module System

```
┌──────────────────────────────────────┐
│               Core                    │
│  (Always On - Personality, AI, Mgmt) │
└──────────────────────────────────────┘
         │           │           │
         ▼           ▼           ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│  CFB Data  │ │   League   │ │  HS Stats  │
│  Default:  │ │  Default:  │ │  Default:  │
│     ON     │ │    OFF     │ │    OFF     │
└────────────┘ └────────────┘ └────────────┘
```

### Per-Channel Controls

```
Server
├── #general      → Harry ENABLED, Auto-responses ON
├── #recruiting   → Harry ENABLED, Auto-responses OFF
├── #random       → Harry DISABLED
└── #admin        → Harry ENABLED, Auto-responses OFF
```

## 🔐 Permissions

### Bot Admin Sources
1. **Discord Administrator** - Automatic access
2. **Bot Admin List** - Added via `/add_bot_admin`
3. **Hardcoded Admins** - Set in `BOT_ADMIN_IDS` env var

### Admin-Only Commands
- `/advance`, `/stop_countdown`
- `/set_season_week`, `/set_timer_channel`
- `/add_rule`, `/update_rule`, `/scan_rules`
- `/add_bot_admin`, `/remove_bot_admin`
- `/config enable/disable`, `/channel` management

## 🚀 Quick Start

```bash
# 1. Clone and install
git clone https://github.com/crob21/cfb-rules-bot.git
cd cfb-rules-bot
pip install -r requirements.txt

# 2. Configure
cp config/env.example .env
# Edit .env with your tokens

# 3. Run
python main.py
```

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/crob21/cfb-rules-bot/issues)
- **Docs**: This documentation folder
- **Code**: `src/cfb_bot/` directory

---

**Version:** 1.16.2  
**Last Updated:** January 10, 2026  
**Made with 🏈 for the CFB 26 League**
