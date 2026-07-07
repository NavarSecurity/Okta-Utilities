from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_reports(run_dir: Path, result: dict[str, Any]) -> None:
    (run_dir / "loader_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (run_dir / "group_membership_plan.json").write_text(json.dumps(result.get("plannedChanges", []), indent=2), encoding="utf-8")

    change_fields = [
        "row_number", "action", "group_id", "group_name", "user_id", "login", "email", "reason", "status", "message", "rollback_method", "rollback_endpoint"
    ]
    _write_csv(run_dir / "membership_changes.csv", result.get("plannedChanges", []), change_fields)
    _write_csv(run_dir / "applied_membership_changes.csv", result.get("appliedChanges", []), change_fields)
    _write_csv(run_dir / "skipped_memberships.csv", result.get("skippedRecords", []), ["row_number", "action", "group", "user", "reason"])
    _write_csv(run_dir / "failed_memberships.csv", result.get("failedRecords", []), ["row_number", "action", "group", "user", "error"])

    rollback = []
    for change in result.get("appliedChanges") or result.get("plannedChanges", []):
        if change.get("rollback_method") and change.get("rollback_endpoint"):
            rollback.append({
                "originalAction": change.get("action"),
                "userId": change.get("user_id"),
                "login": change.get("login"),
                "groupId": change.get("group_id"),
                "groupName": change.get("group_name"),
                "rollbackMethod": change.get("rollback_method"),
                "rollbackEndpoint": change.get("rollback_endpoint"),
                "reason": "Rollback reverses the membership action created by this run. Review before executing.",
            })
    (run_dir / "rollback_plan.json").write_text(json.dumps(rollback, indent=2), encoding="utf-8")

    summary = result.get("summary", {})
    report = [
        "# Okta Group Membership Loader Execution Report",
        "",
        f"Mode: `{result.get('mode')}`",
        f"Target org: `{result.get('targetOrgUrl')}`",
        "",
        "## Summary",
        "",
        f"- Input rows: {summary.get('inputRows', 0)}",
        f"- Valid rows: {summary.get('validRows', 0)}",
        f"- Planned changes: {summary.get('plannedChanges', 0)}",
        f"- Applied changes: {summary.get('appliedChanges', 0)}",
        f"- Skipped records: {summary.get('skippedRecords', 0)}",
        f"- Failed records: {summary.get('totalFailures', 0)}",
        "",
        "## Output files",
        "",
        "```text",
        "loader_result.json",
        "group_membership_plan.json",
        "membership_changes.csv",
        "applied_membership_changes.csv",
        "skipped_memberships.csv",
        "failed_memberships.csv",
        "rollback_plan.json",
        "execution_report.md",
        "```",
        "",
    ]
    if summary.get("totalFailures", 0):
        report.extend(["## Failure note", "", "Review `failed_memberships.csv` and `loader_result.json` before rerunning.", ""])
    (run_dir / "execution_report.md").write_text("\n".join(report), encoding="utf-8")
