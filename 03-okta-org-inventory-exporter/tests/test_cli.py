from pathlib import Path
from okta_org_inventory_exporter.cli import main


def test_cli_runs_sample(tmp_path):
    sample = Path(__file__).resolve().parents[1] / "samples" / "sample-backup"
    rc = main(["--backup-dir", str(sample), "--output-dir", str(tmp_path), "--include", "applications,groups"])
    assert rc == 0
    assert any(tmp_path.glob("okta-org-inventory-*/inventory.json"))
