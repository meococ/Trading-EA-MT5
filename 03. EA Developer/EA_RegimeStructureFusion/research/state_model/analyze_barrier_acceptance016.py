from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import analyze_state_model012 as feature_lib


TARGET_ATR = (0.75, 1.00, 1.25)
STOP_ATR = 1.00
HORIZON = 8
TEST_YEARS = (2019, 2020, 2021, 2022)
TARGET_CADENCES = (2.5, 3.5, 4.5)
MODEL_FAMILIES = ("LOGISTIC", "HGB_SHALLOW")
RNG_SEED = 5867446


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def make_model(family: str):
    if family == "LOGISTIC":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(C=0.1, max_iter=500, solver="lbfgs", random_state=RNG_SEED),
        )
    return HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=100,
        max_leaf_nodes=7,
        min_samples_leaf=500,
        l2_regularization=10.0,
        random_state=RNG_SEED,
    )


def directional_features(base: pd.DataFrame, direction: int) -> pd.DataFrame:
    out = base.copy()
    out["candidate_direction"] = float(direction)
    alignment_columns = (
        "aird_direction_pressure",
        "vrc_direction",
        "mbb_location",
        "tb_bias",
        "tb_swing_high_distance_atr",
        "tb_swing_low_distance_atr",
        "tb_cell_top_distance_atr",
        "tb_cell_bottom_distance_atr",
        "tb_void_top_distance_atr",
        "tb_void_bottom_distance_atr",
        "tb_structure_level_distance_atr",
        "tb_cell_side",
        "tb_void_side",
        "qqe_primary",
        "qqe_secondary",
        "qqe_primary_slope",
        "qqe_secondary_slope",
        "qqe_spread",
        "qqe_state",
    )
    for column in alignment_columns:
        out[f"aligned_{column}"] = out[column] * direction
    return out.astype(np.float32)


def barrier_path(
    df: pd.DataFrame, target_atr: float, direction: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n = len(df)
    entry = df["open"].shift(-1).to_numpy(dtype=float)
    atr = df["tb_atr"].to_numpy(dtype=float)
    target_price = entry + direction * target_atr * atr
    stop_price = entry - direction * STOP_ATR * atr
    resolved = np.zeros(n, dtype=bool)
    target_first = np.zeros(n, dtype=np.int8)
    gross_r = np.full(n, np.nan, dtype=float)
    exit_step = np.zeros(n, dtype=np.int16)

    for step in range(1, HORIZON + 1):
        high = df["high"].shift(-step).to_numpy(dtype=float)
        low = df["low"].shift(-step).to_numpy(dtype=float)
        if direction == 1:
            target_hit = high >= target_price
            stop_hit = low <= stop_price
        else:
            target_hit = low <= target_price
            stop_hit = high >= stop_price
        active = ~resolved & np.isfinite(high) & np.isfinite(low)
        # Conservative ordering: if both barriers occur inside one M15 bar,
        # record the stop. Only target-only bars are successes.
        stop_now = active & stop_hit
        gross_r[stop_now] = -STOP_ATR
        exit_step[stop_now] = step
        resolved[stop_now] = True
        target_now = active & ~stop_hit & target_hit
        gross_r[target_now] = target_atr
        target_first[target_now] = 1
        exit_step[target_now] = step
        resolved[target_now] = True

    timeout = ~resolved
    horizon_close = df["close"].shift(-HORIZON).to_numpy(dtype=float)
    gross_r[timeout] = direction * (horizon_close[timeout] - entry[timeout]) / atr[timeout]
    exit_step[timeout] = HORIZON
    valid = (
        np.isfinite(entry)
        & np.isfinite(atr)
        & (atr > 0)
        & np.isfinite(gross_r)
    )
    return target_first, gross_r, exit_step, valid


def elapsed_weeks(times: pd.Series) -> float:
    return max((times.iloc[-1] - times.iloc[0]).total_seconds() / (7 * 86400), 1.0)


def select_paired(scores: np.ndarray, valid: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    # scores[:, 0] is long and scores[:, 1] is short. Only one direction may
    # survive at a timestamp, and holding windows cannot overlap.
    selected: list[int] = []
    directions: list[int] = []
    i = 0
    while i < len(scores):
        direction_index = int(scores[i, 1] > scores[i, 0])
        score = scores[i, direction_index]
        if valid[i] and score >= threshold:
            selected.append(i)
            directions.append(1 if direction_index == 0 else -1)
            i += HORIZON
        else:
            i += 1
    return np.asarray(selected, dtype=int), np.asarray(directions, dtype=int)


def choose_threshold(scores: np.ndarray, valid: np.ndarray, weeks: float, target_cadence: float) -> float:
    values = np.max(scores[valid], axis=1)
    if len(values) == 0:
        return math.inf
    lo, hi = float(values.min()), float(values.max()) + 1e-12
    for _ in range(40):
        mid = (lo + hi) / 2.0
        chosen, _ = select_paired(scores, valid, mid)
        if len(chosen) / weeks > target_cadence:
            lo = mid
        else:
            hi = mid
    return hi


def trade_metrics(net: np.ndarray, elapsed_test_weeks: float) -> dict:
    gross_win = float(net[net > 0].sum())
    gross_loss = float(-net[net < 0].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    return {
        "trades": int(len(net)),
        "trades_per_week": float(len(net) / elapsed_test_weeks),
        "net_r": float(net.sum()),
        "mean_r": float(net.mean()) if len(net) else 0.0,
        "win_rate": float((net > 0).mean()) if len(net) else 0.0,
        "profit_factor": float(pf),
        "gross_win_r": gross_win,
        "gross_loss_r": gross_loss,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.census)
    expected_id = "HYP-RSF-USDJPY-M15-STATE-MODEL-015"
    if (df["hypothesis_id"] != expected_id).any():
        raise SystemExit("Parent census identity mismatch")
    times = pd.to_datetime(df["source_bar_time_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    if int(times.dt.year.min()) != 2018 or int(times.dt.year.max()) != 2022:
        raise SystemExit("Discovery boundary violation")
    if df["source_bar_time_server"].duplicated().any() or df.isna().any().any():
        raise SystemExit("Census duplicate/NaN gate failed")

    feature_lib.POINT = 0.001
    base, _ = feature_lib.build_features(df)
    long_x = directional_features(base, 1)
    short_x = directional_features(base, -1)
    common_valid = base.notna().all(axis=1).to_numpy() & (df["tb_atr"].to_numpy() > 0.001)
    entry_times = times.shift(-1)
    exit_times = times.shift(-HORIZON)
    elapsed_minutes = (exit_times - entry_times).dt.total_seconds().to_numpy() / 60.0
    common_valid &= np.isfinite(elapsed_minutes) & (elapsed_minutes >= 0) & (elapsed_minutes <= HORIZON * 15 + 30)
    atr = df["tb_atr"].to_numpy(dtype=float)
    cost_r = (
        df["spread_points"].to_numpy(dtype=float)
        * 0.001
        / atr
        * (1.5 + 0.15 * (1.0 + df["vrc_vol_percentile"].to_numpy(dtype=float) / 100.0))
    )

    fold_rows: list[dict] = []
    path_diagnostics: list[dict] = []
    for target_atr in TARGET_ATR:
        long_y, long_gross, long_exit_step, long_valid = barrier_path(df, target_atr, 1)
        short_y, short_gross, short_exit_step, short_valid = barrier_path(df, target_atr, -1)
        valid = common_valid & long_valid & short_valid & np.isfinite(cost_r)
        path_diagnostics.append(
            {
                "target_atr": target_atr,
                "valid_decisions": int(valid.sum()),
                "long_target_first_rate": float(long_y[valid].mean()),
                "short_target_first_rate": float(short_y[valid].mean()),
                "long_mean_exit_step": float(long_exit_step[valid].mean()),
                "short_mean_exit_step": float(short_exit_step[valid].mean()),
            }
        )

        for family in MODEL_FAMILIES:
            for test_year in TEST_YEARS:
                start = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
                end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
                train_mask = (times < start) & (exit_times < start)
                test_mask = (times >= start) & (times < end)
                train_idx = np.flatnonzero(train_mask.to_numpy() & valid)
                test_idx = np.flatnonzero(test_mask.to_numpy() & valid)
                x_train = pd.concat((long_x.iloc[train_idx], short_x.iloc[train_idx]), ignore_index=True)
                y_train = np.concatenate((long_y[train_idx], short_y[train_idx]))
                model = make_model(family)
                model.fit(x_train, y_train)
                train_scores = np.column_stack(
                    (
                        model.predict_proba(long_x.iloc[train_idx])[:, 1],
                        model.predict_proba(short_x.iloc[train_idx])[:, 1],
                    )
                )
                test_scores = np.column_stack(
                    (
                        model.predict_proba(long_x.iloc[test_idx])[:, 1],
                        model.predict_proba(short_x.iloc[test_idx])[:, 1],
                    )
                )
                train_weeks = elapsed_weeks(times.iloc[train_idx].reset_index(drop=True))
                test_weeks = elapsed_weeks(times.iloc[test_idx].reset_index(drop=True))
                for target_cadence in TARGET_CADENCES:
                    threshold = choose_threshold(
                        train_scores, np.ones(len(train_idx), dtype=bool), train_weeks, target_cadence
                    )
                    chosen_local, directions = select_paired(
                        test_scores, np.ones(len(test_idx), dtype=bool), threshold
                    )
                    chosen = test_idx[chosen_local]
                    use_long = directions == 1
                    gross = np.where(use_long, long_gross[chosen], short_gross[chosen])
                    net = gross - cost_r[chosen]
                    metrics = trade_metrics(net, test_weeks)
                    fold_rows.append(
                        {
                            "model_family": family,
                            "target_atr": target_atr,
                            "stop_atr": STOP_ATR,
                            "horizon_bars": HORIZON,
                            "test_year": test_year,
                            "target_cadence": target_cadence,
                            "threshold": float(threshold),
                            "long_trades": int(use_long.sum()),
                            "short_trades": int((~use_long).sum()),
                            **metrics,
                        }
                    )

    folds = pd.DataFrame(fold_rows)
    folds.to_csv(args.out_dir / "barrier_walk_forward_folds.csv", index=False)
    summaries: list[dict] = []
    for family in MODEL_FAMILIES:
        for target_atr in TARGET_ATR:
            subset = folds[(folds.model_family == family) & (folds.target_atr == target_atr)]
            primary = subset[subset.target_cadence == 3.5]
            cadence_valid = primary[(primary.trades_per_week >= 2.0) & (primary.trades_per_week <= 5.0)]
            pooled_loss = float(primary.gross_loss_r.sum())
            pooled_pf = float(primary.gross_win_r.sum() / pooled_loss) if pooled_loss > 0 else 0.0
            positive = primary.gross_win_r.clip(lower=0)
            max_year_share = float(positive.max() / positive.sum()) if positive.sum() > 0 else 1.0
            adjacent_pf: dict[str, float] = {}
            for cadence in (2.5, 4.5):
                adjacent = subset[subset.target_cadence == cadence]
                loss = float(adjacent.gross_loss_r.sum())
                adjacent_pf[str(cadence)] = float(adjacent.gross_win_r.sum() / loss) if loss > 0 else 0.0
            gates = {
                "cadence_valid_folds_at_least_3": len(cadence_valid) >= 3,
                "all_cadence_valid_folds_positive_pf": bool(
                    len(cadence_valid) >= 3
                    and (cadence_valid.net_r > 0).all()
                    and (cadence_valid.profit_factor > 1.0).all()
                ),
                "median_year_pf_ge_1_20": bool(primary.profit_factor.median() >= 1.20),
                "pooled_pf_ge_1_20": bool(pooled_pf >= 1.20),
                "max_year_positive_gross_share_le_0_40": bool(max_year_share <= 0.40),
                "adjacent_thresholds_stable": bool(
                    adjacent_pf["2.5"] > 1.05 and adjacent_pf["4.5"] > 1.05
                ),
            }
            summaries.append(
                {
                    "model_family": family,
                    "target_atr": target_atr,
                    "stop_atr": STOP_ATR,
                    "horizon_bars": HORIZON,
                    "primary_trades": int(primary.trades.sum()),
                    "cadence_valid_folds": int(len(cadence_valid)),
                    "median_year_pf": float(primary.profit_factor.median()),
                    "pooled_pf": pooled_pf,
                    "pooled_net_r": float(primary.net_r.sum()),
                    "max_year_positive_gross_share": max_year_share,
                    "adjacent_pooled_pf": adjacent_pf,
                    "gates": gates,
                    "survivor": all(gates.values()),
                }
            )

    ranked = sorted(summaries, key=lambda row: (row["survivor"], row["pooled_pf"], row["pooled_net_r"]), reverse=True)
    result = {
        "schema_version": "rsf_barrier_acceptance016_discovery.v1",
        "hypothesis_id": "HYP-RSF-USDJPY-M15-BARRIER-ACCEPTANCE-016",
        "parent_census_sha256": sha256_file(args.census),
        "models_preregistered_this_id": 6,
        "model_fits_this_id": 24,
        "threshold_fold_evaluations_this_id": int(len(folds)),
        "target_atr_cells": list(TARGET_ATR),
        "stop_atr": STOP_ATR,
        "horizon_bars": HORIZON,
        "same_bar_priority": "STOP_FIRST",
        "cost_model": "observed_spread*0.001*(1.5+0.15*(1+VRC_vol_percentile/100))/TB_ATR",
        "path_diagnostics": path_diagnostics,
        "summaries": ranked,
        "survivor_count": int(sum(row["survivor"] for row in ranked)),
        "validation_2023_plus_opened": False,
        "verdict": "DISCOVERY_SURVIVOR_FREEZE_REQUIRED" if any(row["survivor"] for row in ranked) else "KILL_NO_STABLE_BARRIER_EDGE",
    }
    (args.out_dir / "barrier_acceptance016_results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verdict": result["verdict"], "survivors": result["survivor_count"], "best": ranked[0]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
