#!/usr/bin/env python3
"""Frozen offline probe and ONNX exporter for the DRAT ICT hypothesis.

The probe uses completed EURUSD M15 bars only.  It trains two tabular
classifiers on causal labels (persistent regime and breakout event), then
evaluates a rules-only ICT state machine against the same state machine gated
by the classifiers on a later, untouched window.  Raw rates stay in memory.

This is discovery evidence, not Strategy Tester or promotion evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


FEATURES = [
    "ret4_atr",
    "ema_gap_atr",
    "atr_ratio",
    "range_atr",
    "efficiency16",
    "volume_z20",
    "close_location",
    "break_distance_atr",
]
REGIME_CLASSES = ["trend", "range", "stress"]
SPEC_VERSION = "drat_onnx_ict_probe.v1"
HYPOTHESIS_ID = "HYP-DRAT-ONNX-ICT-M15-EUR-001"


@dataclass(frozen=True)
class FrozenSpec:
    symbol: str = "EURUSD"
    timeframe: str = "M15"
    train_from: str = "2020.01.01"
    train_to: str = "2023.12.31"
    probe_from: str = "2024.01.01"
    probe_to: str = "2026.06.30"
    sweep_lookback: int = 8
    mss_expiry_bars: int = 4
    zone_expiry_bars: int = 8
    max_hold_bars: int = 32
    stop_atr_buffer: float = 0.15
    target_r: float = 2.0
    cost_r: float = 0.10
    session_start_hour: int = 6
    session_end_hour: int = 20
    min_model_confidence: float = 0.50
    stress_breakout_min: float = 0.65
    min_probe_pf: float = 1.15
    min_trades_per_week: float = 2.0
    max_trades_per_week: float = 5.0


SPEC = FrozenSpec()


def parse_date(value: str, end: bool = False) -> datetime:
    parsed = datetime.strptime(value, "%Y.%m.%d").replace(tzinfo=timezone.utc)
    if end:
        return parsed.replace(hour=23, minute=59, second=59)
    return parsed


def fetch_rates(terminal: str, spec: FrozenSpec) -> tuple[pd.DataFrame, dict[str, Any]]:
    if not mt5.initialize(path=terminal, timeout=60_000):
        raise RuntimeError(f"MetaTrader5 initialize failed: {mt5.last_error()}")
    try:
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        if terminal_info is None or account_info is None:
            raise RuntimeError(f"MT5 terminal/account info unavailable: {mt5.last_error()}")
        frames: list[pd.DataFrame] = []
        for year in range(int(spec.train_from[:4]), int(spec.probe_to[:4]) + 1):
            start = max(parse_date(spec.train_from), datetime(year, 1, 1, tzinfo=timezone.utc))
            finish = min(parse_date(spec.probe_to, end=True), datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
            if finish < start:
                continue
            rates = mt5.copy_rates_range(spec.symbol, mt5.TIMEFRAME_M15, start, finish)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"No rates for {spec.symbol} {year}: {mt5.last_error()}")
            frames.append(pd.DataFrame(rates))
        data = pd.concat(frames, ignore_index=True)
        data["time"] = pd.to_datetime(data["time"], unit="s", utc=True)
        data = data.drop_duplicates(subset="time", keep="last").sort_values("time").reset_index(drop=True)
        provenance = {
            "server": str(account_info.server),
            "trade_mode": int(account_info.trade_mode),
            "terminal_build": int(terminal_info.build),
            "terminal_data_path": str(terminal_info.data_path),
            "rows": int(len(data)),
            "first_bar_utc": data["time"].iloc[0].isoformat(),
            "last_bar_utc": data["time"].iloc[-1].isoformat(),
        }
        return data, provenance
    finally:
        mt5.shutdown()


def build_features(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    df["atr14"] = true_range.ewm(alpha=1.0 / 14.0, adjust=False).mean()
    df["atr96"] = true_range.ewm(alpha=1.0 / 96.0, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    safe_atr = df["atr14"].replace(0.0, np.nan)
    df["ret4_atr"] = (df["close"] - df["close"].shift(4)) / safe_atr
    df["ema_gap_atr"] = (df["ema20"] - df["ema50"]) / safe_atr
    df["atr_ratio"] = df["atr14"] / df["atr96"].replace(0.0, np.nan)
    df["range_atr"] = (df["high"] - df["low"]) / safe_atr
    path = df["close"].diff().abs().rolling(16).sum()
    df["efficiency16"] = (df["close"] - df["close"].shift(16)).abs() / path.replace(0.0, np.nan)
    vol_mean = df["tick_volume"].rolling(20).mean()
    vol_std = df["tick_volume"].rolling(20).std(ddof=0).replace(0.0, np.nan)
    df["volume_z20"] = (df["tick_volume"] - vol_mean) / vol_std
    candle_range = (df["high"] - df["low"]).replace(0.0, np.nan)
    df["close_location"] = (df["close"] - df["low"]) / candle_range
    prior_high = df["high"].shift(1).rolling(20).max()
    prior_low = df["low"].shift(1).rolling(20).min()
    up_distance = (df["close"] - prior_high) / safe_atr
    down_distance = (prior_low - df["close"]) / safe_atr
    df["break_distance_atr"] = np.maximum(up_distance, down_distance)

    stress = (df["atr_ratio"] >= 1.35) | (df["range_atr"] >= 2.00)
    trend = (~stress) & (df["efficiency16"] >= 0.35) & (df["ema_gap_atr"].abs() >= 0.25)
    df["regime_label"] = np.where(stress, 2, np.where(trend, 0, 1)).astype(int)
    df["breakout_label"] = (df["break_distance_atr"] >= 0.05).astype(int)
    return df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES).reset_index(drop=True)


def make_model(random_state: int) -> Pipeline:
    return Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=1.0,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=random_state,
                ),
            ),
        ]
    )


def train_models(df: pd.DataFrame, spec: FrozenSpec) -> tuple[Pipeline, Pipeline, dict[str, Any]]:
    train_end = parse_date(spec.train_to, end=True)
    probe_start = parse_date(spec.probe_from)
    train = df[df["time"] <= train_end].copy()
    probe = df[df["time"] >= probe_start].copy()
    if len(train) < 10_000 or len(probe) < 10_000:
        raise RuntimeError(f"Insufficient train/probe rows: train={len(train)} probe={len(probe)}")
    regime = make_model(5601).fit(train[FEATURES], train["regime_label"])
    breakout = make_model(5602).fit(train[FEATURES], train["breakout_label"])
    regime_prob = regime.predict_proba(probe[FEATURES])
    breakout_prob = breakout.predict_proba(probe[FEATURES])[:, 1]
    class_brier = {
        REGIME_CLASSES[k]: float(brier_score_loss((probe["regime_label"] == k).astype(int), regime_prob[:, k]))
        for k in range(3)
    }
    metrics = {
        "train_rows": int(len(train)),
        "probe_rows": int(len(probe)),
        "regime_accuracy": float(accuracy_score(probe["regime_label"], np.argmax(regime_prob, axis=1))),
        "regime_log_loss": float(log_loss(probe["regime_label"], regime_prob, labels=[0, 1, 2])),
        "regime_brier_by_class": class_brier,
        "breakout_accuracy": float(accuracy_score(probe["breakout_label"], breakout_prob >= 0.5)),
        "breakout_brier": float(brier_score_loss(probe["breakout_label"], breakout_prob)),
        "breakout_log_loss": float(log_loss(probe["breakout_label"], breakout_prob, labels=[0, 1])),
        "train_regime_counts": {REGIME_CLASSES[int(k)]: int(v) for k, v in train["regime_label"].value_counts().sort_index().items()},
        "probe_regime_counts": {REGIME_CLASSES[int(k)]: int(v) for k, v in probe["regime_label"].value_counts().sort_index().items()},
    }
    return regime, breakout, metrics


def model_outputs(df: pd.DataFrame, regime: Pipeline, breakout: Pipeline) -> pd.DataFrame:
    out = df.copy()
    probs = regime.predict_proba(out[FEATURES])
    out[["p_trend", "p_range", "p_stress"]] = probs
    out["p_breakout"] = breakout.predict_proba(out[FEATURES])[:, 1]
    out["pred_regime"] = np.argmax(probs, axis=1)
    out["model_confidence"] = np.max(probs, axis=1)
    return out


def allowed_session(ts: pd.Timestamp, spec: FrozenSpec) -> bool:
    return spec.session_start_hour <= ts.hour < spec.session_end_hour and ts.dayofweek < 5


def find_zone(df: pd.DataFrame, sweep: int, mss: int, direction: int) -> tuple[float, float, str] | None:
    # Prefer a causal three-candle FVG; otherwise use the final opposing candle
    # before the MSS as a deterministic order-block proxy.
    for i in range(max(sweep + 1, 2), mss + 1):
        if direction > 0 and df.at[i, "low"] > df.at[i - 2, "high"]:
            return float(df.at[i - 2, "high"]), float(df.at[i, "low"]), "FVG"
        if direction < 0 and df.at[i, "high"] < df.at[i - 2, "low"]:
            return float(df.at[i, "high"]), float(df.at[i - 2, "low"]), "FVG"
    candidates = range(mss - 1, max(-1, sweep - 4), -1)
    for i in candidates:
        opposing = (direction > 0 and df.at[i, "close"] < df.at[i, "open"]) or (
            direction < 0 and df.at[i, "close"] > df.at[i, "open"]
        )
        if opposing:
            return (
                float(min(df.at[i, "open"], df.at[i, "close"])),
                float(max(df.at[i, "open"], df.at[i, "close"])),
                "OB",
            )
    return None


def gate_allows(row: pd.Series, direction: int, spec: FrozenSpec) -> bool:
    if float(row["model_confidence"]) < spec.min_model_confidence:
        return False
    regime = int(row["pred_regime"])
    if regime == 2:
        return float(row["p_breakout"]) >= spec.stress_breakout_min
    if regime == 0:
        return (direction > 0 and float(row["ema_gap_atr"]) > 0.0) or (
            direction < 0 and float(row["ema_gap_atr"]) < 0.0
        )
    return True


def simulate_exit(
    df: pd.DataFrame,
    entry_i: int,
    direction: int,
    entry: float,
    stop: float,
    target: float,
    max_hold: int,
    cost_r: float,
) -> tuple[int, float, str]:
    risk = abs(entry - stop)
    if not math.isfinite(risk) or risk <= 0.0:
        return entry_i, -1.0 - cost_r, "INVALID_RISK"
    last = min(len(df) - 1, entry_i + max_hold - 1)
    for i in range(entry_i, last + 1):
        low = float(df.at[i, "low"])
        high = float(df.at[i, "high"])
        stop_hit = low <= stop if direction > 0 else high >= stop
        target_hit = high >= target if direction > 0 else low <= target
        if stop_hit and target_hit:
            return i, -1.0 - cost_r, "BOTH_SL_FIRST"
        if stop_hit:
            return i, -1.0 - cost_r, "SL"
        if target_hit:
            return i, abs(target - entry) / risk - cost_r, "TP"
    final_close = float(df.at[last, "close"])
    r_value = direction * (final_close - entry) / risk - cost_r
    return last, float(r_value), "TIME"


def generate_setups(df: pd.DataFrame, spec: FrozenSpec, gated: bool) -> list[dict[str, Any]]:
    trades: list[dict[str, Any]] = []
    i = max(120, spec.sweep_lookback + 5)
    while i < len(df) - spec.max_hold_bars - 2:
        if not allowed_session(df.at[i, "time"], spec):
            i += 1
            continue
        prior_low = float(df.loc[i - spec.sweep_lookback : i - 1, "low"].min())
        prior_high = float(df.loc[i - spec.sweep_lookback : i - 1, "high"].max())
        candle_range = float(df.at[i, "high"] - df.at[i, "low"])
        if candle_range <= 0.0:
            i += 1
            continue
        close_location = float((df.at[i, "close"] - df.at[i, "low"]) / candle_range)
        direction = 0
        if df.at[i, "low"] < prior_low and df.at[i, "close"] > prior_low and close_location >= 0.55:
            direction = 1
        elif df.at[i, "high"] > prior_high and df.at[i, "close"] < prior_high and close_location <= 0.45:
            direction = -1
        if direction == 0:
            i += 1
            continue

        sweep_extreme = float(df.at[i, "low"] if direction > 0 else df.at[i, "high"])
        mss_level = float(
            df.loc[i - 3 : i - 1, "high"].max() if direction > 0 else df.loc[i - 3 : i - 1, "low"].min()
        )
        mss = None
        for j in range(i + 1, min(len(df) - 1, i + spec.mss_expiry_bars) + 1):
            if (direction > 0 and df.at[j, "close"] > mss_level) or (
                direction < 0 and df.at[j, "close"] < mss_level
            ):
                mss = j
                break
        if mss is None:
            i += 1
            continue
        zone = find_zone(df, i, mss, direction)
        if zone is None:
            i += 1
            continue
        zone_low, zone_high, zone_type = zone
        retest = None
        for j in range(mss + 1, min(len(df) - 2, mss + spec.zone_expiry_bars) + 1):
            touches = float(df.at[j, "low"]) <= zone_high and float(df.at[j, "high"]) >= zone_low
            confirms = float(df.at[j, "close"]) >= (zone_low + zone_high) / 2 if direction > 0 else float(
                df.at[j, "close"]
            ) <= (zone_low + zone_high) / 2
            if touches and confirms:
                retest = j
                break
        if retest is None or not allowed_session(df.at[retest, "time"], spec):
            i += 1
            continue
        if gated and not gate_allows(df.loc[retest], direction, spec):
            i = retest + 1
            continue

        entry_i = retest + 1
        entry = float(df.at[entry_i, "open"])
        atr = float(df.at[retest, "atr14"])
        stop = sweep_extreme - spec.stop_atr_buffer * atr if direction > 0 else sweep_extreme + spec.stop_atr_buffer * atr
        risk = abs(entry - stop)
        if risk <= 0.0 or risk > 3.0 * atr:
            i = entry_i + 1
            continue
        target = entry + direction * spec.target_r * risk
        exit_i, outcome_r, exit_reason = simulate_exit(
            df, entry_i, direction, entry, stop, target, spec.max_hold_bars, spec.cost_r
        )
        trades.append(
            {
                "signal_time_utc": df.at[retest, "time"].isoformat(),
                "entry_time_utc": df.at[entry_i, "time"].isoformat(),
                "exit_time_utc": df.at[exit_i, "time"].isoformat(),
                "direction": "LONG" if direction > 0 else "SHORT",
                "zone_type": zone_type,
                "regime": REGIME_CLASSES[int(df.at[retest, "pred_regime"])],
                "p_breakout": round(float(df.at[retest, "p_breakout"]), 8),
                "outcome_r_after_proxy_cost": round(float(outcome_r), 8),
                "exit_reason": exit_reason,
            }
        )
        i = exit_i + 1
    return trades


def summarize_trades(trades: list[dict[str, Any]], spec: FrozenSpec) -> dict[str, Any]:
    start = parse_date(spec.probe_from)
    end = parse_date(spec.probe_to, end=True)
    weeks = (end - start).total_seconds() / (7.0 * 86400.0)
    values = np.array([float(t["outcome_r_after_proxy_cost"]) for t in trades], dtype=float)
    gross_profit = float(values[values > 0.0].sum()) if len(values) else 0.0
    gross_loss = float(-values[values < 0.0].sum()) if len(values) else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0.0 else (999.0 if gross_profit > 0.0 else 0.0)
    by_year: dict[str, Any] = {}
    for year in range(int(spec.probe_from[:4]), int(spec.probe_to[:4]) + 1):
        subset = np.array(
            [float(t["outcome_r_after_proxy_cost"]) for t in trades if t["entry_time_utc"].startswith(str(year))],
            dtype=float,
        )
        gp = float(subset[subset > 0.0].sum()) if len(subset) else 0.0
        gl = float(-subset[subset < 0.0].sum()) if len(subset) else 0.0
        by_year[str(year)] = {
            "trades": int(len(subset)),
            "net_r": float(subset.sum()) if len(subset) else 0.0,
            "profit_factor": gp / gl if gl > 0.0 else (999.0 if gp > 0.0 else 0.0),
        }
    return {
        "trades": int(len(values)),
        "elapsed_weeks": weeks,
        "trades_per_elapsed_week": float(len(values) / weeks),
        "net_r_after_proxy_cost": float(values.sum()) if len(values) else 0.0,
        "profit_factor_after_proxy_cost": float(pf),
        "win_rate": float(np.mean(values > 0.0)) if len(values) else 0.0,
        "mean_r": float(np.mean(values)) if len(values) else 0.0,
        "by_year": by_year,
    }


def gate_verdict(control: dict[str, Any], challenger: dict[str, Any], model: dict[str, Any], spec: FrozenSpec) -> dict[str, Any]:
    checks = {
        "model_breakout_brier_le_0_25": model["breakout_brier"] <= 0.25,
        "challenger_pf_ge_probe_gate": challenger["profit_factor_after_proxy_cost"] >= spec.min_probe_pf,
        "challenger_net_r_positive": challenger["net_r_after_proxy_cost"] > 0.0,
        "challenger_cadence_in_goal_band": spec.min_trades_per_week
        <= challenger["trades_per_elapsed_week"]
        <= spec.max_trades_per_week,
        "challenger_pf_not_below_control": challenger["profit_factor_after_proxy_cost"]
        >= control["profit_factor_after_proxy_cost"],
        "challenger_net_not_below_control": challenger["net_r_after_proxy_cost"]
        >= control["net_r_after_proxy_cost"],
        "full_years_positive": all(
            challenger["by_year"][str(year)]["net_r"] > 0.0 for year in (2024, 2025)
        ),
    }
    return {"checks": checks, "verdict": "PROBE_SURVIVOR" if all(checks.values()) else "KILL_AT_OFFLINE_PROBE"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def export_probability_model(model: Pipeline, feature_count: int, path: Path) -> dict[str, Any]:
    try:
        import onnx
        import onnxruntime as ort
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
    except ImportError as exc:
        raise RuntimeError("Export requires onnx and skl2onnx installed on D runtime") from exc

    converted = convert_sklearn(
        model,
        initial_types=[("features", FloatTensorType([None, feature_count]))],
        options={id(model.named_steps["model"]): {"zipmap": False}},
        target_opset=17,
    )
    probability_outputs = [output for output in converted.graph.output if "prob" in output.name.lower()]
    if len(probability_outputs) != 1:
        raise RuntimeError(f"Expected exactly one probability output, got {[o.name for o in converted.graph.output]}")
    del converted.graph.output[:]
    converted.graph.output.extend(probability_outputs)
    onnx.checker.check_model(converted)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(converted.SerializeToString())
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "input_name": session.get_inputs()[0].name,
        "input_shape": session.get_inputs()[0].shape,
        "output_name": session.get_outputs()[0].name,
        "output_shape": session.get_outputs()[0].shape,
    }


def export_models(
    regime: Pipeline,
    breakout: Pipeline,
    probe_df: pd.DataFrame,
    export_dir: Path,
) -> dict[str, Any]:
    import onnxruntime as ort

    regime_path = export_dir / "regime_model_v1.onnx"
    breakout_path = export_dir / "breakout_model_v1.onnx"
    regime_meta = export_probability_model(regime, len(FEATURES), regime_path)
    breakout_meta = export_probability_model(breakout, len(FEATURES), breakout_path)
    sample = probe_df[FEATURES].iloc[:256].to_numpy(dtype=np.float32)
    parity: dict[str, Any] = {}
    for name, path, sklearn_model in (
        ("regime", regime_path, regime),
        ("breakout", breakout_path, breakout),
    ):
        session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        ort_prob = session.run(None, {session.get_inputs()[0].name: sample})[0]
        py_prob = sklearn_model.predict_proba(sample)
        parity[name] = {
            "max_abs_probability_error": float(np.max(np.abs(ort_prob - py_prob))),
            "rows": int(len(sample)),
            "pass_le_1e_5": bool(np.max(np.abs(ort_prob - py_prob)) <= 1e-5),
        }
    return {"regime": regime_meta, "breakout": breakout_meta, "parity": parity}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", default=r"C:\Program Files\MetaTrader 5\terminal64.exe")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--trades-out", type=Path)
    parser.add_argument("--export-dir", type=Path)
    args = parser.parse_args()

    raw, provenance = fetch_rates(args.terminal, SPEC)
    featured = build_features(raw)
    regime, breakout, model_metrics = train_models(featured, SPEC)
    scored = model_outputs(featured, regime, breakout)
    probe_start = parse_date(SPEC.probe_from)
    probe_end = parse_date(SPEC.probe_to, end=True)
    oos = scored[(scored["time"] >= probe_start) & (scored["time"] <= probe_end)].reset_index(drop=True)
    control_trades = generate_setups(oos, SPEC, gated=False)
    challenger_trades = generate_setups(oos, SPEC, gated=True)
    control_summary = summarize_trades(control_trades, SPEC)
    challenger_summary = summarize_trades(challenger_trades, SPEC)
    verdict = gate_verdict(control_summary, challenger_summary, model_metrics, SPEC)
    payload: dict[str, Any] = {
        "schema_version": SPEC_VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_spec": asdict(SPEC),
        "feature_order": FEATURES,
        "regime_classes": REGIME_CLASSES,
        "data_provenance": provenance,
        "model_metrics_oos": model_metrics,
        "rules_only_control": control_summary,
        "onnx_gate_challenger": challenger_summary,
        "gate": verdict,
        "limitations": [
            "Offline OHLC proxy only; not Strategy Tester or native tick-path evidence.",
            "Cost is a frozen 0.10R falsification proxy, not verified broker execution cost.",
            "Labels are causal heuristic state labels; they do not predict future returns.",
            "Same-bar stop/target collision is scored stop-first.",
        ],
    }
    if args.export_dir is not None:
        payload["onnx_export"] = export_models(regime, breakout, oos, args.export_dir)
    write_json(args.out, payload)
    if args.trades_out is not None:
        write_json(
            args.trades_out,
            {"control": control_trades, "challenger": challenger_trades, "hypothesis_id": HYPOTHESIS_ID},
        )
    print(json.dumps({"verdict": verdict["verdict"], "out": str(args.out), "checks": verdict["checks"]}, indent=2))
    return 0 if verdict["verdict"] == "PROBE_SURVIVOR" else 2


if __name__ == "__main__":
    sys.exit(main())
