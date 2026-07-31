#!/usr/bin/env python3
"""One-shot TRAIN evaluator for HYP-LOMX-MULTI-M1-001.

The evaluator is import-inert and fail-closed.  It accepts only the frozen
2016-2020 broker source, accounts for every executed arm in DSR, applies the
predeclared cost proxy, and never reads validation or holdout data.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-LOMX-MULTI-M1-001"
ATTEMPT_ID = "LOMX001-TRAIN-EVAL-001"
PLAN_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "HYP-LOMX-MULTI-M1-001_TRAIN_PROBE_PLAN_V2.md"
)
SCRIPT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "evaluate_lomx_001_train.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)

TRAIN_YEARS = (2016, 2017, 2018, 2019, 2020)
FORBIDDEN_YEAR_MIN = 2021
N_PERMUTATIONS = 5_000
PERMUTATION_SEED = 5_601_001
N_DSR_TRIALS = 23
HOLM_FAMILY_SIZE = 10
COST_SPREAD_MULTIPLIER = 1.25
COST_TIERS = (1.0, 1.5, 2.0)
MIN_TRADES = 1_000
MIN_SIGN_COUNT = 200
MIN_CADENCE = 2.0
MAX_CADENCE = 5.0
MIN_PF_X1 = 1.30
MIN_PF_X15 = 1.25
MIN_PF_X2 = 1.00
MIN_POSITIVE_YEARS = 4
MAX_POSITIVE_YEAR_SHARE = 0.25
MIN_DSR = 0.95
MAX_HOLM_P = 0.05

SET_WINDOWS = {
    "MIDDAY": ("open_0830", "open_1200", "spread_0830_points", "spread_1200_points"),
    "LATE_FIX": ("open_1530", "open_1600", "spread_1530_points", "spread_1600_points"),
    "FULL_SESSION": ("open_0830", "open_1630", "spread_0830_points", "spread_1630_points"),
}
PRIMARY_POLARITY = {"EURUSD": 1, "GBPUSD": -1, "EURJPY": 1, "USDJPY": 1}
SURVIVOR_PRIORITY = (
    "USDJPY_MIDDAY_PRIMARY",
    "EURJPY_MIDDAY_PRIMARY",
    "EURJPY_LATE_FIX_PRIMARY",
    "EURJPY_FULL_SESSION_PRIMARY",
    "GBPUSD_MIDDAY_PRIMARY",
    "GBPUSD_LATE_FIX_PRIMARY",
    "GBPUSD_FULL_SESSION_PRIMARY",
    "EURUSD_MIDDAY_PRIMARY",
    "EURUSD_LATE_FIX_PRIMARY",
    "EURUSD_FULL_SESSION_PRIMARY",
)


class ContractError(RuntimeError):
    """Fail-closed authority, source, or evaluation violation."""


@dataclass(frozen=True)
class Arm:
    arm_id: str
    symbol: str
    set_name: str
    polarity: int
    role: str
    selectable: bool
    matched_primary_id: str | None = None


def build_arms() -> tuple[Arm, ...]:
    primary: list[Arm] = []
    for symbol in ("EURUSD", "GBPUSD", "EURJPY"):
        for set_name in SET_WINDOWS:
            primary.append(
                Arm(
                    f"{symbol}_{set_name}_PRIMARY",
                    symbol,
                    set_name,
                    PRIMARY_POLARITY[symbol],
                    "PRIMARY",
                    True,
                )
            )
    primary.append(Arm("USDJPY_MIDDAY_PRIMARY", "USDJPY", "MIDDAY", 1, "PRIMARY", True))
    nulls = [
        Arm(f"XAUUSD_{set_name}_EXTERNAL_NULL", "XAUUSD", set_name, 1, "EXTERNAL_NULL", False)
        for set_name in SET_WINDOWS
    ]
    reverse = [
        Arm(
            item.arm_id.replace("_PRIMARY", "_REVERSE_CONTROL"),
            item.symbol,
            item.set_name,
            -item.polarity,
            "REVERSE_CONTROL",
            False,
            matched_primary_id=item.arm_id,
        )
        for item in primary
    ]
    arms = tuple(primary + nulls + reverse)
    if len(primary) != HOLM_FAMILY_SIZE or len(arms) != N_DSR_TRIALS:
        raise ContractError("arm accounting invariant failed")
    return arms


ARMS = build_arms()


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("non-canonical JSON value") from exc


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_d_path(path: Path, *, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D: {resolved}")
    return resolved


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.exists():
        raise ContractError(f"stale temporary file: {tmp}")
    tmp.write_bytes(payload)
    tmp.replace(path)


def reserve_directory(path: Path) -> Path:
    path = require_d_path(path, label="output directory")
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError(f"one-shot output already exists: {path}") from exc
    return path


def latest_registry_row(registry_path: Path) -> tuple[dict[str, object], str]:
    matches: list[tuple[dict[str, object], bytes]] = []
    for raw in registry_path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw.decode("utf-8"))
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            matches.append((row, raw))
    if not matches:
        raise ContractError("matching registry row absent")
    row, raw = matches[-1]
    return row, sha256_bytes(raw + b"\n")


def _require_rel_file(workspace: Path, rel: str, expected_sha: str, label: str) -> Path:
    path = require_d_path(workspace / rel, label=label)
    if not path.is_file():
        raise ContractError(f"{label} missing: {path}")
    if sha256_file(path) != expected_sha.upper():
        raise ContractError(f"{label} SHA mismatch")
    return path


def verify_authority(workspace: Path, reviewed_registry_sha: str) -> dict[str, object]:
    plan = workspace / PLAN_REL
    script = workspace / SCRIPT_REL
    registry = workspace / REGISTRY_REL
    for path in (plan, script, registry):
        if not path.is_file():
            raise ContractError(f"required authority file missing: {path}")
    row, row_sha = latest_registry_row(registry)
    if row_sha != reviewed_registry_sha.upper():
        raise ContractError("reviewed registry SHA does not match latest row")
    if row.get("state") != "probe":
        raise ContractError("TRAIN evaluation requires latest state=probe")
    if row.get("prereg_path") != PLAN_REL:
        raise ContractError("registry prereg path mismatch")
    if str(row.get("prereg_sha256", "")).upper() != sha256_file(plan):
        raise ContractError("registry prereg hash mismatch")
    if row.get("source_path") is not None or row.get("source_hash") is not None:
        raise ContractError("research probe must not impersonate canonical EA source")
    validation = row.get("validation") or {}
    if validation.get("reviewed_evaluator_path") != SCRIPT_REL:
        raise ContractError("registry reviewed evaluator path mismatch")
    if str(validation.get("reviewed_evaluator_sha256", "")).upper() != sha256_file(script):
        raise ContractError("registry reviewed evaluator hash mismatch")
    required_flags = {
        "source_run_authorized": False,
        "economics_authorized": True,
        "research_validation_access_authorized": False,
        "research_holdout_access_authorized": False,
        "mql5_build_authorized": False,
        "model0_authorized": False,
    }
    for key, expected in required_flags.items():
        if validation.get(key) is not expected:
            raise ContractError(f"authority flag mismatch: {key}")
    manifest_rel = str(validation.get("train_source_manifest_path", ""))
    parquet_rel = str(validation.get("train_source_parquet_path", ""))
    manifest = _require_rel_file(
        workspace,
        manifest_rel,
        str(validation.get("train_source_manifest_sha256", "")),
        "source manifest",
    )
    parquet = _require_rel_file(
        workspace,
        parquet_rel,
        str(validation.get("train_source_parquet_sha256", "")),
        "source parquet",
    )
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_data.get("hypothesis_id") != HYPOTHESIS_ID:
        raise ContractError("source manifest hypothesis mismatch")
    if manifest_data.get("split") != "TRAIN" or tuple(manifest_data.get("train_years", ())) != TRAIN_YEARS:
        raise ContractError("source manifest split mismatch")
    if manifest_data.get("parquet_path") != parquet_rel:
        raise ContractError("source manifest parquet path mismatch")
    if str(manifest_data.get("parquet_sha256", "")).upper() != sha256_file(parquet):
        raise ContractError("source manifest parquet SHA mismatch")
    return {
        "registry_row_sha256": row_sha,
        "plan_sha256": sha256_file(plan),
        "script_sha256": sha256_file(script),
        "source_manifest_path": manifest_rel,
        "source_manifest_sha256": sha256_file(manifest),
        "source_parquet_path": parquet_rel,
        "source_parquet_sha256": sha256_file(parquet),
    }


def validate_train_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "symbol", "local_date", "open_0800", "open_0830", "open_1200",
        "open_1530", "open_1600", "open_1630", "spread_0830_points",
        "spread_1200_points", "spread_1530_points", "spread_1600_points",
        "spread_1630_points", "point",
    }
    if not required.issubset(frame.columns):
        raise ContractError("TRAIN parquet schema mismatch")
    result = frame.copy()
    dates = pd.to_datetime(result["local_date"], format="%Y-%m-%d", errors="raise")
    if (dates.dt.year >= FORBIDDEN_YEAR_MIN).any() or set(dates.dt.year.unique()) - set(TRAIN_YEARS):
        raise ContractError("forbidden non-TRAIN year in source")
    if result.duplicated(["symbol", "local_date"]).any():
        raise ContractError("duplicate symbol-date rows")
    numeric = [column for column in required if column not in {"symbol", "local_date"}]
    if not np.isfinite(result[numeric].to_numpy(dtype=float)).all():
        raise ContractError("non-finite source value")
    if (result[[column for column in numeric if column.startswith("open_")]] <= 0).any().any():
        raise ContractError("non-positive source price")
    if (result["point"] <= 0).any():
        raise ContractError("non-positive point geometry")
    result["year"] = dates.dt.year.astype(int)
    return result.sort_values(["symbol", "local_date"], kind="mergesort").reset_index(drop=True)


def simulate_arm(frame: pd.DataFrame, arm: Arm) -> pd.DataFrame:
    entry_col, exit_col, entry_spread_col, exit_spread_col = SET_WINDOWS[arm.set_name]
    part = frame.loc[frame["symbol"] == arm.symbol].copy()
    formation = np.log(part["open_0830"].to_numpy(float) / part["open_0800"].to_numpy(float))
    sign = np.sign(formation)
    part = part.loc[sign != 0].copy()
    sign = sign[sign != 0]
    entry = part[entry_col].to_numpy(float)
    exit_price = part[exit_col].to_numpy(float)
    gross_price = float(arm.polarity) * sign * (exit_price - entry)
    base_cost_price = COST_SPREAD_MULTIPLIER * np.maximum(
        part[entry_spread_col].to_numpy(float),
        part[exit_spread_col].to_numpy(float),
    ) * part["point"].to_numpy(float)
    trades = pd.DataFrame(
        {
            "arm_id": arm.arm_id,
            "role": arm.role,
            "symbol": arm.symbol,
            "set_name": arm.set_name,
            "local_date": part["local_date"].to_numpy(),
            "year": part["year"].to_numpy(int),
            "formation_sign": sign.astype(int),
            "direction": (float(arm.polarity) * sign).astype(int),
            "entry_price": entry,
            "exit_price": exit_price,
            "gross_return": gross_price / entry,
            "cost_x1_return": base_cost_price / entry,
        }
    )
    for tier in COST_TIERS:
        suffix = str(tier).replace(".", "p")
        trades[f"net_x{suffix}_return"] = trades["gross_return"] - tier * trades["cost_x1_return"]
    return trades


def profit_factor(values: np.ndarray) -> float | None:
    values = np.asarray(values, dtype=float)
    wins = float(values[values > 0].sum())
    losses = float(-values[values < 0].sum())
    if losses <= 0:
        return None
    return wins / losses


def sr_skew_kurt(values: np.ndarray) -> tuple[float | None, float | None, float | None]:
    series = pd.Series(np.asarray(values, dtype=float))
    if len(series) <= 3 or float(series.std(ddof=1)) == 0.0:
        return None, None, None
    return (
        float(series.mean() / series.std(ddof=1)),
        float(series.skew()),
        float(series.kurt() + 3.0),
    )


def sign_flip_pvalue(values: np.ndarray, *, seed: int, permutations: int = N_PERMUTATIONS) -> float:
    values = np.asarray(values, dtype=float)
    observed = float(values.mean())
    if len(values) == 0 or observed <= 0.0:
        return 1.0
    rng = np.random.default_rng(seed)
    exceed = 0
    remaining = permutations
    while remaining:
        batch = min(250, remaining)
        signs = rng.choice(np.array([-1.0, 1.0]), size=(batch, len(values)))
        means = (signs * values).mean(axis=1)
        exceed += int(np.count_nonzero(means >= observed))
        remaining -= batch
    return float((exceed + 1) / (permutations + 1))


def holm_adjust(raw_p: dict[str, float]) -> dict[str, float]:
    if len(raw_p) != HOLM_FAMILY_SIZE:
        raise ContractError("Holm family size mismatch")
    ordered = sorted(raw_p.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    size = len(ordered)
    for rank, (arm_id, value) in enumerate(ordered):
        running = max(running, (size - rank) * value)
        adjusted[arm_id] = min(1.0, running)
    return adjusted


def _stable_seed(arm_id: str) -> int:
    token = int(hashlib.sha256(arm_id.encode("ascii")).hexdigest()[:8], 16)
    return (PERMUTATION_SEED + token) % (2**32)


def summarize_arm(trades: pd.DataFrame, arm: Arm) -> dict[str, object]:
    x1 = trades["net_x1p0_return"].to_numpy(float)
    years = trades["year"].to_numpy(int)
    first = pd.Timestamp(str(trades["local_date"].iloc[0]))
    last = pd.Timestamp(str(trades["local_date"].iloc[-1]))
    elapsed_weeks = float(((last - first).days + 1) / 7.0)
    yearly_net = {str(year): float(x1[years == year].sum()) for year in TRAIN_YEARS}
    yearly_pf = {str(year): profit_factor(x1[years == year]) for year in TRAIN_YEARS}
    positive_values = [value for value in yearly_net.values() if value > 0.0]
    positive_year_share = (
        max(positive_values) / sum(positive_values) if positive_values else None
    )
    loo_pf = {
        str(year): profit_factor(x1[years != year])
        for year in TRAIN_YEARS
    }
    sr, skew, kurt = sr_skew_kurt(x1)
    return {
        "arm_id": arm.arm_id,
        "role": arm.role,
        "selectable": arm.selectable,
        "symbol": arm.symbol,
        "set_name": arm.set_name,
        "polarity": arm.polarity,
        "matched_primary_id": arm.matched_primary_id,
        "trades": int(len(trades)),
        "elapsed_calendar_weeks": elapsed_weeks,
        "trades_per_elapsed_week": float(len(trades) / elapsed_weeks),
        "positive_formation_count": int((trades["formation_sign"] > 0).sum()),
        "negative_formation_count": int((trades["formation_sign"] < 0).sum()),
        "pf_gross": profit_factor(trades["gross_return"].to_numpy(float)),
        "pf_x1": profit_factor(x1),
        "pf_x1p5": profit_factor(trades["net_x1p5_return"].to_numpy(float)),
        "pf_x2": profit_factor(trades["net_x2p0_return"].to_numpy(float)),
        "expectancy_x1": float(x1.mean()),
        "total_net_x1": float(x1.sum()),
        "yearly_net_x1": yearly_net,
        "yearly_pf_x1": yearly_pf,
        "positive_years": int(sum(value > 0.0 for value in yearly_net.values())),
        "max_positive_year_share": positive_year_share,
        "leave_one_year_out_pf_x1": loo_pf,
        "min_leave_one_year_out_pf_x1": min(
            value for value in loo_pf.values() if value is not None
        ) if any(value is not None for value in loo_pf.values()) else None,
        "sr_x1": sr,
        "skew_x1": skew,
        "non_excess_kurtosis_x1": kurt,
        "sign_flip_p_raw": sign_flip_pvalue(x1, seed=_stable_seed(arm.arm_id)),
    }


def _load_dsr(workspace: Path):
    path = workspace / DSR_REL
    spec = importlib.util.spec_from_file_location("lomx_canonical_dsr", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load canonical DSR module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_gates(metrics: list[dict[str, object]], workspace: Path) -> None:
    by_id = {str(item["arm_id"]): item for item in metrics}
    raw_p = {
        arm.arm_id: float(by_id[arm.arm_id]["sign_flip_p_raw"])
        for arm in ARMS if arm.selectable
    }
    adjusted = holm_adjust(raw_p)
    sharpe_values = [
        float(item["sr_x1"])
        for item in metrics if item["sr_x1"] is not None
    ]
    var_sr = float(np.var(sharpe_values, ddof=1)) if len(sharpe_values) > 1 else 0.0
    dsr_module = _load_dsr(workspace)
    for arm in ARMS:
        item = by_id[arm.arm_id]
        if item["sr_x1"] is None or item["skew_x1"] is None or item["non_excess_kurtosis_x1"] is None:
            dsr_value = 0.0
        else:
            dsr_value = float(
                dsr_module.dsr(
                    float(item["sr_x1"]),
                    int(item["trades"]),
                    float(item["skew_x1"]),
                    float(item["non_excess_kurtosis_x1"]),
                    var_sr,
                    N_DSR_TRIALS,
                )
            )
        item["dsr_trial_count"] = N_DSR_TRIALS
        item["var_sr_all_trials"] = var_sr
        item["dsr_x1"] = dsr_value
        item["holm_family_size"] = HOLM_FAMILY_SIZE if arm.selectable else None
        item["sign_flip_p_holm"] = adjusted.get(arm.arm_id)
        if not arm.selectable:
            item["gate_checks"] = {"selectable": False}
            item["all_gates_pass"] = False
            continue
        reverse_id = arm.arm_id.replace("_PRIMARY", "_REVERSE_CONTROL")
        reverse = by_id[reverse_id]
        loo = item["min_leave_one_year_out_pf_x1"]
        pf_x1 = item["pf_x1"]
        pf_x15 = item["pf_x1p5"]
        pf_x2 = item["pf_x2"]
        checks = {
            "minimum_trades": int(item["trades"]) >= MIN_TRADES,
            "cadence": MIN_CADENCE <= float(item["trades_per_elapsed_week"]) <= MAX_CADENCE,
            "both_formation_signs": min(
                int(item["positive_formation_count"]), int(item["negative_formation_count"])
            ) >= MIN_SIGN_COUNT,
            "pf_x1": pf_x1 is not None and float(pf_x1) > MIN_PF_X1,
            "pf_x1p5": pf_x15 is not None and float(pf_x15) >= MIN_PF_X15,
            "pf_x2": pf_x2 is not None and float(pf_x2) >= MIN_PF_X2,
            "positive_expectancy_x1": float(item["expectancy_x1"]) > 0.0,
            "positive_years": int(item["positive_years"]) >= MIN_POSITIVE_YEARS,
            "year_concentration": item["max_positive_year_share"] is not None
            and float(item["max_positive_year_share"]) <= MAX_POSITIVE_YEAR_SHARE,
            "leave_one_year_out": loo is not None and float(loo) > 1.0,
            "holm_significance": float(item["sign_flip_p_holm"]) <= MAX_HOLM_P,
            "dsr": dsr_value >= MIN_DSR,
            "beats_reverse_pf": pf_x1 is not None
            and reverse["pf_x1"] is not None
            and float(pf_x1) > float(reverse["pf_x1"]),
            "beats_reverse_expectancy": float(item["expectancy_x1"]) > float(reverse["expectancy_x1"]),
        }
        item["gate_checks"] = checks
        item["all_gates_pass"] = bool(all(checks.values()))


def choose_survivor(metrics: list[dict[str, object]]) -> str | None:
    passing = {str(item["arm_id"]) for item in metrics if item.get("all_gates_pass") is True}
    for arm_id in SURVIVOR_PRIORITY:
        if arm_id in passing:
            return arm_id
    return None


def render_charts(metrics: list[dict[str, object]], trades: pd.DataFrame, chart_dir: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    chart_dir.mkdir(parents=True, exist_ok=False)
    primary = pd.DataFrame([item for item in metrics if item["selectable"]]).set_index("arm_id")
    paths: list[Path] = []

    heat = primary.pivot(index="symbol", columns="set_name", values="pf_x1").reindex(
        index=["EURUSD", "GBPUSD", "EURJPY", "USDJPY"], columns=list(SET_WINDOWS)
    )
    fig, ax = plt.subplots(figsize=(9, 5))
    image = ax.imshow(heat.to_numpy(float), cmap="RdYlGn", vmin=0.6, vmax=1.4, aspect="auto")
    ax.set_xticks(range(len(heat.columns)), heat.columns)
    ax.set_yticks(range(len(heat.index)), heat.index)
    for row in range(len(heat.index)):
        for col in range(len(heat.columns)):
            value = heat.iloc[row, col]
            ax.text(col, row, "N/A" if pd.isna(value) else f"{value:.3f}", ha="center", va="center")
    ax.set_title("TRAIN 2016-2020: Profit Factor after x1 cost")
    fig.colorbar(image, ax=ax, label="PF x1")
    fig.tight_layout()
    path = chart_dir / "01_pf_heatmap.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(primary))
    for offset, (column, label) in enumerate((("pf_gross", "Gross"), ("pf_x1", "x1"), ("pf_x1p5", "x1.5"), ("pf_x2", "x2"))):
        ax.plot(x, primary[column].to_numpy(float), marker="o", label=label)
    ax.axhline(MIN_PF_X1, color="black", linestyle="--", linewidth=1, label="PF x1 target 1.30")
    ax.set_xticks(x, [idx.replace("_PRIMARY", "") for idx in primary.index], rotation=60, ha="right")
    ax.set_ylabel("Profit factor")
    ax.set_title("Cost stress by eligible arm")
    ax.legend(ncol=5)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = chart_dir / "02_cost_stress.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    paths.append(path)

    yearly = pd.DataFrame(primary["yearly_pf_x1"].to_dict()).T.reindex(columns=[str(y) for y in TRAIN_YEARS])
    fig, ax = plt.subplots(figsize=(9, 7))
    image = ax.imshow(yearly.to_numpy(float), cmap="RdYlGn", vmin=0.6, vmax=1.4, aspect="auto")
    ax.set_xticks(range(len(yearly.columns)), yearly.columns)
    ax.set_yticks(range(len(yearly.index)), [idx.replace("_PRIMARY", "") for idx in yearly.index])
    ax.set_title("Year-by-year PF x1 (stability check)")
    fig.colorbar(image, ax=ax, label="PF x1")
    fig.tight_layout()
    path = chart_dir / "03_yearly_pf_heatmap.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(11, 6))
    for arm_id in primary.index:
        part = trades.loc[trades["arm_id"] == arm_id]
        ax.plot(pd.to_datetime(part["local_date"]), part["net_x1p0_return"].cumsum(), label=arm_id.replace("_PRIMARY", ""), alpha=0.8)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_title("Cumulative net return by eligible arm (x1 research cost)")
    ax.set_ylabel("Cumulative simple return")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = chart_dir / "04_equity_curves.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    paths.append(path)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(primary["sign_flip_p_holm"], primary["dsr_x1"], c=primary["pf_x1"], cmap="viridis", s=90)
    for arm_id, row in primary.iterrows():
        ax.annotate(arm_id.replace("_PRIMARY", ""), (row["sign_flip_p_holm"], row["dsr_x1"]), fontsize=7)
    ax.axvline(MAX_HOLM_P, color="red", linestyle="--", label="Holm p = 0.05")
    ax.axhline(MIN_DSR, color="orange", linestyle="--", label="DSR = 0.95")
    ax.set_xlabel("Holm-adjusted one-sided sign-flip p")
    ax.set_ylabel("Deflated Sharpe Ratio")
    ax.set_title("Multiplicity controls (23 total trials; 10 selectable)")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    path = chart_dir / "05_multiplicity.png"
    fig.savefig(path, dpi=170)
    plt.close(fig)
    paths.append(path)
    return paths


def evaluate(workspace: Path, *, reviewed_registry_sha: str) -> dict[str, object]:
    workspace = require_d_path(workspace, label="workspace")
    authority = verify_authority(workspace, reviewed_registry_sha)
    output_root = reserve_directory(workspace / EVIDENCE_ROOT_REL)
    source_path = workspace / str(authority["source_parquet_path"])
    frame = validate_train_frame(pd.read_parquet(source_path))
    all_trades: list[pd.DataFrame] = []
    metrics: list[dict[str, object]] = []
    for arm in ARMS:
        trades = simulate_arm(frame, arm)
        if trades.empty:
            raise ContractError(f"zero trades for arm: {arm.arm_id}")
        all_trades.append(trades)
        metrics.append(summarize_arm(trades, arm))
    trades_frame = pd.concat(all_trades, ignore_index=True)
    apply_gates(metrics, workspace)
    survivor = choose_survivor(metrics)
    terminal_status = (
        "TRAIN_PASS_ONE_VALIDATION_CANDIDATE" if survivor else "TRAIN_KILL_NO_ELIGIBLE_ARM"
    )

    trades_path = output_root / "train_trades.parquet"
    trades_frame.to_parquet(trades_path, index=False, compression="zstd")
    metrics_payload = {
        "schema_version": "lomx_001_train_metrics.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "split": "TRAIN",
        "train_years": list(TRAIN_YEARS),
        "validation_years_accessed": [],
        "holdout_years_accessed": [],
        "cost_contract": {
            "status": "UNVERIFIED_RESEARCH_PROXY_NOT_PROMOTION_GRADE",
            "base_formula": "1.25 * max(entry_spread_points, exit_spread_points) * point",
            "tiers": list(COST_TIERS),
            "commission_included": False,
            "slippage_included": False,
        },
        "trial_accounting": {
            "total_dsr_trials": N_DSR_TRIALS,
            "selectable_holm_family": HOLM_FAMILY_SIZE,
            "primary_eligible": HOLM_FAMILY_SIZE,
            "external_null_non_selectable": 3,
            "reverse_controls_non_selectable": 10,
        },
        "survivor_priority": list(SURVIVOR_PRIORITY),
        "selected_survivor": survivor,
        "metrics": metrics,
        "authority": authority,
    }
    metrics_path = output_root / "train_metrics.json"
    atomic_write(metrics_path, canonical_json(metrics_payload) + b"\n")
    chart_paths = render_charts(metrics, trades_frame, output_root / "charts")
    log_lines = [
        f"hypothesis_id={HYPOTHESIS_ID}",
        f"attempt_id={ATTEMPT_ID}",
        "split=TRAIN years=2016,2017,2018,2019,2020",
        f"trials_total={N_DSR_TRIALS} selectable={HOLM_FAMILY_SIZE}",
        f"terminal_status={terminal_status}",
        f"selected_survivor={survivor or 'NONE'}",
    ]
    for item in metrics:
        if item["selectable"]:
            failed = [key for key, passed in item["gate_checks"].items() if not passed]
            log_lines.append(
                f"arm={item['arm_id']} trades={item['trades']} pf_x1={item['pf_x1']:.6f} "
                f"pf_x1p5={item['pf_x1p5']:.6f} pf_x2={item['pf_x2']:.6f} "
                f"expectancy_x1={item['expectancy_x1']:.12f} holm={item['sign_flip_p_holm']:.6f} "
                f"dsr={item['dsr_x1']:.6f} failed={','.join(failed) if failed else 'NONE'}"
            )
    log_path = output_root / "evaluator.log"
    atomic_write(log_path, ("\n".join(log_lines) + "\n").encode("utf-8"))

    artifact_paths = [trades_path, metrics_path, log_path, *chart_paths]
    artifact_manifest = {
        "schema_version": "lomx_001_train_artifact_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "artifacts": [
            {
                "path": str(path.relative_to(workspace)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in artifact_paths
        ],
    }
    artifact_manifest_path = output_root / "artifact_manifest.json"
    atomic_write(artifact_manifest_path, canonical_json(artifact_manifest) + b"\n")
    terminal = {
        "schema_version": "lomx_001_train_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": terminal_status,
        "selected_survivor": survivor,
        "goal_pf_x1_target": MIN_PF_X1,
        "validation_accessed": False,
        "holdout_accessed": False,
        "mql5_built": False,
        "model0_run": False,
        "promotion_ready": False,
        "cost_status": "UNVERIFIED_RESEARCH_PROXY_NOT_PROMOTION_GRADE",
        "metrics_path": str(metrics_path.relative_to(workspace)).replace("\\", "/"),
        "metrics_sha256": sha256_file(metrics_path),
        "artifact_manifest_path": str(artifact_manifest_path.relative_to(workspace)).replace("\\", "/"),
        "artifact_manifest_sha256": sha256_file(artifact_manifest_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    terminal_path = output_root / "train_terminal.json"
    atomic_write(terminal_path, canonical_json(terminal) + b"\n")
    return terminal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", default=r"D:\Trading EA MT5")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--reviewed-registry-row-sha256")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if not args.production:
        raise ContractError("production is disarmed; pass --production")
    if not args.reviewed_registry_row_sha256:
        raise ContractError("reviewed registry row SHA is required")
    terminal = evaluate(
        Path(args.workspace),
        reviewed_registry_sha=str(args.reviewed_registry_row_sha256),
    )
    print(json.dumps(terminal, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"LOMX_EVALUATOR_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
