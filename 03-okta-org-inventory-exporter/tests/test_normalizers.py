from okta_org_inventory_exporter.normalizers import load_records, inventory_rows


def test_domains_wrapper_normalizes():
    data = [{"domains": [{"id": "default", "domain": "example.okta.com"}]}]
    records = load_records("domains", data)
    assert len(records) == 1
    assert records[0]["domain"] == "example.okta.com"


def test_policies_nested_policy_types_count_all_policies():
    data = {
        "policyTypes": {
            "OKTA_SIGN_ON": {"policies": [{"id": "p1", "name": "SignOn", "type": "OKTA_SIGN_ON"}], "rulesByPolicyId": {"p1": [{"id": "r1"}]}},
            "PASSWORD": {"policies": [{"id": "p2", "name": "Password", "type": "PASSWORD"}], "rulesByPolicyId": {"p2": [{"id": "r2"}, {"id": "r3"}]}},
        }
    }
    records = load_records("policies", data)
    assert len(records) == 2
    by_id = {r["id"]: r for r in records}
    assert by_id["p1"]["policyType"] == "OKTA_SIGN_ON"
    assert by_id["p2"]["ruleCount"] == 2


def test_application_row_extracts_redirect_count_and_grants():
    rows, fields = inventory_rows("applications", [{"id": "a1", "label": "App", "settings": {"oauthClient": {"redirect_uris": ["https://a"], "grant_types": ["authorization_code"]}}}])
    assert rows[0]["redirectUriCount"] == 1
    assert rows[0]["grantTypes"] == "authorization_code"
    assert "label" in fields
