#!/usr/bin/env python3
"""Quantify closed-bar M15/H1/H4/D1 context for HYP-011 C09 versus C10.

This is a read-only extension of the terminal HYP-011 postmortem.  Feature
definitions are fixed in this file before inspecting the rendered HTF charts.
No feature or threshold produced here has rerun, tuning, or promotion authority.
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
PAIR = {"winner": 6912, "loser": 6906}
M5_SHA256 = "AAF14451A0AA3671C5037A19ECB30E3A1A27B115A0F16CACBBB4D4209F921C73"
POSITIONS_SHA256 = "0540939EB9D0523ADB0E3EE599E9D1FE134DC8056439CD29FB8A1D0AB926055C"
CASES_SHA256 = "BB5C14D60D3A4BD168C178D30F8F58AC33623B3E127C01AD4592F0673A9EE1AB"

TIMEFRAMES = {
    "M15": "15min",
    "H1": "1h",
    "H4": "4h",
    "D1": "1D",
}

FEATURE_NAMES = [
    "adx14_mt5",
    "entry_vs_ema20_atr",
    "entry_vs_ema50_atr",
    "ema20_slope5_atr",
    "ret3_atr",
    "ret10_atr",
    "entry_range_pos20",
    "entry_vs_last_swing_high_atr",
    "entry_vs_last_swing_low_atr",
    "entry_in_last_closed_bar_range",
    "last_closed_body_atr",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def assert_sha(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise SystemExit(f"SHA mismatch for {path}: expected={expected} actual={actual}")


def safe(value: object) -> float | None:
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return None
    return float(value)


def resample_closed_bars(m5: pd.DataFrame, rule: str, atr_mt5, adx_mt5, ema) -> pd.DataFrame:
    frame = m5.copy()
    frame["bucket"] = frame["time_server"].dt.floor(rule)
    bars = (
        frame.groupby("bucket", sort=True, as_index=False)
        .agg(
            time_utc=("time_utc", "first"),
            utc_offset_h=("utc_offset_h", "first"),
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            tick_volume=("tick_volume", "sum"),
            real_volume=("real_volume", "sum"),
            m5_rows=("open", "size"),
        )
        .rename(columns={"bucket": "time_server"})
    )
    duration = pd.Timedelta(rule)
    bars["close_time_server"] = bars["time_server"] + duration
    bars["close_time_utc"] = bars["time_utc"] + duration
    # chart_case_render uses strict `< entry`; subtracting one microsecond makes
    # a bar that closes exactly at entry available without admitting a current
    # incomplete higher-timeframe candle.
    bars["available_time_utc"] = bars["close_time_utc"] - pd.Timedelta(microseconds=1)
    bars["atr14_mt5"] = atr_mt5(bars, 14)
    bars["adx14_mt5"] = adx_mt5(bars, 14)
    bars["ema20"] = ema(bars["close"], 20)
    bars["ema50"] = ema(bars["close"], 50)
    bars["ema20_slope5_atr"] = (bars["ema20"] - bars["ema20"].shift(5)) / bars["atr14_mt5"]
    bars["ret3_atr"] = (bars["close"] - bars["close"].shift(3)) / bars["atr14_mt5"]
    bars["ret10_atr"] = (bars["close"] - bars["close"].shift(10)) / bars["atr14_mt5"]
    bars["range20_high"] = bars["high"].rolling(20).max()
    bars["range20_low"] = bars["low"].rolling(20).min()
    return bars


def pivot_indices(bars: pd.DataFrame, end_index: int, high: bool, strength: int = 2) -> list[int]:
    column = "high" if high else "low"
    values = bars[column].to_numpy(dtype=float)
    found: list[int] = []
    start = max(strength, end_index - 100)
    latest_candidate = end_index - strength
    for index in range(start, latest_candidate + 1):
        center = values[index]
        left = values[index - strength : index]
        right = values[index + 1 : index + strength + 1]
        if high and np.all(center > left) and np.all(center > right):
            found.append(index)
        if not high and np.all(center < left) and np.all(center < right):
            found.append(index)
    return found


def structure_state(bars: pd.DataFrame, end_index: int) -> tuple[str, float, float]:
    highs = pivot_indices(bars, end_index, high=True)
    lows = pivot_indices(bars, end_index, high=False)
    if not highs or not lows:
        return "UNKNOWN", np.nan, np.nan
    last_high = float(bars.iloc[highs[-1]]["high"])
    last_low = float(bars.iloc[lows[-1]]["low"])
    if len(highs) < 2 or len(lows) < 2:
        return "INSUFFICIENT_PIVOTS", last_high, last_low
    high_up = last_high > float(bars.iloc[highs[-2]]["high"])
    low_up = last_low > float(bars.iloc[lows[-2]]["low"])
    if high_up and low_up:
        state = "HH_HL_UP"
    elif not high_up and not low_up:
        state = "LH_LL_DOWN"
    elif high_up and not low_up:
        state = "HH_LL_EXPANSION"
    else:
        state = "LH_HL_COMPRESSION"
    return state, last_high, last_low


def feature_at_entry(bars: pd.DataFrame, entry_server: pd.Timestamp, entry: float) -> dict[str, object]:
    close_times = bars["close_time_server"].to_numpy(dtype="datetime64[ns]")
    index = int(np.searchsorted(close_times, np.datetime64(entry_server), side="right") - 1)
    if index < 60:
        return {"feature_status": "INSUFFICIENT_HISTORY"}
    row = bars.iloc[index]
    atr = float(row["atr14_mt5"])
    if not math.isfinite(atr) or atr <= 0:
        return {"feature_status": "INVALID_ATR"}
    state, last_high, last_low = structure_state(bars, index)
    range_width = float(row["range20_high"] - row["range20_low"])
    last_bar_range = float(row["high"] - row["low"])
    if entry > last_high:
        break_state = "ABOVE_LAST_SWING_HIGH"
    elif entry < last_low:
        break_state = "BELOW_LAST_SWING_LOW"
    else:
        break_state = "INSIDE_LAST_SWING_RANGE"
    ema20 = float(row["ema20"])
    ema50 = float(row["ema50"])
    slope = float(row["ema20_slope5_atr"])
    if entry > ema20 > ema50 and slope > 0:
        bias = "BULLISH"
    elif entry < ema20 < ema50 and slope < 0:
        bias = "BEARISH"
    else:
        bias = "MIXED"
    return {
        "feature_status": "OK",
        "last_closed_bar_open_server": row["time_server"],
        "last_closed_bar_close_server": row["close_time_server"],
        "last_closed_bar_close_utc": row["close_time_utc"],
        "last_closed_ohlc": {
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        },
        "atr14_pips": atr * 10000.0,
        "adx14_mt5": float(row["adx14_mt5"]),
        "entry_vs_ema20_atr": (entry - ema20) / atr,
        "entry_vs_ema50_atr": (entry - ema50) / atr,
        "ema20_slope5_atr": slope,
        "ret3_atr": float(row["ret3_atr"]),
        "ret10_atr": float(row["ret10_atr"]),
        "entry_range_pos20": (
            (entry - float(row["range20_low"])) / range_width if range_width > 0 else np.nan
        ),
        "entry_vs_last_swing_high_atr": (entry - last_high) / atr,
        "entry_vs_last_swing_low_atr": (entry - last_low) / atr,
        "entry_in_last_closed_bar_range": (
            (entry - float(row["low"])) / last_bar_range if last_bar_range > 0 else np.nan
        ),
        "last_closed_body_atr": (float(row["close"] - row["open"])) / atr,
        "ema_bias": bias,
        "pivot_structure": state,
        "break_state": break_state,
        "last_confirmed_swing_high": last_high,
        "last_confirmed_swing_low": last_low,
    }


def flatten_features(position: pd.Series, bars_by_tf: dict[str, pd.DataFrame]) -> dict[str, object]:
    output: dict[str, object] = {
        "position_id": int(position["position_id"]),
        "side": position["side"],
        "net": float(position["net"]),
        "r_net": safe(position["r_net"]),
        "winner": bool(float(position["net"]) > 0),
        "entry_time_server": pd.Timestamp(position["entry_time_server"]),
        "entry_time_utc": pd.Timestamp(position["entry_time_utc"]),
        "entry": float(position["entry"]),
    }
    for tf_name, bars in bars_by_tf.items():
        features = feature_at_entry(
            bars,
            pd.Timestamp(position["entry_time_server"]),
            float(position["entry"]),
        )
        output[f"{tf_name}_feature_status"] = features["feature_status"]
        for key, value in features.items():
            if key in {"feature_status", "last_closed_ohlc"}:
                continue
            output[f"{tf_name}_{key}"] = value
        if features["feature_status"] == "OK":
            for key, value in features["last_closed_ohlc"].items():
                output[f"{tf_name}_last_{key}"] = value
    return output


def robust_distance_report(cohort: pd.DataFrame, columns: list[str]) -> dict[str, object]:
    usable = cohort.dropna(subset=columns).copy()
    first = usable[usable["position_id"] == PAIR["winner"]]
    second = usable[usable["position_id"] == PAIR["loser"]]
    if len(first) != 1 or len(second) != 1:
        raise SystemExit("pair is missing from complete-case HTF cohort")
    median = usable[columns].median()
    mad = (usable[columns] - median).abs().median()
    std = usable[columns].std(ddof=0).replace(0.0, 1.0)
    scale = (1.4826 * mad).where(mad > 0.0, std).replace(0.0, 1.0)
    z = (usable[columns] - median) / scale
    c09 = z.loc[first.index[0], columns]
    distances = ((z[columns] - c09) ** 2).mean(axis=1) ** 0.5
    pair_distance = float(distances.loc[second.index[0]])
    competitors = distances[usable["position_id"] != PAIR["winner"]]
    rank = int((competitors < pair_distance).sum() + 1)
    percentile = float(rank / len(competitors) * 100.0)
    return {
        "features": columns,
        "complete_short_positions": int(len(usable)),
        "robust_rms_distance": pair_distance,
        "c10_similarity_rank_from_c09": rank,
        "candidate_comparisons": int(len(competitors)),
        "nearest_percentile_pct": percentile,
        "interpretation": (
            "Lower percentile means C10 is closer to C09 than most other short entries; "
            "the distance uses median/MAD scaling and no outcome feature."
        ),
    }


def auc_for_feature(frame: pd.DataFrame, column: str) -> dict[str, object] | None:
    sample = frame[[column, "winner"]].dropna()
    positives = sample[sample["winner"]]
    negatives = sample[~sample["winner"]]
    if len(positives) < 2 or len(negatives) < 2:
        return None
    ranks = sample[column].rank(method="average")
    pos_rank_sum = float(ranks[sample["winner"]].sum())
    n_pos, n_neg = len(positives), len(negatives)
    auc = (pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    pooled = math.sqrt(
        ((n_pos - 1) * positives[column].var(ddof=1) + (n_neg - 1) * negatives[column].var(ddof=1))
        / max(n_pos + n_neg - 2, 1)
    )
    smd = (
        (float(positives[column].mean()) - float(negatives[column].mean())) / pooled
        if pooled > 0 else 0.0
    )
    return {
        "feature": column,
        "n_wins": int(n_pos),
        "n_losses": int(n_neg),
        "winner_median": safe(positives[column].median()),
        "loser_median": safe(negatives[column].median()),
        "auc_winner_high": float(auc),
        "univariate_separation_auc": float(max(auc, 1.0 - auc)),
        "standardized_mean_difference": float(smd),
    }


def categorical_regime_report(frame: pd.DataFrame, column: str) -> list[dict[str, object]]:
    """Describe each frozen HTF label without turning it into a trade filter."""
    sample = frame[[column, "r_net", "winner"]].dropna(subset=[column, "r_net"])
    report: list[dict[str, object]] = []
    for label, group in sample.groupby(column, sort=True):
        returns = group["r_net"].astype(float)
        gross_profit = float(returns.clip(lower=0.0).sum())
        gross_loss = float(-returns.clip(upper=0.0).sum())
        report.append(
            {
                "label": str(label),
                "n": int(len(group)),
                "win_rate_pct": float(group["winner"].mean() * 100.0),
                "profit_factor_r": gross_profit / gross_loss if gross_loss > 0.0 else None,
                "expectancy_r_per_trade": float(returns.mean()),
            }
        )
    return report


def json_safe_record(row: pd.Series, columns: list[str]) -> dict[str, object]:
    result: dict[str, object] = {}
    for column in columns:
        value = row[column]
        if isinstance(value, pd.Timestamp):
            result[column] = value.isoformat()
        elif isinstance(value, (np.bool_, bool)):
            result[column] = bool(value)
        elif isinstance(value, (np.integer, int)):
            result[column] = int(value)
        elif isinstance(value, (np.floating, float)):
            result[column] = safe(value)
        else:
            result[column] = value
    return result


def main() -> int:
    script = Path(__file__).resolve()
    root = script.parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=root / "02. AlphaFactory/runtime/ictfvg_hyp011_htf_pair",
    )
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    m5_path = root / "02. AlphaFactory/runtime/ictfvg_hyp011_forensics/EURUSD_M5_2018_2026.parquet"
    positions_path = root / "02. AlphaFactory/runtime/ictfvg_hyp011_forensics/positions_with_context.csv"
    cases_path = root / "02. AlphaFactory/runtime/ictfvg_hyp011_forensics/cases.csv"
    assert_sha(m5_path, M5_SHA256)
    assert_sha(positions_path, POSITIONS_SHA256)
    assert_sha(cases_path, CASES_SHA256)

    research_tools = root / "02. AlphaFactory/tools/research"
    sys.path.insert(0, str(research_tools))
    from indicators import adx_mt5, atr_mt5, ema

    m5 = pd.read_parquet(m5_path)
    m5["time_server"] = pd.to_datetime(m5["time_server"])
    m5["time_utc"] = pd.to_datetime(m5["time_utc"])
    positions = pd.read_csv(
        positions_path,
        parse_dates=["entry_time_server", "exit_time_server", "entry_time_utc", "exit_time_utc"],
    )
    shorts = positions[(positions["side"] == "SELL") & positions["entry_time_utc"].notna()].copy()

    bars_by_tf: dict[str, pd.DataFrame] = {}
    tf_paths: dict[str, Path] = {}
    for name, rule in TIMEFRAMES.items():
        bars = resample_closed_bars(m5, rule, atr_mt5, adx_mt5, ema)
        bars_by_tf[name] = bars
        path = out_dir / f"EURUSD_{name}_2018_2026.parquet"
        bars.to_parquet(path, index=False)
        tf_paths[name] = path

    records = [flatten_features(row, bars_by_tf) for _, row in shorts.iterrows()]
    cohort = pd.DataFrame.from_records(records)
    cohort_path = out_dir / "short_cohort_htf_features.csv"
    cohort.to_csv(cohort_path, index=False, date_format="%Y-%m-%dT%H:%M:%S")

    pair_rows = cohort[cohort["position_id"].isin(PAIR.values())].set_index(
        "position_id", drop=False
    )
    if set(pair_rows.index) != set(PAIR.values()):
        raise SystemExit("C09/C10 pair missing from short cohort")

    similarity: dict[str, object] = {}
    for tf in TIMEFRAMES:
        columns = [f"{tf}_{feature}" for feature in FEATURE_NAMES]
        similarity[tf] = robust_distance_report(cohort, columns)
    all_columns = [f"{tf}_{feature}" for tf in TIMEFRAMES for feature in FEATURE_NAMES]
    similarity["COMBINED"] = robust_distance_report(cohort, all_columns)

    categorical = {}
    for tf in TIMEFRAMES:
        categorical[tf] = {}
        for name in ["ema_bias", "pivot_structure", "break_state"]:
            column = f"{tf}_{name}"
            first = pair_rows.loc[PAIR["winner"], column]
            second = pair_rows.loc[PAIR["loser"], column]
            categorical[tf][name] = {
                "C09": first,
                "C10": second,
                "same": bool(first == second),
            }

    separation = []
    for column in all_columns:
        result = auc_for_feature(cohort, column)
        if result is not None:
            separation.append(result)
    separation.sort(key=lambda row: row["univariate_separation_auc"], reverse=True)

    categorical_regimes = {}
    for tf in TIMEFRAMES:
        categorical_regimes[tf] = {
            "ema_bias": categorical_regime_report(cohort, f"{tf}_ema_bias"),
            "pivot_structure": categorical_regime_report(cohort, f"{tf}_pivot_structure"),
        }

    selected_columns = [
        "position_id", "entry_time_server", "entry_time_utc", "entry", "net", "r_net", "winner"
    ]
    for tf in TIMEFRAMES:
        selected_columns.extend(
            [
                f"{tf}_last_closed_bar_open_server",
                f"{tf}_last_closed_bar_close_server",
                f"{tf}_atr14_pips",
                *[f"{tf}_{feature}" for feature in FEATURE_NAMES],
                f"{tf}_ema_bias",
                f"{tf}_pivot_structure",
                f"{tf}_break_state",
                f"{tf}_last_confirmed_swing_high",
                f"{tf}_last_confirmed_swing_low",
            ]
        )
    pair_detail = {
        "C09": json_safe_record(pair_rows.loc[PAIR["winner"]], selected_columns),
        "C10": json_safe_record(pair_rows.loc[PAIR["loser"]], selected_columns),
    }

    source_cases = pd.read_csv(cases_path)
    pair_cases = source_cases[source_cases["position_id"].isin(PAIR.values())].copy()
    pair_cases["case_id"] = pair_cases["position_id"].map(
        {PAIR["winner"]: "C09", PAIR["loser"]: "C10"}
    )
    pair_cases = pair_cases.sort_values("case_id")
    pair_cases_path = out_dir / "pair_cases.csv"
    pair_cases.to_csv(pair_cases_path, index=False)

    result = {
        "schema_version": "ictfvg_hyp011_htf_pair_forensics.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": HYPOTHESIS_ID,
        "scope": "read_only_post_outcome_pair_diagnostic_no_filter_or_rerun_authority",
        "pair": {
            "C09_winner_position_id": PAIR["winner"],
            "C10_loser_position_id": PAIR["loser"],
            "selection": "Frozen by the prior Grok forensic pass before HTF chart rendering.",
        },
        "information_set": {
            "bar_rule": "Only HTF bars with close_time_server <= entry_time_server are used.",
            "indicator_family": "MT5-parity atr_mt5/adx_mt5; EMA adjust=False.",
            "feature_outcome_leakage": False,
            "outcomes_used_only_for_posthoc_population_separation": True,
        },
        "input_identity": {
            "m5_path": str(m5_path), "m5_sha256": M5_SHA256,
            "positions_path": str(positions_path), "positions_sha256": POSITIONS_SHA256,
            "cases_path": str(cases_path), "cases_sha256": CASES_SHA256,
        },
        "short_cohort_positions": int(len(cohort)),
        "pair_detail": pair_detail,
        "categorical_agreement": categorical,
        "similarity": similarity,
        "population_univariate_separation_top10": separation[:10],
        "population_categorical_regimes": categorical_regimes,
        "interpretation_boundary": [
            "Similarity is measured only on point-in-time HTF features and excludes PnL/outcome.",
            "Population separation is descriptive and post-outcome; it cannot authorize a filter.",
            "One winner/loser pair cannot establish a causal HTF rule.",
            "HYP-011 remains terminal and invalid diagnostic at 99% tester history quality.",
        ],
    }
    result_path = out_dir / "pair_htf_forensics.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    outputs = [*tf_paths.values(), cohort_path, pair_cases_path, result_path]
    manifest = {
        "schema_version": "ictfvg_hyp011_htf_pair_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "script": str(script),
        "script_sha256": sha256_file(script),
        "outputs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in outputs
        ],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        "HTF_PAIR_FORENSICS PASS "
        f"shorts={len(cohort)} combined_percentile="
        f"{similarity['COMBINED']['nearest_percentile_pct']:.3f} out={out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
