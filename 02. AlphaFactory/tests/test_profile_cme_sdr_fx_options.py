from __future__ import annotations

import csv
import importlib.util
import io
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "profile_cme_sdr_fx_options.py"


def load_module():
    spec = importlib.util.spec_from_file_location("profile_cme_sdr_fx_options", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_zip(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(path.stem + ".csv", buffer.getvalue())


def test_legacy_profile_counts_only_new_major_option_rows(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "RT.FX.20200102.csv.zip"
    columns = [
        "Event",
        "Dissemination Time",
        "Contract Type",
        "Currency 1",
        "Currency 2",
        "Option Type",
    ]
    write_zip(
        path,
        columns,
        [
            {"Event": "New Trade", "Dissemination Time": "x", "Contract Type": "FXOption", "Currency 1": "EUR", "Currency 2": "USD", "Option Type": "Call"},
            {"Event": "Cancel", "Dissemination Time": "x", "Contract Type": "FXOption", "Currency 1": "EUR", "Currency 2": "USD", "Option Type": "Call"},
            {"Event": "New Trade", "Dissemination Time": "x", "Contract Type": "FXForward", "Currency 1": "EUR", "Currency 2": "USD", "Option Type": ""},
        ],
    )
    result = module.profile_file(path, "2020-01-02")
    assert result["option_rows"] == 2
    assert result["new_option_rows"] == 1
    assert result["major_new_option_rows"] == 1
    assert result["major_pairs"] == {"EURUSD": 1}


def test_modern_profile_requires_new_trade_action(tmp_path: Path) -> None:
    module = load_module()
    path = tmp_path / "RT.FX.20230103.csv.zip"
    columns = [
        "action",
        "event",
        "instrumentType",
        "optionType",
        "exchangeRateBasis",
        "disseminationTimestamp",
    ]
    write_zip(
        path,
        columns,
        [
            {"action": "NEWT", "event": "TRAD", "instrumentType": "Option", "optionType": "CALL", "exchangeRateBasis": "USD/JPY", "disseminationTimestamp": "x"},
            {"action": "MODI", "event": "TRAD", "instrumentType": "Option", "optionType": "PUTO", "exchangeRateBasis": "EUR/USD", "disseminationTimestamp": "x"},
        ],
    )
    result = module.profile_file(path, "2023-01-03")
    assert result["option_rows"] == 2
    assert result["new_option_rows"] == 1
    assert result["major_pairs"] == {"USDJPY": 1}


def test_split_density_uses_unique_pair_days() -> None:
    module = load_module()
    files = [
        {"trade_date": "2020-01-02", "major_pairs": {"EURUSD": 3}, "major_new_option_rows": 3},
        {"trade_date": "2020-01-03", "major_pairs": {"EURUSD": 1, "USDJPY": 2}, "major_new_option_rows": 3},
        {"trade_date": "2020-01-06", "major_pairs": {}, "major_new_option_rows": 0},
        {"trade_date": "2020-01-07", "major_pairs": {}, "major_new_option_rows": 0},
        {"trade_date": "2020-01-08", "major_pairs": {}, "major_new_option_rows": 0},
    ]
    result = module.split_summary(files)
    assert result["unique_major_pair_days"] == 3
    assert result["estimated_pair_days_per_week"] == 3.0
    assert result["estimated_one_trade_max_per_day_per_week"] == 2.0
    assert result["cadence_2_to_5_pass"] is True


def test_pair_parser_rejects_non_major_currency_pair() -> None:
    module = load_module()
    assert module.pair_from_modern({"exchangeRateBasis": "EUR/USD"}) == "EURUSD"
    assert module.pair_from_modern({"exchangeRateBasis": "USD/MXN"}) is None
