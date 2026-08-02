"""Outcome-blind USDJPY M5 Asian-session OU design confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


WORKSPACE = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-VRAS-USDJPY-M5-001"
AUTHORITY_PATH = Path(__file__).with_name(
    "HYP-VRAS-USDJPY-M5-001_P0_RUN_AUTHORITY.json"
)
PASS_VERDICT = "SURVIVE_P0_USDJPY_M5_ASIAN_OU_BUILD_FREEZE_AUTHORIZED"
FAIL_VERDICT = "PARK_P0_USDJPY_M5_ASIAN_OU_DESIGN_GATE_FAIL_NO_OUTCOME_READ"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def calculate_hurst(series: np.ndarray, lags: tuple[int, ...] = (2, 4, 8, 16)) -> float | None:
    values = np.asarray(series, dtype=float)
    if len(values) < max(lags) * 4 or not np.isfinite(values).all() or np.any(values <= 0):
        return None
    log_price = np.log(values)
    x: list[float] = []
    y: list[float] = []
    for lag in lags:
        increments = log_price[lag:] - log_price[:-lag]
        variance = float(np.var(increments, ddof=1))
        if np.isfinite(variance) and variance > 0:
            x.append(math.log(float(lag)))
            y.append(math.log(variance))
    if len(x) < 3:
        return None
    return float(np.polyfit(x, y, 1)[0] / 2.0)


def calculate_variance_ratio(series: np.ndarray, q: int = 5) -> float | None:
    values = np.asarray(series, dtype=float)
    if q < 2 or len(values) < q * 4 or not np.isfinite(values).all() or np.any(values <= 0):
        return None
    returns = np.diff(np.log(values))
    one_bar_variance = float(np.var(returns, ddof=1))
    if not np.isfinite(one_bar_variance) or one_bar_variance <= 0:
        return None
    q_returns = np.convolve(returns, np.ones(q), mode="valid")
    return float((np.var(q_returns, ddof=1) / q) / one_bar_variance)


def calibrate_ou(series: np.ndarray) -> dict[str, float | bool | None]:
    values = np.asarray(series, dtype=float)
    invalid = {"valid": False, "a": None, "b": None, "half_life_m5_bars": None}
    if len(values) < 20 or not np.isfinite(values).all():
        return invalid
    x = values[:-1]
    y = values[1:]
    design = np.column_stack([np.ones(len(x)), x])
    a, b = np.linalg.lstsq(design, y, rcond=None)[0]
    if not np.isfinite(a) or not np.isfinite(b) or b <= 0.0 or b >= 1.0 - 1e-12:
        return {"valid": False, "a": float(a), "b": float(b), "half_life_m5_bars": None}
    half_life = -math.log(2.0) / math.log(float(b))
    if not np.isfinite(half_life) or half_life <= 0:
        return {"valid": False, "a": float(a), "b": float(b), "half_life_m5_bars": None}
    return {
        "valid": True,
        "a": float(a),
        "b": float(b),
        "half_life_m5_bars": float(half_life),
    }


def extract_sessions(frame: pd.DataFrame, min_rows: int = 80) -> list[pd.DataFrame]:
    source = frame.copy()
    source["time_utc"] = pd.to_datetime(source["time_utc"], utc=True)
    source = source.sort_values("time_utc").drop_duplicates("time_utc", keep=False)
    minute = source["time_utc"].dt.hour * 60 + source["time_utc"].dt.minute
    source = source.loc[(minute >= 22 * 60 + 15) | (minute < 5 * 60 + 30)].copy()
    source["session_key"] = (source["time_utc"] + pd.Timedelta(minutes=105)).dt.date
    sessions: list[pd.DataFrame] = []
    for _, group in source.groupby("session_key", sort=True):
        group = group.sort_values("time_utc").reset_index(drop=True)
        if len(group) < min_rows:
            continue
        gaps = group["time_utc"].diff().dropna()
        if not gaps.eq(pd.Timedelta(minutes=5)).all():
            continue
        sessions.append(group)
    return sessions


def bootstrap_median_interval(values: np.ndarray, rng: np.random.Generator, reps: int = 5000) -> dict[str, float]:
    clean = np.asarray(values, dtype=float)
    clean = clean[np.isfinite(clean)]
    if len(clean) == 0:
        raise RuntimeError("EMPTY BOOTSTRAP INPUT")
    medians = np.empty(reps, dtype=float)
    for start in range(0, reps, 250):
        count = min(250, reps - start)
        samples = rng.choice(clean, size=(count, len(clean)), replace=True)
        medians[start : start + count] = np.median(samples, axis=1)
    return {
        "median": float(np.median(clean)),
        "lower_95": float(np.quantile(medians, 0.025)),
        "upper_95": float(np.quantile(medians, 0.975)),
    }


def wilson_lower(successes: int, total: int, z: float = 1.959963984540054) -> float:
    if total <= 0:
        return 0.0
    p = successes / total
    denominator = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    return float((centre - margin) / denominator)


def evaluate_gates(
    *,
    session_count: int,
    yearly_counts: dict[str, int],
    hurst_ci: dict[str, float],
    vr_ci: dict[str, float],
    ou_valid_lower: float,
    half_life_ci: dict[str, float],
) -> dict[str, bool]:
    return {
        "session_count_ge_1000": session_count >= 1000,
        "each_year_count_ge_180": all(yearly_counts.get(str(year), 0) >= 180 for year in range(2016, 2021)),
        "hurst_median_upper95_lt_0_50": hurst_ci["upper_95"] < 0.50,
        "vr5_median_upper95_lt_1_00": vr_ci["upper_95"] < 1.00,
        "ou_valid_share_wilson_lower95_ge_0_50": ou_valid_lower >= 0.50,
        "ou_half_life_median_ci_within_1_36_m5_bars": (
            half_life_ci["lower_95"] >= 1.0 and half_life_ci["upper_95"] <= 36.0
        ),
    }


def _verify_authority(authority: dict) -> Path:
    if authority["hypothesis_id"] != HYPOTHESIS_ID:
        raise RuntimeError("AUTHORITY HYPOTHESIS MISMATCH")
    bindings = authority["bindings"]
    for name in ("plan", "probe", "test", "dataset"):
        path = WORKSPACE / bindings[name]["path"]
        if not path.is_file():
            raise RuntimeError(f"MISSING BINDING: {name}")
        actual = sha256_file(path)
        if actual != bindings[name]["sha256"]:
            raise RuntimeError(f"{name.upper()} SHA256 MISMATCH: {actual}")
    if not authority["authority"]["p0_probe_authorized"]:
        raise RuntimeError("P0 PROBE NOT AUTHORIZED")
    return WORKSPACE / bindings["dataset"]["path"]


def run(output_path: Path) -> dict:
    authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
    dataset_path = _verify_authority(authority)
    frame = pd.read_parquet(
        dataset_path,
        columns=["symbol", "timeframe", "time_utc", "close"],
    )
    frame["time_utc"] = pd.to_datetime(frame["time_utc"], utc=True)
    frame = frame.loc[
        (frame["time_utc"] >= "2016-01-04T00:00:00Z")
        & (frame["time_utc"] < "2021-01-01T00:00:00Z")
    ].copy()
    if frame.empty or not frame["symbol"].astype(str).eq("USDJPY").all():
        raise RuntimeError("USDJPY IDENTITY FAILURE")
    if not frame["timeframe"].astype(str).eq("M5").all():
        raise RuntimeError("M5 IDENTITY FAILURE")

    sessions = extract_sessions(frame)
    hurst_values: list[float] = []
    vr_values: list[float] = []
    half_lives: list[float] = []
    ou_valid = 0
    yearly_counts: dict[str, int] = {}
    for session in sessions:
        prices = pd.to_numeric(session["close"], errors="coerce").to_numpy(float)
        hurst = calculate_hurst(prices)
        vr = calculate_variance_ratio(prices, 5)
        ou = calibrate_ou(prices)
        if hurst is not None:
            hurst_values.append(hurst)
        if vr is not None:
            vr_values.append(vr)
        if bool(ou["valid"]):
            ou_valid += 1
            half_lives.append(float(ou["half_life_m5_bars"]))
        year = str(pd.Timestamp(session["time_utc"].iloc[-1]).year)
        yearly_counts[year] = yearly_counts.get(year, 0) + 1

    rng = np.random.default_rng(20260802)
    hurst_ci = bootstrap_median_interval(np.asarray(hurst_values), rng)
    vr_ci = bootstrap_median_interval(np.asarray(vr_values), rng)
    half_life_ci = bootstrap_median_interval(np.asarray(half_lives), rng)
    ou_valid_lower = wilson_lower(ou_valid, len(sessions))
    gates = evaluate_gates(
        session_count=len(sessions),
        yearly_counts=yearly_counts,
        hurst_ci=hurst_ci,
        vr_ci=vr_ci,
        ou_valid_lower=ou_valid_lower,
        half_life_ci=half_life_ci,
    )
    passed = all(gates.values())
    result = {
        "schema_version": "vras_usdjpy_m5_p0_design_confirmation.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "stage": "P0_OUTCOME_BLIND_TARGET_SYMBOL_TIMEFRAME_CONFIRMATION",
        "source": {
            "path": authority["bindings"]["dataset"]["path"],
            "sha256": authority["bindings"]["dataset"]["sha256"],
            "symbol": "USDJPY",
            "timeframe": "M5",
            "design_from_utc": "2016-01-04T00:00:00Z",
            "design_to_exclusive_utc": "2021-01-01T00:00:00Z",
            "design_rows_read": int(len(frame)),
        },
        "metrics": {
            "eligible_session_count": len(sessions),
            "yearly_session_counts": yearly_counts,
            "hurst": hurst_ci,
            "variance_ratio_q5": vr_ci,
            "ou_valid_sessions": ou_valid,
            "ou_valid_share": float(ou_valid / len(sessions)) if sessions else 0.0,
            "ou_valid_share_wilson_lower_95": ou_valid_lower,
            "ou_half_life_m5_bars": half_life_ci,
        },
        "gates": gates,
        "verdict": PASS_VERDICT if passed else FAIL_VERDICT,
        "authority_after_verdict": {
            "atomic_ou_ea_build_contract_may_be_frozen": passed,
            "mql5_source_authorized": False,
            "compile_authorized": False,
            "model0_authorized": False,
            "validation_authorized": False,
            "holdout_authorized": False,
            "optimization_authorized": False,
            "promotion_eligible": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
        },
        "outcome_blind_attestation": {
            "validation_2021_2024_opened": False,
            "holdout_2025plus_opened": False,
            "trade_paths_simulated": 0,
            "costs_computed": 0,
            "pnl_computed": False,
            "mt5_launched": False,
            "orders_submitted": 0,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            Path(__file__).parent
            / "evidence"
            / "HYP-VRAS-USDJPY-M5-001_P0"
            / "design_confirmation.json"
        ),
    )
    args = parser.parse_args()
    result = run(args.output)
    print(json.dumps({"hypothesis_id": HYPOTHESIS_ID, "verdict": result["verdict"], "gates": result["gates"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
