import json

from okta_oidc_app_create.config import load_config
from okta_oidc_app_create.runner import run_create


def test_dry_run_without_token_creates_plan(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_TARGET_API_TOKEN", raising=False)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "targetOrgUrl": "https://example.okta.com",
        "outputDir": str(tmp_path / "output"),
        "applications": [{
            "label": "App",
            "applicationType": "web",
            "grantTypes": ["authorization_code"],
            "responseTypes": ["code"]
        }]
    }))
    cfg = load_config(config_path)
    code, run_dir, result = run_create(cfg, apply=False)
    assert code == 0
    assert (run_dir / "oidc_app_create_plan.json").exists()
    assert result["counts"]["planned"] == 1
