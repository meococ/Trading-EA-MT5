from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest


MODULE_PATH = Path(__file__).parents[1] / "export_lomx_002_train_source.py"
SPEC = importlib.util.spec_from_file_location("lomx_002_export", MODULE_PATH)
assert SPEC and SPEC.loader
lomx = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lomx
SPEC.loader.exec_module(lomx)


def _spread_frame(positive: int, missing: int) -> pd.DataFrame:
    rows = []
    for symbol in lomx.base.SYMBOLS:
        for index in range(positive + missing):
            spread = 10 + index % 3 if index < positive else 0
            rows.append(
                {
                    "symbol": symbol,
                    "spread_0830_points": spread,
                    "spread_1200_points": spread,
                    "spread_1530_points": spread,
                    "spread_1600_points": spread,
                    "spread_1630_points": spread,
                }
            )
    return pd.DataFrame(rows)


def test_q95_imputation_is_positive_and_reported():
    result, quality = lomx.impute_missing_spreads(_spread_frame(9, 1))
    spread_cols = [column for column in result if column.startswith("spread_")]
    assert (result[spread_cols] > 0).all().all()
    assert quality["EURUSD"]["raw_positive_spread_coverage"] == pytest.approx(0.9)
    assert quality["EURUSD"]["imputed_endpoint_count"] == 5
    assert quality["EURUSD"]["imputation_spread_points"] == 12


def test_successor_still_fails_very_sparse_spread_source():
    with pytest.raises(lomx.ContractError, match="raw positive spread coverage"):
        lomx.impute_missing_spreads(_spread_frame(7, 3))


def test_cli_remains_disarmed():
    with pytest.raises(lomx.ContractError, match="production is disarmed"):
        lomx.main([])
