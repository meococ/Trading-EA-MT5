from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_event_depth_transfer_001_pilot.py"
SPEC = importlib.util.spec_from_file_location("event_depth_transfer_001", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def levels(bid_sizes: list[int], ask_sizes: list[int], *, locked: bool = False):
    assert len(bid_sizes) == len(ask_sizes) == 10
    return [
        SimpleNamespace(
            bid_px=1000 - i,
            ask_px=(1000 if locked and i == 0 else 1001 + i),
            bid_sz=bid_sizes[i], ask_sz=ask_sizes[i], bid_ct=1, ask_ct=1,
        )
        for i in range(10)
    ]


def msg(ts: int, *, action: str = "M", side: str = "N", size: int = 1,
        bid_sizes: list[int] | None = None, ask_sizes: list[int] | None = None,
        locked: bool = False, instrument_id: int = 113):
    bid_sizes = bid_sizes or [10] * 10
    ask_sizes = ask_sizes or [10] * 10
    return SimpleNamespace(
        ts_recv=ts, ts_event=ts - 100, action=action, side=side, size=size,
        instrument_id=instrument_id, levels=levels(bid_sizes, ask_sizes, locked=locked),
    )


def test_request_args_are_exact_single_mbp10_pilot() -> None:
    assert MODULE.request_args() == {
        "dataset": "GLBX.MDP3", "schema": "mbp-10", "symbols": ["6E.v.0"],
        "stype_in": "continuous", "start": "2019-01-03T15:00:00.000Z",
        "end": "2019-01-03T15:02:00.000Z",
    }


def test_depth_weighting_excludes_level_zero_and_uses_levels_two_through_ten() -> None:
    bid = [999, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    ask = [777, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    dbid, dask = MODULE.depth_sides(levels(bid, ask))
    assert dbid == sum((10 - i) * bid[i] for i in range(1, 10))
    assert dask == sum((10 - i) * ask[i] for i in range(1, 10))
    bid[0], ask[0] = 1, 1
    assert MODULE.depth_sides(levels(bid, ask)) == (dbid, dask)


def test_time_weighted_depth_mean_and_coverage() -> None:
    start = 1_000_000_000
    sec = 1_000_000_000
    base_bid = [10] * 10
    base_ask = [10] * 10
    later_bid = [20] * 10
    later_ask = [5] * 10
    records = [
        msg(start + 1 * sec, action="T", side="B", size=20,
            bid_sizes=base_bid, ask_sizes=base_ask),
        msg(start + 10 * sec, action="T", side="A", size=5,
            bid_sizes=base_bid, ask_sizes=base_ask),
        msg(start + 30 * sec, bid_sizes=later_bid, ask_sizes=later_ask),
    ]
    result = MODULE.analyze_records(records, start, start + 120 * sec)
    assert result["coverage"] == 1.0
    assert result["dbid1"] == (result["dbid0"] * 15 + result["dbid0"] * 2 * 30) / 45
    assert result["dask1"] == (result["dask0"] * 15 + result["dask0"] * 0.5 * 30) / 45
    assert result["initial_sign"] == 1
    assert result["classification"] == "CONTINUATION"


def test_initial_aggressor_sign_and_flat_tie() -> None:
    start = 5_000_000_000
    sec = 1_000_000_000
    sell = MODULE.analyze_records([
        msg(start, action="T", side="A", size=8),
        msg(start + sec, action="T", side="B", size=3),
    ], start, start + 120 * sec)
    assert sell["initial_sign"] == -1
    tie = MODULE.analyze_records([
        msg(start, action="T", side="A", size=3),
        msg(start + sec, action="T", side="B", size=3),
    ], start, start + 120 * sec)
    assert tie["initial_sign"] == 0
    assert tie["semantic_gates"]["initial_aggressor_imbalance_nonzero"] is False


def test_transfer_score_has_exhaustive_polarity() -> None:
    assert MODULE.classify_transfer(1, 100, 100, 120, 100)["classification"] == "CONTINUATION"
    assert MODULE.classify_transfer(1, 100, 100, 80, 100)["classification"] == "REVERSAL"
    assert MODULE.classify_transfer(-1, 100, 100, 120, 100)["direction"] == 1
    assert MODULE.classify_transfer(1, 100, 100, 100, 100)["classification"] == "FLAT"
    assert MODULE.classify_transfer(0, 100, 100, 120, 100)["classification"] == "FLAT"


def test_invalid_gap_reduces_coverage_and_parks() -> None:
    start = 10_000_000_000
    sec = 1_000_000_000
    bad = [10] * 10
    bad[4] = 0
    records = [
        msg(start, action="T", side="B", size=2),
        msg(start + 15 * sec, bid_sizes=bad),
        msg(start + 20 * sec),
    ]
    result = MODULE.analyze_records(records, start, start + 120 * sec)
    assert result["coverage"] == 40 / 45
    assert result["verdict"] == "PARK_SOURCE_SEMANTICS"


def test_locked_crossed_over_50ms_parks() -> None:
    start = 20_000_000_000
    ms = 1_000_000
    records = [
        msg(start, action="T", side="B", size=2),
        msg(start + 20 * ms, locked=True),
        msg(start + 80 * ms),
    ]
    result = MODULE.analyze_records(records, start, start + 120_000 * ms)
    assert result["max_locked_crossed_duration_ms"] == 60
    assert result["semantic_gates"]["no_locked_crossed_over_50ms"] is False


def test_clock_and_instrument_integrity_fail_closed() -> None:
    start = 30_000_000_000
    records = [
        msg(start + 2, action="T", side="B", instrument_id=1),
        msg(start + 1, instrument_id=2),
        msg(start - 1, instrument_id=2),
    ]
    result = MODULE.analyze_records(records, start, start + 120_000_000_000)
    assert result["monotonicity_violation_count"] == 2
    assert result["containment_violation_count"] == 1
    assert result["semantic_gates"]["single_instrument_id"] is False


def test_source_has_one_serial_paid_call_surface_and_no_batch_or_subscription() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert source.count("client.timeseries.get_range(") == 1
    assert ".batch." not in source
    assert ".subscribe(" not in source
    assert "automatic retry forbidden" in source


def test_api_key_is_not_embedded() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "DATABENTO_API_KEY" in source
    assert not any(
        token.startswith("db-") and len(token) > 24
        for token in source.replace('"', " ").replace("'", " ").split()
    )

