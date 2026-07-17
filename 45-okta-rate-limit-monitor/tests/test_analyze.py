from okta_rate_limit_monitor.analyze import estimate_planned_operation_risks, find_header_risks, find_system_log_risks


def test_find_header_risks_low_remaining():
    probes = [
        {"name": "users", "path": "/api/v1/users", "remainingPercent": 8},
        {"name": "apps", "path": "/api/v1/apps", "remainingPercent": 80},
    ]
    findings = find_header_risks(probes, {"remainingPercentCritical": 10, "remainingPercentWarning": 25})
    assert len(findings) == 1
    assert findings[0]["severity"] == "CRITICAL"


def test_find_header_risks_missing_headers():
    findings = find_header_risks([{"name": "logs", "path": "/api/v1/logs", "remainingPercent": None}], {})
    assert findings[0]["category"] == "RATE_LIMIT_HEADERS_MISSING"


def test_find_system_log_risks_violation():
    events = [{"displayMessage": "Rate limit violation", "eventType": "system.org.rate_limit.violation"}]
    findings = find_system_log_risks(events, {"rateLimitEventsCritical": 1})
    assert findings[0]["severity"] == "CRITICAL"


def test_estimate_planned_operation_risks():
    planned = [{"name": "backup", "endpoint": "/api/v1/users", "estimatedRequests": 90, "windowMinutes": 1}]
    probes = [{"path": "/api/v1/users", "rateLimitLimit": 100}]
    estimates, findings = estimate_planned_operation_risks(planned, probes, {"plannedUsagePercentCritical": 90, "plannedUsagePercentWarning": 70})
    assert estimates[0]["estimatedUsagePercent"] == 90.0
    assert findings[0]["severity"] == "CRITICAL"


def test_estimate_unknown_limit():
    planned = [{"name": "backup", "endpoint": "/api/v1/users", "estimatedRequests": 90, "windowMinutes": 1}]
    estimates, findings = estimate_planned_operation_risks(planned, [], {})
    assert estimates[0]["matchedRateLimit"] is None
    assert findings[0]["category"] == "PLANNED_OPERATION_LIMIT_UNKNOWN"
