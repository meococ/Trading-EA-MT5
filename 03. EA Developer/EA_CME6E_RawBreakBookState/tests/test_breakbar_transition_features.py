from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "extract_cme6e_breakbar_transition_features.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "extract_cme6e_breakbar_transition_features", MODULE_PATH
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


def message(seconds: float, bid_size: int, ask_size: int, recv_seconds: float | None = None):
    return SimpleNamespace(
        ts_event=int(seconds * 1_000_000_000),
        ts_recv=int((seconds if recv_seconds is None else recv_seconds) * 1_000_000_000),
        levels=[level(bid_size, ask_size) for _ in range(5)],
    )


def request(direction: str = "BUY") -> dict:
    return {
        "position_id": "1",
        "direction": direction,
        "break_bar_open": "1970-01-01T00:00:00Z",
        "actual_decision": "1970-01-01T00:05:00Z",
        "start": "1970-01-01T00:00:00Z",
        "end": "1970-01-01T00:05:00Z",
        "duration_seconds": 300,
        "filename": "sample.dbn.zst",
    }


def test_transition_score_uses_full_break_bar_and_strict_actual_decision_cutoff() -> None:
    module = load_module()
    messages = [
        message(10, 2, 8),
        message(50, 2, 8),
        message(240, 8, 2),
        message(280, 8, 2),
        message(299, 9, 1, recv_seconds=301),  # received after decision: forbidden
        message(301, 9, 1),  # event after decision: forbidden
    ]

    row = module.compute_feature_row(request(), messages)

    assert row["causal_records"] == 4
    assert row["records_early_60s"] == 2
    assert row["records_late_60s"] == 2
    assert row["aligned_imbalance_median_early60"] == pytest.approx(-0.6)
    assert row["aligned_imbalance_median_late60"] == pytest.approx(0.6)
    assert row["aligned_imbalance_transition"] == pytest.approx(1.2)
    assert row["aligned_persistence_full"] == pytest.approx(0.5)
    assert row["book_transition_score"] == pytest.approx(0.65)
    assert row["staleness_ms"] == pytest.approx(20_000.0)
    assert "net" not in row and "realized_r" not in row


def test_direction_alignment_flips_transition_score() -> None:
    module = load_module()
    messages = [
        message(10, 2, 8),
        message(50, 2, 8),
        message(240, 8, 2),
        message(280, 8, 2),
    ]

    row = module.compute_feature_row(request("SELL"), messages)

    assert row["aligned_imbalance_median_early60"] == pytest.approx(0.6)
    assert row["aligned_imbalance_median_late60"] == pytest.approx(-0.6)
    assert row["aligned_imbalance_transition"] == pytest.approx(-1.2)
    assert row["book_transition_score"] == pytest.approx(-0.65)


def test_quality_surface_is_outcome_blind_and_fail_closed() -> None:
    module = load_module()
    base = {
        "source_status": "nonempty",
        "causal_records": 30,
        "records_early_60s": 5,
        "records_late_60s": 5,
        "records_final_30s": 3,
        "spread_ticks_last": 1.0,
        "staleness_ms": 500.0,
        "book_transition_score": 0.1,
    }

    assert module.quality_eligibility(base) == (True, "PASS")
    assert module.quality_eligibility({**base, "causal_records": 29}) == (
        False,
        "INSUFFICIENT_CAUSAL_RECORDS",
    )
    assert module.quality_eligibility({**base, "records_early_60s": 4}) == (
        False,
        "INSUFFICIENT_EARLY_RECORDS",
    )
    assert module.quality_eligibility({**base, "records_late_60s": 4}) == (
        False,
        "INSUFFICIENT_LATE_RECORDS",
    )
    assert module.quality_eligibility({**base, "staleness_ms": 10_001}) == (
        False,
        "STALE_BOOK",
    )
