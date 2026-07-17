import json
from pathlib import Path

from okta_rate_limit_monitor.cli import main


def test_dry_run_writes_files(tmp_path):
    config = {
        "outputDirectory": str(tmp_path / "output"),
        "includeHeaderProbes": True,
        "includeSystemLogEvents": True,
        "includePlannedOperationEstimate": True,
        "probeEndpoints": [{"name": "users", "method": "GET", "path": "/api/v1/users", "params": {"limit": "1"}}],
        "systemLogFilters": ["displayMessage eq \"Rate limit violation\""],
        "plannedOperations": [{"name": "backup", "endpoint": "/api/v1/users", "estimatedRequests": 10, "windowMinutes": 1}],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    code = main(["--config", str(path), "--dry-run"])
    assert code == 0
    output_dirs = list((tmp_path / "output").glob("rate-limit-monitor-dry-run-*"))
    assert output_dirs
    assert (output_dirs[0] / "dry_run_report.json").exists()
    assert (output_dirs[0] / "execution_report.json").exists()
