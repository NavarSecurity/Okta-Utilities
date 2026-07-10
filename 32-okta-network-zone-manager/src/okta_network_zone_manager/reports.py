from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class RunResult:
    operation: str
    output_dir: Path
    counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    dry_run: bool = True

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def add_file(self, path: Path) -> None:
        self.files.append(str(path))

    def console_summary(self) -> str:
        mode = "dry-run" if self.dry_run else "apply"
        count_text = ", ".join(f"{k}={v}" for k, v in sorted(self.counts.items())) or "no counts"
        warning_text = f", warnings={len(self.warnings)}" if self.warnings else ""
        error_text = f", errors={len(self.errors)}" if self.errors else ""
        return f"{self.operation} completed ({mode}): {count_text}{warning_text}{error_text}. Output: {self.output_dir}"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_run_dir(base_dir: str | Path, operation: str) -> Path:
    path = Path(base_dir) / f"network-zone-{operation}-{utc_timestamp()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: stringify_cell(row.get(k, "")) for k in fieldnames})
    return path


def stringify_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def finalize_result(result: RunResult, details: dict[str, Any] | None = None) -> RunResult:
    report = {
        "operation": result.operation,
        "dryRun": result.dry_run,
        "counts": result.counts,
        "warnings": result.warnings,
        "errors": result.errors,
        "files": result.files,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        report["details"] = details
    report_path = write_json(result.output_dir / "execution_report.json", report)
    result.add_file(report_path)

    manifest = {
        "operation": result.operation,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "fileCount": len(result.files),
        "files": result.files,
    }
    manifest_path = write_json(result.output_dir / "manifest.json", manifest)
    result.add_file(manifest_path)
    return result
