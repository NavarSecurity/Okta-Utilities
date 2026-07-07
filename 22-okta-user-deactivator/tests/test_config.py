import json
from pathlib import Path

import pytest

from okta_user_deactivator.config import load_config, normalize_action


def test_load_config_normalizes_deactivate_alias(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "settings": {"defaultAction": "deactivate"}
    }), encoding="utf-8")
    config = load_config(path)
    assert config.settings.default_action == "deprovision"


def test_normalize_action_aliases():
    assert normalize_action("deactivate") == "deprovision"
    assert normalize_action("delete_deprovisioned") == "delete"
    assert normalize_action("suspend") == "suspend"


def test_rejects_invalid_default_action(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    path = tmp_path / "config.json"
    path.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "settings": {"defaultAction": "destroy"}
    }), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)
