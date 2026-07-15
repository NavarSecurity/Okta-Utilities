import pytest

from okta_profile_schema_create.payload import PayloadError, build_schema_payload, get_custom_properties


def test_build_schema_payload_for_string_attribute():
    payload = build_schema_payload("employeeType", {"title": "Employee Type", "type": "string"})
    assert payload["definitions"]["custom"]["properties"]["employeeType"]["title"] == "Employee Type"


def test_invalid_attribute_name_rejected():
    with pytest.raises(PayloadError):
        build_schema_payload("employee-type", {"title": "Employee Type", "type": "string"})


def test_array_defaults_items_to_string():
    payload = build_schema_payload("regions", {"title": "Regions", "type": "array"})
    assert payload["definitions"]["custom"]["properties"]["regions"]["items"]["type"] == "string"


def test_get_custom_properties_handles_missing_sections():
    assert get_custom_properties({}) == {}
