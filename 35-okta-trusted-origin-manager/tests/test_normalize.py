from okta_trusted_origin_manager.normalize import canonical_origin_url, extract_trusted_origins, scope_types, to_okta_payload


def test_extract_trusted_origins_from_container():
    payload = {"trustedOrigins": [{"name": "A"}]}
    assert extract_trusted_origins(payload) == [{"name": "A"}]


def test_scope_types_sorted_and_uppercase():
    origin = {"scopes": [{"type": "redirect"}, {"type": "CORS"}, {"type": "CORS"}]}
    assert scope_types(origin) == ["CORS", "REDIRECT"]


def test_canonical_origin_url_removes_path_and_lowercases_host():
    assert canonical_origin_url("HTTPS://App.Example.COM/callback?x=1") == "https://app.example.com"


def test_to_okta_payload_keeps_supported_shape():
    payload = to_okta_payload({"name": "App", "origin": "https://app.example.com", "scopes": ["CORS", {"type": "REDIRECT"}]})
    assert payload == {
        "name": "App",
        "origin": "https://app.example.com",
        "scopes": [{"type": "CORS"}, {"type": "REDIRECT"}],
    }
