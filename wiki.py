"""
wiki.py — Warframe wiki lookup via the MediaWiki API.

Flow for a query like "Primed Chamber":
  1. Try a direct page lookup (follows redirects automatically).
  2. If the page doesn't exist, fall back to a full-text search and
     re-query the top result.
  3. Return the canonical title, full URL, and a short extract.
"""

from __future__ import annotations

import logging
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)

WIKI_API  = "https://wiki.warframe.com/api.php"
WIKI_BASE = "https://wiki.warframe.com/wiki/"
TIMEOUT   = 6   # seconds per request
MAX_SUMMARY_CHARS = 250


class WikiLookup:
    def __init__(self) -> None:
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "WarframeWikiBot/1.0"

    # ── public ────────────────────────────────────────────────────────────────

    def lookup(self, query: str) -> dict:
        """
        Returns a dict with at minimum {"found": bool, "query": str}.
        On success also includes "title", "url", and optionally "summary".
        """
        query = query.strip()

        result = self._fetch_page(query)
        if result:
            return {"found": True, "query": query, **result}

        # Fallback: search and re-fetch the best hit
        result = self._search_then_fetch(query)
        if result:
            return {"found": True, "query": query, **result}

        log.info("No wiki page found for %r", query)
        return {"found": False, "query": query}

    # ── private ───────────────────────────────────────────────────────────────

    def _fetch_page(self, title: str) -> dict | None:
        """
        Query a specific page title, following redirects.
        Returns None if the page doesn't exist.
        """
        try:
            resp = self._session.get(
                WIKI_API,
                params={
                    "action":     "query",
                    "titles":     title,
                    "redirects":  "1",
                    "prop":       "info|extracts",
                    "inprop":     "url",
                    "exintro":    "1",
                    "exsentences":"2",
                    "explaintext":"1",
                    "format":     "json",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            pages = resp.json()["query"]["pages"]
            page_id, page = next(iter(pages.items()))

            if page_id == "-1":
                return None  # page not found

            return _page_to_dict(page)

        except Exception as exc:
            log.warning("Page fetch failed for %r: %s", title, exc)
            return None

    def _search_then_fetch(self, query: str) -> dict | None:
        """Full-text search; re-fetches the top result for full detail."""
        try:
            resp = self._session.get(
                WIKI_API,
                params={
                    "action":   "query",
                    "list":     "search",
                    "srsearch": query,
                    "srlimit":  "1",
                    "format":   "json",
                },
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            hits = resp.json()["query"]["search"]
            if not hits:
                return None
            return self._fetch_page(hits[0]["title"])

        except Exception as exc:
            log.warning("Search failed for %r: %s", query, exc)
            return None


# ── helpers ───────────────────────────────────────────────────────────────────

def _page_to_dict(page: dict) -> dict:
    title = page["title"]
    # The API returns fullurl when inprop=url is used; fall back to construction
    url = page.get("fullurl") or _build_url(title)
    summary = _trim_extract(page.get("extract", ""))
    return {"title": title, "url": url, "summary": summary}


def _build_url(title: str) -> str:
    return WIKI_BASE + quote(title.replace(" ", "_"), safe=":/")


def _trim_extract(text: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    """
    Return the first paragraph of the extract, trimmed to max_chars.
    Wiki extracts sometimes contain newlines between sections; we only
    want the first meaningful line.
    """
    if not text:
        return ""
    # Take just the first non-empty paragraph
    first_para = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if len(first_para) <= max_chars:
        return first_para
    return first_para[:max_chars].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
