#!/usr/bin/env python3
"""
Pull the league schedule from the #schedule channel.

/league pull_schedule reads the channel's latest posts, whatever shape they're in:
- a .json file (the /league upload_schedule format) replaces the whole schedule
- screenshots and typed matchups are read by the AI into weeks, which replace just those weeks

The newest JSON file is the starting point and anything posted after it goes on top. Nothing
changes until an admin checks the preview and presses Apply.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..config import GAME_NAME, env_str
from .schedule_manager import ScheduleManager
from .timekeeper import MAX_GAME_WEEK

logger = logging.getLogger('CFBBot.ScheduleImport')

SCHEDULE_CHANNEL_NAME = env_str('SCHEDULE_CHANNEL_NAME', 'schedule')
MAX_IMAGES = 8  # each screenshot is a paid AI image; the newest ones win
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.gif')

PROMPT = """These Discord posts (typed text and/or screenshots) are a {game} dynasty league's schedule.
Read every matchup and reply with:
{{"weeks": {{"<week>": {{"games": [{{"away": "Team", "home": "Team"}}], "bye_teams": ["Team"]}}}}}}

- Weeks are whole numbers from 0 to {max_week}, as strings. {week_rule}
- "A @ B" or "A at B" means A is away at B. If home and away aren't clear, put the first team as away.
- A single team's season schedule lists its opponent each week: "@ X" means that team is away at X,
  "vs X" means X is visiting it.
- Write team names as they appear. The league's own teams are: {teams}.
- Only list byes that are actually shown. Ignore anything that isn't a schedule.
- If there's no schedule in them at all, reply {{"weeks": {{}}}}.

The posts, oldest first:"""


@dataclass
class PulledSchedule:
    full: Optional[dict] = None  # from a JSON file: replaces the whole schedule
    weeks: Dict[str, dict] = field(default_factory=dict)  # from screenshots/text: replace these weeks
    notes: List[str] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.full and not self.weeks


def find_schedule_channel(guild):
    """The server's #schedule channel: an exact name match, else the first with 'schedule' in it."""
    channels = getattr(guild, 'text_channels', []) or []
    name = SCHEDULE_CHANNEL_NAME.lower().lstrip('#')
    return (next((c for c in channels if c.name.lower() == name), None)
            or next((c for c in channels if name in c.name.lower()), None))


def _is_json(attachment) -> bool:
    return attachment.filename.lower().endswith('.json')


def _is_image(attachment) -> bool:
    content_type = getattr(attachment, 'content_type', None) or ''
    return content_type.startswith('image/') or attachment.filename.lower().endswith(IMAGE_EXTENSIONS)


def _clean_weeks(raw, week: Optional[int], notes: List[str]) -> Dict[str, dict]:
    """The AI's weeks, checked: numbered 0-MAX_GAME_WEEK, real matchups, no duplicate games."""
    if not isinstance(raw, dict):
        return {}
    weeks: Dict[str, dict] = {}
    for key, data in raw.items():
        target = week if week is not None else (int(key) if str(key).strip().isdigit() else None)
        if target is None or not 0 <= target <= MAX_GAME_WEEK or not isinstance(data, dict):
            notes.append(f"Skipped week `{key}`: not a week from 0-{MAX_GAME_WEEK}.")
            continue
        entry = weeks.setdefault(str(target), {'games': [], 'bye_teams': []})
        seen = {frozenset((g['away'].lower(), g['home'].lower())) for g in entry['games']}
        for game in data.get('games') or []:
            if not isinstance(game, dict):
                continue
            away, home = str(game.get('away') or '').strip(), str(game.get('home') or '').strip()
            pair = frozenset((away.lower(), home.lower()))
            if away and home and away.lower() != home.lower() and pair not in seen:
                seen.add(pair)
                entry['games'].append({'away': away, 'home': home})
        for team in data.get('bye_teams') or []:
            if isinstance(team, str) and team.strip() and team.strip() not in entry['bye_teams']:
                entry['bye_teams'].append(team.strip())
    return {k: v for k, v in weeks.items() if v['games'] or v['bye_teams']}


async def read_schedule_posts(channel, bot_user=None, ai_assistant=None, limit: int = 20,
                              week: Optional[int] = None, teams: Optional[List[str]] = None) -> PulledSchedule:
    """Read the channel's latest `limit` posts into a schedule (nothing is applied here)."""
    pulled = PulledSchedule()
    messages = [m async for m in channel.history(limit=limit) if m.author != bot_user]  # newest first

    # The newest JSON file is the base; only posts after it can add to it
    for i, message in enumerate(messages):
        attachment = next((a for a in message.attachments if _is_json(a)), None)
        if not attachment:
            continue
        try:
            data = json.loads((await attachment.read()).decode('utf-8'))
        except Exception as e:
            pulled.notes.append(f"Couldn't read `{attachment.filename}`: {e}")
            continue
        ok, err = ScheduleManager.validate_schedule(data)
        if not ok:
            pulled.notes.append(f"Skipped `{attachment.filename}`: {err}")
            continue
        pulled.full = data
        messages = messages[:i]
        break

    texts, images = [], []
    for message in reversed(messages):  # oldest first
        if message.content.strip():
            texts.append(f"{message.author.display_name}: {message.content.strip()}")
        images += [a.url for a in message.attachments if _is_image(a)]
    if len(images) > MAX_IMAGES:
        pulled.notes.append(f"Only read the newest {MAX_IMAGES} of {len(images)} screenshots.")
        images = images[-MAX_IMAGES:]
    if not texts and not images:
        return pulled
    if not ai_assistant:
        pulled.notes.append("Screenshots and typed schedules need AI, which isn't set up.")
        return pulled

    week_rule = (f"Every game here is Week {week}, so put them all under \"{week}\"." if week is not None
                 else "Use the week each game is labelled with.")
    prompt = PROMPT.format(game=GAME_NAME, max_week=MAX_GAME_WEEK, week_rule=week_rule,
                           teams=', '.join(teams or []) or 'unknown')
    result = await ai_assistant.extract_json(prompt, '\n'.join(texts) or '(screenshots only)', images)
    if result is None:
        pulled.notes.append("The AI couldn't read those posts. Try again, or upload a JSON file.")
        return pulled
    pulled.weeks = _clean_weeks(result.get('weeks'), week, pulled.notes)
    if not pulled.weeks:
        pulled.notes.append("Didn't find any matchups in the screenshots or text.")
    logger.info(f"Read {len(pulled.weeks)} weeks from #{channel.name} ({len(images)} images, {len(texts)} posts)")
    return pulled


def apply_pulled(manager: ScheduleManager, pulled: PulledSchedule) -> None:
    """Load a pulled schedule: the JSON file (if any) first, then the weeks read on top."""
    if pulled.full:
        manager.load_from_dict(pulled.full)
    for week, data in pulled.weeks.items():
        manager.set_week_games(int(week), data['games'], data['bye_teams'])
