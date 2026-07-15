from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

ATTRIBUTE_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
SUPPORTED_TYPES = {"string", "number", "integer", "boolean", "array"}


class PayloadError(ValueError):
    pass


def validate_attribute_name(name: str) -> None:
    if not name or not ATTRIBUTE_NAME_PATTERN.match(name):
        raise PayloadError(
            f"Invalid attribute name '{name}'. Use letters, numbers, and underscores. The name must start with a letter."
        )


def normalize_definition(definition: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(definition, dict):
        raise PayloadError("Attribute definition must be an object.")
    normalized = deepcopy(definition)
    attr_type = normalized.get("type")
    if attr_type not in SUPPORTED_TYPES:
        raise PayloadError(f"Unsupported attribute type '{attr_type}'. Supported types: {sorted(SUPPORTED_TYPES)}")
    if "title" not in normalized or not str(normalized["title"]).strip():
        raise PayloadError("Attribute definition must include a non-empty title.")
    if attr_type == "array" and "items" not in normalized:
        normalized["items"] = {"type": "string"}
    if "permissions" in normalized and not isinstance(normalized["permissions"], list):
        raise PayloadError("permissions must be an array when provided.")
    return normalized


def build_schema_payload(attribute_name: str, definition: dict[str, Any]) -> dict[str, Any]:
    validate_attribute_name(attribute_name)
    normalized_definition = normalize_definition(definition)
    return {
        "definitions": {
            "custom": {
                "id": "#custom",
                "type": "object",
                "properties": {
                    attribute_name: normalized_definition
                }
            }
        }
    }


def get_custom_properties(schema: dict[str, Any]) -> dict[str, Any]:
    definitions = schema.get("definitions") or {}
    custom = definitions.get("custom") or {}
    properties = custom.get("properties") or {}
    if isinstance(properties, dict):
        return properties
    return {}
