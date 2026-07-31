"""Outcome-blind ASRS Stage-0 cadence and cost-geometry probe.

No future excursion, trade outcome, PnL, PF, MFE, MAE, or holdout data is
computed. The script implements the exact frozen HYP-ASRS-EURUSD-M5-001 plan.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[3]
SDK = WORKSPACE / "02. AlphaFactory" / "tools" / "research"
if str(SDK) not in sys.path:
    sys.path.insert(0, str(SDK))

from indicators import adx_mt5, atr_mt5  # noqa: E402
from sealed_loader import elapsed_weeks, load_sealed_bars, sha256_file  # noqa: E402


HYPOTHESIS_ID = "HYP-ASRS-EURUSD-M5-001"
PLAN_REL = (
    "03. EA Developer/EA_ASRS_AdaptiveSweepReclaim/research/"
    "HYP-ASRS-EURUSD-M5-001_PROBE_PLAN.md"
)
PLAN_SHA256 = "0E6BC15E99E78ACF6D9B5FC88C267CFF685BDEF33855F525450592A0E5BF19D0"
DATA_REL = "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
DATA_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
DESIGN_START = pd.Timestamp("2019-01-01")
HOLDOUT_START = pd.Timestamp("2023-01-01")
PIP = 0.0001
FORBIDDEN_OUTCOME_TOKENS = (
    "pnl",
    "profit",
    "return",
    "expectancy",
    "mfe",
    "mae",
    "win",
    "loss",
    "target_hit",
    "stop_hit",
)


def resample_complete_m5(m1: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Build closed UTC M5 bars and discard every incomplete minute bin."""
    required = {
        "time_utc",
        "time_server",
        "utc_offset_h",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    }
    missing = required - set(m1.columns)
    if missing:
        raise RuntimeError(f"MISSING M1 COLUMNS: {sorted(missing)}")
    src = m1.copy()
    src["time_utc"] = pd.to_datetime(src["time_utc"])
    src["time_server"] = pd.to_datetime(src["time_server"])
    src = src.sort_values("time_utc").drop_duplicates("time_utc", keep=False)
    src["_bin"] = src["time_utc"].dt.floor("5min")
    grouped = src.groupby("_bin", sort=True)
    bars = grouped.agg(
        time_server=("time_server", "first"),
        utc_offset_h=("utc_offset_h", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        _rows=("time_utc", "size"),
        _unique_minutes=("time_utc", "nunique"),
        _first_minute=("time_utc", "min"),
        _last_minute=("time_utc", "max"),
    ).reset_index(names="time_utc")
    complete = (
        (bars["_rows"] == 5)
        & (bars["_unique_minutes"] == 5)
        & ((bars["_last_minute"] - bars["_first_minute"]) == pd.Timedelta(minutes=4))
    )
    quality = {
        "input_m1_rows": int(len(src)),
        "total_m5_bins": int(len(bars)),
        "complete_m5_bins": int(complete.sum()),
        "incomplete_m5_bins": int((~complete).sum()),
    }
    keep = [
        "time_utc",
        "time_server",
        "utc_offset_h",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
    ]
    return bars.loc[complete, keep].reset_index(drop=True), quality


def prior_volume_mean(volume: pd.Series, period: int = 20) -> pd.Series:
    """Mean of prior completed bars; the current bar never enters its threshold."""
    return volume.astype(float).shift(1).rolling(period, min_periods=period).mean()


def mark_confirmed_pivots(bars: pd.DataFrame, strength: int = 2) -> pd.DataFrame:
    """Expose a pivot only when it was known before the current bar began.

    For N=2 and scan bar s, the latest newly available pivot is p=s-3, matching
    the frozen p <= s-3 contract.
    """
    if strength < 1:
        raise ValueError("strength must be >= 1")
    high = bars["high"].to_numpy(float)
    low = bars["low"].to_numpy(float)
    n = len(bars)
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)
    for p in range(strength, n - strength):
        left_h = high[p - strength : p]
        right_h = high[p + 1 : p + strength + 1]
        left_l = low[p - strength : p]
        right_l = low[p + 1 : p + strength + 1]
        is_high[p] = high[p] > np.max(left_h) and high[p] > np.max(right_h)
        is_low[p] = low[p] < np.min(left_l) and low[p] < np.min(right_l)

    last_high = np.full(n, np.nan)
    last_low = np.full(n, np.nan)
    last_high_index = np.full(n, np.nan)
    last_low_index = np.full(n, np.nan)
    high_value = np.nan
    low_value = np.nan
    high_index = np.nan
    low_index = np.nan
    for s in range(n):
        p = s - strength - 1
        if p >= strength:
            if is_high[p]:
                high_value, high_index = high[p], float(p)
            if is_low[p]:
                low_value, low_index = low[p], float(p)
        last_high[s], last_high_index[s] = high_value, high_index
        last_low[s], last_low_index[s] = low_value, low_index
    return pd.DataFrame(
        {
            "pivot_high_flag": is_high,
            "pivot_low_flag": is_low,
            "last_pivot_high": last_high,
            "last_pivot_high_index": last_high_index,
            "last_pivot_low": last_low,
            "last_pivot_low_index": last_low_index,
        },
        index=bars.index,
    )


def add_stage0_features(bars: pd.DataFrame) -> pd.DataFrame:
    out = bars.copy()
    out["atr"] = atr_mt5(out, 14)
    out["adx"] = adx_mt5(out, 14)
    out["volume_mean20"] = prior_volume_mean(out["tick_volume"], 20)
    return pd.concat([out, mark_confirmed_pivots(out, 2)], axis=1)


def _in_frozen_session(timestamp) -> bool:
    ts = pd.Timestamp(timestamp)
    if not 7 <= ts.hour < 21:
        return False
    return not (ts.dayofweek == 4 and ts.hour >= 16)


def _record_common(
    bars: pd.DataFrame,
    direction: str,
    sweep: int,
    reclaim: int,
    retest: int,
    entry: int,
    pivot: float,
    pivot_index: int,
    stop: float,
) -> dict:
    entry_price = float(bars.iloc[entry]["open"])
    risk_price = entry_price - stop if direction == "LONG" else stop - entry_price
    risk_pips = risk_price / PIP
    if not np.isfinite(risk_pips) or risk_pips <= 0:
        raise RuntimeError("NONPOSITIVE INITIAL RISK")
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "direction": direction,
        "sweep_index": int(sweep),
        "reclaim_index": int(reclaim),
        "retest_index": int(retest),
        "entry_index": int(entry),
        "sweep_time_utc": str(pd.Timestamp(bars.iloc[sweep]["time_utc"])),
        "reclaim_time_utc": str(pd.Timestamp(bars.iloc[reclaim]["time_utc"])),
        "retest_time_utc": str(pd.Timestamp(bars.iloc[retest]["time_utc"])),
        "entry_time_utc": str(pd.Timestamp(bars.iloc[entry]["time_utc"])),
        "pivot_price": float(pivot),
        "pivot_index": int(pivot_index),
        "entry_price": entry_price,
        "initial_stop": float(stop),
        "initial_risk_pips": float(risk_pips),
        "sweep_atr_pips": float(bars.iloc[sweep]["atr"] / PIP),
        "sweep_tick_volume": float(bars.iloc[sweep]["tick_volume"]),
        "prior20_tick_volume_mean": float(bars.iloc[sweep]["volume_mean20"]),
        "tick_volume_ratio": float(
            bars.iloc[sweep]["tick_volume"] / bars.iloc[sweep]["volume_mean20"]
        ),
        "reclaim_adx": float(bars.iloc[reclaim]["adx"]),
        "retest_outside_session": not _in_frozen_session(
            bars.iloc[retest]["time_utc"]
        ),
        "entry_outside_session": not _in_frozen_session(
            bars.iloc[entry]["time_utc"]
        ),
        "calendar_year": int(pd.Timestamp(bars.iloc[entry]["time_utc"]).year),
        "cost_r_0_5": float(0.5 / risk_pips),
        "cost_r_1_5": float(1.5 / risk_pips),
        "cost_r_2_25": float(2.25 / risk_pips),
        "cost_r_3_0": float(3.0 / risk_pips),
    }


def scan_asrs_events(bars: pd.DataFrame) -> dict:
    """Scan the two frozen arms without reading any bar after entry."""
    required = {
        "time_utc",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "atr",
        "adx",
        "volume_mean20",
        "last_pivot_low",
        "last_pivot_low_index",
        "last_pivot_high",
        "last_pivot_high_index",
    }
    missing = required - set(bars.columns)
    if missing:
        raise RuntimeError(f"MISSING M5 COLUMNS: {sorted(missing)}")

    n = len(bars)
    o = bars["open"].to_numpy(float)
    h = bars["high"].to_numpy(float)
    l = bars["low"].to_numpy(float)
    c = bars["close"].to_numpy(float)
    volume = bars["tick_volume"].to_numpy(float)
    atr = bars["atr"].to_numpy(float)
    adx = bars["adx"].to_numpy(float)
    vol_mean = bars["volume_mean20"].to_numpy(float)
    pivot_low = bars["last_pivot_low"].to_numpy(float)
    pivot_high = bars["last_pivot_high"].to_numpy(float)
    pivot_low_index = bars["last_pivot_low_index"].to_numpy(float)
    pivot_high_index = bars["last_pivot_high_index"].to_numpy(float)
    times = pd.to_datetime(bars["time_utc"]).to_numpy()

    control_rows: list[dict] = []
    challenger_rows: list[dict] = []
    funnel = {
        "control_same_bar_sweep_reclaims_all_hours": 0,
        "control_in_session_entries": 0,
        "challenger_depth_sweeps": 0,
        "challenger_reclaims_same_or_next": 0,
        "challenger_adx_eligible_all_hours": 0,
        "challenger_volume_eligible_all_hours": 0,
        "challenger_adx_session_eligible": 0,
        "challenger_volume_eligible": 0,
        "challenger_mandatory_retest_entries": 0,
    }

    for s in range(23, n - 3):
        # Matched high-recall same-bar control.
        if np.isfinite(pivot_low[s]) and l[s] < pivot_low[s] and c[s] > pivot_low[s]:
            funnel["control_same_bar_sweep_reclaims_all_hours"] += 1
            if _in_frozen_session(times[s]):
                entry = s + 1
                stop = l[s] - 1.5 * PIP
                try:
                    row = _record_common(
                        bars,
                        "LONG",
                        s,
                        s,
                        s,
                        entry,
                        pivot_low[s],
                        int(pivot_low_index[s]),
                        stop,
                    )
                    control_rows.append(row)
                    funnel["control_in_session_entries"] += 1
                except RuntimeError:
                    pass
        if (
            np.isfinite(pivot_high[s])
            and h[s] > pivot_high[s]
            and c[s] < pivot_high[s]
        ):
            funnel["control_same_bar_sweep_reclaims_all_hours"] += 1
            if _in_frozen_session(times[s]):
                entry = s + 1
                stop = h[s] + 1.5 * PIP
                try:
                    row = _record_common(
                        bars,
                        "SHORT",
                        s,
                        s,
                        s,
                        entry,
                        pivot_high[s],
                        int(pivot_high_index[s]),
                        stop,
                    )
                    control_rows.append(row)
                    funnel["control_in_session_entries"] += 1
                except RuntimeError:
                    pass

        if not np.isfinite(atr[s]) or atr[s] <= 0:
            continue
        depth_long = np.isfinite(pivot_low[s]) and l[s] < pivot_low[s] - 0.25 * atr[s]
        depth_short = (
            np.isfinite(pivot_high[s]) and h[s] > pivot_high[s] + 0.25 * atr[s]
        )
        for direction, is_depth, pivot, pidx in (
            ("LONG", depth_long, pivot_low[s], pivot_low_index[s]),
            ("SHORT", depth_short, pivot_high[s], pivot_high_index[s]),
        ):
            if not is_depth:
                continue
            funnel["challenger_depth_sweeps"] += 1
            if direction == "LONG":
                reclaim = s if c[s] > pivot else (s + 1 if c[s + 1] > pivot else -1)
            else:
                reclaim = s if c[s] < pivot else (s + 1 if c[s + 1] < pivot else -1)
            if reclaim < 0:
                continue
            funnel["challenger_reclaims_same_or_next"] += 1
            if not np.isfinite(adx[reclaim]) or adx[reclaim] > 25.0:
                continue
            funnel["challenger_adx_eligible_all_hours"] += 1
            volume_ok = (
                np.isfinite(vol_mean[s])
                and vol_mean[s] > 0
                and volume[s] >= 1.5 * vol_mean[s]
            )
            if volume_ok:
                funnel["challenger_volume_eligible_all_hours"] += 1
            if not _in_frozen_session(times[reclaim]):
                continue
            funnel["challenger_adx_session_eligible"] += 1
            if not volume_ok:
                continue
            funnel["challenger_volume_eligible"] += 1
            retest = reclaim + 1
            entry = reclaim + 2
            if direction == "LONG":
                retest_ok = (
                    l[retest] <= pivot and c[retest] > pivot and c[retest] > o[retest]
                )
                sweep_extreme = float(np.min(l[s : reclaim + 1]))
                stop = sweep_extreme - 0.30 * atr[s]
            else:
                retest_ok = (
                    h[retest] >= pivot and c[retest] < pivot and c[retest] < o[retest]
                )
                sweep_extreme = float(np.max(h[s : reclaim + 1]))
                stop = sweep_extreme + 0.30 * atr[s]
            if not retest_ok:
                continue
            try:
                row = _record_common(
                    bars,
                    direction,
                    s,
                    reclaim,
                    retest,
                    entry,
                    pivot,
                    int(pidx),
                    stop,
                )
            except RuntimeError:
                continue
            challenger_rows.append(row)
            funnel["challenger_mandatory_retest_entries"] += 1

    control = pd.DataFrame(control_rows)
    challenger = pd.DataFrame(challenger_rows)
    assert_outcome_blind(control)
    assert_outcome_blind(challenger)
    return {
        "funnel": funnel,
        "control_candidates": control,
        "challenger_candidates": challenger,
    }


def assert_outcome_blind(frame: pd.DataFrame) -> None:
    for column in frame.columns:
        lowered = str(column).lower()
        if any(token in lowered for token in FORBIDDEN_OUTCOME_TOKENS):
            raise RuntimeError(f"OUTCOME COLUMN FORBIDDEN: {column}")


def _distribution(series: pd.Series) -> dict:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"count": 0, "min": None, "p25": None, "median": None, "p75": None, "max": None}
    return {
        "count": int(len(values)),
        "min": float(values.min()),
        "p25": float(values.quantile(0.25)),
        "median": float(values.median()),
        "p75": float(values.quantile(0.75)),
        "max": float(values.max()),
    }


def _evaluate_gates(
    challenger: pd.DataFrame, funnel: dict, weeks: float, holdout_bars_loaded: int
) -> tuple[dict, str]:
    count = int(len(challenger))
    tpw = count / weeks if weeks > 0 else 0.0
    risk = _distribution(challenger.get("initial_risk_pips", pd.Series(dtype=float)))
    cost_r = _distribution(challenger.get("cost_r_1_5", pd.Series(dtype=float)))
    pre_volume = int(funnel["challenger_adx_session_eligible"])
    post_volume = int(funnel["challenger_volume_eligible"])
    volume_removed = 1.0 - post_volume / pre_volume if pre_volume else 0.0
    all_volume = int(funnel["challenger_volume_eligible_all_hours"])
    session_share = post_volume / all_volume if all_volume else 0.0
    if count:
        shares = challenger["calendar_year"].value_counts(normalize=True)
        max_year_share = float(shares.max())
    else:
        max_year_share = 1.0
    gates = {
        "holdout_seal": {
            "passed": holdout_bars_loaded == 0,
            "actual": int(holdout_bars_loaded),
            "threshold": 0,
        },
        "minimum_candidates": {
            "passed": count >= 200,
            "actual": count,
            "threshold": 200,
        },
        "minimum_stage0_tpw": {
            "passed": tpw >= 1.0,
            "actual": tpw,
            "threshold": 1.0,
        },
        "median_risk_pips": {
            "passed": risk["median"] is not None and risk["median"] >= 6.75,
            "actual": risk["median"],
            "threshold": 6.75,
        },
        "median_cost_r_1_5": {
            "passed": cost_r["median"] is not None and cost_r["median"] <= 0.20,
            "actual": cost_r["median"],
            "threshold": 0.20,
        },
        "p75_cost_r_1_5": {
            "passed": cost_r["p75"] is not None and cost_r["p75"] <= 0.30,
            "actual": cost_r["p75"],
            "threshold": 0.30,
        },
        "volume_removes_20pct": {
            "passed": volume_removed >= 0.20,
            "actual": volume_removed,
            "threshold": 0.20,
        },
        "volume_not_predominantly_outside_session": {
            "passed": session_share >= 0.50,
            "actual": session_share,
            "threshold": 0.50,
        },
        "max_year_concentration": {
            "passed": max_year_share <= 0.40,
            "actual": max_year_share,
            "threshold": 0.40,
        },
    }
    failures = [name for name, gate in gates.items() if not gate["passed"]]
    if not failures:
        verdict = "SURVIVE_STAGE0_BUILD_PREREG_NEXT"
    elif {"minimum_candidates", "minimum_stage0_tpw"} & set(failures):
        verdict = "PARK_STAGE0_CADENCE_INFEASIBLE_NO_OUTCOME_READ"
    elif {
        "median_risk_pips",
        "median_cost_r_1_5",
        "p75_cost_r_1_5",
    } & set(failures):
        verdict = "KILL_STAGE0_COST_GEOMETRY_NOT_MATERIALLY_NEW"
    else:
        verdict = "PARK_STAGE0_REQUIRED_GATE_FAIL_NO_OUTCOME_READ"
    return gates, verdict


def run_probe(data_path: Path, output_dir: Path) -> dict:
    plan_path = WORKSPACE / PLAN_REL
    if sha256_file(plan_path) != PLAN_SHA256:
        raise RuntimeError("FROZEN PLAN HASH MISMATCH")
    if sha256_file(data_path) != DATA_SHA256:
        raise RuntimeError("DATA HASH MISMATCH")

    m1_all, seal = load_sealed_bars(data_path, HOLDOUT_START)
    m1 = m1_all.loc[pd.to_datetime(m1_all["time_utc"]) >= DESIGN_START].copy()
    m1 = m1[
        [
            "time_utc",
            "time_server",
            "utc_offset_h",
            "open",
            "high",
            "low",
            "close",
            "tick_volume",
        ]
    ]
    bars, quality = resample_complete_m5(m1)
    features = add_stage0_features(bars)
    scan = scan_asrs_events(features)
    control = scan["control_candidates"]
    challenger = scan["challenger_candidates"]
    weeks = elapsed_weeks("2019-01-01", "2022-12-31")
    gates, verdict = _evaluate_gates(
        challenger, scan["funnel"], weeks, int(seal["holdout_bars_loaded"])
    )
    assert_outcome_blind(control)
    assert_outcome_blind(challenger)

    risk = _distribution(
        challenger.get("initial_risk_pips", pd.Series(dtype=float))
    )
    cost_r = {
        tier: _distribution(challenger.get(column, pd.Series(dtype=float)))
        for tier, column in (
            ("0.5_pip_rt", "cost_r_0_5"),
            ("1.5_pip_rt", "cost_r_1_5"),
            ("2.25_pip_rt", "cost_r_2_25"),
            ("3.0_pip_rt", "cost_r_3_0"),
        )
    }
    year_counts = (
        challenger["calendar_year"].value_counts().sort_index().astype(int).to_dict()
        if len(challenger)
        else {}
    )
    artifact = {
        "schema_version": "asrs_stage0_outcome_blind.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "scanner_path": str(Path(__file__).resolve().relative_to(WORKSPACE)).replace("\\", "/"),
        "scanner_sha256": sha256_file(Path(__file__).resolve()),
        "data_path": str(data_path.resolve().relative_to(WORKSPACE)).replace("\\", "/"),
        "data_sha256": DATA_SHA256,
        "seal_receipt": seal,
        "design_start": str(DESIGN_START),
        "design_end_exclusive": str(HOLDOUT_START),
        "elapsed_calendar_weeks": weeks,
        "quality": quality,
        "confirmed_fractal_highs": int(features["pivot_high_flag"].sum()),
        "confirmed_fractal_lows": int(features["pivot_low_flag"].sum()),
        "funnel": scan["funnel"],
        "control_candidates": int(len(control)),
        "challenger_candidates": int(len(challenger)),
        "challenger_candidates_per_week": float(len(challenger) / weeks),
        "challenger_risk_pips": risk,
        "challenger_cost_r": cost_r,
        "challenger_year_counts": {str(k): v for k, v in year_counts.items()},
        "gates": gates,
        "verdict": verdict,
        "cost_status": "UNVERIFIED_PROXY",
        "news_status": "UNMET_OFF_STAGE0",
        "promotion_eligible": False,
        "outcome_blind_attestation": {
            "future_price_read_after_entry": False,
            "pnl_computed": False,
            "trade_outcome_computed": False,
            "mfe_mae_computed": False,
            "profit_factor_computed": False,
            "holdout_bars_loaded": int(seal["holdout_bars_loaded"]),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    challenger_path = output_dir / "stage0_challenger_candidates.csv"
    control_path = output_dir / "stage0_control_candidates.csv"
    json_path = output_dir / "stage0_result.json"
    challenger.to_csv(challenger_path, index=False, lineterminator="\n")
    control.to_csv(control_path, index=False, lineterminator="\n")
    artifact["artifacts"] = {
        "challenger_csv_sha256": sha256_file(challenger_path),
        "control_csv_sha256": sha256_file(control_path),
    }
    payload = (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode("utf-8")
    json_path.write_bytes(payload)

    trials_dir = output_dir.parents[1] / "trials"
    trials_dir.mkdir(parents=True, exist_ok=True)
    trial = {
        "hypothesis_id": HYPOTHESIS_ID,
        "prereg_sha256": PLAN_SHA256,
        "trial_index": 1,
        "trial_universe": 1,
        "stage": "outcome_blind_stage0",
        "verdict": verdict,
        "result_path": str(json_path.relative_to(WORKSPACE)).replace("\\", "/"),
        "result_sha256": sha256_file(json_path),
        "promotion_eligible": False,
    }
    (trials_dir / "trial_log.jsonl").write_text(
        json.dumps(trial, sort_keys=True) + "\n", encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=WORKSPACE / DATA_REL)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            WORKSPACE
            / "03. EA Developer"
            / "EA_ASRS_AdaptiveSweepReclaim"
            / "research"
            / "evidence"
            / "HYP-ASRS-EURUSD-M5-001_STAGE0"
        ),
    )
    args = parser.parse_args()
    artifact = run_probe(args.data, args.output_dir)
    print(json.dumps(
        {
            "verdict": artifact["verdict"],
            "challenger_candidates": artifact["challenger_candidates"],
            "challenger_candidates_per_week": artifact["challenger_candidates_per_week"],
            "median_risk_pips": artifact["challenger_risk_pips"]["median"],
            "median_cost_r_1_5": artifact["challenger_cost_r"]["1.5_pip_rt"]["median"],
        },
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
