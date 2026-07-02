import json

from okta_scope_claim_exporter.cli import main


def test_cli_dry_run(tmp_path, monkeypatch):
    monkeypatch.delenv("OKTA_SOURCE_ORG_URL", raising=False)
    monkeypatch.delenv("OKTA_ORG_URL", raising=False)
    config_path = tmp_path / "config.json"
    output_dir = tmp_path / "output"
    config_path.write_text(
        json.dumps({"sourceOrgUrl": "https://example.okta.com", "outputDir": str(output_dir)}),
        encoding="utf-8",
    )
    rc = main(["--config", str(config_path), "--dry-run"])
    assert rc == 0
    runs = list(output_dir.iterdir())
    assert len(runs) == 1
    assert (runs[0] / "scope_claim_export_plan.json").exists()
