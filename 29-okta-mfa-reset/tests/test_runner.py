from okta_mfa_reset.runner import execute_plan


class FakeClient:
    def get_user(self, user_identifier):
        return {"id": "00uresolved", "status": "ACTIVE", "profile": {"login": "user@example.com", "email": "user@example.com"}}

    def list_factors(self, user_id):
        return [{"id": "factor1", "factorType": "sms", "provider": "OKTA"}]

    def reset_all_factors(self, user_id):
        return {}

    def delete_factor(self, user_id, factor_id):
        return {}


def test_dry_run_would_change():
    plan = {"plannedActions": [{"userId": "00u1", "login": "user@example.com", "email": "user@example.com", "action": "reset_all_factors"}], "skippedRows": []}
    result = execute_plan(plan, FakeClient(), {"verifyUsersBeforeAction": True}, apply=False)
    assert result["summary"]["changedOrWouldChange"] == 1
    assert result["changed"][0]["status"] == "would_change"


def test_apply_delete_factor_by_type():
    plan = {"plannedActions": [{"userId": "00u1", "login": "user@example.com", "email": "user@example.com", "action": "delete_factor", "factorType": "sms", "provider": "OKTA"}], "skippedRows": []}
    result = execute_plan(plan, FakeClient(), {"verifyUsersBeforeAction": True}, apply=True)
    assert result["summary"]["changedOrWouldChange"] == 1
    assert result["changed"][0]["resolvedFactorId"] == "factor1"
