from __future__ import annotations

from typing import Any

from .resources import display_name


def _has_values(selection: dict[str, list[str]], *keys: str) -> bool:
    return any(selection.get(key) for key in keys)


def is_selected(resource: str, obj: dict[str, Any], selection: dict[str, dict[str, list[str]]]) -> bool:
    rules = selection.get(resource) or {}
    if not rules or not any(rules.values()):
        return True

    source_id = obj.get("id")
    if source_id and source_id in set(rules.get("ids") or []):
        return True

    name = display_name(resource, obj)

    if resource == "applications":
        labels = set(rules.get("labels") or []) | set(rules.get("names") or [])
        return name in labels

    if resource == "trusted_origins":
        names = set(rules.get("names") or [])
        origins = set(rules.get("origins") or [])
        return name in names or obj.get("origin") in origins

    names = set(rules.get("names") or [])
    return name in names
