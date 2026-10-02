#!/usr/bin/env python3
"""Version ordering for /changelog"""

from cfb_bot import __version__
from cfb_bot.utils.version_manager import CURRENT_VERSION, VersionManager, version_key


def test_versions_sort_numerically_not_alphabetically():
    """String sorting put 3.9.0 above 3.16.1, hiding the newest releases in /changelog."""
    assert sorted(["3.9.0", "3.16.1", "3.10.0"], key=version_key, reverse=True) == ["3.16.1", "3.10.0", "3.9.0"]


def test_newest_version_is_listed_first():
    versions = VersionManager().get_all_versions()
    assert versions[0] == CURRENT_VERSION


def test_current_version_has_a_changelog_entry_and_matches_package():
    assert __version__ == CURRENT_VERSION
    assert VersionManager().get_latest_version_info().get('title')


def test_every_release_in_code_is_in_the_full_changelog():
    """The bot keeps recent releases; docs/CHANGELOG.md must keep all of them."""
    import pathlib
    from cfb_bot.utils.version_manager import CHANGELOG
    doc = (pathlib.Path(__file__).resolve().parents[2] / "docs" / "CHANGELOG.md").read_text()
    missing = [v for v in CHANGELOG if f"## {v} " not in doc]
    assert not missing, f"Add these releases to docs/CHANGELOG.md: {missing}"
