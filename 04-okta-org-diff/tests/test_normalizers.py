from okta_org_diff.normalizers import normalize_resource_records, natural_key, normalize_for_compare


def test_domains_wrapper_is_flattened():
    data = [{"domains": [{"id": "default", "domain": "example.okta.com"}]}]
    records = normalize_resource_records("domains", data)
    assert len(records) == 1
    assert records[0]["domain"] == "example.okta.com"


def test_policies_are_flattened_from_policy_types():
    data = {
        "policyTypes": {
            "PASSWORD": {
                "policies": [{"id": "00p1", "name": "Default Policy", "type": "PASSWORD"}],
                "rulesByPolicyId": {"00p1": [{"id": "0pr1", "name": "Rule"}]},
            }
        }
    }
    records = normalize_resource_records("policies", data)
    assert len(records) == 1
    assert natural_key("policies", records[0]) == "PASSWORD::Default Policy"
    assert records[0]["_rules"][0]["name"] == "Rule"


def test_compare_normalization_ignores_ids_and_timestamps():
    left = {"id": "1", "name": "A", "lastUpdated": "old"}
    right = {"id": "2", "name": "A", "lastUpdated": "new"}
    assert normalize_for_compare(left, {"id", "lastUpdated"}) == normalize_for_compare(right, {"id", "lastUpdated"})
