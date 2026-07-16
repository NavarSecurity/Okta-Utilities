from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_run_dir(base_dir: str | Path, prefix: str) -> Path:
    run_dir = Path(base_dir) / f"{prefix}-{timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: str | Path, data: Any) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=False)
        handle.write("\n")


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path = Path(path)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_manifest(
    *,
    operation: str,
    config_path: str,
    output_files: Iterable[str],
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "operation": operation,
        "configPath": config_path,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "outputFiles": list(output_files),
        "warnings": warnings or [],
        "errors": errors or [],
    }
