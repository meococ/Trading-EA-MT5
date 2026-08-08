from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


HORIZONS = (3, 6, 12)
MODEL_FAMILIES = ("RIDGE", "HGB_SHALLOW")
TARGET_CADENCES = (2.5, 3.5, 4.5)
TEST_YEARS = (2019, 2020, 2021, 2022)
POINT = 0.00001
RNG_SEED = 5867442


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def safe_distance(level: pd.Series, close: pd.Series, atr: pd.Series) -> tuple[pd.Series, pd.Series]:
    valid = level.abs() > POINT
    value = ((level - close) / atr).where(valid, 0.0)
    return value, valid.astype(float)


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    close = df["close"]
    atr = df["tb_atr"].replace(0.0, np.nan)
    halfwidth = ((df["mbb_upper"] - df["mbb_lower"]) / 2.0).replace(0.0, np.nan)
    utc = pd.to_datetime(df["source_bar_time_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    hour = utc.dt.hour + utc.dt.minute / 60.0
    dow = utc.dt.dayofweek

    x = pd.DataFrame(index=df.index)
    families: dict[str, list[str]] = {k: [] for k in ("AIRD", "VRC", "MBB", "TB", "QQE", "TIME")}

    def add(family: str, name: str, values) -> None:
        x[name] = values
        families[family].append(name)

    add("AIRD", "aird_confidence", df["aird_confidence"])
    for name in ("p_bull", "p_bear", "p_range", "p_highvol"):
        add("AIRD", name, df[name] / 100.0)
    add("AIRD", "aird_direction_pressure", (df["p_bull"] - df["p_bear"]) / 100.0)
    for value in range(4):
        add("AIRD", f"aird_regime_{value}", (df["aird_regime"] == value).astype(float))

    add("VRC", "vrc_direction", df["vrc_direction"])
    add("VRC", "vrc_vol_percentile", df["vrc_vol_percentile"] / 100.0)
    add("VRC", "vrc_high_vol", df["vrc_high_vol"])
    add("VRC", "vrc_low_vol", df["vrc_low_vol"])
    add("VRC", "vrc_changed", (df["vrc_regime"] != df["vrc_previous_regime"]).astype(float))
    for value in (-1, 0, 1, 2, 3, 4, 5, 6, 7):
        add("VRC", f"vrc_regime_{value}", (df["vrc_regime"] == value).astype(float))

    add("MBB", "mbb_location", (close - df["mbb_basis"]) / halfwidth)
    add("MBB", "mbb_width_atr", (2.0 * halfwidth) / atr)
    add("MBB", "mbb_squeeze", df["mbb_squeeze"] / 100.0)
    add("MBB", "mbb_release", df["mbb_release"])
    for name in ("s1_long", "s1_short", "s2_long", "s2_short", "s3_long", "s3_short"):
        add("MBB", name, df[name])

    add("TB", "tb_bias", df["tb_bias"])
    add("TB", "tb_atr_price_pct", atr / close)
    for raw_name in ("tb_swing_high", "tb_swing_low", "tb_cell_top", "tb_cell_bottom", "tb_void_top", "tb_void_bottom", "tb_structure_level"):
        distance, valid = safe_distance(df[raw_name], close, atr)
        add("TB", f"{raw_name}_distance_atr", distance)
        add("TB", f"{raw_name}_valid", valid)
    for name in ("tb_cell_side", "tb_void_side", "tb_sweep_high", "tb_sweep_low", "tb_structure_up", "tb_structure_down", "tb_displacement_up", "tb_displacement_down"):
        add("TB", name, df[name])

    add("QQE", "qqe_primary", df["qqe_primary"] / 25.0)
    add("QQE", "qqe_secondary", df["qqe_secondary"] / 25.0)
    add("QQE", "qqe_primary_slope", (df["qqe_primary"] - df["qqe_primary_prev"]) / 25.0)
    add("QQE", "qqe_secondary_slope", (df["qqe_secondary"] - df["qqe_secondary_prev"]) / 25.0)
    add("QQE", "qqe_spread", (df["qqe_primary"] - df["qqe_secondary"]) / 25.0)
    add("QQE", "qqe_state", df["qqe_state"])

    add("TIME", "hour_sin", np.sin(2.0 * np.pi * hour / 24.0))
    add("TIME", "hour_cos", np.cos(2.0 * np.pi * hour / 24.0))
    add("TIME", "dow_sin", np.sin(2.0 * np.pi * dow / 5.0))
    add("TIME", "dow_cos", np.cos(2.0 * np.pi * dow / 5.0))

    return x.replace([np.inf, -np.inf], np.nan), families


def make_model(family: str):
    if family == "RIDGE":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    return HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_iter=100,
        max_leaf_nodes=7,
        min_samples_leaf=500,
        l2_regularization=10.0,
        random_state=RNG_SEED,
    )


def elapsed_weeks(times: pd.Series) -> float:
    return max((times.iloc[-1] - times.iloc[0]).total_seconds() / (7 * 86400), 1.0)


def select_nonoverlapping(scores: np.ndarray, valid: np.ndarray, threshold: float, horizon: int) -> np.ndarray:
    selected: list[int] = []
    i = 0
    n = len(scores)
    while i < n:
        if valid[i] and abs(scores[i]) >= threshold:
            selected.append(i)
            # The position exits on the close of i+horizon. A signal formed on
            # that same close may enter on the following bar without overlap.
            i += horizon
        else:
            i += 1
    return np.asarray(selected, dtype=int)


def choose_threshold(scores: np.ndarray, valid: np.ndarray, horizon: int, weeks: float, target_cadence: float) -> float:
    values = np.abs(scores[valid])
    if len(values) == 0:
        return math.inf
    lo, hi = float(np.min(values)), float(np.max(values)) + 1e-12
    for _ in range(40):
        mid = (lo + hi) / 2.0
        n = len(select_nonoverlapping(scores, valid, mid, horizon))
        cadence = n / weeks
        if cadence > target_cadence:
            lo = mid
        else:
            hi = mid
    return hi


def trade_metrics(net: np.ndarray, times: pd.Series) -> dict:
    gross_win = float(net[net > 0].sum())
    gross_loss = float(-net[net < 0].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    return {
        "trades": int(len(net)),
        "trades_per_week": float(len(net) / elapsed_weeks(times)),
        "net_r": float(net.sum()),
        "mean_r": float(net.mean()) if len(net) else 0.0,
        "win_rate": float((net > 0).mean()) if len(net) else 0.0,
        "profit_factor": float(pf),
        "gross_win_r": gross_win,
        "gross_loss_r": gross_loss,
    }


def family_permutation_diagnostic(model, x: pd.DataFrame, y: np.ndarray, families: dict[str, list[str]]) -> list[dict]:
    rng = np.random.default_rng(RNG_SEED)
    if len(x) > 20000:
        take = np.sort(rng.choice(len(x), 20000, replace=False))
        x = x.iloc[take].copy()
        y = y[take]
    base = float(np.mean((model.predict(x) - y) ** 2))
    rows = []
    for family, cols in families.items():
        deltas = []
        for _ in range(5):
            xp = x.copy()
            order = rng.permutation(len(xp))
            xp.loc[:, cols] = xp[cols].to_numpy()[order]
            deltas.append(float(np.mean((model.predict(xp) - y) ** 2) - base))
        rows.append({"family": family, "mse_increase_mean": float(np.mean(deltas)), "mse_increase_std": float(np.std(deltas)), "base_mse": base})
    return rows


def main() -> int:
    global POINT
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--hypothesis-id", default="HYP-RSF-EURUSD-M5-STATE-MODEL-012")
    ap.add_argument("--point", type=float, default=0.00001)
    ap.add_argument("--results-name", default="state_model012_results.json")
    ap.add_argument("--horizons", default="3,6,12")
    ap.add_argument("--bar-minutes", type=int, default=5)
    args = ap.parse_args()
    if not math.isfinite(args.point) or args.point <= 0:
        raise SystemExit("Point geometry must be finite and positive")
    POINT = args.point
    horizons = tuple(int(value) for value in args.horizons.split(","))
    if not horizons or len(set(horizons)) != len(horizons) or any(value < 1 for value in horizons):
        raise SystemExit("Horizons must be unique positive integers")
    if args.bar_minutes < 1:
        raise SystemExit("Bar minutes must be positive")
    args.out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.census)
    times = pd.to_datetime(df["source_bar_time_utc"], format="%Y.%m.%d %H:%M:%S", utc=True)
    years = times.dt.year
    if int(years.min()) != 2018 or int(years.max()) != 2022:
        raise SystemExit("Discovery boundary violation")
    if df["source_bar_time_server"].duplicated().any() or df.isna().any().any():
        raise SystemExit("Census duplicate/NaN gate failed")
    if (df["hypothesis_id"] != args.hypothesis_id).any():
        raise SystemExit("Hypothesis identity mismatch")

    x, families = build_features(df)
    common_valid = x.notna().all(axis=1).to_numpy() & (df["tb_atr"].to_numpy() > POINT)
    cell_rows: list[dict] = []
    fold_predictions: dict[tuple[str, int, int], tuple[object, pd.DataFrame, np.ndarray]] = {}

    for horizon in horizons:
        entry = df["open"].shift(-1).to_numpy()
        exit_price = df["close"].shift(-horizon).to_numpy()
        atr = df["tb_atr"].to_numpy()
        gross_target = (exit_price - entry) / atr
        dynamic_cost_points = df["spread_points"].to_numpy() * (1.5 + 0.15 * (1.0 + df["vrc_vol_percentile"].to_numpy() / 100.0))
        cost_r = dynamic_cost_points * POINT / atr
        exit_times = times.shift(-horizon)
        elapsed_minutes = (exit_times - times.shift(-1)).dt.total_seconds().to_numpy() / 60.0
        label_valid = np.isfinite(gross_target) & np.isfinite(cost_r) & (elapsed_minutes >= 0) & (elapsed_minutes <= horizon * args.bar_minutes + 2 * args.bar_minutes)

        for family in MODEL_FAMILIES:
            for test_year in TEST_YEARS:
                test_start = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
                test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
                train_mask = (times < test_start) & (exit_times < test_start)
                test_mask = (times >= test_start) & (times < test_end)
                train_idx = np.flatnonzero(train_mask.to_numpy() & common_valid & label_valid)
                test_idx = np.flatnonzero(test_mask.to_numpy() & common_valid & label_valid)
                model = make_model(family)
                model.fit(x.iloc[train_idx], gross_target[train_idx])
                train_score = model.predict(x.iloc[train_idx])
                test_score = model.predict(x.iloc[test_idx])
                train_valid = np.ones(len(train_idx), dtype=bool)
                test_valid = np.ones(len(test_idx), dtype=bool)
                train_weeks = elapsed_weeks(times.iloc[train_idx].reset_index(drop=True))

                for target_cadence in TARGET_CADENCES:
                    threshold = choose_threshold(train_score, train_valid, horizon, train_weeks, target_cadence)
                    chosen_local = select_nonoverlapping(test_score, test_valid, threshold, horizon)
                    chosen = test_idx[chosen_local]
                    direction = np.sign(test_score[chosen_local])
                    net = direction * gross_target[chosen] - cost_r[chosen]
                    metrics = trade_metrics(net, times.iloc[test_idx].reset_index(drop=True))
                    cell_rows.append({
                        "model_family": family,
                        "horizon_bars": horizon,
                        "test_year": test_year,
                        "target_cadence": target_cadence,
                        "threshold": float(threshold),
                        **metrics,
                    })
                if test_year == TEST_YEARS[-1]:
                    fold_predictions[(family, horizon, test_year)] = (model, x.iloc[test_idx].copy(), gross_target[test_idx].copy())

    folds = pd.DataFrame(cell_rows)
    folds.to_csv(args.out_dir / "walk_forward_folds.csv", index=False)
    summaries = []
    for family in MODEL_FAMILIES:
        for horizon in horizons:
            subset = folds[(folds.model_family == family) & (folds.horizon_bars == horizon)]
            primary = subset[subset.target_cadence == 3.5].copy()
            cadence_valid = primary[(primary.trades_per_week >= 2.0) & (primary.trades_per_week <= 5.0)]
            pooled_win = float(primary.gross_win_r.sum())
            pooled_loss = float(primary.gross_loss_r.sum())
            pooled_pf = pooled_win / pooled_loss if pooled_loss > 0 else 0.0
            positive_contrib = primary.gross_win_r.clip(lower=0)
            max_year_share = float(positive_contrib.max() / positive_contrib.sum()) if positive_contrib.sum() > 0 else 1.0
            adjacent_pf = {}
            for cadence in (2.5, 4.5):
                adj = subset[subset.target_cadence == cadence]
                loss = float(adj.gross_loss_r.sum())
                adjacent_pf[str(cadence)] = float(adj.gross_win_r.sum() / loss) if loss > 0 else 0.0
            gates = {
                "cadence_valid_folds_at_least_3": int(len(cadence_valid)) >= 3,
                "all_cadence_valid_folds_positive_pf": bool(len(cadence_valid) >= 3 and (cadence_valid.net_r > 0).all() and (cadence_valid.profit_factor > 1.0).all()),
                "median_year_pf_ge_1_20": bool(primary.profit_factor.median() >= 1.20),
                "pooled_pf_ge_1_20": bool(pooled_pf >= 1.20),
                "max_year_positive_gross_share_le_0_40": bool(max_year_share <= 0.40),
                "adjacent_thresholds_stable": bool(adjacent_pf["2.5"] > 1.05 and adjacent_pf["4.5"] > 1.05),
            }
            summaries.append({
                "model_family": family,
                "horizon_bars": horizon,
                "primary_trades": int(primary.trades.sum()),
                "cadence_valid_folds": int(len(cadence_valid)),
                "median_year_pf": float(primary.profit_factor.median()),
                "pooled_pf": float(pooled_pf),
                "pooled_net_r": float(primary.net_r.sum()),
                "max_year_positive_gross_share": max_year_share,
                "adjacent_pooled_pf": adjacent_pf,
                "gates": gates,
                "survivor": all(gates.values()),
            })

    ranked = sorted(summaries, key=lambda r: (r["survivor"], r["pooled_pf"], r["pooled_net_r"]), reverse=True)
    best = ranked[0]
    model, xdiag, ydiag = fold_predictions[(best["model_family"], best["horizon_bars"], 2022)]
    diagnostics = family_permutation_diagnostic(model, xdiag, ydiag, families)
    pd.DataFrame(diagnostics).sort_values("mse_increase_mean", ascending=False).to_csv(args.out_dir / "feature_family_diagnostics.csv", index=False)

    result = {
        "schema_version": "rsf_pair_state_model_discovery.v1",
        "hypothesis_id": args.hypothesis_id,
        "census_path": str(args.census.resolve()),
        "census_sha256": sha256_file(args.census),
        "rows": int(len(df)),
        "first_source_bar_utc": times.iloc[0].isoformat(),
        "last_source_bar_utc": times.iloc[-1].isoformat(),
        "models_preregistered": len(MODEL_FAMILIES) * len(horizons),
        "model_fits": len(MODEL_FAMILIES) * len(horizons) * len(TEST_YEARS),
        "threshold_fold_evaluations": int(len(folds)),
        "horizons": list(horizons),
        "bar_minutes": args.bar_minutes,
        "point": POINT,
        "cost_model": f"observed_spread*{POINT}*(1.5+0.15*(1+VRC_vol_percentile/100))/TB_ATR",
        "summaries": ranked,
        "survivor_count": int(sum(r["survivor"] for r in ranked)),
        "best_diagnostic_cell": best,
        "feature_family_diagnostics_2022": diagnostics,
        "validation_2023_plus_opened": False,
        "verdict": "DISCOVERY_SURVIVOR_FREEZE_REQUIRED" if any(r["survivor"] for r in ranked) else "KILL_NO_STABLE_DISCOVERY_EDGE",
    }
    (args.out_dir / args.results_name).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": result["verdict"], "survivors": result["survivor_count"], "best": best}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
