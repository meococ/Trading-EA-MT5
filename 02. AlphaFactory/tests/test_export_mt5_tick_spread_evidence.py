from __future__ import annotations

import importlib.util
from pathlib import Path


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
