from okta_group_create.config import GroupCreateConfig, Settings
from okta_group_create.models import build_group_payload, build_group_specs, validate_specs


def cfg(require_approved=False):
    return GroupCreateConfig(
        target_org_url="https://example.okta.com",
        api_token=None,
        groups_file="groups.csv",
        settings=Settings(require_approved=require_approved),
        columns={"name": "name", "description": "description", "approved": "approved"},
        profile_field_mappings={"name": "name", "description": "description"},
        raw={},
    )


def test_build_payload():
    specs = build_group_specs([{"name": "Test Group", "description": "Desc"}], cfg())
    payload = build_group_payload(specs[0])
    assert payload == {"profile": {"name": "Test Group", "description": "Desc"}}


def test_requires_name():
    specs = build_group_specs([{"name": ""}], cfg())
    valid, skipped = validate_specs(specs, cfg())
    assert valid == []
    assert skipped[0]["reasonCode"] == "MISSING_NAME"


def test_duplicate_input_names():
    rows = [{"name": "Test Group"}, {"name": "test group"}]
    specs = build_group_specs(rows, cfg())
    valid, skipped = validate_specs(specs, cfg())
    assert len(valid) == 1
    assert skipped[0]["reasonCode"] == "DUPLICATE_INPUT_NAME"


def test_require_approved():
    specs = build_group_specs([{"name": "Test Group", "approved": ""}], cfg(True))
    valid, skipped = validate_specs(specs, cfg(True))
    assert not valid
    assert skipped[0]["reasonCode"] == "NOT_APPROVED"
