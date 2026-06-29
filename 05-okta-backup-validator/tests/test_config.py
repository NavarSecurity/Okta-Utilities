from __future__ import annotations

import json
from pathlib import Path

from okta_backup_validator.config import build_config


def test_build_config_from_file(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"backupDir": "backup", "outputDir": "out", "strictMode": True}), encoding="utf-8")

    cfg = build_config(cfg_path)

    assert cfg.backup_dir == Path("backup")
    assert cfg.output_dir == Path("out")
    assert cfg.strict_mode is True
    assert cfg.require_no_resource_errors is True
    assert cfg.fail_on_warnings is True


def test_cli_backup_dir_overrides_config(tmp_path: Path) -> None:
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps({"backupDir": "old"}), encoding="utf-8")

    cfg = build_config(cfg_path, cli_backup_dir=Path("new"))

    assert cfg.backup_dir == Path("new")
