from pathlib import Path

from okta_app_assignment_exporter.config import AppSelection, ExportOptions, HttpConfig, RuntimeConfig
from okta_app_assignment_exporter.runner import run


def test_runner_dry_run_writes_plan(tmp_path: Path):
    cfg = RuntimeConfig(
        target_org_url="https://example.okta.com",
        api_token=None,
        output_dir=tmp_path,
        app_selection=AppSelection(mode="labels", app_labels=["Example App"]),
        export_options=ExportOptions(),
        http=HttpConfig(),
    )
    result, out_dir = run(cfg, export=False)
    assert result["status"] == "DRY_RUN_COMPLETE"
    assert (out_dir / "app_assignment_export_plan.json").exists()
    assert (out_dir / "execution_report.md").exists()
