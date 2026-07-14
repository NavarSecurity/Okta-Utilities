from okta_profile_schema_exporter.config import ExportConfig
from okta_profile_schema_exporter.exporter import _select_apps, _split_exportable_apps


def test_split_exportable_apps_skips_known_okta_system_apps_by_default():
    config = ExportConfig()
    apps = [
        {"id": "0oa-admin", "label": "Okta Admin Console", "name": "saasure", "status": "ACTIVE"},
        {"id": "0oa-plugin", "label": "Okta Browser Plugin", "name": "okta_browser_plugin", "status": "ACTIVE"},
        {"id": "0oa-custom", "label": "Example SAML App", "name": "integrator_example", "status": "ACTIVE"},
    ]

    exportable, skipped = _split_exportable_apps(config, apps)

    assert [app["id"] for app in exportable] == ["0oa-custom"]
    assert [app["id"] for app in skipped] == ["0oa-admin", "0oa-plugin"]


def test_split_exportable_apps_can_be_disabled():
    config = ExportConfig(skip_okta_system_apps=False)
    apps = [
        {"id": "0oa-admin", "label": "Okta Admin Console", "name": "saasure", "status": "ACTIVE"},
        {"id": "0oa-custom", "label": "Example SAML App", "name": "integrator_example", "status": "ACTIVE"},
    ]

    exportable, skipped = _split_exportable_apps(config, apps)

    assert [app["id"] for app in exportable] == ["0oa-admin", "0oa-custom"]
    assert skipped == []


def test_select_apps_all_uses_exportable_apps_only():
    config = ExportConfig()
    apps = [
        {"id": "0oa-custom", "label": "Example SAML App", "name": "integrator_example", "status": "ACTIVE"},
    ]

    selected = _select_apps(config, apps)

    assert selected == apps
