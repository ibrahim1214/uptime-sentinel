"""SQLite storage for check history."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Optional

from .checker import CheckResult

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    ok INTEGER NOT NULL,
    status_code INTEGER,
    latency_ms REAL,
    error TEXT,
    checked_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checks_name_time ON checks(name, checked_at);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def record_check(conn: sqlite3.Connection, result: CheckResult) -> None:
    conn.execute(
        "INSERT INTO checks (name, url, ok, status_code, latency_ms, error, checked_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            result.name,
            result.url,
            1 if result.ok else 0,
            result.status_code,
            result.latency_ms,
            result.error,
            result.checked_at,
        ),
    )
    conn.commit()


def record_checks(conn: sqlite3.Connection, results: List[CheckResult]) -> None:
    for result in results:
        record_check(conn, result)


def get_history(conn: sqlite3.Connection, name: str, limit: int = 100) -> List[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM checks WHERE name = ? ORDER BY checked_at DESC LIMIT ?",
        (name, limit),
    )
    return cur.fetchall()


def get_last_result(conn: sqlite3.Connection, name: str) -> Optional[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM checks WHERE name = ? ORDER BY checked_at DESC, id DESC LIMIT 1",
        (name,),
    )
    return cur.fetchone()


def distinct_site_names(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("SELECT DISTINCT name FROM checks ORDER BY name")
    return [row[0] for row in cur.fetchall()]


def uptime_stats(conn: sqlite3.Connection, name: str) -> dict:
    """Compute uptime percentage, average latency, and incident count for a site."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT ok, latency_ms FROM checks WHERE name = ?", (name,)
    ).fetchall()
    total = len(rows)
    if total == 0:
        return {
            "name": name,
            "total_checks": 0,
            "uptime_pct": None,
            "avg_latency_ms": None,
            "incidents": 0,
        }

    up = sum(1 for r in rows if r["ok"])
    latencies = [r["latency_ms"] for r in rows if r["latency_ms"] is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    # An "incident" is a transition from up to down, counted in chronological order.
    ordered = conn.execute(
        "SELECT ok FROM checks WHERE name = ? ORDER BY checked_at ASC, id ASC", (name,)
    ).fetchall()
    incidents = 0
    previous_ok = True
    for row in ordered:
        current_ok = bool(row["ok"])
        if previous_ok and not current_ok:
            incidents += 1
        previous_ok = current_ok

    return {
        "name": name,
        "total_checks": total,
        "uptime_pct": round(100.0 * up / total, 2),
        "avg_latency_ms": round(avg_latency, 1) if avg_latency is not None else None,
        "incidents": incidents,
    }
