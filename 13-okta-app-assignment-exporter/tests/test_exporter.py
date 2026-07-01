from okta_app_assignment_exporter.config import AppSelection, ExportOptions
from okta_app_assignment_exporter.exporter import group_assignment_row, select_apps, user_assignment_row


APPS = [
    {"id": "0oa1", "label": "App One", "name": "oidc_client", "signOnMode": "OPENID_CONNECT", "status": "ACTIVE"},
    {"id": "0oa2", "label": "App Two", "name": "template_saml_2_0", "signOnMode": "SAML_2_0", "status": "ACTIVE"},
    {"id": "0oa3", "label": "Inactive App", "name": "oidc_client", "signOnMode": "OPENID_CONNECT", "status": "INACTIVE"},
]


def test_select_apps_by_label():
    selection = AppSelection(mode="labels", app_labels=["App One"], statuses=["ACTIVE"])
    selected, warnings = select_apps(APPS, selection, ExportOptions())
    assert [app["id"] for app in selected] == ["0oa1"]
    assert warnings == []


def test_select_apps_by_sign_on_mode():
    selection = AppSelection(mode="all", statuses=["ACTIVE"], sign_on_modes=["SAML_2_0"])
    selected, warnings = select_apps(APPS, selection, ExportOptions())
    assert [app["id"] for app in selected] == ["0oa2"]
    assert warnings == []


def test_select_apps_missing_label_warning():
    selection = AppSelection(mode="labels", app_labels=["Does Not Exist"], statuses=["ACTIVE"])
    selected, warnings = select_apps(APPS, selection, ExportOptions())
    assert selected == []
    assert warnings == ["No selected app matched label: Does Not Exist"]


def test_user_assignment_row_uses_safe_fields():
    app = APPS[0]
    assignment = {
        "id": "00u1",
        "credentials": {"userName": "jane@example.com"},
        "profile": {"email": "jane@example.com", "department": "IT", "nested": {"skip": True}},
        "status": "ACTIVE",
        "scope": ["USER"],
    }
    row = user_assignment_row(app, assignment, include_profile=True)
    assert row["appId"] == "0oa1"
    assert row["assignmentType"] == "USER"
    assert row["userName"] == "jane@example.com"
    assert row["userProfile_department"] == "IT"
    assert "userProfile_nested" not in row


def test_group_assignment_row_uses_profile_name():
    app = APPS[1]
    assignment = {"id": "00g1", "profile": {"name": "Finance"}, "priority": 1}
    row = group_assignment_row(app, assignment, include_profile=True)
    assert row["appId"] == "0oa2"
    assert row["assignmentType"] == "GROUP"
    assert row["groupName"] == "Finance"
    assert row["groupProfile_name"] == "Finance"
