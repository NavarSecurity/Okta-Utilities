import unittest

from okta_network_zone_manager.okta_client import parse_next_link


class OktaClientTests(unittest.TestCase):
    def test_parse_next_link(self):
        link = '<https://example.okta.com/api/v1/zones?after=abc>; rel="next", <https://example.okta.com/api/v1/zones>; rel="self"'
        self.assertEqual(parse_next_link(link), "https://example.okta.com/api/v1/zones?after=abc")

    def test_parse_next_link_empty(self):
        self.assertIsNone(parse_next_link(""))


if __name__ == "__main__":
    unittest.main()
