from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "acquire_cme_daily_volume.py"


def load_module():
    spec = importlib.util.spec_from_file_location("acquire_cme_daily_volume", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_remote_file_contract() -> None:
    module = load_module()
    row = module.RemoteFile("daily_volume_20220103.xlsx", 123)
    assert row.trade_date == "2022-01-03"
    assert row.year == 2022
    assert row.remote_path.endswith("/daily_volume_20220103.xlsx")


def test_filename_contract_rejects_current_aliases_and_zip() -> None:
    module = load_module()
    assert module.FILE_RE.fullmatch("daily_volume_20170103.xlsx")
    assert not module.FILE_RE.fullmatch("daily_volume.xlsx")
    assert not module.FILE_RE.fullmatch("daily_volume_.xlsx")
    assert not module.FILE_RE.fullmatch("daily_volume_reports_2013.zip")


def test_sealed_holdout_guard_precedes_network(monkeypatch, tmp_path: Path) -> None:
    module = load_module()
    monkeypatch.setattr(module, "require_d_external", lambda path: path)
    try:
        module.acquire(tmp_path, 2017, 2024, 1)
    except ValueError as exc:
        assert "sealed" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("holdout guard did not fail")
