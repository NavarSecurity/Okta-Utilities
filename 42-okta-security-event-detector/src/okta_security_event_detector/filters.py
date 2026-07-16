from __future__ import annotations

from typing import Any

from .utils import event_time


def apply_filters(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    filters = config.get("filters", {}) or {}
    event_types = set(filters.get("eventTypes") or [])
    actors = set(filters.get("actors") or [])
    exclude_actors = set(filters.get("excludeActors") or [])
    ip_addresses = set(filters.get("ipAddresses") or [])
    start_time = event_time(filters.get("startTime"))
    end_time = event_time(filters.get("endTime"))

    filtered: list[dict[str, Any]] = []
    for event in events:
        if event_types and event.get("eventType") not in event_types:
            continue
        actor = event.get("actorAlternateId") or event.get("actorId") or ""
        if actors and actor not in actors:
            continue
        if exclude_actors and actor in exclude_actors:
            continue
        if ip_addresses and event.get("clientIpAddress") not in ip_addresses:
            continue
        published = event_time(event.get("published"))
        if start_time and published and published < start_time:
            continue
        if end_time and published and published > end_time:
            continue
        filtered.append(event)
    return filtered
