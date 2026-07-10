import unittest

from okta_network_zone_manager.normalize import normalize_for_compare, prepare_zone_payload, zone_key


class NormalizeTests(unittest.TestCase):
    def test_prepare_zone_payload_removes_read_only_fields(self):
        zone = {
            "id": "nzo123",
            "name": "Corporate",
            "type": "IP",
            "created": "2024-01-01T00:00:00Z",
            "lastUpdated": "2024-01-02T00:00:00Z",
            "_links": {"self": {}},
            "gateways": [{"type": "CIDR", "value": "203.0.113.0/24"}],
        }
        payload = prepare_zone_payload(zone)
        self.assertNotIn("id", payload)
        self.assertNotIn("created", payload)
        self.assertNotIn("lastUpdated", payload)
        self.assertNotIn("_links", payload)
        self.assertEqual(payload["name"], "Corporate")

    def test_normalize_ignores_read_only_fields(self):
        left = {"id": "1", "name": "Zone", "gateways": [{"value": "1.1.1.1", "type": "RANGE"}]}
        right = {"id": "2", "name": "Zone", "gateways": [{"type": "RANGE", "value": "1.1.1.1"}]}
        self.assertEqual(normalize_for_compare(left), normalize_for_compare(right))

    def test_zone_key_is_case_insensitive(self):
        self.assertEqual(zone_key({"name": "Corporate Office"}), "corporate office")


if __name__ == "__main__":
    unittest.main()
