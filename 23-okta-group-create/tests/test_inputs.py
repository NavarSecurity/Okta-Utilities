from pathlib import Path

from okta_group_create.inputs import load_group_rows


def test_load_csv(tmp_path):
    p = tmp_path / "groups.csv"
    p.write_text("name,description\nTest Group,Desc\n", encoding="utf-8")
    rows = load_group_rows(p)
    assert rows[0]["name"] == "Test Group"


def test_load_json_object(tmp_path):
    p = tmp_path / "groups.json"
    p.write_text('{"groups":[{"name":"Json Group"}]}', encoding="utf-8")
    rows = load_group_rows(p)
    assert rows[0]["name"] == "Json Group"


def test_load_yaml_object(tmp_path):
    p = tmp_path / "groups.yaml"
    p.write_text('groups:\n  - name: Yaml Group\n', encoding="utf-8")
    rows = load_group_rows(p)
    assert rows[0]["name"] == "Yaml Group"
