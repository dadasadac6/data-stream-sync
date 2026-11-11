"""
FastAPI Dashboard Server for Autonomous Developer Search Gap Radar
Serves on http://localhost:8080 (and LAN http://0.0.0.0:8080).
Provides REST endpoints for live opportunities, verdicts, reports, export, and scan controls.
"""

import csv
import io
import json
import logging
import os
import threading
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import storage.db as db
from engines.dev_evidence import DevEvidenceCollector
from engines.exclusion_shield import ExclusionShield
from engines.scorer import compute_composite_score
from engines.serp_sieve import SerpSieve
from engines.trends_batch import TrendsBatchHTTP

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dashboard")

app = FastAPI(title="Developer Search Gap Radar", version="3.0")

# Enable CORS for LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "ui", "templates")
STATIC_DIR = os.path.join(BASE_DIR, "ui", "static")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "dev_niches.json")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Scan state tracker
scan_state = {
    "is_scanning": False,
    "progress": 0,
    "total": 0,
    "current_category": "",
    "current_keyword": "",
    "message": "Idle",
    "last_run": None,
}


class VerdictRequest(BaseModel):
    id: int
    verdict: str  # 'confirmed_gold', 'already_served', 'pending'


class ScanRequest(BaseModel):
    category: Optional[str] = "All"
    limit_batches: Optional[int] = 1


def run_pipeline_scan(category_filter: str = "All", limit_batches: int = 1):
    """Background task to run trends batch extraction, exclusion shield, serp sieve, and scoring."""
    global scan_state
    if scan_state["is_scanning"]:
        return

    scan_state["is_scanning"] = True
    scan_state["progress"] = 0
    scan_state["message"] = "Loading seed configurations..."

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        categories = cfg.get("categories", {})
        target_cats = (
            {category_filter: categories[category_filter]}
            if category_filter != "All" and category_filter in categories
            else categories
        )

        trends_engine = TrendsBatchHTTP(time_window="now 1-d")
        shield = ExclusionShield()
        sieve = SerpSieve()
        evidence_collector = DevEvidenceCollector()

        # Calculate total batches
        all_batches: List[tuple] = []
        for cat_name, cat_data in target_cats.items():
            batches = cat_data.get("batches", [])[:limit_batches]
            for b in batches:
                all_batches.append((cat_name, b))

        scan_state["total"] = len(all_batches)
        logger.info(f"Starting scan across {len(all_batches)} batches...")

        queries_discovered = 0
        gold_discovered = 0

        for b_idx, (cat_name, batch_terms) in enumerate(all_batches, 1):
            scan_state["current_category"] = cat_name
            scan_state["progress"] = b_idx
            scan_state["message"] = f"Extracting 8-term Trends for [{cat_name}]: {', '.join(batch_terms[:3])}..."
            logger.info(f"[{b_idx}/{len(all_batches)}] Batch {cat_name}: {batch_terms}")

            batch_data = trends_engine.extract_batch(batch_terms)

            # Process all raw queries returned (Top and Rising Breakouts)
            for seed_term, stream in batch_data.items():
                all_extracted = []
                for item in stream.get("rising", []):
                    item["trend_type"] = "BREAKOUT" if item.get("isBreakout") else "RISING"
                    all_extracted.append(item)
                for item in stream.get("top", []):
                    item["trend_type"] = "TOP"
                    all_extracted.append(item)

                for item in all_extracted:
                    kw = item.get("query", "").strip()
                    if not kw or len(kw) < 4:
                        continue

                    # Exclusion Shield: pre-SERP check
                    passed, reason = shield.evaluate(kw)
                    if not passed:
                        continue

                    scan_state["current_keyword"] = kw
                    queries_discovered += 1

                    # Sieve & Developer Evidence
                    serp_audit = sieve.audit_serp(kw)

                    # Post-SERP Exclusion check
                    passed_serp, s_reason = shield.evaluate(kw, serp_audit.get("raw_results"))
                    if not passed_serp:
                        continue

                    dev_evidence = evidence_collector.collect_evidence(kw)

                    # Composite scoring & archetype classification
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
                            "root_domain_in_top5": serp_audit.get("root_domain_in_top5"),
                        },
                        "dev": {
                            "github": dev_evidence.get("github"),
                            "stack_exchange": dev_evidence.get("stack_exchange"),
                            "hacker_news": dev_evidence.get("hacker_news"),
                        },
                    }

                    # Upsert into SQLite
                    db.upsert_query(scored)

                    if scored["gap_score"] >= 85:
                        gold_discovered += 1
                        logger.info(f"💎 CRITICAL GOLD MINE [{scored['gap_score']}/100]: '{kw}' ({scored['archetype']})")

            db.log_scan_event(
                batch_name=f"{cat_name} Batch {b_idx}",
                category=cat_name,
                queries_found=queries_discovered,
                gold_found=gold_discovered,
                log_message=f"Completed batch with {queries_discovered} candidates evaluated, {gold_discovered} Gold.",
            )

        scan_state["message"] = f"Scan complete! Discovered {queries_discovered} queries ({gold_discovered} Gold Mines)."
        scan_state["last_run"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        logger.error(f"Error during scan: {e}", exc_info=True)
        scan_state["message"] = f"Scan failed: {str(e)}"
    finally:
        scan_state["is_scanning"] = False


@app.get("/", response_class=HTMLResponse)
def index_page():
    html_file = os.path.join(TEMPLATES_DIR, "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Gold Miner UI loading... Please refresh in a moment.</h1>"


@app.get("/api/stats")
def get_stats():
    stats = db.get_stats()
    stats["scan_state"] = scan_state
    return stats


@app.get("/api/queries")
def get_queries(
    category: Optional[str] = "all",
    archetype: Optional[str] = "all",
    verdict: Optional[str] = "all",
    min_score: int = 0,
    search: Optional[str] = None,
    sort_by: str = "gap_score",
    sort_order: str = "DESC",
    page: int = 1,
    limit: int = 30,
):
    offset = (page - 1) * limit
    items, total = db.get_queries(
        category=category,
        archetype=archetype,
        verdict=verdict,
        min_score=min_score,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    # Augment with Google verification link
    for item in items:
        q_enc = urllib.parse.quote(item["keyword"])
        item["google_verify_url"] = f"https://www.google.com/search?q={q_enc}"
        if item.get("evidence_json"):
            try:
                item["evidence"] = json.loads(item["evidence_json"])
            except Exception:
                item["evidence"] = {}

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@app.post("/api/verdict")
def set_verdict(req: VerdictRequest):
    success = db.update_verdict(req.id, req.verdict)
    if not success:
        raise HTTPException(status_code=404, detail="Query ID not found")
    return {"status": "ok", "id": req.id, "verdict": req.verdict}


@app.post("/api/scan")
def trigger_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    if scan_state["is_scanning"]:
        return {"status": "busy", "message": "Scan already in progress", "scan_state": scan_state}

    background_tasks.add_task(run_pipeline_scan, req.category or "All", req.limit_batches or 1)
    return {"status": "started", "message": f"Scan triggered for category: {req.category}"}


@app.get("/api/scan/status")
def get_scan_status():
    return scan_state


@app.get("/api/logs")
def get_logs(limit: int = 30):
    return db.get_recent_logs(limit=limit)


@app.get("/api/categories")
def get_categories():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return list(cfg.get("categories", {}).keys())
    return []


@app.get("/api/export")
def export_data(format: str = "json", category: str = "all", min_score: int = 0):
    items, _ = db.get_queries(category=category, min_score=min_score, limit=5000)

    if format.lower() == "csv":
        output = io.StringIO()
        fieldnames = [
            "id", "keyword", "category", "gap_score", "archetype", "trend_type",
            "trend_velocity", "exact_title_matches", "human_verdict", "top_competitor_title",
            "top_competitor_url", "first_seen", "last_updated"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in items:
            writer.writerow(row)
        output.seek(0)
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=gold_miner_export.csv"},
        )

    return JSONResponse(content=items)


@app.get("/api/reports")
def list_reports():
    reports = []
    if os.path.exists(REPORTS_DIR):
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if fname.endswith(".md"):
                fpath = os.path.join(REPORTS_DIR, fname)
                reports.append({
                    "filename": fname,
                    "date": fname.replace("-goldmines.md", "").replace(".md", ""),
                    "size_bytes": os.path.getsize(fpath),
                    "modified": datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M:%S"),
                })
    return reports


@app.get("/api/reports/{filename}")
def read_report(filename: str):
    safe_name = os.path.basename(filename)
    fpath = os.path.join(REPORTS_DIR, safe_name)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Report file not found")
    with open(fpath, "r", encoding="utf-8") as f:
        return PlainTextResponse(content=f.read())


if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 for localhost and LAN (192.168.100.75:8080)
    uvicorn.run("dashboard:app", host="0.0.0.0", port=8080, reload=False)
