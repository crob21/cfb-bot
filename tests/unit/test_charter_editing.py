#!/usr/bin/env python3
"""
Charter search, add, update and restore.

/charter search called a search_charter method that didn't exist, so it always failed.
/charter add, update and restore wrote only the local file, so the next restart put the
old Discord copy back. Restore also took any path, so '../.env' became the charter.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from cfb_bot.utils.charter_editor import CharterEditor

CHARTER = """# **League Charter**

## **1. League Rules**

### Advances
Advances run on a 48 hour timer.

### Recruiting
No more than 3 five-star recruits per class.

## **5. League History**

### 2025 Season
**National Champion:** South Carolina
"""


@pytest.fixture
def editor(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "charter.md").write_text(CHARTER)
    e = CharterEditor(bot=MagicMock())
    e.save_to_discord = AsyncMock(return_value=True)
    return e


class TestSearch:
    def test_finds_text_with_its_section(self, editor):
        results = editor.search_charter("five-star")
        assert results[0]['section'] == "Recruiting"
        assert "five-star" in results[0]['excerpt']

    def test_matches_headings_case_insensitively(self, editor):
        assert editor.search_charter("league history")[0]['section'] == "5. League History"

    def test_nothing_found(self, editor):
        assert editor.search_charter("ducks") == []
        assert editor.search_charter("   ") == []


@pytest.mark.asyncio
async def test_added_rule_is_saved_to_discord(editor):
    result = await editor.add_rule_section("Ducks", "No Ducks, ever.")
    assert result['success']
    editor.save_to_discord.assert_awaited_once()
    assert "No Ducks, ever." in editor.read_charter()


@pytest.mark.asyncio
async def test_restore_is_saved_to_discord(editor, tmp_path):
    (tmp_path / "data" / "charter_backups" / "charter_backup_20260101_000000.txt").write_text("# Old charter\n")
    assert await editor.restore_backup("charter_backup_20260101_000000.txt")
    assert editor.read_charter() == "# Old charter\n"
    editor.save_to_discord.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["../charter.md", "../../.env", "/etc/passwd", "notes.txt"])
async def test_restore_only_takes_backup_names(editor, name):
    assert not await editor.restore_backup(name)
    assert editor.read_charter() == CHARTER
