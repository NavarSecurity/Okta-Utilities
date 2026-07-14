from okta_idp_exporter.config import parse_app_config


def test_parse_config_defaults():
    config = parse_app_config({})

    assert config.output_dir == "output"
    assert config.include_inactive is True
    assert config.include_keys is True
    assert config.redact_sensitive_values is True


def test_parse_config_filters_uppercase():
    config = parse_app_config({"filters": {"types": ["oidc"], "statuses": ["active"]}})

    assert config.filters.types == ["OIDC"]
    assert config.filters.statuses == ["ACTIVE"]
