"""Perform a single HTTP check against a site."""
from __future__ import annotations

import dataclasses
import time
from datetime import datetime, timezone

import requests

from .config import SiteConfig


@dataclasses.dataclass
class CheckResult:
    name: str
    url: str
    ok: bool
    status_code: int | None
    latency_ms: float | None
    error: str
    checked_at: str  # ISO-8601 UTC timestamp


def check_site(site: SiteConfig, session: requests.Session | None = None) -> CheckResult:
    """Run one HTTP GET against ``site`` and report success/failure + latency.

    A check is considered "ok" only if the request completes without a
    network-level error AND the response status code matches
    ``site.expected_status``.
    """
    http = session or requests
    checked_at = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    try:
        response = http.get(site.url, timeout=site.timeout)
    except requests.RequestException as exc:
        return CheckResult(
            name=site.name,
            url=site.url,
            ok=False,
            status_code=None,
            latency_ms=None,
            error=str(exc),
            checked_at=checked_at,
        )

    latency_ms = (time.monotonic() - start) * 1000
    ok = response.status_code == site.expected_status
    error = "" if ok else f"expected status {site.expected_status}, got {response.status_code}"
    return CheckResult(
        name=site.name,
        url=site.url,
        ok=ok,
        status_code=response.status_code,
        latency_ms=latency_ms,
        error=error,
        checked_at=checked_at,
    )


def check_all(sites, session: requests.Session | None = None) -> list[CheckResult]:
    """Check every site in ``sites`` sequentially, returning one result each."""
    return [check_site(site, session=session) for site in sites]
