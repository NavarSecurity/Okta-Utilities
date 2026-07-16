import json
from pathlib import Path

from okta_system_log_exporter.config import load_config
from okta_system_log_exporter.exporter import dry_run


def test_dry_run_writes_files(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "outputDirectory": str(tmp_path / "output"),
                "relativeHours": 1,
                "eventTypes": ["user.authentication.failed"],
            }
        ),
        encoding="utf-8",
    )
    cfg = load_config(config_path)
    run_dir = dry_run(str(config_path), cfg)
    assert (run_dir / "dry_run_report.json").exists()
    assert (run_dir / "config_summary.json").exists()
    assert (run_dir / "execution_report.json").exists()
    assert (run_dir / "manifest.json").exists()
