from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_barrier_acceptance016 as barrier
import analyze_state_model012 as feature_lib


TARGET_CADENCES = (2.5, 3.5, 4.5)
TEST_YEARS = (2019, 2020, 2021, 2022)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def select_events(
    scores: np.ndarray, census_indices: np.ndarray, threshold: float
) -> np.ndarray:
    selected: list[int] = []
    next_free_index = -1
    for local_index, census_index in enumerate(census_indices):
        if census_index >= next_free_index and scores[local_index] >= threshold:
            selected.append(local_index)
            next_free_index = int(census_index) + barrier.HORIZON
    return np.asarray(selected, dtype=int)


def choose_threshold(
    scores: np.ndarray,
    census_indices: np.ndarray,
    elapsed_weeks: float,
    target_cadence: float,
) -> float:
    if len(scores) == 0:
        return math.inf
    lo, hi = float(scores.min()), float(scores.max()) + 1e-12
    for _ in range(40):
        mid = (lo + hi) / 2.0
        cadence = len(select_events(scores, census_indices, mid)) / elapsed_weeks
        if cadence > target_cadence:
            lo = mid
        else:
            hi = mid
    return hi


def metrics(net: np.ndarray, elapsed_weeks: float) -> dict:
    wins = float(net[net > 0].sum())
    losses = float(-net[net < 0].sum())
    pf = wins / losses if losses > 0 else (999.0 if wins > 0 else 0.0)
    return {
        "trades": int(len(net)),
        "trades_per_week": float(len(net) / elapsed_weeks),
        "net_r": float(net.sum()),
        "mean_r": float(net.mean()) if len(net) else 0.0,
        "win_rate": float((net > 0).mean()) if len(net) else 0.0,
        "profit_factor": float(pf),
        "gross_win_r": wins,
        "gross_loss_r": losses,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True, type=Path)
    ap.add_argument("--events", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.census)
    events = pd.read_csv(args.events)
    if (df["hypothesis_id"] != "HYP-RSF-USDJPY-M15-STATE-MODEL-015").any():
        raise SystemExit("Parent census identity mismatch")
    if events["source_bar_time_utc"].duplicated().any():
        raise SystemExit("Event clock is not unique")
    census_indices = events["census_index"].to_numpy(dtype=int)
    if not np.array_equal(census_indices, np.sort(census_indices)):
        raise SystemExit("Event clock is not chronological")
    direction = events["direction"].to_numpy(dtype=int)
    if not np.isin(direction, (-1, 1)).all():
        raise SystemExit("Invalid event direction")

    times = pd.to_datetime(df["source_bar_time_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    event_times = times.iloc[census_indices].reset_index(drop=True)
    feature_lib.POINT = 0.001
    base, _ = feature_lib.build_features(df)
    long_x = barrier.directional_features(base, 1).iloc[census_indices].reset_index(drop=True)
    short_x = barrier.directional_features(base, -1).iloc[census_indices].reset_index(drop=True)
    event_x = long_x.copy()
    short_mask = direction == -1
    event_x.loc[short_mask, :] = short_x.loc[short_mask, :].to_numpy()
    event_x["event_s1_rise"] = events["s1_rise"].to_numpy(dtype=np.float32)
    event_x["event_s2_rise"] = events["s2_rise"].to_numpy(dtype=np.float32)
    event_x["event_s3_rise"] = events["s3_rise"].to_numpy(dtype=np.float32)

    atr = df["tb_atr"].to_numpy(dtype=float)
    cost_all = (
        df["spread_points"].to_numpy(dtype=float)
        * 0.001
        / atr
        * (1.5 + 0.15 * (1.0 + df["vrc_vol_percentile"].to_numpy(dtype=float) / 100.0))
    )
    exit_times = times.shift(-barrier.HORIZON)
    elapsed_minutes = (exit_times - times.shift(-1)).dt.total_seconds().to_numpy() / 60.0
    common_valid = (
        event_x.notna().all(axis=1).to_numpy()
        & (atr[census_indices] > 0.001)
        & np.isfinite(cost_all[census_indices])
        & np.isfinite(elapsed_minutes[census_indices])
        & (elapsed_minutes[census_indices] >= 0)
        & (elapsed_minutes[census_indices] <= barrier.HORIZON * 15 + 30)
    )

    fold_rows: list[dict] = []
    path_diagnostics: list[dict] = []
    for target_atr in barrier.TARGET_ATR:
        long_y, long_gross, _, long_valid = barrier.barrier_path(df, target_atr, 1)
        short_y, short_gross, _, short_valid = barrier.barrier_path(df, target_atr, -1)
        y = np.where(direction == 1, long_y[census_indices], short_y[census_indices])
        gross = np.where(direction == 1, long_gross[census_indices], short_gross[census_indices])
        valid = common_valid & long_valid[census_indices] & short_valid[census_indices] & np.isfinite(gross)
        path_diagnostics.append(
            {
                "target_atr": target_atr,
                "valid_events": int(valid.sum()),
                "target_first_rate": float(y[valid].mean()),
                "long_target_first_rate": float(y[valid & (direction == 1)].mean()),
                "short_target_first_rate": float(y[valid & (direction == -1)].mean()),
            }
        )

        for family in barrier.MODEL_FAMILIES:
            for test_year in TEST_YEARS:
                start = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
                end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
                event_exit_times = exit_times.iloc[census_indices].reset_index(drop=True)
                train_mask = (event_times < start) & (event_exit_times < start)
                test_mask = (event_times >= start) & (event_times < end)
                train_local = np.flatnonzero(train_mask.to_numpy() & valid)
                test_local = np.flatnonzero(test_mask.to_numpy() & valid)
                model = barrier.make_model(family)
                model.fit(event_x.iloc[train_local], y[train_local])
                train_score = model.predict_proba(event_x.iloc[train_local])[:, 1]
                test_score = model.predict_proba(event_x.iloc[test_local])[:, 1]
                train_weeks = barrier.elapsed_weeks(event_times.iloc[train_local].reset_index(drop=True))
                test_weeks = barrier.elapsed_weeks(event_times.iloc[test_local].reset_index(drop=True))
                train_indices = census_indices[train_local]
                test_indices = census_indices[test_local]
                for target_cadence in TARGET_CADENCES:
                    threshold = choose_threshold(train_score, train_indices, train_weeks, target_cadence)
                    chosen_in_test = select_events(test_score, test_indices, threshold)
                    chosen_local = test_local[chosen_in_test]
                    net = gross[chosen_local] - cost_all[census_indices[chosen_local]]
                    chosen_events = events.iloc[chosen_local]
                    fold_rows.append(
                        {
                            "model_family": family,
                            "target_atr": target_atr,
                            "stop_atr": barrier.STOP_ATR,
                            "horizon_bars": barrier.HORIZON,
                            "test_year": test_year,
                            "target_cadence": target_cadence,
                            "threshold": float(threshold),
                            "long_trades": int((direction[chosen_local] == 1).sum()),
                            "short_trades": int((direction[chosen_local] == -1).sum()),
                            "s1_trades": int(chosen_events.s1_rise.sum()),
                            "s2_trades": int(chosen_events.s2_rise.sum()),
                            "s3_trades": int(chosen_events.s3_rise.sum()),
                            **metrics(net, test_weeks),
                        }
                    )

    folds = pd.DataFrame(fold_rows)
    folds.to_csv(args.out_dir / "mbb_event_acceptance_folds.csv", index=False)
    summaries: list[dict] = []
    for family in barrier.MODEL_FAMILIES:
        for target_atr in barrier.TARGET_ATR:
            subset = folds[(folds.model_family == family) & (folds.target_atr == target_atr)]
            primary = subset[subset.target_cadence == 3.5]
            cadence_valid = primary[(primary.trades_per_week >= 2.0) & (primary.trades_per_week <= 5.0)]
            loss = float(primary.gross_loss_r.sum())
            pooled_pf = float(primary.gross_win_r.sum() / loss) if loss > 0 else 0.0
            positive = primary.gross_win_r.clip(lower=0)
            max_year_share = float(positive.max() / positive.sum()) if positive.sum() > 0 else 1.0
            adjacent_pf = {}
            for cadence in (2.5, 4.5):
                adjacent = subset[subset.target_cadence == cadence]
                adj_loss = float(adjacent.gross_loss_r.sum())
                adjacent_pf[str(cadence)] = float(adjacent.gross_win_r.sum() / adj_loss) if adj_loss > 0 else 0.0
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
                "adjacent_thresholds_stable": bool(adjacent_pf["2.5"] > 1.05 and adjacent_pf["4.5"] > 1.05),
            }
            summaries.append(
                {
                    "model_family": family,
                    "target_atr": target_atr,
                    "stop_atr": barrier.STOP_ATR,
                    "horizon_bars": barrier.HORIZON,
                    "primary_trades": int(primary.trades.sum()),
                    "cadence_valid_folds": int(len(cadence_valid)),
                    "median_year_pf": float(primary.profit_factor.median()),
                    "pooled_pf": pooled_pf,
                    "pooled_net_r": float(primary.net_r.sum()),
                    "selected_event_types": {
                        "s1": int(primary.s1_trades.sum()),
                        "s2": int(primary.s2_trades.sum()),
                        "s3": int(primary.s3_trades.sum()),
                    },
                    "max_year_positive_gross_share": max_year_share,
                    "adjacent_pooled_pf": adjacent_pf,
                    "gates": gates,
                    "survivor": all(gates.values()),
                }
            )

    ranked = sorted(summaries, key=lambda row: (row["survivor"], row["pooled_pf"], row["pooled_net_r"]), reverse=True)
    result = {
        "schema_version": "rsf_mbb_event_acceptance017_discovery.v1",
        "hypothesis_id": "HYP-RSF-USDJPY-M15-MBB-EVENT-ACCEPTANCE-017",
        "parent_census_sha256": sha256_file(args.census),
        "event_clock_sha256": sha256_file(args.events),
        "models_preregistered_this_id": 6,
        "model_fits_this_id": 24,
        "threshold_fold_evaluations_this_id": int(len(folds)),
        "path_diagnostics": path_diagnostics,
        "summaries": ranked,
        "survivor_count": int(sum(row["survivor"] for row in ranked)),
        "validation_2023_plus_opened": False,
        "verdict": "DISCOVERY_SURVIVOR_FREEZE_REQUIRED" if any(row["survivor"] for row in ranked) else "KILL_NO_STABLE_MBB_EVENT_EDGE",
    }
    (args.out_dir / "mbb_event_acceptance017_results.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verdict": result["verdict"], "survivors": result["survivor_count"], "best": ranked[0]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
