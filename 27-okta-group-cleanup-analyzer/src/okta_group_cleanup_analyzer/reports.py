from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import write_csv, write_json

OUTPUT_FIELDS = [
    "id",
    "name",
    "type",
    "created",
    "lastUpdated",
    "description",
    "owner",
    "memberCount",
    "appAssignmentCount",
    "ruleTargetCount",
    "duplicateCount",
    "isProtected",
    "reasonCodes",
    "recommendation",
    "evidenceNotes",
]


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_output_dir(base: str | Path) -> Path:
    out = Path(base) / f"okta-group-cleanup-analyzer-{timestamp()}"
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_outputs(out_dir: Path, result: dict[str, Any], dry_run: bool = False) -> None:
    if dry_run:
        write_json(out_dir / "group_cleanup_plan.json", result)
        (out_dir / "execution_report.md").write_text(render_execution_report(result, dry_run=True), encoding="utf-8")
        return

    write_json(out_dir / "group_cleanup_result.json", result)
    write_csv(out_dir / "group_cleanup_candidates.csv", result.get("candidates", []), OUTPUT_FIELDS)
    write_csv(out_dir / "empty_groups.csv", result.get("emptyGroups", []), OUTPUT_FIELDS)
    write_csv(out_dir / "unused_groups.csv", result.get("unusedGroups", []), OUTPUT_FIELDS)
    write_csv(out_dir / "duplicate_groups.csv", result.get("duplicateGroups", []), OUTPUT_FIELDS)
    write_csv(out_dir / "stale_groups.csv", result.get("staleGroups", []), OUTPUT_FIELDS)
    write_csv(out_dir / "ownerless_groups.csv", result.get("ownerlessGroups", []), OUTPUT_FIELDS)
    write_csv(out_dir / "protected_groups.csv", result.get("protectedGroups", []), OUTPUT_FIELDS)
    (out_dir / "group_cleanup_summary.md").write_text(render_summary(result), encoding="utf-8")
    (out_dir / "execution_report.md").write_text(render_execution_report(result, dry_run=False), encoding="utf-8")


def render_summary(result: dict[str, Any]) -> str:
    counts = result.get("counts", {})
    lines = [
        "# Okta Group Cleanup Analysis Summary",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Mode: {result.get('mode')}",
        f"Org URL: {result.get('orgUrl', '')}",
        "",
        "## Counts",
        "",
        f"- Total groups analyzed: {result.get('totalGroupsAnalyzed', 0)}",
        f"- Cleanup/review candidates: {result.get('candidateCount', 0)}",
        f"- Empty groups: {counts.get('emptyGroups', 0)}",
        f"- Unused groups: {counts.get('unusedGroups', 0)}",
        f"- Duplicate-name groups: {counts.get('duplicateGroups', 0)}",
        f"- Stale groups: {counts.get('staleGroups', 0)}",
        f"- Ownerless groups: {counts.get('ownerlessGroups', 0)}",
        f"- Protected groups: {counts.get('protectedGroups', 0)}",
        "",
        "## Evidence",
        "",
        f"- Evidence fetched: {result.get('evidence', {})}",
        "",
        "## Review guidance",
        "",
        "Do not delete groups based only on this report. Review candidates with group owners, app owners, and IAM administrators before taking action.",
        "",
        "Prioritize groups that are simultaneously empty, unused, ownerless, and stale. Treat protected groups as review-only even if they appear unused.",
        "",
        "Empty and unused findings are now based on live API evidence only. File-mode inference has been removed to avoid stale CSV-based conclusions.",
        "",
        "## Main evidence files",
        "",
        "```text",
        "group_cleanup_candidates.csv",
        "empty_groups.csv",
        "unused_groups.csv",
        "duplicate_groups.csv",
        "stale_groups.csv",
        "ownerless_groups.csv",
        "protected_groups.csv",
        "group_cleanup_result.json",
        "```",
    ]
    return "\n".join(lines) + "\n"


def render_execution_report(result: dict[str, Any], dry_run: bool) -> str:
    lines = [
        "# Execution Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Mode: {'dry-run' if dry_run else 'analyze'}",
        f"Org URL: {result.get('orgUrl', '')}",
        "",
    ]
    if dry_run:
        lines.extend([
            "## Planned actions",
            "",
        ])
        for action in result.get("plannedActions", []):
            lines.append(f"- {action}")
        lines.append("")
    else:
        counts = result.get("counts", {})
        lines.extend([
            "## Summary",
            "",
            f"- Total groups analyzed: {result.get('totalGroupsAnalyzed', 0)}",
            f"- Candidates: {result.get('candidateCount', 0)}",
            f"- Empty groups: {counts.get('emptyGroups', 0)}",
            f"- Unused groups: {counts.get('unusedGroups', 0)}",
            f"- Duplicate groups: {counts.get('duplicateGroups', 0)}",
            f"- Stale groups: {counts.get('staleGroups', 0)}",
            f"- Ownerless groups: {counts.get('ownerlessGroups', 0)}",
            f"- Protected groups: {counts.get('protectedGroups', 0)}",
            f"- Okta API requests: {result.get('requestCount', 0)}",
            "",
            "## Evidence",
            "",
            f"- Evidence fetched: {result.get('evidence', {})}",
            "",
        ])
        warnings = result.get("evidenceWarnings", [])
        if warnings:
            lines.extend(["## Evidence warnings", ""])
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")
        lines.extend([
        ])
    return "\n".join(lines) + "\n"
