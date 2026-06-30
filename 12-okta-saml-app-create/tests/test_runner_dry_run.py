import json
from pathlib import Path

from okta_saml_app_create.config import load_config
from okta_saml_app_create.runner import run


def test_dry_run_without_token_writes_outputs(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OKTA_TARGET_ORG_URL", "https://example.okta.com")
    monkeypatch.delenv("OKTA_TARGET_API_TOKEN", raising=False)
    config = {
        "outputDir": str(tmp_path / "output"),
        "app": {
            "label": "App",
            "ssoAcsUrl": "https://example.com/acs",
            "recipient": "https://example.com/acs",
            "destination": "https://example.com/acs",
            "audience": "https://example.com/metadata",
        },
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    cfg = load_config(path)
    result, out_dir = run(cfg, apply=False)
    assert result["status"] == "DRY_RUN_COMPLETE"
    assert (out_dir / "saml_app_create_plan.json").exists()
    assert (out_dir / "execution_report.md").exists()
    assert "WARNING" not in (out_dir / "execution_report.md").read_text(encoding="utf-8")
