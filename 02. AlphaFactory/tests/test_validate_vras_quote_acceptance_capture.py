from __future__ import annotations

import csv
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "validate_vras_quote_acceptance_capture.py"
SPEC = importlib.util.spec_from_file_location("quote_capture_validator", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _row(event: str, event_msc: int, *, direction: str = "long", **overrides):
    arm_msc = 1_800_000_000_000
    row = {
        "schema_version": MODULE.SCHEMA,
        "hypothesis_id": MODULE.HYPOTHESIS,
        "run_id": "RUN-001",
        "event_time_msc": event_msc,
        "event_time_utc": _utc(event_msc),
        "symbol": "EURUSD",
        "event": event,
        "direction": direction,
        "arm_bar_time": "2027.01.15 10:00:00",
        "arm_time_msc": arm_msc,
        "age_ms": event_msc - arm_msc,
        "bid": 1.10020,
        "ask": 1.10022,
        "mid": 1.10021,
        "spread_points": 2.0,
        "prearm_median_spread_points": 2.0,
        "quote_updates": 20,
        "price_changes": 12,
        "directional_moves": 8,
        "opposite_moves": 4,
        "imbalance": 8 / 12,
        "directional_net_points": 2.0,
        "max_gap_ms": 1000,
        "max_spread_ratio": 1.0,
        "frozen_vwap": 1.10000,
        "data_source": "LIVE_QUOTES",
        "promotion_eligible": "false",
    }
    row.update(overrides)
    return row


def _write(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MODULE.FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_valid_accepted_arm(tmp_path: Path):
    start = 1_800_000_000_000
    path = tmp_path / "valid.csv"
    _write(path, [_row("ARMED", start), _row("ACCEPTED_OBSERVATION", start + 30_000)])
    result = MODULE.validate(path, "LIVE_QUOTES")
    assert result["status"] == "PASS"
    assert result["arms"] == result["accepted_observations"] == 1
    assert result["performance_metrics_authorized"] is False
    assert result["order_activity_verification"].startswith("OUT_OF_SCOPE")
    assert "orders_sent" not in result


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("quote_updates", 19, "count/imbalance"),
        ("price_changes", 11, "count/imbalance"),
        ("imbalance", 0.59, "count/imbalance"),
        ("directional_net_points", 1.99, "expansion"),
        ("spread_points", 2.01, "spread gate"),
        ("max_spread_ratio", 1.51, "spread gate"),
        ("max_gap_ms", 15001, "stale-gap"),
        ("bid", 1.10000, "VWAP"),
    ],
)
def test_acceptance_is_fail_closed_per_gate(tmp_path: Path, field: str, value, message: str):
    start = 1_800_000_000_000
    path = tmp_path / f"bad-{field}.csv"
    accepted = _row("ACCEPTED_OBSERVATION", start + 30_000, **{field: value})
    if field == "price_changes":
        accepted["directional_moves"] = 7
        accepted["opposite_moves"] = 4
        accepted["imbalance"] = 7 / 11
    if field == "bid":
        accepted["mid"] = (accepted["bid"] + accepted["ask"]) / 2
    _write(path, [_row("ARMED", start), accepted])
    with pytest.raises(ValueError, match=message):
        MODULE.validate(path)


def test_rejects_non_monotonic_nested_and_unterminated_arms(tmp_path: Path):
    start = 1_800_000_000_000
    nonmono = tmp_path / "nonmono.csv"
    _write(nonmono, [_row("ARMED", start), _row("OBSERVE", start)])
    with pytest.raises(ValueError, match="strictly increasing"):
        MODULE.validate(nonmono)

    nested = tmp_path / "nested.csv"
    _write(nested, [_row("ARMED", start), _row("ARMED", start + 1)])
    with pytest.raises(ValueError, match="nested arm"):
        MODULE.validate(nested)

    open_arm = tmp_path / "open.csv"
    _write(open_arm, [_row("ARMED", start)])
    with pytest.raises(ValueError, match="non-terminal active arm"):
        MODULE.validate(open_arm)


def test_rejection_terminal_reason_must_be_true(tmp_path: Path):
    start = 1_800_000_000_000
    path = tmp_path / "false-reject.csv"
    _write(path, [_row("ARMED", start), _row("REJECT_SPREAD_SPIKE", start + 1)])
    with pytest.raises(ValueError, match="no spike"):
        MODULE.validate(path)


def test_header_only_is_valid_no_arms(tmp_path: Path):
    path = tmp_path / "empty.csv"
    _write(path, [])
    result = MODULE.validate(path)
    assert result["verdict"] == "VALID_NO_ARMS"
    assert result["row_count"] == 0
