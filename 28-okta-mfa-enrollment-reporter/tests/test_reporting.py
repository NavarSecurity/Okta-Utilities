from okta_mfa_enrollment_reporter.reporting import build_user_summary_rows, build_group_summary_rows, build_factor_summary_rows


def test_user_summary_missing_required_factors():
    users = [{"id": "00u1", "status": "ACTIVE", "profile": {"login": "a@example.com", "email": "a@example.com"}}]
    factors = {"00u1": [{"factorType": "push", "status": "ACTIVE"}]}
    rows = build_user_summary_rows(users, factors, {}, ["push", "webauthn"])
    assert rows[0]["has_any_factor"] == "true"
    assert rows[0]["missing_required_factor_types"] == "webauthn"


def test_group_summary():
    rows = [
        {"group_ids": "00g1", "group_names": "Test Group", "has_any_factor": "true", "has_active_factor": "true"},
        {"group_ids": "00g1", "group_names": "Test Group", "has_any_factor": "false", "has_active_factor": "false"},
    ]
    summary = build_group_summary_rows(rows)
    assert summary[0]["total_users"] == 2
    assert summary[0]["users_without_factor"] == 1
    assert summary[0]["coverage_percent"] == 50.0


def test_factor_summary_counts():
    rows = [
        {"factor_type": "push", "provider": "OKTA", "status": "ACTIVE"},
        {"factor_type": "push", "provider": "OKTA", "status": "ACTIVE"},
        {"factor_type": "sms", "provider": "OKTA", "status": "ACTIVE"},
    ]
    summary = build_factor_summary_rows(rows)
    push = [r for r in summary if r["factor_type"] == "push"][0]
    assert push["count"] == 2
