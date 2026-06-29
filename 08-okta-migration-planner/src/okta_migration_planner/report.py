from __future__ import annotations

from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_json, write_text

MAPPING_FIELDS = [
    "resource",
    "status",
    "source_id",
    "target_id",
    "source_key",
    "target_key",
    "source_name",
    "target_name",
    "confidence",
    "reason",
    "recommended_action",
]

CONFLICT_FIELDS = [
    "resource",
    "conflict_type",
    "source_id",
    "target_id",
    "natural_key",
    "source_name",
    "target_name",
    "reason",
    "recommended_action",
]

MANUAL_REVIEW_FIELDS = [
    "resource",
    "item_id",
    "item_key",
    "item_name",
    "reason",
    "recommended_action",
]


def write_outputs(output_dir: Path, plan: Any, write_csv_files: bool = True, write_markdown: bool = True) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_dict = _to_dict(plan)
    paths: dict[str, str] = {}

    migration_plan_path = output_dir / "migration_plan.json"
    write_json(migration_plan_path, plan_dict)
    paths["migration_plan"] = str(migration_plan_path)

    if write_csv_files:
        mapping_path = output_dir / "object_mapping.csv"
        conflict_path = output_dir / "conflicts.csv"
        manual_path = output_dir / "manual_review_items.csv"
        write_csv(mapping_path, plan_dict.get("object_mappings", []), MAPPING_FIELDS)
        write_csv(conflict_path, plan_dict.get("conflicts", []), CONFLICT_FIELDS)
        write_csv(manual_path, plan_dict.get("manual_review_items", []), MANUAL_REVIEW_FIELDS)
        paths["object_mapping"] = str(mapping_path)
        paths["conflicts"] = str(conflict_path)
        paths["manual_review_items"] = str(manual_path)

    if write_markdown:
        readiness_path = output_dir / "cutover_readiness_report.md"
        execution_path = output_dir / "execution_report.md"
        write_text(readiness_path, render_cutover_readiness(plan_dict))
        write_text(execution_path, render_execution_report(plan_dict))
        paths["cutover_readiness_report"] = str(readiness_path)
        paths["execution_report"] = str(execution_path)

    return paths


def render_cutover_readiness(plan: dict[str, Any]) -> str:
    readiness = plan.get("cutover_readiness", {})
    summary = plan.get("summary", {})
    lines = [
        "# Okta Migration Cutover Readiness Report",
        "",
        f"**Plan ID:** `{plan.get('plan_id')}`",
        f"**Generated:** `{plan.get('generated_at')}`",
        f"**Overall Status:** `{readiness.get('overallStatus')}`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
    ]
    for key, value in summary.items():
        lines.append(f"| {key} | {value} |")

    lines.extend(["", "## Blockers", ""])
    blockers = readiness.get("blockers", [])
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Warnings", ""])
    warnings = readiness.get("warnings", [])
    if warnings:
        for item in warnings:
            lines.append(f"- {item}")
    else:
        lines.append("- None recorded.")

    lines.extend(["", "## Recommended Next Steps", ""])
    for item in readiness.get("recommendedNextSteps", []):
        lines.append(f"- {item}")

    lines.extend(["", "## Resource Summary", "", "| Resource | Source | Target | Matched | Create Candidates | Differences | Manual Review | Target Only |", "|---|---:|---:|---:|---:|---:|---:|---:|"])
    for resource, resource_plan in plan.get("resource_plans", {}).items():
        lines.append(
            f"| {resource} | {resource_plan.get('source_count', 0)} | {resource_plan.get('target_count', 0)} | "
            f"{resource_plan.get('matched_count', 0)} | {resource_plan.get('create_count', 0)} | "
            f"{resource_plan.get('difference_count', 0)} | {resource_plan.get('manual_review_count', 0)} | "
            f"{resource_plan.get('target_only_count', 0)} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_execution_report(plan: dict[str, Any]) -> str:
    lines = [
        "# Okta Migration Planner Execution Report",
        "",
        f"**Plan ID:** `{plan.get('plan_id')}`",
        f"**Generated:** `{plan.get('generated_at')}`",
        f"**Source Backup:** `{plan.get('source_backup_dir')}`",
        f"**Target Backup:** `{plan.get('target_backup_dir')}`",
        f"**Overall Status:** `{plan.get('overall_status')}`",
        "",
        "## Included Resources",
        "",
    ]
    for resource in plan.get("included_resources", []):
        lines.append(f"- `{resource}`")

    lines.extend(["", "## Issues", ""])
    issues = plan.get("issues", [])
    if issues:
        lines.extend(["| Severity | Code | Resource | File | Message |", "|---|---|---|---|---|"])
        for issue in issues:
            lines.append(
                f"| {issue.get('severity')} | {issue.get('code')} | {issue.get('resource')} | "
                f"{issue.get('file') or ''} | {str(issue.get('message', '')).replace('|', '/')} |"
            )
    else:
        lines.append("No issues recorded.")

    lines.extend(["", "## Conflicts", ""])
    conflicts = plan.get("conflicts", [])
    if conflicts:
        lines.extend(["| Resource | Conflict Type | Key | Reason | Recommended Action |", "|---|---|---|---|---|"])
        for conflict in conflicts[:50]:
            lines.append(
                f"| {conflict.get('resource')} | {conflict.get('conflict_type')} | {conflict.get('natural_key')} | "
                f"{str(conflict.get('reason', '')).replace('|', '/')} | {str(conflict.get('recommended_action', '')).replace('|', '/')} |"
            )
        if len(conflicts) > 50:
            lines.append(f"\nAdditional conflicts omitted from markdown preview: {len(conflicts) - 50}")
    else:
        lines.append("No conflicts recorded.")

    lines.append("")
    return "\n".join(lines)


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(value)
    if isinstance(value, dict):
        return value
    raise TypeError(f"Unsupported plan object: {type(value)!r}")
