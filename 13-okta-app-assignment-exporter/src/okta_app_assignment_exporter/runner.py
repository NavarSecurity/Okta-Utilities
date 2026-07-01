from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .client import OktaApiError, OktaClient
from .config import RuntimeConfig, ConfigError
from .exporter import group_assignment_row, select_apps, summary_row, user_assignment_row
from .reporting import utc_timestamp, write_csv, write_execution_report, write_json, write_markdown_summary


def _selection_summary(cfg: RuntimeConfig) -> dict[str, Any]:
    selection = cfg.app_selection
    return {
        "mode": selection.mode,
        "appIds": selection.app_ids,
        "appLabels": selection.app_labels,
        "statuses": selection.statuses,
        "signOnModes": selection.sign_on_modes,
        "excludeAppIds": selection.exclude_app_ids,
        "excludeAppLabels": selection.exclude_app_labels,
    }


def _options_summary(cfg: RuntimeConfig) -> dict[str, Any]:
    opts = cfg.export_options
    return {
        "includeUsers": opts.include_users,
        "includeGroups": opts.include_groups,
        "includeUserProfile": opts.include_user_profile,
        "includeGroupProfile": opts.include_group_profile,
        "includeRawAssignments": opts.include_raw_assignments,
        "maxApps": opts.max_apps,
        "failFast": opts.fail_fast,
    }


def _api_error(error: OktaApiError, resource: str) -> dict[str, Any]:
    return {
        "resource": resource,
        "type": "OktaApiError",
        "statusCode": error.status_code,
        "message": error.message,
        "url": error.url,
        "errorBody": error.body,
    }


def _load_selected_apps(client: OktaClient, cfg: RuntimeConfig) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]]]:
    selection = cfg.app_selection
    warnings: list[str] = []
    errors: list[dict[str, Any]] = []

    if selection.mode == "ids":
        fetched: list[dict[str, Any]] = []
        for app_id in selection.app_ids:
            try:
                fetched.append(client.get_app(app_id))
            except OktaApiError as exc:
                errors.append(_api_error(exc, f"app:{app_id}"))
                if cfg.export_options.fail_fast:
                    raise
        selected, selection_warnings = select_apps(fetched, selection, cfg.export_options)
        warnings.extend(selection_warnings)
        return selected, warnings, errors

    all_apps = client.list_apps(limit=cfg.http.page_limit)
    selected, selection_warnings = select_apps(all_apps, selection, cfg.export_options)
    warnings.extend(selection_warnings)
    return selected, warnings, errors


def _status_from_errors(mode: str, errors: list[dict[str, Any]], selected_count: int) -> str:
    if mode == "dry-run":
        return "DRY_RUN_COMPLETE"
    if errors and selected_count == 0:
        return "ERROR"
    if errors:
        return "EXPORTED_WITH_ERRORS"
    return "EXPORTED"


def run(cfg: RuntimeConfig, export: bool = False) -> tuple[dict[str, Any], Path]:
    run_id = f"okta-app-assignment-exporter-{utc_timestamp()}"
    out_dir = cfg.output_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = "export" if export else "dry-run"
    result: dict[str, Any] = {
        "runId": run_id,
        "utility": "okta-app-assignment-exporter",
        "version": __version__,
        "mode": mode,
        "targetOrgUrl": cfg.target_org_url,
        "status": "PLANNED",
        "selection": _selection_summary(cfg),
        "exportOptions": _options_summary(cfg),
        "apps": [],
        "counts": {
            "selectedApps": 0,
            "exportedApps": 0,
            "userAssignments": 0,
            "groupAssignments": 0,
            "errors": 0,
        },
        "warnings": [],
        "errors": [],
        "requestSummary": {},
        "outputFiles": [],
    }

    assignment_data: dict[str, Any] = {
        "runId": run_id,
        "targetOrgUrl": cfg.target_org_url,
        "selection": _selection_summary(cfg),
        "apps": [],
    }
    user_rows: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    raw_assignments: dict[str, Any] = {"users": {}, "groups": {}}

    if not export:
        result["status"] = "DRY_RUN_COMPLETE"
        result["warnings"].append("Dry-run only validates configuration and writes the export plan. Use --export to perform read-only Okta API calls.")
    else:
        if not cfg.api_token:
            raise ConfigError("OKTA_API_TOKEN is required for --export")

        client = OktaClient(
            cfg.target_org_url,
            cfg.api_token,
            timeout_seconds=cfg.http.timeout_seconds,
            max_retries=cfg.http.max_retries,
            retry_base_seconds=cfg.http.retry_base_seconds,
        )
        try:
            selected_apps, selection_warnings, selection_errors = _load_selected_apps(client, cfg)
            result["warnings"].extend(selection_warnings)
            result["errors"].extend(selection_errors)
            result["counts"]["selectedApps"] = len(selected_apps)

            for app in selected_apps:
                app_id = str(app.get("id", ""))
                app_errors_before = len(result["errors"])
                users: list[dict[str, Any]] = []
                groups: list[dict[str, Any]] = []

                if cfg.export_options.include_users:
                    try:
                        users = client.list_app_users(app_id, limit=cfg.http.page_limit)
                        for assignment in users:
                            user_rows.append(user_assignment_row(app, assignment, cfg.export_options.include_user_profile))
                    except OktaApiError as exc:
                        result["errors"].append(_api_error(exc, f"app_users:{app_id}"))
                        if cfg.export_options.fail_fast:
                            raise

                if cfg.export_options.include_groups:
                    try:
                        groups = client.list_app_groups(app_id, limit=cfg.http.page_limit)
                        for assignment in groups:
                            group_rows.append(group_assignment_row(app, assignment, cfg.export_options.include_group_profile))
                    except OktaApiError as exc:
                        result["errors"].append(_api_error(exc, f"app_groups:{app_id}"))
                        if cfg.export_options.fail_fast:
                            raise

                app_error_count = len(result["errors"]) - app_errors_before
                app_summary = summary_row(app, len(users), len(groups), app_error_count)
                summary_rows.append(app_summary)
                result["apps"].append(app_summary)
                assignment_data["apps"].append({
                    "app": app_summary,
                    "users": [user_assignment_row(app, assignment, cfg.export_options.include_user_profile) for assignment in users],
                    "groups": [group_assignment_row(app, assignment, cfg.export_options.include_group_profile) for assignment in groups],
                })
                if cfg.export_options.include_raw_assignments:
                    raw_assignments["users"][app_id] = users
                    raw_assignments["groups"][app_id] = groups

            result["counts"]["exportedApps"] = len(summary_rows)
            result["counts"]["userAssignments"] = len(user_rows)
            result["counts"]["groupAssignments"] = len(group_rows)
        except OktaApiError as exc:
            result["errors"].append(_api_error(exc, "applications"))
        finally:
            result["counts"]["errors"] = len(result["errors"])
            result["status"] = _status_from_errors(mode, result["errors"], result["counts"].get("selectedApps", 0))
            result["requestSummary"] = {
                "totalRequests": client.summary.total_requests,
                "byStatus": client.summary.by_status,
                "totalElapsedSeconds": round(client.summary.total_elapsed_seconds, 3),
            }

    result["counts"]["errors"] = len(result["errors"])

    plan_path = out_dir / "app_assignment_export_plan.json"
    result_path = out_dir / "app_assignment_export_result.json"
    combined_path = out_dir / "app_assignments.json"
    summary_csv_path = out_dir / "assignment_summary.csv"
    users_csv_path = out_dir / "app_user_assignments.csv"
    groups_csv_path = out_dir / "app_group_assignments.csv"
    errors_csv_path = out_dir / "errors.csv"
    summary_md_path = out_dir / "assignment_summary.md"
    report_path = out_dir / "execution_report.md"

    plan = {
        "runId": run_id,
        "mode": mode,
        "targetOrgUrl": cfg.target_org_url,
        "selection": _selection_summary(cfg),
        "exportOptions": _options_summary(cfg),
        "note": "Dry-run writes this plan only. --export performs read-only Okta API calls and writes assignment data.",
    }
    write_json(plan_path, plan)
    write_json(combined_path, assignment_data)
    write_csv(summary_csv_path, summary_rows)
    write_csv(users_csv_path, user_rows)
    write_csv(groups_csv_path, group_rows)
    write_csv(errors_csv_path, result["errors"])
    if cfg.export_options.include_raw_assignments:
        write_json(out_dir / "raw_assignments.json", raw_assignments)

    result["outputFiles"] = [
        plan_path.name,
        result_path.name,
        combined_path.name,
        summary_csv_path.name,
        users_csv_path.name,
        groups_csv_path.name,
        errors_csv_path.name,
        summary_md_path.name,
        report_path.name,
    ]
    if cfg.export_options.include_raw_assignments:
        result["outputFiles"].append("raw_assignments.json")

    write_json(result_path, result)
    write_markdown_summary(summary_md_path, result)
    write_execution_report(report_path, result)
    return result, out_dir
