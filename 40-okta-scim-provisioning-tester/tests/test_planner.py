from okta_scim_provisioning_tester.planner import build_plan, replace_tokens


def sample_plan():
    return {
        "testUser": {"userName": "test@example.com"},
        "updateUser": {"title": "Updated"},
        "group": {"displayName": "Test Group"},
    }


def test_build_plan_includes_core_operations():
    operations = {
        "serviceProviderConfig": True,
        "schemas": True,
        "resourceTypes": True,
        "createUser": True,
        "updateUser": True,
        "deactivateUser": True,
        "createGroup": True,
        "groupPush": True,
        "cleanup": False,
    }
    plan = build_plan(operations, sample_plan())
    names = [item["name"] for item in plan]
    assert names == [
        "serviceProviderConfig",
        "schemas",
        "resourceTypes",
        "createUser",
        "updateUser",
        "deactivateUser",
        "createGroup",
        "groupPush",
    ]


def test_replace_tokens_nested_payload():
    payload = {"path": "/Users/{userId}", "members": [{"value": "{userId}"}]}
    result = replace_tokens(payload, {"userId": "abc123"})
    assert result["path"] == "/Users/abc123"
    assert result["members"][0]["value"] == "abc123"
