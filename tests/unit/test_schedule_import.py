#!/usr/bin/env python3
"""
/league clear_schedule wipes the schedule so Harry announces nothing, and /league pull_schedule
reads it from #schedule: JSON files directly, screenshots and typed matchups through the AI.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cfb_bot.utils import schedule_import as si
from cfb_bot.utils.schedule_manager import ScheduleManager

SCHEDULE = {"season": 5, "teams": ["Texas", "LSU"], "ghost_teams": ["LSU"],
            "schedule": {"1": {"bye_teams": [], "games": [{"away": "LSU", "home": "Texas"}]},
                         "2": {"bye_teams": ["LSU"], "games": [{"away": "Texas", "home": "FSU"}]}}}


def manager(data=None):
    m = ScheduleManager()
    m.load_from_dict(json.loads(json.dumps(data or SCHEDULE)))
    m.save_to_discord = AsyncMock(return_value=True)
    return m


def attachment(filename, data=None, content_type=None):
    a = MagicMock(filename=filename, content_type=content_type, url=f"https://cdn.example/{filename}")
    a.read = AsyncMock(return_value=json.dumps(data).encode() if data is not None else b"")
    return a


def msg(content="", attachments=(), author="Rob"):
    return MagicMock(content=content, attachments=list(attachments), author=MagicMock(display_name=author))


class Channel:
    def __init__(self, *messages):  # oldest first, like reading the channel
        self.messages = list(messages)
        self.name = "schedule"
        self.mention = "#schedule"

    async def history(self, limit=20):
        for m in list(reversed(self.messages))[:limit]:
            yield m


def ai(weeks):
    return MagicMock(extract_json=AsyncMock(return_value={"weeks": weeks}))


class TestClear:
    def test_clear_keeps_teams_and_ghosts_and_announces_nothing(self):
        m = manager()
        m.clear_schedule()
        assert m.schedule_data['schedule'] == {} and m.teams == ["Texas", "LSU"] and m.ghost_teams == ["LSU"]
        assert m.build_week_embed(1) is None
        assert "No schedule is loaded" in m.get_schedule_context_for_ai()

    def test_uploads_still_need_weeks_but_a_cleared_backup_is_valid(self):
        empty = {"season": 5, "schedule": {}}
        assert not ScheduleManager.validate_schedule(empty)[0]
        assert ScheduleManager.validate_schedule(empty, allow_empty=True)[0]

    @pytest.mark.asyncio
    async def test_cleared_schedule_survives_a_restart(self):
        """The bundled schedule.json must not come back after a redeploy."""
        m = manager()
        m.bot = MagicMock()
        backup = MagicMock(author=m.bot.user, content="SCHEDULE_BACKUP (Season 5)",
                           attachments=[attachment("schedule_backup.json", {"season": 5, "teams": ["Texas"], "schedule": {}})])
        dm = MagicMock()

        async def history(limit=100):
            yield backup
        dm.history = history
        with patch('cfb_bot.utils.owner_dm.get_owner_dm', AsyncMock(return_value=dm)):
            assert await m.load_from_discord()
        assert m.schedule_data['schedule'] == {}


class TestReadingPosts:
    @pytest.mark.asyncio
    async def test_a_json_file_is_the_whole_schedule(self):
        pulled = await si.read_schedule_posts(Channel(msg(attachments=[attachment("s5.json", SCHEDULE)])))
        assert pulled.full == SCHEDULE and not pulled.weeks

    @pytest.mark.asyncio
    async def test_screenshots_and_text_after_the_json_go_to_the_ai(self):
        old_shot = attachment("old.png", content_type="image/png")
        new_shot = attachment("week3.png", content_type="image/png")
        assistant = ai({"3": {"games": [{"away": "Texas", "home": "LSU"}]}})
        channel = Channel(msg(attachments=[old_shot]), msg(attachments=[attachment("s5.json", SCHEDULE)]),
                          msg("week 3 below", attachments=[new_shot]))
        pulled = await si.read_schedule_posts(channel, ai_assistant=assistant, teams=["Texas"])
        assert pulled.full == SCHEDULE
        assert pulled.weeks == {"3": {"games": [{"away": "Texas", "home": "LSU"}], "bye_teams": []}}
        prompt, text, images = assistant.extract_json.await_args.args
        assert images == [new_shot.url]  # the screenshot from before the JSON is ignored
        assert "week 3 below" in text and "Texas" in prompt

    @pytest.mark.asyncio
    async def test_typed_matchups(self):
        assistant = ai({"4": {"games": [{"away": "Stanford", "home": "Texas"}], "bye_teams": ["LSU"]}})
        pulled = await si.read_schedule_posts(Channel(msg("Week 4: Stanford @ Texas, LSU bye")), ai_assistant=assistant)
        assert pulled.weeks["4"]["bye_teams"] == ["LSU"] and not pulled.full
        assert assistant.extract_json.await_args.args[2] == []

    @pytest.mark.asyncio
    async def test_week_option_puts_everything_in_that_week(self):
        assistant = ai({"1": {"games": [{"away": "A", "home": "B"}]}, "2": {"games": [{"away": "C", "home": "D"}]}})
        pulled = await si.read_schedule_posts(Channel(msg("games")), ai_assistant=assistant, week=6)
        assert list(pulled.weeks) == ["6"] and len(pulled.weeks["6"]["games"]) == 2
        assert "Week 6" in assistant.extract_json.await_args.args[0]

    @pytest.mark.asyncio
    async def test_harrys_own_posts_are_skipped(self):
        harry = MagicMock()
        mine = msg("📅 Week 1 Matchups")
        mine.author = harry
        assistant = ai({})
        pulled = await si.read_schedule_posts(Channel(mine), bot_user=harry, ai_assistant=assistant)
        assert pulled.empty
        assistant.extract_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_without_ai_only_json_works(self):
        pulled = await si.read_schedule_posts(Channel(msg(attachments=[attachment("a.png", content_type="image/png")])))
        assert pulled.empty and any("need AI" in n for n in pulled.notes)

    @pytest.mark.asyncio
    async def test_a_broken_json_file_is_noted_not_fatal(self):
        pulled = await si.read_schedule_posts(Channel(msg(attachments=[attachment("bad.json", {"nope": 1})])))
        assert pulled.empty and any("bad.json" in n for n in pulled.notes)

    @pytest.mark.asyncio
    async def test_screenshots_are_capped(self):
        shots = [attachment(f"{i}.png", content_type="image/png") for i in range(si.MAX_IMAGES + 2)]
        assistant = ai({"1": {"games": [{"away": "A", "home": "B"}]}})
        pulled = await si.read_schedule_posts(Channel(msg(attachments=shots)), ai_assistant=assistant)
        assert len(assistant.extract_json.await_args.args[2]) == si.MAX_IMAGES
        assert any("newest" in n for n in pulled.notes)

    def test_ai_weeks_are_checked(self):
        notes = []
        weeks = si._clean_weeks({
            "1": {"games": [{"away": "A", "home": "B"}, {"away": "B", "home": "A"}, {"away": "C", "home": "C"},
                            {"away": "", "home": "D"}, "junk"]},
            "99": {"games": [{"away": "E", "home": "F"}]},
            "bowl": {"games": [{"away": "G", "home": "H"}]},
            "2": {"games": []},
        }, None, notes)
        assert weeks == {"1": {"games": [{"away": "A", "home": "B"}], "bye_teams": []}}
        assert len(notes) == 2


def test_apply_loads_the_json_then_the_weeks_on_top():
    m = manager({"season": 1, "teams": [], "schedule": {"1": {"bye_teams": [], "games": []}}})
    pulled = si.PulledSchedule(full=json.loads(json.dumps(SCHEDULE)),
                               weeks={"2": {"games": [{"away": "X", "home": "Y"}], "bye_teams": []}})
    si.apply_pulled(m, pulled)
    assert m.season == 5 and m.get_week_schedule(1)['games'] == SCHEDULE['schedule']['1']['games']
    assert m.get_week_schedule(2)['games'] == [{"away": "X", "home": "Y"}]


def test_finds_the_schedule_channel():
    def ch(name):
        channel = MagicMock()
        channel.name = name
        return channel
    guild = MagicMock(text_channels=[ch("general"), ch("season-schedule"), ch("schedule")])
    assert si.find_schedule_channel(guild).name == "schedule"
    guild.text_channels = [ch("general"), ch("season-schedule")]
    assert si.find_schedule_channel(guild).name == "season-schedule"
    guild.text_channels = [ch("general")]
    assert si.find_schedule_channel(guild) is None


class TestCommands:
    @pytest.fixture
    def cog(self, mock_server_config):
        from cfb_bot.cogs.league import LeagueCog
        with patch('cfb_bot.cogs.league.server_config', mock_server_config):
            c = LeagueCog(MagicMock())
            c.schedule_manager = manager()
            c.ai_assistant = MagicMock(clear_response_cache=MagicMock())
            c._is_league_admin = MagicMock(return_value=True)
            yield c

    @staticmethod
    async def press(view, label, user_id):
        button = next(b for b in view.children if b.label == label)
        press = MagicMock()
        press.user.id = user_id
        press.response.edit_message = AsyncMock()
        press.response.send_message = AsyncMock()
        await button.callback(press)
        return press

    @pytest.mark.asyncio
    async def test_clear_asks_first_and_hands_back_a_copy(self, cog, mock_interaction):
        await cog.clear_schedule.callback(cog, mock_interaction)
        kwargs = mock_interaction.followup.send.await_args.kwargs
        assert kwargs['file'].filename == "schedule-season-5.json"
        assert cog.schedule_manager.get_week_schedule(1)  # not yet

        stranger = await self.press(kwargs['view'], "Clear schedule", user_id=mock_interaction.user.id + 1)
        stranger.response.send_message.assert_awaited_once()
        assert cog.schedule_manager.get_week_schedule(1)

        done = await self.press(kwargs['view'], "Clear schedule", user_id=mock_interaction.user.id)
        assert "cleared" in done.response.edit_message.await_args.kwargs['content']
        assert not cog.schedule_manager.get_week_schedule(1)
        cog.schedule_manager.save_to_discord.assert_awaited_once()
        cog.ai_assistant.clear_response_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_with_nothing_loaded(self, cog, mock_interaction):
        cog.schedule_manager.clear_schedule()
        await cog.clear_schedule.callback(cog, mock_interaction)
        assert "Nothing to clear" in mock_interaction.followup.send.await_args.args[0]

    @pytest.mark.asyncio
    async def test_pull_previews_then_applies(self, cog, mock_interaction):
        cog.ai_assistant.extract_json = AsyncMock(return_value={"weeks": {"3": {"games": [{"away": "Texas", "home": "Duke"}]}}})
        channel = Channel(msg("Week 3: Texas @ Duke"))
        await cog.pull_schedule.callback(cog, mock_interaction, channel=channel, messages=20, week=None)
        kwargs = mock_interaction.followup.send.await_args.kwargs
        assert kwargs['embed'].fields[0].name == "Week 3" and "Duke" in kwargs['embed'].fields[0].value
        assert not cog.schedule_manager.get_week_schedule(3)  # preview only

        await self.press(kwargs['view'], "Apply", user_id=mock_interaction.user.id)
        assert cog.schedule_manager.get_week_schedule(3)['games'] == [{"away": "Texas", "home": "Duke"}]
        assert cog.schedule_manager.get_week_schedule(1)  # other weeks untouched
        cog.schedule_manager.save_to_discord.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_pull_cancel_changes_nothing(self, cog, mock_interaction):
        channel = Channel(msg(attachments=[attachment("s9.json", {**SCHEDULE, "season": 9})]))
        await cog.pull_schedule.callback(cog, mock_interaction, channel=channel, messages=20, week=None)
        await self.press(mock_interaction.followup.send.await_args.kwargs['view'], "Cancel", mock_interaction.user.id)
        assert cog.schedule_manager.season == 5
        cog.schedule_manager.save_to_discord.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_pull_with_no_schedule_channel(self, cog, mock_interaction):
        mock_interaction.guild.text_channels = []
        await cog.pull_schedule.callback(cog, mock_interaction, channel=None, messages=20, week=None)
        assert "Can't find" in mock_interaction.followup.send.await_args.args[0]


@pytest.mark.asyncio
async def test_extraction_sends_screenshots_to_the_model():
    from cfb_bot.ai.ai_integration import AICharterAssistant
    assistant = AICharterAssistant.__new__(AICharterAssistant)
    assistant.openai_api_key, assistant.anthropic_api_key = "k", None
    assistant.total_openai_tokens, assistant.openai_cost_per_1k = 0, 0.001
    assistant.load_usage_stats = AsyncMock()
    assistant._record_usage = AsyncMock()
    assistant._post = AsyncMock(return_value={"usage": {"total_tokens": 10}, "choices": [
        {"message": {"content": '```json\n{"weeks": {"1": {"games": []}}}\n```'}}]})
    data = await assistant.extract_json("read it", "posts", ["https://cdn.example/a.png"])
    assert data == {"weeks": {"1": {"games": []}}}
    content = assistant._post.await_args.args[3]['messages'][1]['content']
    assert {'type': 'image_url', 'image_url': {'url': "https://cdn.example/a.png"}} in content
