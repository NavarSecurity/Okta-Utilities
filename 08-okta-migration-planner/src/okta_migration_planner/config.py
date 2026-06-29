from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io_utils import read_json

DEFAULT_RESOURCES = [
    "groups",
    "applications",
    "trusted_origins",
    "network_zones",
    "authorization_servers",
    "policies",
    "identity_providers",
]


@dataclass
class PlannerConfig:
    source_backup_dir: Path
    target_backup_dir: Path
    output_dir: Path = Path("output")
    include: list[str] = field(default_factory=lambda: list(DEFAULT_RESOURCES))
    compare_material_differences: bool = True
    treat_missing_high_risk_as_blocker: bool = True
    strict_mode: bool = False
    write_csv: bool = True
    write_markdown: bool = True
    max_json_preview_chars: int = 300


def load_config(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return read_json(path)


def build_config(
    config_path: Path | None = None,
    source_backup_dir: str | None = None,
    target_backup_dir: str | None = None,
    output_dir: str | None = None,
    include: str | None = None,
    strict: bool | None = None,
) -> PlannerConfig:
    raw = load_config(config_path)

    source = source_backup_dir or raw.get("sourceBackupDir")
    target = target_backup_dir or raw.get("targetBackupDir")
    if not source:
        raise ValueError("sourceBackupDir is required. Provide it in config or with --source-backup-dir.")
    if not target:
        raise ValueError("targetBackupDir is required. Provide it in config or with --target-backup-dir.")

    include_list = raw.get("include", list(DEFAULT_RESOURCES))
    if include:
        include_list = [item.strip() for item in include.split(",") if item.strip()]

    return PlannerConfig(
        source_backup_dir=Path(source),
        target_backup_dir=Path(target),
        output_dir=Path(output_dir or raw.get("outputDir", "output")),
        include=include_list,
        compare_material_differences=bool(raw.get("compareMaterialDifferences", True)),
        treat_missing_high_risk_as_blocker=bool(raw.get("treatMissingHighRiskAsBlocker", True)),
        strict_mode=bool(strict if strict is not None else raw.get("strictMode", False)),
        write_csv=bool(raw.get("writeCsv", True)),
        write_markdown=bool(raw.get("writeMarkdown", True)),
        max_json_preview_chars=int(raw.get("maxJsonPreviewChars", 300)),
    )
