from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from .analyze import estimate_planned_operation_risks, find_header_risks, find_system_log_risks
from .config import MonitorConfig
from .normalize import normalize_rate_limit_headers, normalize_system_log_event, summarize_event_counts
from .okta_client import OktaClient, RequestFailure
from .redact import redact


def iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_failure_from_error(error: Exception, endpoint: str, context: str) -> RequestFailure:
    if isinstance(error, requests.HTTPError) and error.response is not None:
        return RequestFailure(endpoint=endpoint, status_code=error.response.status_code, message=str(error), context=context)
    return RequestFailure(endpoint=endpoint, status_code=None, message=str(error), context=context)


def run_header_probes(client: OktaClient, config: MonitorConfig) -> tuple[list[dict[str, Any]], list[RequestFailure]]:
    results: list[dict[str, Any]] = []
    failures: list[RequestFailure] = []
    for endpoint in config.probe_endpoints:
        name = str(endpoint.get("name", ""))
        path = str(endpoint.get("path", ""))
        params = endpoint.get("params", {}) or {}
        try:
            response = client.get_response(path, params=params)
            header_data = normalize_rate_limit_headers(dict(response.headers))
            results.append({
                "name": name,
                "method": "GET",
                "path": path,
                "statusCode": response.status_code,
                "rateLimitLimit": header_data["rateLimitLimit"],
                "rateLimitRemaining": header_data["rateLimitRemaining"],
                "rateLimitResetEpoch": header_data["rateLimitResetEpoch"],
                "rateLimitResetUtc": header_data["rateLimitResetUtc"],
                "remainingPercent": header_data["remainingPercent"],
            })
        except Exception as exc:
            failure = request_failure_from_error(exc, path, f"header probe: {name}")
            failures.append(failure)
            if not config.continue_on_request_error:
                raise
    return results, failures


def fetch_system_log_rate_limit_events(client: OktaClient, config: MonitorConfig) -> tuple[list[dict[str, Any]], list[RequestFailure]]:
    failures: list[RequestFailure] = []
    events_by_uuid: dict[str, dict[str, Any]] = {}
    until = datetime.now(timezone.utc)
    since = until - timedelta(hours=config.lookback_hours)
    base_params = {
        "since": iso_utc(since),
        "until": iso_utc(until),
        "limit": "200",
        "sortOrder": "ASCENDING",
    }
    filters = config.system_log_filters or [
        "displayMessage eq \"Rate limit warning\"",
        "displayMessage eq \"Rate limit violation\"",
    ]
    for filter_expression in filters:
        params = base_params.copy()
        params["filter"] = filter_expression
        try:
            raw_events = client.get_paged("/api/v1/logs", params=params)
            for event in raw_events:
                if isinstance(event, dict):
                    key = str(event.get("uuid") or f"{event.get('published')}-{event.get('eventType')}-{len(events_by_uuid)}")
                    events_by_uuid[key] = event
        except Exception as exc:
            failure = request_failure_from_error(exc, "/api/v1/logs", f"system log filter: {filter_expression}")
            failures.append(failure)
            if not config.continue_on_request_error:
                raise
    normalized = [normalize_system_log_event(event) for event in events_by_uuid.values()]
    normalized.sort(key=lambda item: str(item.get("published", "")))
    return normalized, failures


def run_monitor(client: OktaClient, config: MonitorConfig) -> dict[str, Any]:
    request_failures: list[RequestFailure] = []
    header_probes: list[dict[str, Any]] = []
    system_log_events: list[dict[str, Any]] = []
    planned_estimates: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    if config.include_header_probes:
        header_probes, failures = run_header_probes(client, config)
        request_failures.extend(failures)
        findings.extend(find_header_risks(header_probes, config.risk_thresholds))

    if config.include_system_log_events:
        system_log_events, failures = fetch_system_log_rate_limit_events(client, config)
        request_failures.extend(failures)
        findings.extend(find_system_log_risks(system_log_events, config.risk_thresholds))

    if config.include_planned_operation_estimate:
        planned_estimates, planned_findings = estimate_planned_operation_risks(
            config.planned_operations,
            header_probes,
            config.risk_thresholds,
        )
        findings.extend(planned_findings)

    failures_as_dicts = [failure.__dict__ for failure in request_failures]

    result = {
        "headerProbes": header_probes,
        "systemLogEvents": system_log_events,
        "systemLogEventCounts": summarize_event_counts(system_log_events),
        "plannedOperationEstimates": planned_estimates,
        "riskFindings": findings,
        "requestFailures": failures_as_dicts,
    }
    return redact(result) if config.redact_sensitive_values else result
