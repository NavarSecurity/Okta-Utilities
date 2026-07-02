from okta_scope_claim_exporter.config import ExportConfig, ExportFilters, ExportSettings
from okta_scope_claim_exporter.exporter import ScopeClaimExporter


def make_config(**kwargs):
    settings = kwargs.pop("settings", ExportSettings())
    filters = kwargs.pop("filters", ExportFilters())
    return ExportConfig(
        source_org_url="https://example.okta.com",
        output_dir=kwargs.pop("output_dir", None) or __import__("pathlib").Path("output"),
        settings=settings,
        filters=filters,
        api_token="token",
    )


def test_build_plan_does_not_call_api():
    exporter = ScopeClaimExporter(make_config())
    plan = exporter.build_plan()
    assert plan["apiCallsWillBeMade"] is False
    assert "List custom authorization servers" in plan["plannedActions"]


def test_filter_includes_by_name():
    cfg = make_config(filters=ExportFilters(authorization_server_names=["Keep Me"]))
    exporter = ScopeClaimExporter(cfg)
    assert exporter._should_include_server({"id": "aus1", "name": "Keep Me", "status": "ACTIVE"}) is True
    assert exporter._should_include_server({"id": "aus2", "name": "Skip Me", "status": "ACTIVE"}) is False


def test_filter_excludes_inactive_when_configured():
    cfg = make_config(settings=ExportSettings(include_inactive_authorization_servers=False))
    exporter = ScopeClaimExporter(cfg)
    assert exporter._should_include_server({"id": "aus1", "name": "Active", "status": "ACTIVE"}) is True
    assert exporter._should_include_server({"id": "aus2", "name": "Inactive", "status": "INACTIVE"}) is False


def test_filter_excludes_by_id():
    cfg = make_config(filters=ExportFilters(exclude_authorization_server_ids=["aus2"]))
    exporter = ScopeClaimExporter(cfg)
    assert exporter._should_include_server({"id": "aus1", "name": "One", "status": "ACTIVE"}) is True
    assert exporter._should_include_server({"id": "aus2", "name": "Two", "status": "ACTIVE"}) is False
