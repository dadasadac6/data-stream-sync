"""
Distributed State & Matrix Storage Layer
SQLite storage with WAL mode, indexing, deduplication, state queue, and signature cache.
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "telemetry_matrix.db")
LEGACY_DB_PATH = os.path.join(os.path.dirname(__file__), "niche_gaps.db")
if not os.path.exists(DB_PATH) and os.path.exists(LEGACY_DB_PATH):
    os.rename(LEGACY_DB_PATH, DB_PATH)


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable Write-Ahead Logging (WAL) for high concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                trend_type TEXT NOT NULL,          -- 'BREAKOUT', 'RISING', 'TOP'
                trend_velocity TEXT,               -- e.g. '+3,200%', 'Breakout'
                gap_score INTEGER NOT NULL,        -- 0 to 100
                archetype TEXT NOT NULL,           -- 'Micro-Tool', 'Workaround', 'Template', 'Comparison'
                exact_title_matches INTEGER DEFAULT 0,
                has_github_issues BOOLEAN DEFAULT 0,
                has_stack_questions BOOLEAN DEFAULT 0,
                top_competitor_title TEXT,
                top_competitor_url TEXT,
                human_verdict TEXT DEFAULT 'pending', -- 'confirmed_gold', 'already_served', 'snoozed', 'pending'
                evidence_json TEXT,                -- Detailed signals JSON
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_gap_score ON queries(gap_score DESC);
            CREATE INDEX IF NOT EXISTS idx_archetype ON queries(archetype);
            CREATE INDEX IF NOT EXISTS idx_verdict ON queries(human_verdict);
            CREATE INDEX IF NOT EXISTS idx_category ON queries(category);
            CREATE INDEX IF NOT EXISTS idx_keyword ON queries(keyword);

            CREATE TABLE IF NOT EXISTS scan_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_name TEXT,
                category TEXT,
                queries_found INTEGER DEFAULT 0,
                gold_found INTEGER DEFAULT 0,
                log_message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS frontier_niches (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                niche_term        TEXT UNIQUE NOT NULL,
                category          TEXT NOT NULL,
                parent_niche      TEXT DEFAULT NULL,
                depth_level       INTEGER DEFAULT 0,       -- 0=root, 1=sub-niche, 2=micro, 3=ultra-micro
                status            TEXT DEFAULT 'pending',  -- 'pending', 'claimed', 'completed', 'failed'
                queries_extracted INTEGER DEFAULT 0,
                claimed_by_shard  TEXT DEFAULT NULL,
                last_explored_at  TIMESTAMP DEFAULT NULL,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier_niches(status, depth_level);
            CREATE INDEX IF NOT EXISTS idx_frontier_category ON frontier_niches(category);

            CREATE TABLE IF NOT EXISTS explored_signatures (
                signature_hash TEXT PRIMARY KEY,
                normalized_term TEXT NOT NULL,
                explored_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_signature_date ON explored_signatures(explored_at);
            """
        )
    conn.close()


def normalize_term(term: str) -> str:
    """Normalizes term for signature hashing and deduplication."""
    return " ".join(term.strip().lower().split())


def compute_signature(term: str) -> str:
    """Returns SHA-256 signature hash for a term."""
    return hashlib.sha256(normalize_term(term).encode("utf-8")).hexdigest()


# -------------------------------------------------------------
# 90-Day Cooldown & Explored Signatures Memory
# -------------------------------------------------------------

def is_signature_explored(term: str, cooldown_days: int = 90, db_path: Optional[str] = None) -> bool:
    """Checks whether a term has been explored within the cooldown window (default: 90 days)."""
    sig = compute_signature(term)
    cutoff = (datetime.utcnow() - timedelta(days=cooldown_days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT signature_hash FROM explored_signatures
            WHERE signature_hash = ? AND explored_at >= ?
            """,
            (sig, cutoff),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def add_signature(term: str, db_path: Optional[str] = None) -> None:
    """Records or refreshes an explored signature timestamp for a term."""
    sig = compute_signature(term)
    clean = normalize_term(term)
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO explored_signatures (signature_hash, normalized_term, explored_at)
                VALUES (?, ?, ?)
                ON CONFLICT(signature_hash) DO UPDATE SET
                    explored_at = excluded.explored_at
                """,
                (sig, clean, now_str),
            )
    finally:
        conn.close()


# -------------------------------------------------------------
# Frontier Queue State Machine
# -------------------------------------------------------------

def queue_sub_niche(
    term: str,
    category: str,
    parent: Optional[str] = None,
    depth: int = 0,
    db_path: Optional[str] = None,
) -> bool:
    """
    Inserts a newly discovered niche into the frontier queue.
    Enforces:
    - Depth cap <= 3
    - 90-day cooldown signature check
    - Unique term constraint
    """
    clean = normalize_term(term)
    if not clean or len(clean) < 3 or depth > 3:
        return False

    if is_signature_explored(clean, cooldown_days=90, db_path=db_path):
        return False

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO frontier_niches (
                    niche_term, category, parent_niche, depth_level, status
                ) VALUES (?, ?, ?, ?, 'pending')
                """,
                (clean, category.strip(), parent.strip() if parent else None, depth),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def claim_frontier_batch(
    shard_id: int,
    total_shards: int = 1,
    batch_size: int = 8,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Atomically claims a batch of pending niches for a given swarm shard using modular partitioning.
    Guarantees no two shards ever process the same term.
    """
    conn = get_connection(db_path)
    claimed: List[Dict[str, Any]] = []
    shard_tag = f"shard-{shard_id}"
    try:
        with conn:
            cursor = conn.cursor()
            # Select pending niches belonging to this shard
            if total_shards > 1:
                cursor.execute(
                    """
                    SELECT id, niche_term, category, depth_level, parent_niche
                    FROM frontier_niches
                    WHERE status = 'pending' AND (id % ?) = ?
                    ORDER BY depth_level ASC, created_at ASC
                    LIMIT ?
                    """,
                    (total_shards, shard_id % total_shards, batch_size),
                )
            else:
                cursor.execute(
                    """
                    SELECT id, niche_term, category, depth_level, parent_niche
                    FROM frontier_niches
                    WHERE status = 'pending'
                    ORDER BY depth_level ASC, created_at ASC
                    LIMIT ?
                    """,
                    (batch_size,),
                )
            rows = cursor.fetchall()
            if not rows:
                return []

            ids = [r["id"] for r in rows]
            # Atomically mark as claimed
            placeholders = ",".join("?" for _ in ids)
            cursor.execute(
                f"""
                UPDATE frontier_niches
                SET status = 'claimed', claimed_by_shard = ?
                WHERE id IN ({placeholders})
                """,
                [shard_tag] + ids,
            )
            claimed = [dict(r) for r in rows]
    finally:
        conn.close()
    return claimed


def mark_frontier_complete(
    niche_term: str,
    queries_extracted: int = 0,
    db_path: Optional[str] = None,
) -> None:
    """Marks a claimed niche as completed, records query yield, and logs explored signature."""
    clean = normalize_term(niche_term)
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                UPDATE frontier_niches
                SET status = 'completed',
                    queries_extracted = ?,
                    last_explored_at = ?
                WHERE niche_term = ? COLLATE NOCASE
                """,
                (queries_extracted, now_str, clean),
            )
    finally:
        conn.close()
    add_signature(clean, db_path=db_path)


def mark_frontier_failed(
    niche_term: str,
    error_msg: str = "",
    db_path: Optional[str] = None,
) -> None:
    """Marks a claimed niche as failed to allow later retry or inspection."""
    clean = normalize_term(niche_term)
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                UPDATE frontier_niches
                SET status = 'failed'
                WHERE niche_term = ? COLLATE NOCASE
                """,
                (clean,),
            )
    finally:
        conn.close()


def get_frontier_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Returns real-time telemetry metrics for the frontier discovery queue."""
    conn = get_connection(db_path)
    stats: Dict[str, Any] = {
        "total": 0,
        "pending": 0,
        "claimed": 0,
        "completed": 0,
        "failed": 0,
        "cooldown_active": 0,
        "by_category": {},
        "by_depth": {},
    }
    cutoff = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d %H:%M:%S")
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM frontier_niches")
            stats["total"] = cursor.fetchone()["c"]

            cursor.execute("SELECT status, COUNT(*) as c FROM frontier_niches GROUP BY status")
            for r in cursor.fetchall():
                st = r["status"]
                if st in stats:
                    stats[st] = r["c"]

            cursor.execute("SELECT COUNT(*) as c FROM explored_signatures WHERE explored_at >= ?", (cutoff,))
            stats["cooldown_active"] = cursor.fetchone()["c"]

            cursor.execute("SELECT category, COUNT(*) as c FROM frontier_niches GROUP BY category")
            for r in cursor.fetchall():
                stats["by_category"][r["category"]] = r["c"]

            cursor.execute("SELECT depth_level, COUNT(*) as c FROM frontier_niches GROUP BY depth_level")
            for r in cursor.fetchall():
                stats["by_depth"][str(r["depth_level"])] = r["c"]
    finally:
        conn.close()
    return stats


def get_frontier_page(
    category: Optional[str] = None,
    status: Optional[str] = None,
    depth_level: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated frontier niches with filtering."""
    conn = get_connection(db_path)
    conditions: List[str] = []
    params: List[Any] = []

    if category and category.lower() != "all":
        conditions.append("category = ?")
        params.append(category)

    if status and status.lower() != "all":
        conditions.append("status = ?")
        params.append(status)

    if depth_level is not None:
        conditions.append("depth_level = ?")
        params.append(depth_level)

    if search:
        conditions.append("niche_term LIKE ?")
        params.append(f"%{search}%")

    where_clause = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) as c FROM frontier_niches {where_clause}", params)
            total = cursor.fetchone()["c"]

            query = f"""
                SELECT * FROM frontier_niches
                {where_clause}
                ORDER BY depth_level ASC, created_at DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [limit, offset])
            rows = [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
    return rows, total


# -------------------------------------------------------------
# Queries & Opportunities Operations
# -------------------------------------------------------------

def upsert_query(data: Dict[str, Any], db_path: Optional[str] = None) -> int:
    """
    Inserts a newly evaluated query or updates it if it exists.
    Preserves human_verdict unless explicitly changed.
    """
    conn = get_connection(db_path)
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    evidence_json = (
        json.dumps(data.get("evidence", {}))
        if isinstance(data.get("evidence"), dict)
        else data.get("evidence_json", "{}")
    )

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO queries (
                    keyword, category, trend_type, trend_velocity, gap_score,
                    archetype, exact_title_matches, has_github_issues, has_stack_questions,
                    top_competitor_title, top_competitor_url, human_verdict, evidence_json,
                    first_seen, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(keyword) DO UPDATE SET
                    category = excluded.category,
                    trend_type = excluded.trend_type,
                    trend_velocity = excluded.trend_velocity,
                    gap_score = excluded.gap_score,
                    archetype = excluded.archetype,
                    exact_title_matches = excluded.exact_title_matches,
                    has_github_issues = excluded.has_github_issues,
                    has_stack_questions = excluded.has_stack_questions,
                    top_competitor_title = excluded.top_competitor_title,
                    top_competitor_url = excluded.top_competitor_url,
                    evidence_json = excluded.evidence_json,
                    last_updated = excluded.last_updated
                """,
                (
                    data["keyword"].strip(),
                    data.get("category", "General"),
                    data.get("trend_type", "TOP"),
                    data.get("trend_velocity", "Stable"),
                    int(data.get("gap_score", 0)),
                    data.get("archetype", "Recipe"),
                    int(data["exact_title_matches"]) if data.get("exact_title_matches") is not None else None,
                    1 if data.get("has_github_issues") else 0,
                    1 if data.get("has_stack_questions") else 0,
                    data.get("top_competitor_title", ""),
                    data.get("top_competitor_url", ""),
                    data.get("human_verdict", "pending"),
                    evidence_json,
                    now_str,
                    now_str,
                ),
            )
            row_id = cursor.lastrowid
        return row_id
    finally:
        conn.close()


def is_keyword_processed(keyword: str, max_age_days: int = 7, db_path: Optional[str] = None) -> bool:
    """Checks if a keyword was evaluated within max_age_days to avoid duplicate scrapers."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, last_updated FROM queries 
            WHERE keyword = ? COLLATE NOCASE
            """,
            (keyword.strip(),),
        )
        row = cursor.fetchone()
        if not row:
            return False
        last_updated = row["last_updated"]
        try:
            dt = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S")
            age = (datetime.utcnow() - dt).days
            return age < max_age_days
        except Exception:
            return True
    finally:
        conn.close()


def update_verdict(query_id: int, verdict: str, db_path: Optional[str] = None) -> bool:
    """Updates human verdict for an opportunity ('confirmed_gold', 'already_served', 'snoozed', 'pending')."""
    valid = {"confirmed_gold", "already_served", "snoozed", "pending"}
    if verdict not in valid:
        raise ValueError(f"Invalid verdict '{verdict}'. Must be one of {valid}")

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE queries 
                SET human_verdict = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (verdict, query_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


def bulk_update_verdict(query_ids: List[int], verdict: str, db_path: Optional[str] = None) -> int:
    """Bulk updates human verdict across a list of query IDs."""
    valid = {"confirmed_gold", "already_served", "snoozed", "pending"}
    if verdict not in valid:
        raise ValueError(f"Invalid verdict '{verdict}'. Must be one of {valid}")
    if not query_ids:
        return 0

    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" for _ in query_ids)
            cursor.execute(
                f"""
                UPDATE queries
                SET human_verdict = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                """,
                [verdict] + query_ids,
            )
            return cursor.rowcount
    finally:
        conn.close()


def get_queries(
    category: Optional[str] = None,
    archetype: Optional[str] = None,
    verdict: Optional[str] = None,
    min_score: int = 0,
    search: Optional[str] = None,
    root: Optional[str] = None,
    trend_type: Optional[str] = None,
    untouched_only: bool = False,
    competition_status: Optional[str] = None,
    sort_by: str = "best_to_build",
    sort_order: str = "DESC",
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated queries with filtering, cluster aggregation, and intelligent doability ranking."""
    conn = get_connection(db_path)
    conditions = ["q.gap_score >= ?"]
    params: List[Any] = [min_score]

    if category and category.lower() != "all":
        conditions.append("q.category = ?")
        params.append(category)

    if archetype and archetype.lower() != "all":
        conditions.append("q.archetype = ?")
        params.append(archetype)

    if verdict and verdict.lower() != "all":
        conditions.append("q.human_verdict = ?")
        params.append(verdict)

    if search:
        conditions.append("q.keyword LIKE ?")
        params.append(f"%{search}%")

    if root:
        conditions.append("(json_extract(q.evidence_json, '$.parent_niche') = ? OR q.keyword = ? OR q.keyword LIKE ? OR q.keyword LIKE ? OR q.keyword LIKE ?)")
        params.extend([root, root, f"{root} %", f"% {root}", f"% {root} %"])

    if trend_type and trend_type.lower() != "all":
        conditions.append("q.trend_type = ?")
        params.append(trend_type.upper())

    if untouched_only:
        conditions.append("q.exact_title_matches = 0")

    if competition_status and competition_status.lower() != "all":
        cs = competition_status.lower()
        if cs in ("void", "untouched", "voids"):
            conditions.append("q.exact_title_matches = 0")
        elif cs == "competed":
            conditions.append("q.exact_title_matches > 0")
        elif cs == "pending":
            conditions.append("q.exact_title_matches IS NULL")
        elif cs == "best_picks":
            conditions.append("(q.exact_title_matches <= 1 AND c.cluster_zeros >= 2 AND c.cluster_kws >= 8)")

    where_clause = " WHERE " + " AND ".join(conditions)

    allowed_sorts = {
        "best_to_build": "best_to_build",
        "doability": "best_to_build",
        "gap_score": "gap_score",
        "last_updated": "last_updated",
        "keyword": "keyword",
        "category": "category",
        "trend_type": "trend_type",
        "exact_title_matches": "exact_title_matches",
        "pending_first": "pending_first",
    }
    sort_col = allowed_sorts.get(sort_by, "best_to_build")
    order = "ASC" if sort_order.upper() == "ASC" else "DESC"

    if sort_col == "best_to_build":
        order_clause = "doability_rank DESC, q.gap_score DESC, q.id ASC"
    elif sort_col == "exact_title_matches":
        if order == "ASC":
            order_clause = "CASE WHEN q.exact_title_matches IS NULL THEN 2 WHEN q.exact_title_matches = 0 THEN 0 ELSE 1 END, q.exact_title_matches ASC, q.gap_score DESC"
        else:
            order_clause = "CASE WHEN q.exact_title_matches IS NULL THEN 2 ELSE 0 END, q.exact_title_matches DESC, q.gap_score DESC"
    elif sort_col == "pending_first":
        order_clause = "CASE WHEN q.exact_title_matches IS NULL THEN 0 ELSE 1 END, q.gap_score DESC"
    elif sort_col == "gap_score":
        order_clause = f"q.gap_score {order}, CASE WHEN q.exact_title_matches IS NULL THEN 2 ELSE 0 END, q.exact_title_matches ASC"
    else:
        order_clause = f"q.{sort_col} {order}"

    cte_sql = """
        WITH cluster_stats AS (
            SELECT 
                COALESCE(json_extract(evidence_json, '$.parent_niche'), category) as c_niche,
                COUNT(*) as cluster_kws,
                SUM(CASE WHEN exact_title_matches = 0 THEN 1 ELSE 0 END) as cluster_zeros
            FROM queries
            GROUP BY c_niche
        )
    """

    try:
        with conn:
            cursor = conn.cursor()
            count_query = f"""
                {cte_sql}
                SELECT COUNT(*) as count 
                FROM queries q
                LEFT JOIN cluster_stats c ON c.c_niche = COALESCE(json_extract(q.evidence_json, '$.parent_niche'), q.category)
                {where_clause}
            """
            cursor.execute(count_query, params)
            total = cursor.fetchone()["count"]

            query = f"""
                {cte_sql}
                SELECT 
                    q.*,
                    COALESCE(json_extract(q.evidence_json, '$.parent_niche'), q.category) as cluster_name,
                    COALESCE(c.cluster_kws, 1) as cluster_kws,
                    COALESCE(c.cluster_zeros, 0) as cluster_zeros,
                    (
                        (CASE WHEN q.exact_title_matches = 0 THEN 450
                              WHEN q.exact_title_matches = 1 THEN 250
                              WHEN q.exact_title_matches = 2 THEN 100
                              WHEN q.exact_title_matches IS NULL THEN 40
                              ELSE 0 END)
                        + (q.gap_score * 3)
                        + (COALESCE(c.cluster_zeros, 0) * 35)
                        + (COALESCE(c.cluster_kws, 1) * 6)
                        + (CASE WHEN q.trend_type = 'BREAKOUT' THEN 75 ELSE 0 END)
                        + (CASE WHEN q.archetype IN ('Micro-Tool', 'Cost Estimator', 'Config Generator', 'Workaround') THEN 40 ELSE 0 END)
                        + (CASE WHEN q.category IN ('Finance & Wealth', 'Legal & Compliance', 'Small Business & B2B', 'Clean Energy & Home') THEN 80
                                WHEN q.category IN ('Real Estate & Living', 'Health & Fitness', 'Travel & Visas') THEN 50
                                ELSE 15 END)
                        + (CASE WHEN q.top_competitor_url LIKE '%reddit%' OR q.top_competitor_url LIKE '%quora%' THEN 100 ELSE 0 END)
                    ) as doability_rank
                FROM queries q
                LEFT JOIN cluster_stats c ON c.c_niche = COALESCE(json_extract(q.evidence_json, '$.parent_niche'), q.category)
                {where_clause} 
                ORDER BY {order_clause} 
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [limit, offset])
            rows = [dict(row) for row in cursor.fetchall()]
        return rows, total
    finally:
        conn.close()


def get_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Generates real-time aggregation metrics for the dashboard."""
    conn = get_connection(db_path)
    stats: Dict[str, Any] = {
        "total_queries": 0,
        "critical_gold": 0,
        "high_opportunity": 0,
        "confirmed_gold": 0,
        "snoozed": 0,
        "breakouts": 0,
        "frontier_total": 0,
        "frontier_pending": 0,
        "by_archetype": {},
        "by_category": {},
    }

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as c FROM queries")
            stats["total_queries"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE gap_score >= 85")
            stats["critical_gold"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE gap_score >= 65 AND gap_score < 85")
            stats["high_opportunity"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE human_verdict = 'confirmed_gold'")
            stats["confirmed_gold"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE human_verdict = 'snoozed'")
            stats["snoozed"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE trend_type = 'BREAKOUT'")
            stats["breakouts"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE exact_title_matches = 0")
            stats["verified_voids"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE exact_title_matches > 0")
            stats["competed_queries"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM queries WHERE exact_title_matches IS NULL")
            stats["pending_audits"] = cursor.fetchone()["c"]

            # Calculate intelligent top website picks (high demand cluster + 0/10 or 1/10 SERP competition)
            cursor.execute("""
                WITH cluster_stats AS (
                    SELECT 
                        COALESCE(json_extract(evidence_json, '$.parent_niche'), category) as c_niche,
                        COUNT(*) as cluster_kws,
                        SUM(CASE WHEN exact_title_matches = 0 THEN 1 ELSE 0 END) as cluster_zeros
                    FROM queries
                    GROUP BY c_niche
                )
                SELECT COUNT(*) as c
                FROM queries q
                JOIN cluster_stats c ON c.c_niche = COALESCE(json_extract(q.evidence_json, '$.parent_niche'), q.category)
                WHERE (q.exact_title_matches <= 1)
                  AND (c.cluster_zeros >= 2)
                  AND (c.cluster_kws >= 8)
            """)
            stats["best_picks"] = cursor.fetchone()["c"]

            cursor.execute("SELECT archetype, COUNT(*) as c FROM queries GROUP BY archetype")
            for r in cursor.fetchall():
                stats["by_archetype"][r["archetype"]] = r["c"]

            cursor.execute("SELECT category, COUNT(*) as c FROM queries GROUP BY category")
            for r in cursor.fetchall():
                stats["by_category"][r["category"]] = r["c"]

            # Frontier stats
            cursor.execute("SELECT COUNT(*) as c FROM frontier_niches")
            stats["frontier_total"] = cursor.fetchone()["c"]

            cursor.execute("SELECT COUNT(*) as c FROM frontier_niches WHERE status = 'pending'")
            stats["frontier_pending"] = cursor.fetchone()["c"]
        return stats
    finally:
        conn.close()


def log_scan_event(
    batch_name: str,
    category: str,
    queries_found: int,
    gold_found: int,
    log_message: str,
    db_path: Optional[str] = None,
) -> None:
    conn = get_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO scan_logs (batch_name, category, queries_found, gold_found, log_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (batch_name, category, queries_found, gold_found, log_message),
            )
    finally:
        conn.close()


def get_recent_logs(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM scan_logs ORDER BY timestamp DESC LIMIT ?
                """,
                (limit,),
            )
            logs = [dict(r) for r in cursor.fetchall()]
        return logs
    finally:
        conn.close()


# Auto-initialize DB on import
init_db()
