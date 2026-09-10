from pathlib import Path

from uptime_sentinel import db
from uptime_sentinel.checker import CheckResult
from uptime_sentinel.report import generate_report


def _result(name, ok, checked_at):
    return CheckResult(
        name=name, url="https://example.com", ok=ok,
        status_code=200 if ok else 500, latency_ms=100.0 if ok else None,
        error="" if ok else "boom", checked_at=checked_at,
    )


def test_generate_report_empty_db(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    report = generate_report(conn)
    assert "No checks recorded yet" in report


def test_generate_report_includes_all_sites_and_stats(tmp_path: Path):
    conn = db.connect(tmp_path / "test.db")
    db.record_check(conn, _result("Site A", True, "2026-01-01T00:00:00"))
    db.record_check(conn, _result("Site A", False, "2026-01-01T00:01:00"))
    db.record_check(conn, _result("Site B", True, "2026-01-01T00:00:00"))

    report = generate_report(conn)
    assert "Site A" in report
    assert "Site B" in report
    assert "Uptime Report" in report
    assert "DOWN" in report  # Site A's last status
    assert "up" in report  # Site B's last status
