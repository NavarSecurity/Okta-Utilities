import csv

from okta_scope_claim_exporter.exporter import ExportResult
from okta_scope_claim_exporter.output import write_export


def test_write_export_outputs_expected_files(tmp_path):
    result = ExportResult(
        mode="export",
        source_org_url="https://example.okta.com",
        authorization_servers=[
            {"id": "aus1", "name": "Example API", "status": "ACTIVE", "audiences": ["api://example"]}
        ],
        scopes_by_authorization_server_id={
            "aus1": [
                {"id": "scp1", "name": "read:example", "description": "Read", "status": "ACTIVE"}
            ]
        },
        claims_by_authorization_server_id={
            "aus1": [
                {
                    "id": "clm1",
                    "name": "email",
                    "status": "ACTIVE",
                    "claimType": "IDENTITY",
                    "valueType": "EXPRESSION",
                    "value": "user.email",
                    "conditions": {"scopes": {"include": ["openid"]}},
                }
            ]
        },
    )
    write_export(tmp_path, result)
    assert (tmp_path / "scope_claim_export.json").exists()
    assert (tmp_path / "authorization_servers.csv").exists()
    assert (tmp_path / "scopes.csv").exists()
    assert (tmp_path / "claims.csv").exists()
    assert (tmp_path / "scope_claim_report.md").exists()
    with (tmp_path / "scopes.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["authorization_server_name"] == "Example API"
    assert rows[0]["name"] == "read:example"
