from okta_security_event_detector.normalize import normalize_event


def test_normalize_event_extracts_core_fields():
    event = {
        "uuid": "abc",
        "published": "2026-01-01T00:00:00.000Z",
        "eventType": "policy.lifecycle.update",
        "outcome": {"result": "SUCCESS"},
        "actor": {"alternateId": "admin@example.com", "displayName": "Admin"},
        "client": {
            "ipAddress": "1.2.3.4",
            "geographicalContext": {"country": "United States"},
            "userAgent": {"rawUserAgent": "Agent"},
        },
        "target": [{"id": "t1", "displayName": "Target", "type": "Policy"}],
    }
    normalized = normalize_event(event)
    assert normalized["uuid"] == "abc"
    assert normalized["actorAlternateId"] == "admin@example.com"
    assert normalized["clientIpAddress"] == "1.2.3.4"
    assert normalized["country"] == "United States"
    assert normalized["targetNames"] == "Target"
