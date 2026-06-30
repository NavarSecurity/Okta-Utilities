from pathlib import Path

from okta_hcl_generator.cli import main


def test_cli_sample_run(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    code = main([
        "--backup-dir", str(repo / "samples" / "source-backup"),
        "--output-dir", str(tmp_path),
        "--include", "groups,applications",
    ])
    assert code == 0
    outputs = list(tmp_path.glob("okta-hcl-*"))
    assert outputs
    assert (outputs[0] / "groups.tf").exists()
