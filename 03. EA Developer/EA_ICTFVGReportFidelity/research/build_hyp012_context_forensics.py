#!/usr/bin/env python3
"""Build frozen post-run diagnostics for HYP-012 context-state entries.

This script does not tune or authorize another run.  It joins each executed
challenger position to the last closed M5 confirmation bar, reconstructs the
original bounded sweep where possible, adds closed H1/H4 regime proxies, and
emits descriptive winner/loser and bucket diagnostics plus a deterministic
four-case chart list.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


POINT = 0.00001
PIP = 0.0001
HYPOTHESIS_ID = "HYP-ICT-FVG-CONTEXT-STATE-EURUSD-M5-012"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def safe_float(value: object) -> float | None:
    if value is None or pd.isna(value) or not np.isfinite(float(value)):
        return None
    return float(value)


def europe_server_offset_hours(server_time: pd.Timestamp) -> int:
    """Mirror the EA's Europe-DST server clock for an uncovered tail bar."""
    march_end = pd.Timestamp(server_time.year, 3, 31)
    march_last_sunday = march_end - pd.Timedelta(days=(march_end.dayofweek + 1) % 7)
    october_end = pd.Timestamp(server_time.year, 10, 31)
    october_last_sunday = october_end - pd.Timedelta(days=(october_end.dayofweek + 1) % 7)
    start = march_last_sunday + pd.Timedelta(hours=3)
    finish = october_last_sunday + pd.Timedelta(hours=4)
    return 3 if start <= server_time < finish else 2


def aggregate(group: pd.DataFrame) -> dict[str, object]:
    positive = group.loc[group["net"] > 0, "net"].sum()
    negative = -group.loc[group["net"] < 0, "net"].sum()
    positive_r = group.loc[group["r_net"] > 0, "r_net"].sum()
    negative_r = -group.loc[group["r_net"] < 0, "r_net"].sum()
    return {
        "positions": int(len(group)),
        "win_rate_pct": safe_float((group["net"] > 0).mean() * 100.0),
        "net": safe_float(group["net"].sum()),
        "profit_factor_money": safe_float(positive / negative) if negative > 0 else None,
        "profit_factor_r": safe_float(positive_r / negative_r) if negative_r > 0 else None,
        "expectancy_r": safe_float(group["r_net"].mean()),
    }


def is_pivot(values: pd.Series, index: int, strength: int, high: bool) -> bool:
    if index - strength < 0 or index + strength >= len(values):
        return False
    center = float(values.iloc[index])
    for offset in range(1, strength + 1):
        newer = float(values.iloc[index + offset])
        older = float(values.iloc[index - offset])
        if high and (center <= newer or center <= older):
            return False
        if not high and (center >= newer or center >= older):
            return False
    return True


def latest_pivots(bars: pd.DataFrame, sweep_index: int) -> tuple[float | None, float | None]:
    pivot_high: float | None = None
    pivot_low: float | None = None
    # MQL series indices 2..22 map to chronological sweep_index-2..-22.
    for series_index in range(2, 23):
        candidate = sweep_index - series_index
        if candidate < 2:
            break
        if pivot_high is None and is_pivot(bars["high"], candidate, 2, high=True):
            pivot_high = float(bars.iloc[candidate]["high"])
        if pivot_low is None and is_pivot(bars["low"], candidate, 2, high=False):
            pivot_low = float(bars.iloc[candidate]["low"])
        if pivot_high is not None and pivot_low is not None:
            break
    return pivot_high, pivot_low


def reconstruct_sweep(
    bars: pd.DataFrame, confirmation_index: int, direction: int
) -> dict[str, object]:
    confirmation = bars.iloc[confirmation_index]
    candidates: list[dict[str, object]] = []
    # The oldest live setup wins because later same-direction sweeps are counted
    # as duplicates and cannot replace it.
    for lag in range(3, 0, -1):
        sweep_index = confirmation_index - lag
        if sweep_index < 25:
            continue
        sweep = bars.iloc[sweep_index]
        pivot_high, pivot_low = latest_pivots(bars, sweep_index)
        pivot = pivot_low if direction > 0 else pivot_high
        if pivot is None:
            continue
        swept = (
            float(sweep["low"]) < pivot and float(sweep["close"]) > pivot
            if direction > 0
            else float(sweep["high"]) > pivot and float(sweep["close"]) < pivot
        )
        if not swept:
            continue
        interim = bars.iloc[sweep_index + 1 : confirmation_index]
        invalidated = (
            bool((interim["close"] <= float(sweep["low"])).any())
            if direction > 0
            else bool((interim["close"] >= float(sweep["high"])).any())
        )
        if invalidated:
            continue
        opposite_break = (
            float(confirmation["close"]) > float(sweep["high"])
            if direction > 0
            else float(confirmation["close"]) < float(sweep["low"])
        )
        if not opposite_break:
            continue
        candidates.append(
            {
                "sweep_index": sweep_index,
                "sweep_time_server": sweep["time_server"],
                "bars_after_sweep": lag,
                "pivot": pivot,
                "sweep_open": float(sweep["open"]),
                "sweep_high": float(sweep["high"]),
                "sweep_low": float(sweep["low"]),
                "sweep_close": float(sweep["close"]),
                "sweep_depth_pips": (
                    (pivot - float(sweep["low"])) / PIP
                    if direction > 0
                    else (float(sweep["high"]) - pivot) / PIP
                ),
                "sweep_reclaim_pips": (
                    (float(sweep["close"]) - pivot) / PIP
                    if direction > 0
                    else (pivot - float(sweep["close"])) / PIP
                ),
            }
        )
    if not candidates:
        return {"sweep_reconstruction": "NO_MATCH"}
    chosen = candidates[0]
    chosen["sweep_reconstruction"] = "MATCHED_LOCAL_STATE"
    chosen["candidate_count"] = len(candidates)
    return chosen


def build_timeframe(bars: pd.DataFrame, rule: str, minutes: int) -> pd.DataFrame:
    frame = (
        bars.set_index("time_utc")[["open", "high", "low", "close"]]
        .resample(rule, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
        .reset_index()
    )
    prior_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prior_close).abs(),
            (frame["low"] - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    frame["atr14"] = true_range.rolling(14).mean()
    frame["ema20"] = frame["close"].ewm(span=20, adjust=False).mean()
    frame["ema50"] = frame["close"].ewm(span=50, adjust=False).mean()
    frame["return5"] = frame["close"] - frame["close"].shift(5)
    frame["available_time_utc"] = frame["time_utc"] + pd.Timedelta(minutes=minutes)
    return frame[["available_time_utc", "atr14", "ema20", "ema50", "return5"]]


def attach_timeframe(
    positions: pd.DataFrame, timeframe: pd.DataFrame, prefix: str
) -> pd.DataFrame:
    renamed = timeframe.rename(
        columns={
            "atr14": f"{prefix}_atr14",
            "ema20": f"{prefix}_ema20",
            "ema50": f"{prefix}_ema50",
            "return5": f"{prefix}_return5",
        }
    )
    result = pd.merge_asof(
        positions.sort_values("entry_time_utc"),
        renamed.sort_values("available_time_utc"),
        left_on="entry_time_utc",
        right_on="available_time_utc",
        direction="backward",
    )
    result[f"{prefix}_ema_spread_directional_atr"] = (
        result["direction"] * (result[f"{prefix}_ema20"] - result[f"{prefix}_ema50"])
        / result[f"{prefix}_atr14"]
    )
    result[f"{prefix}_return5_directional_atr"] = (
        result["direction"] * result[f"{prefix}_return5"] / result[f"{prefix}_atr14"]
    )
    return result.drop(columns=["available_time_utc"])


def bucket_diagnostics(data: pd.DataFrame, feature: str) -> list[dict[str, object]]:
    valid = data.dropna(subset=[feature]).copy()
    if valid[feature].nunique() < 2:
        return []
    try:
        valid["_bucket"] = pd.qcut(valid[feature], 4, duplicates="drop")
    except ValueError:
        return []
    rows: list[dict[str, object]] = []
    for bucket, group in valid.groupby("_bucket", observed=True):
        row = aggregate(group)
        row.update(
            {
                "bucket": str(bucket),
                "feature_min": safe_float(group[feature].min()),
                "feature_max": safe_float(group[feature].max()),
            }
        )
        rows.append(row)
    return rows


def matched_short_pair(data: pd.DataFrame) -> dict[str, object]:
    """Freeze the closest win/loss short pair within 60 days and same state."""
    features = [
        "confirmation_body_vs_prior20",
        "confirmation_directional_close_location",
        "confirmation_range_pips",
        "sweep_depth_pips",
        "sweep_reclaim_pips",
        "risk_pts",
        "h1_ema_spread_directional_atr",
        "h4_ema_spread_directional_atr",
    ]
    shorts = data[(data["side"] == "SELL") & data[features].notna().all(axis=1)].copy()
    scales = shorts[features].std(ddof=0).replace(0.0, 1.0)
    best: tuple[float, pd.Series, pd.Series] | None = None
    wins = shorts[shorts["net"] > 0]
    losses = shorts[shorts["net"] < 0]
    for _, win in wins.iterrows():
        candidates = losses[
            (losses["session_actual"] == win["session_actual"])
            & (losses["bars_after_sweep"] == win["bars_after_sweep"])
            & ((losses["entry_time_server"] - win["entry_time_server"]).abs() <= pd.Timedelta(days=60))
        ]
        if candidates.empty:
            continue
        distance = ((candidates[features] - win[features]).abs() / scales).sum(axis=1)
        chosen_index = distance.idxmin()
        candidate = (float(distance.loc[chosen_index]), win, candidates.loc[chosen_index])
        if best is None or candidate[0] < best[0]:
            best = candidate
    if best is None:
        raise SystemExit("No matched short win/loss pair found")
    distance, win, loss = best
    return {
        "distance": distance,
        "win_position_id": int(win["position_id"]),
        "loss_position_id": int(loss["position_id"]),
        "days_apart": abs(
            (pd.Timestamp(win["entry_time_server"]) - pd.Timestamp(loss["entry_time_server"])).total_seconds()
        ) / 86400.0,
        "session": str(win["session_actual"]),
        "bars_after_sweep": int(win["bars_after_sweep"]),
        "win_r": float(win["r_net"]),
        "loss_r": float(loss["r_net"]),
        "features": {
            feature: {"win": safe_float(win[feature]), "loss": safe_float(loss[feature])}
            for feature in features
        },
    }


def choose_cases(data: pd.DataFrame, pair: dict[str, object]) -> pd.DataFrame:
    winners = data[data["r_net"] > 0].copy()
    losers = data[data["r_net"] < 0].copy()
    median_win = float(winners["r_net"].median())
    median_loss = float(losers["r_net"].median())
    selected = [
        ("CTX01", winners.loc[winners["r_net"].idxmax()], "best_r_winner"),
        ("CTX02", winners.loc[(winners["r_net"] - median_win).abs().idxmin()], "median_winner"),
        ("CTX03", losers.loc[(losers["r_net"] - median_loss).abs().idxmin()], "median_loser"),
        ("CTX04", losers.loc[losers["r_net"].idxmin()], "worst_r_loser"),
        (
            "CTX05",
            data.loc[data["position_id"] == pair["win_position_id"]].iloc[0],
            "matched_short_pair_winner",
        ),
        (
            "CTX06",
            data.loc[data["position_id"] == pair["loss_position_id"]].iloc[0],
            "matched_short_pair_loser",
        ),
    ]
    rows: list[dict[str, object]] = []
    for case_id, record, reason in selected:
        risk_price = float(record["risk_pts"]) * POINT
        direction = int(record["direction"])
        server_to_utc = pd.Timestamp(record["entry_time_server"]) - pd.Timestamp(
            record["entry_time_utc"]
        )
        sweep_time_utc = pd.Timestamp(record["sweep_time_server"]) - server_to_utc
        confirmation_time_utc = (
            pd.Timestamp(record["confirmation_time_server"]) - server_to_utc
        )
        rows.append(
            {
                "case_id": case_id,
                "position_id": int(record["position_id"]),
                "entry_time_utc": record["entry_time_utc"],
                "exit_time_utc": record["exit_time_utc"],
                "direction": direction,
                "entry": float(record["entry"]),
                "sl": float(record["entry"] - direction * risk_price),
                "tp": float(record["entry"] + direction * 2.0 * risk_price),
                "exit": float(record["exit"]),
                "reason": reason,
                "sweep_time_utc": sweep_time_utc,
                "pivot": float(record["pivot"]),
                "sweep_open": float(record["sweep_open"]),
                "sweep_high": float(record["sweep_high"]),
                "sweep_low": float(record["sweep_low"]),
                "sweep_close": float(record["sweep_close"]),
                "sweep_depth_pips": float(record["sweep_depth_pips"]),
                "sweep_reclaim_pips": float(record["sweep_reclaim_pips"]),
                "confirmation_time_utc": confirmation_time_utc,
                "confirmation_open": float(record["confirmation_open"]),
                "confirmation_high": float(record["confirmation_high"]),
                "confirmation_low": float(record["confirmation_low"]),
                "confirmation_close": float(record["confirmation_close"]),
                "confirmation_body_vs_prior20": float(
                    record["confirmation_body_vs_prior20"]
                ),
                "confirmation_directional_close_location": float(
                    record["confirmation_directional_close_location"]
                ),
                "bars_after_sweep": int(record["bars_after_sweep"]),
                "label": (
                    f"pid={int(record['position_id'])}; netR={record['r_net']:.3f}; "
                    f"confirm={record['confirmation_body_vs_prior20']:.2f}x; "
                    f"lag={record.get('bars_after_sweep', np.nan):.0f}"
                ),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    script = Path(__file__).resolve()
    root = script.parents[3]
    result_dir = root / "02. AlphaFactory/runtime/ictfvg_hyp012_context_result"
    positions_path = result_dir / "positions_challenger.csv"
    bars_path = root / "02. AlphaFactory/runtime/ictfvg_hyp011_forensics/EURUSD_M5_2018_2026.parquet"
    output_dir = root / "02. AlphaFactory/runtime/ictfvg_hyp012_context_forensics"
    output_dir.mkdir(parents=True, exist_ok=True)

    positions = pd.read_csv(
        positions_path, parse_dates=["entry_time_server", "exit_time_server"]
    )
    positions["direction"] = np.where(positions["side"] == "BUY", 1, -1)
    bars = pd.read_parquet(bars_path).sort_values("time_server").reset_index(drop=True)
    bars["time_server"] = pd.to_datetime(bars["time_server"])
    bars["time_utc"] = pd.to_datetime(bars["time_utc"])
    bar_index = pd.Series(bars.index, index=bars["time_server"])

    records: list[dict[str, object]] = []
    for position in positions.itertuples(index=False):
        # The first executable tick can arrive seconds after the M5 boundary.
        confirmation_time = pd.Timestamp(position.entry_time_server).floor("5min") - pd.Timedelta(minutes=5)
        if confirmation_time not in bar_index.index:
            offset = europe_server_offset_hours(pd.Timestamp(position.entry_time_server))
            records.append(
                {
                    "position_id": int(position.position_id),
                    "context_status": "CONFIRMATION_BAR_MISSING",
                    "entry_time_utc": pd.Timestamp(position.entry_time_server) - pd.Timedelta(hours=offset),
                    "exit_time_utc": pd.Timestamp(position.exit_time_server) - pd.Timedelta(hours=offset),
                }
            )
            continue
        index = int(bar_index.loc[confirmation_time])
        confirmation = bars.iloc[index]
        direction = int(position.direction)
        mean_prior_body = float(
            (bars.iloc[index - 20 : index]["close"] - bars.iloc[index - 20 : index]["open"])
            .abs()
            .mean()
        )
        body = abs(float(confirmation["close"] - confirmation["open"]))
        bar_range = float(confirmation["high"] - confirmation["low"])
        directional_close_location = (
            (float(confirmation["close"] - confirmation["low"]) / bar_range)
            if direction > 0
            else (float(confirmation["high"] - confirmation["close"]) / bar_range)
        )
        entry_utc = pd.Timestamp(position.entry_time_server) - pd.Timedelta(
            hours=int(confirmation["utc_offset_h"])
        )
        exit_utc = pd.Timestamp(position.exit_time_server) - pd.Timedelta(
            hours=int(confirmation["utc_offset_h"])
        )
        row: dict[str, object] = {
            "position_id": int(position.position_id),
            "context_status": "OK",
            "confirmation_time_server": confirmation_time,
            "entry_time_utc": entry_utc,
            "exit_time_utc": exit_utc,
            "actual_utc_hour": int(entry_utc.hour),
            "confirmation_open": float(confirmation["open"]),
            "confirmation_high": float(confirmation["high"]),
            "confirmation_low": float(confirmation["low"]),
            "confirmation_close": float(confirmation["close"]),
            "confirmation_body_pips": body / PIP,
            "confirmation_body_vs_prior20": body / mean_prior_body if mean_prior_body > 0 else np.nan,
            "confirmation_range_pips": bar_range / PIP,
            "confirmation_directional_close_location": directional_close_location,
        }
        row.update(reconstruct_sweep(bars, index, direction))
        records.append(row)

    context = pd.DataFrame(records)
    data = positions.merge(context, on="position_id", how="left", validate="one_to_one")
    data = attach_timeframe(data, build_timeframe(bars, "1h", 60), "h1")
    data = attach_timeframe(data, build_timeframe(bars, "4h", 240), "h4")
    data["session_actual"] = np.where(
        data["actual_utc_hour"].between(7, 10), "LONDON",
        np.where(data["actual_utc_hour"].between(13, 16), "NEW_YORK", "CLOCK_MISMATCH"),
    )
    data["h1_aligned"] = data["h1_ema_spread_directional_atr"] > 0
    data["h4_aligned"] = data["h4_ema_spread_directional_atr"] > 0
    data["h1_h4_alignment"] = np.select(
        [data["h1_aligned"] & data["h4_aligned"], ~data["h1_aligned"] & ~data["h4_aligned"]],
        ["BOTH_ALIGNED", "BOTH_OPPOSED"],
        default="MIXED",
    )
    data["hold_hours"] = (
        data["exit_time_utc"] - data["entry_time_utc"]
    ).dt.total_seconds() / 3600.0
    data["crossed_weekend_close"] = data["hold_hours"] >= 30.0

    features = [
        "confirmation_body_vs_prior20",
        "confirmation_directional_close_location",
        "confirmation_range_pips",
        "bars_after_sweep",
        "sweep_depth_pips",
        "sweep_reclaim_pips",
        "risk_pts",
        "h1_ema_spread_directional_atr",
        "h1_return5_directional_atr",
        "h4_ema_spread_directional_atr",
        "h4_return5_directional_atr",
    ]
    medians = {
        feature: {
            "wins": safe_float(data.loc[data["net"] > 0, feature].median()),
            "losses": safe_float(data.loc[data["net"] < 0, feature].median()),
        }
        for feature in features
    }
    buckets = {feature: bucket_diagnostics(data, feature) for feature in features}
    categorical: dict[str, list[dict[str, object]]] = {}
    for column in ["side", "session_actual", "bars_after_sweep", "h1_h4_alignment"]:
        categorical[column] = []
        for value, group in data.groupby(column, dropna=False):
            row = aggregate(group)
            row[column] = "MISSING" if pd.isna(value) else str(value)
            categorical[column].append(row)

    weekend = data[data["crossed_weekend_close"]]
    beyond_stop = data[data["r_net"] < -1.30]
    exposure_diagnostics = {
        "crossed_weekend_close_positions": int(len(weekend)),
        "crossed_weekend_close_net": safe_float(weekend["net"].sum()),
        "crossed_weekend_close_r": safe_float(weekend["r_net"].sum()),
        "positions_worse_than_minus_1_30r": int(len(beyond_stop)),
        "positions_worse_than_minus_1_30r_net": safe_float(beyond_stop["net"].sum()),
        "positions_worse_than_minus_1_30r_r": safe_float(beyond_stop["r_net"].sum()),
        "worst_position": {
            "position_id": int(data.loc[data["r_net"].idxmin(), "position_id"]),
            "r_net": safe_float(data["r_net"].min()),
            "entry_time_utc": str(data.loc[data["r_net"].idxmin(), "entry_time_utc"]),
            "exit_time_utc": str(data.loc[data["r_net"].idxmin(), "exit_time_utc"]),
        },
        "diagnosis": (
            "Tick-driven >=22:00 UTC flatten cannot close before the Friday market "
            "gap when no tick arrives at or after the threshold; positions then close "
            "on the first Sunday/Monday tick. This is an execution defect, not alpha."
        ),
    }

    positions_output = output_dir / "positions_with_context.csv"
    data.to_csv(positions_output, index=False, date_format="%Y-%m-%dT%H:%M:%S")
    pair = matched_short_pair(data)
    cases = choose_cases(data, pair)
    cases_output = output_dir / "cases.csv"
    cases.to_csv(cases_output, index=False, date_format="%Y-%m-%dT%H:%M:%S")
    payload = {
        "schema_version": "hyp012_context_forensics.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": HYPOTHESIS_ID,
        "boundary": (
            "Post-run descriptive diagnostic only. No threshold selection, rerun, "
            "promotion, or economic authority. H1/H4 features use only completed bars."
        ),
        "inputs": {
            "positions": str(positions_path),
            "positions_sha256": sha256_file(positions_path),
            "bars": str(bars_path),
            "bars_sha256": sha256_file(bars_path),
        },
        "coverage": {
            "positions": int(len(data)),
            "confirmation_context_ok": int((data["context_status"] == "OK").sum()),
            "sweep_reconstruction_matched": int(
                (data["sweep_reconstruction"] == "MATCHED_LOCAL_STATE").sum()
            ),
        },
        "winner_loser_medians": medians,
        "quartile_diagnostics": buckets,
        "categorical_diagnostics": categorical,
        "matched_short_pair": pair,
        "exposure_diagnostics": exposure_diagnostics,
        "outputs": {
            "positions_with_context": str(positions_output),
            "positions_with_context_sha256": sha256_file(positions_output),
            "cases": str(cases_output),
            "cases_sha256": sha256_file(cases_output),
        },
    }
    output = output_dir / "forensics.json"
    output.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "hyp012_context_forensics_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "files": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in [output, positions_output, cases_output]
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        "HYP012_CONTEXT_FORENSICS PASS "
        f"positions={len(data)} sweep_matched={payload['coverage']['sweep_reconstruction_matched']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
