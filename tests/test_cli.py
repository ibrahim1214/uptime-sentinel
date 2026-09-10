import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class _OkHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # silence test output
        pass


class _FailHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(503)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def local_server():
    """Spin up a tiny local HTTP server so CLI tests don't depend on the network."""
    server = http.server.HTTPServer(("127.0.0.1", 0), _OkHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join(timeout=5)


def _run_cli(args, cwd=None):
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


def test_cli_check_against_a_healthy_local_server(tmp_path: Path, local_server: str):
    config_file = tmp_path / "sites.yaml"
    config_file.write_text(
        "db_path: test.db\n"
        "sites:\n"
        f"  - name: Local\n    url: {local_server}\n"
    )
    result = _run_cli(["check", "--config", str(config_file)], cwd=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[OK  ]" in result.stdout
    assert (tmp_path / "test.db").exists()


def test_cli_check_against_unreachable_site_exits_nonzero(tmp_path: Path):
    config_file = tmp_path / "sites.yaml"
    config_file.write_text(
        "db_path: test.db\n"
        "sites:\n"
        "  - name: Dead\n    url: http://127.0.0.1:1\n    timeout: 2\n"
    )
    result = _run_cli(["check", "--config", str(config_file)], cwd=tmp_path)
    assert result.returncode == 1
    assert "[FAIL]" in result.stdout


def test_cli_monitor_runs_fixed_number_of_passes(tmp_path: Path, local_server: str):
    config_file = tmp_path / "sites.yaml"
    config_file.write_text(
        "db_path: test.db\n"
        "sites:\n"
        f"  - name: Local\n    url: {local_server}\n"
    )
    result = _run_cli(
        ["monitor", "--config", str(config_file), "--interval", "0", "--count", "3"],
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.count("[OK  ]") == 3


def test_cli_report_after_checks(tmp_path: Path, local_server: str):
    config_file = tmp_path / "sites.yaml"
    config_file.write_text(
        "db_path: test.db\n"
        "sites:\n"
        f"  - name: Local\n    url: {local_server}\n"
    )
    _run_cli(["check", "--config", str(config_file)], cwd=tmp_path)
    result = _run_cli(["report", "--config", str(config_file)], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Local" in result.stdout
    assert "Uptime Report" in result.stdout


def test_cli_report_writes_to_file(tmp_path: Path, local_server: str):
    config_file = tmp_path / "sites.yaml"
    config_file.write_text(
        "db_path: test.db\n"
        "sites:\n"
        f"  - name: Local\n    url: {local_server}\n"
    )
    _run_cli(["check", "--config", str(config_file)], cwd=tmp_path)
    out_file = tmp_path / "report.md"
    result = _run_cli(
        ["report", "--config", str(config_file), "-o", str(out_file)], cwd=tmp_path
    )
    assert result.returncode == 0
    assert out_file.exists()
    assert "Local" in out_file.read_text()
