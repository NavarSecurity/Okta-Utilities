import json
from pathlib import Path

from okta_config_backup.config import build_config


def test_build_config_uses_env_token_and_cli_include(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"orgUrl": "https://example.okta.com", "include": ["applications"], "outputDir": "output"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("OKTA_API_TOKEN", "token-value")

    cfg = build_config(config_path=config_path, cli_include="groups,policies", dry_run=False)

    assert cfg.org_url == "https://example.okta.com"
    assert cfg.api_token == "token-value"
    assert cfg.include == ["groups", "policies"]


def test_dry_run_does_not_require_api_token(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"orgUrl": "https://example.okta.com"}), encoding="utf-8")
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)

    cfg = build_config(config_path=config_path, dry_run=True)

    assert cfg.api_token is None
