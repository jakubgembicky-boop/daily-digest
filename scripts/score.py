"""
Phase 4 — Global scoring.

All clusters compete in one ranked pool — no per-category quotas.
The day's shape is driven by news importance, not artificial allocation.

Scoring formula (per spec):
    score = (importance * 0.45) + (relevance * 0.45) + (1.0 if is_breaking else 0)

    Monthly floor boost (applied per cluster before final sort):
        share = monthly_stats['by_category'][cat] / monthly_stats['total_stories']
        if share < 0.05:
            score += min((0.05 - share) * 10, 0.5)

Post-selection — no-consecutive-zero rule:
    If a category had 0 stories today AND yesterday, force its top-scoring cluster
    into the digest, displacing the lowest-ranked story currently selected.

Groq is asked to score ALL cluster headlines in a single batched call per
category, then one batched call for relevance (with user profile context).
This is still cheap — each call only sends short headlines.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

import llm
import config

# Max clusters to ask Groq to score at once (keeps prompt manageable)
_BATCH_SIZE = 40

_IMPORTANCE_SYSTEM = (
    "You are a senior news editor scoring story importance globally. "
    "Be concise and consistent. Return only JSON."
)

_IMPORTANCE_TEMPLATE = """\
Score each headline for global/regional NEWS IMPORTANCE (1-5, where 5=breaking major story, 1=minor or evergreen).
Also flag is_breaking=true only if this story must be read TODAY, not tomorrow.

Return JSON: {{"scores": [{{"index": 0, "importance": 3, "is_breaking": false}}, ...]}}

Headlines:
{headlines}"""

_RELEVANCE_SYSTEM = (
    "You are scoring news relevance for a specific reader. Return only JSON."
)

_RELEVANCE_TEMPLATE = """\
Reader profile: {profile}

Score each headline for RELEVANCE to this specific reader (1-5, where 5=directly relevant to their work/interests/location).

Return JSON: {{"scores": [{{"index": 0, "relevance": 3}}, ...]}}

Headlines:
{headlines}"""


def _score_batch_importance(
    clusters: list[dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    """Ask Groq to score importance + breaking for a batch of clusters."""
    headlines = "\n".join(
        f"{i}. {c['topic']} | {c['articles'][0]['title']}"
        for i, c in enumerate(clusters)
    )
    result: dict[int, dict[str, Any]] = {}
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _IMPORTANCE_SYSTEM},
                {"role": "user", "content": _IMPORTANCE_TEMPLATE.format(
                    headlines=headlines
                )},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        for item in data.get("scores", []):
            idx = item.get("index")
            if isinstance(idx, int) and 0 <= idx < len(clusters):
                result[idx] = {
                    "importance":  max(1, min(5, int(item.get("importance", 3)))),
                    "is_breaking": bool(item.get("is_breaking", False)),
                }
    except Exception as err:  # noqa: BLE001
        print(f"    ! importance scoring batch failed: {err}")
    return result


def _score_batch_relevance(
    clusters: list[dict[str, Any]],
) -> dict[int, int]:
    """Ask Groq to score relevance for a batch of clusters."""
    headlines = "\n".join(
        f"{i}. {c['topic']} | {c['articles'][0]['title']}"
        for i, c in enumerate(clusters)
    )
    result: dict[int, int] = {}
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _RELEVANCE_SYSTEM},
                {"role": "user", "content": _RELEVANCE_TEMPLATE.format(
                    profile=config.USER_PROFILE,
                    headlines=headlines,
                )},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        for item in data.get("scores", []):
            idx = item.get("index")
            if isinstance(idx, int) and 0 <= idx < len(clusters):
                result[idx] = max(1, min(5, int(item.get("relevance", 3))))
    except Exception as err:  # noqa: BLE001
        print(f"    ! relevance scoring batch failed: {err}")
    return result


def _floor_boost(
    score: float,
    category: str,
    monthly_stats: dict[str, Any],
) -> float:
    """Apply monthly floor boost if category is underrepresented."""
    total = monthly_stats.get("total_stories", 0)
    if total == 0:
        return score
    by_cat = monthly_stats.get("by_category", {})
    cat_count = by_cat.get(category, 0)
    share = cat_count / total
    if share < config.MONTHLY_FLOOR_THRESHOLD:
        boost = min(
            (config.MONTHLY_FLOOR_THRESHOLD - share) * 10,
            config.MONTHLY_FLOOR_MAX_BOOST,
        )
        score += boost
    return score


def score_clusters(
    clusters: list[dict[str, Any]],
    monthly_stats: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Score all clusters globally. Returns top TARGET_STORIES list.
    Each item has: all cluster fields + score, importance, relevance,
    is_breaking, is_top5 fields.
    """
    if not clusters:
        return []

    total = len(clusters)
    print(f"  Scoring {total} clusters in batches of {_BATCH_SIZE}...")

    # ── Build flat list for batched scoring ───────────────────────────────────
    all_imp:  dict[int, dict[str, Any]] = {}
    all_rel:  dict[int, int] = {}

    for batch_start in range(0, total, _BATCH_SIZE):
        batch = clusters[batch_start: batch_start + _BATCH_SIZE]
        # Re-index within batch; translate back to global index
        imp = _score_batch_importance(batch)
        rel = _score_batch_relevance(batch)
        for local_idx, v in imp.items():
            all_imp[batch_start + local_idx] = v
        for local_idx, v in rel.items():
            all_rel[batch_start + local_idx] = v

    # ── Compute raw scores ────────────────────────────────────────────────────
    scored: list[dict[str, Any]] = []
    for i, cluster in enumerate(clusters):
        imp_data   = all_imp.get(i, {})
        importance = imp_data.get("importance", 3)
        is_breaking = imp_data.get("is_breaking", False)
        relevance  = all_rel.get(i, 3)

        raw_score = (
            importance  * config.SCORE_IMPORTANCE_WEIGHT
            + relevance * config.SCORE_RELEVANCE_WEIGHT
            + (config.SCORE_BREAKING_BONUS if is_breaking else 0)
        )
        # Monthly floor boost BEFORE final sort (max +0.5, never overrides breaking)
        boosted_score = _floor_boost(raw_score, cluster["category"], monthly_stats)

        scored.append({
            **cluster,
            "importance":   importance,
            "relevance":    relevance,
            "is_breaking":  is_breaking,
            "score":        round(boosted_score, 4),
        })

    # ── Sort globally, take top TARGET_STORIES ────────────────────────────────
    scored.sort(key=lambda c: c["score"], reverse=True)
    selected = scored[: config.TARGET_STORIES]

    # ── No-consecutive-zero rule (post-selection) ─────────────────────────────
    yesterday_cats = set(monthly_stats.get("yesterday_categories", []))
    selected_cats  = {c["category"] for c in selected}

    # Categories with 0 today AND 0 yesterday
    zero_zero_cats = [
        cat for cat in config.CATEGORIES
        if cat not in selected_cats and cat not in yesterday_cats
        and cat not in ("random", "learning")  # these are always generated separately
    ]
    if zero_zero_cats:
        # For each such category, find its top-scoring unselected cluster
        unselected = [c for c in scored if c not in selected]
        by_cat: dict[str, list] = defaultdict(list)
        for c in unselected:
            by_cat[c["category"]].append(c)

        for cat in zero_zero_cats:
            if cat not in by_cat:
                continue
            best = max(by_cat[cat], key=lambda c: c["score"])
            # Displace the lowest-ranked currently-selected story
            selected.sort(key=lambda c: c["score"], reverse=True)
            displaced = selected.pop()
            selected.append(best)
            print(f"    no-zero rule: forced '{cat}' story in "
                  f"(displaced score={displaced['score']:.2f})")

    # ── Final sort + mark top 5 ────────────────────────────────────────────────
    selected.sort(key=lambda c: c["score"], reverse=True)
    top5_ids = {c["id"] for c in selected[:5]}
    for c in selected:
        c["is_top5"] = c["id"] in top5_ids

    cats_in = sorted({c["category"] for c in selected})
    print(f"  Selected {len(selected)} stories across {len(cats_in)} categories: "
          f"{', '.join(cats_in)}")
    return selected
