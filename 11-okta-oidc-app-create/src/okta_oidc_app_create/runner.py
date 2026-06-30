from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import json

from .config import RuntimeConfig
from .okta_client import OktaClient, OktaApiError
from .payload import build_oidc_app_payload, safe_payload_preview


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _error_dict(exc: Exception, app_label: str | None = None) -> dict[str, Any]:
    if isinstance(exc, OktaApiError):
        return {
            "appLabel": app_label,
            "type": "OktaApiError",
            "statusCode": exc.status_code,
            "message": exc.message,
            "url": exc.url,
            "errorBody": exc.error_body,
        }
    return {"appLabel": app_label, "type": type(exc).__name__, "message": str(exc)}


def _select_apps(config: RuntimeConfig, labels: list[str] | None) -> list[Any]:
    if not labels:
        return config.applications
    selected = []
    wanted = {label.strip() for label in labels if label.strip()}
    for app in config.applications:
        if app.label in wanted:
            selected.append(app)
    missing = sorted(wanted - {app.label for app in selected})
    if missing:
        raise ValueError(f"Selected label(s) not found in config: {', '.join(missing)}")
    return selected


def run_create(config: RuntimeConfig, *, apply: bool, labels: list[str] | None = None, print_json: bool = False) -> tuple[int, Path, dict[str, Any]]:
    stamp = utc_stamp()
    run_dir = config.output_dir / f"okta-oidc-app-create-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    client = OktaClient(
        config.target_org_url or "",
        config.api_token,
        timeout=config.timeout_seconds,
        max_retries=config.max_retries,
        retry_base=config.retry_base_seconds,
    )

    selected_apps = _select_apps(config, labels)
    plan_items: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    rollback_actions: list[dict[str, Any]] = []
    mapping_rows: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[str] = []

    for app in selected_apps:
        if app.login_uri:
            warnings.append(
                f"{app.label}: loginUri was ignored because Okta Apps API create payloads do not accept settings.oauthClient.login_uri; use initiateLoginUri instead."
            )
        payload = build_oidc_app_payload(app)
        item = {
            "label": app.label,
            "action": "create",
            "payloadPreview": safe_payload_preview(payload),
            "assignments": {"groups": app.assignments.groups, "users": app.assignments.users},
            "assignmentMode": "enabled" if config.create_assignments else "disabled",
        }
        try:
            existing = client.find_app_by_label(app.label, config.page_limit) if config.api_token else None
            if existing:
                item["action"] = "skip_existing" if config.skip_existing else "would_conflict"
                item["existingAppId"] = existing.get("id")
                plan_items.append(item)
                results.append({"label": app.label, "status": item["action"], "existingAppId": existing.get("id")})
                if config.skip_existing:
                    continue
            plan_items.append(item)

            if not apply:
                # In dry-run, optionally verify assignment targets if token is available.
                assignment_checks = []
                if config.create_assignments and config.api_token:
                    for group_name in app.assignments.groups:
                        group = client.find_group_by_name(group_name, config.page_limit)
                        assignment_checks.append({"type": "group", "name": group_name, "found": bool(group), "id": group.get("id") if group else None})
                    for login in app.assignments.users:
                        user = client.find_user_by_login(login)
                        assignment_checks.append({"type": "user", "login": login, "found": bool(user), "id": user.get("id") if user else None})
                results.append({"label": app.label, "status": "planned", "assignmentChecks": assignment_checks})
                continue

            created = client.create_app(payload)
            app_id = created.get("id")
            results.append({"label": app.label, "status": "created", "targetAppId": app_id})
            mapping_rows.append({"label": app.label, "targetAppId": app_id or "", "status": "created"})
            if app_id:
                rollback_actions.append({"action": "delete_app", "appId": app_id, "label": app.label})

            if config.create_assignments and app_id:
                for group_name in app.assignments.groups:
                    group = client.find_group_by_name(group_name, config.page_limit)
                    if not group:
                        raise ValueError(f"Group not found for assignment: {group_name}")
                    client.assign_group_to_app(app_id, group["id"])
                    results.append({"label": app.label, "status": "group_assigned", "group": group_name, "groupId": group["id"]})
                    rollback_actions.append({"action": "remove_group_assignment", "appId": app_id, "groupId": group["id"], "groupName": group_name})
                for login in app.assignments.users:
                    user = client.find_user_by_login(login)
                    if not user:
                        raise ValueError(f"User not found for assignment: {login}")
                    client.assign_user_to_app(app_id, user["id"])
                    results.append({"label": app.label, "status": "user_assigned", "user": login, "userId": user["id"]})
                    rollback_actions.append({"action": "remove_user_assignment", "appId": app_id, "userId": user["id"], "login": login})
        except Exception as exc:
            err = _error_dict(exc, app.label)
            errors.append(err)
            results.append({"label": app.label, "status": "error", "error": err})
            if config.fail_fast:
                break

    plan = {
        "utility": "okta-oidc-app-create",
        "version": "0.1.2",
        "mode": "apply" if apply else "dry-run",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "targetOrgUrl": config.target_org_url,
        "createAssignments": config.create_assignments,
        "skipExisting": config.skip_existing,
        "items": plan_items,
    }
    result = {
        "utility": "okta-oidc-app-create",
        "version": "0.1.2",
        "mode": "apply" if apply else "dry-run",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "targetOrgUrl": config.target_org_url,
        "counts": {
            "planned": sum(1 for r in results if r.get("status") == "planned"),
            "created": sum(1 for r in results if r.get("status") == "created"),
            "skipped": sum(1 for r in results if str(r.get("status", "")).startswith("skip")),
            "errors": len(errors),
        },
        "results": results,
        "errors": errors,
        "warnings": warnings,
        "requestSummary": client.request_summary(),
    }
    rollback = {"mode": "apply" if apply else "dry-run", "actions": rollback_actions}

    _write_json(run_dir / "oidc_app_create_plan.json", plan)
    _write_json(run_dir / "oidc_app_create_result.json", result)
    _write_json(run_dir / "rollback_plan.json", rollback)

    with (run_dir / "app_mapping.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "targetAppId", "status"])
        writer.writeheader()
        writer.writerows(mapping_rows)

    report_lines = [
        "# OIDC App Create Execution Report",
        "",
        f"Mode: {'apply' if apply else 'dry-run'}",
        f"Target org: {config.target_org_url}",
        f"Applications selected: {len(selected_apps)}",
        f"Created: {result['counts']['created']}",
        f"Skipped: {result['counts']['skipped']}",
        f"Errors: {len(errors)}",
        "",
        "## Results",
        "",
    ]
    for row in results:
        report_lines.append(f"- `{row.get('label')}`: {row.get('status')}")
    if errors:
        report_lines.extend(["", "## Errors", ""])
        for err in errors:
            report_lines.append(f"- `{err.get('appLabel')}`: {err.get('message')}")
    (run_dir / "execution_report.md").write_text("\n".join(report_lines), encoding="utf-8")

    if print_json:
        print(json.dumps(result, indent=2, sort_keys=True))

    exit_code = 1 if errors else 0
    return exit_code, run_dir, result
