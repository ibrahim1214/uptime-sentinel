from unittest.mock import MagicMock, patch

from uptime_sentinel.alerts import format_message, is_transition, process_result, send_alert
from uptime_sentinel.checker import CheckResult


def _ok_result(ok=True, error=""):
    return CheckResult(
        name="A", url="https://a.example.com", ok=ok,
        status_code=200 if ok else 500, latency_ms=50.0, error=error,
        checked_at="2026-01-01T00:00:00+00:00",
    )


def test_is_transition_true_when_state_flips():
    assert is_transition(_ok_result(ok=False), previous_ok=True) is True
    assert is_transition(_ok_result(ok=True), previous_ok=False) is True


def test_is_transition_false_when_state_unchanged():
    assert is_transition(_ok_result(ok=True), previous_ok=True) is False
    assert is_transition(_ok_result(ok=False), previous_ok=False) is False


def test_is_transition_false_on_first_ever_check():
    assert is_transition(_ok_result(ok=False), previous_ok=None) is False


def test_format_message_down_includes_error():
    result = _ok_result(ok=False, error="connection refused")
    message = format_message(result)
    assert "DOWN" in message
    assert "connection refused" in message


def test_format_message_up_is_positive():
    message = format_message(_ok_result(ok=True))
    assert "back up" in message


def test_send_alert_without_webhook_logs_instead_of_raising(caplog):
    result = _ok_result(ok=False, error="timeout")
    sent = send_alert(result, webhook_url="")
    assert sent is True


@patch("uptime_sentinel.alerts.requests.post")
def test_send_alert_with_webhook_posts_json(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    result = _ok_result(ok=False, error="timeout")
    sent = send_alert(result, webhook_url="https://hooks.example.com/x")
    assert sent is True
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert "text" in kwargs["json"]


@patch("uptime_sentinel.alerts.requests.post")
def test_process_result_only_alerts_on_transition(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    down = _ok_result(ok=False, error="timeout")

    # No previous state -> baseline, no alert.
    assert process_result(down, previous_ok=None, webhook_url="https://hooks.example.com/x") is False
    # Was up, now down -> alert.
    assert process_result(down, previous_ok=True, webhook_url="https://hooks.example.com/x") is True
    # Was already down -> no repeat alert.
    assert process_result(down, previous_ok=False, webhook_url="https://hooks.example.com/x") is False
    assert mock_post.call_count == 1
