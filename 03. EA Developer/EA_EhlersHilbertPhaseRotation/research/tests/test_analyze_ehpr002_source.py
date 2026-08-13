from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_ehpr002_source.py"
SPEC = importlib.util.spec_from_file_location("analyze_ehpr002_source", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_frozen_predicate_uses_utc_not_source_epoch() -> None:
    filters = MODULE.parquet_filters()
    assert [item[0] for item in filters] == ["time_utc", "time_utc"]
    assert filters[0][1] == ">=" and pd.Timestamp(filters[0][2]) == MODULE.SOURCE_START
    assert filters[1][1] == "<" and pd.Timestamp(filters[1][2]) == MODULE.DESIGN_END


def test_timezone_filter_executes_on_parquet(tmp_path: Path) -> None:
    path = tmp_path / "clock.parquet"
    frame = pd.DataFrame({
        "time_utc": pd.to_datetime([
            "2014-12-31T23:45:00Z",
            "2015-01-01T00:00:00Z",
            "2020-12-31T23:45:00Z",
            "2021-01-01T00:00:00Z",
        ]),
        "source_epoch": [1, 2, 3, 4],
    })
    frame.to_parquet(path, index=False)
    selected = pd.read_parquet(path, filters=MODULE.parquet_filters(), engine="pyarrow")
    assert selected["source_epoch"].tolist() == [2, 3]


def test_parent_algorithm_is_hash_frozen() -> None:
    parent = MODULE_PATH.with_name("analyze_ehpr_source.py")
    assert MODULE.sha256_file(parent) == MODULE.PARENT_ANALYZER_SHA256


def test_child_identity_is_propagated_to_frozen_algorithm() -> None:
    assert MODULE.BASE.HYPOTHESIS_ID == MODULE.HYPOTHESIS_ID
    assert MODULE.BASE.ATTEMPT_ID == MODULE.ATTEMPT_ID
