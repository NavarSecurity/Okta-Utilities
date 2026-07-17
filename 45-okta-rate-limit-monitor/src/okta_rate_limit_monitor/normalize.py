from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def calculate_remaining_percent(limit: int | None, remaining: int | None) -> float | None:
    if limit is None or remaining is None or limit <= 0:
        return None
    return round((remaining / limit) * 100, 2)


def parse_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_rate_limit_headers(headers: dict[str, Any]) -> dict[str, Any]:
    limit = parse_int(headers.get("X-Rate-Limit-Limit") or headers.get("x-rate-limit-limit"))
    remaining = parse_int(headers.get("X-Rate-Limit-Remaining") or headers.get("x-rate-limit-remaining"))
    reset = parse_int(headers.get("X-Rate-Limit-Reset") or headers.get("x-rate-limit-reset"))
    reset_utc = ""
    if reset:
        try:
            reset_utc = datetime.fromtimestamp(reset, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, ValueError):
            reset_utc = ""
    return {
        "rateLimitLimit": limit,
        "rateLimitRemaining": remaining,
        "rateLimitResetEpoch": reset,
        "rateLimitResetUtc": reset_utc,
        "remainingPercent": calculate_remaining_percent(limit, remaining),
    }


def extract_debug_data(event: dict[str, Any]) -> dict[str, Any]:
    debug = event.get("debugContext", {}) or {}
    data = debug.get("debugData", {}) or {}
    if not isinstance(data, dict):
        return {}
    return data


def normalize_system_log_event(event: dict[str, Any]) -> dict[str, Any]:
    actor = event.get("actor", {}) or {}
    client = event.get("client", {}) or {}
    user_agent = client.get("userAgent", {}) or {}
    outcome = event.get("outcome", {}) or {}
    debug_data = extract_debug_data(event)
    return {
        "uuid": event.get("uuid", ""),
        "published": event.get("published", ""),
        "eventType": event.get("eventType", ""),
        "displayMessage": event.get("displayMessage", ""),
        "severity": event.get("severity", ""),
        "actorId": actor.get("id", ""),
        "actorAlternateId": actor.get("alternateId", ""),
        "actorDisplayName": actor.get("displayName", ""),
        "actorType": actor.get("type", ""),
        "clientIp": client.get("ipAddress", ""),
        "userAgent": user_agent.get("rawUserAgent", ""),
        "requestUri": debug_data.get("requestUri", "") or debug_data.get("url", ""),
        "outcomeResult": outcome.get("result", ""),
        "outcomeReason": outcome.get("reason", ""),
    }


def summarize_event_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        key = str(event.get("displayMessage") or event.get("eventType") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def operation_endpoint_key(endpoint: str) -> str:
    if not endpoint:
        return ""
    clean = endpoint.split("?", 1)[0].rstrip("/")
    return clean
