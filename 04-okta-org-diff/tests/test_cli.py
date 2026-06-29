from pathlib import Path

from okta_org_diff.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_sample_config_runs(tmp_path):
    rc = main([
        "--baseline-backup-dir", str(ROOT / "samples" / "baseline-backup"),
        "--comparison-backup-dir", str(ROOT / "samples" / "comparison-backup"),
        "--output-dir", str(tmp_path),
        "--include", "groups",
    ])
    assert rc == 0
    assert list(tmp_path.glob("okta-org-diff-*"))


def test_cli_strict_returns_failure_on_differences(tmp_path):
    rc = main([
        "--baseline-backup-dir", str(ROOT / "samples" / "baseline-backup"),
        "--comparison-backup-dir", str(ROOT / "samples" / "comparison-backup"),
        "--output-dir", str(tmp_path),
        "--include", "groups",
        "--strict",
    ])
    assert rc == 1
