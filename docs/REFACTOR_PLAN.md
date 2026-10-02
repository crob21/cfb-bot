# Bot Refactor Plan: OOP with Cogs

**Goal:** Transform 7,200-line `bot.py` into maintainable, modular codebase
**Estimated Time:** 2-3 hours
**Risk:** Medium (test thoroughly before deploying)

---

## Current State

```
bot.py (7,217 lines)
├── 106 commands/handlers
├── 6 event handlers (on_ready, on_message, etc.)
├── Global variables scattered throughout
├── Hard to test, maintain, or extend
└── Single point of failure
```

---

## Target Architecture

```
src/cfb_bot/
├── bot.py (~150 lines)              # Bot setup, cog loading
├── config.py (~50 lines)            # Constants, colors, footers
│
├── cogs/
│   ├── __init__.py                  # Cog exports
│   ├── core.py (~400 lines)         # Events, /help, /version, /whats_new
│   ├── recruiting.py (~500 lines)   # /recruiting group (6 commands)
│   ├── cfb_data.py (~600 lines)     # /cfb group (9 commands)
│   ├── hs_stats.py (~300 lines)     # /hs group (2 commands)
│   ├── league.py (~800 lines)       # /league group (19 commands)
│   ├── charter.py (~400 lines)      # /charter group (10 commands)
│   ├── admin.py (~700 lines)        # /admin group (14 commands)
│   └── ai_chat.py (~600 lines)      # /harry, /ask, /summarize, @mentions
│
├── services/
│   ├── __init__.py
│   ├── checks.py (~100 lines)       # Module/channel permission checks
│   └── embeds.py (~150 lines)       # Common embed builders
│
└── utils/                           # (existing - no changes needed)
    ├── server_config.py
    ├── on3_scraper.py
    ├── recruiting_scraper.py
    ├── hs_stats_scraper.py
    ├── timekeeper.py
    ├── charter_editor.py
    ├── version_manager.py
    └── ...
```

---

## Cog Breakdown

### 1. `cogs/core.py` - Core Bot Functionality
**Events:**
- `on_ready` - Startup, sync commands, send notifications
- `on_guild_join` / `on_guild_remove` - Guild tracking
- `on_command_error` - Error handling

**Commands:**
- `/help` - Dynamic help based on enabled modules
- `/version` - Current version
- `/changelog` - Version history
- `/whats_new` - Latest features
- `/tokens` - AI token stats

**Shared State:**
- Bot startup time
- Guild count tracking

---

### 2. `cogs/recruiting.py` - Recruiting Data
**Group:** `/recruiting`

**Commands:**
- `player` - Look up a recruit
- `top` - Top recruits by position/state
- `class` - Team recruiting class
- `commits` - Team's committed recruits
- `rankings` - Top 25 team rankings
- `source` - Switch On3/247 source

**Dependencies:**
- `on3_scraper.py`
- `recruiting_scraper.py`
- `server_config.py` (for source preference)

---

### 3. `cogs/cfb_data.py` - College Football Data
**Group:** `/cfb`

**Commands:**
- `player` / `players` - Player lookup
- `rankings` - AP/Coaches/CFP polls
- `schedule` - Team schedules
- `matchup` - Head-to-head history
- `transfers` - Portal activity
- `draft` - NFL draft picks
- `betting` - Game lines
- `ratings` - SP+/SRS/Elo
- `records` - Historical records

**Dependencies:**
- `cfb_data.py` utility

---

### 4. `cogs/hs_stats.py` - High School Stats
**Group:** `/hs`

**Commands:**
- `stats` - Single player lookup
- `bulk` - Multiple players

**Dependencies:**
- `hs_stats_scraper.py`

---

### 5. `cogs/league.py` - League Management
**Group:** `/league`

**Commands (19 total):**
- **Staff:** `staff`, `set_owner`, `set_commish`, `pick_commish`
- **Season:** `week`, `weeks`, `games`, `find_game`, `byes`, `set_week`
- **Timer:** `timer`, `timer_status`, `timer_stop`, `timer_channel`
- **Info:** `team`, `rules`, `dynasty`
- **Fun:** `nag`, `stop_nag`

**Dependencies:**
- `timekeeper.py`
- `schedule_manager.py`

---

### 6. `cogs/charter.py` - Charter Management
**Group:** `/charter`

**Commands:**
- `lookup` - Find a rule
- `link` - Charter URL
- `scan` - Scan channel for votes
- `sync` - Sync to Discord
- `history` - Recent changes
- `search` - Search charter text
- `add` - Add new rule
- `update` - Update existing rule
- `backups` - List backups
- `restore` - Restore from backup

**Dependencies:**
- `charter_editor.py`
- `google_docs.py` (if available)

---

### 7. `cogs/admin.py` - Bot Administration
**Group:** `/admin`

**Commands:**
- `config` - View/enable/disable modules
- `channels` - Manage channel permissions
- `set_channel` - Set admin channel
- `add` / `remove` - Manage bot admins
- `block` / `unblock` - Block channels
- `list` - List admins
- `sync` - Force command sync

**Dependencies:**
- `server_config.py`
- `admin_manager.py`

---

### 8. `cogs/ai_chat.py` - AI Conversations
**Standalone Commands:**
- `/harry` - CFB/league questions
- `/ask` - General AI questions
- `/summarize` - Channel summaries

**Event Handling:**
- `on_message` listener for @mentions
- Auto-responses (Fuck Oregon!, etc.)
- League-related question detection

**Dependencies:**
- `ai_assistant.py`
- `channel_summarizer.py`

---

## Shared Services

### `services/checks.py`
```python
async def check_module_enabled(interaction, module: FeatureModule) -> bool:
    """Check if module is enabled and channel is whitelisted"""
    ...

async def check_module_enabled_deferred(interaction, module: FeatureModule) -> bool:
    """Same but for deferred interactions"""
    ...

def is_admin(user, interaction) -> bool:
    """Check if user is bot admin"""
    ...
```

### `services/embeds.py`
```python
class EmbedBuilder:
    @staticmethod
    def success(title, description) -> discord.Embed: ...

    @staticmethod
    def error(title, description) -> discord.Embed: ...

    @staticmethod
    def warning(title, description) -> discord.Embed: ...
```

---

## Git Branching Strategy

**Do the refactor on a feature branch, NOT main!**

### Setup
```bash
# Start fresh from main
git checkout main
git pull origin main

# Create refactor branch
git checkout -b refactor/cogs-architecture

# Push branch to GitHub (backup + enables CI)
git push -u origin refactor/cogs-architecture
```

### During Refactor
```bash
# Commit frequently with clear messages
git add -A
git commit -m "Extract recruiting cog"

# Push to branch regularly (triggers CI tests)
git push
```

### When Complete
```bash
# Ensure all tests pass locally
pytest tests/ -v

# Push final changes
git push

# Create Pull Request on GitHub:
#   refactor/cogs-architecture → main

# Review the PR, check CI status
# Merge when green ✅
```

### If Something Breaks in Prod
```bash
# Revert is easy - just go back to main
git checkout main
git push origin main --force  # Only if needed

# Fix on branch, re-test, try again
```

---

## Migration Steps

### Phase 1: Setup (15 min)
1. Create `cogs/` and `services/` directories
2. Create `config.py` with Colors, Footers constants
3. Create `services/checks.py` with permission helpers
4. Create `services/embeds.py` with embed builders

### Phase 2: Extract Cogs (90 min)
Extract in this order (least dependencies first):

1. **hs_stats.py** (~15 min) - Simplest, 2 commands
2. **cfb_data.py** (~15 min) - Self-contained
3. **recruiting.py** (~15 min) - Self-contained
4. **charter.py** (~15 min) - Moderate complexity
5. **league.py** (~15 min) - Many commands but straightforward
6. **admin.py** (~15 min) - Config management
7. **ai_chat.py** (~20 min) - Most complex (on_message logic)
8. **core.py** (~15 min) - Events and remaining commands

### Phase 3: Update bot.py (15 min)
```python
# bot.py - Final form
import discord
from discord.ext import commands

from .config import TOKEN
from .cogs import (
    CoreCog, RecruitingCog, CFBDataCog, HSStatsCog,
    LeagueCog, CharterCog, AdminCog, AIChatCog
)

bot = commands.Bot(...)

async def main():
    await bot.add_cog(CoreCog(bot))
    await bot.add_cog(RecruitingCog(bot))
    # ... etc
    await bot.start(TOKEN)
```

### Phase 4: Test (30 min)
1. Test each cog in isolation
2. Test module enable/disable
3. Test channel permissions
4. Test error handling
5. Full integration test

---

## Cog Template

```python
# cogs/example.py
import discord
from discord import app_commands
from discord.ext import commands
import logging

from ..services.checks import check_module_enabled
from ..utils.server_config import FeatureModule

logger = logging.getLogger('CFBBot.Example')


class ExampleCog(commands.Cog):
    """Description of what this cog does"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Define command group
    example_group = app_commands.Group(
        name="example",
        description="Example commands"
    )

    @example_group.command(name="test")
    async def test_command(self, interaction: discord.Interaction):
        """Test command description"""
        if not await check_module_enabled(interaction, FeatureModule.EXAMPLE):
            return

        await interaction.response.send_message("Hello!")

    # Event listeners
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle messages if needed"""
        pass


async def setup(bot: commands.Bot):
    """Required setup function for loading cog"""
    await bot.add_cog(ExampleCog(bot))
```

---

## Rollback Plan

If something breaks:
1. Git revert to pre-refactor commit
2. Redeploy old `bot.py`
3. Debug in development

Keep the old `bot.py` as `bot_legacy.py` until confirmed working.

---

## Post-Refactor Benefits

- ✅ Each file < 800 lines
- ✅ Clear separation of concerns
- ✅ Easy to add new features
- ✅ Testable in isolation
- ✅ Multiple contributors can work simultaneously
- ✅ Hot-reload individual cogs (future)
- ✅ Better error isolation

---

## Testing Strategy

### Directory Structure
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures (mock bot, interactions)
├── test_services/
│   ├── test_checks.py       # Permission check tests
│   └── test_embeds.py       # Embed builder tests
├── test_cogs/
│   ├── test_recruiting.py
│   ├── test_cfb_data.py
│   ├── test_hs_stats.py
│   ├── test_league.py
│   ├── test_charter.py
│   ├── test_admin.py
│   ├── test_ai_chat.py
│   └── test_core.py
├── test_utils/
│   ├── test_server_config.py
│   ├── test_on3_scraper.py
│   └── test_timekeeper.py
└── test_integration/
    └── test_full_flow.py    # End-to-end tests
```

### Testing Tools
```
# requirements-dev.txt
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
dpytest>=0.7.0              # Discord.py testing utilities
aioresponses>=0.7.0         # Mock HTTP requests
```

### Mock Fixtures (`conftest.py`)
```python
import pytest
import discord
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_bot():
    """Create a mock Discord bot"""
    bot = MagicMock(spec=discord.ext.commands.Bot)
    bot.user = MagicMock()
    bot.user.id = 123456789
    bot.guilds = []
    return bot

@pytest.fixture
def mock_interaction():
    """Create a mock Discord interaction"""
    interaction = AsyncMock(spec=discord.Interaction)
    interaction.guild = MagicMock()
    interaction.guild.id = 987654321
    interaction.channel = MagicMock()
    interaction.channel.id = 111222333
    interaction.user = MagicMock()
    interaction.user.id = 444555666
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

@pytest.fixture
def mock_server_config():
    """Mock server config with controllable modules"""
    config = MagicMock()
    config.get_enabled_modules.return_value = ['recruiting', 'cfb_data']
    config.is_module_enabled.return_value = True
    config.is_channel_enabled.return_value = True
    return config
```

### Test Categories

#### 1. Unit Tests - Services (~20 tests)
```python
# tests/test_services/test_checks.py
import pytest
from src.cfb_bot.services.checks import check_module_enabled
from src.cfb_bot.utils.server_config import FeatureModule

@pytest.mark.asyncio
async def test_module_enabled_returns_true(mock_interaction, mock_server_config):
    """Should return True when module is enabled"""
    mock_server_config.is_module_enabled.return_value = True
    result = await check_module_enabled(mock_interaction, FeatureModule.RECRUITING)
    assert result is True

@pytest.mark.asyncio
async def test_module_disabled_sends_message(mock_interaction, mock_server_config):
    """Should send ephemeral message when module disabled"""
    mock_server_config.is_module_enabled.return_value = False
    result = await check_module_enabled(mock_interaction, FeatureModule.RECRUITING)
    assert result is False
    mock_interaction.response.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_channel_not_whitelisted(mock_interaction, mock_server_config):
    """Should fail when channel not in whitelist"""
    mock_server_config.is_channel_enabled.return_value = False
    result = await check_module_enabled(mock_interaction, FeatureModule.RECRUITING)
    assert result is False
```

#### 2. Unit Tests - Cogs (~50 tests)
```python
# tests/test_cogs/test_recruiting.py
import pytest
from src.cfb_bot.cogs.recruiting import RecruitingCog

@pytest.mark.asyncio
async def test_player_command_success(mock_bot, mock_interaction):
    """Should return recruit data for valid name"""
    cog = RecruitingCog(mock_bot)
    # Mock scraper response
    cog.scraper.search_recruit = AsyncMock(return_value={
        'name': 'Arch Manning',
        'stars': 5,
        'rating': 99.5
    })

    await cog.player(mock_interaction, name="Arch Manning")

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert 'Arch Manning' in str(call_args)

@pytest.mark.asyncio
async def test_player_command_not_found(mock_bot, mock_interaction):
    """Should handle recruit not found gracefully"""
    cog = RecruitingCog(mock_bot)
    cog.scraper.search_recruit = AsyncMock(return_value=None)

    await cog.player(mock_interaction, name="Nonexistent Player")

    mock_interaction.followup.send.assert_called_once()
    call_args = mock_interaction.followup.send.call_args
    assert 'not found' in str(call_args).lower()

@pytest.mark.asyncio
async def test_player_module_disabled(mock_bot, mock_interaction, mock_server_config):
    """Should reject when recruiting module disabled"""
    mock_server_config.is_module_enabled.return_value = False
    cog = RecruitingCog(mock_bot)

    await cog.player(mock_interaction, name="Arch Manning")

    # Should NOT call scraper
    cog.scraper.search_recruit.assert_not_called()
```

#### 3. Unit Tests - Utils/Scrapers (~30 tests)
```python
# tests/test_utils/test_server_config.py
import pytest
from src.cfb_bot.utils.server_config import ServerConfig, FeatureModule

def test_default_modules_enabled():
    """New servers should have default modules enabled"""
    config = ServerConfig()
    guild_id = 123456789

    assert config.is_module_enabled(guild_id, FeatureModule.RECRUITING) is True
    assert config.is_module_enabled(guild_id, FeatureModule.CFB_DATA) is True
    assert config.is_module_enabled(guild_id, FeatureModule.CORE) is True

def test_disable_module():
    """Should be able to disable a module"""
    config = ServerConfig()
    guild_id = 123456789

    config.disable_module(guild_id, FeatureModule.LEAGUE)

    assert config.is_module_enabled(guild_id, FeatureModule.LEAGUE) is False

def test_enable_channel():
    """Should be able to enable a channel"""
    config = ServerConfig()
    guild_id = 123456789
    channel_id = 111222333

    config.enable_channel(guild_id, channel_id)

    assert config.is_channel_enabled(guild_id, channel_id) is True
```

#### 4. Integration Tests (~10 tests)
```python
# tests/test_integration/test_full_flow.py
import pytest

@pytest.mark.asyncio
async def test_recruit_search_end_to_end(mock_bot, mock_interaction):
    """Full flow: user searches recruit -> gets formatted response"""
    # 1. Load cog
    from src.cfb_bot.cogs.recruiting import RecruitingCog
    cog = RecruitingCog(mock_bot)

    # 2. Simulate command (with real scraper, mocked network)
    with aioresponses() as mocked:
        mocked.get(
            'https://www.on3.com/db/search/player/',
            payload={'results': [{'name': 'Test Player'}]}
        )

        await cog.player(mock_interaction, name="Test Player")

    # 3. Verify response sent
    assert mock_interaction.followup.send.called

@pytest.mark.asyncio
async def test_module_toggle_affects_commands(mock_bot, mock_interaction):
    """Disabling module should block all its commands"""
    from src.cfb_bot.cogs.admin import AdminCog
    from src.cfb_bot.cogs.recruiting import RecruitingCog

    admin_cog = AdminCog(mock_bot)
    recruiting_cog = RecruitingCog(mock_bot)

    # Disable recruiting
    await admin_cog.config(mock_interaction, action="disable", module="recruiting")

    # Try recruiting command - should fail
    await recruiting_cog.player(mock_interaction, name="Test")

    # Should have sent "module disabled" message
    assert 'disabled' in str(mock_interaction.response.send_message.call_args).lower()
```

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/cfb_bot --cov-report=html

# Run specific test file
pytest tests/test_cogs/test_recruiting.py -v

# Run tests matching pattern
pytest tests/ -k "recruiting" -v

# Run only fast unit tests (skip integration)
pytest tests/ -m "not integration" -v
```

### Where Tests Run

**Two places - Local AND GitHub:**

#### 1. Local (Your Machine)
Run manually before committing:
```bash
# Quick test
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/cfb_bot --cov-report=html
open htmlcov/index.html  # View coverage report in browser
```

#### 2. GitHub Actions (Automatic CI/CD)
Runs automatically on every push/PR - **FREE for GitHub repos!**

**Setup (one-time):**
Create `.github/workflows/test.yml`:

```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [main, refactor/*]  # Run on main AND refactor branches
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest tests/ -v --cov=src/cfb_bot

      - name: Check coverage
        run: coverage report --fail-under=70
```

**How it works:**
1. You push code to GitHub
2. GitHub spins up a fresh Ubuntu server
3. Installs Python + your dependencies
4. Runs `pytest`
5. Shows ✅ or ❌ on your commit/PR

**View results:**
- Go to your repo on GitHub
- Click "Actions" tab
- See all test runs with logs

#### Workflow Summary
```
You write code
    ↓
Run tests locally (quick check)
    ↓
git push
    ↓
GitHub Actions runs tests automatically
    ↓
✅ Green? Safe to merge!
❌ Red? Fix before merging!
```

### Test Coverage Goals

| Component | Target | Priority |
|-----------|--------|----------|
| `services/checks.py` | 100% | High |
| `services/embeds.py` | 100% | High |
| `utils/server_config.py` | 90% | High |
| `cogs/admin.py` | 80% | High |
| `cogs/recruiting.py` | 80% | Medium |
| `cogs/core.py` | 70% | Medium |
| `cogs/ai_chat.py` | 60% | Low (hard to mock AI) |

### Pre-Push Checklist
```bash
# Run before every push to prod
./scripts/pre_push.sh

# Contents of pre_push.sh:
#!/bin/bash
set -e

echo "🧪 Running tests..."
pytest tests/ -v --tb=short

echo "📊 Checking coverage..."
pytest tests/ --cov=src/cfb_bot --cov-fail-under=70

echo "🔍 Checking syntax..."
python -m py_compile src/cfb_bot/bot.py

echo "✅ All checks passed! Safe to push."
```

---

## Questions to Resolve Before Starting

1. **Keep backward compatibility?** - Command names stay the same ✓
2. **Database in future?** - Current Discord DM storage works fine
3. **Testing framework?** - pytest + pytest-asyncio ✓
4. **Type hints?** - Yes, add throughout
5. **CI/CD?** - GitHub Actions for automated testing ✓

---

*Plan created: January 11, 2026*
*Updated: Added comprehensive testing strategy*
*Ready to execute when you are! 🚀*
