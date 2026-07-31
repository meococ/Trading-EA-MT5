from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "extract_cme6e_raw_break_features.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "extract_cme6e_raw_break_features", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def level(bid_size: int, ask_size: int):
    return SimpleNamespace(
        bid_px=1.10000,
        ask_px=1.10005,
        bid_sz=bid_size,
        ask_sz=ask_size,
    )


def message(seconds: float, bid_size: int, ask_size: int):
    return SimpleNamespace(
        ts_event=int(seconds * 1_000_000_000),
        ts_recv=int(seconds * 1_000_000_000),
        levels=[level(bid_size, ask_size) for _ in range(5)],
    )


def test_score_uses_only_causal_last_30_seconds_and_fixed_weights() -> None:
    module = load_module()
    request = {
        "position_id": "1",
        "direction": "BUY",
        "start": "1970-01-01T00:01:00Z",
        "end": "1970-01-01T00:01:40Z",
        "filename": "sample.dbn.zst",
    }
    messages = [
        message(60, 2, 8),
        message(80, 8, 2),
        message(90, 9, 1),
        message(101, 1, 9),  # arrives after the decision and must be ignored
    ]

    row = module.compute_feature_row(request, messages, degraded_dates=set())

    assert row["causal_records"] == 3
    assert row["records_last_30s"] == 2
    assert row["aligned_imbalance_median_30s"] == pytest.approx(0.7)
    assert row["aligned_imbalance_change_30s"] == pytest.approx(1.3)
    assert row["aligned_persistence_30s"] == pytest.approx(1.0)
    assert row["book_alignment_score"] == pytest.approx(0.85)
    assert row["spread_ticks_last"] == pytest.approx(1.0)
    assert row["staleness_ms"] == pytest.approx(10_000.0)
    assert "net" not in row and "realized_r" not in row


def test_direction_alignment_flips_the_same_book_state() -> None:
    module = load_module()
    request = {
        "position_id": "2",
        "direction": "SELL",
        "start": "1970-01-01T00:01:00Z",
        "end": "1970-01-01T00:01:40Z",
        "filename": "sample.dbn.zst",
    }
    messages = [message(60, 2, 8), message(80, 8, 2), message(90, 9, 1)]

    row = module.compute_feature_row(request, messages, degraded_dates=set())

    assert row["aligned_imbalance_median_30s"] == pytest.approx(-0.7)
    assert row["aligned_persistence_30s"] == pytest.approx(0.0)
    assert row["book_alignment_score"] == pytest.approx(-0.85)


def test_dbn_fixed_point_prices_are_normalized_before_spread_ticks() -> None:
    module = load_module()
    raw_level = SimpleNamespace(
        bid_px=1_100_000_000,
        ask_px=1_100_050_000,
        bid_sz=10,
        ask_sz=10,
    )
    raw_message = SimpleNamespace(
        ts_event=1,
        ts_recv=1,
        levels=[raw_level for _ in range(5)],
    )

    observation = module._observation(raw_message)

    assert observation is not None
    assert observation["spread_ticks"] == pytest.approx(1.0)


def test_quality_eligibility_is_outcome_blind_and_fail_closed() -> None:
    module = load_module()
    base = {
        "source_status": "nonempty",
        "degraded_source_date": False,
        "causal_records": 20,
        "records_last_30s": 8,
        "spread_ticks_last": 1.0,
        "staleness_ms": 500.0,
        "book_alignment_score": 0.10,
    }

    assert module.quality_eligibility(base) == (True, "PASS")
    assert module.quality_eligibility({**base, "degraded_source_date": True}) == (
        False,
        "DEGRADED_SOURCE_DATE",
    )
    assert module.quality_eligibility({**base, "records_last_30s": 4}) == (
        False,
        "INSUFFICIENT_LAST30_RECORDS",
    )
    assert module.quality_eligibility({**base, "staleness_ms": 10_001.0}) == (
        False,
        "STALE_BOOK",
    )


def test_real_source_contract_is_hash_bound_and_outcome_blind() -> None:
    module = load_module()
    contract = module.load_source_contract()

    assert len(contract["plan"]["requests"]) == 541
    assert len(contract["plan"]["metadata_empty_windows"]) == 6
    assert len(contract["manifest"]["downloads"]) == 541
    assert contract["receipt"]["decoded_records"] == 353598
    assert contract["degraded_dates"] == {
        "2019-01-15",
        "2019-02-22",
        "2020-02-27",
        "2020-06-30",
        "2020-07-01",
    }
    assert contract["receipt"]["outcome_fields_used"] is False
    assert contract["receipt"]["sealed_oos_opened"] is False
