"""
Fetch — thin RSS + API layer for the Claude Routine pipeline.

Returns a flat list of article dicts:
  {
    title         : str   — original title (never translated here)
    url           : str
    source        : str   — display name
    paid_partner  : bool  — Denník N / NYT / FT / The Athletic
    paywall_only  : bool  — paywalled, not our partner (WSJ, Economist…)
    lang          : str   — "sk" | "cs" | "en"
    published     : str   — ISO-8601 UTC, e.g. "2026-06-10T07:30:00Z"
  }

No categorisation, clustering, or scoring happens here. Claude does all of
that in build.py. This file's only job is to get raw articles from feeds.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Any

import feedparser
import httpx
from dateutil import parser as dateparser

from config import SOURCES

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 DailyDigestBot/1.0"
)
_TIMEOUT        = 18.0
_RETRIES        = 2
_MAX_WORKERS    = 14
_WINDOW_HOURS   = 48    # only articles published within this window
_MAX_PER_FEED   = 25    # newest N items per feed

GUARDIAN_API    = "https://content.guardianapis.com/search"
HN_FRONTPAGE    = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=50"

ARTICLE_TYPES   = {"rss", "guardian", "hackernews"}


# ─── HTTP ─────────────────────────────────────────────────────────────────────

def _http_get(url: str, params: dict | None = None) -> bytes | None:
    headers = {"User-Agent": _UA, "Accept": "*/*"}
    last: Exception | None = None
    for attempt in range(_RETRIES + 1):
        try:
            r = httpx.get(url, params=params, headers=headers,
                          timeout=_TIMEOUT, follow_redirects=True)
            r.raise_for_status()
            return r.content
        except Exception as err:
            last = err
            if attempt < _RETRIES:
                time.sleep(1.0 * (attempt + 1))
    print(f"    ! GET failed: {url[:80]} ({type(last).__name__}: {last})")
    return None


# ─── Date parsing ─────────────────────────────────────────────────────────────

def _parse_date(entry: Any) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    for attr in ("published", "updated", "pubDate", "date"):
        val = getattr(entry, attr, None) if hasattr(entry, attr) else entry.get(attr)
        if val:
            try:
                dt = dateparser.parse(str(val))
                if dt:
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            except Exception:
                pass
    return None


def _to_iso(dt: datetime | None) -> str:
    if not dt:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _cutoff() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=_WINDOW_HOURS)


# ─── Per-type fetchers ────────────────────────────────────────────────────────

def _fetch_rss(source: dict) -> list[dict]:
    content = _http_get(source["url"])
    if content is None:
        return []
    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        return []
    cutoff = _cutoff()
    articles = []
    for entry in feed.entries[:_MAX_PER_FEED]:
        link  = entry.get("link", "").strip()
        title = (entry.get("title") or "").strip()
        if not link or not title:
            continue
        dt = _parse_date(entry)
        if dt and dt < cutoff:
            continue
        articles.append({
            "title":        title,
            "url":          link,
            "source":       source["name"],
            "paid_partner": source.get("paid_partner", False),
            "paywall_only": source.get("paywall_only", False),
            "lang":         source.get("lang", "en"),
            "published":    _to_iso(dt),
        })
    return articles


def _fetch_guardian(source: dict) -> list[dict]:
    api_key = os.environ.get("GUARDIAN_API_KEY", "test")
    p = source.get("params", {})
    params: dict[str, Any] = {
        "api-key":    api_key,
        "show-fields":"headline,trailText",
        "page-size":  p.get("page-size", 12),
        "order-by":   "newest",
    }
    if p.get("section"):
        params["section"] = str(p["section"]).replace(",", "|")
    if p.get("q"):
        params["q"] = p["q"]

    content = _http_get(GUARDIAN_API, params=params)
    if not content:
        return []
    try:
        results = json.loads(content)["response"]["results"]
    except Exception:
        return []

    cutoff = _cutoff()
    articles = []
    for item in results:
        pub = item.get("webPublicationDate", "")
        try:
            dt: datetime | None = dateparser.parse(pub)
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            dt = None
        if dt and dt < cutoff:
            continue
        fields = item.get("fields") or {}
        title = (fields.get("headline") or item.get("webTitle") or "").strip()
        url = item.get("webUrl", "")
        if not title or not url:
            continue
        articles.append({
            "title":        title,
            "url":          url,
            "source":       source["name"],
            "paid_partner": False,
            "paywall_only": False,
            "lang":         "en",
            "published":    _to_iso(dt),
        })
    return articles


def _fetch_hackernews(source: dict) -> list[dict]:
    min_score = source.get("params", {}).get("min_score", 100)
    content = _http_get(HN_FRONTPAGE)
    if not content:
        return []
    try:
        hits = json.loads(content)["hits"]
    except Exception:
        return []

    cutoff = _cutoff()
    articles = []
    for h in hits:
        if (h.get("points") or 0) < min_score:
            continue
        title = (h.get("title") or "").strip()
        if not title:
            continue
        url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
        ts = h.get("created_at_i")
        dt = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else None
        if dt and dt < cutoff:
            continue
        articles.append({
            "title":        title,
            "url":          url,
            "source":       "Hacker News",
            "paid_partner": False,
            "paywall_only": False,
            "lang":         "en",
            "published":    _to_iso(dt),
        })
    return articles


def _fetch_source(source: dict) -> list[dict]:
    """Dispatch by type. Never raises — failures return []."""
    try:
        stype = source.get("type")
        if stype == "rss":
            return _fetch_rss(source)
        if stype == "guardian":
            return _fetch_guardian(source)
        if stype == "hackernews":
            return _fetch_hackernews(source)
        return []   # widget-only types handled by widgets.py
    except Exception as err:
        print(f"    ! {source.get('name')} crashed: {type(err).__name__}: {err}")
        return []


# ─── Public API ───────────────────────────────────────────────────────────────

def fetch_all_articles() -> list[dict]:
    """
    Fetch all configured sources concurrently.
    Returns a deduplicated list of article dicts, newest first.
    """
    sources = [s for s in SOURCES if s.get("type") in ARTICLE_TYPES]
    print(f"  Fetching {len(sources)} sources (concurrent, up to {_MAX_WORKERS} workers)...")

    seen_urls: set[str] = set()
    all_articles: list[dict] = []

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_source, s): s for s in sources}
        for fut in as_completed(futures):
            src = futures[fut]
            batch = fut.result()
            fresh = 0
            for a in batch:
                url = a.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                all_articles.append(a)
                fresh += 1
            if fresh:
                print(f"    {src['name']}: {fresh}")

    # Sort newest first so Claude sees the most recent articles at the top
    all_articles.sort(key=lambda a: a.get("published", ""), reverse=True)
    print(f"  Total: {len(all_articles)} unique articles in last {_WINDOW_HOURS}h")
    return all_articles


if __name__ == "__main__":
    articles = fetch_all_articles()
    print(f"\n=== Sample (first 5) ===")
    for a in articles[:5]:
        pp = "💎" if a["paid_partner"] else ("🔒" if a["paywall_only"] else "")
        print(f"  [{a['source']}{pp}] [{a['lang'].upper()}] {a['title'][:70]}")
        print(f"    {a['published']}  {a['url'][:60]}")
