from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def safe_filename(value: str) -> str:
    allowed = []
    for char in value:
        if char.isalnum() or char in ["-", "_", "."]:
            allowed.append(char)
        elif char.isspace():
            allowed.append("_")
    result = "".join(allowed).strip("._-")
    return result[:120] or "schema"


def create_run_dir(output_directory: str, prefix: str = "profile-schema-export") -> Path:
    run_dir = Path(output_directory) / f"{prefix}-{timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_manifest(run_dir: Path, operation: str, output_files: list[str], config: dict[str, Any]) -> None:
    manifest = {
        "operation": operation,
        "createdAt": timestamp(),
        "outputDirectory": str(run_dir),
        "outputFiles": output_files,
        "configSummary": {
            "includeUserSchemas": config.get("includeUserSchemas"),
            "userSchemaIds": config.get("userSchemaIds"),
            "includeGroupSchema": config.get("includeGroupSchema"),
            "includeAppSchemas": config.get("includeAppSchemas"),
            "appSelection": config.get("appSelection"),
            "includeInactiveApps": config.get("includeInactiveApps"),
        },
    }
    write_json(run_dir / "manifest.json", manifest)


def write_execution_report(run_dir: Path, report: dict[str, Any]) -> None:
    write_json(run_dir / "execution_report.json", report)
