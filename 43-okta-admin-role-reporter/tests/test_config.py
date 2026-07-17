from pathlib import Path

from okta_admin_role_reporter.config import load_config, read_lines_file


def test_load_config_merges_defaults(tmp_path: Path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"includeGroupRoleAssignments": false}', encoding="utf-8")
    config = load_config(config_path)
    assert config["includeGroupRoleAssignments"] is False
    assert config["includeUserRoleAssignments"] is True
    assert config["outputDirectory"] == "output"


def test_read_lines_file_ignores_blank_and_comments(tmp_path: Path):
    file_path = tmp_path / "groups.txt"
    file_path.write_text("# comment\nAdmins\n\nHelp Desk\n", encoding="utf-8")
    assert read_lines_file(file_path) == ["Admins", "Help Desk"]
