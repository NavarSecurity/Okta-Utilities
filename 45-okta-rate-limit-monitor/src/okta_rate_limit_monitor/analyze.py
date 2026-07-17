from __future__ import annotations

from typing import Any

from .normalize import operation_endpoint_key


def threshold(config: dict[str, Any], key: str, default: int | float) -> int | float:
    value = config.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


def find_header_risks(probes: list[dict[str, Any]], risk_thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    warning = float(threshold(risk_thresholds, "remainingPercentWarning", 25))
    critical = float(threshold(risk_thresholds, "remainingPercentCritical", 10))
    findings: list[dict[str, Any]] = []
    for probe in probes:
        remaining_percent = probe.get("remainingPercent")
        if remaining_percent is None:
            findings.append({
                "severity": "INFO",
                "category": "RATE_LIMIT_HEADERS_MISSING",
                "objectName": probe.get("name", ""),
                "endpoint": probe.get("path", ""),
                "message": "The probe response did not include rate-limit headers or the headers could not be parsed.",
            })
            continue
        if remaining_percent <= critical:
            severity = "CRITICAL"
        elif remaining_percent <= warning:
            severity = "WARNING"
        else:
            continue
        findings.append({
            "severity": severity,
            "category": "LOW_REMAINING_RATE_LIMIT",
            "objectName": probe.get("name", ""),
            "endpoint": probe.get("path", ""),
            "message": f"Remaining rate-limit capacity is {remaining_percent}% for this endpoint bucket.",
        })
    return findings


def find_system_log_risks(events: list[dict[str, Any]], risk_thresholds: dict[str, Any]) -> list[dict[str, Any]]:
    if not events:
        return []
    critical_count = int(threshold(risk_thresholds, "rateLimitEventsCritical", 1))
    warning_count = int(threshold(risk_thresholds, "rateLimitEventsWarning", 1))
    count = len(events)
    has_violation = any("violation" in str(event.get("displayMessage", "")).lower() or "violation" in str(event.get("eventType", "")).lower() for event in events)
    if has_violation and count >= critical_count:
        severity = "CRITICAL"
    elif count >= warning_count:
        severity = "WARNING"
    else:
        severity = "INFO"
    return [{
        "severity": severity,
        "category": "RATE_LIMIT_SYSTEM_LOG_EVENTS",
        "objectName": "System Log",
        "endpoint": "/api/v1/logs",
        "message": f"Found {count} rate-limit warning or violation events in the configured lookback window.",
    }]


def estimate_planned_operation_risks(
    planned_operations: list[dict[str, Any]],
    probe_results: list[dict[str, Any]],
    risk_thresholds: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warning = float(threshold(risk_thresholds, "plannedUsagePercentWarning", 70))
    critical = float(threshold(risk_thresholds, "plannedUsagePercentCritical", 90))
    endpoint_limits: dict[str, int] = {}
    for probe in probe_results:
        key = operation_endpoint_key(str(probe.get("path", "")))
        limit = probe.get("rateLimitLimit")
        if key and isinstance(limit, int) and limit > 0:
            endpoint_limits[key] = limit

    estimates: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for operation in planned_operations:
        endpoint = operation_endpoint_key(str(operation.get("endpoint", "")))
        estimated_requests = int(operation.get("estimatedRequests", 0) or 0)
        window_minutes = int(operation.get("windowMinutes", 1) or 1)
        per_minute_estimate = estimated_requests / max(window_minutes, 1)
        matched_limit = endpoint_limits.get(endpoint)
        usage_percent = round((per_minute_estimate / matched_limit) * 100, 2) if matched_limit else None
        estimate = {
            "name": operation.get("name", ""),
            "endpoint": endpoint,
            "estimatedRequests": estimated_requests,
            "windowMinutes": window_minutes,
            "estimatedRequestsPerMinute": round(per_minute_estimate, 2),
            "matchedRateLimit": matched_limit,
            "estimatedUsagePercent": usage_percent,
        }
        estimates.append(estimate)
        if usage_percent is None:
            findings.append({
                "severity": "INFO",
                "category": "PLANNED_OPERATION_LIMIT_UNKNOWN",
                "objectName": operation.get("name", ""),
                "endpoint": endpoint,
                "message": "No matching probe rate-limit limit was available for this planned operation endpoint.",
            })
        elif usage_percent >= critical:
            findings.append({
                "severity": "CRITICAL",
                "category": "PLANNED_OPERATION_RATE_LIMIT_RISK",
                "objectName": operation.get("name", ""),
                "endpoint": endpoint,
                "message": f"Estimated planned request volume is {usage_percent}% of the observed per-minute bucket limit.",
            })
        elif usage_percent >= warning:
            findings.append({
                "severity": "WARNING",
                "category": "PLANNED_OPERATION_RATE_LIMIT_RISK",
                "objectName": operation.get("name", ""),
                "endpoint": endpoint,
                "message": f"Estimated planned request volume is {usage_percent}% of the observed per-minute bucket limit.",
            })
    return estimates, findings
