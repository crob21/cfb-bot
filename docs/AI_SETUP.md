# 🤖 AI Integration Setup Guide

This guide will help you add AI capabilities to your CFB 27 League Bot, allowing users to ask natural language questions about your league charter.

## What AI Integration Adds

- **`/ask <question>`** - Ask natural language questions about league rules
- **Smart responses** - AI understands context and provides helpful answers
- **Charter knowledge** - AI is trained on your specific league rules
- **Fallback support** - Multiple AI providers for reliability

## AI Provider Options

### Option 1: OpenAI (Recommended)
- **Models**: GPT-3.5-turbo, GPT-4
- **Cost**: ~$0.002 per question
- **Speed**: Fast responses
- **Setup**: Easy API key setup

### Option 2: Anthropic Claude
- **Models**: Claude-3-Haiku, Claude-3-Sonnet
- **Cost**: ~$0.001 per question
- **Speed**: Fast responses
- **Setup**: Easy API key setup

### Option 3: Both (Best Reliability)
- **Fallback**: If OpenAI fails, tries Anthropic
- **Cost**: Only pay for successful requests
- **Reliability**: Highest uptime

## Setup Instructions

### Step 1: Get API Keys

#### OpenAI Setup:
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

#### Anthropic Setup:
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up or log in
3. Go to "API Keys" section
4. Create a new key
5. Copy the key (starts with `sk-ant-`)

### Step 2: Configure Environment

1. **Copy the example file:**
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` file:**
   ```bash
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   DISCORD_GUILD_ID=your_guild_id_here
   
   # AI Integration (choose one or both)
   OPENAI_API_KEY=sk-your_openai_key_here
   ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here
   ```

### Step 3: Update Charter Content

The AI needs to know your league rules. Edit `ai_integration.py` and update the `get_charter_content()` method with your actual charter content:

```python
async def get_charter_content(self) -> Optional[str]:
    return """
    Your actual league charter content here...
    
    RECRUITING:
    - Your recruiting rules
    - Visit limits
    - Dead periods
    
    TRANSFERS:
    - Transfer portal rules
    - Eligibility requirements
    
    GAMEPLAY:
    - Difficulty settings
    - House rules
    - Simulation policies
    
    etc...
    """
```

### Step 4: Test the Integration

1. **Run the bot:**
   ```bash
   python bot.py
   ```

2. **Test AI command:**
   ```
   /ask What are the recruiting rules?
   /ask How many transfers can I have?
   /ask What difficulty should I use?
   ```

## Example Questions Users Can Ask

- "What are the recruiting rules for this season?"
- "How many official visits can I give to a player?"
- "What happens if I want to transfer a player?"
- "What difficulty setting should I use for games?"
- "Can I sim games without permission?"
- "What are the penalties for breaking rules?"
- "How often do we advance the schedule?"

## Cost Estimation

### OpenAI (GPT-3.5-turbo):
- **Per question**: ~$0.002
- **100 questions/month**: ~$0.20
- **1000 questions/month**: ~$2.00

### Anthropic (Claude-3-Haiku):
- **Per question**: ~$0.001
- **100 questions/month**: ~$0.10
- **1000 questions/month**: ~$1.00

## Troubleshooting

### "AI integration not available"
- Check that you have the API keys in your `.env` file
- Make sure the keys are valid and have credits

### "Error getting AI response"
- Check your internet connection
- Verify API keys are correct
- Check if you have credits remaining

### "No response from AI"
- Try the fallback provider (if you have both keys)
- Check the bot logs for error messages
- Verify the charter content is properly formatted

## Advanced Configuration

### Custom Charter Content
You can make the AI smarter by providing more detailed charter content:

```python
async def get_charter_content(self) -> Optional[str]:
    # You can also fetch from Google Docs API here
    # or load from a local file
    with open('charter_content.txt', 'r') as f:
        return f.read()
```

### Custom AI Prompts
Modify the AI prompts in `ai_integration.py` to better match your league's tone and style.

## Security Notes

- **Never commit API keys** to version control
- **Use environment variables** for all sensitive data
- **Monitor usage** to avoid unexpected charges
- **Set usage limits** in your AI provider dashboard

## Support

If you need help with AI integration:
1. Check the bot logs for error messages
2. Verify your API keys are working
3. Test with simple questions first
4. Check your AI provider's status page

The AI integration is completely optional - your bot works great without it!
