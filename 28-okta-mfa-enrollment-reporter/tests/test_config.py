import json
import os
from pathlib import Path

import pytest

from okta_mfa_enrollment_reporter.config import ConfigError, load_config, normalize_org_url


def test_normalize_rejects_admin_url():
    with pytest.raises(ConfigError):
        normalize_org_url("https://example-admin.okta.com")


def test_load_config_from_env(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "orgUrl": "https://placeholder.okta.com",
        "input": {"statuses": ["ACTIVE"]},
        "reporting": {"requiredFactorTypes": ["push"]},
        "settings": {"pageLimit": 100}
    }))
    monkeypatch.setenv("OKTA_ORG_URL", "https://example.okta.com")
    monkeypatch.setenv("OKTA_API_TOKEN", "token")
    cfg = load_config(config)
    assert cfg.org_url == "https://example.okta.com"
    assert cfg.reporting.required_factor_types == ["push"]
    assert cfg.settings.page_limit == 100
