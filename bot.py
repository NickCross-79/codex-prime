"""
Warframe Wiki Bot
-----------------
Monitors r/Warframe for [[Item Name]] mentions in comments and
replies with links + short descriptions from the Warframe wiki.
"""

from __future__ import annotations

import argparse
import logging
import re
import time

import praw
from praw.exceptions import RedditAPIException

from config import Config
from db import Database
from wiki import WikiLookup

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────────────────
MENTION_RE = re.compile(r"\[\[([^\[\]\n]{1,100})\]\]")
MAX_LOOKUPS = 5           # cap lookups per comment to prevent abuse
STREAM_RETRY_DELAY = 30   # seconds between stream reconnects

FOOTER = (
    "\n\n---\n"
    "^(I'm a bot! Type) ^(**\\[\\[item name\\]\\]**) "
    "^(in any comment to get a Warframe wiki link.) "
    "^([Source](https://github.com/YOUR_USERNAME/warframe-wiki-bot))"
)


# ── bot ───────────────────────────────────────────────────────────────────────
class WarframeWikiBot:
    def __init__(self, config: Config, dry_run: bool = False):
        self.cfg = config
        self.dry_run = dry_run
        self.wiki = WikiLookup()
        self.db = Database(config.DB_PATH)

        self.reddit = praw.Reddit(
            client_id=config.CLIENT_ID,
            client_secret=config.CLIENT_SECRET,
            username=config.USERNAME,
            password=config.PASSWORD,
            user_agent=f"script:WarframeWikiBot:v1.0 (by u/{config.USERNAME})",
        )

        me = self.reddit.user.me()
        log.info("Authenticated as u/%s%s", me, "  [DRY RUN]" if dry_run else "")

    # ── main loop ─────────────────────────────────────────────────────────────

    def run(self) -> None:
        log.info("Monitoring r/%s for [[mentions]] …", self.cfg.SUBREDDIT)
        sub = self.reddit.subreddit(self.cfg.SUBREDDIT)

        while True:
            try:
                for comment in sub.stream.comments(skip_existing=True):
                    self._handle_comment(comment)
            except KeyboardInterrupt:
                log.info("Shutting down — bye!")
                break
            except Exception as exc:
                log.error("Stream error: %s  — reconnecting in %ds", exc, STREAM_RETRY_DELAY)
                time.sleep(STREAM_RETRY_DELAY)

    # ── comment handling ──────────────────────────────────────────────────────

    def _handle_comment(self, comment: praw.models.Comment) -> None:
        # Skip deleted/removed comments
        if not comment.author:
            return
        # Skip the bot's own comments
        if comment.author.name.lower() == self.cfg.USERNAME.lower():
            return
        # Skip comments we've already replied to
        if self.db.has_replied(comment.id):
            return

        mentions = self._extract_mentions(comment.body)
        if not mentions:
            return

        results = [self.wiki.lookup(m) for m in mentions]
        found = [r for r in results if r["found"]]
        if not found:
            return

        reply = self._build_reply(found)

        if self.dry_run:
            log.info(
                "[DRY RUN] Would reply to %s (u/%s):\n%s",
                comment.id, comment.author, reply,
            )
            return

        self._post_reply(comment, reply)

    def _extract_mentions(self, body: str) -> list[str]:
        """Return unique mentions preserving first-seen order, up to MAX_LOOKUPS."""
        seen: set[str] = set()
        unique: list[str] = []
        for raw in MENTION_RE.findall(body):
            key = raw.strip().lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(raw.strip())
                if len(unique) >= MAX_LOOKUPS:
                    break
        return unique

    def _build_reply(self, results: list[dict]) -> str:
        lines = []
        for r in results:
            if r.get("summary"):
                lines.append(f"[**{r['title']}**]({r['url']}) — {r['summary']}")
            else:
                lines.append(f"[**{r['title']}**]({r['url']})")
        return "\n\n".join(lines) + FOOTER

    def _post_reply(self, comment: praw.models.Comment, text: str) -> None:
        try:
            comment.reply(text)
            self.db.mark_replied(comment.id)
            log.info("Replied to %s (u/%s)", comment.id, comment.author)
            time.sleep(2)  # polite delay between posts
        except RedditAPIException as exc:
            for item in exc.items:
                if item.error_type == "RATELIMIT":
                    wait = _parse_ratelimit_wait(item.message)
                    log.warning("Rate limited — sleeping %ds", wait)
                    time.sleep(wait)
                    return
            log.error("Reddit API error on %s: %s", comment.id, exc)
        except Exception as exc:
            log.error("Unexpected error replying to %s: %s", comment.id, exc)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_ratelimit_wait(message: str) -> int:
    """Extract wait seconds from a Reddit RATELIMIT error message."""
    m = re.search(r"(\d+)\s+minute", message)
    if m:
        return int(m.group(1)) * 60 + 10
    m = re.search(r"(\d+)\s+second", message)
    if m:
        return int(m.group(1)) + 10
    return 65  # safe default


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Warframe Wiki Reddit Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Look up pages but don't post any replies (useful for testing)",
    )
    args = parser.parse_args()

    cfg = Config()
    bot = WarframeWikiBot(cfg, dry_run=args.dry_run)
    bot.run()
