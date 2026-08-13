from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_event_depth_transfer_002_pilot.py"
SPEC = importlib.util.spec_from_file_location("event_depth_transfer_002", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_revision_changes_only_window_identity_and_cost_cap() -> None:
    args = MODULE.request_args()
    assert args == {
        "dataset": "GLBX.MDP3", "schema": "mbp-10", "symbols": ["6E.v.0"],
        "stype_in": "continuous", "start": "2019-01-03T15:00:00.000Z",
        "end": "2019-01-03T15:01:00.000Z",
    }
    assert MODULE.OWNER_CEILING_USD == 0.02
    assert MODULE.ENGINE.BASELINE_SECONDS == 15
    assert MODULE.ENGINE.DECISION_SECONDS == 60
    assert MODULE.ENGINE.MIN_COVERAGE == 0.99


def test_reviewed_engine_hash_is_current() -> None:
    engine_path = MODULE_PATH.with_name("acquire_event_depth_transfer_001_pilot.py")
    assert MODULE.ENGINE.sha256_file(engine_path) == MODULE.ENGINE_SHA256


def test_combined_source_has_exactly_one_paid_call_and_no_batch_or_subscription() -> None:
    wrapper = MODULE_PATH.read_text(encoding="utf-8")
    engine_path = MODULE_PATH.with_name("acquire_event_depth_transfer_001_pilot.py")
    engine = engine_path.read_text(encoding="utf-8")
    combined = wrapper + engine
    assert combined.count("client.timeseries.get_range(") == 1
    assert ".batch." not in combined
    assert ".subscribe(" not in combined


def test_engine_formula_remains_level_two_to_ten_and_exhaustive() -> None:
    level = type("Level", (), {})
    levels = []
    for index in range(10):
        item = level()
        item.bid_px = 1000 - index
        item.ask_px = 1001 + index
        item.bid_sz = 999 if index == 0 else index
        item.ask_sz = 777 if index == 0 else 10 - index
        levels.append(item)
    bid, ask = MODULE.ENGINE.depth_sides(levels)
    assert bid == sum((10 - i) * i for i in range(1, 10))
    assert ask == sum((10 - i) * (10 - i) for i in range(1, 10))
    assert MODULE.ENGINE.classify_transfer(1, 100, 100, 120, 100)["classification"] == "CONTINUATION"
    assert MODULE.ENGINE.classify_transfer(1, 100, 100, 80, 100)["classification"] == "REVERSAL"
    assert MODULE.ENGINE.classify_transfer(1, 100, 100, 100, 100)["classification"] == "FLAT"

