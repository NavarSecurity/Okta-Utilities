import json
from pathlib import Path

from okta_app_provisioning_exporter.config import load_config
from okta_app_provisioning_exporter.exporter import dry_run


def test_dry_run_writes_evidence_files(tmp_path):
    output_dir = tmp_path / "output"
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"outputDirectory": str(output_dir)}), encoding="utf-8")

    cfg = load_config(config_path)
    result = dry_run(cfg)

    run_dir = Path(result["outputDirectory"])
    assert run_dir.exists()
    assert (run_dir / "dry_run_report.json").exists()
    assert (run_dir / "config_summary.json").exists()
    assert (run_dir / "execution_report.json").exists()
    assert (run_dir / "manifest.json").exists()

    report = json.loads((run_dir / "dry_run_report.json").read_text(encoding="utf-8"))
    assert report["status"] == "DRY_RUN_SUCCESS"
    assert report["willCallOkta"] is False
    assert report["willModifyOkta"] is False
