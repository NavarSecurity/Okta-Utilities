from okta_security_event_detector.reports import build_summary


def test_build_summary():
    summary = build_summary([{}], [{}], [{"severity": "high", "ruleId": "R1", "actor": "a"}], [])
    assert summary["eventsLoaded"] == 1
    assert summary["detections"] == 1
    assert summary["highestSeverity"] == "high"
