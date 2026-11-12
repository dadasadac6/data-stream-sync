#!/usr/bin/env python3
"""
Instant On-Demand Keyword & Root Niche Re-checker
Allows the user to re-evaluate any specific keyword or explore any root term immediately.
"""

import argparse
import json
import logging
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.stream_sampler import TrendsBatchHTTP
from engines.index_auditor import SerpSieve
from engines.signal_tracer import DevEvidenceCollector
from engines.filter_pipeline import ExclusionShield
from engines.evaluator import compute_composite_score
import storage.db as db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rechecker")

def recheck_term(term: str, category: str = "Developer & Cloud"):
    term = term.strip()
    logger.info(f"⚡ Starting instant live probe for: '{term}' (Category: {category})")

    # 1. Reset term in frontier if present
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        sig = db.compute_signature(term)
        cur.execute("DELETE FROM explored_signatures WHERE signature_hash = ?", (sig,))
        cur.execute("UPDATE frontier_niches SET status = 'pending', queries_extracted = 0 WHERE niche_term = ?", (term,))
        conn.commit()
    finally:
        conn.close()

    # 2. Query Google Trends
    trends = TrendsBatchHTTP(time_window="today 12-m", shard_id=0)
    logger.info("-> Querying Google Trends explore API...")
    batch_res = trends.extract_batch([term], shard_id=0)
    term_data = batch_res.get(term, {})

    rising = term_data.get("rising", [])
    top = term_data.get("top", [])
    logger.info(f"-> Google Trends returned {len(rising)} rising and {len(top)} top queries.")

    candidates = []
    for item in rising:
        candidates.append({**item, "trend_type": "BREAKOUT" if item.get("isBreakout") else "RISING"})
    for item in top:
        candidates.append({**item, "trend_type": "TOP"})

    # If no related queries from Google Trends, still evaluate the exact term itself!
    if not candidates:
        logger.info(f"-> No related queries found. Evaluating '{term}' as a standalone target query.")
        candidates.append({"query": term, "trend_type": "TOP", "change": "Stable"})

    exclusion_shield = ExclusionShield()
    sieve = SerpSieve()
    dev_collector = DevEvidenceCollector()

    evaluated = 0
    saved = []

    for cand in candidates:
        q = cand.get("query", "").strip()
        if not q:
            continue

        drop, reason = exclusion_shield.should_drop(q, category=category)
        if drop and q != term:
            continue

        logger.info(f"[*] Auditing query: '{q}'")
        serp_res = sieve.audit(q)
        dev_res = dev_collector.collect(q)

        score_data = compute_composite_score(
            serp_score=serp_res.get("serp_score", 0),
            dev_score=dev_res.get("dev_score", 0),
            trend_type=cand.get("trend_type", "TOP"),
            trend_velocity=cand.get("change", "Stable"),
            keyword=q,
            serp_data=serp_res,
        )

        exact_matches = serp_res.get("exact_title_matches")
        payload = {
            "keyword": q,
            "category": category,
            "trend_type": cand.get("trend_type", "TOP"),
            "trend_velocity": cand.get("change", "Stable"),
            "gap_score": score_data["gap_score"],
            "archetype": score_data["archetype"],
            "exact_title_matches": exact_matches,
            "has_github_issues": dev_res.get("has_github_issues", False),
            "has_stack_questions": dev_res.get("has_stack_questions", False),
            "top_competitor_title": serp_res.get("top_competitor_title", ""),
            "top_competitor_url": serp_res.get("top_competitor_url", ""),
            "evidence": {
                "serp": serp_res,
                "dev": dev_res,
                "score_breakdown": score_data["breakdown"],
                "parent_niche": term,
            },
        }

        db.upsert_query(payload)
        evaluated += 1
        saved.append(payload)

    db.mark_frontier_complete(term, queries_extracted=evaluated)
    logger.info(f"✅ Finished! Evaluated {evaluated} queries for '{term}'.")
    return saved

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("term", type=str, help="Keyword or niche to recheck")
    parser.add_argument("--category", type=str, default="Developer & Cloud", help="Category")
    args = parser.parse_args()
    recheck_term(args.term, args.category)
