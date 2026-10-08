#!/usr/bin/env python3
"""
Harry proposes charter changes; humans merge them.

Two gates: CHARTER_EDITOR_IDS says who may propose at all, and GITHUB_TOKEN/GITHUB_REPO
say whether PRs are possible. There is deliberately no merge call anywhere in this path.
"""

import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.utils import charter_git

GIT_SOURCE = pathlib.Path(charter_git.__file__).read_text()


class TestWhoMayPropose:
    def test_listed_editor_may_propose(self):
        with patch.object(charter_git, 'CHARTER_EDITOR_IDS', [111]):
            assert charter_git.may_propose_charter_change(111)

    def test_everyone_else_may_not(self):
        with patch.object(charter_git, 'CHARTER_EDITOR_IDS', [111]):
            assert not charter_git.may_propose_charter_change(222)

    def test_empty_list_means_nobody(self):
        """An unset CHARTER_EDITOR_IDS must not mean 'anyone'."""
        with patch.object(charter_git, 'CHARTER_EDITOR_IDS', []):
            assert not charter_git.may_propose_charter_change(111)
            assert not charter_git.may_propose_charter_change(0)


class TestConfiguration:
    def test_needs_both_token_and_repo(self):
        with patch.object(charter_git, 'GITHUB_TOKEN', 'tok'), patch.object(charter_git, 'GITHUB_REPO', ''):
            assert not charter_git.is_configured()
        with patch.object(charter_git, 'GITHUB_TOKEN', ''), patch.object(charter_git, 'GITHUB_REPO', 'o/r'):
            assert not charter_git.is_configured()
        with patch.object(charter_git, 'GITHUB_TOKEN', 'tok'), patch.object(charter_git, 'GITHUB_REPO', 'o/r'):
            assert charter_git.is_configured()

    @pytest.mark.asyncio
    async def test_unconfigured_open_is_refused(self):
        with patch.object(charter_git, 'GITHUB_TOKEN', ''):
            ok, message = await charter_git.CharterPullRequest().open("text", "summary", "me")
        assert not ok and "configured" in message


class TestBranchNames:
    def test_readable_and_namespaced(self):
        name = charter_git.branch_name("Fix advance cadence")
        assert name.startswith("charter/fix-advance-cadence-")

    def test_awkward_summaries_still_produce_a_valid_branch(self):
        assert charter_git.branch_name("!!! ???").startswith("charter/update-")
        assert " " not in charter_git.branch_name("a b c")


class TestHarryNeverMerges:
    def test_no_merge_call_exists(self):
        assert "/merge" not in GIT_SOURCE
        assert "'PUT', f\"/repos/{self.repo}/pulls" not in GIT_SOURCE

    @pytest.mark.asyncio
    async def test_open_creates_branch_commit_and_pr_only(self):
        pr = charter_git.CharterPullRequest(token='tok', repo='o/r', base='main')
        calls = []

        async def fake_request(self, session, method, path, **kwargs):
            calls.append((method, path.split('?')[0]))
            if path.endswith('/git/ref/heads/main'):
                return {'object': {'sha': 'basesha'}}
            if 'contents' in path and method == 'GET':
                return {'sha': 'filesha'}
            if method == 'POST' and path.endswith('/pulls'):
                return {'html_url': 'https://github.com/o/r/pull/7'}
            return {}

        with patch.object(charter_git.CharterPullRequest, '_request', fake_request), \
             patch('aiohttp.ClientSession', MagicMock()):
            ok, url = await pr.open("new charter", "Fix cadence", "BoozeRob (1)")

        assert ok and url == 'https://github.com/o/r/pull/7'
        methods = [m for m, _ in calls]
        assert methods.count('POST') == 2          # branch + pull request
        assert 'DELETE' not in methods
        assert not any('merge' in path for _, path in calls)


class TestGitHubBoundText:
    def test_at_signs_cannot_ping_github_users(self):
        assert charter_git.for_github_text("@crob21 broke it") == "crob21 broke it"

    def test_backticks_and_newlines_are_neutralised(self):
        assert charter_git.for_github_text("a`b`\nc") == "a'b' c"

    def test_long_text_is_trimmed(self):
        assert len(charter_git.for_github_text("x" * 500)) == 200


class TestProposeCommandGate:
    """The gate that matters is the one on the command, not just the helper."""

    @pytest.mark.asyncio
    async def test_non_editor_gets_refused_and_no_pr_is_attempted(self):
        from cfb_bot.cogs.charter import CharterCog

        cog = CharterCog(MagicMock())
        cog.charter_editor = MagicMock()
        interaction = MagicMock()
        interaction.user.id = 999
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        with patch.object(charter_git, 'CHARTER_EDITOR_IDS', [111]), \
             patch.object(charter_git.CharterPullRequest, 'open', AsyncMock()) as opened:
            await cog.propose.callback(cog, interaction, instruction="rewrite it", summary="nope")

        opened.assert_not_awaited()
        interaction.response.defer.assert_not_awaited()
        assert "charter editors" in interaction.response.send_message.await_args[0][0]

    @pytest.mark.asyncio
    async def test_editor_without_github_configured_is_told_so(self):
        from cfb_bot.cogs.charter import CharterCog

        cog = CharterCog(MagicMock())
        cog.charter_editor = MagicMock()
        interaction = MagicMock()
        interaction.user.id = 111
        interaction.response.send_message = AsyncMock()
        interaction.response.defer = AsyncMock()

        with patch.object(charter_git, 'CHARTER_EDITOR_IDS', [111]), \
             patch.object(charter_git, 'GITHUB_TOKEN', ''), \
             patch.object(charter_git.CharterPullRequest, 'open', AsyncMock()) as opened:
            await cog.propose.callback(cog, interaction, instruction="rewrite it", summary="nope")

        opened.assert_not_awaited()
        assert "GITHUB_TOKEN" in interaction.response.send_message.await_args[0][0]


class TestTruncationGuard:
    @pytest.mark.asyncio
    async def test_a_short_rewrite_is_refused_rather_than_wiping_the_rulebook(self):
        from cfb_bot.utils.charter_editor import CharterEditor

        editor = CharterEditor()
        editor.read_charter = MagicMock(return_value="x" * 5000)
        editor.ai_assistant = MagicMock()
        editor.ai_assistant.ask_ai = AsyncMock(return_value="too short")

        assert await editor.revise_charter("shorten it") is None

    @pytest.mark.asyncio
    async def test_a_full_rewrite_is_accepted(self):
        from cfb_bot.utils.charter_editor import CharterEditor

        editor = CharterEditor()
        editor.read_charter = MagicMock(return_value="x" * 5000)
        editor.ai_assistant = MagicMock()
        editor.ai_assistant.ask_ai = AsyncMock(return_value="y" * 4900)

        assert await editor.revise_charter("tidy it") == "y" * 4900
