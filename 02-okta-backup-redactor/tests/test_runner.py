import json
from pathlib import Path

from okta_backup_redactor.config import RedactorConfig
from okta_backup_redactor.runner import run_redaction


def make_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    (source / "applications.json").write_text(json.dumps({"clientSecret": "secret-value", "label": "App"}), encoding="utf-8")
    (source / "notes.txt").write_text("hello", encoding="utf-8")
    return source


def test_dry_run_does_not_write_redacted_backup(tmp_path):
    source = make_source(tmp_path)
    cfg = RedactorConfig(source_backup_dir=source, output_dir=tmp_path / "out")
    result = run_redaction(cfg, apply=False)
    assert result["mode"] == "dry-run"
    assert result["summary"]["totalFindings"] == 1
    assert not any((tmp_path / "out").rglob("redacted-backup"))


def test_apply_writes_redacted_copy_and_preserves_source(tmp_path):
    source = make_source(tmp_path)
    cfg = RedactorConfig(source_backup_dir=source, output_dir=tmp_path / "out")
    result = run_redaction(cfg, apply=True)
    redacted_dir = Path(result["redactedBackupDir"])
    redacted_app = json.loads((redacted_dir / "applications.json").read_text(encoding="utf-8"))
    original_app = json.loads((source / "applications.json").read_text(encoding="utf-8"))
    assert redacted_app["clientSecret"] == "[REDACTED]"
    assert original_app["clientSecret"] == "secret-value"
    assert (redacted_dir / "notes.txt").exists()
