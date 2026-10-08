#!/usr/bin/env python3
"""
Charter changes as GitHub pull requests.

Harry can propose a charter edit, never land one. Every change goes to a branch and a
PR that a human reviews and merges — this module has no merge call on purpose, and the
token it uses should not be able to push to the base branch.

Gated twice:
  1. CHARTER_EDITOR_IDS — Discord user IDs allowed to propose at all (empty = nobody)
  2. GITHUB_TOKEN / GITHUB_REPO — absent means the whole feature is off
"""

import base64
import logging
from datetime import datetime
from typing import Optional, Tuple

import aiohttp

from ..config import (CHARTER_EDITOR_IDS, CHARTER_FILE, GITHUB_BASE_BRANCH,
                      GITHUB_REPO, GITHUB_TOKEN)
from ..security import HTTP_TIMEOUT

logger = logging.getLogger('CFBBot.CharterGit')

GITHUB_API = "https://api.github.com"


def may_propose_charter_change(user_id: int) -> bool:
    """True only for Discord users explicitly listed in CHARTER_EDITOR_IDS."""
    return bool(CHARTER_EDITOR_IDS) and user_id in CHARTER_EDITOR_IDS


def is_configured() -> bool:
    """True when a token and repo are set, so PRs can be opened at all."""
    return bool(GITHUB_TOKEN and GITHUB_REPO)


def for_github_text(text: str, limit: int = 200) -> str:
    """
    Make Discord-supplied text safe to drop into a GitHub title or body.

    A display name like "@crob21" would ping a real GitHub user from the PR body, and
    backticks or pipes can wreck the formatting.
    """
    cleaned = text.replace('@', '').replace('`', "'").replace('\r', ' ').replace('\n', ' ')
    cleaned = ' '.join(cleaned.split())
    return cleaned[:limit] if len(cleaned) > limit else cleaned


def branch_name(summary: str) -> str:
    """A readable, unique branch name for one charter change."""
    slug = "".join(c if c.isalnum() else "-" for c in summary.lower())
    slug = "-".join(part for part in slug.split("-") if part)[:40].strip("-") or "update"
    return f"charter/{slug}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


class CharterPullRequest:
    """Opens (never merges) a pull request containing the new charter."""

    def __init__(self, token: str = None, repo: str = None, base: str = None):
        self.token = token or GITHUB_TOKEN
        self.repo = repo or GITHUB_REPO
        self.base = base or GITHUB_BASE_BRANCH

    @property
    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }

    async def _request(self, session, method: str, path: str, **kwargs):
        async with session.request(method, f"{GITHUB_API}{path}",
                                   headers=self._headers, **kwargs) as response:
            body = await response.json(content_type=None)
            if response.status >= 400:
                message = body.get('message', response.status) if isinstance(body, dict) else response.status
                raise RuntimeError(f"GitHub {method} {path} failed: {message}")
            return body

    async def open(self, content: str, summary: str, author: str) -> Tuple[bool, Optional[str]]:
        """
        Put `content` on a new branch and open a PR.

        Returns (ok, pr_url_or_error). The PR is left open for a human to merge.
        """
        if not (self.token and self.repo):
            return False, "GitHub isn't configured (GITHUB_TOKEN / GITHUB_REPO)"

        summary = for_github_text(summary)
        author = for_github_text(author, limit=100)
        branch = branch_name(summary)
        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # branch off the base
                base_ref = await self._request(
                    session, 'GET', f"/repos/{self.repo}/git/ref/heads/{self.base}")
                await self._request(
                    session, 'POST', f"/repos/{self.repo}/git/refs",
                    json={'ref': f"refs/heads/{branch}", 'sha': base_ref['object']['sha']})

                # the file's current blob sha, when it already exists
                try:
                    existing = await self._request(
                        session, 'GET',
                        f"/repos/{self.repo}/contents/{CHARTER_FILE}?ref={self.base}")
                    file_sha = existing.get('sha')
                except RuntimeError:
                    file_sha = None

                commit = {
                    'message': f"Charter: {summary}\n\nProposed by {author} via Harry.",
                    'content': base64.b64encode(content.encode('utf-8')).decode('ascii'),
                    'branch': branch,
                }
                if file_sha:
                    commit['sha'] = file_sha
                await self._request(
                    session, 'PUT', f"/repos/{self.repo}/contents/{CHARTER_FILE}", json=commit)

                pull = await self._request(
                    session, 'POST', f"/repos/{self.repo}/pulls",
                    json={
                        'title': f"Charter: {summary}",
                        'head': branch,
                        'base': self.base,
                        'body': (
                            f"Charter change proposed by **{author}** through Harry.\n\n"
                            f"**Summary:** {summary}\n\n"
                            "Harry can open this PR but cannot merge it — review and merge "
                            "it yourself, then redeploy so he reads the new charter."
                        ),
                    })

                url = pull.get('html_url')
                logger.info(f"Opened charter PR {url} on branch {branch} for {author}")
                return True, url

        except Exception as e:
            logger.error(f"Failed to open charter PR: {e}")
            return False, str(e)
