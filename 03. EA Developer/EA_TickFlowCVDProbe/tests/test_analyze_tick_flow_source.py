import csv
import importlib.util
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "analyze_tick_flow_source.py"
SPEC = importlib.util.spec_from_file_location("tick_flow_analysis", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def base_row(**overrides: str) -> dict[str, str]:
    row = {
        "schema_version": MODULE.SCHEMA,
        "hypothesis_id": MODULE.HYPOTHESIS_ID,
        "run_id": "unit",
        "symbol": "XAUUSD",
        "timeframe": "M5",
        "bar_start_server": "2018.01.01 00:00:00",
        "bar_end_server": "2018.01.01 00:05:00",
        "gap_from_prev_bars": "0",
        "total_ticks": "100",
        "valid_quote_ticks": "100",
        "invalid_ticks": "0",
        "exact_duplicate_ticks": "0",
        "unique_quote_updates": "100",
        "classified_updates": "100",
        "up_updates": "70",
        "down_updates": "30",
        "zero_mid_updates": "0",
        "unclassified_updates": "0",
        "quote_tick_delta": "40",
        "delta_high": "40",
        "delta_low": "0",
        "mid_open": "2000.0",
        "mid_high": "2001.0",
        "mid_low": "1999.0",
        "mid_close": "1999.8",
        "mid_range_points": "200.0",
        "spread_mean_points": "20.0",
        "spread_max_points": "25.0",
        "trade_flag_ticks": "0",
        "buy_flag_ticks": "0",
        "sell_flag_ticks": "0",
        "positive_volume_ticks": "0",
        "bar_complete": "true",
        "promotion_eligible": "false",
    }
    row.update(overrides)
    return row


def test_candidate_is_absorption_and_opposite_delta() -> None:
    assert MODULE.is_candidate(base_row()) == (True, "short")
    assert MODULE.is_candidate(base_row(quote_tick_delta="-40", mid_close="2000.2")) == (True, "long")


def test_candidate_rejects_price_followthrough_or_sparse_ticks() -> None:
    assert MODULE.is_candidate(base_row(mid_close="2000.8")) == (False, None)
    assert MODULE.is_candidate(base_row(unique_quote_updates="19")) == (False, None)


def test_analyzer_rejects_outcome_columns(tmp_path: Path) -> None:
    row = base_row()
    row["future_return"] = "1.0"
    path = tmp_path / "bad.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    try:
        MODULE.analyze(path, 100.0)
    except ValueError as exc:
        assert "forbidden outcome columns" in str(exc)
    else:
        raise AssertionError("outcome column was accepted")
