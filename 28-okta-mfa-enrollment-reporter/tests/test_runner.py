import json
from pathlib import Path

from okta_mfa_enrollment_reporter.config import load_config
from okta_mfa_enrollment_reporter.runner import build_plan, selection_mode


def test_build_plan_group_mode(tmp_path, monkeypatch):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "orgUrl": "https://example.okta.com",
        "input": {"groupIds": ["00g1"], "statuses": ["ACTIVE"]},
        "reporting": {"requiredFactorTypes": ["push"]},
        "settings": {"pageLimit": 50}
    }))
    monkeypatch.setenv("OKTA_API_TOKEN", "token")
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    cfg = load_config(config)
    assert selection_mode(cfg) == "groups"
    plan = build_plan(cfg, "dry-run")
    assert plan["selection"]["groupIds"] == ["00g1"]
