"""Load the list of sites to monitor from a YAML config file."""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import List

import yaml

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_EXPECTED_STATUS = 200


@dataclasses.dataclass
class SiteConfig:
    name: str
    url: str
    expected_status: int = DEFAULT_EXPECTED_STATUS
    timeout: float = DEFAULT_TIMEOUT_SECONDS


@dataclasses.dataclass
class MonitorConfig:
    sites: List[SiteConfig]
    webhook_url: str = ""  # e.g. a Slack incoming webhook; empty = log-only alerts
    db_path: str = "uptime_sentinel.db"


def load_config(path: Path) -> MonitorConfig:
    """Parse a YAML config file into a :class:`MonitorConfig`.

    Expected shape::

        db_path: uptime_sentinel.db
        webhook_url: ""   # optional
        sites:
          - name: My Site
            url: https://example.com
            expected_status: 200   # optional, defaults to 200
            timeout: 10            # optional, seconds
    """
    raw = yaml.safe_load(Path(path).read_text()) or {}
    sites_raw = raw.get("sites") or []
    if not sites_raw:
        raise ValueError(f"{path} defines no sites to monitor")

    sites: List[SiteConfig] = []
    for entry in sites_raw:
        if "name" not in entry or "url" not in entry:
            raise ValueError(f"each site needs a 'name' and a 'url': {entry!r}")
        sites.append(
            SiteConfig(
                name=entry["name"],
                url=entry["url"],
                expected_status=int(entry.get("expected_status", DEFAULT_EXPECTED_STATUS)),
                timeout=float(entry.get("timeout", DEFAULT_TIMEOUT_SECONDS)),
            )
        )

    return MonitorConfig(
        sites=sites,
        webhook_url=raw.get("webhook_url", "") or "",
        db_path=raw.get("db_path", "uptime_sentinel.db"),
    )
