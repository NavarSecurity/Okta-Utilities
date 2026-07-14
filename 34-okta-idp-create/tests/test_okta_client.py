from okta_idp_create.okta_client import _parse_next_link, find_existing_by_name


def test_parse_next_link():
    link = '<https://example.okta.com/api/v1/idps?after=abc>; rel="next", <https://example.okta.com/api/v1/idps>; rel="self"'
    assert _parse_next_link(link) == "https://example.okta.com/api/v1/idps?after=abc"


def test_parse_next_link_missing():
    assert _parse_next_link('<https://example.okta.com/api/v1/idps>; rel="self"') is None


def test_find_existing_by_name():
    idps = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
    assert find_existing_by_name(idps, "B")["id"] == "2"
    assert find_existing_by_name(idps, "C") is None
