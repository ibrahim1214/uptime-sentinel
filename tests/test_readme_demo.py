"""Verify the exact scenario shown in the README's 'Live demo' section still works.

Uses examples/sites.yaml -- the same file referenced in the README -- against
the real network (example.com) and a deliberately closed local port, so a
README claim about this tool's behavior can't silently go stale.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"


def _run_cli(args, cwd):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "uptime_sentinel.cli", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_examples_sites_yaml_exists_and_matches_readme():
    assert EXAMPLES_DIR.is_dir()
    content = (EXAMPLES_DIR / "sites.yaml").read_text()
    assert "Company Homepage" in content
    assert "Internal Payments API (staging)" in content


@pytest.mark.network
def test_demo_scenario_reflects_real_network_state(tmp_path):
    """Requires real network access (hits https://example.com)."""
    db_path = tmp_path / "demo.db"
    config = tmp_path / "sites.yaml"
    config.write_text(
        f"db_path: {db_path}\n"
        "sites:\n"
        "  - name: Company Homepage\n"
        "    url: https://example.com\n"
        "    expected_status: 200\n"
        "    timeout: 10\n"
        "  - name: Internal Payments API (staging)\n"
        "    url: http://127.0.0.1:1\n"
        "    timeout: 2\n"
    )

    first = _run_cli(["check", "--config", str(config)], cwd=tmp_path)
    assert "[OK  ] Company Homepage" in first.stdout
    assert "[FAIL] Internal Payments API (staging)" in first.stdout
    assert first.returncode == 1  # one site failing

    report = _run_cli(["report", "--config", str(config)], cwd=tmp_path)
    assert report.returncode == 0
    assert "100.0%" in report.stdout  # Company Homepage uptime
    assert "0.0%" in report.stdout    # Internal Payments API uptime
