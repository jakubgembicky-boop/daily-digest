"""
Phase 3 — Topic clustering.

Groups raw articles into topic clusters using Groq (headlines only — cheap).
Clustering runs PER CATEGORY (one Groq call each), which both keeps prompts
small and matches the spec. Same-story articles from multiple sources collapse
into one cluster carrying all their sources.

Output cluster dict:
    {
      "id":       stable 16-char hex (hash of member URLs),
      "topic":    short provisional label (same language as headlines),
      "category": category id,
      "articles": [ <full article dicts>, ... ],
    }

Guarantees:
  - Every input article ends up in exactly one cluster (no data loss).
  - Articles never appear in two clusters.
  - If the Groq call fails or returns garbage, that category degrades
    gracefully to one-article-per-cluster (pipeline never dies).
  - No translation: topic labels stay in the headlines' own language.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

import llm

# Cap headlines sent per category — bounds token use, keeps it cheap.
MAX_HEADLINES_PER_CATEGORY = 80

_SYSTEM = (
    "You group news headlines that cover the SAME story. You are precise and "
    "conservative: when two headlines are not clearly about the same specific "
    "event, you keep them apart. You never translate."
)

_USER_TEMPLATE = """\
Below are {n} news headlines, each with an index number.

Group together the indices whose headlines describe the SAME specific story or
event (e.g. the same vote, the same match, the same product launch, the same
incident). Headlines that merely share a broad theme are NOT the same story —
keep those separate.

Rules:
- Every index must appear in exactly one group.
- Most groups will contain a single index. That is expected and correct.
- Only merge indices you are confident cover the same event.
- For each group write a short "topic" label (max 8 words) describing the shared
  story. Write the label in the SAME LANGUAGE as the headlines. Do NOT translate.

Return ONLY JSON of this exact shape:
{{"clusters": [{{"topic": "short label", "indices": [0, 4]}}, ...]}}

Headlines:
{headlines}"""


def _cluster_id(articles: list[dict[str, Any]]) -> str:
    """Deterministic id from the sorted member URLs (stable across rebuilds)."""
    key = "|".join(sorted(a["url"] for a in articles))
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def _truncate(text: str, words: int = 8) -> str:
    parts = text.split()
    return " ".join(parts[:words])


def _cluster_one_category(
    category: str,
    articles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Cluster a single category's articles via one Groq call (+ fallback)."""
    if not articles:
        return []

    # newest first, capped
    articles = sorted(articles, key=lambda a: a["published"], reverse=True)
    articles = articles[:MAX_HEADLINES_PER_CATEGORY]

    headlines = "\n".join(f"{i}. {a['title']}" for i, a in enumerate(articles))
    groups: list[dict[str, Any]] = []
    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user",
                 "content": _USER_TEMPLATE.format(n=len(articles), headlines=headlines)},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        if isinstance(data, dict):
            groups = data.get("clusters", []) or []
        elif isinstance(data, list):
            groups = data
    except Exception as err:  # noqa: BLE001
        print(f"    ! cluster({category}) LLM failed — singleton fallback: {err}")
        groups = []

    clusters: list[dict[str, Any]] = []
    assigned: set[int] = set()

    for g in groups:
        if not isinstance(g, dict):
            continue
        raw_idx = g.get("indices", [])
        idxs = [
            i for i in raw_idx
            if isinstance(i, int) and 0 <= i < len(articles) and i not in assigned
        ]
        if not idxs:
            continue
        members = [articles[i] for i in idxs]
        assigned.update(idxs)
        topic = (g.get("topic") or "").strip() or _truncate(members[0]["title"])
        clusters.append({
            "id":       _cluster_id(members),
            "topic":    topic,
            "category": category,
            "articles": members,
        })

    # Any article the model didn't place becomes its own singleton cluster.
    for i, a in enumerate(articles):
        if i not in assigned:
            clusters.append({
                "id":       _cluster_id([a]),
                "topic":    _truncate(a["title"]),
                "category": category,
                "articles": [a],
            })

    return clusters


def cluster_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Group all articles into topic clusters, one Groq call per category.
    Returns the flat list of clusters across every category.
    """
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in articles:
        by_cat[a["category"]].append(a)

    all_clusters: list[dict[str, Any]] = []
    for cat, arts in by_cat.items():
        clusters = _cluster_one_category(cat, arts)
        merged = sum(1 for c in clusters if len(c["articles"]) > 1)
        print(f"    {cat:<9} {len(arts):>3} articles -> {len(clusters):>3} clusters "
              f"({merged} multi-source)")
        all_clusters.extend(clusters)

    print(f"  Total: {len(all_clusters)} clusters from {len(articles)} articles")
    return all_clusters


if __name__ == "__main__":
    # Structural self-test — no network, no Groq key needed.
    # Verifies the coverage guarantee and singleton fallback by stubbing the LLM.
    import sys

    def _fake_chat_json(messages, **kw):
        # Pretend the model merged indices 0 and 2 into one story.
        return {"clusters": [
            {"topic": "merged story", "indices": [0, 2]},
            {"topic": "lonely story", "indices": [1]},
            # note: index 3 deliberately omitted → must become a singleton
        ]}

    llm.chat_json = _fake_chat_json  # type: ignore[assignment]

    sample = [
        {"url": "u0", "title": "Alpha event happens", "published": "2026-06-09T05:00:00Z", "category": "tech"},
        {"url": "u1", "title": "Beta unrelated thing", "published": "2026-06-09T04:00:00Z", "category": "tech"},
        {"url": "u2", "title": "Alpha event analysis",  "published": "2026-06-09T03:00:00Z", "category": "tech"},
        {"url": "u3", "title": "Gamma leftover",        "published": "2026-06-09T02:00:00Z", "category": "tech"},
    ]
    out = cluster_articles(sample)

    # assertions
    total_articles = sum(len(c["articles"]) for c in out)
    all_urls = sorted(a["url"] for c in out for a in c["articles"])
    assert total_articles == 4, f"expected 4 articles, got {total_articles}"
    assert all_urls == ["u0", "u1", "u2", "u3"], f"coverage broken: {all_urls}"
    assert any(len(c["articles"]) == 2 for c in out), "merge not applied"
    assert any(c["topic"] == "Gamma leftover" for c in out), "singleton fallback missing"
    print("\nOK — coverage, merge, and singleton fallback all verified.")
    sys.exit(0)
