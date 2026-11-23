#!/usr/bin/env python3
"""
The league's record book (data/history.md): newest season first, one season added at a time.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.utils.league_history import HEADER, add_season, clean_entry, read_history, season_section

BOOK = HEADER + """
## Season 5

**National Champion:** Duke

## 2025 Season

**National Champion:** South Carolina

### Job Changes

* wustyman - USF -> Ole Miss
"""


class TestSections:
    def test_finds_harrys_and_hand_written_headings(self):
        assert season_section(BOOK, 5) == "## Season 5\n\n**National Champion:** Duke"
        assert "wustyman" in season_section(BOOK, 2025)
        assert season_section(BOOK, 3) is None

    def test_season_1_doesnt_match_season_10(self):
        assert season_section("## Season 10\n\nx", 1) is None


class TestAddSeason:
    def test_newest_season_goes_first_under_the_intro(self):
        book = add_season(BOOK, 6, "## Season 6\n\n**National Champion:** Cal")
        assert book.startswith(HEADER.strip())
        assert book.index("## Season 6") < book.index("## Season 5") < book.index("## 2025 Season")

    def test_writing_a_season_again_replaces_it(self):
        book = add_season(BOOK, 5, "## Season 5\n\n**National Champion:** Syracuse")
        assert book.count("## Season 5") == 1 and "Syracuse" in book and "Duke" not in book
        assert "## 2025 Season" in book

    def test_an_empty_book_gets_the_intro(self):
        book = add_season("", 1, "## Season 1\n\nx")
        assert book.startswith("# League History") and "## Season 1" in book


class TestCleanEntry:
    def test_unwraps_a_code_fence(self):
        assert clean_entry("```markdown\n## Season 5\n\nx\n```", 5) == "## Season 5\n\nx"

    @pytest.mark.parametrize("text", [None, "", "Here you go: ## Season 5", "## Season 4\n\nx"])
    def test_rejects_anything_else(self, text):
        assert clean_entry(text, 5) is None


def test_the_repo_has_a_record_book_and_the_charter_points_to_it():
    assert "## 2025 Season" in read_history()
    with open("data/charter.md", encoding="utf-8") as f:
        charter = f.read()
    assert "League History**" not in charter and "data/history.md" in charter


def test_missing_file_is_empty():
    assert read_history("data/no_such_history.md") == ""


@pytest.mark.asyncio
async def test_harry_reads_the_record_book_with_the_charter():
    from cfb_bot.ai.ai_integration import AICharterAssistant
    with patch('cfb_bot.ai.ai_integration.get_storage'):
        context = await AICharterAssistant().get_charter_content()
    assert "League Roster" in context and "## 2025 Season" in context


@pytest.mark.asyncio
@pytest.mark.parametrize("season,expect", [(None, "## 2025 Season"), (2025, "South Carolina"), (3, None)])
async def test_history_command(mock_interaction, mock_server_config, season, expect):
    from cfb_bot.cogs.league import LeagueCog
    cog = LeagueCog(MagicMock())
    with patch('cfb_bot.cogs.league.server_config', mock_server_config):
        await LeagueCog.history.callback(cog, mock_interaction, season)
    sent = mock_interaction.response.send_message.call_args
    if expect is None:
        assert "Nothing for Season 3" in sent.args[0]
    else:
        assert expect in sent.kwargs['embed'].description
        assert "# League History" not in sent.kwargs['embed'].description
