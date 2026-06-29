from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .config import PlannerConfig
from .io_utils import read_json, utc_timestamp
from .normalizers import (
    RESOURCE_FILES,
    display_name,
    is_high_risk,
    material_fingerprint,
    natural_key,
    normalize_resource,
    source_id,
)


@dataclass
class PlannerIssue:
    code: str
    severity: str
    resource: str
    message: str
    file: str | None = None


@dataclass
class MappingRow:
    resource: str
    status: str
    source_id: str = ""
    target_id: str = ""
    source_key: str = ""
    target_key: str = ""
    source_name: str = ""
    target_name: str = ""
    confidence: str = ""
    reason: str = ""
    recommended_action: str = ""


@dataclass
class ConflictRow:
    resource: str
    conflict_type: str
    source_id: str = ""
    target_id: str = ""
    natural_key: str = ""
    source_name: str = ""
    target_name: str = ""
    reason: str = ""
    recommended_action: str = ""


@dataclass
class ManualReviewRow:
    resource: str
    item_id: str = ""
    item_key: str = ""
    item_name: str = ""
    reason: str = ""
    recommended_action: str = ""


@dataclass
class ResourcePlan:
    resource: str
    source_count: int = 0
    target_count: int = 0
    matched_count: int = 0
    create_count: int = 0
    difference_count: int = 0
    target_only_count: int = 0
    manual_review_count: int = 0
    duplicate_source_keys: list[str] = field(default_factory=list)
    duplicate_target_keys: list[str] = field(default_factory=list)
    created_candidates: list[dict[str, Any]] = field(default_factory=list)
    matched: list[dict[str, Any]] = field(default_factory=list)
    differences: list[dict[str, Any]] = field(default_factory=list)
    target_only: list[dict[str, Any]] = field(default_factory=list)
    manual_review: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class MigrationPlan:
    plan_id: str
    generated_at: str
    source_backup_dir: str
    target_backup_dir: str
    included_resources: list[str]
    overall_status: str
    summary: dict[str, int]
    resource_plans: dict[str, dict[str, Any]]
    issues: list[dict[str, Any]]
    object_mappings: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    manual_review_items: list[dict[str, Any]]
    cutover_readiness: dict[str, Any]


class PlannerError(RuntimeError):
    pass


class MigrationPlanner:
    def __init__(self, config: PlannerConfig) -> None:
        self.config = config
        self.issues: list[PlannerIssue] = []
        self.object_mappings: list[MappingRow] = []
        self.conflicts: list[ConflictRow] = []
        self.manual_review_items: list[ManualReviewRow] = []

    def build_plan(self) -> MigrationPlan:
        self._validate_dirs()
        resource_plans: dict[str, ResourcePlan] = {}

        for resource in self.config.include:
            resource_plans[resource] = self._plan_resource(resource)

        summary = self._build_summary(resource_plans)
        readiness = self._build_cutover_readiness(summary)
        overall_status = readiness["overallStatus"]

        return MigrationPlan(
            plan_id=f"okta-migration-plan-{utc_timestamp()}",
            generated_at=utc_timestamp(),
            source_backup_dir=str(self.config.source_backup_dir),
            target_backup_dir=str(self.config.target_backup_dir),
            included_resources=self.config.include,
            overall_status=overall_status,
            summary=summary,
            resource_plans={key: asdict(value) for key, value in resource_plans.items()},
            issues=[asdict(issue) for issue in self.issues],
            object_mappings=[asdict(row) for row in self.object_mappings],
            conflicts=[asdict(row) for row in self.conflicts],
            manual_review_items=[asdict(row) for row in self.manual_review_items],
            cutover_readiness=readiness,
        )

    def _validate_dirs(self) -> None:
        if not self.config.source_backup_dir.exists() or not self.config.source_backup_dir.is_dir():
            raise PlannerError(f"Source backup directory not found: {self.config.source_backup_dir}")
        if not self.config.target_backup_dir.exists() or not self.config.target_backup_dir.is_dir():
            raise PlannerError(f"Target backup directory not found: {self.config.target_backup_dir}")

    def _load_resource(self, backup_dir: Path, resource: str) -> tuple[list[dict[str, Any]], PlannerIssue | None]:
        filename = RESOURCE_FILES.get(resource, f"{resource}.json")
        path = backup_dir / filename
        if not path.exists():
            return [], PlannerIssue(
                code="RESOURCE_FILE_MISSING",
                severity="WARN",
                resource=resource,
                file=filename,
                message=f"Resource file missing: {filename}",
            )
        try:
            data = read_json(path)
        except Exception as exc:  # noqa: BLE001 - include parser/runtime failure in evidence
            return [], PlannerIssue(
                code="RESOURCE_JSON_INVALID",
                severity="ERROR",
                resource=resource,
                file=filename,
                message=f"Could not parse {filename}: {exc}",
            )
        try:
            return normalize_resource(resource, data), None
        except Exception as exc:  # noqa: BLE001
            return [], PlannerIssue(
                code="RESOURCE_NORMALIZATION_FAILED",
                severity="ERROR",
                resource=resource,
                file=filename,
                message=f"Could not normalize {filename}: {exc}",
            )

    def _plan_resource(self, resource: str) -> ResourcePlan:
        plan = ResourcePlan(resource=resource)
        source_items, source_issue = self._load_resource(self.config.source_backup_dir, resource)
        target_items, target_issue = self._load_resource(self.config.target_backup_dir, resource)
        if source_issue:
            self.issues.append(source_issue)
        if target_issue:
            self.issues.append(target_issue)

        plan.source_count = len(source_items)
        plan.target_count = len(target_items)

        source_index, source_duplicates, source_unkeyed = self._index_items(resource, source_items, "source")
        target_index, target_duplicates, target_unkeyed = self._index_items(resource, target_items, "target")
        plan.duplicate_source_keys = sorted(source_duplicates)
        plan.duplicate_target_keys = sorted(target_duplicates)

        for key in plan.duplicate_source_keys:
            self.conflicts.append(ConflictRow(
                resource=resource,
                conflict_type="DUPLICATE_SOURCE_NATURAL_KEY",
                natural_key=key,
                reason="Multiple source objects use the same natural key, so the migration mapping is ambiguous.",
                recommended_action="Rename, merge, or manually map the duplicate source objects before migration.",
            ))
        for key in plan.duplicate_target_keys:
            self.conflicts.append(ConflictRow(
                resource=resource,
                conflict_type="DUPLICATE_TARGET_NATURAL_KEY",
                natural_key=key,
                reason="Multiple target objects use the same natural key, so the target match is ambiguous.",
                recommended_action="Resolve duplicate target objects before migration or explicitly map the desired target object.",
            ))
        for item in source_unkeyed:
            self.manual_review_items.append(ManualReviewRow(
                resource=resource,
                item_id=source_id(item),
                item_key="",
                item_name=display_name(resource, item),
                reason="Source object does not have a usable natural key for automated matching.",
                recommended_action="Review and map this object manually.",
            ))
            plan.manual_review.append({"id": source_id(item), "name": display_name(resource, item), "reason": "missing natural key"})
        for item in target_unkeyed:
            self.issues.append(PlannerIssue(
                code="TARGET_OBJECT_MISSING_NATURAL_KEY",
                severity="WARN",
                resource=resource,
                message=f"Target object does not have a usable natural key: {display_name(resource, item)}",
                file=RESOURCE_FILES.get(resource),
            ))

        for key, source_item in source_index.items():
            target_item = target_index.get(key)
            if target_item is None:
                if is_high_risk(resource) and self.config.treat_missing_high_risk_as_blocker:
                    reason = "High-risk object missing in target. Do not auto-create from backup without manual review."
                    plan.manual_review.append({"id": source_id(source_item), "key": key, "name": display_name(resource, source_item), "reason": reason})
                    self.manual_review_items.append(ManualReviewRow(
                        resource=resource,
                        item_id=source_id(source_item),
                        item_key=key,
                        item_name=display_name(resource, source_item),
                        reason=reason,
                        recommended_action="Review dependencies, secrets, ordering, and production impact before recreating this object.",
                    ))
                    self.object_mappings.append(MappingRow(
                        resource=resource,
                        status="manual_review_missing_high_risk",
                        source_id=source_id(source_item),
                        source_key=key,
                        source_name=display_name(resource, source_item),
                        confidence="medium",
                        reason=reason,
                        recommended_action="Manual review required before migration.",
                    ))
                else:
                    plan.created_candidates.append({
                        "sourceId": source_id(source_item),
                        "naturalKey": key,
                        "name": display_name(resource, source_item),
                        "recommendedAction": "create_in_target_or_restore_selectively",
                    })
                    self.object_mappings.append(MappingRow(
                        resource=resource,
                        status="missing_in_target",
                        source_id=source_id(source_item),
                        source_key=key,
                        source_name=display_name(resource, source_item),
                        confidence="high",
                        reason="No target object matched this source object by natural key.",
                        recommended_action="Create in target or restore selectively after review.",
                    ))
                continue

            src_fp = material_fingerprint(source_item)
            tgt_fp = material_fingerprint(target_item)
            if self.config.compare_material_differences and src_fp != tgt_fp:
                plan.differences.append({
                    "sourceId": source_id(source_item),
                    "targetId": source_id(target_item),
                    "naturalKey": key,
                    "name": display_name(resource, source_item),
                    "recommendedAction": "review_configuration_difference",
                })
                self.conflicts.append(ConflictRow(
                    resource=resource,
                    conflict_type="MATCHED_WITH_DIFFERENCES",
                    source_id=source_id(source_item),
                    target_id=source_id(target_item),
                    natural_key=key,
                    source_name=display_name(resource, source_item),
                    target_name=display_name(resource, target_item),
                    reason="Source and target objects match by natural key but have material configuration differences.",
                    recommended_action="Review the source and target JSON before deciding whether to update, skip, or manually merge.",
                ))
                status = "matched_with_differences"
                reason = "Natural key matched but material configuration differs."
                action = "Review and decide whether target should be updated."
            else:
                plan.matched.append({
                    "sourceId": source_id(source_item),
                    "targetId": source_id(target_item),
                    "naturalKey": key,
                    "name": display_name(resource, source_item),
                })
                status = "matched"
                reason = "Source and target objects matched by natural key."
                action = "No create action needed."

            self.object_mappings.append(MappingRow(
                resource=resource,
                status=status,
                source_id=source_id(source_item),
                target_id=source_id(target_item),
                source_key=key,
                target_key=key,
                source_name=display_name(resource, source_item),
                target_name=display_name(resource, target_item),
                confidence="high",
                reason=reason,
                recommended_action=action,
            ))

        for key, target_item in target_index.items():
            if key not in source_index:
                plan.target_only.append({
                    "targetId": source_id(target_item),
                    "naturalKey": key,
                    "name": display_name(resource, target_item),
                    "recommendedAction": "review_target_only_object",
                })

        plan.matched_count = len(plan.matched)
        plan.create_count = len(plan.created_candidates)
        plan.difference_count = len(plan.differences)
        plan.target_only_count = len(plan.target_only)
        plan.manual_review_count = len(plan.manual_review)
        return plan

    def _index_items(
        self,
        resource: str,
        items: list[dict[str, Any]],
        side: str,
    ) -> tuple[dict[str, dict[str, Any]], set[str], list[dict[str, Any]]]:
        index: dict[str, dict[str, Any]] = {}
        duplicates: set[str] = set()
        unkeyed: list[dict[str, Any]] = []
        for item in items:
            key = natural_key(resource, item)
            if not key:
                unkeyed.append(item)
                continue
            if key in index:
                duplicates.add(key)
                # Keep the first object in the index so downstream output is stable.
                continue
            index[key] = item
        return index, duplicates, unkeyed

    def _build_summary(self, resource_plans: dict[str, ResourcePlan]) -> dict[str, int]:
        return {
            "resourcesAnalyzed": len(resource_plans),
            "sourceObjects": sum(plan.source_count for plan in resource_plans.values()),
            "targetObjects": sum(plan.target_count for plan in resource_plans.values()),
            "matchedObjects": sum(plan.matched_count for plan in resource_plans.values()),
            "createCandidates": sum(plan.create_count for plan in resource_plans.values()),
            "matchedWithDifferences": sum(plan.difference_count for plan in resource_plans.values()),
            "targetOnlyObjects": sum(plan.target_only_count for plan in resource_plans.values()),
            "manualReviewItems": sum(plan.manual_review_count for plan in resource_plans.values()) + len(self.manual_review_items),
            "conflicts": len(self.conflicts),
            "issues": len(self.issues),
        }

    def _build_cutover_readiness(self, summary: dict[str, int]) -> dict[str, Any]:
        blockers: list[str] = []
        warnings: list[str] = []

        error_issues = [issue for issue in self.issues if issue.severity == "ERROR"]
        if error_issues:
            blockers.append(f"{len(error_issues)} resource file error(s) must be resolved.")
        if summary["manualReviewItems"]:
            blockers.append(f"{summary['manualReviewItems']} item(s) require manual review before migration/cutover.")
        if summary["conflicts"]:
            blockers.append(f"{summary['conflicts']} conflict(s) require review.")
        if summary["matchedWithDifferences"]:
            warnings.append(f"{summary['matchedWithDifferences']} matched object(s) have material differences.")
        if summary["createCandidates"]:
            warnings.append(f"{summary['createCandidates']} object(s) are missing in target and are candidates for creation/restore.")
        warn_issues = [issue for issue in self.issues if issue.severity == "WARN"]
        if warn_issues:
            warnings.append(f"{len(warn_issues)} warning issue(s) were recorded during planning.")

        if blockers:
            status = "NOT_READY"
        elif warnings and self.config.strict_mode:
            status = "READY_WITH_WARNINGS_BLOCKED_BY_STRICT_MODE"
        elif warnings:
            status = "READY_WITH_WARNINGS"
        else:
            status = "READY"

        return {
            "overallStatus": status,
            "blockers": blockers,
            "warnings": warnings,
            "recommendedNextSteps": self._recommended_next_steps(blockers, warnings),
        }

    def _recommended_next_steps(self, blockers: list[str], warnings: list[str]) -> list[str]:
        steps = [
            "Review migration_plan.json and cutover_readiness_report.md.",
            "Review object_mapping.csv for source-to-target object mapping decisions.",
        ]
        if blockers:
            steps.append("Resolve blockers before running restore, app cloning, Terraform import, or cutover tasks.")
        if warnings:
            steps.append("Review warnings and decide which missing or different objects should be created, skipped, or manually merged.")
        steps.append("Run okta-backup-validator against both source and target backups before using this plan for execution.")
        return steps
