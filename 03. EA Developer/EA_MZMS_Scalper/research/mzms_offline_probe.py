"""Frozen two-arm MZMS offline probe.

This script is intentionally strategy-specific. It reads only 2019-2022
FivePercent EURUSD M1 bid bars, creates server-aligned M5 bars, evaluates the
frozen matched control and MZMS challenger, and writes one diagnostic result.
It does not optimize, access 2023+, or confer Model-0/live authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-003"
PLAN_SHA256 = "68D75BEA0C8D2A457F4DF7B47D9D70DAC58FE0824895FD74CD3F8358AF24FBB6"
REPORT_SHA256 = "0D8D8314273320FF2305557844C8200A9D4052F26D5F30039558B5951A361050"
DATA_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
NEWS_SHA256 = "80B9DE46517B42F8B1D9A3ACCEFA6CC6D3DCB4DD06CAE357F16DE46228C64307"
DESIGN_START = pd.Timestamp("2019-01-02")
DESIGN_END_EXCLUSIVE = pd.Timestamp("2022-01-01")
VALIDATION_START = pd.Timestamp("2022-01-01")
END_EXCLUSIVE = pd.Timestamp("2022-12-31")
PIP = 0.0001


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def histogram_turn(
    hist1: float,
    hist2: float,
    hist3: float,
    atr1: float,
    min_delta_atr: float,
) -> int:
    """Return +1/-1 only for a completed local extremum and sufficient delta."""
    if not all(math.isfinite(v) for v in (hist1, hist2, hist3, atr1)) or atr1 <= 0.0:
        return 0
    if hist1 > hist2 and hist2 < hist3 and hist2 <= 0.0:
        return 1 if (hist1 - hist2) / atr1 + 1e-15 >= min_delta_atr else 0
    if hist1 < hist2 and hist2 > hist3 and hist2 >= 0.0:
        return -1 if (hist2 - hist1) / atr1 + 1e-15 >= min_delta_atr else 0
    return 0


def spread_allowed(spread_pips: float, max_pips: float) -> bool:
    return math.isfinite(spread_pips) and 0.0 < spread_pips <= max_pips


def position_released(entry_time: np.datetime64, prior_exit_time: np.datetime64) -> bool:
    """Equality is ambiguous: the prior M1 exit can occur after this bar open."""
    return entry_time > prior_exit_time


def resolve_bar_exit(direction: int, low: float, high: float, stop: float, target: float) -> str | None:
    """Conservative same-M1 collision rule: stop always wins."""
    if direction > 0:
        stop_hit, target_hit = low <= stop, high >= target
    else:
        stop_hit, target_hit = high >= stop, low <= target
    if stop_hit:
        return "STOP"
    if target_hit:
        return "TARGET"
    return None


def mt5_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def mt5_smma(series: pd.Series, period: int) -> pd.Series:
    values = series.to_numpy(dtype=float)
    out = np.full(len(values), np.nan, dtype=float)
    if len(values) <= period:
        return pd.Series(out, index=series.index)
    first = 1 if np.isnan(values[0]) else 0
    start = first + period - 1
    if start >= len(values):
        return pd.Series(out, index=series.index)
    out[start] = np.nanmean(values[first : first + period])
    for idx in range(start + 1, len(values)):
        out[idx] = (out[idx - 1] * (period - 1) + values[idx]) / period
    return pd.Series(out, index=series.index)


def mt5_rsi(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta).clip(lower=0.0)
    avg_gain = mt5_smma(gains, period)
    avg_loss = mt5_smma(losses, period)
    denom = avg_gain + avg_loss
    return (100.0 * avg_gain / denom).where(denom != 0.0, 50.0)


def mt5_atr(frame: pd.DataFrame, period: int) -> pd.Series:
    previous = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous).abs(),
            (frame["low"] - previous).abs(),
        ],
        axis=1,
    ).max(axis=1)
    # AlphaFactory parity harness proves MT5 iATR uses the simple TR average.
    return true_range.rolling(period).mean()


def mt5_adx(frame: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = frame["high"], frame["low"], frame["close"]
    up = high.diff().to_numpy(float)
    down = (-low.diff()).to_numpy(float)
    positive = np.where(up > 0.0, up, 0.0)
    negative = np.where(down > 0.0, down, 0.0)
    plus_dm = pd.Series(np.where(positive > negative, positive, 0.0), index=frame.index)
    minus_dm = pd.Series(np.where(negative > positive, negative, 0.0), index=frame.index)
    previous = close.shift(1)
    true_range = pd.concat([high, previous], axis=1).max(axis=1) - pd.concat(
        [low, previous], axis=1
    ).min(axis=1)
    raw_plus = (100.0 * plus_dm / true_range).where(true_range != 0.0, 0.0)
    raw_minus = (100.0 * minus_dm / true_range).where(true_range != 0.0, 0.0)
    plus_di = raw_plus.iloc[1:].ewm(span=period, adjust=False).mean()
    minus_di = raw_minus.iloc[1:].ewm(span=period, adjust=False).mean()
    denominator = plus_di + minus_di
    dx = (100.0 * (plus_di - minus_di).abs() / denominator).where(denominator != 0.0, 0.0)
    return dx.ewm(span=period, adjust=False).mean().reindex(frame.index)


def build_m5(m1: pd.DataFrame) -> pd.DataFrame:
    indexed = m1.set_index("time_server", drop=False)
    grouped = indexed.resample("5min", label="left", closed="left")
    m5 = grouped.agg(
        time_utc=("time_utc", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        spread=("spread", "first"),
        minute_count=("close", "count"),
    )
    m5 = m5[m5["minute_count"] > 0].copy()
    m5["ema200"] = mt5_ema(m5["close"], 200)
    macd_main = mt5_ema(m5["close"], 12) - mt5_ema(m5["close"], 26)
    # Standard MetaQuotes MACD uses a 9-period SMA of the main line.
    macd_signal = macd_main.rolling(9).mean()
    m5["hist"] = macd_main - macd_signal
    m5["rsi"] = mt5_rsi(m5["close"], 14)
    m5["adx"] = mt5_adx(m5, 14)
    m5["atr"] = mt5_atr(m5, 14)
    return m5


def load_news(path: Path) -> np.ndarray:
    news = pd.read_csv(path, usecols=["event_time_utc"])
    values = pd.to_datetime(news["event_time_utc"], utc=True).dt.tz_convert(None)
    return np.sort(values.to_numpy(dtype="datetime64[ns]"))


def news_blocked(utc_time: np.datetime64, news: np.ndarray) -> bool:
    if utc_time < np.datetime64("2019-01-01") or utc_time >= np.datetime64("2023-01-01"):
        return True
    position = int(np.searchsorted(news, utc_time))
    window = np.timedelta64(15, "m")
    if position < len(news) and abs(news[position] - utc_time) <= window:
        return True
    return position > 0 and abs(utc_time - news[position - 1]) <= window


def resolve_trade(
    direction: int,
    entry_time: np.datetime64,
    entry: float,
    stop: float,
    target: float,
    risk_price: float,
    m1_time: np.ndarray,
    m1_utc: np.ndarray,
    m1_low: np.ndarray,
    m1_high: np.ndarray,
    m1_close: np.ndarray,
    m1_open: np.ndarray | None = None,
) -> tuple[np.datetime64, float, str, float]:
    if m1_open is None:
        m1_open = m1_close
    start = int(np.searchsorted(m1_time, entry_time, side="left"))
    horizon = entry_time + np.timedelta64(75, "m")
    finish = int(np.searchsorted(m1_time, horizon, side="left"))
    last_index = start
    # The M1 bar opening exactly at the horizon is outside the position path.
    for idx in range(start, min(finish, len(m1_time))):
        last_index = idx
        utc = pd.Timestamp(m1_utc[idx])
        if utc.hour * 60 + utc.minute >= 18 * 60 + 15:
            exit_price = float(m1_open[idx])
            gross_r = direction * (exit_price - entry) / risk_price
            return m1_time[idx], float(gross_r), "FLATTEN", exit_price
        exit_kind = resolve_bar_exit(direction, m1_low[idx], m1_high[idx], stop, target)
        if exit_kind == "STOP":
            return m1_time[idx], -1.0, "STOP", stop
        if exit_kind == "TARGET":
            return m1_time[idx], 1.6, "TARGET", target
    if start >= len(m1_time):
        return entry_time, 0.0, "NO_PATH", entry
    gross_r = direction * (m1_close[last_index] - entry) / risk_price
    return m1_time[last_index], float(gross_r), "TIME", float(m1_close[last_index])


def candidate_direction(row: pd.Series, previous: pd.Series, prior: pd.Series, arm: str) -> int:
    bullish = row["close"] > row["open"] and row["close"] > row["ema200"]
    bearish = row["close"] < row["open"] and row["close"] < row["ema200"]
    if not math.isfinite(row["adx"]) or row["adx"] < 18.0:
        return 0
    if arm == "CONTROL":
        return 1 if bullish else (-1 if bearish else 0)
    turn = histogram_turn(row["hist"], previous["hist"], prior["hist"], row["atr"], 0.01)
    in_midzone = 42.0 <= row["rsi"] <= 58.0
    if turn == 1 and bullish and in_midzone and row["rsi"] > previous["rsi"]:
        return 1
    if turn == -1 and bearish and in_midzone and row["rsi"] < previous["rsi"]:
        return -1
    return 0


def simulate_arm(arm: str, m5: pd.DataFrame, m1: pd.DataFrame, news: np.ndarray) -> tuple[pd.DataFrame, dict]:
    m1_time = m1["time_server"].to_numpy(dtype="datetime64[ns]")
    m1_utc = m1["time_utc"].to_numpy(dtype="datetime64[ns]")
    m1_low = m1["low"].to_numpy(float)
    m1_high = m1["high"].to_numpy(float)
    m1_open = m1["open"].to_numpy(float)
    m1_close = m1["close"].to_numpy(float)
    records: list[dict] = []
    next_flat_time = np.datetime64("1970-01-01")
    last_entry_time = np.datetime64("1970-01-01")
    day_key: str | None = None
    trades_today = 0
    funnel = {
        "closed_bars": int(len(m5)),
        "raw_signal": 0,
        "session_pass": 0,
        "news_pass": 0,
        "spread_pass": 0,
        "ownership_cooldown_pass": 0,
        "executed": 0,
    }
    for index in range(202, len(m5) - 1):
        row = m5.iloc[index]
        previous = m5.iloc[index - 1]
        prior = m5.iloc[index - 2]
        direction = candidate_direction(row, previous, prior, arm)
        if direction == 0:
            continue
        funnel["raw_signal"] += 1
        entry_row = m5.iloc[index + 1]
        entry_time = np.datetime64(m5.index[index + 1].to_datetime64())
        entry_utc = np.datetime64(pd.Timestamp(entry_row["time_utc"]).to_datetime64())
        utc_stamp = pd.Timestamp(entry_utc)
        if not (8 <= utc_stamp.hour < 17):
            continue
        funnel["session_pass"] += 1
        if news_blocked(entry_utc, news):
            continue
        funnel["news_pass"] += 1
        spread_pips = float(entry_row["spread"]) / 10.0
        if not spread_allowed(spread_pips, 0.8):
            continue
        funnel["spread_pass"] += 1
        current_day = utc_stamp.strftime("%Y-%m-%d")
        if current_day != day_key:
            day_key, trades_today = current_day, 0
        if (
            not position_released(entry_time, next_flat_time)
            or entry_time - last_entry_time < np.timedelta64(25, "m")
            or trades_today >= 5
        ):
            continue
        funnel["ownership_cooldown_pass"] += 1
        lookback = m5.iloc[index - 4 : index + 1]
        entry = float(entry_row["open"])
        atr = float(row["atr"])
        if not math.isfinite(atr) or atr <= 0.0:
            continue
        if direction > 0:
            structural = float(lookback["low"].min()) - 0.5 * PIP
            stop = min(structural, entry - 1.5 * atr)
        else:
            structural = float(lookback["high"].max()) + 0.5 * PIP
            stop = max(structural, entry + 1.5 * atr)
        risk_price = direction * (entry - stop)
        if not math.isfinite(risk_price) or risk_price <= 0.0:
            continue
        target = entry + direction * 1.6 * risk_price
        exit_time, gross_r, exit_kind, exit_price = resolve_trade(
            direction,
            entry_time,
            entry,
            stop,
            target,
            risk_price,
            m1_time,
            m1_utc,
            m1_low,
            m1_high,
            m1_close,
            m1_open,
        )
        risk_pips = risk_price / PIP
        records.append(
            {
                "arm": arm,
                "signal_time_server": m5.index[index],
                "entry_time_server": pd.Timestamp(entry_time),
                "entry_time_utc": utc_stamp,
                "exit_time_server": pd.Timestamp(exit_time),
                "direction": direction,
                "entry": entry,
                "stop": stop,
                "target": target,
                "exit_price": exit_price,
                "exit_kind": exit_kind,
                "risk_pips": risk_pips,
                "spread_gate_pips": spread_pips,
                "gross_r": gross_r,
                "net_r_x1": gross_r - 1.5 / risk_pips,
                "net_r_x1_5": gross_r - 2.25 / risk_pips,
                "net_r_x2": gross_r - 3.0 / risk_pips,
            }
        )
        next_flat_time = exit_time
        last_entry_time = entry_time
        trades_today += 1
        funnel["executed"] += 1
    return pd.DataFrame.from_records(records), funnel


def profit_factor(values: pd.Series) -> float | None:
    positive = float(values[values > 0.0].sum())
    negative = float(-values[values < 0.0].sum())
    if negative <= 0.0:
        return None
    return positive / negative


def view_metrics(trades: pd.DataFrame, start: pd.Timestamp, end_exclusive: pd.Timestamp) -> dict:
    view = trades[
        (trades["entry_time_utc"] >= start) & (trades["entry_time_utc"] < end_exclusive)
    ].copy()
    elapsed_weeks = (end_exclusive - start).total_seconds() / (7.0 * 86400.0)
    if view.empty:
        return {
            "trades": 0,
            "trades_per_elapsed_week": 0.0,
            "pf_x1": None,
            "expectancy_r_x1": None,
            "pf_x1_5": None,
            "pf_x2": None,
            "net_r_x1": 0.0,
            "max_drawdown_pct_at_0_3pct": None,
            "longs": 0,
            "shorts": 0,
        }
    equity = view["net_r_x1"].cumsum()
    drawdown_r = equity.cummax() - equity
    return {
        "trades": int(len(view)),
        "trades_per_elapsed_week": float(len(view) / elapsed_weeks),
        "pf_x1": profit_factor(view["net_r_x1"]),
        "expectancy_r_x1": float(view["net_r_x1"].mean()),
        "pf_x1_5": profit_factor(view["net_r_x1_5"]),
        "pf_x2": profit_factor(view["net_r_x2"]),
        "net_r_x1": float(view["net_r_x1"].sum()),
        "max_drawdown_pct_at_0_3pct": float(drawdown_r.max() * 0.3),
        "longs": int((view["direction"] > 0).sum()),
        "shorts": int((view["direction"] < 0).sum()),
    }


def arm_metrics(trades: pd.DataFrame) -> dict:
    metrics = {
        "pooled": view_metrics(trades, DESIGN_START, END_EXCLUSIVE),
        "design": view_metrics(trades, DESIGN_START, DESIGN_END_EXCLUSIVE),
        "validation": view_metrics(trades, VALIDATION_START, END_EXCLUSIVE),
    }
    if trades.empty:
        metrics["positive_year_profit_concentration"] = None
        metrics["exit_kinds"] = {}
        return metrics
    yearly = trades.groupby(trades["entry_time_utc"].dt.year)["net_r_x1"].sum()
    positive_years = yearly[yearly > 0.0]
    metrics["positive_year_profit_concentration"] = (
        float(positive_years.max() / positive_years.sum()) if not positive_years.empty else None
    )
    metrics["year_net_r_x1"] = {str(int(year)): float(value) for year, value in yearly.items()}
    metrics["exit_kinds"] = {str(k): int(v) for k, v in trades["exit_kind"].value_counts().items()}
    return metrics


def gate_result(control: dict, challenger: dict) -> tuple[dict, bool]:
    gates: dict[str, bool] = {}
    pooled = challenger["pooled"]
    validation = challenger["validation"]
    gates["pooled_n_ge_350"] = pooled["trades"] >= 350
    gates["validation_n_ge_100"] = validation["trades"] >= 100
    for name in ("pooled", "design", "validation"):
        view = challenger[name]
        prefix = f"{name}_"
        gates[prefix + "cadence_2_to_5"] = 2.0 <= view["trades_per_elapsed_week"] <= 5.0
        gates[prefix + "pf_x1_ge_1_35"] = view["pf_x1"] is not None and view["pf_x1"] >= 1.35
        gates[prefix + "expectancy_ge_0_18r"] = (
            view["expectancy_r_x1"] is not None and view["expectancy_r_x1"] >= 0.18
        )
        gates[prefix + "pf_x1_5_ge_1_25"] = (
            view["pf_x1_5"] is not None and view["pf_x1_5"] >= 1.25
        )
        gates[prefix + "pf_x2_ge_1"] = view["pf_x2"] is not None and view["pf_x2"] >= 1.0
        gates[prefix + "dd_le_6pct"] = (
            view["max_drawdown_pct_at_0_3pct"] is not None
            and view["max_drawdown_pct_at_0_3pct"] <= 6.0
        )
        gates[prefix + "both_directions"] = view["longs"] > 0 and view["shorts"] > 0
    gates["beats_control_net_r"] = pooled["net_r_x1"] > control["pooled"]["net_r_x1"]
    gates["pf_not_below_control"] = (
        pooled["pf_x1"] is not None
        and control["pooled"]["pf_x1"] is not None
        and pooled["pf_x1"] >= control["pooled"]["pf_x1"]
    )
    concentration = challenger["positive_year_profit_concentration"]
    gates["positive_year_concentration_le_40pct"] = concentration is not None and concentration <= 0.40
    return gates, all(gates.values())


def parse_args() -> argparse.Namespace:
    workspace = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=workspace / "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet",
    )
    parser.add_argument(
        "--news",
        type=Path,
        default=workspace
        / "02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent
        / "evidence/HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-003_PROBE_RESULT.json",
    )
    parser.add_argument(
        "--trades-output",
        type=Path,
        default=Path(__file__).resolve().parent
        / "evidence/HYP-MZMS-MACD-HIST-SLOPE-EURUSD-M5-003_PROBE_TRADES.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    actual_data_sha = sha256_file(args.data)
    actual_news_sha = sha256_file(args.news)
    if actual_data_sha != DATA_SHA256 or actual_news_sha != NEWS_SHA256:
        raise SystemExit(
            f"hash mismatch data={actual_data_sha} news={actual_news_sha}; no outcome access authorized"
        )
    columns = ["time_server", "time_utc", "open", "high", "low", "close", "spread"]
    m1 = pd.read_parquet(args.data, columns=columns)
    m1["time_server"] = pd.to_datetime(m1["time_server"])
    m1["time_utc"] = pd.to_datetime(m1["time_utc"])
    # Filter before any indicator or outcome calculation; 2023+ stays sealed.
    warmup = pd.Timestamp("2018-12-20")
    m1 = m1[(m1["time_server"] >= warmup) & (m1["time_server"] < END_EXCLUSIVE)].copy()
    m1.sort_values("time_server", inplace=True, ignore_index=True)
    news = load_news(args.news)
    m5 = build_m5(m1)
    m5 = m5[(m5["time_utc"] >= DESIGN_START) & (m5["time_utc"] < END_EXCLUSIVE)].copy()
    results: dict[str, dict] = {}
    trade_frames: list[pd.DataFrame] = []
    for arm in ("CONTROL", "MZMS_CHALLENGER"):
        trades, funnel = simulate_arm(arm, m5, m1, news)
        metrics = arm_metrics(trades)
        results[arm] = {"funnel": funnel, "metrics": metrics}
        trade_frames.append(trades)
    gates, survived = gate_result(
        results["CONTROL"]["metrics"], results["MZMS_CHALLENGER"]["metrics"]
    )
    source = Path(__file__).resolve().parents[1] / "EA_MZMS_Scalper.mq5"
    payload = {
        "schema_version": "alphafactory_offline_probe_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "verdict": "SURVIVE_DIAGNOSTIC_PROBE" if survived else "KILL_AT_FROZEN_OFFLINE_PROBE",
        "promotion_eligible": False,
        "model0_authorized": False,
        "cost_status": "UNVERIFIED_DIAGNOSTIC_ONLY",
        "hashes": {
            "plan_sha256": PLAN_SHA256,
            "report_sha256": REPORT_SHA256,
            "data_sha256": actual_data_sha,
            "news_sha256": actual_news_sha,
            "source_sha256": sha256_file(source),
            "probe_sha256": sha256_file(Path(__file__)),
        },
        "windows": {
            "design": [str(DESIGN_START.date()), "2021-12-31"],
            "validation": [str(VALIDATION_START.date()), "2022-12-30"],
            "sealed": "2023-01-01 onward was not read into the analysis frame",
        },
        "arms": results,
        "gates": gates,
        "gate_pass_count": int(sum(gates.values())),
        "gate_total": len(gates),
        "limitations": [
            "M1 OHLC path is bid-only; same-minute ambiguity is resolved stop-first.",
            "The M1 spread field is used only as a fail-closed entry eligibility gate because 24.5553% of source rows are zero.",
            "Fixed 1.5/2.25/3.0-pip round-turn costs are diagnostic assumptions, not broker-verified cost truth.",
            "Forex Factory news is source class C and promotion_eligible=false.",
            "No BE-on, intrabar, parameter sweep, Model-0, live, or 2023+ result is included.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    combined = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
    combined.to_csv(args.trades_output, index=False)
    print(json.dumps({"verdict": payload["verdict"], "gate_pass": payload["gate_pass_count"], "gate_total": payload["gate_total"], "result": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
