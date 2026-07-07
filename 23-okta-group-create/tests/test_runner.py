import json
from pathlib import Path

from okta_group_create.config import load_config
from okta_group_create.runner import run


def test_dry_run_creates_outputs(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_TARGET_ORG_URL", raising=False)
    groups = tmp_path / "groups.csv"
    groups.write_text("name,description\nDry Run Group,Desc\n", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"targetOrgUrl": "https://example.okta.com", "groupsFile": str(groups)}), encoding="utf-8")
    cfg = load_config(config)
    result = run(cfg, apply=False, output_dir=tmp_path / "output")
    assert result["summary"]["plannedGroups"] == 1
    assert Path(result["outputDir"], "group_create_plan.json").exists()
