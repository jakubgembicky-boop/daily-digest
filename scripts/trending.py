"""
Trending detection — Reddit daily top posts, Europe/US filtered.

Fetches the top N posts from each configured subreddit and filters to
stories geographically relevant to Europe or the US. Returns a list of:
  {
    title      : str
    url        : str
    subreddit  : str
    score      : int   — Reddit upvote score
    permalink  : str   — https://www.reddit.com/r/.../
  }

No authentication required — uses Reddit's public JSON API.
"""
from __future__ import annotations

import time
from typing import Any

import httpx

from config import (
    TRENDING_SUBREDDITS,
    TRENDING_TOP_N,
    TRENDING_GEO_KEYWORDS,
)

_UA      = "Mozilla/5.0 DailyDigestBot/1.0 (daily news digest; contact via GitHub)"
_TIMEOUT = 12.0
_BASE    = "https://www.reddit.com/r/{sub}/top.json?t=day&limit={n}"


def _get(url: str) -> Any | None:
    try:
        r = httpx.get(url, headers={"User-Agent": _UA}, timeout=_TIMEOUT,
                      follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as err:
        print(f"    ! trending GET failed {url[:80]}: {err}")
        return None


def _is_geo_relevant(title: str) -> bool:
    """True if the title mentions Europe, the EU, US, UK, or specific countries."""
    low = title.lower()
    return any(kw in low for kw in TRENDING_GEO_KEYWORDS)


def fetch_trending() -> list[dict]:
    """
    Return today's top Reddit stories relevant to Europe / US,
    sorted by score descending.
    """
    seen_urls: set[str] = set()
    results: list[dict] = []

    for sub in TRENDING_SUBREDDITS:
        data = _get(_BASE.format(sub=sub, n=TRENDING_TOP_N))
        time.sleep(0.6)   # gentle throttle — Reddit bans fast scrapers
        if not data:
            continue

        posts = data.get("data", {}).get("children", [])
        accepted = 0
        for post in posts:
            p   = post.get("data", {})
            title     = (p.get("title") or "").strip()
            url       = (p.get("url") or "").strip()
            score     = p.get("score", 0)
            permalink = "https://www.reddit.com" + (p.get("permalink") or "")

            if not title or not url:
                continue
            if url in seen_urls:
                continue
            # Skip pure discussion threads (no external article)
            if p.get("is_self"):
                continue
            if not _is_geo_relevant(title):
                continue

            seen_urls.add(url)
            results.append({
                "title":     title,
                "url":       url,
                "subreddit": sub,
                "score":     score,
                "permalink": permalink,
            })
            accepted += 1

        print(f"    r/{sub}: {accepted} relevant posts")

    results.sort(key=lambda x: x["score"], reverse=True)
    print(f"  Trending total: {len(results)} geo-relevant posts")
    return results


if __name__ == "__main__":
    posts = fetch_trending()
    print(f"\n=== Top 10 trending ===")
    for p in posts[:10]:
        print(f"  r/{p['subreddit']} ({p['score']:,}): {p['title'][:70]}")
        print(f"    {p['url'][:70]}")
