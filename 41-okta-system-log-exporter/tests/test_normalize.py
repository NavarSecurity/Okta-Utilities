from okta_system_log_exporter.normalize import actor_summary, event_type_summary, normalize_event, outcome_summary, target_summary


def sample_event():
    return {
        "uuid": "evt-1",
        "published": "2026-07-16T18:30:00.000Z",
        "eventType": "user.authentication.sso",
        "displayMessage": "SSO",
        "severity": "INFO",
        "actor": {
            "id": "00u1",
            "type": "User",
            "alternateId": "jane@example.com",
            "displayName": "Jane Example",
        },
        "client": {"ipAddress": "203.0.113.1", "geographicalContext": {"country": "United States"}},
        "outcome": {"result": "SUCCESS"},
        "transaction": {"id": "txn-1"},
        "target": [{"id": "0oa1", "type": "AppInstance", "displayName": "Test App"}],
    }


def test_normalize_event():
    row = normalize_event(sample_event())
    assert row["uuid"] == "evt-1"
    assert row["eventType"] == "user.authentication.sso"
    assert row["actorAlternateId"] == "jane@example.com"
    assert row["targetCount"] == 1
    assert "Test App" in row["targets"]


def test_summaries():
    events = [sample_event(), sample_event()]
    assert event_type_summary(events)[0]["count"] == 2
    assert actor_summary(events)[0]["actorAlternateId"] == "jane@example.com"
    assert target_summary(events)[0]["targetDisplayName"] == "Test App"
    assert outcome_summary(events)[0]["outcomeResult"] == "SUCCESS"
