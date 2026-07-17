from pathlib import Path

from okta_api_access_auditor.config import Config
from okta_api_access_auditor.exporter import ApiAccessAuditor


class DummyClient:
    pass


def test_dry_run_writes_files(tmp_path: Path):
    config = Config(output_directory=str(tmp_path))
    auditor = ApiAccessAuditor(DummyClient(), config)
    result = auditor.dry_run()
    out_dir = Path(result["outputDirectory"])
    assert (out_dir / "dry_run_report.json").exists()
    assert (out_dir / "execution_report.json").exists()
