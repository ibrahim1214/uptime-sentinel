"""Generate a human-readable Markdown report from check history."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import db


def generate_report(conn: sqlite3.Connection) -> str:
    names = db.distinct_site_names(conn)
    if not names:
        return "# Uptime Report\n\nNo checks recorded yet.\n"

    lines = [
        "# Uptime Report",
        "",
        f"_Generated {datetime.now(timezone.utc).isoformat()}_",
        "",
        "| Site | Uptime | Avg Latency | Incidents | Checks | Last Status |",
        "|---|---|---|---|---|---|",
    ]

    for name in names:
        stats = db.uptime_stats(conn, name)
        last = db.get_last_result(conn, name)
        last_status = "unknown"
        if last is not None:
            last_status = "up" if last["ok"] else f"DOWN ({last['error']})"
        uptime_display = f"{stats['uptime_pct']}%" if stats["uptime_pct"] is not None else "n/a"
        latency_display = (
            f"{stats['avg_latency_ms']} ms" if stats["avg_latency_ms"] is not None else "n/a"
        )
        lines.append(
            f"| {name} | {uptime_display} | {latency_display} | "
            f"{stats['incidents']} | {stats['total_checks']} | {last_status} |"
        )

    return "\n".join(lines) + "\n"
