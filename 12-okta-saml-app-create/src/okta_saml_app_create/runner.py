from __future__ import annotations

from pathlib import Path
from typing import Any

from .client import OktaClient, OktaApiError
from .config import RuntimeConfig, ConfigError
from .payload import build_saml_app_payload, validate_saml_app_config
from .reporting import utc_timestamp, write_json, write_mapping_csv, write_report


def _app_summary(cfg: RuntimeConfig) -> dict[str, Any]:
    return {
        "label": cfg.app.label,
        "ssoAcsUrl": cfg.app.sso_acs_url,
        "audience": cfg.app.audience,
        "groupAssignmentCount": len(cfg.app.assignments.group_ids),
        "userAssignmentCount": len(cfg.app.assignments.user_ids),
    }


def _existing_app(client: OktaClient, label: str, limit: int) -> dict[str, Any] | None:
    matches = client.list_apps_by_query(label, limit=limit)
    for app in matches:
        if app.get("label") == label:
            return app
    return None


def _api_error(error: OktaApiError, resource: str) -> dict[str, Any]:
    return {
        "resource": resource,
        "type": "OktaApiError",
        "statusCode": error.status_code,
        "message": error.message,
        "url": error.url,
        "errorBody": error.body,
    }


def run(cfg: RuntimeConfig, apply: bool = False) -> tuple[dict[str, Any], Path]:
    run_id = f"okta-saml-app-create-{utc_timestamp()}"
    out_dir = cfg.output_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    warnings = validate_saml_app_config(cfg.app)
    payload = build_saml_app_payload(cfg.app)

    mode = "apply" if apply else "dry-run"
    result: dict[str, Any] = {
        "runId": run_id,
        "utility": "okta-saml-app-create",
        "version": "0.1.2",
        "mode": mode,
        "targetOrgUrl": cfg.target_org_url,
        "status": "PLANNED",
        "app": _app_summary(cfg),
        "payload": payload,
        "duplicateCheck": None,
        "assignments": {
            "groups": [{"groupId": g, "action": "assign"} for g in cfg.app.assignments.group_ids],
            "users": [{"userId": u, "action": "assign"} for u in cfg.app.assignments.user_ids],
        },
        "counts": {
            "createdApps": 0,
            "skippedApps": 0,
            "groupAssignmentsAttempted": 0,
            "groupAssignmentsSucceeded": 0,
            "userAssignmentsAttempted": 0,
            "userAssignmentsSucceeded": 0,
        },
        "warnings": warnings,
        "errors": [],
        "requestSummary": {},
        "outputFiles": [],
    }

    rollback = {
        "runId": run_id,
        "mode": mode,
        "actions": [],
        "note": "Review before executing rollback. This utility does not automatically roll back changes.",
    }
    mappings: list[dict[str, Any]] = []

    if not cfg.target_api_token:
        if apply:
            raise ConfigError("OKTA_TARGET_API_TOKEN is required for --apply")
        result["warnings"].append("No OKTA_TARGET_API_TOKEN set; duplicate check skipped in dry-run")
        result["status"] = "DRY_RUN_COMPLETE"
    else:
        client = OktaClient(
            cfg.target_org_url,
            cfg.target_api_token,
            timeout_seconds=cfg.timeout_seconds,
            max_retries=cfg.max_retries,
            retry_base_seconds=cfg.retry_base_seconds,
        )
        try:
            existing = _existing_app(client, cfg.app.label, cfg.page_limit)
            result["duplicateCheck"] = {
                "checked": True,
                "existingAppFound": existing is not None,
                "existingAppId": existing.get("id") if existing else None,
                "existingAppLabel": existing.get("label") if existing else None,
            }
            if existing:
                if cfg.skip_existing:
                    result["status"] = "SKIPPED_EXISTING"
                    result["counts"]["skippedApps"] = 1
                    mappings.append({
                        "label": cfg.app.label,
                        "action": "skip_existing",
                        "targetAppId": existing.get("id"),
                        "targetAppUrl": existing.get("_links", {}).get("self", {}).get("href", ""),
                        "message": "App with same label already exists in target org",
                    })
                else:
                    result["status"] = "ERROR"
                    result["errors"].append({
                        "resource": "applications",
                        "type": "DuplicateAppLabel",
                        "message": f"App with label '{cfg.app.label}' already exists and skipExisting is false",
                    })
            elif apply:
                created = client.create_app(payload)
                app_id = created.get("id")
                result["status"] = "CREATED"
                result["counts"]["createdApps"] = 1
                mappings.append({
                    "label": cfg.app.label,
                    "action": "created",
                    "targetAppId": app_id,
                    "targetAppUrl": created.get("_links", {}).get("self", {}).get("href", ""),
                    "message": "App created",
                })
                rollback["actions"].append({
                    "action": "delete_app",
                    "appId": app_id,
                    "label": cfg.app.label,
                    "method": "DELETE",
                    "path": f"/api/v1/apps/{app_id}",
                })

                for group_id in cfg.app.assignments.group_ids:
                    result["counts"]["groupAssignmentsAttempted"] += 1
                    try:
                        client.assign_group(app_id, group_id)
                        result["counts"]["groupAssignmentsSucceeded"] += 1
                    except OktaApiError as exc:
                        result["errors"].append(_api_error(exc, f"group_assignment:{group_id}"))
                        if cfg.fail_fast:
                            raise

                for user_id in cfg.app.assignments.user_ids:
                    result["counts"]["userAssignmentsAttempted"] += 1
                    try:
                        client.assign_user(app_id, user_id)
                        result["counts"]["userAssignmentsSucceeded"] += 1
                    except OktaApiError as exc:
                        result["errors"].append(_api_error(exc, f"user_assignment:{user_id}"))
                        if cfg.fail_fast:
                            raise

                if result["errors"]:
                    result["status"] = "CREATED_WITH_ASSIGNMENT_ERRORS"
            else:
                result["status"] = "DRY_RUN_COMPLETE"
        except OktaApiError as exc:
            result["status"] = "ERROR"
            result["errors"].append(_api_error(exc, "applications"))
        finally:
            result["requestSummary"] = {
                "totalRequests": client.summary.total_requests,
                "byStatus": client.summary.by_status,
                "totalElapsedSeconds": round(client.summary.total_elapsed_seconds, 3),
            }

    if not mappings:
        mappings.append({
            "label": cfg.app.label,
            "action": "planned" if not apply else "not_created",
            "targetAppId": "",
            "targetAppUrl": "",
            "message": "Dry-run plan generated" if not apply else "No app created",
        })

    plan_path = out_dir / "saml_app_create_plan.json"
    result_path = out_dir / "saml_app_create_result.json"
    rollback_path = out_dir / "rollback_plan.json"
    mapping_path = out_dir / "app_mapping.csv"
    report_path = out_dir / "execution_report.md"

    write_json(plan_path, {
        "runId": run_id,
        "mode": mode,
        "targetOrgUrl": cfg.target_org_url,
        "app": _app_summary(cfg),
        "payload": payload,
        "assignments": result["assignments"],
        "warnings": warnings,
    })
    write_json(result_path, result)
    write_json(rollback_path, rollback)
    write_mapping_csv(mapping_path, mappings)
    result["outputFiles"] = [p.name for p in [plan_path, result_path, rollback_path, mapping_path, report_path]]
    write_json(result_path, result)
    write_report(report_path, result)

    return result, out_dir
