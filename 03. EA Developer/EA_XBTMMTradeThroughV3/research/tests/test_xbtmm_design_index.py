from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[2]
TOOL = PACKAGE / "research" / "tools" / "build_xbtmm_design_index.py"
SPEC = importlib.util.spec_from_file_location("build_xbtmm_design_index", TOOL)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sut
SPEC.loader.exec_module(sut)


def test_full_design_population_is_exact() -> None:
    days = sut.days_between(sut.DESIGN_START, sut.DESIGN_END)
    assert len(days) == 1461
    assert days[0] == date(2018, 1, 1)
    assert days[-1] == date(2021, 12, 31)


def test_normalizer_cannot_open_validation_or_holdout() -> None:
    with pytest.raises(ValueError):
        sut.days_between(date(2022, 1, 1), date(2022, 1, 2))


def test_index_row_is_file_common_and_hash_bound(tmp_path: Path) -> None:
    event = tmp_path / "events" / "2018" / "01" / "20180101.xbtmm"
    event.parent.mkdir(parents=True)
    event.write_bytes(b"event")
    manifest = {
        "utc_day": "20180101",
        "output": {
            "path": str(event),
            "sha256": "A" * 64,
            "bytes": 5,
            "records": 3,
            "quote_records": 2,
            "trade_records": 1,
            "first_time_us": 1,
            "last_time_us": 2,
        },
        "instrument_schedule": {"tick_size": 0.5},
    }
    row = sut.index_row(tmp_path, manifest)
    assert row["event_file_common"] == "xbtmm\\events\\2018\\01\\20180101.xbtmm"
    assert row["event_sha256"] == "A" * 64
