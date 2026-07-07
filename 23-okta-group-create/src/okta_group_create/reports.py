from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_execution_report(path: Path, result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    lines = [
        f"# Okta Group Create Execution Report",
        "",
        f"Run ID: `{result.get('runId')}`",
        f"Mode: `{result.get('mode')}`",
        f"Target org: `{result.get('targetOrgUrl')}`",
        "",
        "## Summary",
        "",
        f"- Input rows: {summary.get('inputRows', 0)}",
        f"- Planned groups: {summary.get('plannedGroups', 0)}",
        f"- Created groups: {summary.get('createdGroups', 0)}",
        f"- Existing groups: {summary.get('existingGroups', 0)}",
        f"- Skipped groups: {summary.get('skippedGroups', 0)}",
        f"- Failed groups: {summary.get('failedGroups', 0)}",
        "",
    ]
    if result.get("errors"):
        lines.extend(["## Errors", ""])
        for error in result["errors"]:
            lines.append(f"- `{error.get('name', '')}`: {error.get('message', error.get('reason', ''))}")
        lines.append("")
    lines.extend([
        "## Output Files",
        "",
        "- `group_create_plan.json`",
        "- `group_create_result.json`",
        "- `created_groups.csv`",
        "- `existing_groups.csv`",
        "- `skipped_groups.csv`",
        "- `failed_groups.csv`",
        "- `rollback_plan.json`",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
