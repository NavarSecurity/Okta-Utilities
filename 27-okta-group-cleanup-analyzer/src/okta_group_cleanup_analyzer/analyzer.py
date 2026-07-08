from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any

from .models import GroupRecord, parse_dt
from .okta_api import OktaApiError, OktaClient


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def get_first(row: dict[str, Any], keys: list[str], default: str = "") -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def flatten_profile(row: dict[str, Any]) -> dict[str, Any]:
    profile = row.get("profile") if isinstance(row.get("profile"), dict) else {}
    flat = dict(row)
    for k, v in profile.items():
        flat[f"profile.{k}"] = v
    return flat


def parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def split_multi(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if not text:
        return []
    for sep in [";", "|", ","]:
        if sep in text:
            return [part.strip() for part in text.split(sep) if part.strip()]
    return [text]


def group_from_row(row: dict[str, Any], owner_fields: list[str]) -> GroupRecord:
    flat = flatten_profile(row)
    profile = row.get("profile") if isinstance(row.get("profile"), dict) else {}
    gid = str(get_first(flat, ["id", "groupId", "group_id", "targetGroupId", "target_group_id"])).strip()
    name = str(get_first(flat, ["name", "groupName", "group_name", "targetGroupName", "target_group_name", "profile.name"])).strip()
    gtype = str(get_first(flat, ["type", "groupType"])).strip()
    created = str(get_first(flat, ["created", "createdAt"])).strip()
    last_updated = str(get_first(flat, ["lastUpdated", "last_updated", "updated", "updatedAt"])).strip()
    description = str(get_first(flat, ["description", "profile.description"])).strip()
    owner = str(get_first(flat, owner_fields)).strip()
    member_count = parse_int(get_first(flat, ["memberCount", "membersCount", "userCount", "usersCount"], ""))
    app_assignment_count = parse_int(get_first(flat, ["appAssignmentCount", "appAssignmentsCount", "appLinkCount"], ""))
    rule_target_count = parse_int(get_first(flat, ["ruleTargetCount", "groupRuleTargetCount", "ruleCount"], ""))
    return GroupRecord(
        id=gid,
        name=name,
        type=gtype,
        created=created,
        last_updated=last_updated,
        description=description,
        owner=owner,
        profile=profile,
        raw=row,
        member_count=member_count,
        app_assignment_count=app_assignment_count,
        rule_target_count=rule_target_count,
    )


def extract_group_ids_from_rule(rule: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    actions = rule.get("actions") if isinstance(rule.get("actions"), dict) else {}
    assign = actions.get("assignUserToGroups") or actions.get("assignUserToGroup") or {}
    if isinstance(assign, dict):
        for key in ["groupIds", "group_ids", "groups"]:
            ids.extend(split_multi(assign.get(key)))
    for key in ["targetGroupIds", "target_group_ids", "groupIds", "groupId", "targetGroupId"]:
        ids.extend(split_multi(rule.get(key)))
    return [gid for gid in ids if gid]


def load_groups_from_api(config: dict[str, Any], owner_fields: list[str]) -> tuple[list[GroupRecord], int, list[str], dict[str, bool]]:
    settings = config.get("settings", {})
    continue_on_evidence_error = bool(settings.get("continueOnEvidenceFetchError", True))
    client = OktaClient(
        config["orgUrl"],
        config["apiToken"],
        timeout=int(settings.get("requestTimeoutSeconds", 30)),
        max_retries=int(settings.get("maxRetries", 3)),
    )
    warnings: list[str] = []
    evidence = {
        "groupsFetched": False,
        "memberCountsFetched": False,
        "appAssignmentCountsFetched": False,
        "ruleTargetCountsFetched": False,
    }

    raw_groups = client.list_groups()
    evidence["groupsFetched"] = True
    groups = [group_from_row(row, owner_fields) for row in raw_groups]
    group_by_id = {group.id: group for group in groups if group.id}
    group_by_name = {normalize_name(group.name): group for group in groups if group.name}

    if settings.get("fetchMemberCountsInApiMode", True):
        try:
            for group in groups:
                if group.id:
                    group.member_count = client.count_group_members(group.id)
            evidence["memberCountsFetched"] = True
        except OktaApiError as exc:
            warnings.append(f"Member count fetch failed: {exc}")
            if not continue_on_evidence_error:
                raise

    if settings.get("fetchAppAssignmentCountsInApiMode", True):
        try:
            counts: Counter[str] = Counter()
            for app in client.list_apps():
                app_id = str(app.get("id") or "").strip()
                if not app_id:
                    continue
                for assignment in client.list_app_group_assignments(app_id):
                    gid = str(get_first(assignment, ["id", "groupId", "group_id"])).strip()
                    if gid:
                        counts[gid] += 1
            for group in groups:
                group.app_assignment_count = counts.get(group.id, 0)
            evidence["appAssignmentCountsFetched"] = True
        except OktaApiError as exc:
            warnings.append(f"App group assignment count fetch failed: {exc}")
            if not continue_on_evidence_error:
                raise

    if settings.get("fetchRuleTargetCountsInApiMode", True):
        try:
            counts: Counter[str] = Counter()
            for rule in client.list_group_rules():
                for gid in extract_group_ids_from_rule(rule):
                    counts[gid] += 1
            for group in groups:
                group.rule_target_count = counts.get(group.id, 0)
            evidence["ruleTargetCountsFetched"] = True
        except OktaApiError as exc:
            warnings.append(f"Group rule target count fetch failed: {exc}")
            if not continue_on_evidence_error:
                raise

    for group in groups:
        if group.member_count is None:
            group.evidence_notes.append("member_count_not_fetched")
        if group.app_assignment_count is None:
            group.evidence_notes.append("app_assignment_count_not_fetched")
        if group.rule_target_count is None:
            group.evidence_notes.append("rule_target_count_not_fetched")

    return groups, client.request_count, warnings, evidence


def is_protected_group(group: GroupRecord, patterns: list[str]) -> bool:
    text = f"{group.name} {group.description}".lower()
    return any(pattern.lower() in text for pattern in patterns if pattern)


def analyze(config: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    analysis = config.get("analysis", {})
    settings = config.get("settings", {})
    owner_fields = analysis.get("ownerFields") or ["owner", "groupOwner", "profile.owner"]
    request_count = 0
    evidence_warnings: list[str] = []
    evidence = {
        "groupsFetched": False,
        "memberCountsFetched": False,
        "appAssignmentCountsFetched": False,
        "ruleTargetCountsFetched": False,
    }

    if dry_run:
        return build_dry_run_plan(config)

    groups, request_count, evidence_warnings, evidence = load_groups_from_api(config, owner_fields)

    if not settings.get("includeOktaBuiltInGroups", False):
        groups = [g for g in groups if (g.type or "").upper() not in {"BUILT_IN", "OKTA_BUILT_IN"}]

    name_counts = Counter(normalize_name(g.name) for g in groups if g.name)
    for group in groups:
        group.duplicate_count = name_counts.get(normalize_name(group.name), 0)

    stale_days = int(analysis.get("staleDays", 180))
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    protected_patterns = analysis.get("protectedGroupNamePatterns") or []

    can_evaluate_empty = bool(evidence.get("memberCountsFetched"))
    can_evaluate_unused = bool(
        evidence.get("memberCountsFetched")
        and evidence.get("appAssignmentCountsFetched")
        and evidence.get("ruleTargetCountsFetched")
    )

    if analysis.get("findEmptyGroups", True) and not can_evaluate_empty:
        evidence_warnings.append("Empty-group analysis skipped because current member counts were not fetched.")
    if analysis.get("findUnusedGroups", True) and not can_evaluate_unused:
        evidence_warnings.append("Unused-group analysis skipped because current member, app-assignment, and group-rule evidence was not fully fetched.")

    for group in groups:
        reasons: list[str] = []
        group.is_protected = is_protected_group(group, protected_patterns)
        if group.is_protected:
            reasons.append("PROTECTED_NAME_PATTERN")

        if analysis.get("findEmptyGroups", True) and can_evaluate_empty:
            if group.member_count == 0:
                reasons.append("EMPTY_GROUP")

        if analysis.get("findUnusedGroups", True) and can_evaluate_unused:
            if group.member_count == 0 and group.app_assignment_count == 0 and group.rule_target_count == 0:
                reasons.append("UNUSED_GROUP")

        if analysis.get("findDuplicateNames", True):
            if group.duplicate_count > 1:
                reasons.append("DUPLICATE_NAME")

        if analysis.get("findStaleGroups", True):
            dt = parse_dt(group.last_updated) or parse_dt(group.created)
            if dt and dt < cutoff:
                reasons.append("STALE_GROUP")

        if analysis.get("findOwnerlessGroups", True):
            if not group.owner:
                reasons.append("OWNERLESS_GROUP")

        group.reasons = reasons
        group.recommendation = recommend(group)

    candidates = [g for g in groups if g.reasons]
    return {
        "mode": "analyze",
        "analysisMode": "api",
        "orgUrl": config.get("orgUrl", ""),
        "requestCount": request_count,
        "evidence": evidence,
        "evidenceWarnings": evidence_warnings,
        "totalGroupsAnalyzed": len(groups),
        "candidateCount": len(candidates),
        "counts": {
            "emptyGroups": count_reason(candidates, "EMPTY_GROUP"),
            "unusedGroups": count_reason(candidates, "UNUSED_GROUP"),
            "duplicateGroups": count_reason(candidates, "DUPLICATE_NAME"),
            "staleGroups": count_reason(candidates, "STALE_GROUP"),
            "ownerlessGroups": count_reason(candidates, "OWNERLESS_GROUP"),
            "protectedGroups": count_reason(candidates, "PROTECTED_NAME_PATTERN"),
        },
        "groups": [g.to_output_row() for g in groups],
        "candidates": [g.to_output_row() for g in candidates],
        "emptyGroups": [g.to_output_row() for g in groups if "EMPTY_GROUP" in g.reasons],
        "unusedGroups": [g.to_output_row() for g in groups if "UNUSED_GROUP" in g.reasons],
        "duplicateGroups": [g.to_output_row() for g in groups if "DUPLICATE_NAME" in g.reasons],
        "staleGroups": [g.to_output_row() for g in groups if "STALE_GROUP" in g.reasons],
        "ownerlessGroups": [g.to_output_row() for g in groups if "OWNERLESS_GROUP" in g.reasons],
        "protectedGroups": [g.to_output_row() for g in groups if "PROTECTED_NAME_PATTERN" in g.reasons],
    }


def count_reason(groups: list[GroupRecord], reason: str) -> int:
    return sum(1 for group in groups if reason in group.reasons)


def recommend(group: GroupRecord) -> str:
    if group.is_protected:
        return "protected_review_only"
    reason_set = set(group.reasons)
    if {"EMPTY_GROUP", "UNUSED_GROUP", "OWNERLESS_GROUP"}.issubset(reason_set):
        return "cleanup_candidate_review_required"
    if "DUPLICATE_NAME" in reason_set:
        return "duplicate_review_required"
    if "STALE_GROUP" in reason_set:
        return "stale_review_required"
    if "EMPTY_GROUP" in reason_set or "UNUSED_GROUP" in reason_set:
        return "cleanup_candidate_review_required"
    return "review"


def build_dry_run_plan(config: dict[str, Any]) -> dict[str, Any]:
    settings = config.get("settings", {})
    return {
        "mode": "dry-run",
        "analysisMode": "api",
        "orgUrl": config.get("orgUrl", ""),
        "analysis": config.get("analysis", {}),
        "settings": {k: v for k, v in settings.items() if k != "apiToken"},
        "plannedActions": [
            "Read current Okta groups from the Okta API",
            "Fetch current group member counts when fetchMemberCountsInApiMode is enabled",
            "Fetch current group app-assignment counts when fetchAppAssignmentCountsInApiMode is enabled",
            "Fetch current group-rule target counts when fetchRuleTargetCountsInApiMode is enabled",
            "Identify empty groups only when current member count evidence is available",
            "Identify unused groups only when member, app-assignment, and rule-target evidence is available",
            "Identify duplicate group names",
            "Identify stale groups",
            "Identify ownerless groups",
            "Write cleanup analysis reports",
        ],
    }
