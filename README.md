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

Example `sentinel check` output:

```
[OK  ] My Website              142ms  https://example.com
[FAIL] My API health check      n/a   https://api.example.com/health
         -> HTTPSConnectionPool(host='api.example.com', port=443): Read timed out.

1/2 sites healthy. 1 alert(s) sent.
```

Example report (`sentinel report`):

```
# Uptime Report

_Generated 2026-09-11T02:00:00+00:00_

| Site | Uptime | Avg Latency | Incidents | Checks | Last Status |
|---|---|---|---|---|---|
| My Website | 100.0% | 138.2 ms | 0 | 288 | up |
| My API health check | 97.2% | 210.5 ms | 3 | 288 | up |
```

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
```

## Testing

```bash
pip install -r requirements-dev.txt
pytest -v
```

The suite mocks HTTP for pure unit tests (`test_checker.py`, `test_alerts.py`) so it never depends on the real network, and additionally spins up a real local HTTP server (`test_cli.py`) to exercise the actual `sentinel` entry point end-to-end — config parsing, checking, SQLite recording, and report generation — via subprocess, including a genuine unreachable-host failure case.

## License

MIT — see [LICENSE](LICENSE).
