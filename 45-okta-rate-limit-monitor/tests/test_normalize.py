from okta_rate_limit_monitor.normalize import calculate_remaining_percent, normalize_rate_limit_headers, normalize_system_log_event, operation_endpoint_key


def test_calculate_remaining_percent():
    assert calculate_remaining_percent(100, 25) == 25.0
    assert calculate_remaining_percent(0, 25) is None
    assert calculate_remaining_percent(None, 25) is None


def test_normalize_rate_limit_headers():
    headers = {
        "X-Rate-Limit-Limit": "600",
        "X-Rate-Limit-Remaining": "150",
        "X-Rate-Limit-Reset": "1893456000",
    }
    normalized = normalize_rate_limit_headers(headers)
    assert normalized["rateLimitLimit"] == 600
    assert normalized["rateLimitRemaining"] == 150
    assert normalized["remainingPercent"] == 25.0
    assert "2030" in normalized["rateLimitResetUtc"]


def test_normalize_system_log_event():
    event = {
        "uuid": "abc",
        "published": "2026-07-17T10:00:00.000Z",
        "eventType": "system.org.rate_limit.violation",
        "displayMessage": "Rate limit violation",
        "severity": "ERROR",
        "actor": {"id": "00u1", "alternateId": "admin@example.com", "displayName": "Admin", "type": "User"},
        "client": {"ipAddress": "203.0.113.10", "userAgent": {"rawUserAgent": "pytest"}},
        "debugContext": {"debugData": {"requestUri": "/api/v1/users"}},
        "outcome": {"result": "FAILURE", "reason": "Rate limit violation"},
    }
    row = normalize_system_log_event(event)
    assert row["uuid"] == "abc"
    assert row["actorAlternateId"] == "admin@example.com"
    assert row["requestUri"] == "/api/v1/users"


def test_operation_endpoint_key():
    assert operation_endpoint_key("/api/v1/users?limit=200") == "/api/v1/users"
    assert operation_endpoint_key("/api/v1/users/") == "/api/v1/users"
