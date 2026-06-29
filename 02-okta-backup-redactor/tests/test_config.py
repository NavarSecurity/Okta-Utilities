import json
from pathlib import Path

from okta_backup_redactor.config import load_config


def test_load_config_camel_case(tmp_path: Path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"sourceBackupDir": "backup", "outputDir": "out", "failOnFindings": True}), encoding="utf-8")
    cfg = load_config(cfg_file)
    assert str(cfg.source_backup_dir) == "backup"
    assert str(cfg.output_dir) == "out"
    assert cfg.fail_on_findings is True
