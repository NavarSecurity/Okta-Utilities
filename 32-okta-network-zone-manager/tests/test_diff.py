import unittest

from okta_network_zone_manager.diff import compare_zones


class DiffTests(unittest.TestCase):
    def test_compare_detects_missing_extra_modified_and_unchanged(self):
        source = [
            {"name": "A", "type": "IP", "gateways": [{"type": "CIDR", "value": "203.0.113.0/24"}]},
            {"name": "B", "type": "IP", "gateways": []},
            {"name": "C", "type": "IP", "gateways": []},
        ]
        target = [
            {"name": "A", "type": "IP", "gateways": [{"type": "CIDR", "value": "203.0.113.0/24"}]},
            {"name": "B", "type": "IP", "gateways": [{"type": "CIDR", "value": "198.51.100.0/24"}]},
            {"name": "D", "type": "IP", "gateways": []},
        ]
        result = compare_zones(source, target)
        self.assertEqual(len(result.unchanged), 1)
        self.assertEqual(len(result.modified), 1)
        self.assertEqual(len(result.missing_in_target), 1)
        self.assertEqual(len(result.extra_in_target), 1)
        self.assertEqual(result.total_differences, 3)


if __name__ == "__main__":
    unittest.main()
