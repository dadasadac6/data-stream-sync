"""
Database Re-Sanitization & Precision Calibration Migration Script
Applies Claude's Architecture Review fixes retroactively to all rows in storage/telemetry_matrix.db:
1. Strips DuckDuckGo sponsored ad links from raw_results and top_competitor_url
2. Re-scores SERPs and detects navigational TLD collisions (e.g. 'calorie calculator net')
3. Applies strict token overlap (Jaccard + coverage) to StackExchange developer evidence
4. Reclassifies verticals using the 3-layer token classifier (resolving category drift)
5. Maps opportunities into the expanded 8 Archetypes
6. Re-scores gap_score with hard caps on navigational queries
"""

import json
import logging
import os
import shutil
import sqlite3
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from engines.evaluator import classify_vertical, compute_composite_score
from engines.index_auditor import SerpSieve, strip_ads_from_results
from engines.signal_tracer import is_dev_evidence_relevant

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("resanitize")

DB_PATH = os.path.join(BASE_DIR, "storage", "telemetry_matrix.db")
BACKUP_PATH = os.path.join(BASE_DIR, "storage", "telemetry_matrix.db.pre_sanitization_bak")


def run_migration():
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}")
        return

    # 1. Create a safe backup
    logger.info(f"Backing up database to {BACKUP_PATH}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM queries")
    total_records = cursor.fetchone()[0]
    logger.info(f"Loaded {total_records} query records for re-sanitization.")

    sieve = SerpSieve()

    cursor.execute("""
        SELECT id, keyword, category, trend_type, trend_velocity, gap_score,
               archetype, exact_title_matches, has_stack_questions,
               top_competitor_title, top_competitor_url, evidence_json
        FROM queries
    """)
    rows = cursor.fetchall()

    ads_stripped_count = 0
    navigational_demoted_count = 0
    se_false_matches_removed = 0
    verticals_reclassified_count = 0
    critical_before = sum(1 for r in rows if r["gap_score"] >= 85)
    critical_after = 0

    calorie_net_before = None
    calorie_net_after = None

    updates = []

    for r in rows:
        row_id = r["id"]
        keyword = r["keyword"]
        old_cat = r["category"]
        trend_type = r["trend_type"] or "TOP"
        trend_velocity = r["trend_velocity"] or "Stable"
        old_gap_score = r["gap_score"]
        old_top_url = r["top_competitor_url"] or ""

        evidence = {}
        if r["evidence_json"]:
            try:
                evidence = json.loads(r["evidence_json"])
            except Exception:
                evidence = {}

        serp_data = evidence.get("serp", {})
        raw_results = serp_data.get("raw_results", [])

        # 1. Strip ads
        cleaned_results = strip_ads_from_results(raw_results)
        had_ad = len(cleaned_results) < len(raw_results) or "y.js" in old_top_url or "ad_domain=" in old_top_url
        if had_ad:
            ads_stripped_count += 1

        # 2. Re-audit SERP with updated index auditor (includes navigational detection)
        if cleaned_results:
            re_audited_serp = sieve.audit_serp(keyword, serp_results=cleaned_results)
        else:
            # Fallback if no raw_results stored: create synthetic entry from top competitor if present
            if old_top_url:
                synthetic = [{"title": r["top_competitor_title"] or "", "url": old_top_url, "snippet": ""}]
                re_audited_serp = sieve.audit_serp(keyword, serp_results=synthetic)
            else:
                re_audited_serp = {
                    "serp_score": serp_data.get("serp_score", 0),
                    "exact_title_matches": r["exact_title_matches"],
                    "results_count": 0,
                    "top_competitor_title": "",
                    "top_competitor_url": "",
                    "raw_results": [],
                    "navigational_signal": {"is_navigational": False},
                }

        is_nav = re_audited_serp.get("navigational_signal", {}).get("is_navigational", False)
        if is_nav:
            navigational_demoted_count += 1

        # 3. Re-evaluate Developer Evidence
        dev_data = evidence.get("dev", {})
        old_dev_score = dev_data.get("dev_score", 0)
        recomputed_dev_score = old_dev_score
        has_stack = r["has_stack_questions"]

        # Check StackExchange relevance
        se_data = dev_data.get("stack_exchange", {})
        se_sample_title = se_data.get("sample_title", "")
        if se_sample_title:
            is_rel, jac, cov, _ = is_dev_evidence_relevant(keyword, se_sample_title)
            if not is_rel and old_dev_score > 0:
                # Deduct unearned points (up to 15 pts)
                recomputed_dev_score = max(0, old_dev_score - 15)
                se_data["unresolved_count"] = 0
                se_data["has_unresolved"] = False
                has_stack = False
                se_false_matches_removed += 1

        # 4. Reclassify vertical (Layer 1 tokens, Layer 2 SERP domains)
        new_vertical = classify_vertical(
            keyword,
            serp_results=re_audited_serp.get("raw_results", []),
            parent_category=old_cat,
        )
        if new_vertical != old_cat:
            verticals_reclassified_count += 1

        # 5. Recompute composite score
        eval_result = compute_composite_score(
            query=keyword,
            trend_type=trend_type,
            trend_velocity=trend_velocity,
            serp_audit=re_audited_serp,
            dev_score=recomputed_dev_score,
            is_navigational=is_nav,
        )

        new_gap_score = eval_result["gap_score"]
        new_archetype = eval_result["archetype"]
        new_exact_matches = eval_result["exact_title_matches"]
        new_top_title = eval_result["top_competitor_title"] or re_audited_serp.get("top_competitor_title", "")
        new_top_url = eval_result["top_competitor_url"] or re_audited_serp.get("top_competitor_url", "")

        if new_gap_score >= 85:
            critical_after += 1

        # Track calorie calculator net specifically
        if keyword == "calorie calculator net":
            calorie_net_before = {
                "gap_score": old_gap_score,
                "archetype": r["archetype"],
                "serp_score": serp_data.get("serp_score"),
                "top_url": old_top_url[:60] + "...",
            }
            calorie_net_after = {
                "gap_score": new_gap_score,
                "archetype": new_archetype,
                "serp_score": re_audited_serp.get("serp_score"),
                "top_url": new_top_url,
                "is_navigational": is_nav,
                "nav_reason": re_audited_serp.get("navigational_reason"),
            }

        # Update evidence JSON
        evidence.setdefault("serp", {})
        evidence.setdefault("dev", {})
        evidence["serp"] = re_audited_serp
        evidence["dev"]["dev_score"] = recomputed_dev_score
        evidence["score_breakdown"] = eval_result["breakdown"]
        evidence_str = json.dumps(evidence)

        updates.append((
            new_vertical,
            new_gap_score,
            new_archetype,
            new_exact_matches,
            new_top_title,
            new_top_url,
            has_stack,
            evidence_str,
            row_id,
        ))

    # Perform batch update
    cursor.executemany("""
        UPDATE queries
        SET category = ?,
            gap_score = ?,
            archetype = ?,
            exact_title_matches = ?,
            top_competitor_title = ?,
            top_competitor_url = ?,
            has_stack_questions = ?,
            evidence_json = ?,
            last_updated = CURRENT_TIMESTAMP
        WHERE id = ?
    """, updates)

    conn.commit()
    conn.close()

    print("\n" + "="*60)
    print("DATABASE RE-SANITIZATION MIGRATION COMPLETE")
    print("="*60)
    print(f"Total Records Processed:            {total_records}")
    print(f"Sponsored Ad URLs Stripped:         {ads_stripped_count}")
    print(f"Navigational Queries Demoted:       {navigational_demoted_count}")
    print(f"StackExchange False Matches Fixed:  {se_false_matches_removed}")
    print(f"Verticals Reclassified (Drift Fix): {verticals_reclassified_count}")
    print(f"Critical Gaps (85+) Before:         {critical_before}")
    print(f"Critical Gaps (85+) After:          {critical_after}")
    print("-"*60)
    print("CALORIE CALCULATOR NET AUDIT:")
    print("Before:", calorie_net_before)
    print("After: ", calorie_net_after)
    print("="*60 + "\n")


if __name__ == "__main__":
    run_migration()
