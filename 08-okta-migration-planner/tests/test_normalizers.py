from okta_migration_planner.normalizers import natural_key, normalize_resource


def test_normalize_wrapped_authorization_servers():
    data = [{"authorizationServers": [{"id": "aus1", "name": "API"}], "detailsByAuthorizationServerId": {}}]
    records = normalize_resource("authorization_servers", data)
    assert len(records) == 1
    assert records[0]["name"] == "API"


def test_normalize_policies_flattens_policy_types():
    data = {
        "policyTypes": {
            "PASSWORD": {
                "errors": [],
                "policies": [{"id": "p1", "name": "Default Policy"}],
                "rulesByPolicyId": {},
            }
        }
    }
    records = normalize_resource("policies", data)
    assert len(records) == 1
    assert records[0]["_migrationPolicyType"] == "PASSWORD"
    assert natural_key("policies", records[0]) == "PASSWORD::Default Policy"


def test_natural_key_group_profile_name():
    item = {"id": "00g1", "profile": {"name": "Finance"}}
    assert natural_key("groups", item) == "Finance"


def test_domains_wrapper_normalized():
    data = [{"domains": [{"id": "default", "domain": "example.okta.com"}]}]
    records = normalize_resource("domains", data)
    assert len(records) == 1
    assert natural_key("domains", records[0]) == "example.okta.com"
