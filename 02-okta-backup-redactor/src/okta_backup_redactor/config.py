from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass(slots=True)
class RedactorConfig:
    source_backup_dir: Path
    output_dir: Path = Path("output")
    include_files: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)
    replacement: str = "[REDACTED]"
    copy_non_json_files: bool = True
    redact_known_secret_keys: bool = True
    redact_authorization_headers: bool = True
    redact_private_key_blocks: bool = True
    redact_bearer_values: bool = True
    redact_high_entropy_values: bool = False
    max_value_preview_chars: int = 160
    fail_on_findings: bool = False
    strict_mode: bool = False


def _camel_to_snake(name: str) -> str:
    out: list[str] = []
    for ch in name:
        if ch.isupper() and out:
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def _normalize_config_keys(obj):
    if isinstance(obj, dict):
        return {_camel_to_snake(str(k)): _normalize_config_keys(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_config_keys(v) for v in obj]
    return obj


def load_config(path: str | Path | None, *, source_backup_dir: str | Path | None = None, output_dir: str | Path | None = None) -> RedactorConfig:
    raw: dict = {}
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")
        raw = _normalize_config_keys(json.loads(p.read_text(encoding="utf-8")))

    if source_backup_dir is not None:
        raw["source_backup_dir"] = str(source_backup_dir)
    if output_dir is not None:
        raw["output_dir"] = str(output_dir)

    if not raw.get("source_backup_dir"):
        raise ValueError("sourceBackupDir is required. Provide it in config or with --source-backup-dir.")

    cfg = RedactorConfig(
        source_backup_dir=Path(raw["source_backup_dir"]),
        output_dir=Path(raw.get("output_dir", "output")),
        include_files=list(raw.get("include_files", [])),
        exclude_files=list(raw.get("exclude_files", [])),
        replacement=str(raw.get("replacement", "[REDACTED]")),
        copy_non_json_files=bool(raw.get("copy_non_json_files", True)),
        redact_known_secret_keys=bool(raw.get("redact_known_secret_keys", True)),
        redact_authorization_headers=bool(raw.get("redact_authorization_headers", True)),
        redact_private_key_blocks=bool(raw.get("redact_private_key_blocks", True)),
        redact_bearer_values=bool(raw.get("redact_bearer_values", True)),
        redact_high_entropy_values=bool(raw.get("redact_high_entropy_values", False)),
        max_value_preview_chars=int(raw.get("max_value_preview_chars", 160)),
        fail_on_findings=bool(raw.get("fail_on_findings", False)),
        strict_mode=bool(raw.get("strict_mode", False)),
    )
    return cfg
