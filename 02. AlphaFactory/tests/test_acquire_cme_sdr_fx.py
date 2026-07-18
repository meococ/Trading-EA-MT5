from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "acquire_cme_sdr_fx.py"


def load_module():
    spec = importlib.util.spec_from_file_location("acquire_cme_sdr_fx", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_daily_filename_contract_excludes_hourly_fragments() -> None:
    module = load_module()
    assert module.is_daily_file("RT.FX.20170403.zip")
    assert module.is_daily_file("RT.FX.20230103.csv.zip")
    assert not module.is_daily_file("RT.FX.20260709.0800.csv.zip")
    assert not module.is_daily_file("RT.RATES.20230103.csv.zip")


def test_even_sample_is_deterministic_and_uses_interior_dates() -> None:
    module = load_module()
    files = [
        module.RemoteFile(2020, 1, f"RT.FX.202001{day:02d}.csv.zip", 10)
        for day in range(1, 10)
    ]
    selected = module.select_even_sample(files, 3)
    assert [item.name for item in selected] == [
        "RT.FX.20200102.csv.zip",
        "RT.FX.20200105.csv.zip",
        "RT.FX.20200107.csv.zip",
    ]


def test_zero_sample_selects_all_daily_files() -> None:
    module = load_module()
    files = [
        module.RemoteFile(2021, 2, "RT.FX.20210201.csv.zip", 10),
        module.RemoteFile(2021, 2, "RT.FX.20210202.csv.zip", 11),
    ]
    assert module.select_even_sample(files, 0) == files


def test_remote_file_exposes_point_in_time_date_and_path() -> None:
    module = load_module()
    item = module.RemoteFile(2018, 7, "RT.FX.20180716.zip", 123)
    assert item.trade_date == "2018-07-16"
    assert item.remote_path == "/sdr/fx/2018/07/RT.FX.20180716.zip"
