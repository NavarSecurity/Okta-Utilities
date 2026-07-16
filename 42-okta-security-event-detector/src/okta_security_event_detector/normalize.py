from __future__ import annotations

from typing import Any

from .utils import get_path


def _user_agent(client: dict[str, Any]) -> str:
    user_agent = client.get("userAgent")
    if isinstance(user_agent, dict):
        return user_agent.get("rawUserAgent") or user_agent.get("browser") or ""
    if isinstance(user_agent, str):
        return user_agent
    return ""


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    actor = event.get("actor") or {}
    client = event.get("client") or {}
    outcome = event.get("outcome") or {}
    geo = client.get("geographicalContext") or {}
    debug_data = get_path(event, "debugContext.debugData", {}) or {}
    targets = event.get("target") or []

    actor_alternate_id = actor.get("alternateId") or actor.get("id") or "unknown"
    client_ip = client.get("ipAddress") or debug_data.get("requestUriIpChain") or ""
    target_names = []
    target_ids = []
    target_types = []
    if isinstance(targets, list):
        for target in targets:
            if isinstance(target, dict):
                target_names.append(target.get("displayName") or target.get("alternateId") or "")
                target_ids.append(target.get("id") or "")
                target_types.append(target.get("type") or "")

    return {
        "uuid": event.get("uuid") or event.get("id") or "",
        "published": event.get("published") or event.get("publishedTime") or "",
        "eventType": event.get("eventType") or "",
        "displayMessage": event.get("displayMessage") or "",
        "severity": event.get("severity") or "",
        "outcomeResult": outcome.get("result") or "",
        "outcomeReason": outcome.get("reason") or "",
        "actorId": actor.get("id") or "",
        "actorType": actor.get("type") or "",
        "actorAlternateId": actor_alternate_id,
        "actorDisplayName": actor.get("displayName") or "",
        "clientIpAddress": client_ip,
        "clientUserAgent": _user_agent(client),
        "clientDevice": client.get("device") or "",
        "clientZone": client.get("zone") or "",
        "country": geo.get("country") or "",
        "city": geo.get("city") or "",
        "state": geo.get("state") or "",
        "targetNames": "; ".join([item for item in target_names if item]),
        "targetIds": "; ".join([item for item in target_ids if item]),
        "targetTypes": "; ".join([item for item in target_types if item]),
        "requestUri": debug_data.get("requestUri") or "",
        "rawEvent": event,
    }
