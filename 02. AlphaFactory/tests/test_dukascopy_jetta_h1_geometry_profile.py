import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "research" / "dukascopy_jetta_h1_geometry_profile.py"
SPEC = importlib.util.spec_from_file_location("dukascopy_jetta_h1_geometry_profile", MODULE_PATH)
assert SPEC and SPEC.loader
PROFILE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROFILE)


def _payload(*, open_: float, high: float, low: float, close: float) -> bytes:
    return json.dumps(
        {
            "timestamp": 1_514_764_800_000,
            "multiplier": 0.01,
            "shift": 3_600_000,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "times": [0],
            "opens": [0],
            "highs": [0],
            "lows": [0],
            "closes": [0],
            "volumes": [1],
        }
    ).encode()


def test_profile_measures_required_envelope_points_without_rejecting() -> None:
    result = PROFILE._decode_geometry(
        _payload(open_=100.00, high=100.00, low=99.00, close=100.23),
        "synthetic",
        0.01,
    )
    assert result["bar_count"] == 1
    assert result["violating_bar_count"] == 1
    assert result["maximum_required_envelope_correction_points"] == 23


def test_aggregate_reports_tail_on_violations_only() -> None:
    rows = [
        {
            "bar_count": 4,
            "violating_bar_count": 2,
            "correction_points": [0, 1, 0, 4],
        }
    ]
    result = PROFILE._aggregate(rows)
    assert result["bar_count"] == 4
    assert result["violating_fraction"] == 0.5
    assert result["maximum_required_envelope_correction_points"] == 4
    assert result["violating_only_correction_points_percentiles"]["p50"] == 1


def test_pair_open_stats_profiles_crosses_without_clamping() -> None:
    result = PROFILE._pair_open_stats(
        {1: 100, 2: 110, 3: 120},
        {1: 102, 2: 108, 3: 120},
    )
    assert result["common_timestamp_count"] == 3
    assert result["crossed_open_count"] == 1
    assert result["maximum_crossed_open_deficit_points"] == 2
    assert result["minimum_uncrossed_spread_points"] == 0


def test_aggregate_open_pairs_proves_crosses_are_pre_activation() -> None:
    rows = [
        {
            "common_timestamp_count": 3,
            "bid_only_timestamp_count": 0,
            "ask_only_timestamp_count": 0,
            "crossed_deficit_points": [2],
            "crossed_open_rows": [
                {
                    "epoch": 2,
                    "bid_open_points": 110,
                    "ask_open_points": 108,
                    "crossed_open_deficit_points": 2,
                }
            ],
        }
    ]
    result = PROFILE._aggregate_open_pairs(
        rows, point=0.01, strategy_active_from_epoch=3
    )
    assert result["maximum_crossed_open_deficit_price"] == 0.02
    assert result["crossed_open_before_activation_count"] == 1
    assert result["crossed_open_on_or_after_activation_count"] == 0
    assert result["all_crossed_opens_strictly_pre_activation"] is True
