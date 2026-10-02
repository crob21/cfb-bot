# 🚀 CFB 26 Rules Bot Setup Guide

Complete setup guide for Harry, the CFB 26 Rules Bot.

**Current Version:** 1.14.0

## 📋 Prerequisites

- A Discord account
- A Discord server where you have admin permissions
- Python 3.11+ (3.13 recommended)
- Optional: OpenAI API Key (for AI features)
- Optional: CollegeFootballData.com API Key (for CFB data)

## 🔧 Step 1: Discord Bot Setup

### 1.1 Create a Discord Application

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Name it (e.g., "CFB 26 Rules Bot" or "Harry")
4. Click **"Create"**

### 1.2 Create the Bot

1. Go to the **"Bot"** section
2. Click **"Add Bot"**
3. Customize:
   - **Username**: `Harry` or `CFB Bot`
   - **Avatar**: Upload a football-themed image

### 1.3 Configure Bot Permissions

In **"Bot"** section → **"Privileged Gateway Intents"**:
- ✅ **MESSAGE CONTENT INTENT** (required)
- ✅ **SERVER MEMBERS INTENT** (required)

### 1.4 Get Your Bot Token

1. In **"Bot"** section, click **"Reset Token"**
2. Copy the token (keep it secret!)

### 1.5 Get Your Server ID

1. In Discord → **User Settings** → **Advanced**
2. Enable **"Developer Mode"**
3. Right-click server name → **"Copy Server ID"**

## 🔑 Step 2: API Keys (Optional)

### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com)
2. **"API Keys"** → **"Create new secret key"**
3. Copy the key (starts with `sk-`)

### CollegeFootballData.com API Key

1. Go to [CollegeFootballData.com](https://collegefootballdata.com)
2. Create an account
3. Get your API key from the dashboard

## 💻 Step 3: Local Development Setup

### 3.1 Clone the Repository

```bash
git clone https://github.com/crob21/cfb-rules-bot.git
cd cfb-rules-bot
```

### 3.2 Install Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3.3 Configure Environment Variables

```bash
cp config/env.example .env
# Edit .env with your tokens
```

**Required:**
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_server_id_here
```

**Optional (AI features):**
```env
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Optional (CFB data):**
```env
CFB_DATA_API_KEY=your_cfb_data_api_key_here
```

**Optional (Dashboard):**
```env
DISCORD_CLIENT_ID=your_discord_app_client_id
DISCORD_CLIENT_SECRET=your_discord_app_client_secret
DISCORD_REDIRECT_URI=http://localhost:8080/auth/callback
DASHBOARD_SECRET_KEY=generate_a_random_secret_key
DASHBOARD_PORT=8080
```

### 3.4 Test the Bot Locally

```bash
python main.py
```

You should see:
```
🏈 CFB 26 League Bot v1.13.0 (Harry#1109) has connected to Discord!
📊 Connected to 1 guilds
👋 Harry is ready to help with league questions!
✅ Synced commands
```

## 📦 Step 4: Storage Configuration

Harry supports two storage backends:

### Discord DM Storage (Default)

- **Pros**: Free, no setup, survives deploys
- **Cons**: ~10-20 server limit
- **Config**: No extra setup needed!

## 🚀 Step 5: Deploy to Render

### 5.1 Connect to Render

1. Go to [Render](https://render.com)
2. Sign up with GitHub
3. **"New +"** → **"Web Service"**
4. Connect your GitHub repository

### 5.2 Configure the Service

**Basic Settings:**
- **Name**: `cfb-rules-bot`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`

**Environment Variables:**
Add all variables from your `.env` file.

### 5.3 Deploy

1. Click **"Create Web Service"**
2. Wait for build to complete
3. Check logs for successful connection

## 🔗 Step 6: Invite Bot to Your Server

### Generate Invite URL

1. [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. **"OAuth2"** → **"URL Generator"**

### Configure Permissions

**Scopes:**
- ✅ `bot`
- ✅ `applications.commands`

**Bot Permissions:**
- ✅ Send Messages
- ✅ Use Slash Commands
- ✅ Read Message History
- ✅ Add Reactions
- ✅ Embed Links
- ✅ View Channels
- ✅ Manage Messages (optional, for cleanup)

### Invite the Bot

1. Copy the generated URL
2. Paste in browser
3. Select your server
4. Click **"Authorize"**

## ✅ Step 7: Initial Configuration

### Enable Harry in Channels

Harry is **disabled by default**. Enable him in channels:

```
/channel enable
```

### Configure Modules

Enable/disable features:
```
/config              # View current settings
/config enable league    # Enable league features
/config disable cfb_data # Disable CFB data
```

### Set Up Admins

```
/add_bot_admin @user
```

### Set Timer Channel

```
/set_timer_channel #general
```

## 🔧 Troubleshooting

### Bot not responding to messages
- Check MESSAGE CONTENT INTENT is enabled
- Verify bot has View Channels permission
- Use `/channel enable` to enable Harry in the channel
- Check logs for errors

### Slash commands not appearing
- Wait a few minutes for sync
- Ensure `applications.commands` scope is selected
- Try restarting the bot

### AI features not working
- Verify your API key is correct
- Check you have credits in OpenAI account
- Look for API errors in logs

### CFB data not working
- Verify CFB_DATA_API_KEY is set
- Check CollegeFootballData.com account is active
- Some data may not be available in offseason

### Storage issues
- For Discord storage: Check bot can DM the owner

## 🌐 Web Dashboard

Run the dashboard for visual configuration:

```bash
python run_dashboard.py
# Visit http://localhost:8080
```

For production, deploy dashboard separately or alongside the bot.

## 🎉 You're Done!

Harry is now ready to help your league! Key commands:

- `/help_cfb` - See all commands
- `/whats_new` - Latest features
- `/channel enable` - Enable in current channel
- `/config` - Configure modules

**Welcome to the CFB 26 League! 🏈**

---

**Last Updated:** January 9, 2026  
**Version:** 1.13.0
