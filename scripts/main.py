"""
Orchestrator — runs the full daily digest pipeline.

Usage:
    python main.py              # full run
    python main.py --dry-run    # fetch + cluster + score only (no Groq summaries,
                                #   no widgets, writes a skeleton digest for testing)
"""
from __future__ import annotations

import argparse
import sys
import os

# Ensure scripts/ is on the path when invoked directly
sys.path.insert(0, os.path.dirname(__file__))

# Force UTF-8 output so non-ASCII source names (ČT24, Denník N…) don't crash
# on Windows cp1252 terminals. GitHub Actions uses UTF-8 natively.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from stats     import read_stats, reset_if_new_month, write_stats
from fetch     import fetch_all_articles
from cluster   import cluster_articles
from categorize import categorize_clusters
from score     import score_clusters
from process  import process_top_stories
from widgets  import build_sport_widget, build_market_snapshot
from generate import generate_random, generate_learning
from build    import build_digest, write_digest


def main(dry_run: bool = False) -> None:
    print("=== Daily Digest pipeline starting ===")

    # 1. Stats
    print("[1/9] Reading stats...")
    stats = read_stats()
    stats = reset_if_new_month(stats)

    # 2. Fetch
    print("[2/9] Fetching articles...")
    articles = fetch_all_articles()
    print(f"      {len(articles)} articles fetched")

    # 3. Cluster
    print("[3/9] Clustering...")
    clusters = cluster_articles(articles)
    print(f"      {len(clusters)} clusters")

    # 3.5 Re-categorize by topic (so an Iran story from a Slovak source is
    #     filed under 'war'/'global', not 'slovakia').
    print("[3.5] Re-categorizing by topic...")
    clusters = categorize_clusters(clusters)

    # 4. Score
    print("[4/9] Scoring...")
    top_stories = score_clusters(clusters, stats)
    print(f"      {len(top_stories)} stories selected")

    if dry_run:
        print("\n[dry-run] Skipping Groq summarisation, widgets, generation.")
        print(f"Top 5 topics:")
        for s in top_stories[:5]:
            print(f"  [{s['category']}] {s['topic'][:70]}  score={s['score']:.2f}")
        return

    # 5. Process
    print("[5/9] Summarising with Groq...")
    processed = process_top_stories(top_stories)

    # 6. Widgets
    print("[6/9] Building sport widget...")
    sport = build_sport_widget()
    print("[7/9] Building market snapshot...")
    market = build_market_snapshot()

    # 7. Generate
    top_topics = [s["topic"] for s in processed[:10]]
    print("[8/9] Generating Random item...")
    random_item = generate_random(stats, top_topics)
    # Pass Random's URL(s) so Learning never picks the same article
    random_urls = [s["url"] for s in random_item.get("sources", [])]
    print("[9/9] Generating Learning item...")
    learning_item = generate_learning(top_topics, exclude_urls=random_urls)

    # 8. Build + write
    print("Assembling digest.json...")
    digest = build_digest(processed, sport, market, random_item, learning_item)
    write_digest(digest)

    # 9. Update stats (include random + learning so their counts aren't always 0)
    write_stats(stats, processed + [random_item, learning_item])

    mins = digest["estimated_read_minutes"]
    total = digest["total_stories"]
    print(f"\n=== Done — {total} stories, ~{mins} min read ===")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Fetch + cluster + score without calling Groq")
    args = ap.parse_args()
    main(dry_run=args.dry_run)
