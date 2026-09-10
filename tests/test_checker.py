from unittest.mock import MagicMock

import requests

from uptime_sentinel.checker import check_all, check_site
from uptime_sentinel.config import SiteConfig


def _mock_session(status_code=200, raise_exc=None):
    session = MagicMock()
    if raise_exc is not None:
        session.get.side_effect = raise_exc
    else:
        response = MagicMock()
        response.status_code = status_code
        session.get.return_value = response
    return session


def test_check_site_success():
    site = SiteConfig(name="A", url="https://a.example.com", expected_status=200)
    session = _mock_session(status_code=200)
    result = check_site(site, session=session)
    assert result.ok is True
    assert result.status_code == 200
    assert result.error == ""
    assert result.latency_ms is not None and result.latency_ms >= 0
    assert result.name == "A"


def test_check_site_wrong_status_is_not_ok():
    site = SiteConfig(name="A", url="https://a.example.com", expected_status=200)
    session = _mock_session(status_code=500)
    result = check_site(site, session=session)
    assert result.ok is False
    assert result.status_code == 500
    assert "expected status 200" in result.error


def test_check_site_network_error_is_not_ok():
    site = SiteConfig(name="A", url="https://a.example.com")
    session = _mock_session(raise_exc=requests.ConnectionError("boom"))
    result = check_site(site, session=session)
    assert result.ok is False
    assert result.status_code is None
    assert result.latency_ms is None
    assert "boom" in result.error


def test_check_site_respects_custom_expected_status():
    site = SiteConfig(name="A", url="https://a.example.com", expected_status=204)
    session = _mock_session(status_code=204)
    result = check_site(site, session=session)
    assert result.ok is True


def test_check_all_runs_every_site():
    sites = [
        SiteConfig(name="A", url="https://a.example.com"),
        SiteConfig(name="B", url="https://b.example.com"),
    ]
    session = _mock_session(status_code=200)
    results = check_all(sites, session=session)
    assert [r.name for r in results] == ["A", "B"]
    assert all(r.ok for r in results)
    assert session.get.call_count == 2
