from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_output_dir(base_dir: str | Path, prefix: str = "admin-role-report") -> Path:
    path = Path(base_dir) / f"{prefix}-{utc_timestamp()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key, "")) for key in fieldnames})


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary", {})
    lines = [
        "# Okta Admin Role Report",
        "",
        "## Summary",
        "",
        f"- Status: `{report.get('status', '')}`",
        f"- Timestamp: `{report.get('timestamp', '')}`",
        f"- User role assignments: `{summary.get('userRoleAssignments', 0)}`",
        f"- Group role assignments: `{summary.get('groupRoleAssignments', 0)}`",
        f"- Client role assignments: `{summary.get('clientRoleAssignments', 0)}`",
        f"- Custom roles exported: `{summary.get('customRoles', 0)}`",
        f"- Resource sets exported: `{summary.get('resourceSets', 0)}`",
        f"- High privilege assignments: `{summary.get('highPrivilegeAssignments', 0)}`",
        f"- Request failures: `{summary.get('requestFailures', 0)}`",
        "",
        "## Review Notes",
        "",
        "Review `privileged_assignments.csv` first. It is the fastest view of who has elevated admin access.",
        "Review `admin_role_targets.csv` to identify scoped or delegated administration boundaries.",
        "Review `resource_set_bindings.csv` and `binding_members.csv` when custom admin roles are used.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def manifest(config_path: str, output_dir: Path, generated_files: list[str]) -> dict[str, Any]:
    return {
        "utility": "okta-admin-role-reporter",
        "timestamp": utc_timestamp(),
        "configPath": config_path,
        "outputDirectory": str(output_dir),
        "generatedFiles": generated_files,
    }
