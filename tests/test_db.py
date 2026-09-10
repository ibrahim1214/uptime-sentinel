from pathlib import Path

from uptime_sentinel import db
from uptime_sentinel.checker import CheckResult


def _result(name="A", ok=True, latency_ms=100.0, checked_at="2026-01-01T00:00:00+00:00", error=""):
    return CheckResult(
        name=name,
        url="https://example.com",
        ok=ok,
        status_code=200 if ok else 500,
        latency_ms=latency_ms,
        error=error,
        checked_at=checked_at,
    )


def test_connect_creates_schema(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checks'")
    assert cur.fetchone() is not None


def test_record_and_get_history(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    db.record_check(conn, _result(checked_at="2026-01-01T00:00:00+00:00"))
    db.record_check(conn, _result(checked_at="2026-01-01T00:01:00+00:00"))
    history = db.get_history(conn, "A")
    assert len(history) == 2
    # Most recent first.
    assert history[0]["checked_at"] == "2026-01-01T00:01:00+00:00"


def test_get_last_result_returns_none_when_empty(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    assert db.get_last_result(conn, "Nonexistent") is None


def test_uptime_stats_computes_percentage_and_latency(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    db.record_check(conn, _result(ok=True, latency_ms=100, checked_at="2026-01-01T00:00:00"))
    db.record_check(conn, _result(ok=True, latency_ms=200, checked_at="2026-01-01T00:01:00"))
    db.record_check(conn, _result(ok=False, latency_ms=None, checked_at="2026-01-01T00:02:00"))
    db.record_check(conn, _result(ok=True, latency_ms=150, checked_at="2026-01-01T00:03:00"))

    stats = db.uptime_stats(conn, "A")
    assert stats["total_checks"] == 4
    assert stats["uptime_pct"] == 75.0
    assert stats["avg_latency_ms"] == 150.0  # avg of 100, 200, 150 (None excluded)


def test_uptime_stats_counts_incidents_as_up_to_down_transitions(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    # up, down, down, up, down  -> 2 incidents (up->down happens twice)
    sequence = [True, False, False, True, False]
    for i, ok in enumerate(sequence):
        db.record_check(conn, _result(ok=ok, checked_at=f"2026-01-01T00:0{i}:00"))

    stats = db.uptime_stats(conn, "A")
    assert stats["incidents"] == 2


def test_uptime_stats_empty_site_returns_none_values(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    stats = db.uptime_stats(conn, "Never Checked")
    assert stats["total_checks"] == 0
    assert stats["uptime_pct"] is None
    assert stats["incidents"] == 0


def test_distinct_site_names(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    db.record_check(conn, _result(name="B", checked_at="2026-01-01T00:00:00"))
    db.record_check(conn, _result(name="A", checked_at="2026-01-01T00:00:00"))
    db.record_check(conn, _result(name="A", checked_at="2026-01-01T00:01:00"))
    assert db.distinct_site_names(conn) == ["A", "B"]
