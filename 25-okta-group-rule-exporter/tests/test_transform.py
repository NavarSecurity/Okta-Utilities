from okta_group_rule_exporter.transform import condition_rows, filter_rules, rule_summary_row, target_group_rows


def sample_rule():
    return {
        "id": "0pr123",
        "name": "Engineering Rule",
        "status": "ACTIVE",
        "priority": 1,
        "conditions": {
            "expression": {"type": "urn:okta:expression:1.0", "value": "user.department==\"Engineering\""},
            "groupMembership": {"include": ["00gsource"], "exclude": []},
            "people": {"users": {"exclude": ["00u1"]}},
        },
        "actions": {"assignUserToGroups": {"groupIds": ["00gtarget"]}},
        "_embedded": {"groupIdToGroupName": {"00gtarget": "Engineering Users"}},
    }


def test_filter_rules_status_name_and_id():
    rules = [sample_rule(), {"id": "0pr456", "name": "Other", "status": "INACTIVE"}]
    assert len(filter_rules(rules, ["0pr123"], ["ACTIVE"], "engineer")) == 1
    assert len(filter_rules(rules, [], ["ACTIVE"], "missing")) == 0


def test_summary_row_flattens_targets_and_expression():
    row = rule_summary_row(sample_rule())
    assert row["expressionValue"] == 'user.department=="Engineering"'
    assert row["targetGroupIds"] == "00gtarget"
    assert row["targetGroupNames"] == "Engineering Users"


def test_condition_rows_extract_expression_group_and_user_exclusions():
    rows = condition_rows(sample_rule())
    types = {r["conditionType"] for r in rows}
    assert "expression" in types
    assert "groupMembership" in types
    assert "people.users" in types


def test_target_group_rows_maps_group_names():
    rows = target_group_rows(sample_rule())
    assert rows[0]["targetGroupId"] == "00gtarget"
    assert rows[0]["targetGroupName"] == "Engineering Users"
