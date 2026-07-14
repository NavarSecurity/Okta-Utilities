from __future__ import annotations

import json
from typing import Any


def stable_json(value: Any) -> str:
    if value is None or value == {} or value == []:
        return ""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def boolish(value: Any) -> str:
    if value is None:
        return ""
    return "true" if bool(value) else "false"


def schema_title(schema: dict[str, Any]) -> str:
    return str(schema.get("title") or schema.get("name") or schema.get("id") or "")


def iter_schema_properties(schema: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    definitions = schema.get("definitions") or {}
    if not isinstance(definitions, dict):
        return rows

    for definition_name, definition in definitions.items():
        if not isinstance(definition, dict):
            continue
        properties = definition.get("properties") or {}
        required_values = set(definition.get("required") or [])
        if not isinstance(properties, dict):
            continue
        for attr_name, attr in properties.items():
            if not isinstance(attr, dict):
                attr = {}
            permissions = attr.get("permissions")
            rows.append(
                {
                    "definition": definition_name,
                    "attributeName": attr_name,
                    "title": attr.get("title", ""),
                    "type": attr.get("type", ""),
                    "required": boolish(attr_name in required_values or attr.get("required")),
                    "mutability": attr.get("mutability", ""),
                    "scope": attr.get("scope", ""),
                    "master": attr.get("master", ""),
                    "unique": boolish(attr.get("unique")) if "unique" in attr else "",
                    "minLength": attr.get("minLength", ""),
                    "maxLength": attr.get("maxLength", ""),
                    "enum": stable_json(attr.get("enum")),
                    "oneOf": stable_json(attr.get("oneOf")),
                    "permissions": stable_json(permissions),
                    "externalName": attr.get("externalName", ""),
                    "externalNamespace": attr.get("externalNamespace", ""),
                }
            )
    return rows


def summarize_schema(category: str, schema: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    context = context or {}
    base = {
        "schemaCategory": category,
        "schemaId": schema.get("id", ""),
        "schemaName": schema_title(schema),
        "schemaType": schema.get("type", ""),
        "appId": context.get("appId", ""),
        "appLabel": context.get("appLabel", ""),
        "appName": context.get("appName", ""),
        "appStatus": context.get("appStatus", ""),
    }
    rows: list[dict[str, Any]] = []
    for prop in iter_schema_properties(schema):
        row = dict(base)
        row.update(prop)
        rows.append(row)
    return rows


def summarize_schema_header() -> list[str]:
    return [
        "schemaCategory",
        "schemaId",
        "schemaName",
        "schemaType",
        "appId",
        "appLabel",
        "appName",
        "appStatus",
        "definition",
        "attributeName",
        "title",
        "type",
        "required",
        "mutability",
        "scope",
        "master",
        "unique",
        "minLength",
        "maxLength",
        "enum",
        "oneOf",
        "permissions",
        "externalName",
        "externalNamespace",
    ]


def summarize_app(app: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": app.get("id", ""),
        "label": app.get("label", ""),
        "name": app.get("name", ""),
        "status": app.get("status", ""),
        "signOnMode": app.get("signOnMode", ""),
    }
