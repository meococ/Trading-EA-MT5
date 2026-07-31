from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "build_eurfxofi_012_source_classifier.py"
SPEC = importlib.util.spec_from_file_location("eurfxofi012", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@dataclass
class WindowSpec:
    request_id: str = "TEST"
    local_date: str = "2020-01-02"
    split: str = "TRAIN"
    start: str = "2020-01-02T13:14:45Z"
    end: str = "2020-01-02T13:15:00Z"
    filename: str | None = "TEST.dbn.zst"
    source_empty: bool = False
    expected_bytes: int = 1
    expected_sha256: str | None = "A" * 64
    expected_records: int = 1


class V1:
    @staticmethod
    def _side_labels(series: pd.Series) -> pd.Series:
        return series.astype(str).str.upper().replace({"NONE": "N", "": "N"})


def _frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    data = pd.DataFrame(rows)
    data["ts_event"] = pd.to_datetime(data["ts_event"], utc=True)
    data["ts_recv"] = pd.to_datetime(data.pop("ts_recv"), utc=True)
    return data.set_index("ts_recv")


def _classify(rows: list[dict[str, object]]) -> tuple[dict[str, object], list[str]]:
    captured: list[str] = []

    def original(proxy: pd.DataFrame, spec: WindowSpec) -> dict[str, object]:
        captured.extend(proxy["side"].tolist())
        return {"request_id": spec.request_id}

    result = MODULE.aggregate_window_frame_012(
        V1(), original, _frame(rows), WindowSpec(expected_records=len(rows))
    )
    return result, captured


def _row(second: int, side: str, price: float, bid: float | None, ask: float | None, size: int = 1) -> dict[str, object]:
    return {
        "ts_recv": f"2020-01-02T13:14:{second:02d}.000500Z",
        "ts_event": f"2020-01-02T13:14:{second:02d}.000000Z",
        "side": side,
        "price": price,
        "bid_px_00": bid,
        "ask_px_00": ask,
        "size": size,
    }


def test_disarmed_sentinel_normalization_is_stable() -> None:
    assert MODULE.REVIEWED_REGISTRY_ROW_SHA256 is None
    payload = SCRIPT.read_bytes()
    base = MODULE.normalized_builder_base_sha256(payload)
    armed = payload.replace(
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None",
        b'REVIEWED_REGISTRY_ROW_SHA256: str | None = "' + b"A" * 64 + b'"',
        1,
    )
    assert MODULE.normalized_builder_base_sha256(armed) == base


def test_direct_side_is_trusted_and_audited_against_quote() -> None:
    result, sides = _classify([
        _row(46, "B", 1.1001, 1.1000, 1.1001, 2),
        _row(47, "A", 1.1000, 1.1000, 1.1001, 3),
    ])
    assert sides == ["B", "A"]
    assert result["direct_count"] == 2
    assert result["direct_volume"] == 5
    assert result["direct_quote_comparable_count"] == 2
    assert result["direct_quote_agree_count"] == 2


def test_unknown_side_uses_quote_touch_then_midpoint() -> None:
    result, sides = _classify([
        _row(46, "N", 1.1001, 1.1000, 1.1001, 2),
        _row(47, "N", 1.1000, 1.1000, 1.1001, 3),
        _row(48, "N", 1.100075, 1.1000, 1.1001, 4),
        _row(49, "N", 1.100025, 1.1000, 1.1001, 5),
    ])
    assert sides == ["B", "A", "B", "A"]
    assert result["quote_touch_count"] == 2
    assert result["quote_touch_volume"] == 5
    assert result["quote_mid_count"] == 2
    assert result["quote_mid_volume"] == 9
    assert result["residual_unknown_count"] == 0


def test_tick_rule_and_equal_price_carry_are_sequential_and_window_local() -> None:
    result, sides = _classify([
        _row(46, "N", 1.1000, None, None, 1),
        _row(47, "N", 1.1001, None, None, 2),
        _row(48, "N", 1.1001, None, None, 3),
        _row(49, "N", 1.1000, None, None, 4),
    ])
    assert sides == ["N", "B", "B", "A"]
    assert result["residual_unknown_count"] == 1
    assert result["tick_count"] == 2
    assert result["tick_carry_count"] == 1
    assert result["tick_volume"] == 6
    assert result["tick_carry_volume"] == 3


def test_receive_time_range_is_authoritative_not_publisher_event() -> None:
    row = _row(45, "N", 1.1001, 1.1000, 1.1001)
    row["ts_recv"] = "2020-01-02T13:14:45.000100Z"
    row["ts_event"] = "2020-01-02T13:14:44.999000Z"
    result, sides = _classify([row])
    assert sides == ["B"]
    assert result["ts_recv_outside_count"] == 0
    assert result["event_before_start_count"] == 1


def test_receive_time_outside_range_fails_closed() -> None:
    row = _row(45, "B", 1.1001, 1.1000, 1.1001)
    row["ts_recv"] = "2020-01-02T13:14:44.999999999Z"
    with pytest.raises(MODULE.SourceQualityError, match="ts_recv outside"):
        _classify([row])


def test_source_empty_has_zero_classifier_counters() -> None:
    result = MODULE.aggregate_window_frame_012(
        V1(), lambda frame, spec: {}, pd.DataFrame(), WindowSpec(source_empty=True, filename=None, expected_records=0)
    )
    assert result["direct_classified_count"] == 0
    assert result["residual_unknown_volume"] == 0


def test_render_diagnostics_do_not_use_incompatible_indicator_trace() -> None:
    assert "go.Indicator" not in SCRIPT.read_text(encoding="utf-8")


def test_authority_fails_while_disarmed(tmp_path: Path) -> None:
    with pytest.raises(MODULE.SourceQualityError, match="not armed"):
        MODULE.verify_authority(tmp_path)
