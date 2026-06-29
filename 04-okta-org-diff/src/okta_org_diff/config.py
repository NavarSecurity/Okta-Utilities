from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any

DEFAULT_RESOURCES = [
    "org",
    "applications",
    "groups",
    "group_rules",
    "policies",
    "identity_providers",
    "authorization_servers",
    "trusted_origins",
    "network_zones",
    "domains",
    "brands",
    "authenticators",
    "event_hooks",
    "inline_hooks",
]

DEFAULT_IGNORE_FIELDS = [
    "id",
    "_links",
    "created",
    "lastUpdated",
    "lastMembershipUpdated",
    "createdBy",
    "lastUpdatedBy",
]


@dataclass
class DiffConfig:
    baseline_backup_dir: Path
    comparison_backup_dir: Path
    output_dir: Path = Path("output")
    include: list[str] = field(default_factory=lambda: list(DEFAULT_RESOURCES))
    ignore_fields: list[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_FIELDS))
    write_csv: bool = True
    write_markdown: bool = True
    strict_mode: bool = False
    fail_on_differences: bool = False
    max_diff_preview_chars: int = 500


def _camel_or_snake(data: dict[str, Any], camel: str, snake: str, default: Any = None) -> Any:
    if camel in data:
        return data[camel]
    if snake in data:
        return data[snake]
    return default


def load_config(path: str | Path | None) -> DiffConfig:
    data: dict[str, Any] = {}
    if path:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")
        data = json.loads(p.read_text(encoding="utf-8"))

    baseline = _camel_or_snake(data, "baselineBackupDir", "baseline_backup_dir")
    comparison = _camel_or_snake(data, "comparisonBackupDir", "comparison_backup_dir")

    if not baseline:
        raise ValueError("baselineBackupDir is required. Pass --baseline-backup-dir or set it in config.")
    if not comparison:
        raise ValueError("comparisonBackupDir is required. Pass --comparison-backup-dir or set it in config.")

    return DiffConfig(
        baseline_backup_dir=Path(baseline),
        comparison_backup_dir=Path(comparison),
        output_dir=Path(_camel_or_snake(data, "outputDir", "output_dir", "output")),
        include=list(_camel_or_snake(data, "include", "include", DEFAULT_RESOURCES)),
        ignore_fields=list(_camel_or_snake(data, "ignoreFields", "ignore_fields", DEFAULT_IGNORE_FIELDS)),
        write_csv=bool(_camel_or_snake(data, "writeCsv", "write_csv", True)),
        write_markdown=bool(_camel_or_snake(data, "writeMarkdown", "write_markdown", True)),
        strict_mode=bool(_camel_or_snake(data, "strictMode", "strict_mode", False)),
        fail_on_differences=bool(_camel_or_snake(data, "failOnDifferences", "fail_on_differences", False)),
        max_diff_preview_chars=int(_camel_or_snake(data, "maxDiffPreviewChars", "max_diff_preview_chars", 500)),
    )


def merge_cli_overrides(
    config: DiffConfig,
    baseline_backup_dir: str | None = None,
    comparison_backup_dir: str | None = None,
    output_dir: str | None = None,
    include: str | None = None,
    ignore_fields: str | None = None,
    strict: bool | None = None,
    fail_on_differences: bool | None = None,
) -> DiffConfig:
    if baseline_backup_dir:
        config.baseline_backup_dir = Path(baseline_backup_dir)
    if comparison_backup_dir:
        config.comparison_backup_dir = Path(comparison_backup_dir)
    if output_dir:
        config.output_dir = Path(output_dir)
    if include:
        config.include = [item.strip() for item in include.split(",") if item.strip()]
    if ignore_fields:
        merged = set(config.ignore_fields)
        merged.update(item.strip() for item in ignore_fields.split(",") if item.strip())
        config.ignore_fields = sorted(merged)
    if strict is True:
        config.strict_mode = True
    if fail_on_differences is True:
        config.fail_on_differences = True
    return config
