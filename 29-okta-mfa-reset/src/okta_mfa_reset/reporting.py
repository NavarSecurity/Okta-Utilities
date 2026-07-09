from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .io_utils import write_csv, write_json


def rollback_plan(result: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    for row in result.get("changed", []):
        items.append({
            "userId": row.get("resolvedUserId") or row.get("userId"),
            "login": row.get("resolvedLogin") or row.get("login"),
            "actionPerformed": row.get("action"),
            "rollbackAvailable": False,
            "rollbackGuidance": "MFA reset cannot be automatically rolled back. User must re-enroll required MFA/authenticator factors through the normal Okta enrollment flow.",
            "reason": row.get("reason", ""),
        })
    return {"rollbackItems": items}


def write_reports(output_dir: Path, plan: Dict[str, Any], result: Dict[str, Any]) -> None:
    write_json(output_dir / "mfa_reset_plan.json", plan)
    write_json(output_dir / "mfa_reset_result.json", result)
    write_json(output_dir / "rollback_plan.json", rollback_plan(result))

    write_csv(output_dir / "changed_mfa_resets.csv", result.get("changed", []))
    write_csv(output_dir / "skipped_mfa_resets.csv", result.get("skipped", []))
    write_csv(output_dir / "failed_mfa_resets.csv", result.get("failed", []))

    summary = result.get("summary", {})
    report = [
        "# Okta MFA Reset Execution Report",
        "",
        f"Mode: {summary.get('mode', 'unknown')}",
        f"Changed / Would change: {summary.get('changedOrWouldChange', 0)}",
        f"Skipped: {len(result.get('skipped', []))}",
        f"Failed: {summary.get('failed', 0)}",
        "",
        "## Notes",
        "",
        "MFA resets are not automatically reversible. Affected users may need to re-enroll MFA/authenticator factors.",
    ]
    (output_dir / "execution_report.md").write_text("\n".join(report), encoding="utf-8")
