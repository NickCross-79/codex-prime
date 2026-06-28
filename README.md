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

