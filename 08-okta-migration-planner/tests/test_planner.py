from pathlib import Path

from okta_migration_planner.config import PlannerConfig
from okta_migration_planner.planner import MigrationPlanner

ROOT = Path(__file__).resolve().parents[1]


def test_planner_generates_expected_counts_for_samples():
    config = PlannerConfig(
        source_backup_dir=ROOT / "samples" / "source-backup",
        target_backup_dir=ROOT / "samples" / "target-backup",
        include=["groups", "applications", "authorization_servers", "policies", "identity_providers"],
    )
    plan = MigrationPlanner(config).build_plan()
    assert plan.summary["resourcesAnalyzed"] == 5
    assert plan.summary["createCandidates"] >= 2
    assert plan.summary["matchedObjects"] >= 1
    assert plan.summary["conflicts"] >= 1
    assert plan.overall_status == "NOT_READY"


def test_planner_identifies_group_missing_in_target():
    config = PlannerConfig(
        source_backup_dir=ROOT / "samples" / "source-backup",
        target_backup_dir=ROOT / "samples" / "target-backup",
        include=["groups"],
    )
    plan = MigrationPlanner(config).build_plan()
    rows = plan.object_mappings
    assert any(row["status"] == "missing_in_target" and row["source_key"] == "App Users" for row in rows)


def test_planner_marks_missing_policy_manual_review():
    config = PlannerConfig(
        source_backup_dir=ROOT / "samples" / "source-backup",
        target_backup_dir=ROOT / "samples" / "target-backup",
        include=["policies"],
    )
    plan = MigrationPlanner(config).build_plan()
    assert any(item["resource"] == "policies" for item in plan.manual_review_items)
    assert plan.overall_status == "NOT_READY"
