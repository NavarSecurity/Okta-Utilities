from pathlib import Path

from okta_admin_role_reporter.config import load_config
from okta_admin_role_reporter.exporter import run_export
from okta_admin_role_reporter.okta_client import OktaClient


def test_dry_run_writes_files(tmp_path: Path):
    config_path = tmp_path / "config.json"
    output_dir = tmp_path / "output"
    config_path.write_text('{"outputDirectory": "' + str(output_dir).replace('\\', '/') + '"}', encoding="utf-8")
    config = load_config(config_path)
    client = OktaClient("", "")
    run_dir = run_export(config, client, dry_run=True)
    assert (run_dir / "dry_run_report.json").exists()
    assert (run_dir / "config_summary.json").exists()
    assert (run_dir / "execution_report.json").exists()
    assert (run_dir / "manifest.json").exists()
