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
from engines.dev_evidence import DevEvidenceCollector
from engines.exclusion_shield import ExclusionShield
from engines.scorer import compute_composite_score
from engines.serp_sieve import SerpSieve
from engines.trends_batch import TrendsBatchHTTP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("radar_daemon")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "dev_niches.json")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def generate_daily_report(top_items: List[Dict[str, Any]]) -> str:
    """Generates an actionable Markdown product brief with 1-click verification links."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    report_filename = f"{today_str}-goldmines.md"
    report_path = os.path.join(REPORTS_DIR, report_filename)

    lines = [
        f"# ⛏️ Developer Search Gap Radar — Daily Intelligence Brief ({today_str})",
        "",
        "> **Budget Spent:** $0.00 (Hard Rule) | **Protocol:** Pure HTTP Dual-Evidence Sieve",
        f"> **Generated At:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "---",
        "",
        "## 1. Executive Summary & Radar KPIs",
        "",
        f"- **Qualified High-Demand Opportunities Discovered:** {len(top_items)}",
        f"- **Critical Gold Mines (85+ Score):** {sum(1 for i in top_items if i.get('gap_score', 0) >= 85)}",
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
    """Performs one full intelligence sweep across all categories."""
    if not os.path.exists(CONFIG_PATH):
        logger.error(f"Configuration file {CONFIG_PATH} not found.")
        return []

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    categories = cfg.get("categories", {})
    trends_engine = TrendsBatchHTTP(time_window="now 1-d")
    shield = ExclusionShield()
    sieve = SerpSieve()
    evidence_collector = DevEvidenceCollector()

    qualified_opportunities: List[Dict[str, Any]] = []

    for cat_name, cat_data in categories.items():
        batches = cat_data.get("batches", [])[:limit_batches_per_cat]
        logger.info(f"=== Scanning Category: {cat_name} ({len(batches)} batches) ===")

        for b_idx, batch_terms in enumerate(batches, 1):
            logger.info(f"Processing 8-term batch #{b_idx}: {batch_terms}")
            try:
                batch_data = trends_engine.extract_batch(batch_terms)
            except Exception as e:
                logger.warning(f"Batch extraction failed: {e}")
                continue

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
                    if not kw or len(kw) < 4:
                        continue

                    # Check deduplication cache (avoid re-auditing if tested in last 7 days)
                    if db.is_keyword_processed(kw, max_age_days=7):
                        continue

                    # Exclusion Shield check 1 (syntactic/navigational)
                    passed, reason = shield.evaluate(kw)
                    if not passed:
                        continue

                    # Serp Sieve audit
                    serp_audit = sieve.audit_serp(kw)

                    # Exclusion Shield check 2 (institutional domain in top 3)
                    passed_serp, s_reason = shield.evaluate(kw, serp_audit.get("raw_results"))
                    if not passed_serp:
                        continue

                    # Dev Evidence collection
                    dev_evidence = evidence_collector.collect_evidence(kw)

                    # Composite scoring
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
                    scored["evidence"] = {
                        "serp": {
                            "top_competitor_title": serp_audit.get("top_competitor_title"),
                            "top_competitor_url": serp_audit.get("top_competitor_url"),
                            "exact_title_matches": serp_audit.get("exact_title_matches"),
                            "forum_count": serp_audit.get("forum_count"),
                        },
                        "dev": {
                            "github": dev_evidence.get("github"),
                            "stack_exchange": dev_evidence.get("stack_exchange"),
                            "hacker_news": dev_evidence.get("hacker_news"),
                        },
                    }

                    # Save to DB
                    db.upsert_query(scored)

                    if scored["gap_score"] >= 65:
                        qualified_opportunities.append(scored)
                        logger.info(
                            f"✨ Found High Opp [{scored['gap_score']}/100]: '{kw}' "
                            f"({scored['archetype']}, Exact Titles: {scored['exact_title_matches']}/10)"
                        )

            # Jitter between batches to respect free endpoints
            time.sleep(random.uniform(1.0, 2.5))

    # Sort opportunities by gap score descending
    qualified_opportunities.sort(key=lambda x: x["gap_score"], reverse=True)

    # Generate daily Markdown report if opportunities were identified
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
