# 🤖 AI Setup

Harry's AI powers `/harry`, `/ask`, `/summarize`, @mention replies, roasts, `/league pick_commish`, and
charter work (`/charter propose`, `/charter season_recap`). Everything else works without it.

## Keys

Set one or both on the host (or in `.env`, copied from `config/env.example`):

| Variable | Notes |
|----------|-------|
| `OPENAI_API_KEY` | Tried first. Model: `OPENAI_MODEL` (default `gpt-5-mini`) |
| `ANTHROPIC_API_KEY` | Fallback if OpenAI fails or isn't set. Model: `ANTHROPIC_MODEL` (default `claude-haiku-4-5`) |
| `OPENAI_COST_PER_1K` / `ANTHROPIC_COST_PER_1K` | Blended $/1k tokens for the cost estimates in `/tokens` and `/admin budget` |
| `AI_MONTHLY_BUDGET` | Monthly AI budget in USD (default 10). Harry DMs you at 50/80/90/100% |

No code changes needed: a model swap is an env change.

## What Harry knows

- **The charter**: read from [`data/charter.md`](../data/charter.md) (or the copy saved in Discord, see the README).
- **The schedule**: the last one uploaded with `/league upload_schedule`, including user teams, ghosts 👻 and user-vs-user games ⚔️.
- **His persona**: `HARRY_PERSONALITY` in `src/cfb_bot/utils/server_config.py`. Charter edits use the plainer `CHARTER_PERSONALITY`.

Answers are cached for an hour (uploading a schedule clears the cache). Any key- or token-like string in a reply is
redacted before it reaches Discord.

## Where Harry answers

The `ai_chat` module must be on (`/admin config`), and `/harry`, `/ask`, `/summarize` and @mentions only work in
channels enabled with `/admin channels`. An empty list means nowhere: AI chat is opt-in per channel.

## Checking usage

- `/tokens`: tokens and estimated cost since the last restart
- `/admin ai`: the same, plus OpenAI's own usage figures when available
- `/admin budget`: spend this month against the budget

## Troubleshooting

- **"My brain's not plugged in"**: no AI key is set.
- **Harry ignores a channel**: enable it with `/admin channels`, and check `ai_chat` is on in `/admin config`.
- **Errors**: the bot owner gets the details by DM. Check the host logs for `CFBBot.AI`.
