"""
db.py — SQLite store that tracks which Reddit comment IDs the bot
has already replied to. Prevents duplicate replies across restarts.
"""

from __future__ import annotations

import sqlite3
import logging

log = logging.getLogger(__name__)

_CREATE = """
CREATE TABLE IF NOT EXISTS replied_comments (
    comment_id  TEXT PRIMARY KEY,
    replied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class Database:
    def __init__(self, path: str = "bot.db") -> None:
        # check_same_thread=False is safe here because we access the DB
        # only from the main thread (PRAW's stream is synchronous).
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute(_CREATE)
        self._conn.commit()
        log.info("Database ready at %s", path)

    def has_replied(self, comment_id: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM replied_comments WHERE comment_id = ?",
            (comment_id,),
        )
        return cur.fetchone() is not None

    def mark_replied(self, comment_id: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO replied_comments (comment_id) VALUES (?)",
            (comment_id,),
        )
        self._conn.commit()

    def reply_count(self) -> int:
        """Return total number of comments ever replied to (for stats)."""
        cur = self._conn.execute("SELECT COUNT(*) FROM replied_comments")
        return cur.fetchone()[0]
