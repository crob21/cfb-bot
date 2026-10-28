# 📖 Command Reference

Every slash command, by group. The tables are generated from the commands themselves, and a test fails if
one is missing here. `?` marks an optional option. Discord shows each option's help as you type.

## Modules

Each group belongs to a module that admins switch on or off per server with `/admin config`.

| Module | Commands | Default |
|--------|----------|---------|
| `core` | `/help`, `/version`, `/changelog`, `/whats_new`, `/tokens` | Always on |
| `ai_chat` | `/harry`, `/ask`, `/summarize`, @mentions | On, in channels enabled with `/admin channels` |
| `cfb_data` | `/cfb` | On (needs `CFB_DATA_API_KEY`) |
| `fun_games` | `/fun`, team banter | On |
| `league` | `/league`, `/charter` | Off (opt-in) |
| `recruiting` | `/recruiting` | Off (opt-in) |
| `hs_stats` | `/hs` | Off (opt-in) |

## 🤖 Core and AI chat

Module: `core / ai_chat`

| Command | What it does | Options |
|---------|--------------|---------|
| `/help` | Show all available commands | - |
| `/version` | Show current bot version | - |
| `/changelog` | View version changelog | `version`? |
| `/whats_new` | See what's new with Harry! | - |
| `/tokens` | Show AI token usage statistics | - |
| `/harry` | Ask Harry about college football | `question` |
| `/ask` | Ask Harry general questions (not league-specific) | `question` |
| `/summarize` | Summarize channel activity for a time period | `hours`?, `focus`? |

## 🏆 League (`/league`)

Module: `league`

| Command | What it does | Options |
|---------|--------------|---------|
| `/league timer` | Start advance countdown timer (Admin only) | `hours`? |
| `/league side_timer` | Start a countdown for another league (Madden, 2K…) | `league`, `hours`? |
| `/league side_timer_stop` | Stop a side league's countdown | `league` |
| `/league timer_status` | Check the current advance countdown status | - |
| `/league timer_stop` | Stop the current advance countdown (Admin only) | - |
| `/league timers` | List all active advance timers and stop them (Admin only) | - |
| `/league week` | Check the current season and week | - |
| `/league weeks` | View the full CFB 27 Dynasty week schedule | - |
| `/league games` | View the games for a specific week | `week`? |
| `/league schedule` | View the full season schedule, or one team's whole season | `team`? |
| `/league find_game` | Find a team's game for a specific week | `team`, `week`? |
| `/league byes` | Show which teams have a bye this week | `week`? |
| `/league set_week` | Set the current season and week (Admin only) | `season`, `week` |
| `/league upload_schedule` | Upload a full schedule JSON file (Admin only) | `file` |
| `/league set_week_games` | Set one week's games/byes by typing them (Admin only) | `week`, `games`, `byes`? |
| `/league ghost` | Mark or unmark a team whose coach never shows up 👻 (Admin only) | `team` |
| `/league schedule_template` | Show the schedule JSON format for uploads | - |
| `/league timer_channel` | Set the channel for timer notifications (Admin only) | `channel` |
| `/league staff` | View the current league owner and co-commissioner | - |
| `/league set_owner` | Set the league owner (Admin only) | `user` |
| `/league set_commish` | Set the co-commissioner (Admin only) | `user`?, `none`? |
| `/league pick_commish` | Rank the chat's most active members for co-commissioner (Admin only) | `channel`?, `hours`? |
| `/league nag` | Nag the league owner to advance (Bot Owner only) | `action`?, `interval`? |

## 📜 Charter (`/charter`)

Module: `league`

| Command | What it does | Options |
|---------|--------------|---------|
| `/charter link` | Get link to the official league charter | - |
| `/charter scan` | Scan a channel for rule changes and votes | `channel`, `hours`? |
| `/charter import` | Import the charter from its Google Doc (Admin only) | `url`? |
| `/charter sync` | Sync charter to Discord (Admin only) | - |
| `/charter history` | View recent charter changes | - |
| `/charter search` | Search the official league charter | `search_term` |
| `/charter add` | Add a new rule to the charter (Admin only) | `section_title`, `rule_content`, `position`? |
| `/charter propose` | Have Harry draft a charter change and open a pull request (charter editors only) | `instruction`, `summary`, `channel`?, `hours`? |
| `/charter season_recap` | Have Harry write the season into League History (charter editors only) | `channel`?, `hours`? |
| `/charter update` | Update an existing rule (Admin only) | `section_identifier`, `new_content` |
| `/charter backups` | View available backups (Admin only) | - |
| `/charter restore` | Restore from backup (Admin only) | `backup_filename` |

## 🏈 CFB data (`/cfb`)

Module: `cfb_data`

| Command | What it does | Options |
|---------|--------------|---------|
| `/cfb player` | Look up a college football player's stats and info | `name`, `team`? |
| `/cfb players` | Look up multiple players at once | `player_list` |
| `/cfb rankings` | Get college football rankings (AP, Coaches, CFP) | `team`?, `year`?, `week`?, `poll`?, `top`? |
| `/cfb matchup` | Get historical matchup data between two teams | `team1`, `team2` |
| `/cfb schedule` | Get a team's schedule and results | `team`, `year`? |
| `/cfb draft` | Get NFL draft picks from a college | `team`?, `year`? |
| `/cfb transfers` | Get transfer portal activity for a team | `team`, `year`? |
| `/cfb betting` | Get betting lines for games | `team`?, `year`?, `week`? |
| `/cfb ratings` | Get advanced ratings (SP+, SRS, Elo) for a team | `team`, `year`? |
| `/cfb teamstats` | Get full season statistics for a team (offense & defense) | `team`, `year`? |

## ⭐ Recruiting (`/recruiting`)

Module: `recruiting`

| Command | What it does | Options |
|---------|--------------|---------|
| `/recruiting player` | Look up a recruit's ranking | `name`, `year`?, `position`?, `deep_search`? |
| `/recruiting top` | Get top recruits by position or state | `position`?, `state`?, `year`?, `top`? |
| `/recruiting class` | Get a team's recruiting class ranking | `team`, `year`? |
| `/recruiting commits` | List all committed recruits for a team | `team`, `year`?, `show`? |
| `/recruiting rankings` | Get top team recruiting class rankings | `year`?, `top`? |
| `/recruiting portal` | Look up a transfer portal player (recruiting + college stats) | `name`, `team`? |
| `/recruiting source` | Set the recruiting data source | `source`? |

## 🏫 High school stats (`/hs`)

Module: `hs_stats`

| Command | What it does | Options |
|---------|--------------|---------|
| `/hs stats` | Look up high school football player stats from MaxPreps | `name`, `state`?, `school`? |
| `/hs bulk` | Look up multiple HS players at once | `players` |

## 🔧 Admin (`/admin`)

Module: `-`

| Command | What it does | Options |
|---------|--------------|---------|
| `/admin set_channel` | Set the channel for admin outputs | `channel`?, `channel_id`? |
| `/admin add` | Add a user as bot admin | `user` |
| `/admin remove` | Remove a user as bot admin | `user` |
| `/admin list` | List all bot admins | - |
| `/admin block` | Block unprompted responses in a channel | `channel` |
| `/admin unblock` | Allow unprompted responses in a channel | `channel` |
| `/admin blocked` | Show all blocked channels | - |
| `/admin config` | Configure Harry's features for this server | `action`?, `module`? |
| `/admin sync` | Force sync slash commands | - |
| `/admin channels` | View/manage which channels Harry can respond in | `action`?, `channel`? |
| `/admin zyte` | Check Zyte API usage and estimated costs | `view`? |
| `/admin ai` | Check AI API usage, token consumption, and estimated costs | `view`? |
| `/admin cache` | View or manage bot cache | `action`? |
| `/admin budget` | View monthly API cost budget and spending | `action`? |
| `/admin digest` | View or send weekly summary digest | `action`? |
| `/admin schedule_reload` | Reload the league schedule from file (Admin only) | - |

## 🎭 Fun (`/fun`, admin only)

Module: `fun_games`

| Command | What it does | Options |
|---------|--------------|---------|
| `/fun target` | 🎯 Start trolling a user (Admin only) | `user`, `timeout`?, `engage`?, `everywhere`? |
| `/fun untarget` | 🛑 Stop trolling a user (Admin only) | `user` |
| `/fun timeout` | ⏱️ Adjust timeout for a user (Admin only) | `user`, `timeout` |
| `/fun toggle_engage` | 🔥 Toggle argument mode for a user (Admin only) | `user` |
| `/fun status` | 📋 Check trolling status (Admin only) | - |
| `/fun target_all` | 🎯 Start trolling multiple users at once (Admin only) | `users`, `timeout`?, `engage`?, `everywhere`? |
| `/fun roast` | 🔥 Roast a user immediately (Admin only) | `user` |
| `/fun untarget_all` | 🛑 Stop trolling ALL users (Admin only) | - |

## 🎮 Without a slash command

- **`@everyone advanced`**: posted in the advance channel, it moves the dynasty week on, restarts the 48-hour
  countdown and posts the new week's matchups. On the advance into End of Season Recap, Harry also opens the
  season's history thread.
- **"done" in a 📜 Season N History thread**: from a charter editor, it makes Harry open the charter PR.
- **@Harry**: ask a question without a slash command, in channels enabled with `/admin channels`. One reply per
  person every 10 seconds. `@everyone`/`@here` never counts.
- **Team banter**: name a rival (Oregon, Ohio State, Michigan…) and Harry has something to say. Whole words only.

## 🔑 Who can run what

| Who | Commands |
|-----|----------|
| Everyone | Most commands |
| Admins (server admins and `BOT_ADMIN_IDS`) | Anything marked *Admin only*, plus `/admin` and `/fun` |
| Charter editors (`CHARTER_EDITOR_IDS`) | `/charter propose`, `/charter season_recap` |
| League owner | Gets nagged by `/league nag` |
