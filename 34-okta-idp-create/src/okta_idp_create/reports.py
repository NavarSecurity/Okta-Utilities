from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_run_dir(base_dir: Path) -> Path:
    run_dir = base_dir / f"idp-create-{utc_timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def summarize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append(
            {
                "name": record.get("name", ""),
                "type": record.get("type", ""),
                "action": record.get("action", ""),
                "result": record.get("result", ""),
                "id": record.get("id", ""),
                "message": record.get("message", ""),
            }
        )
    return rows


def write_standard_reports(
    run_dir: Path,
    planned: list[dict[str, Any]],
    redacted_payloads: list[dict[str, Any]],
    created: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    failed: list[dict[str, Any]],
    rollback_actions: list[dict[str, Any]],
    dry_run: bool,
    config_path: str,
    input_path: str,
) -> None:
    write_json(run_dir / "planned_changes.json", planned)
    write_json(run_dir / "idp_payloads_redacted.json", redacted_payloads)
    write_json(run_dir / "created_idps.json", created)
    write_json(run_dir / "skipped_existing.json", skipped)
    write_json(run_dir / "failed_idps.json", failed)
    write_json(run_dir / "rollback_actions.json", rollback_actions)

    all_records = []
    all_records.extend(planned)
    all_records.extend(created)
    all_records.extend(skipped)
    all_records.extend(failed)
    write_csv(
        run_dir / "idp_create_summary.csv",
        summarize_records(all_records),
        ["name", "type", "action", "result", "id", "message"],
    )

    execution_report = {
        "utility": "okta-idp-create",
        "mode": "dry-run" if dry_run else "apply",
        "timestamp": utc_timestamp(),
        "counts": {
            "planned": len(planned),
            "created": len(created),
            "skipped": len(skipped),
            "failed": len(failed),
            "rollbackActions": len(rollback_actions),
        },
        "success": len(failed) == 0,
    }
    write_json(run_dir / "execution_report.json", execution_report)

    manifest = {
        "utility": "okta-idp-create",
        "configFile": config_path,
        "inputFile": input_path,
        "outputDirectory": str(run_dir),
        "files": [
            "planned_changes.json",
            "idp_payloads_redacted.json",
            "created_idps.json",
            "skipped_existing.json",
            "failed_idps.json",
            "rollback_actions.json",
            "idp_create_summary.csv",
            "execution_report.json",
            "manifest.json",
        ],
    }
    write_json(run_dir / "manifest.json", manifest)
