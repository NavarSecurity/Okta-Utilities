import json
from pathlib import Path

from okta_group_rule_create.cli import main


def test_cli_dry_run(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_API_TOKEN", raising=False)
    config = {
        "targetOrgUrl": "https://example.okta.com",
        "apiToken": "token",
        "rules": [
            {
                "name": "Rule - CLI",
                "approved": True,
                "expression": "user.department == \"CLI\"",
                "targetGroupIds": ["00gcli"],
            }
        ],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    assert main(["--config", str(path), "--output-dir", str(tmp_path), "--dry-run"]) == 0
