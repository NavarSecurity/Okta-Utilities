from pathlib import Path

from okta_group_rule_create.config import AppConfig, GroupRuleConfig, Settings
from okta_group_rule_create.runner import run


def make_config():
    return AppConfig(
        target_org_url="https://example.okta.com",
        api_token="token",
        settings=Settings(require_approved=True),
        rules=[
            GroupRuleConfig(
                name="Rule - Approved",
                approved=True,
                expression='user.department == "IAM"',
                target_group_ids=["00g123"],
            ),
            GroupRuleConfig(
                name="Rule - Not Approved",
                approved=False,
                expression='user.department == "HR"',
                target_group_ids=["00g456"],
            ),
        ],
    )


def test_dry_run_writes_outputs(tmp_path: Path):
    result = run(make_config(), apply=False, output_dir=tmp_path)
    assert result["mode"] == "dry-run"
    assert result["counts"]["planned"] == 1
    assert result["counts"]["skipped"] == 1
    run_folder = Path(result["runFolder"])
    assert (run_folder / "group_rule_plan.json").exists()
    assert (run_folder / "execution_report.md").exists()


def test_unresolved_names_allowed_in_dry_run(tmp_path: Path):
    cfg = AppConfig(
        target_org_url="https://example.okta.com",
        api_token="token",
        settings=Settings(require_approved=True),
        rules=[
            GroupRuleConfig(
                name="Rule - Name Target",
                approved=True,
                expression='user.department == "IAM"',
                target_group_names=["IAM Users"],
            )
        ],
    )
    result = run(cfg, apply=False, output_dir=tmp_path)
    assert result["counts"]["planned"] == 1
