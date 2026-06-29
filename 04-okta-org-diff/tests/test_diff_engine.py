from pathlib import Path

from okta_org_diff.config import DiffConfig
from okta_org_diff.diff_engine import run_diff

ROOT = Path(__file__).resolve().parents[1]


def test_sample_diff_detects_expected_differences(tmp_path):
    config = DiffConfig(
        baseline_backup_dir=ROOT / "samples" / "baseline-backup",
        comparison_backup_dir=ROOT / "samples" / "comparison-backup",
        output_dir=tmp_path,
        include=["applications", "groups", "policies", "domains", "authorization_servers"],
    )
    result = run_diff(config)
    assert result["status"] == "DIFFERENCES_FOUND"
    assert result["totals"]["added"] >= 2
    assert result["totals"]["removed"] >= 2
    assert result["totals"]["changed"] >= 4


def test_missing_files_are_warnings_not_runtime_failures(tmp_path):
    baseline = tmp_path / "baseline"
    comparison = tmp_path / "comparison"
    baseline.mkdir()
    comparison.mkdir()
    config = DiffConfig(
        baseline_backup_dir=baseline,
        comparison_backup_dir=comparison,
        output_dir=tmp_path,
        include=["applications"],
    )
    result = run_diff(config)
    assert result["totals"]["warnings"] == 2
