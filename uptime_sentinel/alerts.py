"""Decide when a check result is alert-worthy, and dispatch the alert.

To avoid spamming on every failed check while a site is down, an alert only
fires on a *state transition*: healthy -> down, or down -> healthy. That
transition is determined by comparing the new result against the
previously stored result for the same site.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

from .checker import CheckResult

logger = logging.getLogger("uptime_sentinel")


def is_transition(current: CheckResult, previous_ok: Optional[bool]) -> bool:
    """Return True if ``current`` represents a change in site health.

    ``previous_ok`` is ``None`` when there is no prior recorded check (in
    which case the very first check is never itself an "alert", it just
    establishes a baseline).
    """
    if previous_ok is None:
        return False
    return current.ok != previous_ok


def format_message(result: CheckResult) -> str:
    if result.ok:
        return f":white_check_mark: *{result.name}* is back up ({result.url})"
    detail = result.error or f"status {result.status_code}"
    return f":rotating_light: *{result.name}* is DOWN ({result.url}) -- {detail}"


def send_alert(result: CheckResult, webhook_url: str = "") -> bool:
    """Send an alert for ``result``.

    If ``webhook_url`` is set, POSTs a Slack-compatible ``{"text": ...}``
    payload to it. Otherwise (the free default) logs the alert so it still
    shows up wherever this tool's logs/output are captured (console, a
    systemd journal, cron mail, etc).

    Returns True if the alert was (successfully) dispatched.
    """
    message = format_message(result)
    if not webhook_url:
        logger.warning(message)
        return True

    try:
        response = requests.post(webhook_url, json={"text": message}, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.error("failed to deliver alert via webhook: %s", exc)
        return False


def process_result(result: CheckResult, previous_ok: Optional[bool], webhook_url: str = "") -> bool:
    """Send an alert for ``result`` only if it represents a state transition.

    Returns True if an alert was sent, False otherwise.
    """
    if not is_transition(result, previous_ok):
        return False
    return send_alert(result, webhook_url=webhook_url)
