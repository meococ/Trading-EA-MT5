from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "analyze_gc_source_integrity_003.py"
SPEC = importlib.util.spec_from_file_location("gc_source_003", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUT
SPEC.loader.exec_module(SUT)


def test_exact_mapping_dates() -> None:
    assert SUT.expected_instrument(SUT.epoch_day("2019-01-01")) == 32257
    assert SUT.expected_instrument(SUT.epoch_day("2019-02-01")) == 14651
    assert SUT.expected_instrument(SUT.epoch_day("2019-03-31")) == 142620
    assert SUT.expected_instrument(SUT.epoch_day("2019-04-01")) is None


def test_bbo_gate_is_strict() -> None:
    assert SUT.bbo_valid(100, 101)
    assert not SUT.bbo_valid(100, 100)
    assert not SUT.bbo_valid(101, 100)
    assert not SUT.bbo_valid(0, 100)


def test_status_tilde_retains_previous_value() -> None:
    assert SUT.apply_status_value("Y", "~") == "Y"
    assert SUT.apply_status_value("N", "~") == "N"
    assert SUT.apply_status_value(None, "~") is None
    with pytest.raises(SUT.IntegrityError, match="unknown"):
        SUT.apply_status_value("Y", "X")


def test_dbn_status_bool_adapter_restores_tristate_wire_values() -> None:
    assert SUT.status_value_from_dbn(True) == "Y"
    assert SUT.status_value_from_dbn(False) == "N"
    assert SUT.status_value_from_dbn(None) == "~"
    with pytest.raises(SUT.IntegrityError, match="adapter"):
        SUT.status_value_from_dbn(1)


def test_coverage_share_is_fail_closed() -> None:
    assert SUT.share(99, 100) == pytest.approx(0.99)
    with pytest.raises(SUT.IntegrityError, match="denominator"):
        SUT.share(0, 0)


def test_bin_validity_enforces_reset_and_session_boundary() -> None:
    state = SUT.BinState(32257, 1, 1_000, signed_count=2, first_bid=100, first_ask=101, last_bid=101, last_ask=102)
    bounds = {(32257, 1): (1_000, 1_000 + SUT.BIN_NS)}
    assert SUT.bin_is_valid(state, bounds) == (True, "valid")
    state.contains_first_after_reset = True
    assert SUT.bin_is_valid(state, bounds)[1] == "first_after_reset"


def test_source_never_calls_tail_predicate_or_target_outcome() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "paired_candidate(" not in source
    assert "timeseries.get_range" not in source
    assert "XAUUSD" not in source
