"""
Autonomous 24/7 Background Worker Daemon for Developer Search Gap Radar
Runs continuous sweeps across curated 8-keyword batches, scores opportunities,
updates SQLite, and generates daily Markdown product briefs with 1-click Google links.
"""

import argparse
import json
import logging
import os
import random
import time
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List

import storage.db as db
from engines.signal_tracer import SignalTracer, DevEvidenceCollector
from engines.filter_pipeline import FilterPipeline, ExclusionShield
from engines.evaluator import compute_composite_score
from engines.index_auditor import IndexAuditor, SerpSieve
from engines.stream_sampler import StreamSamplerHTTP, TrendsBatchHTTP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("probe_daemon")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "matrix_taxonomy.json")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def generate_daily_report(top_items: List[Dict[str, Any]]) -> str:
    """Generates an actionable Markdown brief with 1-click verification links."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    today_str = datetime.now().strftime("%Y-%m-%d")
    report_filename = f"{today_str}-telemetry-audit.md"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    lines = [
        f"# 📊 Ecosystem Telemetry — Shard Audit Matrix ({today_str})",
        "",
        "> **Protocol:** Pure HTTP Matrix Probe",
        f"> **Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "---",
        "",
        "## 1. Executive Summary & Telemetry KPIs",
        "",
        f"- **Qualified High-Demand Opportunities Discovered:** {len(top_items)}",
        f"- **Critical Opportunities (85+ Score):** {sum(1 for i in top_items if i.get('gap_score', 0) >= 85)}",
        f"- **Surging Breakouts:** {sum(1 for i in top_items if i.get('trend_type') == 'BREAKOUT')}",
        "",
        "---",
        "",
        "## 2. Priority Opportunities (Actionable Briefs)",
        "",
    ]

    for rank, item in enumerate(top_items, 1):
        q = item["keyword"]
        q_enc = urllib.parse.quote(q)
        verify_url = f"https://www.google.com/search?q={q_enc}"
        score = item["gap_score"]
        archetype = item["archetype"]
        category = item["category"]
        velocity = item.get("trend_velocity", "Breakout")
        exact_titles = item.get("exact_title_matches", 0)

        lines.extend([
            f"### #{rank}. [{score}/100] `{q}`",
            "",
            f"- **Archetype:** `{archetype}`",
            f"- **Category:** `{category}`",
            f"- **Velocity surge:** `{velocity}`",
            f"- **Exact `<title>` match count:** `{exact_titles}/10` ({'Untouched Void 🛡️' if exact_titles == 0 else 'Vulnerable'})",
            f"- **1-Click Google Verification:** [Verify Live SERP in Browser]({verify_url})",
            "",
            "#### Developer Implementation Blueprint:",
        ])

        if archetype == "Micro-Tool":
            lines.extend([
                "- **Suggested Deliverable:** Single-page responsive web utility with programmatic SEO.",
                "- **Tech Stack:** Next.js / Tailwind CSS / Vercel (or static HTML on GitHub Pages).",
                f"- **Core Value Proposition:** Instant browser-based conversion or calculation for `{q}` with zero signup required.",
            ])
        elif archetype == "Workaround":
            lines.extend([
                "- **Suggested Deliverable:** Definitive technical troubleshooting guide with reproducible root-cause analysis.",
                "- **Key Components:** Minimal reproducible example, error explanation, copy-paste config fix / patch script.",
                f"- **Target Intent:** Provide the exact snippet that resolves `{q}` without forcing the user to dig through 50 forum posts.",
            ])
        elif archetype == "Recipe":
            lines.extend([
                "- **Suggested Deliverable:** GitHub starter repo, Docker Compose scaffold, or interactive cheatsheet.",
                "- **Key Components:** Production-ready boilerplate, environment config, copy-paste code snippets.",
                f"- **Target Intent:** The fast, canonical starting point for developers searching `{q}`.",
            ])
        else:
            lines.extend([
                "- **Suggested Deliverable:** Rapid technical migration briefing or benchmark breakdown.",
                "- **Key Components:** Breaking change diffs, performance comparisons, upgrade path.",
                f"- **Target Intent:** Immediate answers to developer questions regarding `{q}`.",
            ])

        lines.extend(["", "---", ""])

    report_content = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    logger.info(f"Daily Markdown brief saved to: {report_path}")
    return report_path


def run_radar_sweep(limit_batches_per_cat: int = 2) -> List[Dict[str, Any]]:
    """Performs one full intelligence sweep across frontier niches and taxonomy categories."""
    trends_engine = StreamSamplerHTTP(time_window="today 12-m")
    shield = FilterPipeline()
    sieve = IndexAuditor()
    evidence_collector = SignalTracer()

    qualified_opportunities: List[Dict[str, Any]] = []

    # Priority 1: Check dynamic frontier queue
    frontier_batch = db.claim_frontier_batch(shard_id=0, total_shards=1, batch_size=8)
    if frontier_batch:
        terms = [item["niche_term"] for item in frontier_batch]
        logger.info(f"=== Processing Dynamic Frontier Batch ({len(terms)} terms): {terms} ===")
        try:
            batch_data = trends_engine.extract_batch(terms)
            for f_item in frontier_batch:
                niche_term = f_item["niche_term"]
                category = f_item["category"]
                depth = f_item.get("depth", 0)
                stream = batch_data.get(niche_term, {})

                all_queries = []
                for item in stream.get("rising", []):
                    item["trend_type"] = "BREAKOUT" if item.get("isBreakout") else "RISING"
                    all_queries.append(item)
                for item in stream.get("top", []):
                    item["trend_type"] = "TOP"
                    all_queries.append(item)

                for item in all_queries:
                    kw = item.get("query", "").strip()
                    if not kw or len(kw) < 4:
                        continue
                    if db.is_keyword_processed(kw, max_age_days=7):
                        continue
                    passed, reason = shield.evaluate(kw)
                    if not passed:
                        continue

                    serp_audit = sieve.audit_serp(kw)
                    passed_serp, _ = shield.evaluate(kw, serp_audit.get("raw_results"))
                    if not passed_serp:
                        continue

                    dev_evidence = evidence_collector.collect_evidence(kw)
                    scored = compute_composite_score(
                        query=kw,
                        trend_type=item.get("trend_type", "TOP"),
                        trend_velocity=item.get("change", "Stable"),
                        serp_audit=serp_audit,
                        dev_evidence=dev_evidence,
                    )
                    scored["category"] = category
                    scored["trend_velocity"] = str(item.get("change", "Stable"))
                    scored["trend_type"] = item.get("trend_type", "TOP")

                    db.upsert_query(scored)
                    if scored["gap_score"] >= 65:
                        qualified_opportunities.append(scored)
                        logger.info(f"✨ Found High Opp [{scored['gap_score']}/100]: '{kw}' ({scored['archetype']})")

                    if scored["gap_score"] >= 60 and depth < 3 and len(kw.split()) <= 4:
                        db.queue_sub_niche(kw, category=category, parent=niche_term, depth=depth + 1)

                db.mark_frontier_complete(niche_term, queries_extracted=len(all_queries))
        except Exception as e:
            logger.warning(f"Frontier batch extraction error: {e}")

    # Priority 2: Also run static taxonomy categories
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        categories = cfg.get("categories", {})
        for cat_name, cat_data in categories.items():
            batches = cat_data.get("batches", [])[:limit_batches_per_cat]
            for b_idx, batch_terms in enumerate(batches, 1):
                try:
                    batch_data = trends_engine.extract_batch(batch_terms)
                    for seed, stream in batch_data.items():
                        all_queries = []
                        for item in stream.get("rising", []):
                            item["trend_type"] = "BREAKOUT" if item.get("isBreakout") else "RISING"
                            all_queries.append(item)
                        for item in stream.get("top", []):
                            item["trend_type"] = "TOP"
                            all_queries.append(item)

                        for item in all_queries:
                            kw = item.get("query", "").strip()
                            if not kw or len(kw) < 4 or db.is_keyword_processed(kw, max_age_days=7):
                                continue
                            passed, _ = shield.evaluate(kw)
                            if not passed:
                                continue
                            serp_audit = sieve.audit_serp(kw)
                            passed_serp, _ = shield.evaluate(kw, serp_audit.get("raw_results"))
                            if not passed_serp:
                                continue
                            dev_evidence = evidence_collector.collect_evidence(kw)
                            scored = compute_composite_score(
                                query=kw,
                                trend_type=item.get("trend_type", "TOP"),
                                trend_velocity=item.get("change", "Stable"),
                                serp_audit=serp_audit,
                                dev_evidence=dev_evidence,
                            )
                            scored["category"] = cat_name
                            scored["trend_velocity"] = str(item.get("change", "Stable"))
                            scored["trend_type"] = item.get("trend_type", "TOP")
                            db.upsert_query(scored)
                            if scored["gap_score"] >= 65:
                                qualified_opportunities.append(scored)
                                logger.info(f"✨ Found High Opp [{scored['gap_score']}/100]: '{kw}' ({scored['archetype']})")
                except Exception as e:
                    logger.warning(f"Batch sweep error for {cat_name}: {e}")
                time.sleep(random.uniform(1.0, 2.5))

    qualified_opportunities.sort(key=lambda x: x["gap_score"], reverse=True)
    if qualified_opportunities:
        generate_daily_report(qualified_opportunities[:25])
    return qualified_opportunities


def main():
    parser = argparse.ArgumentParser(description="Autonomous Developer Search Gap Radar Daemon")
    parser.add_argument("--once", action="store_true", help="Run a single sweep and exit")
    parser.add_argument("--interval-hours", type=float, default=6.0, help="Hours between sweeps in continuous mode")
    args = parser.parse_args()

    db.init_db()
    logger.info("Radar Daemon initialized. WAL SQLite ready.")

    if args.once:
        logger.info("Running single radar sweep...")
        results = run_radar_sweep(limit_batches_per_cat=1)
        logger.info(f"Sweep complete. Qualified opportunities found: {len(results)}")
        return

    logger.info(f"Starting continuous daemon mode (interval: {args.interval_hours} hours)...")
    while True:
        try:
            logger.info("Initiating scheduled radar sweep...")
            results = run_radar_sweep(limit_batches_per_cat=1)
            logger.info(f"Sweep finished with {len(results)} opportunities. Sleeping for {args.interval_hours} hours...")
        except Exception as e:
            logger.error(f"Daemon sweep error: {e}", exc_info=True)

        time.sleep(args.interval_hours * 3600)


if __name__ == "__main__":
    main()
