from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd


PATH = Path(__file__).resolve().parents[1] / "analyze_kvo_h1_source.py"
SPEC = spec_from_file_location("kvo", PATH)
MODULE = module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def synthetic(rows: int = 140) -> pd.DataFrame:
    index = np.arange(rows, dtype=float)
    close = 1.1 + 0.0002 * index + 0.003 * np.sin(index / 4.0)
    high = close + 0.001 + 0.0002 * np.cos(index / 3.0)
    low = close - 0.001 - 0.0001 * np.sin(index / 5.0)
    times = pd.date_range("2017-12-20", periods=rows, freq="h", tz="UTC")
    return pd.DataFrame({"symbol": "EURUSD", "timeframe": "H1",
                         "source_epoch": times.astype("int64") // 1_000_000_000,
                         "time_utc": times, "utc_ambiguous": False,
                         "high": high, "low": low, "close": close,
                         "tick_volume": (100 + index % 17).astype(int)})


def test_klinger_seeds_are_exact() -> None:
    ind = MODULE.calculate_indicators(synthetic())
    assert np.isnan(ind["ema34"][33]) and np.isfinite(ind["ema34"][34])
    assert np.isnan(ind["ema55"][54]) and np.isfinite(ind["ema55"][55])
    assert np.isnan(ind["signal"][66]) and np.isfinite(ind["signal"][67])
    assert np.isnan(ind["ema100"][98]) and np.isfinite(ind["ema100"][99])


def test_trend_equality_is_minus_one_and_vf_has_no_absolute_value() -> None:
    data = synthetic()
    data.loc[1, ["high", "low", "close"]] = data.loc[0, ["high", "low", "close"]].to_numpy()
    ind = MODULE.calculate_indicators(data)
    assert ind["trend"][1] == -1.0
    expected = (data.at[1, "tick_volume"] * 2.0 *
                (ind["dm"][1] / ind["cm"][1] - 1.0) * -1.0 * 100.0)
    assert ind["vf"][1] == expected


def test_zero_cm_fails_closed() -> None:
    data = synthetic()
    data.loc[0:1, "high"] = data.loc[0:1, "close"]
    data.loc[0:1, "low"] = data.loc[0:1, "close"]
    try:
        MODULE.calculate_indicators(data)
    except ValueError as exc:
        assert "CM is zero" in str(exc)
    else:
        raise AssertionError("zero CM must fail")


def test_event_allowlist_is_outcome_blind() -> None:
    forbidden = {"entry", "exit", "return", "pnl", "profit_factor", "cost"}
    assert not (MODULE.EVENT_KEYS & forbidden)


def test_claimed_analyzer_and_final_input_rehash_are_required() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert 'initial["analyzer"] != claimed_analyzer_sha' in source
    assert "if final != initial" in source
    assert '"test": test_path' in source


def test_exact_next_and_decision_year_are_frozen() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert "pd.Timedelta(hours=1)" in source
    assert "+ 3600" in source
    assert 'pd.Timestamp(row["decision_time_utc"]).year' in source
    assert '"next_row_ohlc_read": False' in source


def test_fsm_existing_state_is_evaluated_before_idle_arm() -> None:
    source = PATH.read_text(encoding="utf-8")
    long_branch = source.index("if state == LONG_ARMED")
    short_branch = source.index("elif state == SHORT_ARMED", long_branch)
    idle_branch = source.index("else:\n            if ko[index] < 0.0", short_branch)
    assert long_branch < short_branch < idle_branch
