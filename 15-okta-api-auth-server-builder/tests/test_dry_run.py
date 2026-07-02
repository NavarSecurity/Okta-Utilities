from pathlib import Path

from okta_api_auth_server_builder.config import load_config
from okta_api_auth_server_builder.runner import run_builder


def test_sample_dry_run(tmp_path: Path):
    config_path = Path(__file__).resolve().parents[1] / "samples" / "api-auth-server.sample.json"
    config = load_config(config_path, require_api_token=False)
    result = run_builder(config, apply=False, output_dir=tmp_path)
    assert result["mode"] == "dry-run"
    assert result["summary"]["authorizationServersPlanned"] == 1
    run_dir = tmp_path / result["runId"]
    assert (run_dir / "authorization_server_plan.json").exists()
    assert (run_dir / "execution_report.md").exists()
    report = (run_dir / "execution_report.md").read_text()
    assert "WARNING" not in report
