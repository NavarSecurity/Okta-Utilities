from pathlib import Path
from okta_app_provisioning_exporter.normalize import (
    flatten_mapping_properties,
    flatten_schema_attributes,
    mapping_involves_app,
    provisioning_feature_rows,
    is_feature_not_applicable,
    select_apps,
    should_skip_app,
)


def test_should_skip_inactive():
    skip, reason = should_skip_app({"status":"INACTIVE", "name":"x"}, False, True, [])
    assert skip is True
    assert reason == "inactive_app"


def test_should_skip_system_app():
    skip, reason = should_skip_app({"status":"ACTIVE", "name":"okta_enduser", "label":"Okta Dashboard"}, False, True, ["okta_enduser"])
    assert skip is True
    assert reason == "okta_system_or_internal_app"


def test_select_apps_by_names():
    apps = [{"id":"1", "name":"salesforce", "label":"Salesforce"}, {"id":"2", "name":"workday", "label":"Workday"}]
    selected, skipped = select_apps(apps, "names", [], ["Salesforce"], "unused")
    assert len(selected) == 1
    assert selected[0]["name"] == "salesforce"
    assert len(skipped) == 1


def test_select_apps_by_file(tmp_path):
    app_file = tmp_path / "apps.txt"
    app_file.write_text("# comment\nWorkday\n", encoding="utf-8")
    apps = [{"id":"1", "name":"salesforce", "label":"Salesforce"}, {"id":"2", "name":"workday", "label":"Workday"}]
    selected, _ = select_apps(apps, "file", [], [], str(app_file))
    assert len(selected) == 1
    assert selected[0]["label"] == "Workday"


def test_feature_rows():
    rows = provisioning_feature_rows({"id":"1", "name":"app", "label":"App"}, [{"name":"PUSH_NEW_USERS"}, {"name":"OTHER"}])
    assert any(row["feature"] == "PUSH_NEW_USERS" and row["isProvisioningRelated"] for row in rows)


def test_flatten_schema_attributes():
    app = {"id":"1", "name":"app", "label":"App"}
    schema = {"definitions":{"custom":{"properties":{"externalRole":{"title":"External Role", "type":"string"}}}}}
    rows = flatten_schema_attributes(app, schema)
    assert rows[0]["attribute"] == "externalRole"


def test_mapping_filter_and_flatten():
    mapping = {"id":"m1", "source":{"id":"user", "name":"user", "type":"user"}, "target":{"id":"app1", "name":"app", "type":"appuser"}, "properties":{"email":{"expression":"user.email", "pushStatus":"PUSH"}}}
    assert mapping_involves_app(mapping, {"app1"}) is True
    rows = flatten_mapping_properties(mapping)
    assert rows[0]["targetAttribute"] == "email"


def test_feature_not_applicable_for_provisioning_not_supported():
    payload = {"errorSummary": "Provisioning is not supported."}
    assert is_feature_not_applicable(400, payload, '{"errorSummary":"Provisioning is not supported."}') is True


def test_feature_not_applicable_false_for_other_errors():
    payload = {"errorSummary": "You do not have permission to access the requested resource."}
    assert is_feature_not_applicable(403, payload, "Forbidden") is False
