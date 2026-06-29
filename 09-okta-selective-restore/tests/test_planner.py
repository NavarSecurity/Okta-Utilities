from pathlib import Path

from okta_selective_restore.config import RestoreConfig
from okta_selective_restore.planner import build_plan


def test_build_plan_selects_named_group(sample_backup_dir: Path):
    config = RestoreConfig(
        source_backup_dir=sample_backup_dir,
        target_org_url="https://target.okta.com",
        target_api_token="token",
        include=["groups"],
        selection={"groups": {"names": ["Engineering"], "ids": []}},
    )
    plan = build_plan(config)
    assert len(plan.operations) == 1
    assert plan.operations[0].display_name == "Engineering"
    assert plan.operations[0].endpoint == "/api/v1/groups"


def test_build_plan_skips_inactive_by_default(sample_backup_dir: Path):
    config = RestoreConfig(
        source_backup_dir=sample_backup_dir,
        target_org_url="https://target.okta.com",
        target_api_token="token",
        include=["groups"],
    )
    plan = build_plan(config)
    names = [op.display_name for op in plan.operations]
    assert "Engineering" in names
    assert "Inactive Group" not in names
    assert any("Source object status" in item["reason"] for item in plan.skipped)


def test_build_plan_skips_unsupported_resource(sample_backup_dir: Path):
    config = RestoreConfig(
        source_backup_dir=sample_backup_dir,
        target_org_url="https://target.okta.com",
        target_api_token="token",
        include=["policies"],
    )
    plan = build_plan(config)
    assert not plan.operations
    assert plan.skipped[0]["resource"] == "policies"
