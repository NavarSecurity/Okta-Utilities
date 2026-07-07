import csv
import json
from pathlib import Path

from okta_group_membership_loader.config import LoaderConfig
from okta_group_membership_loader.inputs import read_membership_requests


def test_reads_csv(tmp_path):
    csv_path = tmp_path / "members.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["groupId", "userId", "action", "approved", "reason"])
        writer.writeheader()
        writer.writerow({"groupId": "g1", "userId": "u1", "action": "add", "approved": "true", "reason": "approved"})
    cfg = LoaderConfig("https://example.okta.com", str(csv_path))
    rows = read_membership_requests(cfg)
    assert len(rows) == 1
    assert rows[0].group_id == "g1"


def test_reads_json(tmp_path):
    p = tmp_path / "members.json"
    p.write_text(json.dumps({"memberships": [{"groupId": "g1", "userId": "u1", "approved": "true", "reason": "approved"}]}))
    cfg = LoaderConfig("https://example.okta.com", str(p))
    rows = read_membership_requests(cfg)
    assert rows[0].action == "add"
