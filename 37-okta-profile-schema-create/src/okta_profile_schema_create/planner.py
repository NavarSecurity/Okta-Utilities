from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import Settings
from .okta_client import OktaApiError, OktaClient
from .payload import build_schema_payload, get_custom_properties, normalize_definition, validate_attribute_name


@dataclass
class PlanItem:
    index: int
    action: str
    status: str
    target_type: str
    schema_id: str
    attribute_name: str
    app_id: str | None = None
    app_name: str | None = None
    reason: str | None = None
    payload: dict[str, Any] | None = None
    existing_definition: dict[str, Any] | None = None
    requested_definition: dict[str, Any] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "action": self.action,
            "status": self.status,
            "targetType": self.target_type,
            "schemaId": self.schema_id,
            "attributeName": self.attribute_name,
            "appId": self.app_id,
            "appName": self.app_name,
            "reason": self.reason,
            "payload": self.payload,
            "existingDefinition": self.existing_definition,
            "requestedDefinition": self.requested_definition,
            "error": self.error,
        }


@dataclass
class PlanResult:
    planned: list[PlanItem] = field(default_factory=list)
    errors: list[PlanItem] = field(default_factory=list)

    @property
    def items(self) -> list[PlanItem]:
        return self.planned + self.errors


def _target_type(attribute: dict[str, Any]) -> str:
    value = str(attribute.get("targetType", attribute.get("target", "user"))).lower().strip()
    if value not in {"user", "app"}:
        raise ValueError("targetType must be user or app.")
    return value


def _resolve_app_id(attribute: dict[str, Any], client: OktaClient | None) -> tuple[str | None, str | None]:
    app_id = attribute.get("appId")
    app_name = attribute.get("appName")
    if app_id:
        return str(app_id), str(app_name) if app_name else None
    if app_name and client:
        app = client.find_app_by_name(str(app_name))
        if app:
            return str(app.get("id")), str(app_name)
    return None, str(app_name) if app_name else None


def _get_schema(target_type: str, schema_id: str, app_id: str | None, client: OktaClient | None) -> dict[str, Any] | None:
    if not client:
        return None
    if target_type == "user":
        return client.get_user_schema(schema_id)
    if not app_id:
        raise ValueError("appId or resolvable appName is required for app schema targets.")
    return client.get_app_schema(app_id, schema_id)


def create_plan(settings: Settings, input_data: dict[str, Any], client: OktaClient | None) -> PlanResult:
    result = PlanResult()
    attributes = input_data.get("attributes", [])

    for index, attribute in enumerate(attributes, start=1):
        try:
            if not isinstance(attribute, dict):
                raise ValueError("Each attribute entry must be an object.")

            target_type = _target_type(attribute)
            if target_type == "app" and not settings.allow_app_schema_updates:
                raise ValueError("App schema updates are disabled by config.")
            if target_type == "user" and not settings.allow_user_schema_updates:
                raise ValueError("User schema updates are disabled by config.")

            schema_id = str(attribute.get("schemaId", "default"))
            attribute_name = str(attribute.get("name", "")).strip()
            validate_attribute_name(attribute_name)
            definition = normalize_definition(attribute.get("definition", {}))
            app_id, app_name = _resolve_app_id(attribute, client)
            payload = build_schema_payload(attribute_name, definition)

            existing_definition = None
            status = "planned"
            action = "create"
            reason = "Attribute does not exist or existing check was not requested."

            if settings.check_existing and client:
                schema = _get_schema(target_type, schema_id, app_id, client)
                properties = get_custom_properties(schema or {})
                existing_definition = properties.get(attribute_name)
                if existing_definition is not None:
                    if settings.on_existing == "skip":
                        status = "skipped"
                        action = "skip"
                        reason = "Attribute already exists and onExisting is skip."
                    elif settings.on_existing == "fail":
                        status = "error"
                        action = "fail"
                        reason = "Attribute already exists and onExisting is fail."
                    else:
                        status = "planned"
                        action = "update"
                        reason = "Attribute already exists and onExisting is update. Okta may reject incompatible type changes."

            item = PlanItem(
                index=index,
                action=action,
                status=status,
                target_type=target_type,
                schema_id=schema_id,
                attribute_name=attribute_name,
                app_id=app_id,
                app_name=app_name,
                reason=reason,
                payload=payload,
                existing_definition=existing_definition,
                requested_definition=definition,
            )
            if status == "error":
                result.errors.append(item)
            else:
                result.planned.append(item)
        except (ValueError, OktaApiError) as exc:
            item = PlanItem(
                index=index,
                action="error",
                status="error",
                target_type=str(attribute.get("targetType", attribute.get("target", "unknown"))) if isinstance(attribute, dict) else "unknown",
                schema_id=str(attribute.get("schemaId", "default")) if isinstance(attribute, dict) else "default",
                attribute_name=str(attribute.get("name", "")) if isinstance(attribute, dict) else "",
                app_id=str(attribute.get("appId")) if isinstance(attribute, dict) and attribute.get("appId") else None,
                app_name=str(attribute.get("appName")) if isinstance(attribute, dict) and attribute.get("appName") else None,
                error=str(exc),
            )
            result.errors.append(item)
            if not settings.continue_on_error:
                break
    return result
