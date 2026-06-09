"""
Phase 2 — Fetch all articles from RSS feeds and APIs.

Public API:
    fetch_all_articles() -> list[Article]   # the main news pool (88 sources)
    fetch_feeds(sources) -> list[Article]    # reusable: Random / Learning pools

Each Article is a dict:
    {
      "id":              stable 16-char hex (sha1 of url),
      "title":           str,
      "url":             str,
      "summary":         str (plain text, tags stripped),
      "published":       ISO-8601 str (UTC),
      "source":          display name,
      "category":        category id (or "random" / "learning" for side pools),
      "is_subscription": bool,
      "image_url":       str | None,
      "language":        "sk" | "cs" | "en",
    }

Design notes:
  - HTTP via httpx with a browser-like UA (many feeds reject default agents).
  - feedparser parses bytes we fetched ourselves, so we control timeout/retry.
  - Each source is fetched in its own thread; one failure never aborts the run.
  - Widget-only source types (nhl, football_data, api_football) are SKIPPED here
    — they're handled in widgets.py (Phase 7), they don't produce article cards.
  - Exact-URL de-duplication only; same-story cross-source merge is Phase 3.
"""
from __future__ import annotations

import hashlib
import html
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Iterable

import feedparser
import httpx
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

import config

# ─── Tunables ────────────────────────────────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 DailyDigestBot/1.0"
)
HTTP_TIMEOUT       = 20.0   # seconds per request
HTTP_RETRIES       = 2      # extra attempts after the first
MAX_WORKERS        = 12     # concurrent source fetches
MAX_ITEMS_PER_FEED = 25     # newest N items per feed (keeps clustering cheap)
HN_MIN_SCORE       = 100    # HackerNews points floor (overridden by source param)

GUARDIAN_ENDPOINT  = "https://content.guardianapis.com/search"
HN_FRONTPAGE       = "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=50"

# Source types that produce article cards (everything else is a data widget)
ARTICLE_TYPES = {"rss", "guardian", "hackernews"}

_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


# ─── Low-level helpers ───────────────────────────────────────────────────────
def _make_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _clean_text(raw: str | None, limit: int = 600) -> str:
    """Strip HTML tags, unescape entities, collapse whitespace."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(" ")
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _parse_date(entry: Any) -> str:
    """Return an ISO-8601 UTC timestamp; fall back to 'now' if unparseable."""
    # feedparser pre-parses many date formats into a struct_time
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            try:
                return datetime(*st[:6], tzinfo=timezone.utc).isoformat()
            except (ValueError, TypeError):
                pass
    for key in ("published", "updated", "pubDate", "date"):
        val = entry.get(key)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            except (ValueError, TypeError, OverflowError):
                pass
    return datetime.now(timezone.utc).isoformat()


def _extract_image(entry: Any) -> str | None:
    """Find a usable image URL from common RSS image fields, else None."""
    # media:content / media:thumbnail
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if media and isinstance(media, list):
            url = media[0].get("url")
            if url:
                return url
    # <enclosure> or <link rel="enclosure" type="image/...">
    for link in entry.get("links", []) or []:
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
            if link.get("href"):
                return link["href"]
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("image") and enc.get("href"):
            return enc["href"]
    # first <img> inside summary or content HTML
    blobs: list[str] = []
    if entry.get("summary"):
        blobs.append(entry["summary"])
    for c in entry.get("content", []) or []:
        if c.get("value"):
            blobs.append(c["value"])
    for blob in blobs:
        m = _IMG_RE.search(blob)
        if m:
            return m.group(1)
    return None


def _http_get(url: str, params: dict | None = None) -> bytes | None:
    """GET with retries. Returns response bytes, or None on persistent failure."""
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    last_err: Exception | None = None
    for attempt in range(HTTP_RETRIES + 1):
        try:
            resp = httpx.get(
                url,
                params=params,
                headers=headers,
                timeout=HTTP_TIMEOUT,
                follow_redirects=True,
            )
            resp.raise_for_status()
            return resp.content
        except Exception as err:  # noqa: BLE001 — any network error is recoverable
            last_err = err
            if attempt < HTTP_RETRIES:
                time.sleep(1.0 * (attempt + 1))
    print(f"    ! GET failed: {url} ({type(last_err).__name__}: {last_err})")
    return None


# ─── Per-type fetchers ───────────────────────────────────────────────────────
def _fetch_rss(
    url: str,
    *,
    source_name: str,
    category: str,
    is_subscription: bool,
    language: str,
    limit: int = MAX_ITEMS_PER_FEED,
) -> list[dict[str, Any]]:
    """Fetch and parse a single RSS/Atom feed into Article dicts."""
    content = _http_get(url)
    if content is None:
        return []
    parsed = feedparser.parse(content)
    entries = parsed.entries[:limit] if parsed.entries else []
    out: list[dict[str, Any]] = []
    for e in entries:
        link = e.get("link") or ""
        title = _clean_text(e.get("title"), limit=300)
        if not link or not title:
            continue
        out.append({
            "id":              _make_id(link),
            "title":           title,
            "url":             link,
            "summary":         _clean_text(e.get("summary") or e.get("description")),
            "published":       _parse_date(e),
            "source":          source_name,
            "category":        category,
            "is_subscription": is_subscription,
            "image_url":       _extract_image(e),
            "language":        language,
        })
    return out


def _fetch_guardian(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch from the Guardian Content API. Needs GUARDIAN_API_KEY."""
    api_key = os.environ.get("GUARDIAN_API_KEY")
    if not api_key:
        print("    ! GUARDIAN_API_KEY not set — skipping Guardian source")
        return []
    p = source.get("params", {})
    params: dict[str, Any] = {
        "api-key":      api_key,
        "show-fields":  "thumbnail,trailText,byline",
        "page-size":    p.get("page-size", 15),
        "order-by":     "newest",
    }
    if p.get("section"):
        # Guardian uses pipe for OR across sections, config uses commas
        params["section"] = str(p["section"]).replace(",", "|")
    if p.get("q"):
        params["q"] = p["q"]

    content = _http_get(GUARDIAN_ENDPOINT, params=params)
    if content is None:
        return []
    import json
    try:
        results = json.loads(content)["response"]["results"]
    except (KeyError, ValueError):
        print("    ! Guardian: unexpected response shape")
        return []

    out: list[dict[str, Any]] = []
    for r in results:
        url = r.get("webUrl")
        title = _clean_text(r.get("webTitle"), limit=300)
        if not url or not title:
            continue
        fields = r.get("fields", {}) or {}
        out.append({
            "id":              _make_id(url),
            "title":           title,
            "url":             url,
            "summary":         _clean_text(fields.get("trailText")),
            "published":       r.get("webPublicationDate")
                               or datetime.now(timezone.utc).isoformat(),
            "source":          source["name"],
            "category":        source["category"],
            "is_subscription": source.get("is_subscription", False),
            "image_url":       fields.get("thumbnail"),
            "language":        "en",
        })
    return out


def _fetch_hackernews(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch HN front page via Algolia, filter by points >= min_score."""
    min_score = source.get("params", {}).get("min_score", HN_MIN_SCORE)
    content = _http_get(HN_FRONTPAGE)
    if content is None:
        return []
    import json
    try:
        hits = json.loads(content)["hits"]
    except (KeyError, ValueError):
        return []

    out: list[dict[str, Any]] = []
    for h in hits:
        points = h.get("points") or 0
        if points < min_score:
            continue
        title = _clean_text(h.get("title"), limit=300)
        if not title:
            continue
        obj_id = h.get("objectID")
        # External link if present, else the HN discussion page
        url = h.get("url") or f"https://news.ycombinator.com/item?id={obj_id}"
        ts = h.get("created_at_i")
        published = (
            datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            if ts else datetime.now(timezone.utc).isoformat()
        )
        out.append({
            "id":              _make_id(url),
            "title":           title,
            "url":             url,
            "summary":         f"{points} points · {h.get('num_comments', 0)} comments on Hacker News",
            "published":       published,
            "source":          source["name"],
            "category":        source["category"],
            "is_subscription": False,
            "image_url":       None,
            "language":        "en",
        })
    return out


def _fetch_source(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Dispatch a single source by its type. Never raises."""
    try:
        stype = source["type"]
        if stype == "rss":
            cat = source["category"]
            language = config.CATEGORIES.get(cat, {}).get("language", "en")
            return _fetch_rss(
                source["url"],
                source_name=source["name"],
                category=cat,
                is_subscription=source.get("is_subscription", False),
                language=language,
            )
        if stype == "guardian":
            return _fetch_guardian(source)
        if stype == "hackernews":
            return _fetch_hackernews(source)
        # widget-only types handled elsewhere
        return []
    except Exception as err:  # noqa: BLE001
        print(f"    ! {source.get('name')} crashed: {type(err).__name__}: {err}")
        return []


# ─── Public API ──────────────────────────────────────────────────────────────
def _dedupe(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop exact-URL duplicates, keeping first occurrence."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for a in articles:
        if a["url"] in seen:
            continue
        seen.add(a["url"])
        out.append(a)
    return out


def _fetch_concurrent(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fetch a list of sources concurrently and flatten the results."""
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_source, s): s for s in sources}
        for fut in as_completed(futures):
            src = futures[fut]
            items = fut.result()
            print(f"    {len(items):>3} · {src['name']} ({src['category']})")
            results.extend(items)
    return results


def fetch_all_articles() -> list[dict[str, Any]]:
    """Fetch the full news pool (config.SOURCES, article types only)."""
    sources = [s for s in config.SOURCES if s["type"] in ARTICLE_TYPES]
    print(f"  Fetching {len(sources)} article sources "
          f"({len(config.SOURCES) - len(sources)} widget sources skipped)...")
    articles = _fetch_concurrent(sources)
    deduped = _dedupe(articles)
    print(f"  {len(articles)} raw → {len(deduped)} after de-dup")
    return deduped


def fetch_feeds(
    sources: Iterable[dict[str, Any]],
    *,
    category: str = "random",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Reusable RSS fetch for side pools (Random, Learning).
    `sources` items only need {name, url}. Returns up to `limit` newest items
    per feed, tagged with the given category. Used by generate.py (Phase 8).
    """
    out: list[dict[str, Any]] = []
    src_list = list(sources)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                _fetch_rss,
                s["url"],
                source_name=s["name"],
                category=category,
                is_subscription=False,
                language="en",
                limit=limit,
            ): s
            for s in src_list
        }
        for fut in as_completed(futures):
            src = futures[fut]
            try:
                items = fut.result()
            except Exception as err:  # noqa: BLE001
                print(f"    ! {src['name']} crashed: {err}")
                items = []
            print(f"    {len(items):>3} · {src['name']}")
            out.extend(items)
    return _dedupe(out)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Fetch smoke test")
    ap.add_argument("--all", action="store_true", help="fetch all 88 sources")
    ap.add_argument("--cat", help="fetch only one category")
    args = ap.parse_args()

    if args.all:
        arts = fetch_all_articles()
    elif args.cat:
        subset = [s for s in config.SOURCES
                  if s["category"] == args.cat and s["type"] in ARTICLE_TYPES]
        arts = _dedupe(_fetch_concurrent(subset))
    else:
        # tiny default smoke test — a few reliable feeds
        smoke = [s for s in config.SOURCES if s["name"] in {
            "BBC World", "The Verge", "Kyiv Independent", "Denník N", "Ars Technica",
        }]
        arts = _dedupe(_fetch_concurrent(smoke))

    print(f"\nTOTAL: {len(arts)} articles")
    with_img = sum(1 for a in arts if a["image_url"])
    print(f"with image: {with_img}/{len(arts)}")
    for a in arts[:5]:
        print(f"\n  [{a['source']}] {a['title']}")
        print(f"    {a['published']} · img={'yes' if a['image_url'] else 'no'} · lang={a['language']}")
        print(f"    {a['summary'][:120]}")
