from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_state_model012 as base


HYPOTHESIS_ID = "HYP-RSF-EURUSD-M5-STATE-TRANSITION-013"


def changed(series: pd.Series) -> pd.Series:
    out = series.ne(series.shift(1))
    out.iloc[0] = False
    return out


def zero_cross(series: pd.Series) -> pd.Series:
    prev = series.shift(1)
    out = ((series > 0) & (prev <= 0)) | ((series < 0) & (prev >= 0))
    return out.fillna(False)


def bars_since(mask: pd.Series, cap: int = 48) -> np.ndarray:
    idx = np.arange(len(mask))
    last = np.maximum.accumulate(np.where(mask.to_numpy(), idx, -10_000_000))
    return np.minimum(idx - last, cap + 1).astype(float)


def build_transition_features(df: pd.DataFrame):
    x, families = base.build_features(df)
    events = {
        "AIRD": changed(df["aird_regime"]),
        "VRC": changed(df["vrc_regime"]),
        "MBB": df[["mbb_release", "s1_long", "s1_short", "s2_long", "s2_short", "s3_long", "s3_short"]].astype(bool).any(axis=1),
        "TB": (
            df[["tb_sweep_high", "tb_sweep_low", "tb_structure_up", "tb_structure_down", "tb_displacement_up", "tb_displacement_down"]].astype(bool).any(axis=1)
            | changed(df["tb_bias"]) | changed(df["tb_cell_side"]) | changed(df["tb_void_side"])
        ),
        "QQE": changed(df["qqe_state"]) | zero_cross(df["qqe_primary"]) | zero_cross(df["qqe_secondary"]),
    }
    event_union = pd.concat(events, axis=1).any(axis=1)

    delta_columns = {
        "AIRD": ["aird_confidence", "p_bull", "p_bear", "p_range", "p_highvol", "aird_direction_pressure"],
        "VRC": ["vrc_direction", "vrc_vol_percentile"],
        "MBB": ["mbb_location", "mbb_width_atr", "mbb_squeeze"],
        "TB": ["tb_bias", "tb_atr_price_pct", "tb_swing_high_distance_atr", "tb_swing_low_distance_atr", "tb_structure_level_distance_atr"],
        "QQE": ["qqe_primary", "qqe_secondary", "qqe_primary_slope", "qqe_secondary_slope", "qqe_spread"],
    }
    for family, cols in delta_columns.items():
        for col in cols:
            for lag in (1, 3):
                name = f"{col}_delta_{lag}"
                x[name] = x[col] - x[col].shift(lag)
                families[family].append(name)
        event_name = f"{family.lower()}_event"
        age_name = f"{family.lower()}_event_age48"
        x[event_name] = events[family].astype(float)
        x[age_name] = bars_since(events[family]) / 48.0
        families[family].extend([event_name, age_name])
    return x.replace([np.inf, -np.inf], np.nan), families, events, event_union


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.census)
    times = pd.to_datetime(df["source_bar_time_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    if int(times.dt.year.min()) != 2018 or int(times.dt.year.max()) != 2022:
        raise SystemExit("Discovery boundary violation")
    x, families, events, event_union = build_transition_features(df)
    common_valid = x.notna().all(axis=1).to_numpy() & (df["tb_atr"].to_numpy() > base.POINT) & event_union.to_numpy()
    event_counts = {name: int(mask.sum()) for name, mask in events.items()}
    event_counts["UNION"] = int(event_union.sum())

    fold_rows = []
    diagnostics_cache = {}
    for horizon in base.HORIZONS:
        entry = df["open"].shift(-1).to_numpy()
        exit_price = df["close"].shift(-horizon).to_numpy()
        atr = df["tb_atr"].to_numpy()
        gross_target = (exit_price - entry) / atr
        dynamic_cost_points = df["spread_points"].to_numpy() * (1.5 + 0.15 * (1.0 + df["vrc_vol_percentile"].to_numpy() / 100.0))
        cost_r = dynamic_cost_points * base.POINT / atr
        exit_times = times.shift(-horizon)
        elapsed_minutes = (exit_times - times.shift(-1)).dt.total_seconds().to_numpy() / 60.0
        label_valid = np.isfinite(gross_target) & np.isfinite(cost_r) & (elapsed_minutes >= 0) & (elapsed_minutes <= horizon * 5 + 10)

        for family in base.MODEL_FAMILIES:
            for test_year in base.TEST_YEARS:
                start = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
                end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
                train_mask = (times < start) & (exit_times < start)
                test_mask = (times >= start) & (times < end)
                train_idx = np.flatnonzero(train_mask.to_numpy() & common_valid & label_valid)
                test_idx = np.flatnonzero(test_mask.to_numpy() & common_valid & label_valid)
                model = base.make_model(family)
                model.fit(x.iloc[train_idx], gross_target[train_idx])
                train_score = model.predict(x.iloc[train_idx])
                test_score = model.predict(x.iloc[test_idx])
                train_valid = np.ones(len(train_idx), dtype=bool)
                test_valid = np.ones(len(test_idx), dtype=bool)
                train_weeks = base.elapsed_weeks(times.iloc[train_idx].reset_index(drop=True))
                for target_cadence in base.TARGET_CADENCES:
                    threshold = base.choose_threshold(train_score, train_valid, horizon, train_weeks, target_cadence)
                    chosen_local = base.select_nonoverlapping(test_score, test_valid, threshold, horizon)
                    chosen = test_idx[chosen_local]
                    direction = np.sign(test_score[chosen_local])
                    net = direction * gross_target[chosen] - cost_r[chosen]
                    metrics = base.trade_metrics(net, times.iloc[test_idx].reset_index(drop=True))
                    fold_rows.append({
                        "model_family": family, "horizon_bars": horizon, "test_year": test_year,
                        "target_cadence": target_cadence, "threshold": float(threshold), **metrics,
                    })
                if test_year == 2022:
                    diagnostics_cache[(family, horizon)] = (model, x.iloc[test_idx].copy(), gross_target[test_idx].copy())

    folds = pd.DataFrame(fold_rows)
    folds.to_csv(args.out_dir / "walk_forward_transition_folds.csv", index=False)
    summaries = []
    for family in base.MODEL_FAMILIES:
        for horizon in base.HORIZONS:
            subset = folds[(folds.model_family == family) & (folds.horizon_bars == horizon)]
            primary = subset[subset.target_cadence == 3.5]
            cadence_valid = primary[(primary.trades_per_week >= 2.0) & (primary.trades_per_week <= 5.0)]
            win = float(primary.gross_win_r.sum())
            loss = float(primary.gross_loss_r.sum())
            pooled_pf = win / loss if loss > 0 else 0.0
            max_year_share = float(primary.gross_win_r.max() / win) if win > 0 else 1.0
            adjacent = {}
            for cadence in (2.5, 4.5):
                adj = subset[subset.target_cadence == cadence]
                adj_loss = float(adj.gross_loss_r.sum())
                adjacent[str(cadence)] = float(adj.gross_win_r.sum() / adj_loss) if adj_loss > 0 else 0.0
            gates = {
                "cadence_valid_folds_at_least_3": len(cadence_valid) >= 3,
                "all_cadence_valid_folds_positive_pf": bool(len(cadence_valid) >= 3 and (cadence_valid.net_r > 0).all() and (cadence_valid.profit_factor > 1.0).all()),
                "median_year_pf_ge_1_20": bool(primary.profit_factor.median() >= 1.20),
                "pooled_pf_ge_1_20": pooled_pf >= 1.20,
                "max_year_positive_gross_share_le_0_40": max_year_share <= 0.40,
                "adjacent_thresholds_stable": adjacent["2.5"] > 1.05 and adjacent["4.5"] > 1.05,
            }
            summaries.append({
                "model_family": family, "horizon_bars": horizon, "primary_trades": int(primary.trades.sum()),
                "cadence_valid_folds": int(len(cadence_valid)), "median_year_pf": float(primary.profit_factor.median()),
                "pooled_pf": pooled_pf, "pooled_net_r": float(primary.net_r.sum()),
                "max_year_positive_gross_share": max_year_share, "adjacent_pooled_pf": adjacent,
                "gates": gates, "survivor": all(gates.values()),
            })

    ranked = sorted(summaries, key=lambda r: (r["survivor"], r["pooled_pf"], r["pooled_net_r"]), reverse=True)
    best = ranked[0]
    model, xdiag, ydiag = diagnostics_cache[(best["model_family"], best["horizon_bars"])]
    diagnostics = base.family_permutation_diagnostic(model, xdiag, ydiag, families)
    pd.DataFrame(diagnostics).sort_values("mse_increase_mean", ascending=False).to_csv(args.out_dir / "transition_feature_family_diagnostics.csv", index=False)

    result = {
        "schema_version": "rsf_state_transition013_discovery.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "parent_census_sha256": base.sha256_file(args.census),
        "event_counts": event_counts,
        "models_preregistered_this_id": 6,
        "model_fits_this_id": 24,
        "threshold_fold_evaluations_this_id": int(len(folds)),
        "cumulative_model_cells": 12,
        "cumulative_model_fits": 48,
        "cumulative_threshold_fold_evaluations": 144,
        "cost_model": "observed_spread*(1.5+0.15*(1+VRC_vol_percentile/100))",
        "summaries": ranked,
        "survivor_count": int(sum(r["survivor"] for r in ranked)),
        "best_diagnostic_cell": best,
        "feature_family_diagnostics_2022": diagnostics,
        "validation_2023_plus_opened": False,
        "verdict": "DISCOVERY_SURVIVOR_FREEZE_REQUIRED" if any(r["survivor"] for r in ranked) else "KILL_NO_STABLE_TRANSITION_EDGE",
    }
    (args.out_dir / "state_transition013_results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "survivors": result["survivor_count"], "event_counts": event_counts, "best": best}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

