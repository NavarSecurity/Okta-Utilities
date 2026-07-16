import json
from pathlib import Path
from okta_security_event_detector.loader import load_events


def test_load_events_array(tmp_path: Path):
    path = tmp_path / "events.json"
    path.write_text(json.dumps([{"uuid": "1"}, {"uuid": "2"}]), encoding="utf-8")
    assert len(load_events(path)) == 2


def test_load_events_wrapped(tmp_path: Path):
    path = tmp_path / "events.json"
    path.write_text(json.dumps({"events": [{"uuid": "1"}]}), encoding="utf-8")
    assert len(load_events(path)) == 1
