"""Command-line interface: ``sentinel check|monitor|report``."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from . import db
from .alerts import process_result
from .checker import check_all
from .config import load_config
from .report import generate_report


def _run_one_pass(config_path: Path) -> int:
    config = load_config(config_path)
    conn = db.connect(config.db_path)

    # Snapshot each site's previous state *before* recording new results,
    # so alerting can detect up<->down transitions.
    previous_state = {}
    for site in config.sites:
        last = db.get_last_result(conn, site.name)
        previous_state[site.name] = bool(last["ok"]) if last is not None else None

    results = check_all(config.sites)
    alerts_sent = 0
    for result in results:
        db.record_check(conn, result)
        if process_result(result, previous_state[result.name], webhook_url=config.webhook_url):
            alerts_sent += 1

    failures = [r for r in results if not r.ok]
    for r in results:
        status = "OK  " if r.ok else "FAIL"
        latency = f"{r.latency_ms:.0f}ms" if r.latency_ms is not None else "n/a"
        print(f"[{status}] {r.name:<20} {latency:>8}  {r.url}")
        if not r.ok and r.error:
            print(f"         -> {r.error}")

    print(f"\n{len(results) - len(failures)}/{len(results)} sites healthy. "
          f"{alerts_sent} alert(s) sent.")
    conn.close()
    return 1 if failures else 0


def _cmd_check(args: argparse.Namespace) -> int:
    return _run_one_pass(Path(args.config))


def _cmd_monitor(args: argparse.Namespace) -> int:
    """Repeatedly run checks every ``--interval`` seconds.

    ``--count`` bounds how many passes to run (default: run forever, i.e.
    until interrupted) -- mainly useful for scripted/testable runs.
    """
    passes = 0
    try:
        while args.count is None or passes < args.count:
            _run_one_pass(Path(args.config))
            passes += 1
            if args.count is not None and passes >= args.count:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    conn = db.connect(config.db_path)
    report = generate_report(conn)
    conn.close()

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report written to {args.output}")
    else:
        print(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel",
        description="A free, self-hosted website uptime and latency monitor.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Run a single check pass over all configured sites")
    p_check.add_argument("--config", default="sites.yaml", help="Path to sites config (YAML)")
    p_check.set_defaults(func=_cmd_check)

    p_monitor = sub.add_parser("monitor", help="Run checks repeatedly on an interval")
    p_monitor.add_argument("--config", default="sites.yaml", help="Path to sites config (YAML)")
    p_monitor.add_argument("--interval", type=float, default=60,
                            help="Seconds between check passes (default: 60)")
    p_monitor.add_argument("--count", type=int, default=None,
                            help="Number of passes to run (default: run forever)")
    p_monitor.set_defaults(func=_cmd_monitor)

    p_report = sub.add_parser("report", help="Print/save a Markdown uptime report")
    p_report.add_argument("--config", default="sites.yaml", help="Path to sites config (YAML)")
    p_report.add_argument("-o", "--output", help="Write the report to this file instead of stdout")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
