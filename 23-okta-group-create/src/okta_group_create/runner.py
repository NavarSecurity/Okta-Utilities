from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import GroupCreateConfig
from .inputs import load_group_rows
from .models import build_group_payload, build_group_specs, validate_specs
from .okta_client import OktaApiError, OktaClient
from .reports import write_csv, write_execution_report, write_json


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def run(config: GroupCreateConfig, apply: bool = False, output_dir: str | Path = "output") -> dict[str, Any]:
    run_id = f"okta-group-create-{utc_timestamp()}"
    run_dir = Path(output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    rows = load_group_rows(config.groups_file)
    specs = build_group_specs(rows, config)
    valid_specs, pre_skipped = validate_specs(specs, config)

    if len(valid_specs) > config.settings.max_groups_per_run:
        raise ValueError(f"Planned group count {len(valid_specs)} exceeds maxGroupsPerRun {config.settings.max_groups_per_run}.")

    client: OktaClient | None = None
    if apply:
        if not config.api_token:
            raise ValueError("OKTA_API_TOKEN is required for apply mode.")
        client = OktaClient(
            config.target_org_url,
            config.api_token,
            timeout=config.settings.request_timeout_seconds,
            max_retries=config.settings.max_retries,
            backoff_seconds=config.settings.retry_backoff_seconds,
        )

    planned: list[dict[str, Any]] = []
    created: list[dict[str, Any]] = []
    existing: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = list(pre_skipped)
    failed: list[dict[str, Any]] = []
    rollback: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for spec in valid_specs:
        payload = build_group_payload(spec)
        planned_item = {"rowNumber": spec.row_number, "name": spec.name, "payload": payload}
        planned.append(planned_item)

        if not apply:
            continue

        try:
            assert client is not None
            found = client.find_group_by_name(spec.name)
            if found and config.settings.skip_existing:
                existing.append({
                    "rowNumber": spec.row_number,
                    "name": spec.name,
                    "groupId": found.get("id", ""),
                    "status": "EXISTING",
                    "reason": "Group already exists and skipExisting is enabled.",
                })
                continue
            if found and not config.settings.skip_existing:
                skipped.append({
                    "rowNumber": spec.row_number,
                    "name": spec.name,
                    "status": "SKIPPED",
                    "reasonCode": "EXISTS",
                    "reason": "Group already exists. Utility does not update existing groups.",
                })
                continue
            group = client.create_group(payload)
            created.append({
                "rowNumber": spec.row_number,
                "name": spec.name,
                "groupId": group.get("id", ""),
                "status": "CREATED",
            })
            if group.get("id"):
                rollback.append({
                    "action": "delete_group",
                    "groupId": group.get("id"),
                    "name": spec.name,
                    "method": "DELETE",
                    "endpoint": f"/api/v1/groups/{group.get('id')}",
                })
        except OktaApiError as exc:
            failure = {
                "rowNumber": spec.row_number,
                "name": spec.name,
                "status": "FAILED",
                "message": str(exc),
                "statusCode": exc.status_code,
                "oktaResponse": exc.response,
            }
            failed.append(failure)
            errors.append(failure)
            if not config.settings.continue_on_error:
                break
        except Exception as exc:
            failure = {
                "rowNumber": spec.row_number,
                "name": spec.name,
                "status": "FAILED",
                "message": str(exc),
            }
            failed.append(failure)
            errors.append(failure)
            if not config.settings.continue_on_error:
                break

    result = {
        "runId": run_id,
        "mode": "apply" if apply else "dry-run",
        "targetOrgUrl": config.target_org_url,
        "groupsFile": str(config.groups_file),
        "summary": {
            "inputRows": len(rows),
            "plannedGroups": len(planned),
            "createdGroups": len(created),
            "existingGroups": len(existing),
            "skippedGroups": len(skipped),
            "failedGroups": len(failed),
        },
        "planned": planned,
        "created": created,
        "existing": existing,
        "skipped": skipped,
        "failed": failed,
        "rollback": rollback,
        "errors": errors,
    }

    write_json(run_dir / "group_create_plan.json", {"runId": run_id, "groups": planned})
    write_json(run_dir / "group_create_result.json", result)
    write_json(run_dir / "rollback_plan.json", {"runId": run_id, "rollback": rollback})
    write_csv(run_dir / "created_groups.csv", created, ["rowNumber", "name", "groupId", "status"])
    write_csv(run_dir / "existing_groups.csv", existing, ["rowNumber", "name", "groupId", "status", "reason"])
    write_csv(run_dir / "skipped_groups.csv", skipped, ["rowNumber", "name", "status", "reasonCode", "reason"])
    write_csv(run_dir / "failed_groups.csv", failed, ["rowNumber", "name", "status", "message", "statusCode"])
    write_execution_report(run_dir / "execution_report.md", result)
    result["outputDir"] = str(run_dir)
    return result
