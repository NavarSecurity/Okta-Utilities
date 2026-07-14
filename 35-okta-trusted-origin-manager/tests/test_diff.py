from okta_trusted_origin_manager.diff import compare_trusted_origins


def test_compare_detects_missing_extra_and_modified():
    source = {
        "trustedOrigins": [
            {"name": "A", "origin": "https://a.example.com", "status": "ACTIVE", "scopes": [{"type": "CORS"}]},
            {"name": "B", "origin": "https://b.example.com", "status": "ACTIVE", "scopes": [{"type": "REDIRECT"}]},
        ]
    }
    target = {
        "trustedOrigins": [
            {"name": "A", "origin": "https://a.example.com", "status": "ACTIVE", "scopes": [{"type": "REDIRECT"}]},
            {"name": "C", "origin": "https://c.example.com", "status": "ACTIVE", "scopes": [{"type": "CORS"}]},
        ]
    }
    result = compare_trusted_origins(source, target)
    assert result["summary"]["missingInTarget"] == 1
    assert result["summary"]["extraInTarget"] == 1
    assert result["summary"]["modified"] == 1
    assert result["summary"]["totalDifferences"] == 3
