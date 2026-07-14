from okta_profile_schema_exporter.normalize import iter_schema_properties, summarize_schema


def sample_schema():
    return {
        "id": "schema-id",
        "title": "User",
        "type": "object",
        "definitions": {
            "base": {
                "required": ["login"],
                "properties": {
                    "login": {"title": "Username", "type": "string", "mutability": "READ_WRITE"}
                },
            },
            "custom": {
                "properties": {
                    "employeeNumber": {"title": "Employee Number", "type": "string", "unique": True}
                }
            },
        },
    }


def test_iter_schema_properties_extracts_base_and_custom():
    rows = iter_schema_properties(sample_schema())
    assert len(rows) == 2
    assert rows[0]["attributeName"] == "login"
    assert rows[0]["required"] == "true"
    assert rows[1]["attributeName"] == "employeeNumber"
    assert rows[1]["unique"] == "true"


def test_summarize_schema_adds_context():
    rows = summarize_schema("app", sample_schema(), {"appId": "0oa1", "appLabel": "App"})
    assert rows[0]["schemaCategory"] == "app"
    assert rows[0]["appId"] == "0oa1"
    assert rows[0]["appLabel"] == "App"
