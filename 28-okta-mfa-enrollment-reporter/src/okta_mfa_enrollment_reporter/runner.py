from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AppConfig
from .okta_client import OktaApiError, OktaClient
from .redaction import maybe_redact
from .reporting import (
    build_factor_rows,
    build_factor_summary_rows,
    build_group_summary_rows,
    build_user_summary_rows,
    user_login,
    write_csv,
    write_execution_report,
    write_json,
)


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_output_dir(base: str = "output") -> Path:
    out = Path(base) / f"okta-mfa-enrollment-reporter-{timestamp()}"
    out.mkdir(parents=True, exist_ok=False)
    return out


def build_plan(cfg: AppConfig, mode: str) -> dict[str, Any]:
    input_cfg = cfg.input
    return {
        "mode": mode,
        "configPath": str(cfg.config_path),
        "orgUrl": cfg.org_url,
        "selection": {
            "userIds": input_cfg.user_ids,
            "userLogins": input_cfg.user_logins,
            "groupIds": input_cfg.group_ids,
            "groupNames": input_cfg.group_names,
            "statuses": input_cfg.statuses,
            "selectionMode": selection_mode(cfg),
        },
        "reporting": {
            "requiredFactorTypes": cfg.reporting.required_factor_types,
            "factorTypes": cfg.reporting.factor_types,
            "includeFactorProfile": cfg.reporting.include_factor_profile,
            "includeRawFactors": cfg.reporting.include_raw_factors,
        },
        "settings": {
            "pageLimit": cfg.settings.page_limit,
            "requestTimeoutSeconds": cfg.settings.request_timeout_seconds,
            "maxRetries": cfg.settings.max_retries,
            "redactSensitiveProfileValues": cfg.settings.redact_sensitive_profile_values,
        },
    }


def selection_mode(cfg: AppConfig) -> str:
    if cfg.input.user_ids or cfg.input.user_logins:
        return "specific_users"
    if cfg.input.group_ids or cfg.input.group_names:
        return "groups"
    return "all_users"


def run_dry_run(cfg: AppConfig) -> Path:
    out = create_output_dir()
    plan = build_plan(cfg, "dry-run")
    result = {
        "summary": {
            "plannedMode": "dry-run",
            "selectionMode": plan["selection"]["selectionMode"],
            "configuredUserIds": len(cfg.input.user_ids),
            "configuredUserLogins": len(cfg.input.user_logins),
            "configuredGroupIds": len(cfg.input.group_ids),
            "configuredGroupNames": len(cfg.input.group_names),
            "requiredFactorTypes": len(cfg.reporting.required_factor_types),
        },
        "warnings": dry_run_warnings(cfg),
        "errors": [],
    }
    write_json(out / "mfa_enrollment_plan.json", plan)
    write_json(out / "mfa_enrollment_result.json", result)
    write_execution_report(out / "execution_report.md", "Okta MFA Enrollment Reporter", "dry-run", result)
    return out


def dry_run_warnings(cfg: AppConfig) -> list[str]:
    warnings: list[str] = []
    if selection_mode(cfg) == "all_users":
        warnings.append("No user or group filters were provided. Report mode will inspect all users matching the status filter.")
    if not cfg.reporting.required_factor_types:
        warnings.append("No requiredFactorTypes were configured. Missing required factor reporting will be empty.")
    if cfg.reporting.include_raw_factors:
        warnings.append("includeRawFactors is enabled. Raw factor data will be written in redacted form when redaction is enabled.")
    return warnings


def run_report(cfg: AppConfig) -> Path:
    out = create_output_dir()
    plan = build_plan(cfg, "report")
    write_json(out / "mfa_enrollment_plan.json", plan)

    client = OktaClient(
        cfg.org_url,
        cfg.api_token,
        timeout=cfg.settings.request_timeout_seconds,
        max_retries=cfg.settings.max_retries,
        page_limit=cfg.settings.page_limit,
    )

    errors: list[str] = []
    warnings: list[str] = []

    users, group_context = collect_users(cfg, client, warnings, errors)
    users = filter_users_by_status(users, cfg.input.statuses)

    factor_map: dict[str, list[dict[str, Any]]] = {}
    raw_factor_records: list[dict[str, Any]] = []
    for user in users:
        user_id = user.get("id", "")
        if not user_id:
            continue
        try:
            factors = client.list_user_factors(user_id)
            factor_map[user_id] = factors
            if cfg.reporting.include_raw_factors:
                raw_factor_records.append({
                    "userId": user_id,
                    "login": user_login(user),
                    "factors": maybe_redact(factors, cfg.settings.redact_sensitive_profile_values),
                })
        except OktaApiError as exc:
            errors.append(f"Failed to fetch factors for user {user_id}: {exc}")
            factor_map[user_id] = []

    user_rows = build_user_summary_rows(users, factor_map, group_context, cfg.reporting.required_factor_types)
    factor_rows = build_factor_rows(users, factor_map, cfg)
    users_without_mfa = [row for row in user_rows if row.get("has_any_factor") != "true"]
    missing_required = [row for row in user_rows if row.get("missing_required_factor_types")]
    group_rows = build_group_summary_rows(user_rows)
    factor_summary_rows = build_factor_summary_rows(factor_rows)

    write_csv(out / "user_mfa_summary.csv", user_rows)
    write_csv(out / "factor_enrollments.csv", factor_rows)
    write_csv(out / "users_without_mfa.csv", users_without_mfa)
    write_csv(out / "missing_required_factors.csv", missing_required)
    write_csv(out / "group_mfa_summary.csv", group_rows)
    write_csv(out / "factor_type_summary.csv", factor_summary_rows)

    if cfg.reporting.include_raw_factors:
        write_json(out / "raw_factors_redacted.json", raw_factor_records)

    result = {
        "summary": {
            "usersAnalyzed": len(users),
            "factorEnrollmentsFound": len(factor_rows),
            "usersWithAnyFactor": sum(1 for row in user_rows if row.get("has_any_factor") == "true"),
            "usersWithActiveFactor": sum(1 for row in user_rows if row.get("has_active_factor") == "true"),
            "usersWithoutMfa": len(users_without_mfa),
            "usersMissingRequiredFactors": len(missing_required),
            "groupsIncluded": len(group_rows),
            "factorTypeSummaryRows": len(factor_summary_rows),
            "requestSummary": client.request_counts,
        },
        "warnings": warnings,
        "errors": errors,
    }
    write_json(out / "mfa_enrollment_result.json", result)
    write_execution_report(out / "execution_report.md", "Okta MFA Enrollment Reporter", "report", result)
    return out


def collect_users(
    cfg: AppConfig,
    client: OktaClient,
    warnings: list[str],
    errors: list[str],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, str]]]]:
    users_by_id: dict[str, dict[str, Any]] = {}
    group_context: dict[str, list[dict[str, str]]] = {}

    def add_user(user: dict[str, Any], group: dict[str, str] | None = None) -> None:
        user_id = user.get("id")
        if not user_id:
            return
        users_by_id[user_id] = user
        if group:
            group_context.setdefault(user_id, [])
            if group not in group_context[user_id]:
                group_context[user_id].append(group)

    if cfg.input.user_ids or cfg.input.user_logins:
        for user_id in cfg.input.user_ids:
            try:
                add_user(client.get_user(user_id))
            except OktaApiError as exc:
                errors.append(f"Failed to fetch user ID {user_id}: {exc}")
        for login in cfg.input.user_logins:
            try:
                add_user(client.get_user(login))
            except OktaApiError as exc:
                errors.append(f"Failed to fetch user login {login}: {exc}")
        return list(users_by_id.values()), group_context

    if cfg.input.group_ids or cfg.input.group_names:
        groups: list[dict[str, Any]] = []
        for group_id in cfg.input.group_ids:
            try:
                groups.append(client.get_group_by_id(group_id))
            except OktaApiError as exc:
                errors.append(f"Failed to fetch group ID {group_id}: {exc}")
        for group_name in cfg.input.group_names:
            try:
                group = client.find_group_by_name(group_name)
                if group:
                    groups.append(group)
                else:
                    warnings.append(f"Group name not found: {group_name}")
            except OktaApiError as exc:
                errors.append(f"Failed to resolve group name {group_name}: {exc}")
        for group in groups:
            group_id = group.get("id", "")
            group_name = (group.get("profile") or {}).get("name", "")
            try:
                for user in client.list_group_users(group_id):
                    add_user(user, {"id": group_id, "name": group_name})
            except OktaApiError as exc:
                errors.append(f"Failed to fetch users for group {group_id}: {exc}")
        return list(users_by_id.values()), group_context

    for user in client.list_users():
        add_user(user)
    return list(users_by_id.values()), group_context


def filter_users_by_status(users: list[dict[str, Any]], statuses: list[str]) -> list[dict[str, Any]]:
    if not statuses:
        return users
    allowed = {status.upper() for status in statuses}
    return [user for user in users if str(user.get("status", "")).upper() in allowed]
