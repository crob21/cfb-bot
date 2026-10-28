#!/usr/bin/env python3
"""
Which charter goes live at startup: the committed file or the Discord copy.

Restoring Discord unconditionally undid every merged charter PR (and the season 5
roster update) on the next restart.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.utils.charter_editor import BASE_MARKER, CharterEditor, charter_fingerprint

OLD = "# Charter\n\n* North Carolina\n* Minnesota\n"
NEW = "# Charter\n\n* Syracuse\n* Michigan State\n"
EDITED = NEW + "\n## New rule\nNo Ducks.\n"


class FakeDM:
    """Owner DM: newest message first, like discord.py's history()."""

    def __init__(self, bot_user):
        self.bot_user = bot_user
        self.messages = []
        self.files = []

    def history(self, limit=50):
        async def gen():
            for m in list(reversed(self.messages))[:limit]:
                yield m
        return gen()

    async def send(self, content="", file=None):
        msg = MagicMock()
        msg.author = self.bot_user
        msg.content = content
        msg.delete = AsyncMock(side_effect=lambda m=msg: self.messages.remove(m))
        self.messages.append(msg)
        if file:
            self.files.append(file.filename)
        return msg


def _editor(tmp_path, committed, dm):
    path = tmp_path / "charter.md"
    path.write_text(committed)
    bot = MagicMock(user=dm.bot_user)
    with patch('cfb_bot.config.CHARTER_FILE', str(path)), patch('cfb_bot.config.CHARTER_FILE_LEGACY', str(path)):
        editor = CharterEditor(bot=bot)
    editor.backup_dir = str(tmp_path)
    editor._get_bot_owner_dm = AsyncMock(return_value=dm)
    return editor, path


async def _discord_copy(dm, content, base):
    chunk = MagicMock(author=dm.bot_user, content="📜CHARTER_CHUNK_1of1📜\n" + content)
    chunk.delete = AsyncMock(side_effect=lambda m=chunk: dm.messages.remove(m))
    dm.messages.append(chunk)
    if base:
        await dm.send(f"{BASE_MARKER}{base}")


@pytest.mark.asyncio
async def test_merged_charter_beats_an_old_discord_copy(tmp_path):
    dm = FakeDM("harry")
    await _discord_copy(dm, OLD, base=None)  # saved before the marker existed
    editor, path = _editor(tmp_path, NEW, dm)

    await editor.restore_from_discord()

    assert path.read_text() == NEW
    assert dm.files == ["charter_replaced.md"]  # old copy handed to the owner
    assert await editor.load_from_discord() == NEW  # Discord now holds the repo copy


@pytest.mark.asyncio
async def test_discord_edits_survive_a_redeploy(tmp_path):
    dm = FakeDM("harry")
    await _discord_copy(dm, EDITED, base=charter_fingerprint(NEW))  # edited in Discord on top of NEW
    editor, path = _editor(tmp_path, NEW, dm)

    await editor.restore_from_discord()

    assert path.read_text() == EDITED
    assert dm.files == []


@pytest.mark.asyncio
async def test_newer_commit_beats_discord_edits_on_an_older_base(tmp_path):
    dm = FakeDM("harry")
    await _discord_copy(dm, OLD + "edit", base=charter_fingerprint(OLD))
    editor, path = _editor(tmp_path, NEW, dm)

    await editor.restore_from_discord()

    assert path.read_text() == NEW
    assert dm.files == ["charter_replaced.md"]


@pytest.mark.asyncio
async def test_sync_saves_the_current_file(tmp_path):
    """/charter sync called save_to_discord() with no content and always crashed."""
    dm = FakeDM("harry")
    editor, _ = _editor(tmp_path, NEW, dm)
    assert await editor.save_to_discord()
    assert await editor.load_from_discord() == NEW
    assert editor._discord_base == charter_fingerprint(NEW)
