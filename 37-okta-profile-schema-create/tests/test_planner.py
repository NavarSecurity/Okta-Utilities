from types import SimpleNamespace

from okta_profile_schema_create.planner import create_plan


class FakeClient:
    def __init__(self, schema):
        self.schema = schema

    def get_user_schema(self, schema_id="default"):
        return self.schema

    def get_app_schema(self, app_id, schema_id="default"):
        return self.schema

    def find_app_by_name(self, app_name):
        return {"id": "0oa123", "label": app_name}


def settings(on_existing="skip"):
    return SimpleNamespace(
        check_existing=True,
        on_existing=on_existing,
        continue_on_error=True,
        allow_app_schema_updates=True,
        allow_user_schema_updates=True,
    )


def test_create_plan_creates_new_attribute():
    input_data = {
        "attributes": [
            {"targetType": "user", "name": "employeeType", "definition": {"title": "Employee Type", "type": "string"}}
        ]
    }
    plan = create_plan(settings(), input_data, FakeClient({"definitions": {"custom": {"properties": {}}}}))
    assert plan.planned[0].action == "create"
    assert plan.planned[0].status == "planned"


def test_create_plan_skips_existing_attribute():
    input_data = {
        "attributes": [
            {"targetType": "user", "name": "employeeType", "definition": {"title": "Employee Type", "type": "string"}}
        ]
    }
    existing_schema = {"definitions": {"custom": {"properties": {"employeeType": {"type": "string"}}}}}
    plan = create_plan(settings("skip"), input_data, FakeClient(existing_schema))
    assert plan.planned[0].action == "skip"
    assert plan.planned[0].status == "skipped"


def test_create_plan_updates_existing_attribute_when_configured():
    input_data = {
        "attributes": [
            {"targetType": "user", "name": "employeeType", "definition": {"title": "Employee Type", "type": "string"}}
        ]
    }
    existing_schema = {"definitions": {"custom": {"properties": {"employeeType": {"type": "string"}}}}}
    plan = create_plan(settings("update"), input_data, FakeClient(existing_schema))
    assert plan.planned[0].action == "update"
    assert plan.planned[0].status == "planned"


def test_app_name_resolves_to_app_id():
    input_data = {
        "attributes": [
            {"targetType": "app", "appName": "Demo App", "name": "externalRole", "definition": {"title": "External Role", "type": "string"}}
        ]
    }
    plan = create_plan(settings(), input_data, FakeClient({"definitions": {"custom": {"properties": {}}}}))
    assert plan.planned[0].app_id == "0oa123"
