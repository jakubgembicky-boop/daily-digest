"""
Phase 9 — Assemble digest.json and archive it.

Takes all processed data and writes two files:
  pwa/digest.json                 — the "latest" file the PWA defaults to
  pwa/digests/YYYY-MM-DD.json     — dated archive for the calendar history view

digest.json schema matches the spec exactly. Stories are grouped by category;
random and learning each appear as their own single-story category.
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

_PWA_DIR      = os.path.join(os.path.dirname(__file__), "..", "pwa")
_DIGESTS_DIR  = os.path.join(_PWA_DIR, "digests")
_DIGEST_LATEST = os.path.join(_PWA_DIR, "digest.json")

_WORDS_PER_MINUTE = 200


def _total_read_minutes(stories: list[dict[str, Any]]) -> int:
    total_seconds = sum(s.get("estimated_seconds", 60) for s in stories)
    return max(1, math.ceil(total_seconds / 60))


def _category_meta(cat: str) -> dict[str, str]:
    from config import CATEGORIES
    m = CATEGORIES.get(cat, {})
    return {
        "label":  m.get("label",  cat.title()),
        "emoji":  m.get("emoji",  "📰"),
        "accent": m.get("accent", "#6B7280"),
    }


def build_digest(
    stories: list[dict[str, Any]],
    sport_widget:   dict[str, Any],
    market_widget:  dict[str, Any],
    random_item:    dict[str, Any],
    learning_item:  dict[str, Any],
) -> dict[str, Any]:
    """Assemble and return the full digest dict."""
    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # All stories including special cards (for read-time + top5)
    all_stories = stories + [random_item, learning_item]
    top5_ids    = [s["id"] for s in stories if s.get("is_top5")]

    # Group main stories by category
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in stories:
        by_cat[s["category"]].append(s)

    # Build category blocks
    categories: dict[str, Any] = {}
    for cat, cat_stories in by_cat.items():
        meta  = _category_meta(cat)
        block: dict[str, Any] = {
            **meta,
            "story_count": len(cat_stories),
            "stories":     cat_stories,
        }
        if cat == "sport":
            block["scoreboard"] = sport_widget
        if cat == "economy":
            block["market_snapshot"] = market_widget
        categories[cat] = block

    # Random and Learning always present (even if empty fallback)
    for item in (random_item, learning_item):
        cat  = item["category"]
        meta = _category_meta(cat)
        categories[cat] = {
            **meta,
            "story_count": 1,
            "stories":     [item],
        }

    # If sport/economy had no scored stories, still attach widget data
    if "sport" not in categories:
        meta = _category_meta("sport")
        categories["sport"] = {
            **meta,
            "story_count": 0,
            "stories":     [],
            "scoreboard":  sport_widget,
        }
    if "economy" not in categories:
        meta = _category_meta("economy")
        categories["economy"] = {
            **meta,
            "story_count":    0,
            "stories":        [],
            "market_snapshot": market_widget,
        }

    return {
        "generated_at":          date_str,
        "date":                  now.strftime("%Y-%m-%d"),
        "total_stories":         len(stories),
        "estimated_read_minutes": _total_read_minutes(all_stories),
        "top5_ids":              top5_ids,
        "categories":            categories,
    }


def write_digest(digest: dict[str, Any]) -> None:
    """Write digest.json (latest) and pwa/digests/YYYY-MM-DD.json (archive)."""
    os.makedirs(_DIGESTS_DIR, exist_ok=True)

    payload = json.dumps(digest, indent=2, ensure_ascii=False)

    # Latest
    with open(_DIGEST_LATEST, "w", encoding="utf-8") as f:
        f.write(payload)
    print(f"  Written: {_DIGEST_LATEST}")

    # Dated archive
    dated = os.path.join(_DIGESTS_DIR, f"{digest['date']}.json")
    with open(dated, "w", encoding="utf-8") as f:
        f.write(payload)
    print(f"  Archived: {dated}")
