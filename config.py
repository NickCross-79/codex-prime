"""
config.py — Loads bot configuration from environment variables.
Copy .env.example to .env and fill in your credentials before running.
"""

from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Reddit OAuth credentials (from https://www.reddit.com/prefs/apps)
    CLIENT_ID:     str = os.getenv("REDDIT_CLIENT_ID",     "")
    CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    USERNAME:      str = os.getenv("REDDIT_USERNAME",      "")
    PASSWORD:      str = os.getenv("REDDIT_PASSWORD",      "")

    # Which subreddit to monitor (without the r/ prefix)
    SUBREDDIT: str = os.getenv("SUBREDDIT", "Warframe")

    # Path to the SQLite database file (created automatically)
    DB_PATH: str = os.getenv("DB_PATH", "bot.db")

    def __init__(self) -> None:
        required = {
            "REDDIT_CLIENT_ID":     self.CLIENT_ID,
            "REDDIT_CLIENT_SECRET": self.CLIENT_SECRET,
            "REDDIT_USERNAME":      self.USERNAME,
            "REDDIT_PASSWORD":      self.PASSWORD,
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Copy .env.example to .env and fill in the values."
            )
