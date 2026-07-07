from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .models import ActionResult, PlanItem
from .utils import write_json


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys or ["message"]
    with p.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_plan(output_dir: Path, plan: list[PlanItem]) -> None:
    plan_rows = [item.to_dict() for item in plan]
    write_json(output_dir / "user_lifecycle_plan.json", plan_rows)
    write_csv(output_dir / "user_lifecycle_plan.csv", plan_rows)
    # Backward-compatible aliases for earlier Utility 22 versions.
    write_json(output_dir / "user_deactivation_plan.json", plan_rows)
    write_csv(output_dir / "user_deactivation_plan.csv", plan_rows)


def rollback_entry(result: ActionResult) -> dict[str, Any] | None:
    if not result.success or result.skipped or not result.rollback_action:
        return None
    note = "Review before executing."
    if result.action == "deprovision":
        note += " Re-activating a user may not fully restore app assignments or downstream provisioning state."
    elif result.action == "suspend":
        note += " Unsuspending a user reverses the Okta suspension state but should still be reviewed."
    return {
        "userId": result.okta_user_id,
        "login": result.login,
        "originalAction": result.action,
        "rollbackAction": result.rollback_action,
        "rollbackEndpoint": result.rollback_endpoint,
        "note": note,
    }


def write_results(output_dir: Path, mode: str, plan: list[PlanItem], results: list[ActionResult], errors: list[str]) -> None:
    result_rows = [r.to_dict() for r in results]
    changed = [r.to_dict() for r in results if r.success and not r.skipped]
    skipped = [r.to_dict() for r in results if r.skipped]
    failed = [r.to_dict() for r in results if not r.success and not r.skipped]
    rollback = [entry for r in results if (entry := rollback_entry(r))]
    summary = {
        "mode": mode,
        "plannedCount": len([p for p in plan if p.planned]),
        "skippedPlanCount": len([p for p in plan if not p.planned]),
        "changedCount": len(changed),
        "skippedCount": len(skipped),
        "failedCount": len(failed),
        "suspendCount": len([r for r in results if r.success and not r.skipped and r.action == "suspend"]),
        "deprovisionCount": len([r for r in results if r.success and not r.skipped and r.action == "deprovision"]),
        "deleteCount": len([r for r in results if r.success and not r.skipped and r.action == "delete"]),
        "errors": errors,
        "results": result_rows,
    }
    write_json(output_dir / "user_lifecycle_result.json", summary)
    write_json(output_dir / "user_deactivation_result.json", summary)
    write_csv(output_dir / "changed_users.csv", changed)
    write_csv(output_dir / "skipped_users.csv", skipped)
    write_csv(output_dir / "failed_users.csv", failed)
    write_json(output_dir / "rollback_plan.json", rollback)
    write_execution_report(output_dir, summary, rollback)


def write_execution_report(output_dir: Path, summary: dict[str, Any], rollback: list[dict[str, Any]]) -> None:
    lines = [
        "# Okta User Lifecycle Execution Report",
        "",
        f"Mode: `{summary['mode']}`",
        "",
        "## Summary",
        "",
        f"- Planned users: {summary['plannedCount']}",
        f"- Plan-level skipped users: {summary['skippedPlanCount']}",
        f"- Changed users: {summary['changedCount']}",
        f"- Suspended users: {summary.get('suspendCount', 0)}",
        f"- Deprovisioned users: {summary.get('deprovisionCount', 0)}",
        f"- Deleted users: {summary.get('deleteCount', 0)}",
        f"- Runtime skipped users: {summary['skippedCount']}",
        f"- Failed users: {summary['failedCount']}",
        f"- Rollback entries: {len(rollback)}",
        "",
        "## Output files",
        "",
        "- `user_lifecycle_plan.json`",
        "- `user_lifecycle_plan.csv`",
        "- `user_lifecycle_result.json`",
        "- `changed_users.csv`",
        "- `skipped_users.csv`",
        "- `failed_users.csv`",
        "- `rollback_plan.json`",
        "",
    ]
    if summary.get("errors"):
        lines.extend(["## Errors", ""])
        for error in summary["errors"]:
            lines.append(f"- {error}")
        lines.append("")
    lines.extend([
        "## Rollback note",
        "",
        "Review `rollback_plan.json` before taking any corrective action. Suspending users can usually be reversed with unsuspend. Deprovisioning users may trigger app deprovisioning and may not be fully reversible through a single activate call. Deleted users cannot be restored by this utility.",
        "",
    ])
    (output_dir / "execution_report.md").write_text("\n".join(lines), encoding="utf-8")
