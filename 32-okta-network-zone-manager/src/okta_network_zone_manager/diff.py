from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .normalize import normalize_for_compare, stable_json, zone_key


@dataclass
class ZoneDriftResult:
    missing_in_target: list[dict[str, Any]] = field(default_factory=list)
    extra_in_target: list[dict[str, Any]] = field(default_factory=list)
    modified: list[dict[str, Any]] = field(default_factory=list)
    unchanged: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_differences(self) -> int:
        return len(self.missing_in_target) + len(self.extra_in_target) + len(self.modified)


def compare_zones(source_zones: list[dict[str, Any]], target_zones: list[dict[str, Any]], *, match_by: str = "name") -> ZoneDriftResult:
    source_index = {zone_key(zone, match_by): zone for zone in source_zones}
    target_index = {zone_key(zone, match_by): zone for zone in target_zones}
    result = ZoneDriftResult()

    for key in sorted(source_index):
        source_zone = source_index[key]
        target_zone = target_index.get(key)
        if target_zone is None:
            result.missing_in_target.append({
                "matchKey": key,
                "source": source_zone,
            })
            continue

        source_norm = normalize_for_compare(source_zone)
        target_norm = normalize_for_compare(target_zone)
        if stable_json(source_norm) == stable_json(target_norm):
            result.unchanged.append({"matchKey": key, "name": source_zone.get("name", key)})
        else:
            result.modified.append({
                "matchKey": key,
                "name": source_zone.get("name", key),
                "fieldChanges": describe_field_changes(source_norm, target_norm),
                "source": source_zone,
                "target": target_zone,
            })

    for key in sorted(target_index):
        if key not in source_index:
            result.extra_in_target.append({
                "matchKey": key,
                "target": target_index[key],
            })

    return result


def describe_field_changes(source: dict[str, Any], target: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    keys = sorted(set(source) | set(target))
    for key in keys:
        left = source.get(key)
        right = target.get(key)
        if stable_json(left) != stable_json(right):
            changes.append({
                "field": key,
                "source": left,
                "target": right,
            })
    return changes
