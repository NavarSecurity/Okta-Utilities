from okta_hcl_generator.hcl import safe_name, hcl_list


def test_safe_name_normalizes_for_terraform():
    assert safe_name("Customer Portal OIDC") == "customer_portal_oidc"
    assert safe_name("123 App") == "r_123_app"
    assert safe_name("A---B") == "a_b"


def test_hcl_list_quotes_values():
    assert hcl_list(["a", "b"]) == '["a", "b"]'
    assert hcl_list([]) == "[]"
