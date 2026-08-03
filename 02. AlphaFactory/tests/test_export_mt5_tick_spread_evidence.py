from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ALPHA_ROOT = Path(__file__).resolve().parents[1]
EXPORTER_PATH = ALPHA_ROOT / "tools" / "export_mt5_tick_spread_evidence.py"


def _load_exporter():
    spec = importlib.util.spec_from_file_location("tick_spread_exporter", EXPORTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_first_valid_tick_is_selected_for_each_expected_bar() -> None:
    exporter = _load_exporter()
    ticks = [
        {"time": 1, "time_msc": 1_000, "bid": 100.0, "ask": 99.9},
        {"time": 2, "time_msc": 2_000, "bid": 100.0, "ask": 100.1},
        {"time": 3, "time_msc": 3_000, "bid": 100.1, "ask": 100.2},
        {"time": 305, "time_msc": 305_000, "bid": 101.0, "ask": 101.1},
        {"time": 900, "time_msc": 900_000, "bid": 102.0, "ask": 102.1},
    ]

    selected = exporter.first_valid_tick_by_bar(ticks, {0, 300, 600})

    assert selected == {
        0: (2_000, 100.0, 100.1),
        300: (305_000, 101.0, 101.1),
    }


def test_out_of_population_ticks_are_never_selected() -> None:
    exporter = _load_exporter()
    selected = exporter.first_valid_tick_by_bar(
        [{"time": 300, "time_msc": 300_000, "bid": 100.0, "ask": 100.1}],
        {0},
    )
    assert selected == {}


def test_vectorized_selection_matches_mapping_contract() -> None:
    exporter = _load_exporter()
    ticks = np.array(
        [
            (305, 305_000, 101.0, 101.1),
            (2, 2_000, 100.0, 100.1),
            (1, 1_000, 100.0, 99.9),
            (3, 3_000, 100.1, 100.2),
            (900, 900_000, 102.0, 102.1),
        ],
        dtype=[("time", "i8"), ("time_msc", "i8"), ("bid", "f8"), ("ask", "f8")],
    )

    selected = exporter.first_valid_tick_by_bar_array(ticks, {0, 300, 600})

    assert selected == {
        0: (2_000, 100.0, 100.1),
        300: (305_000, 101.0, 101.1),
    }


def test_vectorized_selection_rejects_missing_fields() -> None:
    exporter = _load_exporter()
    ticks = np.array([(1, 1_000)], dtype=[("time", "i8"), ("time_msc", "i8")])

    try:
        exporter.first_valid_tick_by_bar_array(ticks, {0})
    except ValueError as exc:
        assert "bid" in str(exc) and "ask" in str(exc)
    else:
        raise AssertionError("missing tick geometry must fail closed")


def test_vectorized_selection_preserves_raw_order_for_same_millisecond() -> None:
    exporter = _load_exporter()
    ticks = np.array(
        [
            (1, 1_000, 100.0, 100.2),
            (1, 1_000, 100.0, 100.1),
        ],
        dtype=[("time", "i8"), ("time_msc", "i8"), ("bid", "f8"), ("ask", "f8")],
    )

    assert exporter.first_valid_tick_by_bar_array(ticks, {0}) == {
        0: (1_000, 100.0, 100.2)
    }


def test_exporter_receipt_tracks_total_raw_tick_population() -> None:
    source = EXPORTER_PATH.read_text(encoding="utf-8")

    assert "raw_tick_count = 0" in source
    assert "raw_tick_count += len(ticks)" in source
    assert '"raw_tick_count": raw_tick_count' in source
    assert "tick_times_msc < chunk_end_msc" in source
