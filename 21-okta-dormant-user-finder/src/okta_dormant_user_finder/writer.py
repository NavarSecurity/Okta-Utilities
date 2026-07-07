from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CSV_COLUMNS = [
    "id", "login", "email", "action", "approved", "reason",
    "firstName", "lastName", "status", "created", "lastLogin", "passwordChanged",
    "appLinkCount", "groupCount", "createdDays", "lastLoginDays", "passwordChangedDays",
    "isDormantCandidate", "reasons", "evidence", "riskScore", "reviewPriority",
]


def run_folder(base: str = "output", prefix: str = "okta-dormant-user-finder") -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = Path(base) / f"{prefix}-{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    cols = columns or CSV_COLUMNS
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_summary_csv(path: Path, summary: dict[str, int]) -> None:
    rows = [{"reason": key, "count": value} for key, value in sorted(summary.items())]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["reason", "count"])
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, result: dict[str, Any]) -> None:
    counts = result.get("counts", {})
    lines = [
        "# Dormant User Finder Report",
        "",
        f"Mode: `{result.get('mode')}`",
        f"Source mode: `{result.get('sourceMode')}`",
        f"Org URL: `{result.get('orgUrl')}`",
        "",
        "## Summary",
        "",
        f"- Users analyzed: {counts.get('usersAnalyzed', 0)}",
        f"- Dormant candidates: {counts.get('dormantCandidates', 0)}",
        f"- Non-dormant users: {counts.get('nonDormantUsers', 0)}",
        "",
        "## Findings by Reason",
        "",
    ]
    summary = result.get("summaryByReason", {})
    if summary:
        for reason, count in sorted(summary.items()):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- No dormant candidates found.")
    warnings = result.get("warnings", [])
    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")
    lines.extend([
        "",
        "## Review Guidance",
        "",
        "This report identifies accounts that should be reviewed. It does not deactivate, suspend, deprovision, delete, or modify users.",
        "The dormant_users.csv file includes action, approved, and reason columns so it can be reviewed and then used with Utility 22.",
        "Validate each candidate with the account owner, HR/source of truth, application owner, or support process before setting approved=true and taking lifecycle action.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_execution_report(path: Path, result: dict[str, Any]) -> None:
    counts = result.get("counts", {})
    lines = [
        "# Execution Report",
        "",
        f"Mode: `{result.get('mode')}`",
        f"Source mode: `{result.get('sourceMode')}`",
        f"Org URL: `{result.get('orgUrl')}`",
        "",
        "## Counts",
        "",
    ]
    if counts:
        for key, value in counts.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- Plan generated only; no users were analyzed.")
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    write_json(out_dir / "finder_result.json", result)
    if result.get("mode") == "dry-run":
        write_json(out_dir / "dormant_user_plan.json", result)
        write_execution_report(out_dir / "execution_report.md", result)
        return
    write_csv(out_dir / "dormant_users.csv", result.get("dormantUsers", []))
    write_csv(out_dir / "all_users_analyzed.csv", result.get("allUsersAnalyzed", []))
    write_summary_csv(out_dir / "summary_by_reason.csv", result.get("summaryByReason", {}))
    if result.get("rawUsers"):
        write_json(out_dir / "raw_users.json", result.get("rawUsers", []))
    write_report(out_dir / "dormant_user_report.md", result)
    write_execution_report(out_dir / "execution_report.md", result)
