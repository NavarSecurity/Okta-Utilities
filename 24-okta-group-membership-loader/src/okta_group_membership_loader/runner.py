from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import LoaderConfig
from .inputs import read_membership_requests
from .models import FailedRecord, MembershipRequest, PlannedChange, SkippedRecord, VALID_ACTIONS
from .okta_client import OktaClient, OktaApiError
from .reports import write_reports


class RunnerError(RuntimeError):
    pass


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _truthy(value: str, approved_values: list[str]) -> bool:
    return str(value or "").strip().lower() in {str(v).lower() for v in approved_values}


def _protected_login(login: str, patterns: list[str]) -> bool:
    lower = (login or "").lower()
    return any(pattern.lower() in lower for pattern in patterns if pattern)


def _skip(row: MembershipRequest, skipped: list[SkippedRecord], reason: str) -> None:
    skipped.append(SkippedRecord(row.row_number, row.action, row.group_lookup_value, row.user_lookup_value, reason))


def validate_request(row: MembershipRequest, cfg: LoaderConfig, skipped: list[SkippedRecord]) -> bool:
    action = row.normalized_action()
    safety = cfg.safety
    if action not in VALID_ACTIONS:
        _skip(row, skipped, f"Invalid action '{row.action}'. Expected add, remove, or replace.")
        return False
    if action == "remove" and not safety.get("allowRemove", False):
        _skip(row, skipped, "Remove action is blocked by safety.allowRemove=false.")
        return False
    if action == "replace" and not safety.get("allowReplace", False):
        _skip(row, skipped, "Replace action is blocked by safety.allowReplace=false.")
        return False
    if safety.get("requireApproved", True) and not _truthy(row.approved, safety.get("approvedValues", ["true", "yes", "y", "approved"])):
        _skip(row, skipped, "Row was not approved for group membership action.")
        return False
    if safety.get("requireReason", True) and not row.reason:
        _skip(row, skipped, "Row does not have a required reason.")
        return False
    if not row.group_id and not row.group_name:
        _skip(row, skipped, "Missing groupId or groupName.")
        return False
    if not row.user_id and not row.login and not row.email:
        _skip(row, skipped, "Missing userId, login, or email.")
        return False
    if not row.group_id and not safety.get("allowGroupNameLookup", True):
        _skip(row, skipped, "groupName lookup is disabled; provide groupId.")
        return False
    if not row.user_id and not safety.get("allowUserLoginLookup", True):
        _skip(row, skipped, "User login/email lookup is disabled; provide userId.")
        return False
    if safety.get("blockAdminUsers", True) and _protected_login(row.login or row.email, safety.get("protectedLoginPatterns", [])):
        _skip(row, skipped, "User login/email matched a protected account pattern.")
        return False
    return True


def _resolve_group(row: MembershipRequest, client: OktaClient | None) -> tuple[str, str]:
    if row.group_id:
        return row.group_id, row.group_name
    if client is None:
        return "", row.group_name
    group = client.find_group_by_name(row.group_name)
    if not group:
        raise OktaApiError(f"Group not found by name: {row.group_name}")
    return group.get("id", ""), group.get("profile", {}).get("name", row.group_name)


def _resolve_user(row: MembershipRequest, client: OktaClient | None) -> tuple[str, str, str]:
    if row.user_id:
        return row.user_id, row.login, row.email
    lookup = row.login or row.email
    if client is None:
        return "", row.login, row.email
    user = client.get_user(lookup)
    if not user:
        raise OktaApiError(f"User not found by login/email: {lookup}")
    profile = user.get("profile", {})
    return user.get("id", ""), profile.get("login", row.login), profile.get("email", row.email)


def _membership_set(client: OktaClient | None, group_id: str) -> set[str] | None:
    if client is None or not group_id:
        return None
    return {u.get("id", "") for u in client.get_group_users(group_id) if u.get("id")}


def _planned(row: MembershipRequest, action: str, group_id: str, group_name: str, user_id: str, login: str, email: str, message: str = "") -> PlannedChange:
    if action == "add":
        rb_method = "DELETE"
        rb_endpoint = f"/api/v1/groups/{group_id}/users/{user_id}"
    elif action == "remove":
        rb_method = "PUT"
        rb_endpoint = f"/api/v1/groups/{group_id}/users/{user_id}"
    else:
        rb_method = "REVIEW"
        rb_endpoint = "See rollback_plan.json replace actions"
    return PlannedChange(row.row_number, action, group_id, group_name, user_id, login, email, row.reason, "planned", message, rb_method, rb_endpoint)


def build_plan(cfg: LoaderConfig, client: OktaClient | None = None) -> tuple[list[PlannedChange], list[SkippedRecord], list[FailedRecord], dict[str, Any]]:
    rows = read_membership_requests(cfg)
    skipped: list[SkippedRecord] = []
    failed: list[FailedRecord] = []
    valid_rows = [row for row in rows if validate_request(row, cfg, skipped)]

    max_changes = int(cfg.safety.get("maxChangesPerRun", 250))
    if len(valid_rows) > max_changes:
        raise RunnerError(f"Planned row count {len(valid_rows)} exceeds maxChangesPerRun {max_changes}")

    planned: list[PlannedChange] = []
    group_membership_cache: dict[str, set[str] | None] = {}

    replace_rows_by_group: dict[str, list[tuple[MembershipRequest, str, str, str, str, str]]] = defaultdict(list)

    for row in valid_rows:
        try:
            group_id, group_name = _resolve_group(row, client)
            user_id, login, email = _resolve_user(row, client)
            action = row.normalized_action()
            if client is not None and group_id and group_id not in group_membership_cache:
                group_membership_cache[group_id] = _membership_set(client, group_id)
            current = group_membership_cache.get(group_id)

            if action == "add":
                if current is not None and user_id in current and cfg.safety.get("skipExistingAdditions", True):
                    _skip(row, skipped, "User is already a member of the group.")
                    continue
                planned.append(_planned(row, action, group_id, group_name, user_id, login, email))
            elif action == "remove":
                if current is not None and user_id not in current and cfg.safety.get("skipMissingRemovals", True):
                    _skip(row, skipped, "User is not currently a member of the group.")
                    continue
                planned.append(_planned(row, action, group_id, group_name, user_id, login, email))
            elif action == "replace":
                replace_rows_by_group[group_id].append((row, group_id, group_name, user_id, login, email))
        except Exception as e:
            failed.append(FailedRecord(row.row_number, row.action, row.group_lookup_value, row.user_lookup_value, str(e)))
            if not cfg.settings.get("continueOnError", False):
                break

    for group_id, entries in replace_rows_by_group.items():
        desired = {user_id for _, _, _, user_id, _, _ in entries if user_id}
        current = group_membership_cache.get(group_id)
        if current is None:
            # Without current state, replace cannot be safely expanded.
            for row, _, group_name, user_id, login, email in entries:
                planned.append(_planned(row, "replace", group_id, group_name, user_id, login, email, "Desired replacement member; current members not resolved in this run."))
            continue
        group_name = entries[0][2]
        template_row = entries[0][0]
        # Add desired missing members.
        for row, _, _, user_id, login, email in entries:
            if user_id not in current:
                planned.append(_planned(row, "add", group_id, group_name, user_id, login, email, "Replace operation: add missing desired member."))
        # Remove current members not present in desired.
        for existing_user_id in sorted(current - desired):
            synthetic = MembershipRequest(template_row.row_number, "remove", group_id=group_id, group_name=group_name, user_id=existing_user_id, approved=template_row.approved, reason=template_row.reason)
            planned.append(_planned(synthetic, "remove", group_id, group_name, existing_user_id, "", "", "Replace operation: remove member not present in desired set."))

    summary = {
        "inputRows": len(rows),
        "validRows": len(valid_rows),
        "plannedChanges": len(planned),
        "skippedRecords": len(skipped),
        "failedRecords": len(failed),
    }
    return planned, skipped, failed, summary


def apply_plan(cfg: LoaderConfig, planned: list[PlannedChange], client: OktaClient) -> tuple[list[PlannedChange], list[FailedRecord]]:
    applied: list[PlannedChange] = []
    failed: list[FailedRecord] = []
    for change in planned:
        try:
            if change.action == "add":
                client.add_user_to_group(change.group_id, change.user_id)
            elif change.action == "remove":
                client.remove_user_from_group(change.group_id, change.user_id)
            else:
                raise RunnerError("Unexpanded replace action cannot be applied")
            change.status = "applied"
            applied.append(change)
        except Exception as e:
            change.status = "failed"
            change.message = str(e)
            failed.append(FailedRecord(change.row_number, change.action, change.group_id, change.user_id, str(e)))
            if not cfg.settings.get("continueOnError", False):
                break
    return applied, failed


def run_loader(cfg: LoaderConfig, mode: str, output_dir: str = "output") -> Path:
    run_dir = Path(output_dir) / f"okta-group-membership-loader-{_utc_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    should_init_client = mode == "apply" or bool(cfg.settings.get("verifyExistingStateInDryRun", True))
    client = None
    if should_init_client:
        client = OktaClient(
            cfg.target_org_url,
            timeout=int(cfg.settings.get("requestTimeoutSeconds", 30)),
            max_retries=int(cfg.settings.get("maxRetries", 3)),
            retry_backoff=int(cfg.settings.get("retryBackoffSeconds", 2)),
        )

    planned, skipped, failed, summary = build_plan(cfg, client)
    applied: list[PlannedChange] = []
    apply_failed: list[FailedRecord] = []

    if mode == "apply" and planned:
        applied, apply_failed = apply_plan(cfg, planned, client)  # type: ignore[arg-type]
        failed.extend(apply_failed)

    result = {
        "utility": "okta-group-membership-loader",
        "mode": mode,
        "targetOrgUrl": cfg.target_org_url,
        "summary": {
            **summary,
            "appliedChanges": len(applied),
            "totalFailures": len(failed),
        },
        "plannedChanges": [asdict(p) for p in planned],
        "appliedChanges": [asdict(a) for a in applied],
        "skippedRecords": [asdict(s) for s in skipped],
        "failedRecords": [asdict(f) for f in failed],
    }
    write_reports(run_dir, result)
    return run_dir
