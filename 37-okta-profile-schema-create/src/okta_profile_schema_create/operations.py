from __future__ import annotations

from typing import Any

from .okta_client import OktaApiError, OktaClient
from .planner import PlanItem


def apply_plan(items: list[PlanItem], client: OktaClient) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    applied: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    rollback_actions: list[dict[str, Any]] = []

    for item in items:
        if item.status == "skipped" or item.action == "skip":
            applied.append({**item.as_dict(), "applyStatus": "skipped"})
            continue
        if item.status == "error" or item.action == "fail":
            failures.append({**item.as_dict(), "applyStatus": "failed", "error": item.reason or item.error})
            continue
        if not item.payload:
            failures.append({**item.as_dict(), "applyStatus": "failed", "error": "Missing payload."})
            continue

        try:
            if item.target_type == "user":
                response = client.update_user_schema(item.schema_id, item.payload)
            elif item.target_type == "app":
                if not item.app_id:
                    raise OktaApiError("Missing appId for app schema update.")
                response = client.update_app_schema(item.app_id, item.schema_id, item.payload)
            else:
                raise OktaApiError(f"Unsupported target type: {item.target_type}")

            applied.append({**item.as_dict(), "applyStatus": "applied", "responseId": response.get("id") if isinstance(response, dict) else None})
            rollback_actions.append({
                "action": "review_remove_attribute",
                "targetType": item.target_type,
                "schemaId": item.schema_id,
                "appId": item.app_id,
                "appName": item.app_name,
                "attributeName": item.attribute_name,
                "note": "Best-effort rollback evidence. Review in Okta Profile Editor before removing schema attributes.",
            })
        except OktaApiError as exc:
            failures.append({
                **item.as_dict(),
                "applyStatus": "failed",
                "error": str(exc),
                "statusCode": exc.status_code,
                "body": exc.body,
            })
    return applied, failures, rollback_actions
