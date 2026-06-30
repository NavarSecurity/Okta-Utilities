from okta_hcl_generator.normalizers import normalize_authorization_servers, normalize_policies


def test_normalize_authorization_server_wrapper():
    servers, details = normalize_authorization_servers({
        "authorizationServers": [{"id": "aus1", "name": "API"}],
        "detailsByAuthorizationServerId": {"aus1": {"scopes": []}},
    })
    assert len(servers) == 1
    assert servers[0]["name"] == "API"
    assert "aus1" in details


def test_normalize_policies_from_policy_types():
    policies = normalize_policies({
        "policyTypes": {
            "PASSWORD": {
                "policies": [{"id": "p1", "name": "Default"}],
                "errors": [],
            }
        }
    })
    assert len(policies) == 1
    assert policies[0]["type"] == "PASSWORD"
