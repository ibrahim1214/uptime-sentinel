from pathlib import Path

import pytest

from uptime_sentinel.config import load_config


def test_load_config_parses_sites(tmp_path: Path):
    config_file = tmp_path / "sites.yaml"
    config_file.write_text(
        "db_path: test.db\n"
        "webhook_url: https://hooks.example.com/x\n"
        "sites:\n"
        "  - name: Example\n"
        "    url: https://example.com\n"
        "  - name: API\n"
        "    url: https://api.example.com/health\n"
        "    expected_status: 204\n"
        "    timeout: 5\n"
    )
    config = load_config(config_file)
    assert config.db_path == "test.db"
    assert config.webhook_url == "https://hooks.example.com/x"
    assert len(config.sites) == 2

    example = config.sites[0]
    assert example.name == "Example"
    assert example.expected_status == 200  # default
    assert example.timeout == 10  # default

    api = config.sites[1]
    assert api.expected_status == 204
    assert api.timeout == 5


def test_load_config_requires_at_least_one_site(tmp_path: Path):
    config_file = tmp_path / "empty.yaml"
    config_file.write_text("sites: []\n")
    with pytest.raises(ValueError, match="no sites"):
        load_config(config_file)


def test_load_config_requires_name_and_url(tmp_path: Path):
    config_file = tmp_path / "bad.yaml"
    config_file.write_text("sites:\n  - name: Missing URL\n")
    with pytest.raises(ValueError, match="name.*url"):
        load_config(config_file)


def test_load_config_defaults_db_path_and_webhook(tmp_path: Path):
    config_file = tmp_path / "minimal.yaml"
    config_file.write_text("sites:\n  - name: A\n    url: https://a.example.com\n")
    config = load_config(config_file)
    assert config.db_path == "uptime_sentinel.db"
    assert config.webhook_url == ""
