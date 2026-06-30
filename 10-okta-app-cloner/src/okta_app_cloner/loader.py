from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import OktaApiError, OktaClient
from .config import AppClonerConfig
from .planner import ClonePlan


@dataclass
class CloneResult:
    operations: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    rollback: list[dict[str, Any]] = field(default_factory=list)
    request_summary: dict[str, Any] = field(default_factory=dict)

    def has_errors(self) -> bool:
        return bool(self.errors)


def execute_plan(client: OktaClient, config: AppClonerConfig, plan: ClonePlan, *, apply: bool) -> CloneResult:
    result = CloneResult(skipped=list(plan.skipped))

    for op in plan.operations:
        try:
            existing = client.find_apps_by_label(op.label)
            if existing and config.skip_existing:
                result.skipped.append({
                    "resource": "applications",
                    "label": op.label,
                    "sourceId": op.source_id,
                    "reason": "target_app_with_same_label_exists",
                    "targetIds": [app.get("id") for app in existing if isinstance(app, dict)],
                })
                continue

            if not apply:
                result.operations.append({
                    "resource": "applications",
                    "label": op.label,
                    "sourceId": op.source_id,
                    "status": "would_create",
                    "signOnMode": op.sign_on_mode,
                    "warnings": op.warnings,
                })
                continue

            created = client.post("/api/v1/apps", json_body=op.payload)
            target_id = created.get("id") if isinstance(created, dict) else None
            result.operations.append({
                "resource": "applications",
                "label": op.label,
                "sourceId": op.source_id,
                "targetId": target_id,
                "status": "created",
                "signOnMode": op.sign_on_mode,
                "warnings": op.warnings,
            })
            if target_id:
                result.rollback.append({
                    "resource": "applications",
                    "action": "delete_created_application",
                    "method": "DELETE",
                    "endpoint": f"/api/v1/apps/{target_id}",
                    "targetId": target_id,
                    "label": op.label,
                    "note": "Rollback is not automatically executed. Review before use.",
                })
                if config.activate_cloned_apps:
                    try:
                        client.post(f"/api/v1/apps/{target_id}/lifecycle/activate")
                    except OktaApiError as exc:
                        result.errors.append({
                            "resource": "applications",
                            "label": op.label,
                            "targetId": target_id,
                            "stage": "activate_cloned_app",
                            **exc.to_dict(),
                        })
                        if config.fail_fast:
                            break

        except OktaApiError as exc:
            result.errors.append({
                "resource": "applications",
                "label": op.label,
                "sourceId": op.source_id,
                **exc.to_dict(),
            })
            if config.fail_fast:
                break
        except Exception as exc:
            result.errors.append({
                "resource": "applications",
                "label": op.label,
                "sourceId": op.source_id,
                "type": type(exc).__name__,
                "message": str(exc),
            })
            if config.fail_fast:
                break

    result.request_summary = client.request_summary()
    return result
