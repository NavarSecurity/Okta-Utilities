from pathlib import Path
import json

import pytest

from okta_app_assignment_exporter.config import ConfigError, load_config


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def base_config() -> dict:
    return {
        "targetOrgUrl": "https://example.okta.com",
        "outputDir": "output",
        "appSelection": {"mode": "all", "statuses": ["ACTIVE"]},
        "exportOptions": {"includeUsers": True, "includeGroups": True},
        "http": {"pageLimit": 200},
    }


def test_load_config_basic(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    path = write_config(tmp_path, base_config())
    cfg = load_config(path)
    assert cfg.target_org_url == "https://example.okta.com"
    assert cfg.app_selection.mode == "all"
    assert cfg.app_selection.statuses == ["ACTIVE"]
    assert cfg.export_options.include_users is True


def test_reject_admin_org_url(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    data = base_config()
    data["targetOrgUrl"] = "https://example-admin.okta.com"
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        load_config(path)


def test_labels_mode_requires_labels(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    data = base_config()
    data["appSelection"] = {"mode": "labels", "appLabels": []}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        load_config(path)


def test_page_limit_max_200(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    data = base_config()
    data["http"] = {"pageLimit": 500}
    path = write_config(tmp_path, data)
    with pytest.raises(ConfigError):
        load_config(path)
