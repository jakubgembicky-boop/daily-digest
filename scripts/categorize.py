"""
Phase 3.5 — Topic-based re-categorization.

The fetch step tags every article with its SOURCE's category. That means a story
about Iran reported by a Slovak outlet (Denník N) is tagged "slovakia", and an
Israeli-airstrike story from a Czech outlet (ČT24) is tagged "czechia". That is
wrong: the reader expects categories to reflect what a story is ABOUT, not who
reported it.

This step runs AFTER clustering and BEFORE scoring. It asks Groq to assign each
cluster the best topic category from the fixed 12-set, with one hard rule:

    slovakia / czechia are ONLY for stories primarily about Slovak / Czech
    DOMESTIC affairs. International news from a Slovak / Czech source must be
    categorized by its actual topic (war, europe, global, economy, …).

We never translate: only the `category` label changes; topic text and language
tags are untouched.

Public API:
    categorize_clusters(clusters) -> list[dict]   # same clusters, fixed category
"""
from __future__ import annotations

from typing import Any

import llm
import config

_BATCH_SIZE = 40

# The categories the model may assign (random/learning are generated separately).
_ALLOWED = [
    "slovakia", "czechia", "europe", "war", "sport",
    "global", "tech", "economy", "hr", "health",
]

_SYSTEM = (
    "You are a news desk editor who files each story under the single best topic "
    "category. You judge a story by WHAT IT IS ABOUT, never by which outlet "
    "published it. You return only JSON."
)

_GUIDE = """\
Categories and their exact meaning:
- slovakia : ONLY stories primarily about Slovak DOMESTIC affairs — Slovak politics,
             economy, society, courts, culture happening in/about Slovakia itself.
- czechia  : ONLY stories primarily about Czech DOMESTIC affairs — Czech politics,
             economy, society, courts, culture happening in/about Czechia itself.
- war      : the Russia–Ukraine war and other active armed conflicts (Middle East
             military strikes, etc.).
- europe   : EU-level politics, European defense & security, cross-border European
             affairs that are NOT specifically Slovak/Czech domestic news.
- sport    : any sport — football, hockey, tennis, the World Cup, results, transfers.
- global   : major world news that doesn't fit elsewhere — US politics, Middle East
             diplomacy, Asia, international organisations, world-shaping events.
- tech     : technology, AI, software, gadgets, computing, space & hard science.
- economy  : markets, business, finance, trade, central banks, macroeconomics.
- hr       : management, leadership, the workplace, careers, organisational behaviour.
- health   : health, medicine, fitness, nutrition, mental health, wellbeing.

CRITICAL RULE: A Slovak or Czech outlet reporting on Iran, Ukraine, the EU, the US,
markets or sport is NOT 'slovakia'/'czechia'. File it under the real topic. Use
'slovakia'/'czechia' ONLY when the story itself is about domestic Slovak/Czech matters.
"""

_TEMPLATE = """\
{guide}

Assign exactly one category to each story below, by its topic.

Return ONLY JSON of this shape:
{{"items": [{{"index": 0, "category": "war"}}, ...]}}

Stories (index | current-source-tag | topic | headline):
{rows}"""


def _categorize_batch(clusters: list[dict[str, Any]]) -> dict[int, str]:
    """Ask Groq for the best topic category of each cluster in the batch."""
    rows = "\n".join(
        f"{i} | {c.get('category','?')} | {c.get('topic','')[:80]} | "
        f"{c['articles'][0]['title'][:90]}"
        for i, c in enumerate(clusters)
    )
    out: dict[int, str] = {}
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _TEMPLATE.format(guide=_GUIDE, rows=rows)},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        for item in data.get("items", []):
            idx = item.get("index")
            cat = str(item.get("category", "")).strip().lower()
            if isinstance(idx, int) and 0 <= idx < len(clusters) and cat in _ALLOWED:
                out[idx] = cat
    except Exception as err:  # noqa: BLE001
        print(f"    ! categorize batch failed: {err} — keeping source tags")
    return out


def categorize_clusters(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Re-label every cluster with its real topic category. Mutates and returns the
    same list. On any failure the original source-derived category is kept, so the
    pipeline never loses data.
    """
    if not clusters:
        return clusters

    total = len(clusters)
    print(f"  Re-categorizing {total} clusters by topic (batches of {_BATCH_SIZE})...")

    changed = 0
    for start in range(0, total, _BATCH_SIZE):
        batch = clusters[start: start + _BATCH_SIZE]
        mapping = _categorize_batch(batch)
        for local_idx, new_cat in mapping.items():
            cluster = batch[local_idx]
            if new_cat != cluster.get("category"):
                changed += 1
            cluster["category"] = new_cat

    # Report the resulting distribution so the log makes the effect visible.
    dist: dict[str, int] = {}
    for c in clusters:
        dist[c["category"]] = dist.get(c["category"], 0) + 1
    summary = ", ".join(f"{k}:{v}" for k, v in sorted(dist.items()))
    print(f"    {changed}/{total} clusters re-labeled. Distribution: {summary}")
    return clusters


if __name__ == "__main__":
    # Offline self-test — stub the LLM, verify relabel + fallback safety.
    def _fake(messages, **kw):
        return {"items": [
            {"index": 0, "category": "war"},      # Slovak source, Iran story -> war
            {"index": 1, "category": "slovakia"}, # genuine domestic -> stays
            {"index": 2, "category": "nonsense"}, # invalid -> ignored, keeps original
        ]}
    llm.chat_json = _fake  # type: ignore[assignment]

    sample = [
        {"category": "slovakia", "topic": "Iran útok", "articles": [{"title": "Iran strikes back"}]},
        {"category": "slovakia", "topic": "Fico vláda", "articles": [{"title": "Fico o rozpočte"}]},
        {"category": "tech",     "topic": "Chip news",  "articles": [{"title": "New chip"}]},
    ]
    categorize_clusters(sample)
    assert sample[0]["category"] == "war", sample[0]
    assert sample[1]["category"] == "slovakia", sample[1]
    assert sample[2]["category"] == "tech", sample[2]  # invalid kept original
    print("OK — re-categorization + fallback verified.")
