from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Any


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict], fieldnames: list[str]) -> None:
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_execution_report(path: Path, result: dict) -> None:
    counts = result.get("counts", {})
    lines = [
        "# Okta Group Rule Create Execution Report",
        "",
        f"Mode: `{result.get('mode')}`",
        f"Target org: `{result.get('targetOrgUrl')}`",
        f"Run folder: `{result.get('runFolder')}`",
        "",
        "## Counts",
        "",
        f"- Rules in config: {counts.get('rulesInConfig', 0)}",
        f"- Planned: {counts.get('planned', 0)}",
        f"- Created: {counts.get('created', 0)}",
        f"- Activated: {counts.get('activated', 0)}",
        f"- Skipped: {counts.get('skipped', 0)}",
        f"- Failed: {counts.get('failed', 0)}",
        "",
        "## Output files",
        "",
        "```text",
        "group_rule_plan.json",
        "group_rule_create_result.json",
        "created_group_rules.csv",
        "skipped_group_rules.csv",
        "failed_group_rules.csv",
        "rollback_plan.json",
        "execution_report.md",
        "```",
        "",
    ]

    if result.get("errors"):
        lines.extend(["## Errors", ""])
        for error in result["errors"]:
            lines.append(f"- {error.get('ruleName', 'unknown')}: {error.get('message')}")
        lines.append("")

    if result.get("warnings"):
        lines.extend(["## Warnings", ""])
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
