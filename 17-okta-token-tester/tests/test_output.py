from okta_token_tester.output import create_run_dir, write_plan


def test_write_plan(tmp_path):
    run_dir = create_run_dir(tmp_path)
    write_plan(run_dir, {"orgUrl": "https://example.okta.com", "issuerUrl": "https://example.okta.com/oauth2/default"})
    assert (run_dir / "token_test_plan.json").exists()
    assert (run_dir / "execution_report.md").exists()
