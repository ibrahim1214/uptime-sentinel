# uptime-sentinel

A free, self-hosted website uptime and latency monitor — no paid service, no account, just a config file, SQLite, and a cron job (or `cron`-style `systemd` timer).

## Why

Third-party uptime monitors are great until you hit their free-tier site limit or check-frequency cap. `uptime-sentinel` does the same core job — periodically hit a list of URLs, remember the history, alert on state changes, report uptime % — as a small, auditable Python tool you run yourself.

## How it works

```
sites.yaml ──▶ checker.py ──▶ db.py (SQLite) ──▶ report.py (Markdown)
                    │
                    ▼
              alerts.py ──▶ webhook (optional) or console log
```

1. **Configure** — list the sites you care about in `sites.yaml` (name, URL, expected status code, timeout).
2. **Check** — `sentinel check` hits every site once, records the result (status code, latency, error) to a local SQLite database, and prints a pass/fail summary. Exit code is non-zero if anything failed, so it's cron/CI-friendly.
3. **Alert** — an alert only fires on a *state transition* (healthy → down, or down → healthy), not on every failed check while something is down, so you don't get paged every minute for the same outage. With no `webhook_url` configured, alerts are just logged to the console/journal — genuinely free by default. Set `webhook_url` to a Slack (or any Slack-compatible) incoming webhook to get pushed notifications instead.
4. **Report** — `sentinel report` reads the accumulated history and prints (or saves) a Markdown table: uptime %, average latency, incident count, and last known status per site.
5. **Monitor** — `sentinel monitor --interval 60` loops the check pass forever (or `--count N` times), for when you'd rather run this as a long-lived process than via cron.

## Install

```bash
git clone https://github.com/ibrahim1214/uptime-sentinel.git
cd uptime-sentinel
pip install -r requirements.txt
pip install -e .          # installs the `sentinel` command
cp sites.example.yaml sites.yaml
# edit sites.yaml with your own sites
```

No API key or paid service required. `webhook_url` in `sites.yaml` is optional.

## Usage

```bash
# One-off check of everything in sites.yaml
sentinel check

# Loop forever, checking every 5 minutes
sentinel monitor --interval 300

# Loop exactly 10 times (useful for scripted/testable runs)
sentinel monitor --interval 60 --count 10

# Generate a report
sentinel report
sentinel report -o report.md
```

## Live demo

Real output, not a mockup — this is `examples/sites.yaml` in this repo (one genuinely reachable site, one deliberately pointed at a closed local port so the failure case is real too), run twice with `sentinel check` and then `sentinel report`:

```bash
cd examples
sentinel check --config sites.yaml
```
```
[OK  ] Company Homepage        415ms  https://example.com
[FAIL] Internal Payments API (staging)      n/a  http://127.0.0.1:1
         -> HTTPConnectionPool(host='127.0.0.1', port=1): Max retries exceeded with url: /
         (Caused by NewConnectionError('...: Failed to establish a new connection: [Errno 111] Connection refused'))

1/2 sites healthy. 0 alert(s) sent.
```

```bash
sentinel check --config sites.yaml   # run again a moment later
sentinel report --config sites.yaml
```
```
# Uptime Report

_Generated 2026-09-10T19:29:41+00:00_

| Site | Uptime | Avg Latency | Incidents | Checks | Last Status |
|---|---|---|---|---|---|
| Company Homepage | 100.0% | 435.3 ms | 0 | 2 | up |
| Internal Payments API (staging) | 0.0% | n/a | 1 | 2 | DOWN (Connection refused) |
```

`0 alert(s) sent` on both runs is correct, not a bug: the very first check of a site only establishes a baseline (nothing to transition *from* yet), and the second check found no state change either. Point `sentinel monitor` at these same sites and take one of them offline mid-run and you'll see exactly one alert fire, the moment it flips — not one per failed check.

### Running it on a schedule

Cron, every 5 minutes:

```
*/5 * * * * cd /path/to/uptime-sentinel && /usr/bin/python3 -m uptime_sentinel.cli check >> sentinel.log 2>&1
```

## Project layout

```
uptime_sentinel/
├── config.py    # parses sites.yaml into SiteConfig / MonitorConfig
├── checker.py   # performs one HTTP check, returns a CheckResult
├── db.py        # SQLite schema, inserts, and uptime/latency/incident stats
├── alerts.py    # transition-only alerting, console or webhook delivery
├── report.py    # renders a Markdown uptime report from history
└── cli.py       # `sentinel check|monitor|report`
examples/sites.yaml   # the exact config used in the Live demo above
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest -v
```

The suite mocks HTTP for pure unit tests (`test_checker.py`, `test_alerts.py`) so it never depends on the real network, and additionally spins up a real local HTTP server (`test_cli.py`) to exercise the actual `sentinel` entry point end-to-end — config parsing, checking, SQLite recording, and report generation — via subprocess, including a genuine unreachable-host failure case.

## License

MIT — see [LICENSE](LICENSE).
