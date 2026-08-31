"""Hash-bound, outcome-blind preflight for the proposed VRAS V4 plan.

The original version of this script treated a three-symbol parquet as EURJPY
and took its last rows without filtering ``symbol``.  This corrected version
keeps a forensic reproduction of that calculation, applies exact identity
filters, prevents session stitching, and denies EA/MT5 authority when the plan
or data contract is incomplete.  It never computes trade outcomes or PnL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


WORKSPACE = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-VRAS-EURUSD-M5-015"
VERDICT_BLOCKED = (
    "PARK_PRE_EA_INVALID_PLAN_EVIDENCE_OR_CAPABILITY_NO_OUTCOME_READ"
)
VERDICT_SURVIVOR = "SURVIVE_PREFLIGHT_FREEZE_ATOMIC_ENGINE_NEXT"

PREFLIGHT_PLAN = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_VRAS_RegimeAdaptiveScalperV4"
    / "research"
    / "HYP-VRAS-EURUSD-M5-015_PREFLIGHT_PLAN.md"
)
PREFLIGHT_PLAN_SHA256 = (
    "BB0F95FDF5DA3654D212E443CCDAA87CBE2A1081FC6B8C1E29B0253DF6E916DB"
)
# The supplied plan was hardcoded to
#   C:\Users\ADMIN\.gemini\antigravity\brain\911cac32-...\final_ea_build_plan.md
# a path on a machine that is not this one. The hash check below already made
# the runner fail there, just with an unreadable error. Make the input explicit
# and fail closed with a message that names the problem.
_SUPPLIED_PLAN_ENV = "EMPIRICAL_PROBE_SUPPLIED_PLAN"
SUPPLIED_PLAN = Path(os.environ.get(_SUPPLIED_PLAN_ENV, "")) if os.environ.get(
    _SUPPLIED_PLAN_ENV
) else None
SUPPLIED_PLAN_SHA256 = (
    "453E8EC25F5C79BCEBBF598D2394AA7E3112531366AA7E7A7C9D72F7B4653B9C"
)
ORIGINAL_RUNNER_SHA256 = (
    "E77C29139BB2B1D1A178639381306D77E7E0A631C2773CB13041BA47C6FBD663"
)

TRIANGULAR_ROOT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "fivepercent"
    / "TriangularConsensusLag"
    / "HYP-TRILAG-EURJPY-M1-002"
)
TRIANGULAR_DATA = TRIANGULAR_ROOT / "design_m1_close.parquet"
TRIANGULAR_DATA_SHA256 = (
    "C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6"
)
TRIANGULAR_MANIFEST = TRIANGULAR_ROOT / "design_m1_manifest.json"
TRIANGULAR_MANIFEST_SHA256 = (
    "4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8"
)

EURUSD_ROOT = WORKSPACE / "02. AlphaFactory" / "data" / "fivepercent" / "EURUSD"
EURUSD_DATA = EURUSD_ROOT / "EURUSD_M1_2015_now.parquet"
EURUSD_MANIFEST = EURUSD_ROOT / "manifest.json"
EURUSD_MANIFEST_SHA256 = (
    "2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def legacy_calculate_hurst(series: Iterable[float], lags=range(2, 40)) -> float:
    """Reproduce the estimator used by the supplied plan for forensic parity."""
    values = np.asarray(series, dtype=float)
    if len(values) < 100 or np.any(values <= 0):
        return 0.5
    tau: list[float] = []
    lag_log: list[float] = []
    for lag in lags:
        differences = values[lag:] - values[:-lag]
        scale = float(np.sqrt(np.std(differences)))
        if not np.isfinite(scale) or scale <= 0:
            continue
        tau.append(np.log(scale))
        lag_log.append(np.log(lag))
    if len(tau) < 3:
        return 0.5
    slope = np.polyfit(lag_log, tau, 1)[0]
    return float(slope * 2.0)


def calculate_hurst(series: Iterable[float], lags=(2, 4, 8, 16)) -> float | None:
    """Variance-time point estimate; no significance claim is implied."""
    values = np.asarray(series, dtype=float)
    if len(values) < max(lags) * 4 or np.any(values <= 0):
        return None
    log_price = np.log(values)
    x: list[float] = []
    y: list[float] = []
    for lag in lags:
        increments = log_price[lag:] - log_price[:-lag]
        variance = float(np.var(increments, ddof=1))
        if not np.isfinite(variance) or variance <= 0:
            continue
        x.append(np.log(float(lag)))
        y.append(np.log(variance))
    if len(x) < 3:
        return None
    return float(np.polyfit(x, y, 1)[0] / 2.0)


def calculate_variance_ratio(series: Iterable[float], q: int = 5) -> float | None:
    values = np.asarray(series, dtype=float)
    if q < 2 or len(values) < q * 4 or np.any(values <= 0):
        return None
    returns = np.diff(np.log(values))
    var_one = float(np.var(returns, ddof=1))
    if not np.isfinite(var_one) or var_one <= 0:
        return None
    q_returns = np.convolve(returns, np.ones(q), mode="valid")
    var_q = float(np.var(q_returns, ddof=1)) / q
    return float(var_q / var_one)


def calibrate_ou_process(series: Iterable[float], dt: float = 1.0) -> dict:
    """Fit AR(1) X_t=a+bX_(t-1) and map valid 0<b<1 to OU terms."""
    values = np.asarray(series, dtype=float)
    if dt <= 0 or len(values) < 20 or not np.isfinite(values).all():
        return {
            "valid": False,
            "a": None,
            "b": None,
            "theta": None,
            "mu": None,
            "sigma_eq": None,
            "half_life": None,
        }
    x = values[:-1]
    y = values[1:]
    design = np.column_stack([np.ones(len(x)), x])
    a, b = np.linalg.lstsq(design, y, rcond=None)[0]
    # Numerical least-squares can return 0.9999999999999999 for a unit root.
    # Treat a near-unit root as non-mean-reverting instead of manufacturing an
    # enormous but finite half-life.
    if not np.isfinite(b) or b <= 0.0 or b >= 1.0 - 1e-12:
        return {
            "valid": False,
            "a": float(a) if np.isfinite(a) else None,
            "b": float(b) if np.isfinite(b) else None,
            "theta": None,
            "mu": None,
            "sigma_eq": None,
            "half_life": None,
        }
    theta = -np.log(b) / dt
    mu = a / (1.0 - b)
    residuals = y - (a + b * x)
    sigma_residual = float(np.std(residuals, ddof=0))
    denominator = 1.0 - b * b
    if theta <= 0 or denominator <= 0:
        return {
            "valid": False,
            "a": float(a),
            "b": float(b),
            "theta": None,
            "mu": None,
            "sigma_eq": None,
            "half_life": None,
        }
    return {
        "valid": True,
        "a": float(a),
        "b": float(b),
        "theta": float(theta),
        "mu": float(mu),
        "sigma_eq": float(sigma_residual / np.sqrt(denominator)),
        "half_life": float(-np.log(2.0) / np.log(b) * dt),
    }


def select_symbol(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if "symbol" not in frame.columns:
        raise RuntimeError("MISSING SYMBOL COLUMN")
    selected = frame.loc[frame["symbol"].astype(str) == symbol].copy()
    if selected.empty:
        raise RuntimeError(f"SYMBOL NOT FOUND: {symbol}")
    if "time_utc" in selected.columns:
        selected["time_utc"] = pd.to_datetime(selected["time_utc"], utc=True)
        selected = selected.sort_values("time_utc").reset_index(drop=True)
    if not selected["symbol"].eq(symbol).all():
        raise RuntimeError("MIXED SYMBOL IDENTITY AFTER FILTER")
    return selected


def contiguous_daily_sessions(
    frame: pd.DataFrame,
    start_hour: int,
    end_hour: int,
    min_rows: int = 300,
) -> list[pd.DataFrame]:
    """Return complete, one-minute-contiguous UTC sessions without stitching."""
    if not 0 <= start_hour <= 23 or not 1 <= end_hour <= 24 or start_hour >= end_hour:
        raise ValueError("only non-wrapping UTC sessions are supported")
    if "time_utc" not in frame.columns:
        raise RuntimeError("MISSING TIME_UTC COLUMN")
    source = frame.copy()
    source["time_utc"] = pd.to_datetime(source["time_utc"], utc=True)
    source = source.sort_values("time_utc")
    hours = source["time_utc"].dt.hour
    source = source.loc[(hours >= start_hour) & (hours < end_hour)].copy()
    sessions: list[pd.DataFrame] = []
    for _, group in source.groupby(source["time_utc"].dt.date, sort=True):
        group = group.drop_duplicates("time_utc", keep=False).reset_index(drop=True)
        if len(group) < min_rows:
            continue
        gaps = group["time_utc"].diff().dropna()
        if not gaps.eq(pd.Timedelta(minutes=1)).all():
            continue
        sessions.append(group)
    return sessions


def inspect_flow_contract(columns: Iterable[str]) -> dict:
    available = {str(column).lower() for column in columns}
    vpin_cvd_required = {"trade_side", "trade_volume"}
    lob_ofi_required = {"bid_size", "ask_size"}
    vpin_cvd = vpin_cvd_required.issubset(available)
    lob_ofi = lob_ofi_required.issubset(available)
    return {
        "available_columns": sorted(available),
        "vpin_cvd_required": sorted(vpin_cvd_required),
        "lob_ofi_required": sorted(lob_ofi_required),
        "vpin_cvd_available": bool(vpin_cvd),
        "lob_ofi_available": bool(lob_ofi),
        "all_required_available": bool(vpin_cvd and lob_ofi),
        "tick_volume_is_true_flow": False,
    }


def evaluate_preflight(
    *,
    identity_ok: bool,
    coverage_ok: bool,
    target_evidence_ok: bool,
    flow_contract_ok: bool,
    estimator_contract_ok: bool,
    async_kernel_ready: bool,
) -> dict:
    checks = {
        "source_identity": identity_ok,
        "history_coverage": coverage_ok,
        "target_symbol_evidence": target_evidence_ok,
        "true_flow_contract": flow_contract_ok,
        "estimator_and_arbitration_contract": estimator_contract_ok,
        "production_async_kernel": async_kernel_ready,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    survivor = not blockers
    return {
        "checks": checks,
        "blockers": blockers,
        "verdict": VERDICT_SURVIVOR if survivor else VERDICT_BLOCKED,
        "authority": {
            "mql5_build_authorized": survivor,
            "compile_authorized": survivor,
            "mt5_authorized": False,
            "model0_authorized": False,
            "model4_authorized": False,
            "economics_authorized": False,
            "optimization_authorized": False,
            "holdout_authorized": False,
            "promotion_eligible": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
        },
    }


def _summary(values: Iterable[float | None]) -> dict:
    clean = np.asarray(
        [float(value) for value in values if value is not None and np.isfinite(value)],
        dtype=float,
    )
    if len(clean) == 0:
        return {
            "count": 0,
            "min": None,
            "p10": None,
            "median": None,
            "p90": None,
            "max": None,
        }
    return {
        "count": int(len(clean)),
        "min": float(np.min(clean)),
        "p10": float(np.quantile(clean, 0.10)),
        "median": float(np.median(clean)),
        "p90": float(np.quantile(clean, 0.90)),
        "max": float(np.max(clean)),
    }


def _legacy_tail_metrics(frame: pd.DataFrame) -> dict:
    prices = pd.to_numeric(frame["close"], errors="coerce").dropna().to_numpy(float)
    sample_10k = prices[-10000:]
    sample_1440 = prices[-1440:]
    return {
        "rows_used_hurst_vr": int(len(sample_10k)),
        "rows_used_ou": int(len(sample_1440)),
        "hurst_legacy": legacy_calculate_hurst(sample_10k),
        "variance_ratio_q5": calculate_variance_ratio(sample_10k, 5),
        "variance_ratio_q20": calculate_variance_ratio(sample_10k, 20),
        "ou_ar1": calibrate_ou_process(sample_1440),
    }


def _daily_session_summary(frame: pd.DataFrame, start_hour: int, end_hour: int) -> dict:
    sessions = contiguous_daily_sessions(frame, start_hour, end_hour, min_rows=300)
    hurst_values: list[float | None] = []
    vr_values: list[float | None] = []
    half_lives: list[float | None] = []
    range_gate = 0
    trend_gate = 0
    for session in sessions:
        prices = pd.to_numeric(session["close"], errors="coerce").dropna().to_numpy(float)
        hurst = calculate_hurst(prices)
        vr = calculate_variance_ratio(prices, 5)
        ou = calibrate_ou_process(prices)
        hurst_values.append(hurst)
        vr_values.append(vr)
        half_lives.append(ou["half_life"] if ou["valid"] else None)
        if hurst is not None and vr is not None:
            range_gate += int(hurst < 0.45 and vr < 1.0)
            trend_gate += int(hurst > 0.55 and vr > 1.5)
    count = len(sessions)
    return {
        "nonstitched_complete_session_days": count,
        "hurst_variance_time": _summary(hurst_values),
        "variance_ratio_q5": _summary(vr_values),
        "ou_half_life_m1_bars": _summary(half_lives),
        "range_master_gate_days": int(range_gate),
        "trend_master_gate_days": int(trend_gate),
        "range_master_gate_share": float(range_gate / count) if count else 0.0,
        "trend_master_gate_share": float(trend_gate / count) if count else 0.0,
    }


def _verify_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA256 MISMATCH: {actual}")


def run_preflight(output_dir: Path) -> dict:
    _verify_hash(PREFLIGHT_PLAN, PREFLIGHT_PLAN_SHA256, "PREFLIGHT PLAN")
    if SUPPLIED_PLAN is None:
        raise RuntimeError(
            "SUPPLIED PLAN is not configured. Set "
            f"{_SUPPLIED_PLAN_ENV}=<path to final_ea_build_plan.md>. The old "
            r"hardcoded C:\Users\ADMIN\.gemini\... path was removed 2026-08-31; "
            "it belongs to a machine that is not this one."
        )
    _verify_hash(SUPPLIED_PLAN, SUPPLIED_PLAN_SHA256, "SUPPLIED PLAN")
    _verify_hash(TRIANGULAR_MANIFEST, TRIANGULAR_MANIFEST_SHA256, "TRIANGULAR MANIFEST")
    _verify_hash(TRIANGULAR_DATA, TRIANGULAR_DATA_SHA256, "TRIANGULAR DATA")
    _verify_hash(EURUSD_MANIFEST, EURUSD_MANIFEST_SHA256, "EURUSD MANIFEST")

    triangular_manifest = json.loads(TRIANGULAR_MANIFEST.read_text(encoding="utf-8"))
    design = pd.read_parquet(
        TRIANGULAR_DATA, columns=["symbol", "time_utc", "close"]
    )
    design["symbol"] = design["symbol"].astype(str)
    design["time_utc"] = pd.to_datetime(design["time_utc"], utc=True)
    design = design.sort_values(["symbol", "time_utc"]).reset_index(drop=True)

    unfiltered_tail = design.tail(10000)
    unfiltered_tail_symbols = sorted(unfiltered_tail["symbol"].unique().tolist())
    per_symbol = {}
    filtered_frames = {}
    for symbol in ("EURJPY", "EURUSD", "USDJPY"):
        selected = select_symbol(design, symbol)
        filtered_frames[symbol] = selected
        per_symbol[symbol] = {
            "rows": int(len(selected)),
            "first_time_utc": selected["time_utc"].min().isoformat(),
            "last_time_utc": selected["time_utc"].max().isoformat(),
            "legacy_tail_metrics": _legacy_tail_metrics(selected),
        }

    eurjpy = filtered_frames["EURJPY"]
    eurjpy_sessions = {
        "asian_00_06_utc": _daily_session_summary(eurjpy, 0, 6),
        "london_07_13_utc": _daily_session_summary(eurjpy, 7, 13),
    }

    eurusd_schema = pq.ParquetFile(EURUSD_DATA).schema_arrow.names
    flow_contract = inspect_flow_contract(eurusd_schema)

    declared_eurjpy = triangular_manifest["per_symbol"]["EURJPY"]
    identity_ok = bool(
        triangular_manifest["row_count"] == declared_eurjpy["rows"]
        and unfiltered_tail_symbols == ["EURJPY"]
    )
    coverage_ok = bool(
        triangular_manifest["design_years"] == list(range(2016, 2025))
    )
    target_evidence_ok = False
    estimator_contract_ok = False
    async_kernel_ready = False
    routing = evaluate_preflight(
        identity_ok=identity_ok,
        coverage_ok=coverage_ok,
        target_evidence_ok=target_evidence_ok,
        flow_contract_ok=bool(flow_contract["all_required_available"]),
        estimator_contract_ok=estimator_contract_ok,
        async_kernel_ready=async_kernel_ready,
    )

    artifact = {
        "schema_version": "vras_v4_plan_preflight.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "stage": "P0_OUTCOME_BLIND_PLAN_AND_DATA_CAPABILITY_PREFLIGHT",
        "trial_index": 1,
        "trial_universe": 1,
        "preflight_plan_path": str(PREFLIGHT_PLAN.relative_to(WORKSPACE)).replace("\\", "/"),
        "preflight_plan_sha256": PREFLIGHT_PLAN_SHA256,
        "supplied_plan_path": str(SUPPLIED_PLAN) if SUPPLIED_PLAN else None,
        "supplied_plan_sha256": SUPPLIED_PLAN_SHA256,
        "original_runner_sha256": ORIGINAL_RUNNER_SHA256,
        "source": {
            "triangular_manifest_path": str(TRIANGULAR_MANIFEST.relative_to(WORKSPACE)).replace("\\", "/"),
            "triangular_manifest_sha256": TRIANGULAR_MANIFEST_SHA256,
            "triangular_data_path": str(TRIANGULAR_DATA.relative_to(WORKSPACE)).replace("\\", "/"),
            "triangular_data_sha256": TRIANGULAR_DATA_SHA256,
            "manifest_row_count": int(triangular_manifest["row_count"]),
            "manifest_symbols": list(triangular_manifest["symbols"]),
            "manifest_design_years": list(triangular_manifest["design_years"]),
            "manifest_sealed_validation_years": list(
                triangular_manifest["sealed_validation_years"]
            ),
            "sealed_validation_rows_loaded": 0,
        },
        "forensic_reproduction": {
            "unfiltered_tail_symbols": unfiltered_tail_symbols,
            "unfiltered_tail_metrics": _legacy_tail_metrics(design),
            "per_symbol_corrected": per_symbol,
            "eurjpy_nonstitched_sessions": eurjpy_sessions,
        },
        "plan_claim_audit": {
            "claimed_dataset": "5.5 million EURJPY M1 bars, 2016-2024",
            "actual_dataset": (
                "5,580,755 combined EURJPY/EURUSD/USDJPY DESIGN rows, 2016-2020"
            ),
            "claimed_headline_hurst": 0.4612,
            "claimed_headline_vr_q5": 0.8654,
            "claimed_headline_ou_half_life_minutes": 89.43,
            "headline_values_source_symbol": (
                unfiltered_tail_symbols[0] if len(unfiltered_tail_symbols) == 1 else "MIXED"
            ),
            "proposed_ea_symbol": "EURUSD",
            "cross_symbol_transfer_authorized": False,
        },
        "eurusd_flow_contract": flow_contract,
        "estimator_contract": {
            "window_defined_in_supplied_plan": False,
            "confidence_interval_defined": False,
            "null_and_power_defined": False,
            "rolling_stability_gate_defined": False,
            "engine_arbitration_defined": False,
            "valid": False,
        },
        "async_execution_contract": {
            "current_shared_kernel_mutation_default": "DISABLED",
            "durable_intent_restart_proof": False,
            "behavioral_callback_fixture_suite": False,
            "timeout_may_reset_idle_on_empty_position_scan_in_supplied_plan": True,
            "production_ready": False,
        },
        "checks": routing["checks"],
        "blockers": routing["blockers"],
        "verdict": routing["verdict"],
        "authority": routing["authority"],
        "outcome_blind_attestation": {
            "trade_outcomes_read": False,
            "pnl_computed": False,
            "profit_factor_computed": False,
            "mfe_mae_computed": False,
            "mt5_launched": False,
            "orders_submitted": False,
            "holdout_opened": False,
        },
        "failure_radius": (
            "The supplied three-engine V4 plan and its current empirical/data/execution "
            "contract are invalid before EA build. This does not prove that a future "
            "atomic strategy using a correctly identified symbol and genuine causal "
            "flow source has no edge."
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "preflight_result.json"
    output_path.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=(
            WORKSPACE
            / "03. EA Developer"
            / "EA_VRAS_RegimeAdaptiveScalperV4"
            / "research"
            / "evidence"
            / "HYP-VRAS-EURUSD-M5-015_PREFLIGHT"
        ),
    )
    args = parser.parse_args()
    artifact = run_preflight(args.output_dir)
    print(
        json.dumps(
            {
                "hypothesis_id": artifact["hypothesis_id"],
                "verdict": artifact["verdict"],
                "unfiltered_tail_symbols": artifact["forensic_reproduction"][
                    "unfiltered_tail_symbols"
                ],
                "blockers": artifact["blockers"],
                "mql5_build_authorized": artifact["authority"][
                    "mql5_build_authorized"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
