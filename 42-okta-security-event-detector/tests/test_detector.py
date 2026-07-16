from okta_security_event_detector.detector import detect


def base_event(uuid, event_type, actor="a@example.com", ip="1.1.1.1", country="United States", outcome="SUCCESS"):
    return {
        "uuid": uuid,
        "published": "2026-01-01T00:00:00.000Z",
        "eventType": event_type,
        "displayMessage": event_type,
        "outcomeResult": outcome,
        "outcomeReason": "",
        "actorAlternateId": actor,
        "actorDisplayName": actor,
        "clientIpAddress": ip,
        "country": country,
        "targetNames": "",
        "rawEvent": {},
    }


def test_detect_policy_change():
    config = {"detections": {"policyChanges": {"enabled": True, "severity": "high"}}, "includeLowSeverity": True}
    findings = detect([base_event("1", "policy.lifecycle.update")], config)
    assert any(f["ruleId"] == "POLICY_CONFIGURATION_CHANGE" for f in findings)


def test_detect_failed_signin_spike():
    config = {
        "detections": {"failedSignInSpike": {"enabled": True, "threshold": 2, "severity": "medium"}},
        "includeLowSeverity": True,
    }
    events = [
        base_event("1", "user.authentication.failed", outcome="FAILURE"),
        base_event("2", "user.authentication.failed", outcome="FAILURE"),
    ]
    findings = detect(events, config)
    assert any(f["ruleId"] == "FAILED_SIGN_IN_SPIKE_BY_ACTOR" for f in findings)


def test_detect_suspicious_country():
    config = {
        "detections": {"suspiciousCountry": {"enabled": True, "allowedCountries": ["United States"], "severity": "medium"}},
        "includeLowSeverity": True,
    }
    findings = detect([base_event("1", "user.session.start", country="Canada")], config)
    assert any(f["ruleId"] == "SUSPICIOUS_COUNTRY" for f in findings)
