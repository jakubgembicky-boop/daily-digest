"""
Phase 5 — Monthly stats persistence.

Reads/writes monthly_stats.json in the repo root.
Resets to zero on the 1st of each month.
Tracks yesterday_categories for the no-consecutive-zero rule in score.py.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

_STATS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "monthly_stats.json"
)

_EMPTY_STATS_TEMPLATE: dict[str, Any] = {
    "month":                "",
    "total_stories":        0,
    "yesterday_categories": [],
    "by_category": {
        "slovakia": 0, "czechia": 0, "europe": 0, "war": 0,
        "sport":    0, "global": 0,  "tech":   0, "economy": 0,
        "hr":       0, "health": 0,  "random": 0, "learning": 0,
    },
}


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def read_stats() -> dict[str, Any]:
    """Load monthly_stats.json. Returns a fresh template if file is missing."""
    try:
        with open(_STATS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        # Ensure all expected keys exist (forward-compat if we add categories)
        for cat in _EMPTY_STATS_TEMPLATE["by_category"]:
            data.setdefault("by_category", {}).setdefault(cat, 0)
        data.setdefault("yesterday_categories", [])
        data.setdefault("total_stories", 0)
        return data
    except FileNotFoundError:
        stats = json.loads(json.dumps(_EMPTY_STATS_TEMPLATE))
        stats["month"] = _current_month()
        return stats


def reset_if_new_month(stats: dict[str, Any]) -> dict[str, Any]:
    """
    If stats['month'] doesn't match the current UTC month, reset all counters
    to zero and return the reset dict. Does NOT write to disk yet.
    """
    now_month = _current_month()
    if stats.get("month") == now_month:
        return stats
    print(f"  New month ({now_month}) — resetting monthly stats.")
    fresh = json.loads(json.dumps(_EMPTY_STATS_TEMPLATE))
    fresh["month"] = now_month
    return fresh


def write_stats(
    stats: dict[str, Any],
    selected_stories: list[dict[str, Any]],
) -> None:
    """
    Update stats with today's selected stories and write back to disk.
    - Increments by_category counts.
    - Increments total_stories.
    - Sets yesterday_categories to today's set of categories.
    """
    today_cats: list[str] = []
    for story in selected_stories:
        cat = story.get("category", "")
        if cat in stats["by_category"]:
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            stats["total_stories"] = stats.get("total_stories", 0) + 1
            today_cats.append(cat)

    stats["yesterday_categories"] = sorted(set(today_cats))

    with open(_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"  Stats written — total stories this month: {stats['total_stories']}")


if __name__ == "__main__":
    # Smoke test — round-trip without a GROQ key
    import tempfile, shutil, sys

    tmp = tempfile.mkdtemp()
    try:
        fake_path = os.path.join(tmp, "monthly_stats.json")
        import stats as _stats_mod
        _stats_mod._STATS_PATH = fake_path

        # 1. Missing file → fresh template
        s = read_stats()
        assert s["total_stories"] == 0

        # 2. New-month reset
        s["month"] = "2000-01"
        s2 = reset_if_new_month(s)
        assert s2["month"] == _current_month()
        assert s2["total_stories"] == 0

        # 3. write_stats increments correctly
        stories = [
            {"category": "tech"},
            {"category": "tech"},
            {"category": "slovakia"},
        ]
        _stats_mod.write_stats(s2, stories)
        s3 = _stats_mod.read_stats()
        assert s3["by_category"]["tech"] == 2, s3
        assert s3["by_category"]["slovakia"] == 1
        assert s3["total_stories"] == 3
        assert set(s3["yesterday_categories"]) == {"tech", "slovakia"}

        print("OK — stats round-trip verified.")
    finally:
        shutil.rmtree(tmp)
