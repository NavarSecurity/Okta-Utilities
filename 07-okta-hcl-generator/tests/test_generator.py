from pathlib import Path

from okta_hcl_generator.config import GeneratorConfig
from okta_hcl_generator.generator import generate


def test_generate_sample_outputs(tmp_path):
    repo = Path(__file__).resolve().parents[1]
    cfg = GeneratorConfig(
        backup_dir=repo / "samples" / "source-backup",
        output_dir=tmp_path,
        include=["groups", "applications", "authorization_servers", "authorization_server_scopes", "authorization_server_claims", "policies", "identity_providers"],
    )
    result = generate(cfg)
    assert result.status == "WARN"  # policies and IdPs are manual review.
    out = Path(result.output_dir)
    assert (out / "groups.tf").exists()
    assert (out / "applications.tf").exists()
    assert (out / "authorization_servers.tf").exists()
    assert (out / "authorization_server_scopes.tf").exists()
    assert (out / "authorization_server_claims.tf").exists()
    assert (out / "manual_review_items.csv").exists()
    assert "okta_app_oauth" in (out / "applications.tf").read_text()


def test_strict_mode_fails_on_missing_file(tmp_path):
    backup_dir = tmp_path / "backup"
    backup_dir.mkdir()
    cfg = GeneratorConfig(
        backup_dir=backup_dir,
        output_dir=tmp_path / "out",
        include=["groups"],
        strict_mode=True,
    )
    result = generate(cfg)
    assert result.status == "FAIL"
    assert "groups.json" in result.missing_files
