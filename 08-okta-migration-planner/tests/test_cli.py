from pathlib import Path

from okta_migration_planner.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_cli_runs_with_samples(tmp_path):
    code = main([
        "--source-backup-dir", str(ROOT / "samples" / "source-backup"),
        "--target-backup-dir", str(ROOT / "samples" / "target-backup"),
        "--include", "groups,applications",
        "--output-dir", str(tmp_path),
    ])
    assert code in {0, 1}
    assert any(tmp_path.iterdir())
