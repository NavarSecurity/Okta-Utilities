from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path: str | Path) -> Path:
    output_path = Path(path)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def write_json(path: str | Path, data: Any) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = sorted({key for row in rows for key in row.keys()}) if rows else []
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def relative_files(base_dir: str | Path) -> list[str]:
    base = Path(base_dir)
    files: list[str] = []
    for path in sorted(base.rglob("*")):
        if path.is_file():
            files.append(str(path.relative_to(base)))
    return files


def build_manifest(operation: str, run_dir: str | Path, config_path: str, files: list[str]) -> dict[str, Any]:
    return {
        "utility": "okta-idp-exporter",
        "operation": operation,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "configPath": config_path,
        "outputDirectory": str(run_dir),
        "files": files,
    }
