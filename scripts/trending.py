"""
Trending detection — Reddit daily top posts via RSS, Europe/US filtered.

Uses Reddit's public Atom/RSS feed (less aggressively blocked than the JSON
API on datacenter IPs such as GitHub Actions runners).

Each returned story:
  {
    title      : str
    url        : str   — external article URL (parsed from feed content)
    subreddit  : str
    score      : int   — synthetic position-based score (top post = 1500)
    permalink  : str   — https://www.reddit.com/r/.../
  }

No auth required.
"""
from __future__ import annotations

import re
import time

import feedparser
import httpx

from config import (
    TRENDING_SUBREDDITS,
    TRENDING_TOP_N,
    TRENDING_GEO_KEYWORDS,
)

_UA      = "Mozilla/5.0 (compatible; DailyDigestBot/1.0; +https://github.com)"
_TIMEOUT = 15.0
# Reddit Atom feed — top posts, current day
_BASE    = "https://www.reddit.com/r/{sub}/top.rss?t=day&limit={n}"
# Fallback: try old.reddit.com (different CDN path, sometimes not blocked)
_BASE_OLD = "https://old.reddit.com/r/{sub}/top.rss?t=day&limit={n}"


def _fetch_feed(url: str) -> list | None:
    """Fetch an RSS/Atom feed with a browser-like UA.  Returns feedparser entries or None."""
    try:
        resp = httpx.get(
            url,
            headers={
                "User-Agent": _UA,
                "Accept": "application/rss+xml,application/atom+xml,text/xml,*/*",
            },
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 403:
            return None
        resp.raise_for_status()
        feed = feedparser.parse(resp.text)
        return feed.entries if feed.entries else None
    except Exception as err:
        print(f"    ! feed fetch failed {url[:70]}: {err}")
        return None


def _parse_article_url(entry) -> str | None:
    """
    Extract the external article URL from a Reddit feed entry.

    Reddit RSS wraps the actual link inside the HTML content block:
        <a href="https://example.com/article">...</a>
    The entry.link itself is the Reddit permalink — not what we want.
    """
    content_html = ""
    if hasattr(entry, "content") and entry.content:
        content_html = entry.content[0].get("value", "")
    elif hasattr(entry, "summary"):
        content_html = entry.summary or ""

    # First href that is NOT reddit.com / redd.it
    for url in re.findall(r'href="(https?://[^"]+)"', content_html):
        if "reddit.com" not in url and "redd.it" not in url:
            return url

    # Self-posts have no external URL; skip
    return None


def _is_geo_relevant(title: str) -> bool:
    low = title.lower()
    return any(kw in low for kw in TRENDING_GEO_KEYWORDS)


def fetch_trending() -> list[dict]:
    """
    Return today's top Reddit stories relevant to Europe / US,
    sorted by (synthetic) score descending.
    """
    seen_urls: set[str] = set()
    results: list[dict] = []

    for sub in TRENDING_SUBREDDITS:
        url = _BASE.format(sub=sub, n=TRENDING_TOP_N)
        entries = _fetch_feed(url)

        if entries is None:
            # Try old.reddit.com as fallback
            url_old = _BASE_OLD.format(sub=sub, n=TRENDING_TOP_N)
            entries = _fetch_feed(url_old)

        time.sleep(0.8)  # gentle throttle

        if not entries:
            print(f"    r/{sub}: blocked or empty")
            continue

        accepted = 0
        for rank, entry in enumerate(entries[:TRENDING_TOP_N], start=1):
            title     = (getattr(entry, "title", "") or "").strip()
            permalink = (getattr(entry, "link",  "") or "").strip()

            if not title:
                continue
            if not _is_geo_relevant(title):
                continue

            article_url = _parse_article_url(entry)
            if not article_url:
                continue  # self-post / no external link
            if article_url in seen_urls:
                continue

            # Synthetic position-based score: rank 1 → 1500, rank 2 → 1460, …
            # All top posts should comfortably exceed the 500 wildcard threshold.
            synthetic_score = max(500, 1500 - (rank - 1) * 60)

            seen_urls.add(article_url)
            results.append({
                "title":     title,
                "url":       article_url,
                "subreddit": sub,
                "score":     synthetic_score,
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
        print(f"  r/{p['subreddit']} (score {p['score']:,}): {p['title'][:70]}")
        print(f"    {p['url'][:70]}")
