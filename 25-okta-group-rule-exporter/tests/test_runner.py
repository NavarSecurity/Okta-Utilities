import json
from pathlib import Path

from okta_group_rule_exporter.config import AppConfig, ExportOptions, Settings
from okta_group_rule_exporter.runner import run_export


def test_dry_run_writes_output(tmp_path):
    cfg = AppConfig(
        target_org_url="https://example.okta.com",
        api_token="token",
        output_dir=tmp_path / "output",
        export=ExportOptions(),
        settings=Settings(),
    )
    result = run_export(cfg, "dry-run")
    run_dir = Path(result["runDirectory"])
    assert (run_dir / "group_rules.csv").exists()
    assert (run_dir / "execution_report.md").exists()
    assert result["rulesExported"] == 0
