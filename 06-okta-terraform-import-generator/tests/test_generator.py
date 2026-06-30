from pathlib import Path

from okta_terraform_import_generator.generator import TerraformImportGenerator
from okta_terraform_import_generator.models import GeneratorConfig
from okta_terraform_import_generator.utils import slugify


def test_slugify_produces_valid_name():
    assert slugify("Customer Portal OIDC") == "customer_portal_oidc"
    assert slugify("123 Admins") == "r_123_admins"


def test_sample_generates_imports(tmp_path):
    backup_dir = Path(__file__).resolve().parents[1] / "samples" / "source-backup"
    cfg = GeneratorConfig(backup_dir=backup_dir, output_dir=tmp_path)
    result = TerraformImportGenerator(cfg).generate()
    assert result.total_imports >= 10
    assert result.total_unsupported >= 1
    assert Path(result.output_dir, "terraform_imports.sh").exists()
    assert Path(result.output_dir, "imports.tf").exists()
    assert Path(result.output_dir, "resource_mapping.csv").exists()


def test_groups_only(tmp_path):
    backup_dir = Path(__file__).resolve().parents[1] / "samples" / "source-backup"
    cfg = GeneratorConfig(backup_dir=backup_dir, output_dir=tmp_path, include=["groups"])
    result = TerraformImportGenerator(cfg).generate()
    assert result.total_imports == 1
    assert result.counts_by_resource["groups"] == 1
    rec = result.imports[0]
    assert rec["terraform_type"] == "okta_group"
    assert rec["import_id"] == "00gsourceadmins"


def test_module_prefix(tmp_path):
    backup_dir = Path(__file__).resolve().parents[1] / "samples" / "source-backup"
    cfg = GeneratorConfig(backup_dir=backup_dir, output_dir=tmp_path, include=["groups"], module_prefix="module.okta")
    result = TerraformImportGenerator(cfg).generate()
    assert result.imports[0]["terraform_address"].startswith("module.okta.okta_group")


def test_app_mapping_supports_oidc_and_marks_unknown(tmp_path):
    backup_dir = Path(__file__).resolve().parents[1] / "samples" / "source-backup"
    cfg = GeneratorConfig(backup_dir=backup_dir, output_dir=tmp_path, include=["applications"])
    result = TerraformImportGenerator(cfg).generate()
    assert any(r["terraform_type"] == "okta_app_oauth" for r in result.imports)
    assert any(r["resource"] == "applications" for r in result.unsupported)


def test_import_block_format(tmp_path):
    backup_dir = Path(__file__).resolve().parents[1] / "samples" / "source-backup"
    cfg = GeneratorConfig(backup_dir=backup_dir, output_dir=tmp_path, include=["groups"], mode="blocks")
    result = TerraformImportGenerator(cfg).generate()
    imports_tf = Path(result.output_dir, "imports.tf").read_text()
    assert "import {" in imports_tf
    assert 'id = "00gsourceadmins"' in imports_tf
