"""
FastAPI Dashboard Server for Data Stream Sync & Telemetry Monitor
Serves on http://localhost:8080 (and LAN http://0.0.0.0:8080).
Provides REST endpoints for live opportunities, verdicts, reports, export, frontier queue, and stream controls.
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

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import time
import storage.db as db
from engines.signal_tracer import SignalTracer, DevEvidenceCollector
from engines.filter_pipeline import FilterPipeline, ExclusionShield
from engines.taxonomy_loader import VERTICALS
from engines.evaluator import compute_composite_score
from engines.index_auditor import IndexAuditor, SerpSieve
from engines.stream_sampler import StreamSamplerHTTP, TrendsBatchHTTP, load_cookie_pool
from engines.trends_rss_harvester import GoogleTrendsRSSHarvester, classify_trend_category
from engines.multi_suggester import MultiStreamSuggester
from engines.cluster_engine import get_doable_website_ideas, generate_markdown_production_package

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dashboard")

app = FastAPI(title="Data Stream Sync & Telemetry Monitor", version="5.0")

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
REPORTS_DIR = os.path.join(os.path.dirname(BASE_DIR), "reports")

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
    verdict: str  # 'confirmed_gold', 'already_served', 'snoozed', 'pending'


class BulkVerdictRequest(BaseModel):
    ids: List[int]
    verdict: str


class LiveAuditRequest(BaseModel):
    id: int
    keyword: str


class BatchAuditRequest(BaseModel):
    items: List[LiveAuditRequest]


class InstantProbeRequest(BaseModel):
    term: str
    category: Optional[str] = "Developer & Cloud"


class RecheckFrontierRequest(BaseModel):
    term: str


class AddFrontierRequest(BaseModel):
    term: str
    category: str


class BatchAddFrontierRequest(BaseModel):
    terms: List[str]
    category: str


class SeedExpandRequest(BaseModel):
    topic: str
    preset: str  # 'technical', 'pain_points', 'subtopics', 'comparative', 'emerging', 'tools', 'myth_busting'


class ScanRequest(BaseModel):
    category: Optional[str] = "All"
    limit_batches: Optional[int] = 2


class TrendIngestRequest(BaseModel):
    title: str
    category: Optional[str] = "General"
    geo: Optional[str] = "US"


class AutopilotToggleRequest(BaseModel):
    enabled: bool


def run_pipeline_scan(category_filter: str = "All", limit_batches: int = 2):
    """Background task to run trends batch extraction from frontier queue."""
    global scan_state
    if scan_state["is_scanning"]:
        return

    scan_state["is_scanning"] = True
    scan_state["progress"] = 0
    scan_state["message"] = "Claiming frontier niches..."

    try:
        trends_engine = TrendsBatchHTTP(time_window="today 12-m")
        shield = ExclusionShield()
        sieve = SerpSieve()
        evidence_collector = DevEvidenceCollector()

        queries_discovered = 0
        gold_discovered = 0

        for b_idx in range(1, limit_batches + 1):
            claimed = db.claim_frontier_batch(shard_id=0, total_shards=1, batch_size=8)
            if not claimed:
                scan_state["message"] = "Frontier queue empty. Run niche ingestor to harvest roots."
                break

            terms = [c["niche_term"] for c in claimed]
            scan_state["current_category"] = claimed[0]["category"]
            scan_state["progress"] = b_idx
            scan_state["total"] = limit_batches
            scan_state["message"] = f"Extracting 8-term Trends for: {', '.join(terms[:3])}..."

            batch_results = trends_engine.extract_batch(terms)

            for niche_info in claimed:
                niche_term = niche_info["niche_term"]
                category = niche_info["category"]
                term_data = batch_results.get(niche_term, {})

                # Prioritize genuine Google Trends data (Rising & Top queries)
                candidates = []
                for item in term_data.get("rising", []):
                    candidates.append({**item, "trend_type": "BREAKOUT" if item.get("isBreakout") else "RISING"})
                for item in term_data.get("top", []):
                    candidates.append({**item, "trend_type": "TOP"})

                # Only supplement with intent tree if Google Trends returned fewer than 5 queries
                if len(candidates) < 5:
                    try:
                        suggester = MultiStreamSuggester()
                        intent_queries = suggester.expand_seed_with_intent_trees(niche_term)
                        for iq in intent_queries:
                            # Strict 3+ word filter to avoid generic head terms
                            if len(iq.split()) >= 3:
                                candidates.append({"query": iq, "trend_type": "QUALIFIED_INTENT", "change": "High Intent"})
                    except Exception as ex:
                        logger.debug(f"Suggester expansion failed for {niche_term}: {ex}")

                evaluated_for_niche = 0
                for cand in candidates:
                    query = cand.get("query", "").strip()
                    if not query:
                        continue

                    should_drop, _ = shield.should_drop(query, category=category)
                    if should_drop:
                        continue

                    serp_res = sieve.audit(query)
                    dev_res = evidence_collector.collect(query)
                    score_data = compute_composite_score(
                        serp_score=serp_res["serp_score"],
                        dev_score=dev_res["dev_score"],
                        trend_type=cand.get("trend_type", "TOP"),
                        trend_velocity=cand.get("change", "Stable"),
                        keyword=query,
                        serp_data=serp_res,
                    )

                    gap_score = score_data["gap_score"]
                    if gap_score >= 40:
                        db.upsert_query({
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
                            "evidence": {"serp": serp_res, "dev": dev_res, "score_breakdown": score_data["breakdown"]},
                        })
                        queries_discovered += 1
                        if gap_score >= 75:
                            gold_discovered += 1

                        # RECURSIVE DEEP DRILL-DOWN:
                        # If query is a breakout or uncontested void (<= 1 title matches) and depth < 3:
                        # Automatically queue it as a child seed to research even deeper!
                        depth = niche_info.get("depth_level", 0)
                        if depth < 3 and (serp_res.get("exact_title_matches", 10) <= 1 or cand.get("trend_type") == "BREAKOUT" or gap_score >= 55):
                            words = query.strip().split()
                            if 2 <= len(words) <= 5:
                                queued = db.queue_sub_niche(query, category=category, parent=niche_term, depth=depth + 1)
                                if queued:
                                    logger.info(f"🌱 [RECURSIVE DRILL-DOWN (Depth {depth+1})] Queued child seed: '{query}' under root '{niche_term}'")

                    evaluated_for_niche += 1

                db.mark_frontier_complete(niche_term, queries_extracted=evaluated_for_niche)

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
    return "<h1>Telemetry UI loading... Please refresh in a moment.</h1>"


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
    root: Optional[str] = None,
    trend_type: Optional[str] = None,
    untouched_only: bool = False,
    competition_status: Optional[str] = None,
    sort_by: str = "best_to_build",
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
        root=root,
        trend_type=trend_type,
        untouched_only=untouched_only,
        competition_status=competition_status,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    # Augment with 3-way verification links & evidence
    for item in items:
        q_enc = urllib.parse.quote(item["keyword"])
        item["google_verify_url"] = f"https://www.google.com/search?q={q_enc}"
        item["google_allintitle_url"] = f"https://www.google.com/search?q=allintitle%3A%22{q_enc}%22"
        item["ddg_verify_url"] = f"https://duckduckgo.com/?q={q_enc}"
        item["trends_verify_url"] = f"https://trends.google.com/explore?q={q_enc}&date=today%2012-m"

        if item.get("evidence_json"):
            try:
                item["evidence"] = json.loads(item["evidence_json"])
            except Exception:
                item["evidence"] = {}

        # Defense-in-depth: Never treat an unverified/empty response as exact_title_matches = 0
        raw_results = item.get("evidence", {}).get("serp", {}).get("raw_results", [])
        if not raw_results or len(raw_results) == 0:
            item["exact_title_matches"] = None

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@app.get("/api/website-ideas")
def get_website_ideas_endpoint(limit: int = 60, min_score: int = 50, category: Optional[str] = "all"):
    """Returns clustered, high-doability website ideas with blueprints."""
    ideas = get_doable_website_ideas(limit=limit, min_score=min_score)
    if category and category.lower() != "all":
        ideas = [i for i in ideas if i.get("category", "").lower() == category.lower()]
    return {"ideas": ideas, "total": len(ideas)}


@app.get("/api/blueprint/export")
def export_blueprint_endpoint(topic: str = Query(...)):
    """Generates and downloads a complete turnkey AI production package for a topic."""
    ideas = get_doable_website_ideas(limit=120, min_score=30)
    target_idea = None
    topic_clean = topic.strip().lower()
    for idea in ideas:
        p_kw = idea.get("pillar_keyword", "").lower()
        if p_kw == topic_clean or topic_clean in p_kw:
            target_idea = idea
            break

    if not target_idea and ideas:
        target_idea = ideas[0]

    if not target_idea:
        raise HTTPException(status_code=404, detail="Topic blueprint not found")

    pkg_content = generate_markdown_production_package(target_idea)
    slug = re.sub(r"[^a-z0-9]+", "_", target_idea.get("pillar_keyword", "topic").lower()).strip("_")
    filename = f"{slug}_ai_production_package.md"
    return Response(
        content=pkg_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/trends/live")
def get_live_trends_endpoint(geo: str = "US"):
    """Fetches real-time breakout trends from Google Trends RSS across Tier-1 English geos."""
    harvester = GoogleTrendsRSSHarvester(geos=[geo.upper()])
    items = harvester.fetch_geo_rss(geo.upper())

    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT LOWER(niche_term) FROM frontier_niches")
    existing_terms = {r[0] for r in c.fetchall()}
    c.execute("SELECT LOWER(keyword) FROM queries")
    existing_queries = {r[0] for r in c.fetchall()}
    conn.close()

    for item in items:
        item["category"] = classify_trend_category(item["title"], item.get("snippet", ""))
        clean_title = item["title"].lower().strip()
        item["is_ingested"] = (clean_title in existing_terms or clean_title in existing_queries)

    return {"items": items, "geo": geo.upper(), "total": len(items)}


@app.post("/api/trends/ingest")
def ingest_trend_endpoint(req: TrendIngestRequest, background_tasks: BackgroundTasks):
    """Ingests a live breakout trend, runs Trio-Stream expansion & SERP audit, and clusters it."""
    title = req.title.strip()
    category = req.category or "General"
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    added = db.queue_sub_niche(title, category=category, depth=0)

    def _process_trend_now(kw: str, cat: str):
        try:
            suggester = MultiStreamSuggester()
            sieve = SerpSieve()
            collector = DevEvidenceCollector()
            sub_queries = suggester.expand_seed_with_intent_trees(kw)
            for sq in sub_queries[:12]:
                serp_res = sieve.audit(sq)
                dev_res = collector.collect(sq)
                score_data = compute_composite_score(
                    serp_score=serp_res["serp_score"],
                    dev_score=dev_res["dev_score"],
                    trend_type="BREAKOUT",
                    trend_velocity="10,000+ Searches",
                    keyword=sq,
                    serp_data=serp_res
                )
                db.upsert_query({
                    "keyword": sq,
                    "category": cat,
                    "trend_type": "BREAKOUT",
                    "trend_velocity": "High Breakout",
                    "gap_score": score_data["gap_score"],
                    "archetype": score_data["archetype"],
                    "exact_title_matches": serp_res.get("exact_title_matches", 0),
                    "has_github_issues": False,
                    "has_stack_questions": False,
                    "top_competitor_title": serp_res.get("top_competitor_title", ""),
                    "top_competitor_url": serp_res.get("top_competitor_url", ""),
                    "evidence": {"serp": serp_res, "dev": dev_res, "score_breakdown": score_data["breakdown"]},
                })
        except Exception as e:
            logger.error(f"Error processing trend {kw}: {e}")

    background_tasks.add_task(_process_trend_now, title, category)
    return {"status": "ok", "message": f"Trend '{title}' queued for immediate silo generation", "added": added}


autopilot_state = {
    "is_active": False,
    "last_run": None,
    "cycles_completed": 0,
    "items_discovered": 0,
    "current_status": "Idle"
}
autopilot_thread = None
autopilot_stop_event = threading.Event()


def _autopilot_worker_loop():
    logger.info("Autonomous Auto-Pilot daemon started.")
    harvester = GoogleTrendsRSSHarvester(geos=["US", "GB", "CA", "AU", "IN"])
    while not autopilot_stop_event.is_set():
        try:
            autopilot_state["current_status"] = "Harvesting Live Google Trends Breakouts (US, GB, CA, AU, IN)..."
            autopilot_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trends = harvester.harvest_all_geos()

            # Automatically queue high-value commercial trends into frontier
            ingested = 0
            for t in trends:
                cat = t.get("category", "")
                if cat in [
                    "Finance & Wealth", "Legal & Compliance", "Small Business & B2B",
                    "Real Estate & Living", "Health & Fitness", "Clean Energy & Home",
                    "Travel & Visas", "Productivity & Work", "Developer & Cloud"
                ]:
                    title = t.get("title", "").strip()
                    if title and db.queue_sub_niche(title, category=cat, depth=0):
                        ingested += 1

            autopilot_state["current_status"] = "Drilling into frontier queue (Recursive Depth Scan)..."
            run_pipeline_scan(category_filter="All", limit_batches=2)

            autopilot_state["cycles_completed"] += 1
            autopilot_state["current_status"] = f"Active (Cycle {autopilot_state['cycles_completed']} done, {ingested} breakouts queued)"
        except Exception as e:
            logger.error(f"Auto-pilot cycle error: {e}")
            autopilot_state["current_status"] = f"Cycle paused: {e}"

        # Sleep 300s (5 minutes) with 5s wake checks
        for _ in range(60):
            if autopilot_stop_event.is_set():
                break
            time.sleep(5)

    autopilot_state["current_status"] = "Stopped"
    autopilot_state["is_active"] = False


@app.on_event("startup")
def startup_event():
    """Starts the autonomous recursive discovery daemon automatically on application boot."""
    global autopilot_thread, autopilot_stop_event
    if not autopilot_state["is_active"]:
        autopilot_stop_event.clear()
        autopilot_state["is_active"] = True
        autopilot_thread = threading.Thread(target=_autopilot_worker_loop, daemon=True)
        autopilot_thread.start()
        logger.info("⚡ Autonomous Discovery Auto-Pilot automatically started on startup!")


@app.get("/api/autopilot/status")
def get_autopilot_status():
    return autopilot_state


@app.post("/api/autopilot/toggle")
def toggle_autopilot(req: AutopilotToggleRequest):
    global autopilot_thread, autopilot_stop_event
    if req.enabled:
        if not autopilot_state["is_active"]:
            autopilot_stop_event.clear()
            autopilot_state["is_active"] = True
            autopilot_thread = threading.Thread(target=_autopilot_worker_loop, daemon=True)
            autopilot_thread.start()
            return {"status": "ok", "message": "Autonomous Auto-Pilot enabled", "state": autopilot_state}
        return {"status": "ok", "message": "Auto-Pilot already running", "state": autopilot_state}
    else:
        if autopilot_state["is_active"]:
            autopilot_stop_event.set()
            autopilot_state["is_active"] = False
            return {"status": "ok", "message": "Autonomous Auto-Pilot stopping...", "state": autopilot_state}
        return {"status": "ok", "message": "Auto-Pilot already stopped", "state": autopilot_state}


@app.get("/api/input-keywords")
def get_input_keywords(
    category: Optional[str] = "all",
    status: Optional[str] = "all",
    search: Optional[str] = None,
    sort_by: str = "best_clusters",
    limit: int = 150,
    offset: int = 0,
):
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        conditions = []
        params = []
        if category and category.lower() != "all":
            conditions.append("f.category = ?")
            params.append(category)
        if status and status.lower() != "all":
            conditions.append("f.status = ?")
            params.append(status)
        if search:
            conditions.append("f.niche_term LIKE ?")
            params.append(f"%{search}%")

        where_sql = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"SELECT COUNT(*) as c FROM frontier_niches f {where_sql}", params)
        total = cursor.fetchone()["c"]

        cte_sql = """
            WITH topic_stats AS (
                SELECT 
                    COALESCE(json_extract(evidence_json, '$.parent_niche'), keyword) as topic,
                    COUNT(*) as total_kws,
                    SUM(CASE WHEN exact_title_matches = 0 THEN 1 ELSE 0 END) as zero_comp,
                    SUM(CASE WHEN gap_score >= 65 THEN 1 ELSE 0 END) as high_scores,
                    MAX(gap_score) as max_score
                FROM queries
                GROUP BY topic
            )
        """

        if sort_by == "recent":
            order_clause = "f.last_explored_at DESC, f.id DESC"
        elif sort_by in ("name", "term"):
            order_clause = "f.niche_term ASC"
        elif sort_by == "gaps":
            order_clause = "f.queries_extracted DESC, f.last_explored_at DESC, f.id ASC"
        elif sort_by == "depth":
            order_clause = "f.depth_level ASC, f.queries_extracted DESC"
        else:  # "best_clusters" or default
            order_clause = "cluster_doability_rank DESC, f.queries_extracted DESC, f.id ASC"

        query = f"""
            {cte_sql}
            SELECT 
                f.id, f.niche_term, f.category, f.status, f.queries_extracted, f.depth_level, f.created_at, f.last_explored_at,
                COALESCE(t.zero_comp, 0) as zero_comp_count,
                COALESCE(t.high_scores, 0) as high_score_count,
                (
                    (COALESCE(t.zero_comp, 0) * 60)
                    + (COALESCE(t.high_scores, 0) * 20)
                    + (f.queries_extracted * 3)
                    + COALESCE(t.max_score, 0)
                ) as cluster_doability_rank
            FROM frontier_niches f
            LEFT JOIN topic_stats t ON t.topic = f.niche_term
            {where_sql}
            ORDER BY {order_clause}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [limit, offset])
        rows = [dict(r) for r in cursor.fetchall()]
        return {"items": rows, "total": total}
    finally:
        conn.close()


@app.post("/api/frontier/harvest")
def trigger_harvester(background_tasks: BackgroundTasks):
    from engines.taxonomy_loader import TaxonomyLoader
    loader = TaxonomyLoader()
    background_tasks.add_task(loader.run_all)
    return {"status": "success", "message": "Multi-source taxonomy harvester started in background"}


@app.post("/api/verdict")
def set_verdict(req: VerdictRequest):
    success = db.update_verdict(req.id, req.verdict)
    if not success:
        raise HTTPException(status_code=404, detail="Query ID not found")
    return {"status": "ok", "id": req.id, "verdict": req.verdict}


@app.post("/api/bulk-verdict")
def bulk_verdict(req: BulkVerdictRequest):
    updated = db.bulk_update_verdict(req.ids, req.verdict)
    return {"status": "ok", "updated_count": updated, "verdict": req.verdict}


@app.get("/api/frontier")
def get_frontier(
    category: Optional[str] = "all",
    status: Optional[str] = "all",
    depth_level: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 40,
):
    offset = (page - 1) * limit
    items, total = db.get_frontier_page(
        category=category,
        status=status,
        depth_level=depth_level,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@app.get("/api/frontier/stats")
def get_frontier_stats():
    return db.get_frontier_stats()


@app.post("/api/frontier/add")
def add_frontier_seed(req: AddFrontierRequest):
    if not req.term.strip():
        raise HTTPException(status_code=400, detail="Seed term cannot be empty")
    added = db.queue_sub_niche(req.term, category=req.category, depth=0)
    return {"status": "ok" if added else "exists_or_cooldown", "term": req.term, "added": added}


@app.post("/api/frontier/add-batch")
def add_frontier_batch(req: BatchAddFrontierRequest):
    added_count = 0
    for t in req.terms:
        clean = t.strip()
        if clean and db.queue_sub_niche(clean, category=req.category, depth=0):
            added_count += 1
    return {"status": "ok", "added_count": added_count, "total_submitted": len(req.terms)}


@app.post("/api/seeds/expand")
def expand_seeds(req: SeedExpandRequest):
    topic = req.topic.strip().lower()
    preset = req.preset.lower()

    PATTERNS = {
        "technical": [
            f"{topic} cli", f"{topic} api error", f"{topic} configuration",
            f"{topic} architecture diagram", f"{topic} benchmarking", f"{topic} sdk documentation",
            f"{topic} docker compose", f"{topic} open telemetry", f"{topic} rate limit",
            f"{topic} webhook payload"
        ],
        "pain_points": [
            f"{topic} error codes", f"{topic} not working", f"{topic} connection timeout",
            f"{topic} workaround", f"{topic} high cpu memory", f"{topic} deprecation fix",
            f"{topic} silent failure", f"{topic} permission denied", f"{topic} slow query"
        ],
        "subtopics": [
            f"{topic} best practices", f"{topic} checklist", f"{topic} design principles",
            f"{topic} security hardening", f"{topic} schema design", f"{topic} automated testing",
            f"{topic} monitoring metrics", f"{topic} latency optimization"
        ],
        "comparative": [
            f"{topic} vs", f"{topic} alternative open source", f"{topic} vs competitor",
            f"{topic} migration guide", f"{topic} lightweight replacement", f"is {topic} obsolete"
        ],
        "emerging": [
            f"{topic} llm integration", f"{topic} ai agent", f"{topic} serverless",
            f"{topic} wasm edge", f"{topic} modern stack 2026", f"{topic} realtime websocket"
        ],
        "tools": [
            f"{topic} calculator", f"{topic} generator", f"{topic} converter online",
            f"{topic} validator", f"{topic} formatter", f"{topic} visualizer",
            f"{topic} cheat sheet", f"{topic} interactive sandbox"
        ],
        "myth_busting": [
            f"why {topic} is bad", f"{topic} common mistakes", f"when not to use {topic}",
            f"{topic} anti patterns", f"is {topic} worth it"
        ]
    }

    seeds = PATTERNS.get(preset, PATTERNS["tools"])
    return {"topic": topic, "preset": preset, "seeds": seeds}


@app.get("/api/serp/compare")
def compare_serps(q1: str, q2: str):
    q1 = q1.strip()
    q2 = q2.strip()
    if not q1 or not q2:
        raise HTTPException(status_code=400, detail="Both q1 and q2 are required")

    conn = db.get_connection()
    results1 = []
    results2 = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT evidence_json FROM queries WHERE keyword = ?", (q1,))
        r1 = cur.fetchone()
        if r1 and r1["evidence_json"]:
            try:
                ev1 = json.loads(r1["evidence_json"])
                results1 = ev1.get("serp", {}).get("raw_results", [])
            except Exception:
                pass

        cur.execute("SELECT evidence_json FROM queries WHERE keyword = ?", (q2,))
        r2 = cur.fetchone()
        if r2 and r2["evidence_json"]:
            try:
                ev2 = json.loads(r2["evidence_json"])
                results2 = ev2.get("serp", {}).get("raw_results", [])
            except Exception:
                pass
    finally:
        conn.close()

    sieve = SerpSieve()
    if not results1:
        results1 = sieve.fetch_serp(q1)
    if not results2:
        results2 = sieve.fetch_serp(q2)

    def norm_domain(url: str):
        try:
            netloc = urllib.parse.urlparse(url).netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    domains1 = [norm_domain(r.get("url", "")) for r in results1 if r.get("url")]
    domains2 = [norm_domain(r.get("url", "")) for r in results2 if r.get("url")]

    pairs = []
    common_domains = set(domains1).intersection(set(domains2)) - {""}
    for idx1, d1 in enumerate(domains1):
        if d1 in common_domains:
            for idx2, d2 in enumerate(domains2):
                if d1 == d2:
                    pairs.append({
                        "domain": d1,
                        "rank1": idx1 + 1,
                        "rank2": idx2 + 1,
                        "title1": results1[idx1].get("title", ""),
                        "title2": results2[idx2].get("title", ""),
                        "url1": results1[idx1].get("url", ""),
                        "url2": results2[idx2].get("url", ""),
                    })

    union = len(set(domains1).union(set(domains2)))
    similarity_pct = round((len(common_domains) / union * 100)) if union > 0 else 0

    if similarity_pct >= 50:
        verdict = f"High SERP Similarity ({similarity_pct}%) — Google treats these as the same user intent. Build 1 comprehensive authority page/tool covering both."
        action = "Consolidate into 1 Page/Tool"
    elif similarity_pct >= 20:
        verdict = f"Moderate Overlap ({similarity_pct}%) — Shared conceptual space with distinct ranking angles. Build 1 main tool with a dedicated sub-tool."
        action = "Build Pillar + Sub-tool"
    else:
        verdict = f"Low SERP Similarity ({similarity_pct}%) — Untouched Independent Voids! Google treats '{q1}' and '{q2}' as completely separate problems. Build 2 standalone tools/pages."
        action = "Build 2 Independent Tools"

    return {
        "q1": q1,
        "q2": q2,
        "results1": results1[:10],
        "results2": results2[:10],
        "common_count": len(common_domains),
        "similarity_pct": similarity_pct,
        "verdict": verdict,
        "action": action,
        "pairs": pairs,
    }


@app.post("/api/serp/audit-live")
def audit_serp_live(req: LiveAuditRequest):
    sieve = SerpSieve()
    serp_res = sieve.audit_serp(req.keyword)

    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT evidence_json, gap_score FROM queries WHERE id = ?", (req.id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Query not found")

        ev = json.loads(row["evidence_json"]) if row["evidence_json"] else {}
        ev["serp"] = serp_res

        # Recompute score with real verified SERP data
        serp_pts = serp_res.get("serp_score", 0)
        dev_pts = ev.get("dev", {}).get("dev_score", 15)
        vel_pts = 20 if ev.get("score_breakdown", {}).get("velocity") else 10
        new_score = min(100, max(0, serp_pts + dev_pts + vel_pts))

        exact_matches = serp_res.get("exact_title_matches")  # None if 0 results
        top_title = serp_res.get("top_competitor_title", "")
        top_url = serp_res.get("top_competitor_url", "")

        cur.execute("""
            UPDATE queries
            SET exact_title_matches = ?, top_competitor_title = ?, top_competitor_url = ?, gap_score = ?, evidence_json = ?
            WHERE id = ?
        """, (exact_matches, top_title, top_url, new_score, json.dumps(ev), req.id))
        conn.commit()

        return {
            "status": "ok",
            "id": req.id,
            "exact_title_matches": exact_matches,
            "results_count": serp_res.get("results_count", 0),
            "top_competitor_title": top_title,
            "top_competitor_url": top_url,
            "new_score": new_score,
            "evidence": ev,
        }
    finally:
        conn.close()


@app.post("/api/serp/audit-batch")
def audit_serp_batch(req: BatchAuditRequest):
    sieve = SerpSieve()
    results = []
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        for item in req.items[:15]:  # Safety limit: max 15 per batch
            serp_res = sieve.audit_serp(item.keyword)
            cur.execute("SELECT evidence_json, gap_score FROM queries WHERE id = ?", (item.id,))
            row = cur.fetchone()
            if not row:
                continue

            ev = json.loads(row["evidence_json"]) if row["evidence_json"] else {}
            ev["serp"] = serp_res

            serp_pts = serp_res.get("serp_score", 0)
            dev_pts = ev.get("dev", {}).get("dev_score", 15)
            vel_pts = 20 if ev.get("score_breakdown", {}).get("velocity") else 10
            new_score = min(100, max(0, serp_pts + dev_pts + vel_pts))

            exact_matches = serp_res.get("exact_title_matches")
            top_title = serp_res.get("top_competitor_title", "")
            top_url = serp_res.get("top_competitor_url", "")

            cur.execute("""
                UPDATE queries
                SET exact_title_matches = ?, top_competitor_title = ?, top_competitor_url = ?, gap_score = ?, evidence_json = ?
                WHERE id = ?
            """, (exact_matches, top_title, top_url, new_score, json.dumps(ev), item.id))
            conn.commit()

            results.append({
                "id": item.id,
                "exact_title_matches": exact_matches,
                "results_count": serp_res.get("results_count", 0),
                "top_competitor_title": top_title,
                "top_competitor_url": top_url,
                "new_score": new_score,
                "evidence": ev,
            })
            time.sleep(random.uniform(0.3, 0.6))

        return {"status": "ok", "audited": results}
    finally:
        conn.close()


@app.post("/api/probe/instant")
def instant_probe_endpoint(req: InstantProbeRequest, background_tasks: BackgroundTasks):
    from engines.rechecker import recheck_term
    background_tasks.add_task(recheck_term, req.term, req.category)
    return {"status": "ok", "message": f"Instant live probe launched for '{req.term}'"}


@app.post("/api/frontier/recheck")
def recheck_frontier_endpoint(req: RecheckFrontierRequest):
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        sig = db.compute_signature(req.term)
        cur.execute("DELETE FROM explored_signatures WHERE signature_hash = ?", (sig,))
        cur.execute("UPDATE frontier_niches SET status = 'pending', queries_extracted = 0 WHERE niche_term = ?", (req.term,))
        conn.commit()
        return {"status": "ok", "message": f"Frontier term '{req.term}' reset to pending"}
    finally:
        conn.close()


@app.get("/api/cookies/status")
def get_cookies_status():
    pool = load_cookie_pool()
    return {
        "active_count": len(pool),
        "status": "ready" if pool else "anonymous_fallback",
        "shards_supported": len(pool) if pool else 1,
    }


@app.post("/api/scan")
def trigger_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    if scan_state["is_scanning"]:
        return {"status": "busy", "message": "Scan already in progress", "scan_state": scan_state}

    background_tasks.add_task(run_pipeline_scan, req.category or "All", req.limit_batches or 2)
    return {"status": "started", "message": f"Scan triggered for category: {req.category}"}


@app.get("/api/scan/status")
def get_scan_status():
    return scan_state


@app.get("/api/logs")
def get_logs(limit: int = 40):
    return db.get_recent_logs(limit=limit)


@app.get("/api/categories")
def get_categories():
    return VERTICALS


@app.get("/api/export")
def export_data(
    format: str = "json",
    scope: str = "all",
    category: str = "all",
    min_score: int = 0,
    competition_status: Optional[str] = "all",
    verdict: Optional[str] = None,
    sort_by: str = "best_to_build",
    limit: int = 5000,
):
    """
    Comprehensive, AI-Ready Export Engine.
    Exports full database or active filtered view with rich competitive intelligence,
    raw SERP competitor analysis, cluster hierarchies, and monetization RPM projections.
    """
    cat_filter = None if (scope == "all" or category.lower() == "all") else category
    score_filter = 0 if scope == "all" else min_score
    comp_filter = None if (scope == "all" or competition_status == "all") else competition_status

    items, total = db.get_queries(
        category=cat_filter,
        min_score=score_filter,
        competition_status=comp_filter,
        verdict=verdict if scope != "all" else None,
        sort_by=sort_by,
        limit=limit,
    )

    enriched_items = []
    for it in items:
        ev = {}
        if it.get("evidence_json"):
            try:
                ev = json.loads(it["evidence_json"]) if isinstance(it["evidence_json"], str) else it["evidence_json"]
            except Exception:
                ev = {}

        serp = ev.get("serp", {})
        dev = ev.get("dev", {})
        raw_serp = serp.get("raw_results", [])

        cat = it.get("category", "General")
        if cat in ("Finance & Wealth", "Legal & Compliance"):
            rpm_est = "$60 - $150 RPM (High Value / Lead-Gen)"
        elif cat in ("Small Business & B2B", "Real Estate & Living"):
            rpm_est = "$40 - $90 RPM (B2B SaaS / Affiliate)"
        elif cat in ("Health & Fitness", "Travel & Visas"):
            rpm_est = "$30 - $70 RPM (Sponsor / AdSense)"
        else:
            rpm_est = "$20 - $50 RPM (Programmatic Display)"

        is_zero_comp = it.get("exact_title_matches") == 0
        exact_matches = it.get("exact_title_matches")
        matches_label = f"{exact_matches}/10" if exact_matches is not None else "Not Checked"

        enriched = {
            "id": it.get("id"),
            "keyword": it.get("keyword"),
            "category": cat,
            "gap_score": it.get("gap_score", 0),
            "doability_rank": it.get("doability_rank", 0),
            "tool_archetype": it.get("archetype", "Recipe"),
            "trend_velocity": it.get("trend_velocity", "Stable"),
            "trend_type": it.get("trend_type", "TOP"),
            "google_exact_title_matches": matches_label,
            "is_zero_competition_void": is_zero_comp,
            "parent_cluster": it.get("cluster_name", cat),
            "cluster_total_keywords": it.get("cluster_kws", 1),
            "cluster_zero_comp_voids": it.get("cluster_zeros", 0),
            "top_competitor_title": it.get("top_competitor_title", ""),
            "top_competitor_url": it.get("top_competitor_url", ""),
            "monetization_rpm_estimate": rpm_est,
            "serp_signals": {
                "forum_count_in_top10": serp.get("forum_count", 0),
                "top_forum_rank": serp.get("top_forum_rank"),
                "root_domain_in_top5": serp.get("root_domain_in_top5", False),
                "has_stale_content": serp.get("has_stale_content", False),
            },
            "dev_signals": {
                "github_issues": bool(it.get("has_github_issues")),
                "stack_questions": bool(it.get("has_stack_questions")),
            },
            "top_competitors": [
                {
                    "rank": idx + 1,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                }
                for idx, r in enumerate(raw_serp[:5])
            ],
            "first_seen": it.get("first_seen", ""),
            "last_updated": it.get("last_updated", ""),
        }
        enriched_items.append(enriched)

    timestamp = datetime.utcnow().strftime("%Y-%m-%d")

    if format.lower() == "csv":
        output = io.StringIO()
        fieldnames = [
            "id", "keyword", "category", "gap_score", "google_exact_title_matches",
            "is_zero_competition_void", "tool_archetype", "trend_velocity", "parent_cluster",
            "cluster_total_keywords", "cluster_zero_comp_voids", "monetization_rpm_estimate",
            "top_competitor_title", "top_competitor_url", "forum_count_in_top10",
            "competitor_2_title", "competitor_2_url", "competitor_3_title", "competitor_3_url",
            "first_seen", "last_updated"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for it in enriched_items:
            comps = it.get("top_competitors", [])
            row = {
                "id": it["id"],
                "keyword": it["keyword"],
                "category": it["category"],
                "gap_score": it["gap_score"],
                "google_exact_title_matches": it["google_exact_title_matches"],
                "is_zero_competition_void": "YES" if it["is_zero_competition_void"] else "NO",
                "tool_archetype": it["tool_archetype"],
                "trend_velocity": it["trend_velocity"],
                "parent_cluster": it["parent_cluster"],
                "cluster_total_keywords": it["cluster_total_keywords"],
                "cluster_zero_comp_voids": it["cluster_zero_comp_voids"],
                "monetization_rpm_estimate": it["monetization_rpm_estimate"],
                "top_competitor_title": it["top_competitor_title"],
                "top_competitor_url": it["top_competitor_url"],
                "forum_count_in_top10": it["serp_signals"]["forum_count_in_top10"],
                "competitor_2_title": comps[1]["title"] if len(comps) > 1 else "",
                "competitor_2_url": comps[1]["url"] if len(comps) > 1 else "",
                "competitor_3_title": comps[2]["title"] if len(comps) > 2 else "",
                "competitor_3_url": comps[2]["url"] if len(comps) > 2 else "",
                "first_seen": it["first_seen"],
                "last_updated": it["last_updated"],
            }
            writer.writerow(row)
        output.seek(0)
        filename = f"search_gaps_{scope}_{timestamp}.csv"
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    if format.lower() in ("markdown", "prompt"):
        zero_voids = [x for x in enriched_items if x["is_zero_competition_void"]]
        lines = [
            f"# 🎯 Autonomous Search Void Intelligence Dossier ({timestamp})",
            "",
            "> **Generated by Data Stream Sync Autonomous Discovery Engine**",
            f"> Scope: **{scope.upper()}** | Total Evaluated Opportunities: **{len(enriched_items)}** | Untouched Voids (0/10): **{len(zero_voids)}**",
            "",
            "---",
            "",
            "## 🤖 AI Execution & Evaluation Prompt (Copy & Paste to Claude / GPT / Gemini)",
            "",
            "```text",
            "Act as an elite Niche Website Investor, Senior SEO Architect, and Micro-SaaS Product Manager.",
            "",
            "I have provided a vetted intelligence dossier of uncontested Google search voids discovered by an automated telemetry engine.",
            "Each opportunity represents an authentic search query where 0 out of 10 top pages target the exact title,",
            "leaving the SERP vulnerable to forum threads, generic homepages, or outdated content.",
            "",
            "YOUR PRIMARY OBJECTIVE:",
            "Analyze all the opportunities in this dataset and identify the #1 SINGLE BEST NICHE to build a brand new, high-authority,",
            "profitable niche website from scratch. Do NOT give me scattered, random keywords across different industries.",
            "Group the keywords into topical clusters and choose the single most lucrative, easiest-to-rank niche silo.",
            "",
            "CRITERIA FOR THE #1 BEST NICHE:",
            "1. Deep Cluster of 0/10 Voids: Must have at least 5 to 15 related zero-competition search voids in this dataset so the new site has an entire topical cluster ready to launch.",
            "2. High Commercial Intent & RPM: Must have proven monetization ($50 to $150 RPM through lead generation, high-ticket affiliate, or high-CPM display ads).",
            "3. Beatable Google SERP: The current ranking pages on Google are weak Reddit/Quora threads, outdated articles, or generic root pages that don't directly answer the query.",
            "4. Interactive Tool / Calculator Potential: Can be anchored by a simple 1-page interactive web tool (e.g. calculator, decision tree, or template generator) that acts as a link magnet.",
            "",
            "DELIVERABLES:",
            "1. The Winning Niche Selection:",
            "   - Name of the Niche & Core Target Audience.",
            "   - Why this beat all other niches in the dataset (ROI vs effort analysis).",
            "   - 3 Brandable .com Domain Name ideas.",
            "   - Projected Revenue Model (how this site reaches $3,000–$10,000/month).",
            "",
            "2. Complete Website Silo Architecture (The Site Map):",
            "   - Flagship Interactive Asset: Exact specification for the 1-page web tool / calculator / template to build on the homepage (features, inputs, outputs).",
            "   - Cornerstone Pillar Page: 2,500-word comprehensive master guide outline targeting the main parent term.",
            "   - 8 Supporting Cluster Articles: Select 8 exact 0/10 keywords from this dataset that will link up to the pillar page to create complete topical authority.",
            "",
            "3. 14-Day Step-by-Step Launch Blueprint:",
            "   - Days 1-3: Domain setup & interactive tool coding.",
            "   - Days 4-7: Pillar page + first 3 cluster articles.",
            "   - Days 8-11: Remaining 5 cluster articles + internal linking structure.",
            "   - Days 12-14: Schema markup, sitemap submission & monetization integration.",
            "",
            "4. Top 2 Runner-Up Niches:",
            "   - In case I want to build in an alternative vertical, provide the #2 and #3 best niche clusters with their revenue potential.",
            "```",
            "",
            "---",
            "",
            "## 🏆 Top Uncontested 0/10 Opportunities (Ready to Build)",
            "",
            "| # | Target Keyword | Vertical | Score | Tool Format | Projected RPM | Top Google Competitor |",
            "| :--- | :--- | :--- | :---: | :--- | :--- | :--- |",
        ]

        for idx, it in enumerate(zero_voids[:50]):
            comp_short = (it['top_competitor_title'][:40] + "...") if len(it['top_competitor_title']) > 40 else it['top_competitor_title']
            lines.append(f"| {idx+1} | **{it['keyword']}** | {it['category']} | `{it['gap_score']}/100` | {it['tool_archetype']} | {it['monetization_rpm_estimate'].split(' ')[0]} | {comp_short or 'None'} |")

        lines.extend([
            "",
            "---",
            "",
            "## 🔬 Deep Opportunity Analysis (Top 15 Breakdowns)",
            "",
        ])

        for idx, it in enumerate(zero_voids[:15]):
            lines.extend([
                f"### {idx+1}. `{it['keyword']}`",
                f"- **Vertical**: {it['category']} | **Parent Cluster**: `{it['parent_cluster']}`",
                f"- **Opportunity Score**: **{it['gap_score']}/100** | **Velocity**: `{it['trend_velocity']}`",
                f"- **Google Competition**: **`{it['google_exact_title_matches']}` (100% Untargeted Title Void)**",
                f"- **Recommended Asset**: {it['tool_archetype']}",
                f"- **Monetization Projection**: {it['monetization_rpm_estimate']}",
                f"- **SERP Vulnerability**: {it['serp_signals']['forum_count_in_top10']} forum results ranking in top 10.",
                f"- **Top Current Competitor**: [{it['top_competitor_title'] or 'None'}]({it['top_competitor_url'] or '#'})",
                "",
                "```json",
                json.dumps({
                    "keyword": it["keyword"],
                    "category": it["category"],
                    "top_competitors": it["top_competitors"],
                    "serp_signals": it["serp_signals"]
                }, indent=2),
                "```",
                "",
            ])

        filename = f"search_gaps_ai_prompt_dossier_{timestamp}.md"
        return Response(
            content="\n".join(lines),
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # Default: Deep AI-Ready JSON
    payload = {
        "metadata": {
            "engine": "Data Stream Sync Autonomous Radar",
            "scope": scope,
            "total_opportunities": len(enriched_items),
            "zero_competition_voids": sum(1 for x in enriched_items if x["is_zero_competition_void"]),
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "ai_prompt_instructions": (
                "Identify the #1 SINGLE BEST NICHE CLUSTER in this dataset to build a complete new authority website from scratch. "
                "Group opportunities by parent_cluster and select the cluster with the highest monetization potential ($50-$150 RPM) "
                "and at least 5-15 zero-competition voids (is_zero_competition_void=true). "
                "Deliver a turnkey website plan: 3 brandable domain names, 1-page interactive tool specification (the hook), "
                "a 2,500-word cornerstone pillar page outline, and 8 supporting cluster articles selected directly from the dataset."
            ),
        },
        "opportunities": enriched_items,
    }
    filename = f"search_gaps_ai_dossier_{scope}_{timestamp}.json"
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


FLEET_REPOS = [
    {
        "name": "web-metric-evaluator",
        "description": "Automated web performance latency and endpoint metric collector",
        "shards": [0, 1, 2, 3],
        "verticals": ["Media & Converters", "Productivity & Work"],
        "url": "https://github.com/dadasadac6/web-metric-evaluator"
    },
    {
        "name": "stream-pipeline-core",
        "description": "High-throughput stream processing pipeline and event transformation framework",
        "shards": [4, 5, 6, 7],
        "verticals": ["Developer & Cloud", "AI/LLM", "Databases"],
        "url": "https://github.com/dadasadac6/stream-pipeline-core"
    },
    {
        "name": "network-pulse-monitor",
        "description": "Distributed network reachability monitor and synthetic latency probe",
        "shards": [8, 9, 10, 11],
        "verticals": ["Finance & Wealth", "Small Business & B2B", "Legal & Compliance"],
        "url": "https://github.com/dadasadac6/network-pulse-monitor"
    },
    {
        "name": "edge-latency-bench",
        "description": "Endpoint latency benchmark, health probe, and availability evaluator",
        "shards": [12, 13, 14, 15],
        "verticals": ["Health & Fitness", "Real Estate & Living"],
        "url": "https://github.com/dadasadac6/edge-latency-bench"
    },
    {
        "name": "endpoint-telemetry-node",
        "description": "Distributed endpoint telemetry runner and synthetic signal aggregator",
        "shards": [16, 17, 18, 19],
        "verticals": ["Gaming & Entertainment", "Travel & Visas", "Academic & Education", "E-Commerce & Selling"],
        "url": "https://github.com/dadasadac6/endpoint-telemetry-node"
    },
    {
        "name": "data-stream-sync",
        "description": "Automated data pipeline, telemetry diagnostics, and local event synchronization engine",
        "shards": [20],
        "verticals": ["Central Aggregation", "Niche Radar"],
        "url": "https://github.com/dadasadac6/data-stream-sync"
    }
]


@app.get("/api/fleet/status")
def get_fleet_status():
    return {
        "total_repositories": len(FLEET_REPOS),
        "total_concurrent_runners": 20,
        "repositories": FLEET_REPOS,
        "is_public_unlimited": True,
    }


@app.post("/api/fleet/dispatch")
def trigger_fleet_dispatch(background_tasks: BackgroundTasks, batches: int = Query(default=3)):
    import tools.fleet_sync as fleet_sync
    background_tasks.add_task(fleet_sync.dispatch_fleet, max_batches=batches)
    return {"status": "success", "message": f"Dispatched 20 runners across 5 repos (max_batches={batches})"}


@app.post("/api/fleet/sync")
def trigger_fleet_sync(background_tasks: BackgroundTasks):
    import tools.fleet_sync as fleet_sync
    background_tasks.add_task(fleet_sync.sync_fleet)
    return {"status": "success", "message": "Fleet synchronization started"}


@app.get("/api/reports")
def list_reports():
    reports = []
    if os.path.exists(REPORTS_DIR):
        for fname in sorted(os.listdir(REPORTS_DIR), reverse=True):
            if fname.endswith(".md"):
                fpath = os.path.join(REPORTS_DIR, fname)
                repo_tag = "central"
                for r in FLEET_REPOS:
                    if fname.startswith(r["name"] + "-"):
                        repo_tag = r["name"]
                        break
                clean_date = fname.replace("-telemetry-audit.md", "").replace("-goldmines.md", "").replace(".md", "")
                if repo_tag != "central":
                    clean_date = clean_date.replace(repo_tag + "-", "")
                reports.append({
                    "filename": fname,
                    "repo": repo_tag,
                    "date": clean_date,
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
