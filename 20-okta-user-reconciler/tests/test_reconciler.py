import json
from pathlib import Path

from okta_user_reconciler.config import load_config, ConfigError
from okta_user_reconciler.io_utils import read_users_csv, read_users_json
from okta_user_reconciler.reconcile import reconcile_users, build_match_key
from okta_user_reconciler.cli import run


def make_config(tmp_path, source="source.csv", target="target.csv", strict=False):
    cfg = {
        "sourceUsersFile": source,
        "targetUsersFile": target,
        "matchRules": {
            "primaryMatchField": "login",
            "fallbackMatchFields": ["email", "profile.login", "profile.email"],
            "caseInsensitive": True,
            "trimWhitespace": True,
        },
        "profileFieldsToCompare": ["login", "email", "profile.title", "status"],
        "settings": {"strictMode": strict, "detectDuplicates": True},
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return p


def write_csv(path, text):
    path.write_text(text)


def test_load_config_requires_files(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{}")
    try:
        load_config(p)
    except ConfigError as exc:
        assert "sourceUsersFile" in str(exc)
    else:
        raise AssertionError("expected ConfigError")


def test_read_users_csv(tmp_path):
    p = tmp_path / "users.csv"
    write_csv(p, "login,email\na@example.com,a@example.com\n")
    rows = read_users_csv(p)
    assert rows[0]["login"] == "a@example.com"
    assert rows[0]["__row_number"] == 2


def test_read_users_json_flattens_profile(tmp_path):
    p = tmp_path / "users.json"
    p.write_text(json.dumps([{"profile": {"login": "a@example.com", "title": "Engineer"}}]))
    rows = read_users_json(p)
    assert rows[0]["profile.login"] == "a@example.com"
    assert rows[0]["profile.title"] == "Engineer"


def test_build_match_key_case_insensitive(tmp_path):
    cfg_path = make_config(tmp_path)
    cfg = load_config(cfg_path)
    key, field = build_match_key({"login": " User@Example.com "}, cfg)
    assert key == "user@example.com"
    assert field == "login"


def test_reconcile_counts(tmp_path):
    cfg = load_config(make_config(tmp_path))
    source = [
        {"login": "a@example.com", "email": "a@example.com", "profile.title": "Engineer", "status": "ACTIVE"},
        {"login": "b@example.com", "email": "b@example.com", "profile.title": "Analyst", "status": "ACTIVE"},
    ]
    target = [
        {"login": "a@example.com", "email": "a@example.com", "profile.title": "Senior Engineer", "status": "ACTIVE"},
        {"login": "c@example.com", "email": "c@example.com", "profile.title": "Analyst", "status": "ACTIVE"},
    ]
    result = reconcile_users(source, target, cfg)
    assert result["summary"]["matchedUserCount"] == 1
    assert result["summary"]["sourceOnlyUserCount"] == 1
    assert result["summary"]["targetOnlyUserCount"] == 1
    assert result["summary"]["materialDifferenceCount"] == 1


def test_duplicate_detection(tmp_path):
    cfg = load_config(make_config(tmp_path))
    source = [{"login": "a@example.com"}, {"login": "a@example.com"}]
    target = [{"login": "a@example.com"}]
    result = reconcile_users(source, target, cfg)
    assert result["summary"]["duplicateOrMissingKeyCount"] >= 2


def test_fallback_email_match(tmp_path):
    cfg = load_config(make_config(tmp_path))
    source = [{"login": "", "email": "a@example.com"}]
    target = [{"login": "", "email": "A@Example.com"}]
    result = reconcile_users(source, target, cfg)
    assert result["summary"]["matchedUserCount"] == 1


def test_ignore_blank_source_values(tmp_path):
    cfg = load_config(make_config(tmp_path))
    source = [{"login": "a@example.com", "profile.title": ""}]
    target = [{"login": "a@example.com", "profile.title": "Engineer"}]
    result = reconcile_users(source, target, cfg)
    assert result["summary"]["materialDifferenceCount"] == 0


def test_cli_dry_run_outputs(tmp_path):
    write_csv(tmp_path / "source.csv", "login,email,profile.title\na@example.com,a@example.com,Engineer\n")
    write_csv(tmp_path / "target.csv", "login,email,profile.title\na@example.com,a@example.com,Engineer\n")
    cfg = make_config(tmp_path)
    out = tmp_path / "output"
    rc = run(["--config", str(cfg), "--dry-run", "--output-dir", str(out)])
    assert rc == 0
    runs = list(out.glob("okta-user-reconciler-*"))
    assert runs
    assert (runs[0] / "user_reconciliation_result.json").exists()


def test_strict_mode_returns_failure(tmp_path):
    write_csv(tmp_path / "source.csv", "login,email\na@example.com,a@example.com\n")
    write_csv(tmp_path / "target.csv", "login,email\nb@example.com,b@example.com\n")
    cfg = make_config(tmp_path, strict=True)
    rc = run(["--config", str(cfg), "--reconcile", "--output-dir", str(tmp_path / "out")])
    assert rc == 1


def test_config_uses_utility18_users_csv_folder_layout(tmp_path):
    (tmp_path / "input" / "source").mkdir(parents=True)
    (tmp_path / "input" / "target").mkdir(parents=True)
    write_csv(tmp_path / "input" / "source" / "users.csv", "login,email\na@example.com,a@example.com\n")
    write_csv(tmp_path / "input" / "target" / "users.csv", "login,email\na@example.com,a@example.com\n")
    cfg = {
        "sourceUsersFile": "input/source/users.csv",
        "targetUsersFile": "input/target/users.csv",
        "matchRules": {"primaryMatchField": "login"},
        "profileFieldsToCompare": ["login", "email"],
        "settings": {},
    }
    cfg_path = tmp_path / "user-reconcile.config.json"
    cfg_path.write_text(json.dumps(cfg))
    loaded = load_config(cfg_path)
    assert loaded.source_users_file.name == "users.csv"
    assert loaded.target_users_file.name == "users.csv"
    assert loaded.source_users_file.exists()
    assert loaded.target_users_file.exists()
