from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import OktaApiError, OktaClient
from .config import RestoreConfig
from .planner import RestoreOperation, RestorePlan
from .resources import DELETE_ENDPOINTS, LIST_ENDPOINTS, natural_key


@dataclass
class RestoreResult:
    mode: str
    operations: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    rollback: list[dict[str, Any]] = field(default_factory=list)
    request_summary: dict[str, Any] = field(default_factory=dict)

    def has_errors(self) -> bool:
        return bool(self.errors)


def _existing_objects_by_key(client: OktaClient, resource: str) -> dict[str, dict[str, Any]]:
    endpoint = LIST_ENDPOINTS[resource]
    existing = client.paged_get(endpoint)
    by_key: dict[str, dict[str, Any]] = {}
    for item in existing:
        if isinstance(item, dict):
            key = natural_key(resource, item)
            if key:
                by_key[key] = item
    return by_key


def _create_operation(client: OktaClient, config: RestoreConfig, op: RestoreOperation) -> dict[str, Any]:
    params: dict[str, Any] | None = None
    if op.resource == "applications":
        params = {"activate": "true" if config.activate_apps else "false"}
    created = client.post(op.endpoint, json_body=op.payload, params=params)
    if not isinstance(created, dict):
        created = {}
    op.target_id = created.get("id")
    op.status = "created"
    return created


def execute_plan(client: OktaClient, config: RestoreConfig, plan: RestorePlan, apply: bool) -> RestoreResult:
    mode = "apply" if apply else "dry-run"
    result = RestoreResult(mode=mode)
    result.skipped.extend(plan.skipped)

    cache: dict[str, dict[str, dict[str, Any]]] = {}

    for op in plan.operations:
        try:
            if op.resource not in cache:
                cache[op.resource] = _existing_objects_by_key(client, op.resource)

            existing = cache[op.resource].get(op.natural_key)
            if existing:
                skipped = op.to_dict(include_payload=False)
                skipped["status"] = "skipped_existing"
                skipped["reason"] = "An object with the same natural key already exists in the target org."
                skipped["targetId"] = existing.get("id")
                if config.skip_existing:
                    result.skipped.append(skipped)
                    continue
                error = dict(skipped)
                error["type"] = "DuplicateObjectError"
                result.errors.append(error)
                if config.fail_fast:
                    break
                continue

            if not apply:
                planned = op.to_dict(include_payload=False)
                planned["status"] = "would_create"
                result.operations.append(planned)
                continue

            created = _create_operation(client, config, op)
            op_dict = op.to_dict(include_payload=False)
            op_dict["status"] = "created"
            op_dict["targetId"] = created.get("id")
            result.operations.append(op_dict)

            if created.get("id") and op.resource in DELETE_ENDPOINTS:
                result.rollback.append(
                    {
                        "resource": op.resource,
                        "action": "delete_created_object",
                        "method": "DELETE",
                        "endpoint": DELETE_ENDPOINTS[op.resource].format(id=created["id"]),
                        "targetId": created["id"],
                        "displayName": op.display_name,
                        "note": "Rollback is not automatically executed. Review before use.",
                    }
                )
                cache[op.resource][op.natural_key] = created

        except OktaApiError as exc:
            err = op.to_dict(include_payload=False)
            err.update(exc.to_dict())
            err["resource"] = op.resource
            err["displayName"] = op.display_name
            result.errors.append(err)
            if config.fail_fast:
                break
        except Exception as exc:
            err = op.to_dict(include_payload=False)
            err.update({"type": type(exc).__name__, "message": str(exc)})
            result.errors.append(err)
            if config.fail_fast:
                break

    result.request_summary = client.request_summary()
    return result
