from okta_api_access_auditor.config import Config
from okta_api_access_auditor.exporter import ApiAccessAuditor


class DummyClient:
    pass


def test_high_risk_scope_and_role_findings():
    auditor = ApiAccessAuditor(DummyClient(), Config())
    apps = [{"appId": "0oa1", "label": "Svc", "clientId": "cid", "applicationType": "service", "grantTypes": "client_credentials", "lastUpdated": "2026-01-01T00:00:00.000Z"}]
    grants = [{"appId": "0oa1", "appLabel": "Svc", "clientId": "cid", "scope": "okta.users.manage"}]
    roles = [{"appId": "0oa1", "appLabel": "Svc", "clientId": "cid", "roleType": "SUPER_ADMIN"}]
    findings = auditor._build_findings([], apps, grants, roles)
    codes = {f["findingCode"] for f in findings}
    assert "HIGH_RISK_OAUTH_SCOPE" in codes
    assert "HIGH_RISK_CLIENT_ADMIN_ROLE" in codes


def test_api_token_network_finding():
    auditor = ApiAccessAuditor(DummyClient(), Config())
    tokens = [{"tokenId": "tok", "name": "Token", "networkConnection": "ANYWHERE", "created": "2026-01-01T00:00:00.000Z", "lastUsed": "2026-01-01T00:00:00.000Z"}]
    findings = auditor._build_findings(tokens, [], [], [])
    assert any(f["findingCode"] == "API_TOKEN_BROAD_NETWORK" for f in findings)
