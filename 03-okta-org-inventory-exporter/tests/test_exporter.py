from pathlib import Path

from okta_org_inventory_exporter.config import InventoryConfig
from okta_org_inventory_exporter.exporter import export_inventory


def test_sample_export_creates_inventory(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "samples" / "sample-backup"
    config = InventoryConfig(backup_dir=sample, output_dir=tmp_path, include=("applications", "groups", "policies", "domains"))
    inventory = export_inventory(config)
    assert inventory["summary"]["resources"]["applications"]["count"] == 2
    assert inventory["summary"]["resources"]["groups"]["count"] == 2
    assert inventory["summary"]["resources"]["policies"]["count"] == 2
    assert inventory["summary"]["resources"]["domains"]["count"] == 1
    out_dir = Path(inventory["outputDir"])
    assert (out_dir / "inventory.json").exists()
    assert (out_dir / "inventory_report.md").exists()
    assert (out_dir / "csv" / "applications.csv").exists()


def test_missing_file_warning(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "samples" / "sample-backup"
    config = InventoryConfig(backup_dir=sample, output_dir=tmp_path, include=("applications", "not_a_resource", "some_missing"))
    inventory = export_inventory(config)
    codes = [w["code"] for w in inventory["warnings"]]
    assert "UNKNOWN_RESOURCE" in codes
