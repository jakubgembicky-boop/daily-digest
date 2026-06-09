"""
Phase 6 — Summarize and synthesize top-30 stories via Groq.

For each selected cluster:
  - per-source 2-sentence summary (in the source's original language)
  - 2-3 sentence cross-source synthesis
  - reading time estimate (~200 wpm)

CRITICAL: Slovak (sk) and Czech (cs) content is NEVER translated.
Summaries for sk/cs sources are written in the source's own language.

Rate-limited via llm.py (>= 2s between calls — Groq free: 30 RPM, 6000 TPM).
"""
from __future__ import annotations

import math
import uuid
from typing import Any

import llm
import config

_WORDS_PER_MINUTE = 200

# Two separate system prompts — one for English, one for native-language sources
_SYSTEM_EN = (
    "You are a sharp editorial assistant. Write crisp, factual summaries. "
    "Never add opinions. Never translate. Return only JSON."
)

_SYSTEM_NATIVE = (
    "Si skúsený novinársky asistent. Píš stručné, faktické zhrnutia. "
    "Nikdy nepridávaj vlastné názory. Nikdy neprekladaj. Odpovedaj iba v JSON. "
    "(Also handles Czech: Jsi zkušený novinářský asistent.)"
)

_SYNTHESIS_TEMPLATE = """\
Story topic: {topic}

Sources covering this story:
{source_block}

Task:
1. Write a "synthesis": 2-3 sentence overview of this story that captures the key \
facts and most important angle. Write in English (regardless of source languages).
2. For EACH source, write a "summary": exactly 2 sentences in the SAME LANGUAGE \
as that source's headline and text. Do NOT translate Slovak or Czech content.
3. Estimate "has_depth": true if there is meaningful analysis/context beyond \
the bare facts.

Return JSON exactly:
{{
  "synthesis": "...",
  "has_depth": true,
  "sources": [
    {{"source": "Source Name", "summary": "2 sentences in original language.", \
"angle": "news|analysis|opinion|data"}},
    ...
  ]
}}"""


def _estimate_seconds(text: str) -> int:
    words = len(text.split())
    return max(20, math.ceil(words / _WORDS_PER_MINUTE * 60))


def _build_source_block(articles: list[dict[str, Any]]) -> str:
    lines = []
    for a in articles:
        lang_note = f" [language: {a.get('language', 'en')}]"
        lines.append(
            f"- {a['source']}{lang_note}: \"{a['title']}\"\n"
            f"  Context: {a['summary'][:300]}"
        )
    return "\n".join(lines)


def _process_one(cluster: dict[str, Any]) -> dict[str, Any]:
    """Summarize and synthesize a single cluster. Returns a story dict."""
    articles = cluster["articles"]
    topic    = cluster["topic"]
    category = cluster["category"]

    # Choose system prompt based on whether ANY source is native-language
    langs = {a.get("language", "en") for a in articles}
    system = _SYSTEM_NATIVE if langs & {"sk", "cs"} else _SYSTEM_EN

    source_block = _build_source_block(articles)
    prompt = _SYNTHESIS_TEMPLATE.format(topic=topic, source_block=source_block)

    # Default fallback in case Groq fails
    result = {
        "synthesis": topic,
        "has_depth": False,
        "sources": [
            {
                "source":  a["source"],
                "summary": a["summary"][:200] or a["title"],
                "angle":   "news",
            }
            for a in articles
        ],
    }

    try:
        data = llm.chat_json(
            [
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=600,
        )
        result["synthesis"] = data.get("synthesis", topic)
        result["has_depth"] = bool(data.get("has_depth", False))
        # Match returned sources back to original articles
        returned = data.get("sources", [])
        if len(returned) == len(articles):
            result["sources"] = [
                {
                    "source":  articles[i]["source"],
                    "summary": s.get("summary", articles[i]["summary"][:200]),
                    "angle":   s.get("angle", "news"),
                }
                for i, s in enumerate(returned)
            ]
    except Exception as err:  # noqa: BLE001
        print(f"    ! process({topic[:40]}) failed: {err} — using fallback")

    # Estimate reading time from synthesis + all summaries
    all_text = result["synthesis"] + " ".join(
        s["summary"] for s in result["sources"]
    )
    est_seconds = _estimate_seconds(all_text)

    # Assemble final source list with article metadata
    full_sources = []
    for i, a in enumerate(articles):
        src_data = result["sources"][i] if i < len(result["sources"]) else {}
        full_sources.append({
            "source":          a["source"],
            "headline":        a["title"],
            "summary":         src_data.get("summary", a["summary"][:200]),
            "url":             a["url"],
            "angle":           src_data.get("angle", "news"),
            "is_subscription": a.get("is_subscription", False),
            "published":       a.get("published", ""),
            "image_url":       a.get("image_url"),
            "language":        a.get("language", "en"),
        })

    return {
        "id":                str(uuid.uuid4()),
        "cluster_id":        cluster["id"],
        "topic":             topic,
        "category":          category,
        "synthesis":         result["synthesis"],
        "has_depth":         result["has_depth"],
        "score":             cluster.get("score", 0.0),
        "importance":        cluster.get("importance", 3),
        "relevance":         cluster.get("relevance", 3),
        "is_breaking":       cluster.get("is_breaking", False),
        "is_top5":           cluster.get("is_top5", False),
        "estimated_seconds": est_seconds,
        "sources":           full_sources,
    }


def process_top_stories(
    scored_clusters: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Enrich each selected cluster with AI summaries and synthesis.
    Returns fully-processed story dicts matching the digest.json schema.
    """
    total = len(scored_clusters)
    processed: list[dict[str, Any]] = []
    for i, cluster in enumerate(scored_clusters, 1):
        print(f"  [{i:>2}/{total}] {cluster['category']:<9} {cluster['topic'][:55]}")
        story = _process_one(cluster)
        processed.append(story)
    return processed
