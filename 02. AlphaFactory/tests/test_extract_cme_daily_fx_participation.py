from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "extract_cme_daily_fx_participation.py"
SAMPLES = ROOT / "02. AlphaFactory" / "external" / "cme_daily_volume" / "source_samples"


def require_sample(name: str) -> Path:
    """Return a vendor workbook sample, skipping when it is outside this checkout.

    `02. AlphaFactory/external/` is gitignored (`.gitignore`) and holds CME
    workbooks downloaded by the acquisition tooling; the bytes are vendor input,
    never committed evidence, and are absent from every git ref. The parser is
    still exercised wherever the samples exist.
    """
    path = SAMPLES / name
    if not path.is_file():
        pytest.skip(
            f"{name} is not in this checkout: 02. AlphaFactory/external/ is "
            "gitignored vendor input, not tracked evidence"
        )
    return path


def load_module():
    spec = importlib.util.spec_from_file_location("extract_cme_daily_fx_participation", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_date_normalization_handles_legacy_and_current_formats() -> None:
    module = load_module()
    assert module.sheet_trade_date_candidates("Trade Date:  1/3/17") == {"2017-01-03", "2017-03-01"}
    assert "2025-01-02" in module.sheet_trade_date_candidates("Trade Date:  01/02/2025")


def test_parser_handles_legacy_shifted_columns() -> None:
    module = load_module()
    rows = module.parse_workbook(require_sample("daily_volume_20170103.xlsx"))
    by_symbol = {row["symbol"]: row for row in rows}
    assert by_symbol["EURUSD"]["total_volume"] == 244244
    assert by_symbol["EURUSD"]["open_interest"] == 416424
    assert by_symbol["USDJPY"]["total_volume"] == 154840


def test_parser_handles_current_columns() -> None:
    module = load_module()
    rows = module.parse_workbook(require_sample("daily_volume_20250102.xlsx"))
    by_symbol = {row["symbol"]: row for row in rows}
    assert by_symbol["EURUSD"]["total_volume"] == 282417
    assert by_symbol["EURUSD"]["open_interest"] == 613044
    assert by_symbol["GBPUSD"]["open_interest"] == 193244


def test_filename_is_unambiguous_point_in_time_authority() -> None:
    module = load_module()
    assert module.trade_date_from_filename(Path("daily_volume_20170103.xlsx")) == "2017-01-03"
    assert module.trade_date_from_filename(Path("daily_volume_20170301.xlsx")) == "2017-03-01"
