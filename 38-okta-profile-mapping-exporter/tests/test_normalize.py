from okta_profile_mapping_exporter.normalize import mapping_properties, mapping_summary, sources_targets


def sample_mapping():
    return {
        "id": "prm123",
        "source": {"id": "src1", "name": "Okta User", "type": "user"},
        "target": {"id": "target1", "name": "Salesforce User", "type": "appuser"},
        "properties": {
            "email": {"expression": "user.email", "pushStatus": "PUSH"},
            "department": {"expression": "user.department", "pushStatus": "DONT_PUSH"},
        },
    }


def test_mapping_summary_counts_properties():
    summary = mapping_summary(sample_mapping())
    assert summary["id"] == "prm123"
    assert summary["sourceName"] == "Okta User"
    assert summary["targetName"] == "Salesforce User"
    assert summary["propertyCount"] == 2


def test_mapping_properties_flattens_attributes():
    rows = mapping_properties(sample_mapping())
    assert len(rows) == 2
    assert {row["targetAttribute"] for row in rows} == {"email", "department"}
    assert any(row["expression"] == "user.email" for row in rows)


def test_sources_targets_are_distinct():
    rows = sources_targets([sample_mapping(), sample_mapping()])
    assert len(rows) == 2
