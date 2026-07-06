from okta_user_bulk_importer.okta_client import OktaClient


def test_client_sets_headers():
    client = OktaClient("https://example.okta.com", "token")
    assert client.session.headers["Authorization"] == "SSWS token"
    assert client.org_url == "https://example.okta.com"
