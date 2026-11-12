"""
FastAPI Dashboard Server for Search Gap Radar & Stealth Swarm (Gold Miner)
Serves on http://localhost:8080 (and LAN http://0.0.0.0:8080).
Provides REST endpoints for live opportunities, verdicts, reports, export, frontier queue, and swarm controls.
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
from engines.signal_tracer import SignalTracer, DevEvidenceCollector
from engines.filter_pipeline import FilterPipeline, ExclusionShield
from engines.taxonomy_loader import VERTICALS
from engines.evaluator import compute_composite_score
from engines.index_auditor import IndexAuditor, SerpSieve
from engines.stream_sampler import StreamSamplerHTTP, TrendsBatchHTTP, load_cookie_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dashboard")

app = FastAPI(title="Search Gap Radar & Stealth Swarm", version="5.0")

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

                candidates = []
                for item in term_data.get("rising", []):
                    candidates.append({**item, "trend_type": "BREAKOUT" if item.get("isBreakout") else "RISING"})
                for item in term_data.get("top", []):
                    candidates.append({**item, "trend_type": "TOP"})

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
    root: Optional[str] = None,
    trend_type: Optional[str] = None,
    untouched_only: bool = False,
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
        root=root,
        trend_type=trend_type,
        untouched_only=untouched_only,
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

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if limit > 0 else 1,
    }


@app.get("/api/input-keywords")
def get_input_keywords(
    category: Optional[str] = "all",
    status: Optional[str] = "all",
    search: Optional[str] = None,
    sort_by: str = "queries_extracted",
    limit: int = 150,
    offset: int = 0,
):
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        conditions = []
        params = []
        if category and category.lower() != "all":
            conditions.append("category = ?")
            params.append(category)
        if status and status.lower() != "all":
            conditions.append("status = ?")
            params.append(status)
        if search:
            conditions.append("niche_term LIKE ?")
            params.append(f"%{search}%")

        where_sql = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        cursor.execute(f"SELECT COUNT(*) as c FROM frontier_niches {where_sql}", params)
        total = cursor.fetchone()["c"]

        if sort_by == "recent":
            order_clause = "last_explored_at DESC, id DESC"
        elif sort_by == "term":
            order_clause = "niche_term ASC"
        else:
            order_clause = "queries_extracted DESC, last_explored_at DESC, id ASC"

        query = f"""
            SELECT id, niche_term, category, status, queries_extracted, depth_level, created_at, last_explored_at
            FROM frontier_niches
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

    if format.lower() == "markdown":
        lines = [
            f"# 💎 Gold Mine Action Checklist ({datetime.utcnow().strftime('%Y-%m-%d')})",
            "",
            "> Exported from Autonomous Search Gap Radar",
            "",
            "## 💎 Critical Gold Mines (Score >= 85)",
        ]
        for it in items:
            if it.get("gap_score", 0) >= 85:
                lines.append(f"- [ ] **{it['keyword']}** [{it['category']} / {it['archetype']}] — Score: {it['gap_score']}/100")

        lines.extend(["", "## ⚡ High Opportunities (Score 65-84)"])
        for it in items:
            if 65 <= it.get("gap_score", 0) < 85:
                lines.append(f"- [ ] **{it['keyword']}** [{it['category']} / {it['archetype']}] — Score: {it['gap_score']}/100")

        return Response(
            content="\n".join(lines),
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=gold_mine_checklist.md"},
        )

    return JSONResponse(content=items)


FLEET_REPOS = [
    {
        "name": "ecosystem-telemetry-probe",
        "description": "Distributed runtime health probe and dependency matrix verification",
        "shards": [0, 1, 2, 3],
        "verticals": ["Media & Converters", "Productivity & Work"],
        "url": "https://github.com/beachjampore-lab/ecosystem-telemetry-probe"
    },
    {
        "name": "matrix-stream-probe",
        "description": "Distributed streaming matrix benchmark and telemetry probes",
        "shards": [4, 5, 6, 7],
        "verticals": ["Developer & Cloud", "AI/LLM", "Databases"],
        "url": "https://github.com/beachjampore-lab/matrix-stream-probe"
    },
    {
        "name": "runtime-audit-probe",
        "description": "Runtime service health auditor and entropy monitoring matrix",
        "shards": [8, 9, 10, 11],
        "verticals": ["Finance & Wealth", "Small Business & B2B", "Legal & Compliance"],
        "url": "https://github.com/beachjampore-lab/runtime-audit-probe"
    },
    {
        "name": "node-matrix-sampler",
        "description": "High-throughput node sampling matrix and distributed state probe",
        "shards": [12, 13, 14, 15],
        "verticals": ["Health & Fitness", "Real Estate & Living"],
        "url": "https://github.com/beachjampore-lab/node-matrix-sampler"
    },
    {
        "name": "distributed-signal-core",
        "description": "Distributed telemetry signal core and matrix evaluation suite",
        "shards": [16, 17, 18, 19],
        "verticals": ["Gaming & Entertainment", "Travel & Visas", "Academic & Education", "E-Commerce & Selling"],
        "url": "https://github.com/beachjampore-lab/distributed-signal-core"
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
