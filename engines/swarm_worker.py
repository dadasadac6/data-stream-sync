"""
Ecosystem Telemetry Probe & Swarm Worker
Executes parallel matrix partition sweeps against the frontier discovery queue.
Designed for both local execution and camouflaged GitHub Actions CI/CD runs.
"""

import argparse
import json
import logging
import os
import random
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import storage.db as db
from engines.dev_evidence import DevEvidenceCollector
from engines.exclusion_shield import ExclusionShield
from engines.scorer import compute_composite_score
from engines.serp_sieve import SerpSieve
from engines.trends_batch import TrendsBatchHTTP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("telemetry_probe")

REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def generate_daily_report(top_items: List[Dict[str, Any]], shard_id: int = 0) -> str:
    """Appends newly discovered high-value opportunities to the daily report."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_filename = f"{today_str}-goldmines.md"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    is_new = not os.path.exists(report_path)
    lines: List[str] = []

    if is_new:
        lines = [
            f"# ⛏️ Search Gap Radar — Daily Intelligence Brief ({today_str})",
            "",
            "> **Budget Spent:** $0.00 (Hard Rule) | **Protocol:** Pure HTTP Dual-Evidence Sieve",
            f"> **Generated At:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "---",
            "",
            "## 1. Top Opportunities (Actionable Briefs)",
            "",
        ]

    for item in top_items:
        q = item["keyword"]
        encoded_q = urllib.parse.quote(q)
        cat = item.get("category", "General")
        arch = item.get("archetype", "Micro-Tool")
        score = item.get("gap_score", 0)
        vel = item.get("trend_velocity", "Breakout")
        ttype = item.get("trend_type", "TOP")
        voids = item.get("exact_title_matches", 0)

        badge = "🔥 BREAKOUT" if ttype == "BREAKOUT" else f"⚡ {vel}"
        google_link = f"https://www.google.com/search?q={encoded_q}"
        ddg_link = f"https://duckduckgo.com/?q={encoded_q}"
        trends_link = f"https://trends.google.com/trends/explore?q={encoded_q}&date=today%2012-m"

        card = [
            f"### `[{score}/100]` {q}",
            f"- **Category:** {cat} | **Archetype:** {arch} | **Velocity:** {badge}",
            f"- **SERP Competition:** {voids}/10 exact `<title>` matches (Untouched Void if 0-1)",
            f"- **1-Click Verify:** [Google Live ↗]({google_link}) | [DuckDuckGo ↗]({ddg_link}) | [Trends 12m ↗]({trends_link})",
            "",
        ]
        lines.extend(card)

    with open(report_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return report_path


def run_swarm_shard(
    shard_id: int = 0,
    total_shards: int = 1,
    max_batches: int = 3,
    batch_size: int = 8,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Executes a single shard partition run:
    1. Atomically claims batches from frontier_niches
    2. Runs Trends 8-batch HTTP exploration ('today 12-m')
    3. Filters with Exclusion Shield
    4. Audits with SERP Sieve + Dev Evidence
    5. Scores and upserts opportunities
    6. Expands child niches recursively
    """
    logger.info(f"--- Launching Swarm Shard {shard_id}/{total_shards} (Max Batches: {max_batches}) ---")

    trends_engine = TrendsBatchHTTP(time_window="today 12-m", shard_id=shard_id)
    exclusion_shield = ExclusionShield()
    serp_sieve = SerpSieve()
    dev_collector = DevEvidenceCollector()

    total_queries_found = 0
    total_gold_found = 0
    batches_completed = 0
    all_top_gold: List[Dict[str, Any]] = []

    for batch_num in range(1, max_batches + 1):
        # 1. Claim batch from frontier queue
        claimed = db.claim_frontier_batch(
            shard_id=shard_id,
            total_shards=total_shards,
            batch_size=batch_size,
        )
        if not claimed:
            logger.info(f"Shard {shard_id}: No pending frontier niches available. Partition finished.")
            break

        terms = [item["niche_term"] for item in claimed]
        logger.info(f"Shard {shard_id} [Batch {batch_num}/{max_batches}]: Processing {len(terms)} claimed root terms: {terms}")

        # 2. Extract batch from Trends HTTP
        batch_results = trends_engine.extract_batch(terms, shard_id=shard_id)

        # 3. Process each term
        for niche_info in claimed:
            niche_term = niche_info["niche_term"]
            category = niche_info["category"]
            depth = niche_info.get("depth_level", 0)
            term_data = batch_results.get(niche_term, {})

            candidates: List[Dict[str, Any]] = []
            for item in term_data.get("rising", []):
                candidates.append({**item, "trend_type": "BREAKOUT" if item.get("isBreakout") else "RISING"})
            for item in term_data.get("top", []):
                candidates.append({**item, "trend_type": "TOP"})

            evaluated_for_niche = 0
            gold_for_niche = 0

            for cand in candidates:
                query = cand.get("query", "").strip()
                if not query:
                    continue

                # Exclusion shield filter
                should_drop, reason = exclusion_shield.should_drop(query, category=category)
                if should_drop:
                    logger.debug(f"Dropped '{query}': {reason}")
                    continue

                # Audit SERP (DuckDuckGo HTML void count)
                serp_res = serp_sieve.audit(query)

                # Dev evidence (Stack Overflow, GitHub, HN)
                dev_res = dev_collector.collect(query)

                # Composite score (0-100) & archetype
                score_data = compute_composite_score(
                    serp_score=serp_res["serp_score"],
                    dev_score=dev_res["dev_score"],
                    trend_type=cand.get("trend_type", "TOP"),
                    trend_velocity=cand.get("change", "Stable"),
                    keyword=query,
                    serp_data=serp_res,
                )

                gap_score = score_data["gap_score"]
                evaluated_for_niche += 1

                if gap_score >= 40:
                    payload = {
                        "keyword": query,
                        "category": category,
                        "trend_type": cand.get("trend_type", "TOP"),
                        "trend_velocity": cand.get("change", "Stable"),
                        "gap_score": gap_score,
                        "archetype": score_data["archetype"],
                        "exact_title_matches": serp_res.get("exact_title_matches", 0),
                        "has_github_issues": dev_res.get("has_github_issues", False),
                        "has_stack_questions": dev_res.get("has_stack_questions", False),
                        "top_competitor_title": serp_res.get("top_competitor_title", ""),
                        "top_competitor_url": serp_res.get("top_competitor_url", ""),
                        "evidence": {
                            "serp": serp_res,
                            "dev": dev_res,
                            "score_breakdown": score_data["breakdown"],
                            "parent_niche": niche_term,
                            "shard_id": shard_id,
                        },
                    }
                    if not dry_run:
                        db.upsert_query(payload)

                    if gap_score >= 70:
                        gold_for_niche += 1
                        all_top_gold.append(payload)
                        logger.info(f"💎 [GOLD MINE {gap_score}/100] Shard {shard_id}: '{query}' ({score_data['archetype']})")

                    # Recursive sub-niche queueing (Depth N+1, max 3)
                    if gap_score >= 60 and depth < 3 and len(query.split()) <= 4:
                        db.queue_sub_niche(query, category=category, parent=niche_term, depth=depth + 1)

            # Mark frontier niche completed
            if not dry_run:
                db.mark_frontier_complete(niche_term, queries_extracted=evaluated_for_niche)

            total_queries_found += evaluated_for_niche
            total_gold_found += gold_for_niche

        batches_completed += 1
        # Stealth jitter between 8-term batches
        time.sleep(random.uniform(2.5, 4.5))

    # Append report if opportunities were discovered
    if all_top_gold and not dry_run:
        generate_daily_report(all_top_gold, shard_id=shard_id)

    db.log_scan_event(
        batch_name=f"shard-{shard_id}",
        category="Multi-Vertical",
        queries_found=total_queries_found,
        gold_found=total_gold_found,
        log_message=f"Shard {shard_id}/{total_shards} processed {batches_completed} batches. Found {total_gold_found} gold mines.",
    )

    logger.info(
        f"Shard {shard_id} Completed: {batches_completed} batches | "
        f"{total_queries_found} queries evaluated | {total_gold_found} gold mines"
    )
    return {
        "shard_id": shard_id,
        "batches_completed": batches_completed,
        "queries_found": total_queries_found,
        "gold_found": total_gold_found,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ecosystem Telemetry Probe & Swarm Worker")
    parser.add_argument("--shard-id", type=int, default=0, help="Shard index (0 to total_shards-1)")
    parser.add_argument("--total-shards", type=int, default=1, help="Total number of parallel shards")
    parser.add_argument("--max-batches", type=int, default=2, help="Maximum 8-keyword batches to process")
    parser.add_argument("--dry-run", action="store_true", help="Audit without writing to database")

    args = parser.parse_args()
    run_swarm_shard(
        shard_id=args.shard_id,
        total_shards=args.total_shards,
        max_batches=args.max_batches,
        dry_run=args.dry_run,
    )
