from pathlib import Path

from okta_app_cloner.config import AppClonerConfig
from okta_app_cloner.planner import build_plan


def test_build_plan_selects_one_app_by_label():
    cfg = AppClonerConfig(
        source_backup_dir=Path("samples/source-backup"),
        target_org_url="https://target.example.okta.com",
        target_api_token="fake-token",
        selection={"applications": {"labels": ["Customer Portal OIDC"], "ids": [], "signOnModes": []}},
    )
    plan = build_plan(cfg)
    assert len(plan.operations) == 1
    assert plan.operations[0].label == "Customer Portal OIDC"


def test_build_plan_empty_selection_selects_all_apps():
    cfg = AppClonerConfig(
        source_backup_dir=Path("samples/source-backup"),
        target_org_url="https://target.example.okta.com",
        target_api_token="fake-token",
        selection={"applications": {"labels": [], "ids": [], "signOnModes": []}},
    )
    plan = build_plan(cfg)
    assert len(plan.operations) == 2
