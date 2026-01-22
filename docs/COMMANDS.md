# 📖 Complete Command Reference
**CFB Rules Bot (Harry) - All Commands**  
**Version:** 3.5.0  
**Last Updated:** January 22, 2026

---

## 🎯 **QUICK START**

Type `/` in Discord to see all available command groups:
- `/admin` - Bot administration
- `/cfb` - College football data
- `/charter` - League charter
- `/harry` - AI assistant
- `/hs` - High school stats
- `/league` - League management
- `/recruiting` - Recruiting rankings

---

## 🤖 **CORE COMMANDS** (Always Available)

### `/help`
**Description:** Show all available commands  
**Module:** Core (always on)  
**Usage:** `/help`

### `/version`
**Description:** Show current bot version  
**Module:** Core (always on)  
**Usage:** `/version`

### `/changelog`
**Description:** View version history and changes  
**Module:** Core (always on)  
**Usage:** `/changelog`

### `/whats_new`
**Description:** See latest features added to Harry  
**Module:** Core (always on)  
**Usage:** `/whats_new`

---

## 🔧 **ADMIN COMMANDS** (`/admin`)

**Module:** Core (always on)  
**Permission:** Bot Admin only

### `/admin config`
**Description:** View or configure which modules are enabled  
**Options:**
- `action`: `view`, `enable`, `disable`, `enable_all`, `disable_all`
- `module`: Which module to toggle

**Usage:**
```
/admin config action:view
/admin config action:enable module:ai_chat
/admin config action:disable module:recruiting
```

### `/admin set_channel`
**Description:** Set the channel for admin notifications  
**Options:**
- `channel`: Channel to use (optional)
- `channel_id`: Channel ID (optional)

**Usage:** `/admin set_channel channel:#admin-channel`

### `/admin add`
**Description:** Add a user as bot admin  
**Options:**
- `user`: User to make admin

**Usage:** `/admin add user:@Username`

### `/admin remove`
**Description:** Remove a user as bot admin  
**Options:**
- `user`: User to remove as admin

**Usage:** `/admin remove user:@Username`

### `/admin list`
**Description:** List all bot admins  
**Usage:** `/admin list`

### `/admin block`
**Description:** Block unprompted AI responses in a channel  
**Options:**
- `channel`: Channel to block

**Usage:** `/admin block channel:#general`

### `/admin unblock`
**Description:** Allow unprompted AI responses in a channel  
**Options:**
- `channel`: Channel to unblock

**Usage:** `/admin unblock channel:#general`

### `/admin blocked`
**Description:** Show all blocked channels  
**Usage:** `/admin blocked`

### `/admin sync`
**Description:** Force sync slash commands to Discord  
**Usage:** `/admin sync`

### `/admin zyte`
**Description:** Check Zyte API usage and estimated costs  
**Options:**
- `view`: `local` (bot tracked), `api` (official stats), `both`

**Usage:** `/admin zyte view:both`

### `/admin ai`
**Description:** Check AI API usage, token consumption, and costs  
**Options:**
- `view`: `local` (bot tracked), `api` (official stats), `both`

**Usage:** `/admin ai view:both`

### `/admin cache`
**Description:** View or manage bot cache  
**Options:**
- `action`: `stats`, `clear_recruiting`, `clear_all`

**Usage:**
```
/admin cache action:stats
/admin cache action:clear_recruiting
```

### `/admin budget`
**Description:** View monthly API cost budget and spending  
**Usage:** `/admin budget`

### `/admin digest`
**Description:** View or send weekly summary digest  
**Options:**
- `action`: `view` (preview), `send` (send to all admins)

**Usage:**
```
/admin digest action:view
/admin digest action:send
```

### `/admin schedule_reload`
**Description:** Reload the league schedule from file  
**Usage:** `/admin schedule_reload`

---

## 💬 **AI CHAT COMMANDS**

**Module:** AI Chat (configurable)

### `/harry`
**Description:** Ask Harry a question about the league  
**Options:**
- `question`: Your question

**Usage:** `/harry question:What are the recruiting rules?`

### `/ask`
**Description:** Ask a general CFB question  
**Options:**
- `question`: Your question

**Usage:** `/ask question:Who won the national championship in 2023?`

### `/summarize`
**Description:** Summarize recent channel activity  
**Options:**
- `hours`: Hours of chat to summarize (default: 24)

**Usage:** `/summarize hours:48`

**Note:** You can also @mention Harry in any channel to ask questions!

---

## 🏈 **CFB DATA COMMANDS** (`/cfb`)

**Module:** CFB Data (configurable)

### `/cfb player`
**Description:** Look up college player stats  
**Options:**
- `name`: Player name (required)
- `team`: Team name (optional)

**Usage:**
```
/cfb player name:Travis Hunter
/cfb player name:Michael Penix team:Washington
```

### `/cfb rankings`
**Description:** View AP, Coaches, or CFP rankings  
**Options:**
- `poll`: `AP Top 25`, `Coaches Poll`, or `CFP`
- `week`: Week number (optional)

**Usage:** `/cfb rankings poll:AP Top 25`

### `/cfb schedule`
**Description:** View a team's schedule  
**Options:**
- `team`: Team name (required)
- `year`: Season year (optional, defaults to current)

**Usage:** `/cfb schedule team:Michigan`

### `/cfb matchup`
**Description:** View head-to-head history between two teams  
**Options:**
- `team1`: First team
- `team2`: Second team

**Usage:** `/cfb matchup team1:Ohio State team2:Michigan`

### `/cfb transfers`
**Description:** View transfer portal activity  
**Options:**
- `team`: Team name (optional)
- `year`: Year (optional)

**Usage:** `/cfb transfers team:Alabama`

---

## ⭐ **RECRUITING COMMANDS** (`/recruiting`)

**Module:** Recruiting (configurable)

### `/recruiting player`
**Description:** Look up a recruit's profile  
**Options:**
- `name`: Player name (required)
- `year`: Recruiting class year (optional, defaults to current)

**Usage:**
```
/recruiting player name:Julian Lewis
/recruiting player name:Julian Lewis year:2025
```

### `/recruiting top`
**Description:** View top recruits by position or state  
**Options:**
- `position`: Position (e.g., QB, WR, LB)
- `state`: State (e.g., CA, TX, FL)
- `limit`: Number of results (default: 10)

**Usage:**
```
/recruiting top position:QB limit:25
/recruiting top state:Texas
```

### `/recruiting class`
**Description:** View a team's recruiting class  
**Options:**
- `team`: Team name (required)
- `year`: Recruiting class year (optional)

**Usage:** `/recruiting class team:Georgia`

### `/recruiting commits`
**Description:** List a team's commits  
**Options:**
- `team`: Team name (required)
- `year`: Recruiting class year (optional)

**Usage:** `/recruiting commits team:Alabama`

### `/recruiting rankings`
**Description:** View Top 25 team recruiting rankings  
**Options:**
- `year`: Recruiting class year (optional)

**Usage:** `/recruiting rankings`

### `/recruiting source`
**Description:** Switch between On3/Rivals and 247Sports  
**Options:**
- `source`: `on3` or `247`

**Usage:** `/recruiting source source:247`

---

## 🏫 **HIGH SCHOOL STATS** (`/hs`)

**Module:** HS Stats (configurable)

### `/hs player`
**Description:** Look up high school player stats  
**Options:**
- `name`: Player name (required)
- `state`: State (optional)
- `sport`: Sport (default: football)

**Usage:**
```
/hs player name:John Smith
/hs player name:John Smith state:California
```

### `/hs team`
**Description:** Look up high school team stats  
**Options:**
- `school`: School name (required)
- `state`: State (optional)

**Usage:** `/hs team school:De La Salle state:California`

---

## 🏆 **LEAGUE COMMANDS** (`/league`)

**Module:** League (configurable)

### `/league games`
**Description:** View the games for a specific week  
**Options:**
- `week`: Week number (0-14, optional - defaults to current week)

**Usage:**
```
/league games
/league games week:12
```

### `/league find_game`
**Description:** Find a team's game for a specific week  
**Options:**
- `team`: Team name (required)
- `week`: Week number (optional)

**Usage:** `/league find_game team:Nebraska`

### `/league byes`
**Description:** Show which teams have a bye this week  
**Options:**
- `week`: Week number (optional)

**Usage:** `/league byes`

### `/league week`
**Description:** Check the current season and week  
**Usage:** `/league week`

### `/league weeks`
**Description:** View the full CFB 26 Dynasty week schedule  
**Usage:** `/league weeks`

### `/league timer`
**Description:** Start advance countdown timer (Admin only)  
**Options:**
- `hours`: Number of hours for countdown (default: 48)

**Usage:** `/league timer hours:48`

### `/league timer_status`
**Description:** Check the current advance countdown status  
**Usage:** `/league timer_status`

### `/league timer_stop`
**Description:** Stop the current advance countdown (Admin only)  
**Usage:** `/league timer_stop`

### `/league set_week`
**Description:** Set the current season and week (Admin only)  
**Options:**
- `season`: Season number
- `week`: Week number (0-14)

**Usage:** `/league set_week season:5 week:12`

### `/league staff`
**Description:** View the current league owner and co-commissioner  
**Usage:** `/league staff`

### `/league set_owner`
**Description:** Set the league owner (Admin only)  
**Options:**
- `user`: User to set as league owner

**Usage:** `/league set_owner user:@Username`

### `/league set_commish`
**Description:** Set the co-commissioner (Admin only)  
**Options:**
- `user`: User to set as co-commissioner
- `none`: Set to 'None' (optional)

**Usage:** `/league set_commish user:@Username`

### `/league pick_commish`
**Description:** Harry analyzes chat and picks a co-commissioner  
**Options:**
- `channel`: Channel to analyze (optional)
- `hours`: Hours of chat history (default: 168 = 1 week)

**Usage:** `/league pick_commish hours:336`

---

## 📜 **CHARTER COMMANDS** (`/charter`)

**Module:** League (configurable)

### `/charter view`
**Description:** View the full league charter  
**Usage:** `/charter view`

### `/charter search`
**Description:** Search the charter for specific content  
**Options:**
- `query`: Search query

**Usage:** `/charter search query:recruiting`

### `/charter section`
**Description:** View a specific section of the charter  
**Options:**
- `section_number`: Section number or name

**Usage:** `/charter section section_number:3`

### `/charter update`
**Description:** Update the charter (Admin only)  
**Options:**
- `request`: Natural language update request

**Usage:** `/charter update request:Change the recruiting limit to 5 star max`

### `/charter history`
**Description:** View recent changes to the charter  
**Options:**
- `limit`: Number of changes to show (default: 10)

**Usage:** `/charter history`

---

## 🎮 **SPECIAL FEATURES**

### **@everyone advanced**
**Description:** Advance the league week (manual trigger)  
**Usage:** Type `@everyone advanced` or `@channel advanced` in any channel  
**Effect:**
- Stops current timer
- Increments week
- Shows next week's schedule
- Starts new 48-hour timer

### **Rivalry Responses**
**Module:** Fun & Games (configurable)  
**Description:** Harry automatically responds to mentions of Oregon/Ducks  
**Keywords:**
- "Oregon"
- "Ducks"
- "Autzen"
- And more...

### **@Harry Mentions**
**Module:** AI Chat (configurable)  
**Description:** @mention Harry in any channel to ask questions  
**Usage:** `@Harry what are the recruiting rules?`

---

## 📊 **MODULE STATUS**

Check which modules are enabled with `/admin config action:view`

| Module | Commands | Default Status |
|--------|----------|----------------|
| **Core** | `/help`, `/version` | ✅ Always On |
| **AI Chat** | `/harry`, `/ask`, @mentions | ✅ Enabled |
| **CFB Data** | `/cfb` group | ✅ Enabled |
| **League** | `/league`, `/charter` | ✅ Enabled |
| **HS Stats** | `/hs` group | ✅ Enabled |
| **Recruiting** | `/recruiting` group | ✅ Enabled |
| **Fun & Games** | Rivalry responses | ✅ Enabled |

---

## 🔑 **PERMISSION LEVELS**

| Level | Commands | Who |
|-------|----------|-----|
| **Everyone** | Most commands | All server members |
| **Admin** | `/admin`, `/league timer`, `/charter update` | Bot admins + Guild owner |
| **Bot Owner** | Debug commands, full access | Bot owner only |

---

## 💡 **TIPS & TRICKS**

1. **Command Auto-complete**: Start typing `/` and Discord will suggest commands
2. **Module Toggle**: Disable unwanted features with `/admin config`
3. **Help per Command**: Discord shows command descriptions as you type
4. **Ephemeral Responses**: Most error messages are private (only you see them)
5. **Cache Clearing**: Use `/admin cache` if data seems stale
6. **Budget Monitoring**: Check spending with `/admin budget`
7. **Weekly Digest**: Admins receive automated weekly usage reports

---

## 🆘 **TROUBLESHOOTING**

**Command not showing?**
- Check if module is enabled: `/admin config`
- Ask admin to enable: `/admin config action:enable module:MODULE_NAME`

**Bot not responding?**
- Check if channel is blocked: `/admin blocked`
- Try in a different channel

**API errors?**
- Check budget: `/admin budget`
- Check API status: `/admin ai` or `/admin zyte`

**Need help?**
- Use `/help` for quick reference
- Check docs at `/docs`
- Ask Harry: `/harry question:How do I...?`

---

*Generated from CFB Rules Bot v3.5.0*  
*For support, contact bot owner or check GitHub repository*
