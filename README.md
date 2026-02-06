# Charles — Smart Notification Gateway

**Live:** https://charles.aws.monce.ai

Charles is a memory system with a bullshit filter. Anyone can spam it with messages — Haiku classifies every one, and only the genuinely important stuff triggers a Telegram push notification to Charles Dana's phone. Max 3 notifications per day out of potentially thousands of calls.

## How it works

```
charles "hey, production is down"
    │
    ▼  POST /message
charles.aws.monce.ai (FastAPI)
    │
    ├─ remember in memories.json
    ├─ haiku classifies: notify?
    │   └─ important + count < 3
    │       └─ telegram push ──→ 📱
    │           ├─ [Yes]
    │           ├─ [No]
    │           └─ [Prompt] → type response
    │                          └─ stored → smarter filter
    └─ reply
```

The filter gets smarter over time: Charles Dana's responses feed back into Haiku's classification context.

## CLI

```bash
pip install -e .

charles "hello world"                  # remember + classify + maybe notify
charles "hey charles dana, prod down"  # probably triggers notification
charles forget coffee                  # forget memories about coffee
```

Falls back to local Bedrock if the API is unreachable.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Landing page (mobile-friendly) |
| `/health` | GET | Stats: memories, notifications today, responses |
| `/message` | POST | Receive text → remember → classify → maybe notify |
| `/forget` | POST | Remove memories matching query |
| `/memories` | GET | List all memories (paginated) |
| `/webhook/telegram` | POST | Telegram bot callback (Yes/No/Prompt) |
| `/docs` | GET | Swagger API docs |

### Quick test

```bash
# Health check
curl https://charles.aws.monce.ai/health

# Send a message
curl -X POST https://charles.aws.monce.ai/message \
  -H "Content-Type: application/json" \
  -d '{"text": "is charles dana around?"}'

# View memories
curl https://charles.aws.monce.ai/memories

# Forget something
curl -X POST https://charles.aws.monce.ai/forget \
  -H "Content-Type: application/json" \
  -d '{"query": "coffee"}'
```

## Claude Code hook

Every prompt you type in Claude Code gets forwarded to Charles automatically via a `UserPromptSubmit` hook.

**Config** (`~/.claude/settings.json`):
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/charlesdana/.claude/hooks/forward-prompt.sh",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

The hook script extracts the prompt from stdin JSON and POSTs it in the background (fire-and-forget, never blocks).

## Infrastructure

| Resource | Value |
|----------|-------|
| Instance | `t3.small` (2 vCPU, 2GB) |
| Region | eu-west-3 (Paris) |
| DNS | `charles.aws.monce.ai` → Route53 A record |
| SSL | Let's Encrypt via certbot |
| Process | gunicorn + uvicorn, 2 workers |
| Reverse proxy | nginx |

## Deploy

```bash
cd terraform
terraform init && terraform apply   # first time only
./deploy.sh                         # rsync + restart
```

## Environment variables (`/opt/charles/.env`)

```
AWS_BEARER_TOKEN_BEDROCK=...    # Bedrock Haiku access
TELEGRAM_BOT_TOKEN=...          # from @BotFather
TELEGRAM_CHAT_ID=...            # your Telegram chat ID
```

## Telegram setup

1. Message @BotFather → `/newbot` → name it "Charles" → copy token
2. Message the bot, then call `https://api.telegram.org/bot<TOKEN>/getUpdates` to get your chat ID
3. Add both to `/opt/charles/.env`, restart: `sudo systemctl restart charles`
4. Set webhook:
   ```
   curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://charles.aws.monce.ai/webhook/telegram"
   ```

## Project structure

```
charles/
├── charles.py              # CLI (posts to API, local fallback)
├── setup.py                # pip install -e .
├── api/
│   ├── main.py             # FastAPI app + landing page
│   ├── config.py           # env vars
│   ├── routes.py           # all endpoints
│   ├── haiku.py            # Bedrock Haiku classifier + chat
│   ├── notifications.py    # Telegram bot (buttons + rate limit)
│   ├── memory.py           # JSON memory management
│   ├── requirements.txt    # dependencies
│   └── static/
│       └── index.html      # mobile-first dark theme UI
└── terraform/
    ├── main.tf             # EC2, SG, Route53
    └── deploy.sh           # rsync + systemd + nginx
```

## Server-side data

```
/opt/charles/
├── app/                    # code (synced from local)
├── data/
│   ├── memories.json       # all messages
│   └── charles-dana/
│       ├── MANIFEST.md     # rules
│       └── responses.json  # Charles Dana's replies
├── venv/
└── .env
```
