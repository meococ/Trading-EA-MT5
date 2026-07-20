#!/usr/bin/env python3
"""Run the single frozen HYP-014 rolling-OOS probability/no-trade diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


WORKSPACE = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "runtime"
    / "ictfvg_hyp012_context_forensics"
    / "positions_with_context.csv"
)
DEFAULT_OUT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "runtime"
    / "ictfvg_hyp014_probability_probe"
)
INPUT_SHA256 = "1661ECE481CC1D52BE7751F445602ECE79AC1CA1F6F92AA6C2BF28594645B5B6"
INPUT_BYTES = 2_580_003
PLAN_SHA256 = "A814148BFCDFFDE12F1DA49A7BF3A8C79379FEA753BEA626C248DACA4FC9AED2"
SEED = 560014
BOOTSTRAP_SAMPLES = 10_000
EVAL_YEARS = tuple(range(2020, 2027))
COST_PIPS = {"x1_0": 1.50, "x1_5": 2.25, "x2_0": 3.00}

BASE_FEATURES = [
    "direction",
    "confirmation_body_vs_prior20",
    "confirmation_directional_close_location",
    "confirmation_range_pips",
    "bars_after_sweep",
    "sweep_depth_pips",
    "sweep_reclaim_pips",
    "risk_pips",
    "h1_ema_spread_directional_atr",
    "h1_return5_directional_atr",
    "h4_ema_spread_directional_atr",
    "h4_return5_directional_atr",
]
INTERACTION_FEATURES = [
    "body_x_close_location",
    "sweep_depth_x_reclaim",
    "h1_x_h4_ema_spread",
    "h1_x_h4_return5",
]
ALL_FEATURES = BASE_FEATURES + INTERACTION_FEATURES


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_ready(value):
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return None if not np.isfinite(value) else value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return value


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(json_ready(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def impute_and_interact(
    train: pd.DataFrame, test: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    medians: dict[str, float] = {}
    train_columns: list[np.ndarray] = []
    test_columns: list[np.ndarray] = []
    for feature in BASE_FEATURES:
        train_values = pd.to_numeric(train[feature], errors="coerce").to_numpy(float)
        test_values = pd.to_numeric(test[feature], errors="coerce").to_numpy(float)
        median = float(np.nanmedian(train_values))
        if not np.isfinite(median):
            raise ValueError(f"training feature is entirely missing: {feature}")
        medians[feature] = median
        train_columns.append(np.where(np.isfinite(train_values), train_values, median))
        test_columns.append(np.where(np.isfinite(test_values), test_values, median))

    train_base = np.column_stack(train_columns)
    test_base = np.column_stack(test_columns)
    index = {name: position for position, name in enumerate(BASE_FEATURES)}

    def interactions(values: np.ndarray) -> np.ndarray:
        return np.column_stack(
            [
                values[:, index["confirmation_body_vs_prior20"]]
                * values[:, index["confirmation_directional_close_location"]],
                values[:, index["sweep_depth_pips"]]
                * values[:, index["sweep_reclaim_pips"]],
                values[:, index["h1_ema_spread_directional_atr"]]
                * values[:, index["h4_ema_spread_directional_atr"]],
                values[:, index["h1_return5_directional_atr"]]
                * values[:, index["h4_return5_directional_atr"]],
            ]
        )

    return (
        np.column_stack([train_base, interactions(train_base)]),
        np.column_stack([test_base, interactions(test_base)]),
        medians,
    )


def profit_factor(returns: np.ndarray) -> float | None:
    gross_profit = float(returns[returns > 0].sum())
    gross_loss = float(-returns[returns < 0].sum())
    if gross_loss <= 0:
        return None
    return gross_profit / gross_loss


def max_drawdown_r(returns: np.ndarray) -> float:
    equity = np.concatenate([[0.0], np.cumsum(returns)])
    peaks = np.maximum.accumulate(equity)
    return float(np.max(peaks - equity))


def apply_weekly_cap(times: pd.Series, scores: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    accepted = np.zeros(len(times), dtype=bool)
    weekly_rank = np.zeros(len(times), dtype=int)
    counts: dict[str, int] = {}
    for index, (timestamp, score) in enumerate(zip(times, scores, strict=True)):
        iso = timestamp.isocalendar()
        week_key = f"{iso.year:04d}-W{iso.week:02d}"
        if score >= threshold and counts.get(week_key, 0) < 5:
            counts[week_key] = counts.get(week_key, 0) + 1
            accepted[index] = True
            weekly_rank[index] = counts[week_key]
    return accepted, weekly_rank


def bootstrap_week_blocks(predictions: pd.DataFrame) -> dict:
    grouped = (
        predictions.groupby("iso_week", sort=True)
        .agg(
            opportunities=("position_id", "size"),
            policy_r=("policy_r_x1_0", "sum"),
            control_r=("r_x1_0", "sum"),
        )
        .reset_index(drop=True)
    )
    opportunities = grouped["opportunities"].to_numpy(float)
    policy = grouped["policy_r"].to_numpy(float)
    control = grouped["control_r"].to_numpy(float)
    rng = np.random.default_rng(SEED)
    policy_samples = np.empty(BOOTSTRAP_SAMPLES, dtype=float)
    delta_samples = np.empty(BOOTSTRAP_SAMPLES, dtype=float)
    block_count = len(grouped)
    for sample in range(BOOTSTRAP_SAMPLES):
        selected = rng.integers(0, block_count, size=block_count)
        denominator = float(opportunities[selected].sum())
        policy_samples[sample] = float(policy[selected].sum()) / denominator
        delta_samples[sample] = float((policy[selected] - control[selected]).sum()) / denominator
    return {
        "blocks": block_count,
        "samples": BOOTSTRAP_SAMPLES,
        "seed": SEED,
        "policy_r_per_opportunity_ci95": [
            float(np.quantile(policy_samples, 0.025)),
            float(np.quantile(policy_samples, 0.975)),
        ],
        "paired_delta_r_per_opportunity_ci95": [
            float(np.quantile(delta_samples, 0.025)),
            float(np.quantile(delta_samples, 0.975)),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    input_path = args.input.resolve()
    if input_path.stat().st_size != INPUT_BYTES or sha256(input_path) != INPUT_SHA256:
        raise SystemExit("input ledger binding failed")

    data = pd.read_csv(input_path)
    if len(data) != 3385 or data["position_id"].duplicated().any():
        raise SystemExit("opportunity identity contract failed")
    data["entry_time"] = pd.to_datetime(data["entry_time_utc"], utc=True)
    data = data.sort_values(["entry_time", "position_id"], kind="stable").reset_index(drop=True)
    data["entry_year"] = data["entry_time"].dt.year
    data["risk_pips"] = pd.to_numeric(data["risk_pts"], errors="raise") / 10.0
    if (data["risk_pips"] <= 0).any():
        raise SystemExit("non-positive risk geometry")
    for label, cost in COST_PIPS.items():
        data[f"r_{label}"] = pd.to_numeric(data["r_gross"], errors="raise") - cost / data["risk_pips"]
    data["target_positive_x1_0"] = (data["r_x1_0"] > 0).astype(int)

    fold_payloads: list[dict] = []
    prediction_frames: list[pd.DataFrame] = []
    for year in EVAL_YEARS:
        train = data[data["entry_year"] < year].copy()
        test = data[data["entry_year"] == year].copy()
        if train["entry_year"].min() != 2018 or train["entry_year"].max() != year - 1:
            raise SystemExit(f"expanding train boundary failed for {year}")
        if test.empty:
            raise SystemExit(f"empty evaluation year: {year}")

        x_train, x_test, medians = impute_and_interact(train, test)
        scaler = StandardScaler()
        x_train_scaled = scaler.fit_transform(x_train)
        x_test_scaled = scaler.transform(x_test)
        model = LogisticRegression(
            penalty="l2",
            C=0.1,
            solver="liblinear",
            max_iter=2000,
            random_state=SEED,
            class_weight=None,
        )
        model.fit(x_train_scaled, train["target_positive_x1_0"].to_numpy(int))
        train_scores = model.predict_proba(x_train_scaled)[:, 1]
        test_scores = model.predict_proba(x_test_scaled)[:, 1]

        train_r = train["r_x1_0"].to_numpy(float)
        mean_win = float(train_r[train_r > 0].mean())
        mean_loss = float(train_r[train_r <= 0].mean())
        probability_for_plus_005r = float(np.clip((0.05 - mean_loss) / (mean_win - mean_loss), 0.0, 1.0))
        train_p60 = float(np.quantile(train_scores, 0.60, method="linear"))
        threshold = max(train_p60, probability_for_plus_005r)
        accepted, weekly_rank = apply_weekly_cap(test["entry_time"], test_scores, threshold)

        frame = test[
            [
                "position_id",
                "entry_time_utc",
                "entry_year",
                "r_x1_0",
                "r_x1_5",
                "r_x2_0",
            ]
        ].copy()
        frame["score"] = test_scores
        frame["train_p60"] = train_p60
        frame["probability_for_plus_005r"] = probability_for_plus_005r
        frame["policy_threshold"] = threshold
        frame["accepted"] = accepted.astype(int)
        frame["weekly_accepted_rank"] = weekly_rank
        iso = test["entry_time"].dt.isocalendar()
        frame["iso_week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
        for label in COST_PIPS:
            frame[f"policy_r_{label}"] = frame[f"r_{label}"] * frame["accepted"]
        prediction_frames.append(frame)

        fold_payloads.append(
            {
                "evaluation_year": year,
                "train_year_from": int(train["entry_year"].min()),
                "train_year_to": int(train["entry_year"].max()),
                "train_rows": len(train),
                "test_rows": len(test),
                "accepted_rows": int(accepted.sum()),
                "train_p60": train_p60,
                "train_mean_win_r_x1_0": mean_win,
                "train_mean_loss_r_x1_0": mean_loss,
                "probability_for_plus_005r": probability_for_plus_005r,
                "policy_threshold": threshold,
                "imputation_medians": medians,
                "scaler_mean": dict(zip(ALL_FEATURES, scaler.mean_, strict=True)),
                "scaler_scale": dict(zip(ALL_FEATURES, scaler.scale_, strict=True)),
                "standardized_coefficients": dict(zip(ALL_FEATURES, model.coef_[0], strict=True)),
                "intercept": float(model.intercept_[0]),
            }
        )

    predictions = pd.concat(prediction_frames, ignore_index=True)
    accepted_mask = predictions["accepted"].to_numpy(bool)
    accepted_rows = int(accepted_mask.sum())
    start = pd.to_datetime(predictions["entry_time_utc"], utc=True).min()
    finish = pd.to_datetime(predictions["entry_time_utc"], utc=True).max()
    elapsed_weeks = float((finish - start).total_seconds() / (7 * 86400))

    metrics: dict[str, object] = {
        "evaluation_opportunities": len(predictions),
        "accepted_rows": accepted_rows,
        "elapsed_calendar_weeks": elapsed_weeks,
        "accepted_per_elapsed_week": accepted_rows / elapsed_weeks,
        "control_expectancy_r_x1_0": float(predictions["r_x1_0"].mean()),
    }
    for label in COST_PIPS:
        accepted_returns = predictions.loc[accepted_mask, f"r_{label}"].to_numpy(float)
        policy_returns = predictions[f"policy_r_{label}"].to_numpy(float)
        metrics[f"profit_factor_{label}"] = profit_factor(accepted_returns)
        metrics[f"accepted_expectancy_r_{label}"] = float(accepted_returns.mean()) if accepted_rows else None
        metrics[f"r_per_opportunity_{label}"] = float(policy_returns.mean())
    metrics["accepted_expectancy_delta_vs_control_x1_0"] = (
        float(metrics["accepted_expectancy_r_x1_0"]) - float(metrics["control_expectancy_r_x1_0"])
    )
    metrics["max_drawdown_r_x1_0"] = max_drawdown_r(predictions["policy_r_x1_0"].to_numpy(float))
    metrics["max_drawdown_pct_at_0_01pct_risk"] = float(metrics["max_drawdown_r_x1_0"]) * 0.01

    annual = (
        predictions.groupby("entry_year", sort=True)
        .agg(
            opportunities=("position_id", "size"),
            accepted=("accepted", "sum"),
            policy_r_x1_0=("policy_r_x1_0", "sum"),
        )
        .reset_index()
    )
    positive_annual = annual[annual["policy_r_x1_0"] > 0]["policy_r_x1_0"]
    metrics["positive_evaluation_years"] = int(len(positive_annual))
    metrics["positive_year_concentration"] = (
        float(positive_annual.max() / positive_annual.sum()) if len(positive_annual) else None
    )
    bootstrap = bootstrap_week_blocks(predictions)

    concentration = metrics["positive_year_concentration"]
    gates = {
        "accepted_rows_gte_300": accepted_rows >= 300,
        "cadence_gte_2": float(metrics["accepted_per_elapsed_week"]) >= 2.0,
        "cadence_lte_5": float(metrics["accepted_per_elapsed_week"]) <= 5.0,
        "pf_x1_0_gte_1_30": (metrics["profit_factor_x1_0"] or 0.0) >= 1.30,
        "expectancy_x1_0_gte_0_05r": (metrics["accepted_expectancy_r_x1_0"] or -999.0) >= 0.05,
        "r_per_opportunity_x1_0_gt_0": float(metrics["r_per_opportunity_x1_0"]) > 0.0,
        "expectancy_delta_gte_0_15r": float(metrics["accepted_expectancy_delta_vs_control_x1_0"]) >= 0.15,
        "bootstrap_policy_ci95_lower_gt_0": bootstrap["policy_r_per_opportunity_ci95"][0] > 0.0,
        "bootstrap_delta_ci95_lower_gt_0": bootstrap["paired_delta_r_per_opportunity_ci95"][0] > 0.0,
        "positive_years_gte_5": int(metrics["positive_evaluation_years"]) >= 5,
        "positive_year_concentration_lte_0_35": concentration is not None and float(concentration) <= 0.35,
        "pf_x1_5_gte_1_25": (metrics["profit_factor_x1_5"] or 0.0) >= 1.25,
        "pf_x2_0_gte_1_00": (metrics["profit_factor_x2_0"] or 0.0) >= 1.00,
        "max_drawdown_pct_lte_8": float(metrics["max_drawdown_pct_at_0_01pct_risk"]) <= 8.0,
    }
    passed = all(gates.values())

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = out_dir / "rolling_oos_predictions.csv"
    folds_path = out_dir / "fold_models.json"
    result_path = out_dir / "probe_result.json"
    predictions.to_csv(predictions_path, index=False, float_format="%.12g", lineterminator="\n")
    write_json(folds_path, {"feature_order": ALL_FEATURES, "folds": fold_payloads})
    result = {
        "schema_version": "alphafactory.probability_probe.v1",
        "run_id": "HYP014-ROLLING-OOS-001",
        "hypothesis_id": "HYP-ICT-FVG-PROB-RANK-EURUSD-M5-014",
        "epistemic_class": "DESIGN_AFTER_PARENT_OUTCOME_ROLLING_OOS_NOT_SEALED",
        "plan_sha256": PLAN_SHA256,
        "input": {"path": str(input_path), "bytes": INPUT_BYTES, "sha256": INPUT_SHA256},
        "trial_count": 1,
        "evaluation_years": list(EVAL_YEARS),
        "cost_pips_round_trip": COST_PIPS,
        "metrics": metrics,
        "annual": annual.to_dict(orient="records"),
        "bootstrap": bootstrap,
        "gates": gates,
        "passed_all_gates": passed,
        "verdict": (
            "PASS_DIAGNOSTIC_FRESH_SOURCE_PREREG_REQUIRED"
            if passed
            else "KILL_AT_ROLLING_OOS_DIAGNOSTIC_NO_CODE"
        ),
        "promotion_eligible": False,
        "source_build_authorized": False,
        "model0_authorized": False,
        "outputs": {
            "predictions": {"path": str(predictions_path), "sha256": sha256(predictions_path)},
            "fold_models": {"path": str(folds_path), "sha256": sha256(folds_path)},
        },
    }
    write_json(result_path, result)
    print(json.dumps({"verdict": result["verdict"], "metrics": metrics, "gates": gates}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

