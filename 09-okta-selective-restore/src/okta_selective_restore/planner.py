from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RestoreConfig, SUPPORTED_RESOURCES, UNSUPPORTED_BUT_KNOWN
from .resources import CREATE_ENDPOINTS, RESOURCE_FILES, display_name, natural_key
from .sanitizers import SANITIZERS, contains_redaction_marker
from .selectors import is_selected


@dataclass
class RestoreOperation:
    resource: str
    source_id: str | None
    display_name: str
    natural_key: str
    method: str
    endpoint: str
    payload: dict[str, Any]
    action: str = "create"
    status: str = "planned"
    reason: str | None = None
    target_id: str | None = None

    def to_dict(self, include_payload: bool = True) -> dict[str, Any]:
        data = {
            "resource": self.resource,
            "sourceId": self.source_id,
            "displayName": self.display_name,
            "naturalKey": self.natural_key,
            "action": self.action,
            "method": self.method,
            "endpoint": self.endpoint,
            "status": self.status,
            "reason": self.reason,
            "targetId": self.target_id,
        }
        if include_payload:
            data["payload"] = self.payload
        return data


@dataclass
class RestorePlan:
    operations: list[RestoreOperation] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self, include_payload: bool = True) -> dict[str, Any]:
        return {
            "operations": [op.to_dict(include_payload=include_payload) for op in self.operations],
            "skipped": self.skipped,
            "warnings": self.warnings,
            "counts": {
                "planned": len(self.operations),
                "skipped": len(self.skipped),
            },
        }


def _load_backup_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        # Some exporters write wrappers such as {"items": [...]}; support that pattern.
        for key in ("items", "data", "results"):
            if isinstance(data.get(key), list):
                return [item for item in data[key] if isinstance(item, dict)]
        return [data]
    return []


def build_plan(config: RestoreConfig) -> RestorePlan:
    plan = RestorePlan()

    for resource in config.include:
        if resource in UNSUPPORTED_BUT_KNOWN:
            plan.skipped.append(
                {
                    "resource": resource,
                    "reason": "Resource type is recognized but intentionally not restored by this safe initial version.",
                }
            )
            continue
        if resource not in SUPPORTED_RESOURCES:
            continue

        file_name = RESOURCE_FILES[resource]
        file_path = config.source_backup_dir / file_name
        if not file_path.exists():
            plan.skipped.append({"resource": resource, "reason": f"Backup file not found: {file_name}"})
            continue

        try:
            items = _load_backup_file(file_path)
        except Exception as exc:
            plan.skipped.append({"resource": resource, "reason": f"Could not parse {file_name}: {exc}"})
            continue

        for item in items:
            if not is_selected(resource, item, config.selection):
                continue

            source_status = str(item.get("status", "")).upper()
            if source_status and source_status not in {"ACTIVE", "ENABLED"} and not config.restore_inactive_objects:
                plan.skipped.append(
                    {
                        "resource": resource,
                        "sourceId": item.get("id"),
                        "displayName": display_name(resource, item),
                        "reason": f"Source object status is {source_status}; set restoreInactiveObjects=true to include it.",
                    }
                )
                continue

            sanitizer = SANITIZERS[resource]
            payload = sanitizer(item)
            if contains_redaction_marker(payload):
                plan.skipped.append(
                    {
                        "resource": resource,
                        "sourceId": item.get("id"),
                        "displayName": display_name(resource, item),
                        "reason": "Sanitized payload still contains redaction markers; refusing to restore this object.",
                    }
                )
                continue

            key = natural_key(resource, item)
            if not key:
                plan.skipped.append(
                    {
                        "resource": resource,
                        "sourceId": item.get("id"),
                        "displayName": display_name(resource, item),
                        "reason": "Could not determine a stable name/label key for idempotency checks.",
                    }
                )
                continue

            plan.operations.append(
                RestoreOperation(
                    resource=resource,
                    source_id=item.get("id"),
                    display_name=display_name(resource, item),
                    natural_key=key,
                    method="POST",
                    endpoint=CREATE_ENDPOINTS[resource],
                    payload=payload,
                )
            )

    if not plan.operations:
        plan.warnings.append("No restore operations were planned. Check include, selection, backup files, and skipped items.")
    return plan
