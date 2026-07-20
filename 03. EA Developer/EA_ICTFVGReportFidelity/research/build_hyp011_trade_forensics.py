#!/usr/bin/env python3
"""Build deterministic trade/context forensics for terminal HYP-011.

This is a read-only diagnostic of the frozen AlphaFactory run.  It does not
optimize parameters, alter the EA, or authorize another economic run.  All
trade economics include the OPEN-deal commission and are reconciled by MT5
position_id before any R multiple is calculated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011"
SOURCE_SHA256 = "EFEA68F7763873B5F880BBCB2919A3A2DF629289E06F69A525FA91396C9674A6"
LIFECYCLE_SHA256 = "D475B6FC5145BBD79C26645A04900F3366B75961A665C36A112C6BF693A5C6A6"
M1_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
POINT = 0.00001


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def assert_sha(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise SystemExit(f"SHA mismatch: {path}\nexpected={expected}\nactual={actual}")


def profit_factor(values: pd.Series) -> float | None:
    positive = float(values[values > 0].sum())
    negative = float(-values[values < 0].sum())
    return positive / negative if negative > 0 else None


def safe_float(value: object) -> float | None:
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return None
    return float(value)


def aggregate(group: pd.DataFrame) -> dict[str, object]:
    net = group["net"].astype(float)
    r = group["r_net"].dropna().astype(float)
    winners = net[net > 0]
    losers = net[net < 0]
    return {
        "positions": int(len(group)),
        "wins": int((net > 0).sum()),
        "losses": int((net < 0).sum()),
        "win_rate_pct": safe_float((net > 0).mean() * 100.0),
        "net": float(net.sum()),
        "profit_factor": safe_float(profit_factor(net)),
        "expectancy_money": safe_float(net.mean()),
        "expectancy_r": safe_float(r.mean()),
        "median_r": safe_float(r.median()),
        "avg_win_money": safe_float(winners.mean()),
        "avg_loss_money": safe_float(losers.mean()),
    }


def reconcile_positions(lifecycle: pd.DataFrame) -> pd.DataFrame:
    lifecycle = lifecycle.copy()
    lifecycle["event_time"] = pd.to_datetime(
        lifecycle["event_time"], format="%Y.%m.%d %H:%M:%S"
    )
    numeric = [
        "volume", "price", "risk_pts", "initial_risk_account", "deal_profit",
        "deal_commission", "deal_swap", "deal_fee", "deal_net", "is_final_close",
    ]
    for column in numeric:
        lifecycle[column] = pd.to_numeric(lifecycle[column], errors="coerce")

    records: list[dict[str, object]] = []
    for position_id, group in lifecycle.groupby("position_id", sort=True):
        group = group.sort_values(["event_time", "deal"])
        opened = group[group["action"] == "OPEN"]
        final = group[group["is_final_close"] == 1]
        if len(opened) != 1 or len(final) != 1:
            raise SystemExit(
                f"position {position_id}: expected one OPEN and one final close; "
                f"found opens={len(opened)} finals={len(final)}"
            )
        first = opened.iloc[0]
        last = final.iloc[-1]
        risk_account = float(first["initial_risk_account"])
        gross = float((group["deal_profit"] + group["deal_swap"] + group["deal_fee"]).sum())
        commission = float(group["deal_commission"].sum())
        net = float(group["deal_net"].sum())
        if not math.isclose(net, gross + commission, abs_tol=1e-7):
            raise SystemExit(f"position {position_id}: lifecycle net does not reconcile")
        records.append(
            {
                "position_id": int(position_id),
                "direction": 1 if first["order_type"] == "BUY" else -1,
                "side": str(first["order_type"]),
                "entry_time_server": first["event_time"],
                "exit_time_server": last["event_time"],
                "entry": float(first["price"]),
                "exit": float(last["price"]),
                "volume": float(first["volume"]),
                "risk_pts": float(first["risk_pts"]),
                "initial_risk_account": risk_account,
                "gross_before_commission": gross,
                "commission": commission,
                "net": net,
                "r_gross": gross / risk_account if risk_account > 0 else np.nan,
                "r_net": net / risk_account if risk_account > 0 else np.nan,
                "hold_minutes": (last["event_time"] - first["event_time"]).total_seconds() / 60.0,
                "deal_rows": int(len(group)),
            }
        )
    positions = pd.DataFrame.from_records(records)
    if len(positions) != 4341:
        raise SystemExit(f"expected 4341 positions, found {len(positions)}")
    return positions


def build_m5(m1_path: Path, positions: pd.DataFrame) -> pd.DataFrame:
    start = positions["entry_time_server"].min().floor("D") - pd.Timedelta(days=3)
    end = positions["exit_time_server"].max().ceil("D") + pd.Timedelta(days=1)
    columns = [
        "time_server", "time_utc", "utc_offset_h", "open", "high", "low", "close",
        "tick_volume", "spread", "real_volume",
    ]
    try:
        m1 = pd.read_parquet(
            m1_path,
            columns=columns,
            filters=[("time_server", ">=", start), ("time_server", "<=", end)],
        )
    except (TypeError, ValueError):
        m1 = pd.read_parquet(m1_path, columns=columns)
        m1 = m1[(m1["time_server"] >= start) & (m1["time_server"] <= end)]
    m1 = m1.sort_values("time_server").copy()
    m1_expected_utc = m1["time_server"] - pd.to_timedelta(m1["utc_offset_h"], unit="h")
    if not (m1_expected_utc == m1["time_utc"]).all():
        raise SystemExit("M1 input failed the measured server-to-UTC offset check")
    m1["m5_server"] = m1["time_server"].dt.floor("5min")
    m5 = (
        m1.groupby("m5_server", sort=True, as_index=False)
        .agg(
            time_utc=("time_utc", "first"),
            utc_offset_h=("utc_offset_h", "first"),
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            tick_volume=("tick_volume", "sum"),
            spread=("spread", "last"),
            real_volume=("real_volume", "sum"),
            m1_rows=("time_server", "size"),
        )
        .rename(columns={"m5_server": "time_server"})
    )
    # The first available M1 row can be later than the nominal M5 open after a
    # quote gap.  Canonicalize the M5 timestamp from its server bar open and the
    # already-verified measured offset instead of inheriting that later minute.
    m5["time_utc"] = m5["time_server"] - pd.to_timedelta(m5["utc_offset_h"], unit="h")
    return m5


def last_sunday(year: int, month: int, hour: int) -> pd.Timestamp:
    if month == 12:
        next_month = pd.Timestamp(year=year + 1, month=1, day=1, hour=hour)
    else:
        next_month = pd.Timestamp(year=year, month=month + 1, day=1, hour=hour)
    day = next_month - pd.Timedelta(days=1)
    return day - pd.Timedelta(days=(day.dayofweek + 1) % 7)


def ea_europe_offset(server_time: pd.Timestamp) -> int:
    start = last_sunday(server_time.year, 3, 3)
    finish = last_sunday(server_time.year, 10, 4)
    return 3 if start <= server_time < finish else 2


def session_name(timestamp_utc: pd.Timestamp) -> str:
    minute = timestamp_utc.hour * 60 + timestamp_utc.minute
    if 7 * 60 <= minute < 11 * 60:
        return "LONDON"
    if 13 * 60 <= minute < 17 * 60:
        return "NEW_YORK"
    return "OUTSIDE"


def is_pivot(m5: pd.DataFrame, row: int, strength: int, high: bool) -> bool:
    column = "high" if high else "low"
    value = float(m5.iloc[row][column])
    for offset in range(1, strength + 1):
        newer = float(m5.iloc[row + offset][column])
        older = float(m5.iloc[row - offset][column])
        if high and (value <= newer or value <= older):
            return False
        if not high and (value >= newer or value >= older):
            return False
    return True


def add_context(positions: pd.DataFrame, m5: pd.DataFrame) -> pd.DataFrame:
    positions = positions.copy()
    m5 = m5.sort_values("time_server").reset_index(drop=True)
    row_by_time = {timestamp: i for i, timestamp in enumerate(m5["time_server"])}
    feature_rows: list[dict[str, object]] = []

    previous_close = m5["close"].shift(1)
    true_range = pd.concat(
        [
            m5["high"] - m5["low"],
            (m5["high"] - previous_close).abs(),
            (m5["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    m5["atr20_simple"] = true_range.rolling(20).mean()
    m5["ema20"] = m5["close"].ewm(span=20, adjust=False).mean()
    m5["ema50"] = m5["close"].ewm(span=50, adjust=False).mean()

    for record in positions.itertuples(index=False):
        entry_server = pd.Timestamp(record.entry_time_server)
        signal_time = entry_server.floor("5min") - pd.Timedelta(minutes=5)
        idx = row_by_time.get(signal_time)
        if idx is None or idx < 60 or idx + 2 >= len(m5):
            feature_rows.append({"position_id": record.position_id, "context_status": "MISSING_BAR"})
            continue

        high_pivot = None
        low_pivot = None
        for series_index in range(2, 23):
            candidate = idx - series_index
            if high_pivot is None and is_pivot(m5, candidate, 2, high=True):
                high_pivot = float(m5.iloc[candidate]["high"])
            if low_pivot is None and is_pivot(m5, candidate, 2, high=False):
                low_pivot = float(m5.iloc[candidate]["low"])
            if high_pivot is not None and low_pivot is not None:
                break

        signal = m5.iloc[idx]
        direction = int(record.direction)
        pivot = low_pivot if direction > 0 else high_pivot
        signal_range = float(signal["high"] - signal["low"])
        mean_prior_body = float(
            (m5.iloc[idx - 20 : idx]["close"] - m5.iloc[idx - 20 : idx]["open"])
            .abs()
            .mean()
        )
        atr = float(signal["atr20_simple"])
        sweep_depth = (
            float(pivot - signal["low"]) if direction > 0 else float(signal["high"] - pivot)
        ) if pivot is not None else np.nan
        reclaim = (
            float(signal["close"] - pivot) if direction > 0 else float(pivot - signal["close"])
        ) if pivot is not None else np.nan
        close_location = (
            (float(signal["close"] - signal["low"]) / signal_range)
            if direction > 0
            else (float(signal["high"] - signal["close"]) / signal_range)
        ) if signal_range > 0 else np.nan
        canonical_utc = pd.Timestamp(signal["time_utc"]) + pd.Timedelta(minutes=5)
        measured_offset = int(signal["utc_offset_h"])
        ea_offset = ea_europe_offset(entry_server)
        ea_utc = entry_server - pd.Timedelta(hours=ea_offset)
        canonical_entry_utc = entry_server - pd.Timedelta(hours=measured_offset)
        if canonical_entry_utc != canonical_utc:
            # Entry may occur seconds after the M5 boundary, but its minute/hour
            # must still map through the measured server offset.
            canonical_utc = canonical_entry_utc

        feature_rows.append(
            {
                "position_id": record.position_id,
                "context_status": "OK",
                "signal_time_server": signal_time,
                "entry_time_utc": canonical_entry_utc,
                "exit_time_utc": pd.Timestamp(record.exit_time_server) - pd.Timedelta(hours=measured_offset),
                "measured_utc_offset_h": measured_offset,
                "ea_utc_offset_h": ea_offset,
                "dst_clock_mismatch": measured_offset != ea_offset,
                "ea_session": session_name(ea_utc),
                "actual_session": session_name(canonical_entry_utc),
                "session_mismatch": session_name(ea_utc) != session_name(canonical_entry_utc),
                "signal_open": float(signal["open"]),
                "signal_high": float(signal["high"]),
                "signal_low": float(signal["low"]),
                "signal_close": float(signal["close"]),
                "pivot": pivot,
                "sweep_depth_pips": sweep_depth * 10000.0,
                "reclaim_pips": reclaim * 10000.0,
                "signal_range_pips": signal_range * 10000.0,
                "signal_body_pips": abs(float(signal["close"] - signal["open"])) * 10000.0,
                "body_vs_prior_mean": (
                    abs(float(signal["close"] - signal["open"])) / mean_prior_body
                    if mean_prior_body > 0 else np.nan
                ),
                "range_vs_atr20": signal_range / atr if atr > 0 else np.nan,
                "directional_close_location": close_location,
                "directional_return_20_atr": (
                    direction * (float(signal["close"]) - float(m5.iloc[idx - 20]["close"])) / atr
                    if atr > 0 else np.nan
                ),
                "ema20_minus_ema50_directional_atr": (
                    direction * (float(signal["ema20"]) - float(signal["ema50"])) / atr
                    if atr > 0 else np.nan
                ),
            }
        )

    features = pd.DataFrame.from_records(feature_rows)
    merged = positions.merge(features, on="position_id", how="left", validate="one_to_one")
    return merged


def feature_diagnostics(positions: pd.DataFrame) -> dict[str, object]:
    features = [
        "risk_pts", "sweep_depth_pips", "reclaim_pips", "signal_range_pips", "body_vs_prior_mean",
        "range_vs_atr20", "directional_close_location", "directional_return_20_atr",
        "ema20_minus_ema50_directional_atr",
    ]
    result: dict[str, object] = {"winner_loser_medians": {}, "quartiles": {}}
    for feature in features:
        result["winner_loser_medians"][feature] = {
            "wins": safe_float(positions.loc[positions["net"] > 0, feature].median()),
            "losses": safe_float(positions.loc[positions["net"] < 0, feature].median()),
        }
        try:
            labels = pd.qcut(positions[feature], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
        except ValueError:
            continue
        table = []
        for label, group in positions.assign(_bucket=labels).groupby("_bucket", observed=True):
            row = aggregate(group)
            row["bucket"] = str(label)
            row["feature_min"] = safe_float(group[feature].min())
            row["feature_max"] = safe_float(group[feature].max())
            table.append(row)
        result["quartiles"][feature] = table
    return result


def exit_cluster(r_value: float) -> str:
    if pd.isna(r_value):
        return "UNDEFINED_RISK"
    if r_value < -1.30:
        return "WORSE_THAN_MINUS_1_3R"
    if -1.30 <= r_value <= -0.70:
        return "NEAR_FULL_STOP"
    if -0.30 < r_value < 0.30:
        return "SCRATCH"
    if 0.30 <= r_value < 1.70:
        return "LOCKED_PROFIT_OR_PARTIAL"
    if r_value >= 1.70:
        return "NEAR_2R_TARGET"
    return "OTHER"


def add_risk_decile(positions: pd.DataFrame) -> pd.DataFrame:
    positions = positions.copy()
    positions["risk_decile"] = pd.qcut(
        positions["risk_pts"], 10, labels=False, duplicates="drop"
    ).astype(int)
    return positions


def build_matched_pairs(positions: pd.DataFrame) -> pd.DataFrame:
    data = add_risk_decile(positions[positions["context_status"] == "OK"].copy())
    wins = data[data["net"] > 0].sort_values("entry_time_server")
    losses = data[data["net"] < 0].copy()
    unused = set(losses["position_id"].astype(int))
    feature_cols = [
        "sweep_depth_pips", "reclaim_pips", "range_vs_atr20",
        "directional_close_location", "directional_return_20_atr",
    ]
    scales = {column: float(data[column].std(ddof=0)) or 1.0 for column in feature_cols}
    records: list[dict[str, object]] = []
    for win in wins.itertuples(index=False):
        candidates = losses[
            losses["position_id"].isin(unused)
            & (losses["direction"] == win.direction)
            & (losses["entry_time_utc"].dt.hour == win.entry_time_utc.hour)
            & ((losses["risk_decile"] - win.risk_decile).abs() <= 1)
            & ((losses["entry_time_server"] - win.entry_time_server).abs() <= pd.Timedelta(days=60))
        ].copy()
        if candidates.empty:
            continue
        distance = (
            (candidates["entry_time_server"] - win.entry_time_server).abs().dt.total_seconds() / 86400.0 / 60.0
            + (candidates["risk_pts"] - win.risk_pts).abs() / max(float(data["risk_pts"].std(ddof=0)), 1.0)
        )
        for column in feature_cols:
            distance += (candidates[column] - getattr(win, column)).abs() / scales[column]
        chosen_index = distance.idxmin()
        loss = candidates.loc[chosen_index]
        unused.remove(int(loss["position_id"]))
        records.append(
            {
                "win_position_id": int(win.position_id),
                "loss_position_id": int(loss["position_id"]),
                "direction": int(win.direction),
                "hour_utc": int(win.entry_time_utc.hour),
                "days_apart": abs((pd.Timestamp(win.entry_time_server) - loss["entry_time_server"]).total_seconds()) / 86400.0,
                "win_r": float(win.r_net),
                "loss_r": float(loss["r_net"]),
                "win_risk_pts": float(win.risk_pts),
                "loss_risk_pts": float(loss["risk_pts"]),
                "context_distance": float(distance.loc[chosen_index]),
            }
        )
    return pd.DataFrame.from_records(records)


def post_lock_counterfactual(positions: pd.DataFrame, m5: pd.DataFrame) -> dict[str, object]:
    """Describe the post-exit path of +0.5R lock exits without claiming a strategy.

    The scan starts at the next complete M5 bar after exit, applies SL-first on
    ambiguous bars, and stops at 22:00 measured UTC.  It uses bid OHLC, so ask
    spread for short stops is not represented; the result is diagnostic only.
    """
    locked = positions[positions["exit_cluster"] == "LOCKED_PROFIT_OR_PARTIAL"]
    bars = m5.sort_values("time_utc").reset_index(drop=True)
    times = pd.to_datetime(bars["time_utc"]).to_numpy(dtype="datetime64[ns]")
    outcomes: list[dict[str, object]] = []
    for row in locked.itertuples(index=False):
        start = pd.Timestamp(row.exit_time_utc).ceil("5min")
        finish = pd.Timestamp(row.entry_time_utc).normalize() + pd.Timedelta(hours=22)
        left = int(np.searchsorted(times, np.datetime64(start), side="left"))
        right = int(np.searchsorted(times, np.datetime64(finish), side="left"))
        risk_price = float(row.risk_pts) * POINT
        sl = float(row.entry - row.direction * risk_price)
        tp = float(row.entry + row.direction * 2.0 * risk_price)
        outcome = "NEITHER_BY_22UTC"
        outcome_time = pd.NaT
        for bar in bars.iloc[left:right].itertuples(index=False):
            hit_sl = bar.low <= sl if row.direction > 0 else bar.high >= sl
            hit_tp = bar.high >= tp if row.direction > 0 else bar.low <= tp
            if hit_sl and hit_tp:
                outcome = "SL_FIRST_SAME_BAR"
                outcome_time = bar.time_utc
                break
            if hit_sl:
                outcome = "SL_FIRST"
                outcome_time = bar.time_utc
                break
            if hit_tp:
                outcome = "TP_FIRST"
                outcome_time = bar.time_utc
                break
        outcomes.append(
            {
                "position_id": int(row.position_id),
                "outcome": outcome,
                "minutes_after_exit": (
                    (pd.Timestamp(outcome_time) - pd.Timestamp(row.exit_time_utc)).total_seconds() / 60.0
                    if pd.notna(outcome_time) else np.nan
                ),
            }
        )
    result = pd.DataFrame.from_records(outcomes)
    counts = result["outcome"].value_counts().to_dict()
    return {
        "locked_profit_positions": int(len(result)),
        "outcomes": {str(key): int(value) for key, value in counts.items()},
        "tp_first_pct": float((result["outcome"] == "TP_FIRST").mean() * 100.0),
        "sl_first_including_same_bar_pct": float(
            result["outcome"].isin(["SL_FIRST", "SL_FIRST_SAME_BAR"]).mean() * 100.0
        ),
        "median_minutes_to_decision": safe_float(result["minutes_after_exit"].median()),
        "boundary": (
            "Post-exit M5 diagnostic only: next complete bar, SL-first ambiguity, "
            "bid OHLC without short-side ask spread, no economic or tuning authority."
        ),
    }


def exit_cluster_context(positions: pd.DataFrame) -> list[dict[str, object]]:
    features = [
        "risk_pts", "sweep_depth_pips", "reclaim_pips", "signal_range_pips",
        "body_vs_prior_mean", "range_vs_atr20", "directional_close_location",
        "directional_return_20_atr", "ema20_minus_ema50_directional_atr",
        "hold_minutes",
    ]
    total_positive = float(positions.loc[positions["net"] > 0, "net"].sum())
    total_negative = float(-positions.loc[positions["net"] < 0, "net"].sum())
    rows: list[dict[str, object]] = []
    for cluster, group in positions.groupby("exit_cluster"):
        net = float(group["net"].sum())
        row: dict[str, object] = {
            "cluster": cluster,
            "positions": int(len(group)),
            "share_of_positions_pct": float(len(group) / len(positions) * 100.0),
            "net_contribution": net,
            "share_of_winner_profit_pct": (
                float(net / total_positive * 100.0) if net > 0 and total_positive > 0 else None
            ),
            "share_of_loser_loss_pct": (
                float(-net / total_negative * 100.0) if net < 0 and total_negative > 0 else None
            ),
            "feature_medians": {
                feature: safe_float(group[feature].median()) for feature in features
            },
        }
        rows.append(row)
    return rows


def build_cases(positions: pd.DataFrame) -> pd.DataFrame:
    # Frozen by the Grok forensic pass before any chart was rendered.  Keeping
    # the exact list prevents visual cherry-picking after looking at images.
    case_specs = [
        ("C01", 1374, "worst_r"),
        ("C02", 4930, "fast_large_loss"),
        ("C03", 6836, "large_target_winner"),
        ("C04", 6534, "large_target_winner"),
        ("C05", 5726, "median_winner"),
        ("C06", 246, "modal_locked_profit_winner"),
        ("C07", 4052, "median_full_stop"),
        ("C08", 3630, "modal_full_stop"),
        ("C09", 6912, "matched_pair_winner"),
        ("C10", 6906, "matched_pair_loser"),
        ("C11", 6606, "second_matched_pair_loser"),
        ("C12", 224, "zero_risk_telemetry_anomaly"),
    ]
    by_id = positions.set_index("position_id")
    records = []
    for case_id, position_id, reason in case_specs:
        if position_id not in by_id.index:
            raise SystemExit(f"Grok-frozen case missing: position_id={position_id}")
        row = by_id.loc[position_id]
        risk_price = float(row["risk_pts"]) * POINT
        direction = int(row["direction"])
        sl = float(row["entry"] - direction * risk_price) if risk_price > 0 else np.nan
        tp = float(row["entry"] + direction * 2.0 * risk_price) if risk_price > 0 else np.nan
        label = (
            f"pid={position_id}; netR={row['r_net']:.3f}; "
            f"depth={row['sweep_depth_pips']:.1f}p; reclaim={row['reclaim_pips']:.1f}p"
            if pd.notna(row["r_net"])
            else f"pid={position_id}; netR=undefined; telemetry anomaly"
        )
        records.append(
            {
                "case_id": case_id,
                "position_id": position_id,
                "entry_time_utc": row["entry_time_utc"],
                "exit_time_utc": row["exit_time_utc"],
                "direction": direction,
                "entry": float(row["entry"]),
                "sl": sl,
                "tp": tp,
                "exit": float(row["exit"]),
                "pivot": safe_float(row["pivot"]),
                "reason": reason,
                "label": label,
            }
        )
    return pd.DataFrame.from_records(records)


def main() -> int:
    script = Path(__file__).resolve()
    root = script.parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir", type=Path,
        default=root / "02. AlphaFactory/runtime/ictfvg_hyp011_forensics",
    )
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    source = root / "03. EA Developer/EA_ICTFVGReportFidelity/EA_ICTFVGReportFidelity.mq5"
    lifecycle_path = root / (
        "02. AlphaFactory/runs/EA_ICTFVGReportFidelity/20260719_142214/logs/"
        "EURUSD_LifecycleTrades_HYP-ICT-FVG-FULLCHART-NONEWS-2018YTD-EURUSD-M5-011_90560921.csv"
    )
    m1_path = root / "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
    assert_sha(source, SOURCE_SHA256)
    assert_sha(lifecycle_path, LIFECYCLE_SHA256)
    assert_sha(m1_path, M1_SHA256)

    lifecycle = pd.read_csv(lifecycle_path)
    if len(lifecycle) != 8682:
        raise SystemExit(f"expected 8682 lifecycle rows, found {len(lifecycle)}")
    positions = reconcile_positions(lifecycle)
    m5 = build_m5(m1_path, positions)
    positions = add_context(positions, m5)
    positions["exit_cluster"] = positions["r_net"].map(exit_cluster)
    positions = add_risk_decile(positions)

    net_summary = aggregate(positions)
    gross_summary = aggregate(
        positions.rename(columns={"net": "net_original", "r_net": "r_net_original"})
        .assign(
            net=lambda frame: frame["gross_before_commission"],
            r_net=lambda frame: frame["r_gross"],
        )
    )
    defined_r = positions[positions["initial_risk_account"] > 0]
    avg_win = float(positions.loc[positions["net"] > 0, "net"].mean())
    avg_loss_abs = abs(float(positions.loc[positions["net"] < 0, "net"].mean()))
    breakeven_wr = avg_loss_abs / (avg_win + avg_loss_abs) * 100.0

    by_year = []
    for year, group in positions.groupby(positions["entry_time_server"].dt.year):
        row = aggregate(group)
        row["year"] = int(year)
        by_year.append(row)
    by_direction = []
    for side, group in positions.groupby("side"):
        row = aggregate(group)
        row["side"] = side
        by_direction.append(row)
    by_actual_session = []
    for session, group in positions.groupby("actual_session", dropna=False):
        row = aggregate(group)
        row["session"] = str(session)
        by_actual_session.append(row)
    by_actual_utc_hour = []
    for hour, group in positions.dropna(subset=["entry_time_utc"]).groupby(
        positions.dropna(subset=["entry_time_utc"])["entry_time_utc"].dt.hour
    ):
        row = aggregate(group)
        row["hour_utc"] = int(hour)
        by_actual_utc_hour.append(row)
    by_hold = []
    hold_labels = pd.cut(
        positions["hold_minutes"], [-np.inf, 15, 60, 180, np.inf],
        labels=["0_15m", "15_60m", "60_180m", "over_180m"], right=False,
    )
    for label, group in positions.assign(_bucket=hold_labels).groupby("_bucket", observed=True):
        row = aggregate(group)
        row["bucket"] = str(label)
        by_hold.append(row)
    by_cluster = []
    for label, group in positions.groupby("exit_cluster"):
        row = aggregate(group)
        row["cluster"] = label
        by_cluster.append(row)

    month_net = positions.groupby(positions["entry_time_server"].dt.to_period("M"))["net"].sum()
    mismatch = positions[positions["dst_clock_mismatch"].eq(True)]
    session_mismatch = positions[positions["session_mismatch"].eq(True)]
    matched = build_matched_pairs(positions)

    diagnostics = {
        "schema_version": "ictfvg_trade_forensics.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": "20260719_142214",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "read_only_postmortem_no_tuning_no_rerun_authority",
        "input_identity": {
            "source": str(source), "source_sha256": SOURCE_SHA256,
            "lifecycle": str(lifecycle_path), "lifecycle_sha256": LIFECYCLE_SHA256,
            "m1_bars": str(m1_path), "m1_bars_sha256": M1_SHA256,
        },
        "reconciliation": {
            "lifecycle_rows": int(len(lifecycle)),
            "opens": int((lifecycle["action"] == "OPEN").sum()),
            "final_closes": int((pd.to_numeric(lifecycle["is_final_close"]) == 1).sum()),
            "positions": int(len(positions)),
            "positions_with_m5_context": int((positions["context_status"] == "OK").sum()),
            "positions_missing_m5_context": int((positions["context_status"] != "OK").sum()),
            "missing_m5_context_position_ids": positions.loc[
                positions["context_status"] != "OK", "position_id"
            ].astype(int).tolist(),
            "zero_initial_risk_positions": int((positions["initial_risk_account"] <= 0).sum()),
            "defined_r_positions": int(len(defined_r)),
        },
        "economics_net": net_summary,
        "economics_before_explicit_commission": gross_summary,
        "explicit_commission": {
            "total": float(positions["commission"].sum()),
            "average_per_position": float(positions["commission"].mean()),
            "average_r_on_defined_positions": float(
                (defined_r["commission"] / defined_r["initial_risk_account"]).mean()
            ),
            "note": "This removes explicit commission only; spread/slippage remain embedded in deal profit.",
        },
        "payoff_geometry": {
            "avg_win_money": avg_win,
            "avg_loss_money": -avg_loss_abs,
            "breakeven_win_rate_pct_at_observed_payoff": breakeven_wr,
            "achieved_win_rate_pct": net_summary["win_rate_pct"],
            "avg_win_r": float(defined_r.loc[defined_r["net"] > 0, "r_net"].mean()),
            "median_win_r": float(defined_r.loc[defined_r["net"] > 0, "r_net"].median()),
            "avg_loss_r": float(defined_r.loc[defined_r["net"] < 0, "r_net"].mean()),
            "median_loss_r": float(defined_r.loc[defined_r["net"] < 0, "r_net"].median()),
        },
        "temporal_stability": {
            "by_entry_year": by_year,
            "calendar_months": int(len(month_net)),
            "negative_months": int((month_net < 0).sum()),
            "positive_months": int((month_net > 0).sum()),
            "flat_months": int((month_net == 0).sum()),
        },
        "by_direction": by_direction,
        "by_actual_session": by_actual_session,
        "by_actual_utc_hour": by_actual_utc_hour,
        "by_holding_time": by_hold,
        "exit_clusters": by_cluster,
        "exit_cluster_context": exit_cluster_context(positions),
        "post_lock_counterfactual": post_lock_counterfactual(positions, m5),
        "context_features": feature_diagnostics(positions),
        "clock_model_diagnostic": {
            "ea_model": "EU last-Sunday DST for all years",
            "measured_broker_model": "EU DST through 2023; US DST from 2024",
            "clock_mismatch_positions": int(len(mismatch)),
            "clock_mismatch_economics": aggregate(mismatch) if len(mismatch) else None,
            "session_classification_mismatch_positions": int(len(session_mismatch)),
            "session_classification_mismatch_economics": aggregate(session_mismatch) if len(session_mismatch) else None,
            "causal_limit": "The clock mismatch is real but cannot explain losses before 2024 and is not a post-hoc trading filter.",
        },
        "matched_pairs": {
            "pairs": int(len(matched)),
            "contract": "same direction, actual UTC hour, risk decile +/-1, <=60 calendar days; greedy one-to-one minimum pre-entry context distance",
        },
        "interpretation_boundary": [
            "All context buckets are descriptive post-outcome diagnostics, not candidate filters.",
            "Holding-time buckets contain outcome-duration survivor bias and cannot be used at entry.",
            "The frozen run failed its 100% history-quality gate at 99%; all economics remain invalid diagnostic evidence.",
        ],
    }

    positions_path = out_dir / "positions_with_context.csv"
    m5_path = out_dir / "EURUSD_M5_2018_2026.parquet"
    matched_path = out_dir / "matched_pairs.csv"
    cases_path = out_dir / "cases.csv"
    diagnostics_path = out_dir / "trade_forensics.json"
    positions.to_csv(positions_path, index=False, date_format="%Y-%m-%dT%H:%M:%S")
    m5.to_parquet(m5_path, index=False)
    matched.to_csv(matched_path, index=False)
    cases = build_cases(positions)
    cases.to_csv(cases_path, index=False, date_format="%Y-%m-%dT%H:%M:%S")
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")

    output_files = [positions_path, m5_path, matched_path, cases_path, diagnostics_path]
    manifest = {
        "schema_version": "ictfvg_trade_forensics_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "script": str(script),
        "script_sha256": sha256_file(script),
        "outputs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in output_files
        ],
    }
    manifest_path = out_dir / "forensics_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        "FORENSICS PASS "
        f"positions={len(positions)} net={positions['net'].sum():.2f} "
        f"pf={profit_factor(positions['net']):.9f} matched_pairs={len(matched)} "
        f"out={out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
