"""
Phase 8 — Random item selection + Learning article selection.

Both are generated AFTER the main digest is built.
Neither goes through the scoring pipeline.

Random:
  - Fetches 5 articles from each RANDOM_SOURCES source
  - Reads monthly_stats to bias selection AWAY from over-represented categories
  - Groq picks the single most surprising article + writes a hook sentence

Learning:
  - Fetches articles from LEARNING_SOURCES (HBR, Guardian Long Read, Aeon, ...)
  - Evergreen OK — no recency filter
  - day-of-year domain acts as a soft steering hint (not a hard filter)
  - Groq selects the single best "explains a concept clearly" article
  - Returns a real article URL + hook + short synthesis (like Random, not AI prose)
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any

import llm
import config
from fetch import fetch_feeds

_ITEMS_PER_RANDOM_SOURCE  = 5
_ITEMS_PER_LEARNING_SOURCE = 6


# ─── Random ──────────────────────────────────────────────────────────────────

_RANDOM_SYSTEM = (
    "You select the single most surprising, mind-expanding article for a reader. "
    "Be decisive. Return only JSON."
)

_RANDOM_TEMPLATE = """\
Reader context: {profile}

The reader usually reads about: {over_represented}
Today's main news themes: {themes}

Below are {n} articles from curiosity/science/culture sources.
Pick the ONE article most likely to genuinely surprise this reader.

Criteria (in order):
1. Completely outside their usual topics
2. Genuinely interesting — not clickbait
3. Specific and substantive (not vague or generic)
4. Avoid technology, politics, business, sport

Return JSON:
{{
  "index": <int>,
  "hook": "<one punchy sentence: why this is surprising or fascinating>"
}}

Articles:
{articles}"""


def _over_represented_categories(monthly_stats: dict[str, Any]) -> str:
    """Return a human-readable list of the top 3 most-read categories."""
    by_cat = monthly_stats.get("by_category", {})
    total  = monthly_stats.get("total_stories", 1) or 1
    ranked = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
    top3   = [cat for cat, _ in ranked[:3] if cat not in ("random", "learning")]
    return ", ".join(top3) if top3 else "general news"


def generate_random(
    monthly_stats: dict[str, Any],
    top_story_topics: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch Random pool, let Groq pick the most surprising article."""
    print("  Fetching Random source pool...")
    articles = fetch_feeds(
        config.RANDOM_SOURCES,
        category="random",
        limit=_ITEMS_PER_RANDOM_SOURCE,
    )
    if not articles:
        return _random_fallback()

    over_rep = _over_represented_categories(monthly_stats)
    themes   = ", ".join((top_story_topics or [])[:8]) or "general world news"
    article_list = "\n".join(
        f"{i}. [{a['source']}] {a['title']} — {a['summary'][:150]}"
        for i, a in enumerate(articles)
    )

    chosen_idx  = random.randrange(len(articles))   # fallback: random, not always 0
    hook        = "A fascinating story from outside your usual reading."
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _RANDOM_SYSTEM},
                {"role": "user",   "content": _RANDOM_TEMPLATE.format(
                    profile        = config.USER_PROFILE,
                    over_represented = over_rep,
                    themes         = themes,
                    n              = len(articles),
                    articles       = article_list,
                )},
            ],
            temperature=0.5,
            max_tokens=200,
        )
        idx  = int(data.get("index", 0))
        hook = data.get("hook", hook)
        if 0 <= idx < len(articles):
            chosen_idx = idx
    except Exception as err:  # noqa: BLE001
        print(f"    ! Random selection failed: {err} — using random article")

    a = articles[chosen_idx]
    return {
        "id":                str(uuid.uuid4()),
        "topic":             a["title"],
        "category":          "random",
        "synthesis":         a["summary"][:400] or a["title"],
        "hook":              hook,
        "has_depth":         True,
        "is_breaking":       False,
        "is_top5":           False,
        "score":             0.0,
        "estimated_seconds": 90,
        "sources": [{
            "source":          a["source"],
            "headline":        a["title"],
            "summary":         hook,
            "url":             a["url"],
            "angle":           "feature",
            "is_subscription": False,
            "published":       a.get("published", ""),
            "image_url":       a.get("image_url"),
            "language":        "en",
        }],
    }


def _random_fallback() -> dict[str, Any]:
    return {
        "id":                str(uuid.uuid4()),
        "topic":             "No surprise today",
        "category":          "random",
        "synthesis":         "Random sources could not be fetched today.",
        "hook":              "Check back tomorrow.",
        "has_depth":         False,
        "is_breaking":       False,
        "is_top5":           False,
        "score":             0.0,
        "estimated_seconds": 0,
        "sources":           [],
    }


# ─── Learning ─────────────────────────────────────────────────────────────────

_LEARNING_SYSTEM = (
    "You select the single best 'explains a concept clearly' article for a curious reader. "
    "Prefer pieces that teach something concrete, not opinion pieces. Return only JSON."
)

_LEARNING_TEMPLATE = """\
Reader profile: {profile}
Today's domain hint (soft preference, not a hard filter): {domain}
Today's main news themes: {themes}

Below are {n} articles from quality explainer/ideas sources.
Pick the ONE article that best teaches an interesting concept the reader likely doesn't know well.

Criteria (in order):
1. Explains a specific concept clearly (behavioral, scientific, philosophical, historical...)
2. Evergreen is fine — does NOT need to be recent news
3. Genuinely useful or mind-expanding for a curious generalist
4. Prefer the domain hint if a good match exists; ignore it if nothing fits well

Return JSON:
{{
  "index": <int>,
  "hook": "<one sentence: what concept this teaches and why it's worth reading>",
  "synthesis": "<2-3 sentences summarising the key insight in plain language>"
}}

Articles:
{articles}"""


def _today_domain() -> str:
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    return config.LEARNING_DOMAINS[day_of_year % len(config.LEARNING_DOMAINS)]


def generate_learning(
    top_story_topics: list[str] | None = None,
    exclude_urls: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch Learning pool, let Groq pick the best concept-explaining article."""
    print("  Fetching Learning source pool...")
    articles = fetch_feeds(
        config.LEARNING_SOURCES,
        category="learning",
        limit=_ITEMS_PER_LEARNING_SOURCE,
    )
    # Remove any URLs already picked by Random (avoids duplicate cards)
    if exclude_urls:
        _excl = set(exclude_urls)
        articles = [a for a in articles if a.get("url") not in _excl]
    if not articles:
        return _learning_fallback()

    domain = _today_domain()
    themes = ", ".join((top_story_topics or [])[:8]) or "general world news"
    article_list = "\n".join(
        f"{i}. [{a['source']}] {a['title']} — {a['summary'][:150]}"
        for i, a in enumerate(articles)
    )

    chosen_idx = random.randrange(len(articles))   # fallback: random, not always 0
    hook       = "An interesting concept worth understanding."
    synthesis  = ""
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _LEARNING_SYSTEM},
                {"role": "user",   "content": _LEARNING_TEMPLATE.format(
                    profile  = config.USER_PROFILE,
                    domain   = domain,
                    themes   = themes,
                    n        = len(articles),
                    articles = article_list,
                )},
            ],
            temperature=0.4,
            max_tokens=300,
        )
        idx       = int(data.get("index", 0))
        hook      = data.get("hook", hook)
        synthesis = data.get("synthesis", "")
        if 0 <= idx < len(articles):
            chosen_idx = idx
    except Exception as err:  # noqa: BLE001
        print(f"    ! Learning selection failed: {err} — using random article")

    a = articles[chosen_idx]
    return {
        "id":                str(uuid.uuid4()),
        "topic":             a["title"],
        "category":          "learning",
        "domain":            domain,
        "synthesis":         synthesis or a["summary"][:400] or a["title"],
        "hook":              hook,
        "has_depth":         True,
        "is_breaking":       False,
        "is_top5":           False,
        "score":             0.0,
        "estimated_seconds": 120,
        "sources": [{
            "source":          a["source"],
            "headline":        a["title"],
            "summary":         synthesis or hook,
            "url":             a["url"],
            "angle":           "analysis",
            "is_subscription": a.get("is_subscription", False),
            "published":       a.get("published", ""),
            "image_url":       a.get("image_url"),
            "language":        "en",
        }],
    }


def _learning_fallback() -> dict[str, Any]:
    return {
        "id":                str(uuid.uuid4()),
        "topic":             "No learning today",
        "category":          "learning",
        "domain":            _today_domain(),
        "synthesis":         "Learning sources could not be fetched today.",
        "hook":              "Check back tomorrow.",
        "has_depth":         False,
        "is_breaking":       False,
        "is_top5":           False,
        "score":             0.0,
        "estimated_seconds": 0,
        "sources":           [],
    }
