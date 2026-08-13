from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "probe_gc_dataset_condition_003.py"
SPEC = importlib.util.spec_from_file_location("gc_condition_003", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUT
SPEC.loader.exec_module(SUT)


def test_condition_contract_is_metadata_only() -> None:
    assert SUT.DATASET == "GLBX.MDP3"
    assert SUT.START_DATE == "2019-01-01"
    assert SUT.END_DATE == "2019-04-01"
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "client.timeseries" not in source
    assert "client.batch" not in source


def test_validate_conditions_preserves_provider_fields() -> None:
    rows = SUT.validate_conditions([
        {"date": "2019-01-01", "condition": "available", "last_modified_date": "2019-01-02"},
        {"date": "2019-01-02", "condition": "degraded", "last_modified_date": "2019-01-03"},
    ])
    assert rows[0]["condition"] == "available"
    assert rows[1]["condition"] == "degraded"
    assert rows[0]["last_modified_date"] == "2019-01-02"


def test_validate_conditions_rejects_duplicate_dates() -> None:
    with pytest.raises(SUT.ConditionError, match="duplicate"):
        SUT.validate_conditions([
            {"date": "2019-01-01", "condition": "available"},
            {"date": "2019-01-01", "condition": "degraded"},
        ])


def test_validate_conditions_rejects_missing_fields() -> None:
    with pytest.raises(SUT.ConditionError, match="missing"):
        SUT.validate_conditions([{"date": "2019-01-01"}])
