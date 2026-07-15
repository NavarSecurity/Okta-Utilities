from __future__ import annotations

from typing import Any


def get_nested(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def object_info(mapping: dict[str, Any], side: str) -> dict[str, str]:
    obj = mapping.get(side) if isinstance(mapping.get(side), dict) else {}
    links = mapping.get("_links") if isinstance(mapping.get("_links"), dict) else {}
    link_obj = links.get(side) if isinstance(links.get(side), dict) else {}

    return {
        "id": str(obj.get("id") or link_obj.get("id") or ""),
        "name": str(obj.get("name") or link_obj.get("name") or link_obj.get("title") or ""),
        "type": str(obj.get("type") or link_obj.get("type") or ""),
    }


def mapping_summary(mapping: dict[str, Any]) -> dict[str, Any]:
    source = object_info(mapping, "source")
    target = object_info(mapping, "target")
    properties = mapping.get("properties") if isinstance(mapping.get("properties"), dict) else {}
    return {
        "id": mapping.get("id", ""),
        "sourceId": source["id"],
        "sourceName": source["name"],
        "sourceType": source["type"],
        "targetId": target["id"],
        "targetName": target["name"],
        "targetType": target["type"],
        "propertyCount": len(properties),
        "status": mapping.get("status", ""),
        "created": mapping.get("created", ""),
        "lastUpdated": mapping.get("lastUpdated", ""),
    }


def mapping_properties(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    source = object_info(mapping, "source")
    target = object_info(mapping, "target")
    properties = mapping.get("properties") if isinstance(mapping.get("properties"), dict) else {}
    rows: list[dict[str, Any]] = []

    for target_attribute, definition in sorted(properties.items()):
        if not isinstance(definition, dict):
            definition = {"value": definition}
        rows.append(
            {
                "mappingId": mapping.get("id", ""),
                "sourceId": source["id"],
                "sourceName": source["name"],
                "sourceType": source["type"],
                "targetId": target["id"],
                "targetName": target["name"],
                "targetType": target["type"],
                "targetAttribute": target_attribute,
                "expression": definition.get("expression", ""),
                "pushStatus": definition.get("pushStatus", ""),
                "mappingStatus": definition.get("status", ""),
                "type": definition.get("type", ""),
                "value": definition.get("value", ""),
            }
        )
    return rows


def sources_targets(mappings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    rows: list[dict[str, Any]] = []
    for mapping in mappings:
        for side in ["source", "target"]:
            info = object_info(mapping, side)
            key = (side, info["id"], info["name"], info["type"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "role": side,
                    "id": info["id"],
                    "name": info["name"],
                    "type": info["type"],
                }
            )
    return sorted(rows, key=lambda row: (row["role"], row["type"], row["name"], row["id"]))


def group_by_type(mappings: list[dict[str, Any]], side: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for mapping in mappings:
        info = object_info(mapping, side)
        type_name = info["type"] or "UNKNOWN"
        groups.setdefault(type_name, []).append(mapping)
    return groups
