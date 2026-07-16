from __future__ import annotations

import re
from collections import Counter
from typing import Any


def get_nested(obj: dict[str, Any], path: str, default: Any = "") -> Any:
    current: Any = obj
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def target_summary_string(event: dict[str, Any]) -> str:
    targets = event.get("target") or []
    if not isinstance(targets, list):
        return ""
    values = []
    for target in targets:
        if not isinstance(target, dict):
            continue
        label = target.get("displayName") or target.get("alternateId") or target.get("id") or "unknown"
        type_value = target.get("type") or "unknown"
        values.append(f"{label} ({type_value})")
    return "; ".join(values)


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "uuid": event.get("uuid", ""),
        "published": event.get("published", ""),
        "eventType": event.get("eventType", ""),
        "displayMessage": event.get("displayMessage", ""),
        "severity": event.get("severity", ""),
        "actorId": get_nested(event, "actor.id"),
        "actorType": get_nested(event, "actor.type"),
        "actorAlternateId": get_nested(event, "actor.alternateId"),
        "actorDisplayName": get_nested(event, "actor.displayName"),
        "clientIpAddress": get_nested(event, "client.ipAddress"),
        "clientCountry": get_nested(event, "client.geographicalContext.country"),
        "clientState": get_nested(event, "client.geographicalContext.state"),
        "clientCity": get_nested(event, "client.geographicalContext.city"),
        "outcomeResult": get_nested(event, "outcome.result"),
        "outcomeReason": get_nested(event, "outcome.reason"),
        "transactionId": get_nested(event, "transaction.id"),
        "requestId": get_nested(event, "debugContext.debugData.requestId"),
        "targetCount": len(event.get("target") or []) if isinstance(event.get("target") or [], list) else 0,
        "targets": target_summary_string(event),
    }


def normalize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_event(event) for event in events]


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "unknown")
    return cleaned.strip("._") or "unknown"


def event_type_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(event.get("eventType") or "unknown" for event in events)
    return [{"eventType": key, "count": value} for key, value in counts.most_common()]


def actor_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for event in events:
        key = (
            get_nested(event, "actor.id"),
            get_nested(event, "actor.alternateId"),
            get_nested(event, "actor.displayName"),
            get_nested(event, "actor.type"),
        )
        counts[key] += 1
    return [
        {
            "actorId": actor_id,
            "actorAlternateId": alternate_id,
            "actorDisplayName": display_name,
            "actorType": actor_type,
            "count": count,
        }
        for (actor_id, alternate_id, display_name, actor_type), count in counts.most_common()
    ]


def target_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for event in events:
        targets = event.get("target") or []
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            key = (
                str(target.get("id", "")),
                str(target.get("alternateId", "")),
                str(target.get("displayName", "")),
                str(target.get("type", "")),
            )
            counts[key] += 1
    return [
        {
            "targetId": target_id,
            "targetAlternateId": alternate_id,
            "targetDisplayName": display_name,
            "targetType": target_type,
            "count": count,
        }
        for (target_id, alternate_id, display_name, target_type), count in counts.most_common()
    ]


def outcome_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(get_nested(event, "outcome.result") or "unknown" for event in events)
    return [{"outcomeResult": key, "count": value} for key, value in counts.most_common()]
