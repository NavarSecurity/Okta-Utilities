from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from .config import ReconcileConfig
from .io_utils import write_csv, write_json


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def make_output_dir(base: str | Path = "output") -> Path:
    path = Path(base) / f"okta-user-reconciler-{utc_timestamp()}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_reports(out_dir: Path, config: ReconcileConfig, result: dict[str, Any], mode: str, errors: list[str] | None = None) -> None:
    errors = errors or []
    summary = result.get("summary", {})
    plan = {
        "mode": mode,
        "sourceUsersFile": str(config.source_users_file),
        "targetUsersFile": str(config.target_users_file),
        "primaryMatchField": config.match_rules.primary_match_field,
        "fallbackMatchFields": config.match_rules.fallback_match_fields,
        "profileFieldsToCompare": config.profile_fields_to_compare,
        "settings": config.settings.__dict__,
    }
    write_json(out_dir / "user_reconciliation_plan.json", plan)
    write_json(out_dir / "user_reconciliation_result.json", result)

    write_csv(out_dir / "matched_users.csv", result.get("matchedUsers", []))
    write_csv(out_dir / "source_only_users.csv", result.get("sourceOnlyUsers", []))
    write_csv(out_dir / "target_only_users.csv", result.get("targetOnlyUsers", []))
    write_csv(out_dir / "material_differences.csv", result.get("materialDifferences", []))
    write_csv(out_dir / "duplicate_users.csv", result.get("duplicateUsers", []))

    summary_md = [
        "# Okta User Reconciliation Summary",
        "",
        f"Mode: `{mode}`",
        "",
        "## Summary",
        "",
        f"- Source users: {summary.get('sourceUserCount', 0)}",
        f"- Target users: {summary.get('targetUserCount', 0)}",
        f"- Matched users: {summary.get('matchedUserCount', 0)}",
        f"- Matched without differences: {summary.get('matchedWithoutDifferences', 0)}",
        f"- Matched with material differences: {summary.get('matchedWithMaterialDifferences', 0)}",
        f"- Material field-level differences: {summary.get('materialDifferenceCount', 0)}",
        f"- Source-only users: {summary.get('sourceOnlyUserCount', 0)}",
        f"- Target-only users: {summary.get('targetOnlyUserCount', 0)}",
        f"- Duplicate or missing match-key records: {summary.get('duplicateOrMissingKeyCount', 0)}",
        "",
        "## Interpretation",
        "",
        "- Source-only users may need to be imported, intentionally excluded, or remediated.",
        "- Target-only users may be local admins, service accounts, test users, or unexpected accounts.",
        "- Material differences indicate matched users whose configured comparison fields differ.",
        "- Duplicate records should be reviewed before relying on the reconciliation result.",
    ]
    (out_dir / "reconciliation_summary.md").write_text("\n".join(summary_md), encoding="utf-8")

    report = [
        "# Execution Report",
        "",
        f"Utility: `okta-user-reconciler`",
        f"Mode: `{mode}`",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Files",
        "",
        f"- Source users file: `{config.source_users_file}`",
        f"- Target users file: `{config.target_users_file}`",
        "",
        "## Result Counts",
        "",
    ]
    for key, value in summary.items():
        report.append(f"- {key}: {value}")
    report.extend(["", "## Errors", ""])
    if errors:
        report.extend([f"- {err}" for err in errors])
    else:
        report.append("- None")
    (out_dir / "execution_report.md").write_text("\n".join(report), encoding="utf-8")
