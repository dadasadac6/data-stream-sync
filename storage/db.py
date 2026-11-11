"""
Database Layer for Autonomous Developer Search Gap Radar (Gold Miner)
SQLite storage with WAL mode, indexing, deduplication, and filtering.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "niche_gaps.db")


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
                archetype TEXT NOT NULL,           -- 'Micro-Tool', 'Workaround', 'Recipe', 'Breaking News'
                exact_title_matches INTEGER DEFAULT 0,
                has_github_issues BOOLEAN DEFAULT 0,
                has_stack_questions BOOLEAN DEFAULT 0,
                top_competitor_title TEXT,
                top_competitor_url TEXT,
                human_verdict TEXT DEFAULT 'pending', -- 'confirmed_gold', 'already_served', 'pending'
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
            """
        )
    conn.close()


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
                int(data.get("exact_title_matches", 0)),
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
    conn.close()
    return row_id


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
        # If exists, check age
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
    """Updates the human verdict for an opportunity ('confirmed_gold', 'already_served', 'pending')."""
    valid = {"confirmed_gold", "already_served", "pending"}
    if verdict not in valid:
        raise ValueError(f"Invalid verdict '{verdict}'. Must be one of {valid}")

    conn = get_connection(db_path)
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
        updated = cursor.rowcount > 0
    conn.close()
    return updated


def get_queries(
    category: Optional[str] = None,
    archetype: Optional[str] = None,
    verdict: Optional[str] = None,
    min_score: int = 0,
    search: Optional[str] = None,
    sort_by: str = "gap_score",
    sort_order: str = "DESC",
    limit: int = 50,
    offset: int = 0,
    db_path: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves paginated queries with filtering and total count."""
    conn = get_connection(db_path)
    conditions = ["gap_score >= ?"]
    params: List[Any] = [min_score]

    if category and category.lower() != "all":
        conditions.append("category = ?")
        params.append(category)

    if archetype and archetype.lower() != "all":
        conditions.append("archetype = ?")
        params.append(archetype)

    if verdict and verdict.lower() != "all":
        conditions.append("human_verdict = ?")
        params.append(verdict)

    if search:
        conditions.append("keyword LIKE ?")
        params.append(f"%{search}%")

    where_clause = " WHERE " + " AND ".join(conditions)

    # Valid sort columns
    allowed_sorts = {
        "gap_score": "gap_score",
        "last_updated": "last_updated",
        "keyword": "keyword",
        "category": "category",
        "trend_type": "trend_type",
    }
    sort_col = allowed_sorts.get(sort_by, "gap_score")
    order = "ASC" if sort_order.upper() == "ASC" else "DESC"

    with conn:
        cursor = conn.cursor()
        # Count total
        cursor.execute(f"SELECT COUNT(*) as count FROM queries {where_clause}", params)
        total = cursor.fetchone()["count"]

        # Fetch page
        query = f"""
            SELECT * FROM queries 
            {where_clause} 
            ORDER BY {sort_col} {order} 
            LIMIT ? OFFSET ?
        """
        cursor.execute(query, params + [limit, offset])
        rows = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return rows, total


def get_stats(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Generates real-time aggregation metrics for the dashboard."""
    conn = get_connection(db_path)
    stats: Dict[str, Any] = {
        "total_queries": 0,
        "critical_gold": 0,
        "high_opportunity": 0,
        "confirmed_gold": 0,
        "breakouts": 0,
        "by_archetype": {},
        "by_category": {},
    }

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

        cursor.execute("SELECT COUNT(*) as c FROM queries WHERE trend_type = 'BREAKOUT'")
        stats["breakouts"] = cursor.fetchone()["c"]

        cursor.execute("SELECT archetype, COUNT(*) as c FROM queries GROUP BY archetype")
        for r in cursor.fetchall():
            stats["by_archetype"][r["archetype"]] = r["c"]

        cursor.execute("SELECT category, COUNT(*) as c FROM queries GROUP BY category")
        for r in cursor.fetchall():
            stats["by_category"][r["category"]] = r["c"]

    conn.close()
    return stats


def log_scan_event(
    batch_name: str,
    category: str,
    queries_found: int,
    gold_found: int,
    log_message: str,
    db_path: Optional[str] = None,
) -> None:
    conn = get_connection(db_path)
    with conn:
        conn.execute(
            """
            INSERT INTO scan_logs (batch_name, category, queries_found, gold_found, log_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (batch_name, category, queries_found, gold_found, log_message),
        )
    conn.close()


def get_recent_logs(limit: int = 50, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection(db_path)
    with conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM scan_logs ORDER BY timestamp DESC LIMIT ?
            """,
            (limit,),
        )
        logs = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return logs


# Auto-initialize DB on import
init_db()
