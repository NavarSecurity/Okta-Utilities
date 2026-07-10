from __future__ import annotations

import copy
import json
from typing import Any

READ_ONLY_FIELDS = {
    "id",
    "created",
    "lastUpdated",
    "_links",
}

# These are not secrets, but sort them to make drift output stable.
SORTABLE_LIST_KEYS = {
    "asns",
    "countriesAndRegions",
    "locations",
    "proxyType",
    "ipServiceCategories",
}


def stable_json(value: Any) -> str:
    return json.dumps(normalize_for_compare(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalize_for_compare(value: Any) -> Any:
    if isinstance(value, dict):
        normalized = {}
        for key in sorted(value):
            if key in READ_ONLY_FIELDS:
                continue
            normalized[key] = normalize_for_compare(value[key])
        return normalized
    if isinstance(value, list):
        normalized_list = [normalize_for_compare(item) for item in value]
        return sorted(normalized_list, key=lambda item: stable_json_no_recursion(item))
    return value


def stable_json_no_recursion(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def prepare_zone_payload(zone: dict[str, Any], *, include_status: bool = True) -> dict[str, Any]:
    payload = copy.deepcopy(zone)
    for key in list(payload.keys()):
        if key in READ_ONLY_FIELDS:
            payload.pop(key, None)
    if not include_status:
        payload.pop("status", None)
    return payload


def zone_key(zone: dict[str, Any], match_by: str = "name") -> str:
    value = zone.get(match_by)
    if value is None:
        raise ValueError(f"Zone is missing match key '{match_by}': {zone}")
    return str(value).strip().lower()


def summarize_zone(zone: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": zone.get("id", ""),
        "name": zone.get("name", ""),
        "type": zone.get("type", ""),
        "usage": zone.get("usage", ""),
        "status": zone.get("status", ""),
        "system": zone.get("system", False),
        "gatewayCount": len(zone.get("gateways") or []),
        "proxyCount": len(zone.get("proxies") or []),
        "locationCount": len(zone.get("locations") or zone.get("countriesAndRegions") or []),
        "asnCount": len(zone.get("asns") or []),
        "created": zone.get("created", ""),
        "lastUpdated": zone.get("lastUpdated", ""),
    }
