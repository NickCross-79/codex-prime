# Warframe Wiki Bot

A Reddit bot for r/Warframe that detects `[[Item Name]]` mentions in comments and replies with links + short descriptions from the [Warframe Wiki](https://warframe.wiki.gg/).

---

## Example

A user posts a comment:

> Anyone know how to get [[Primed Chamber]]? Also heard [[New Loka]] gives good rewards.

The bot replies:

> [**Primed Chamber**](https://warframe.wiki.gg/wiki/Primed_Chamber) — Primed Chamber is a legendary Sniper Mod that increases the damage of the first round fired from a magazine by 100%.
>
> [**New Loka**](https://warframe.wiki.gg/wiki/New_Loka) — New Loka is one of the six Syndicates in WARFRAME, a nature-revering movement whose goal is to restore…
>
> ---
> *I'm a bot! Type **[[item name]]** in any comment to get a Warframe wiki link.*

---

## Setup

### 1. Create a Reddit bot account

Register a separate Reddit account for your bot (e.g. `u/WarframeWikiLinker`).

### 2. Create a Reddit app

1. Log in as your **bot account**
2. Go to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps)
3. Click **"create another app…"** at the bottom
4. Select **script**, give it a name (e.g. "Warframe Wiki Bot")
5. Set redirect URI to `http://localhost:8080` (not used, but required)
6. Note the **client ID** (the string directly under the app name) and **client secret**

### 3. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/warframe-wiki-bot.git
cd warframe-wiki-bot

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **Python 3.9+** required.

### 4. Configure

```bash
cp .env.example .env
# Open .env in your editor and fill in the credentials
```

### 5. Test with `--dry-run`

The `--dry-run` flag looks up wiki pages and logs what the bot *would* post, without actually replying to anything. Great for checking everything works before going live.

```bash
python bot.py --dry-run
```

### 6. Run

```bash
python bot.py
```

The bot streams new comments from the subreddit in real time. It writes a `bot.db` SQLite file to remember which comments it has already replied to, so duplicate replies are prevented even across restarts.

---

## Configuration

All settings live in your `.env` file (or as real environment variables):

| Variable | Description | Default |
|---|---|---|
| `REDDIT_CLIENT_ID` | App client ID from reddit.com/prefs/apps | *(required)* |
| `REDDIT_CLIENT_SECRET` | App client secret | *(required)* |
| `REDDIT_USERNAME` | Bot account username | *(required)* |
| `REDDIT_PASSWORD` | Bot account password | *(required)* |
| `SUBREDDIT` | Subreddit to monitor (no `r/` prefix) | `Warframe` |
| `DB_PATH` | Path to the SQLite tracking database | `bot.db` |

---

## How it works

```
reddit stream
    │
    ▼
comment received
    │
    ├─ skip: bot's own comment / deleted author / already replied
    │
    ▼
regex: find all [[...]] mentions  (max 5 per comment, deduplicated)
    │
    ▼
for each mention:
    ├─ MediaWiki API: direct page lookup (follows redirects)
    └─ if not found → full-text search → re-fetch top result
    │
    ▼
format reply with title links + short extracts
    │
    ▼
comment.reply() → mark comment ID in SQLite
```

**Lookup logic** (in `wiki.py`):
1. `action=query&titles=<name>&redirects=1&prop=info|extracts` — direct lookup, handles redirects (e.g. `Primed Chamber` → canonical page)
2. If page ID is `-1` (not found), fall back to `action=query&list=search&srsearch=<name>` and re-fetch the top result

---

## Running in production

### systemd (Linux — recommended)

Create `/etc/systemd/system/warframe-wiki-bot.service`:

```ini
[Unit]
Description=Warframe Wiki Reddit Bot
After=network.target

[Service]
User=youruser
WorkingDirectory=/opt/warframe-wiki-bot
EnvironmentFile=/opt/warframe-wiki-bot/.env
ExecStart=/opt/warframe-wiki-bot/venv/bin/python bot.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now warframe-wiki-bot
sudo journalctl -fu warframe-wiki-bot   # live logs
```

### screen (simple)

```bash
screen -S warframe-bot
python bot.py
# Ctrl+A, D to detach
# screen -r warframe-bot to re-attach
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t warframe-wiki-bot .
docker run -d --restart unless-stopped \
  --env-file .env \
  -v $(pwd)/bot.db:/app/bot.db \
  warframe-wiki-bot
```

---

## Notes & tips

- **Subreddit karma gate**: r/Warframe's AutoModerator may hold replies from new accounts. Let your bot account age and earn karma first, or ask a mod to whitelist it.
- **Fandom vs wiki.gg**: The Warframe community officially migrated from warframe.fandom.com to [warframe.wiki.gg](https://warframe.wiki.gg) in 2023. This bot uses wiki.gg.
- **Rate limits**: PRAW handles Reddit's OAuth rate limits automatically. The bot adds a 2-second sleep after each reply as an extra courtesy.
- **Max 5 lookups per comment**: Caps how many `[[mentions]]` the bot processes per comment to prevent abuse.

## Ideas for extension

- Scan post bodies (submissions) in addition to comments
- Cache frequent lookups with `functools.lru_cache` to reduce API calls
- Add a `!wf search <term>` command as an alternative trigger
- Reply to comment edits (requires polling instead of streaming)
- Post a summary of daily activity to a mod channel
