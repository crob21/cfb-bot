# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the bot
```bash
python main.py
```

### Run tests
```bash
# Unit tests only (fast, no network)
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ -v --cov=src/cfb_bot --cov-report=term-missing

# Integration smoke tests (may fail without env vars)
pytest tests/integration/test_bot_startup.py -v
```

### Run the optional web dashboard
```bash
python run_dashboard.py
```

### Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium   # required for recruiting scraper
```

## Environment Setup

Copy `config/env.example` to `.env`. Only `DISCORD_BOT_TOKEN` is required. All others are optional:

- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` — enables `/harry`, `/ask`, `/summarize`
- `CFB_DATA_API_KEY` — enables `/cfb` commands (CollegeFootballData.com)
- `ZYTE_API_KEY` — enables recruiting scraping with Cloudflare bypass
- `BOT_ADMIN_IDS` — comma-separated Discord user IDs for bot admins
- `STORAGE_BACKEND` — `discord` (default) or `supabase`

## Architecture

### Entry point flow
`main.py` → `src/cfb_bot/__init__.py` → `src/cfb_bot/bot_main.py`

discord.py 2.x **Cog-based architecture**. All slash commands are grouped into cogs loaded at startup. Cog dependencies are injected via `set_dependencies()` in `on_ready` after all cogs load.

### Module system
Every command group maps to a `FeatureModule` enum in `utils/server_config.py`. Modules are toggled per-guild via `/admin config`. Defaults on: `core`, `ai_chat`, `cfb_data`, `fun_games`. Opt-in: `league`, `hs_stats`, `recruiting`.

Every cog command must call `check_module_enabled()` or `check_module_enabled_deferred()` from `services/checks.py` before executing.

### Storage
`StorageBackend` in `utils/storage.py` has two backends:
- **Discord DMs** (default): JSON stored as edited messages in a DM to the bot owner. Free, ~1900 chars per namespace, survives redeploys.
- **Supabase**: Set `STORAGE_BACKEND=supabase`. Currently a stub (`NotImplementedError`).

### Key singletons
- `server_config` (`utils/server_config.py`) — per-guild feature flags and settings
- `cfb_data` (`utils/cfb_data.py`) — CollegeFootballData.com API wrapper
- `on3_scraper` / `recruiting_scraper` (`utils/`) — web scrapers for On3/Rivals and 247Sports
- `get_cache()` (`utils/cache.py`) — in-memory TTL cache for expensive results

## Key Patterns and Conventions

**Cog dependency injection**: Cogs declare dependencies as `None` in `__init__`, receive them in `set_dependencies()`. Never import dependencies at module load time inside cogs — use `set_dependencies` to avoid circular imports.

**Deferred vs. immediate responses**: For commands making HTTP calls, always `await interaction.response.defer()` first, then `interaction.followup.send()`. Use `check_module_enabled_deferred()` (not `check_module_enabled`) in these cases.

**Timer advancement via @everyone**: The bot listens for `@everyone` + the word "advanced" in `on_message`. This advances the dynasty week and restarts a 48-hour countdown. Hardcoded social convention for the league.

**Python 3.13 compatibility**: `utils/audioop_fix.py` must be imported before discord.py on Python 3.13+ (the `audioop` module was removed). Handled automatically via the import chain.

**Recruiting scraper fallback chain**: Playwright (headless Chromium) → cloudscraper → plain httpx. On Render, Playwright's Chromium must be installed separately.

**Version tracking**: Version is defined in both `src/cfb_bot/__init__.py` (`__version__`) and `utils/version_manager.py` (`CURRENT_VERSION`). Update both when bumping, and add a changelog entry in `version_manager.py`.

**Harry's personality**: Core prompt defined as `HARRY_PERSONALITY` in `utils/server_config.py`. `sanitize_ai_response()` in `security.py` redacts key/token-like strings from all AI output before Discord delivery.

**Embed consistency**: Use `Colors` and `Footers` constants from `config.py`. `EmbedBuilder` in `services/embeds.py` provides `success()`, `error()`, and `warning()` helpers.

**Tests**: Unit tests in `tests/unit/` never make real HTTP or Discord API calls. Integration tests in `tests/integration/` may require real env vars and run with `continue-on-error: true` in CI. Shared fixtures are in `tests/conftest.py`.

## Deployment

- **Render**: Use `config/render.yaml`. Start command: `python3 -u main.py`. Build command must include `playwright install chromium`.
- **Railway**: Start command `python main.py`. Set env vars in the dashboard.
- On startup, the bot sends a status embed to the hardcoded dev channel (`DEV_CHANNEL_ID = 1417732043936108564`).
