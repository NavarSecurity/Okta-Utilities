from pathlib import Path

from okta_dormant_user_finder.writer import write_outputs


def test_write_find_outputs(tmp_path):
    result = {
        "mode": "find",
        "sourceMode": "file",
        "orgUrl": "https://example.okta.com",
        "counts": {"usersAnalyzed": 1, "dormantCandidates": 1, "nonDormantUsers": 0},
        "summaryByReason": {"NEVER_LOGGED_IN": 1},
        "warnings": [],
        "dormantUsers": [{"id": "1", "login": "a@example.com", "isDormantCandidate": True, "reasons": "NEVER_LOGGED_IN"}],
        "allUsersAnalyzed": [{"id": "1", "login": "a@example.com", "isDormantCandidate": True, "reasons": "NEVER_LOGGED_IN"}],
    }
    write_outputs(result, tmp_path)
    assert (tmp_path / "dormant_users.csv").exists()
    assert (tmp_path / "dormant_user_report.md").exists()
    assert (tmp_path / "execution_report.md").exists()
