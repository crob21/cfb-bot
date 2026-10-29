#!/usr/bin/env python3
"""
What the two recruiting sources (247Sports and On3/Rivals) share: the shared cache, the
recruiting-class year, and the parts of their Discord output that look the same.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from .cache import get_cache


class RecruitingScraperBase:
    """Base for a recruiting scraper. Subclasses set CACHE_NAMESPACE and _cache_ttl_seconds."""

    CACHE_NAMESPACE = ''
    _cache_ttl_seconds = 3600
    # How the source's team-class average rating reads (247: 0.9123, On3: 91.23)
    AVG_RATING_FORMAT = '.4f'
    POINTS_LABEL = 'Points'

    def _get_current_recruiting_year(self) -> int:
        """The class being recruited: next year's from February on (signing day), else this year's."""
        now = datetime.now()
        return now.year + 1 if now.month >= 2 else now.year

    def _get_cached(self, key: str) -> Optional[Any]:
        """Cached data if still valid (shared cache, so /admin cache clear clears it)"""
        return get_cache().get(key, namespace=self.CACHE_NAMESPACE)

    def _set_cached(self, key: str, data: Any):
        """Cache data with the scraper's TTL"""
        get_cache().set(key, data, ttl_seconds=self._cache_ttl_seconds, namespace=self.CACHE_NAMESPACE)

    @staticmethod
    def _recruit_summary_lines(recruit: Dict[str, Any], rating_lines: List[str]) -> List[str]:
        """Name, ratings, rankings and profile: the top of every recruit card."""
        stars = recruit.get('stars')
        position = recruit.get('position', '')
        lines = [f"**{recruit.get('name', 'Unknown')}** {'⭐' * stars if stars else ''}"]
        if position:
            lines.append(f"📍 **{position}** | Class of **{recruit.get('year', '')}**")
        lines += ["", "**📊 Ratings**", *rating_lines, "", "**🏆 Rankings**"]

        ranks = []
        natl = recruit.get('national_rank') or recruit.get('national_rank_247')
        if natl:
            ranks.append(f"• National: **#{natl}**")
        pos_rank = recruit.get('position_rank') or recruit.get('position_rank_247')
        if pos_rank:
            ranks.append(f"• {position}: **#{pos_rank}**")
        state_rank = recruit.get('state_rank') or recruit.get('state_rank_247')
        if state_rank:
            ranks.append(f"• {recruit.get('state', '')}: **#{state_rank}**")
        lines += ranks or ["• _Rankings not available_"]
        lines += ["", "**📏 Profile**"]

        size = [f"**{v}**" for v in [recruit.get('height')] if v]
        if recruit.get('weight'):
            size.append(f"**{recruit['weight']} lbs**")
        if size:
            lines.append(f"• Size: {' / '.join(size)}")
        if recruit.get('city') and recruit.get('state'):
            lines.append(f"• Hometown: {recruit['city']}, {recruit['state']}")
        if recruit.get('high_school'):
            lines.append(f"• High School: {recruit['high_school']}")
        return lines

    def format_top_recruits(self, recruits: List[Dict[str, Any]], title: str = "Top Recruits") -> str:
        """Format list of top recruits"""
        if not recruits:
            return "❌ No recruits there, mate. Try different filters."

        lines = [f"**{title}**", ""]
        for i, r in enumerate(recruits, 1):
            stars = '⭐' * r['stars'] if r.get('stars') else ''
            line = f"`{i:2d}.` {stars} **{r.get('name', 'Unknown')}** ({r.get('position', '')})"
            if r.get('committed_to'):
                line += f" → {r['committed_to']}"
            lines.append(line)
        return '\n'.join(lines)

    def format_team_class(self, team_data: Dict[str, Any]) -> str:
        """Format team recruiting class for display"""
        if not team_data:
            return "❌ Never heard of that team, mate. Check the spelling."

        lines = [f"**{team_data.get('team', 'Unknown')}** - #{team_data.get('rank', '?')} Nationally "
                 f"({team_data.get('year', '')})", ""]
        if team_data.get('total_commits'):
            lines.append(f"👥 **{team_data['total_commits']}** Commits")
        if team_data.get('avg_rating'):
            lines.append(f"📊 Avg Rating: **{team_data['avg_rating']:{self.AVG_RATING_FORMAT}}**")
        if team_data.get('avg_nil'):
            lines.append(f"💰 Avg NIL: **{team_data['avg_nil']}**")
        if team_data.get('points'):
            lines.append(f"🏆 {self.POINTS_LABEL}: **{team_data['points']:.2f}**")

        stars = [f"{'⭐' * n} {team_data[f'{n}_stars']}" for n in (5, 4, 3) if team_data.get(f'{n}_stars')]
        if stars:
            lines += ["", "**Star Breakdown:**", *stars]
        return '\n'.join(lines)
