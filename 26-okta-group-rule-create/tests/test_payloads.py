from okta_group_rule_create.config import GroupRuleConfig
from okta_group_rule_create.payloads import build_group_rule_payload


def test_build_group_rule_payload_shape():
    rule = GroupRuleConfig(
        name="Rule - Engineering",
        description="Engineering rule",
        approved=True,
        expression='user.department == "Engineering"',
        target_group_ids=["00g123"],
        exclude_user_ids=["00u123"],
        exclude_group_ids=["00gexclude"],
    )
    payload = build_group_rule_payload(rule, ["00g123"])
    assert payload["type"] == "group_rule"
    assert payload["status"] == "INACTIVE"
    assert payload["conditions"]["expression"]["type"] == "urn:okta:expression:1.0"
    assert payload["conditions"]["expression"]["value"] == 'user.department == "Engineering"'
    assert payload["actions"]["assignUserToGroups"]["groupIds"] == ["00g123"]
    assert payload["conditions"]["people"]["users"]["exclude"] == ["00u123"]


def test_build_group_rule_payload_accepts_basic_condition_resolved_expression():
    rule = GroupRuleConfig(
        name="Rule - Basic Department",
        description="Basic condition rule",
        approved=True,
        expression='user.department == "Engineering"',
        condition_source="basicCondition",
        basic_condition={"attribute": "department", "operator": "equals", "value": "Engineering"},
        target_group_ids=["00g123"],
    )
    payload = build_group_rule_payload(rule, ["00g123"])
    assert payload["conditions"]["expression"]["value"] == 'user.department == "Engineering"'
