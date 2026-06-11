"""
Daily Digest — Claude Routine orchestrator.

Pipeline:
  1. Fetch articles            (fetch.py)
  2. Fetch trending data       (trending.py)
  3. Build sport + market      (widgets.py)
  4. Call Claude               (Anthropic API — ANTHROPIC_API_KEY env var)
  5. Parse + validate JSON
  6. Merge widget data
  7. Write pwa/data/digest.json + archive copy

Usage:
  python build.py              # full run
  python build.py --dry-run    # fetch only, no Claude call (test sources)
  python build.py --model claude-haiku-4-5   # override model
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

# Ensure scripts/ is on the path when invoked directly
sys.path.insert(0, str(Path(__file__).parent))

from fetch    import fetch_all_articles
from trending import fetch_trending
from widgets  import build_sport_widget, build_market_snapshot
from config   import USER_PROFILE, TRENDING_WILDCARD_MIN_SCORE

_SCRIPTS = Path(__file__).parent
_PWA     = _SCRIPTS.parent / "pwa"
_PROMPT  = _SCRIPTS / "prompt.md"

# Default model — sonnet gives quality summaries at a reasonable cost
_DEFAULT_MODEL = "claude-sonnet-4-6"
# Full digest JSON runs ~10-14K tokens; give generous headroom.
_MAX_TOKENS    = 32000
# Trim article list to this many chars to avoid blowing the context window
_MAX_ARTICLES_CHARS = 120_000


def _format_articles(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        tags = []
        if a.get("paid_partner"):
            tags.append("[PAID_PARTNER]")
        if a.get("paywall_only"):
            tags.append("[PAYWALL]")
        lang = a.get("lang", "en")
        if lang in ("sk", "cs"):
            tags.append(f"[{lang.upper()}]")
        tag_str    = " ".join(tags)
        source_str = f"{a['source']}{(' ' + tag_str) if tag_str else ''}"
        lines.append(
            f"{i}. [{source_str}] {a['title']}\n"
            f"   URL: {a['url']}\n"
            f"   Published: {a.get('published', 'unknown')}"
        )
    text = "\n\n".join(lines)
    if len(text) > _MAX_ARTICLES_CHARS:
        text = text[:_MAX_ARTICLES_CHARS] + "\n\n[... list trimmed for length ...]"
    return text


def _format_trending(trending: list[dict]) -> str:
    if not trending:
        return "No geo-relevant trending stories found today."
    lines = []
    for t in trending[:25]:
        lines.append(
            f"- r/{t['subreddit']} (score {t['score']:,}): {t['title']}\n"
            f"  URL: {t['url']}"
        )
    return "\n".join(lines)


def _build_prompt(articles: list[dict], trending: list[dict], today: str) -> str:
    template = _PROMPT.read_text(encoding="utf-8")
    return (
        template
        .replace("{{DATE}}", today)
        .replace("{{USER_PROFILE}}", USER_PROFILE)
        .replace("{{ARTICLES}}", _format_articles(articles))
        .replace("{{TRENDING}}", _format_trending(trending))
        .replace("{{WILDCARD_MIN_SCORE}}", str(TRENDING_WILDCARD_MIN_SCORE))
    )


def _extract_json(raw: str) -> str:
    """Strip markdown code fences if Claude wrapped the output."""
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        content = parts[1] if len(parts) > 1 else raw
        if content.startswith("json"):
            content = content[4:]
        return content.strip()
    return raw


def _call_claude(prompt: str, model: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # Stream — required for large max_tokens to avoid HTTP timeouts
    with client.messages.stream(
        model=model,
        max_tokens=_MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        message = stream.get_final_message()
    if message.stop_reason == "max_tokens":
        raise ValueError(
            f"Output truncated at {_MAX_TOKENS} tokens — raise _MAX_TOKENS"
        )
    raw = next(b.text for b in message.content if b.type == "text")
    return json.loads(_extract_json(raw))


def _retry_claude(prompt: str, model: str, max_attempts: int = 3) -> dict:
    last_err: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return _call_claude(prompt, model)
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            last_err = e
            print(f"  Attempt {attempt}/{max_attempts} failed: {type(e).__name__}: {e}")
            if attempt < max_attempts:
                time.sleep(3 * attempt)
    raise RuntimeError(f"Claude failed after {max_attempts} attempts: {last_err}")


def _validate(digest: dict) -> None:
    if "categories" not in digest:
        raise ValueError("Missing 'categories' key in Claude output")
    for cat, data in digest["categories"].items():
        if not isinstance(data.get("stories"), list):
            raise ValueError(f"Category '{cat}' missing stories list")


def _write_digest(digest: dict) -> None:
    # pwa/data/digest.json  (served by PWA)
    data_dir = _PWA / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out = data_dir / "digest.json"
    out.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written:  {out}")

    # pwa/digests/YYYY-MM-DD.json  (calendar archive)
    archive_dir = _PWA / "digests"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive = archive_dir / f"{digest['date']}.json"
    archive.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Archived: {archive}")


def main(dry_run: bool = False, model: str = _DEFAULT_MODEL) -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"=== Daily Digest — {today} (model: {model}) ===")

    # Force UTF-8 on Windows terminals
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # 1. Fetch articles
    print("\n[1/4] Fetching articles...")
    articles = fetch_all_articles()

    if dry_run:
        print(f"\n[dry-run] {len(articles)} articles fetched. Stopping before Claude call.")
        for a in articles[:8]:
            pp = "💎" if a["paid_partner"] else ("🔒" if a["paywall_only"] else "  ")
            print(f"  {pp} [{a['source']}] {a['title'][:65]}")
        return

    # 2. Fetch trending
    print("\n[2/4] Fetching trending...")
    trending = fetch_trending()

    # 3. Build widgets
    print("\n[3/4] Building widgets...")
    sport  = build_sport_widget()
    market = build_market_snapshot()

    # 4. Call Claude
    print(f"\n[4/4] Calling Claude ({model})...")
    prompt = _build_prompt(articles, trending, today)
    print(f"  Prompt: ~{len(prompt):,} chars (~{len(prompt)//4:,} tokens)")

    digest = _retry_claude(prompt, model)
    _validate(digest)

    # Inject metadata + widget data (Claude does not produce these)
    digest["date"]   = today
    digest["sport"]  = sport
    digest["market"] = market

    _write_digest(digest)

    # Summary
    cats   = digest.get("categories", {})
    total  = sum(len(v.get("stories", [])) for v in cats.values())
    print(f"\n=== Done — {total} stories across {len(cats)} categories ===")
    for cat, data in cats.items():
        n          = len(data.get("stories", []))
        trending_n = sum(1 for s in data.get("stories", []) if s.get("trending"))
        suffix     = f"  ({trending_n} trending)" if trending_n else ""
        print(f"  {cat:<12} {n} stories{suffix}")
    if digest.get("wildcard"):
        print(f"  wildcard     1 story  (Reddit score: {digest['wildcard'].get('trending_score','?')})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Daily Digest builder")
    ap.add_argument("--dry-run", action="store_true",
                    help="Fetch articles only — no Claude call")
    ap.add_argument("--model", default=_DEFAULT_MODEL,
                    help=f"Anthropic model (default: {_DEFAULT_MODEL})")
    args = ap.parse_args()
    main(dry_run=args.dry_run, model=args.model)
