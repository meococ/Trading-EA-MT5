#!/usr/bin/env python3
"""One-shot 2021-2024 validation of EURUSD post-fix pressure continuation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EURFXMOM-EURUSD-M1-001"
ATTEMPT_ID = "EURFXMOM001-VALIDATION-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXMOM-EURUSD-M1-001_VALIDATION_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfxmom_eurusd_001_validation.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfxmom_eurusd_001_validation.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
SIGNAL_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-002/EURFXOFI002-SIGNAL-DATE-SELECTION-001/"
    "signal_dates.jsonl"
)
PARQUET_REL = "02. AlphaFactory/data/fivepercent/EURUSD/EURUSD_M1_2015_now.parquet"
MANIFEST_REL = "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json"
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
DISCOVERY_TERMINAL_REL = (
    BASE_REL + "evidence/HYP-EURFXOFI-EURUSD-M1-016/"
    "EURFXOFI016-TRAIN-ECON-001/train_economic_terminal.json"
)
DISCOVERY_TRADES_REL = (
    BASE_REL + "evidence/HYP-EURFXOFI-EURUSD-M1-016/"
    "EURFXOFI016-TRAIN-ECON-001/trades.jsonl"
)
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"

PLAN_SHA256 = "3731C07AC6A70A23CEB79C3340ADFCFD71FE1EC8F7FAE353CB57C6A1E0CA7332"
SIGNAL_SHA256 = "EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
PARQUET_SHA256 = "2959C555DB6690FD6EFD6CFB3B4C6323698E590C9B2D71E1E55F1902F724235A"
MANIFEST_SHA256 = "2CD996FD4416B1E888BF1C9D272BF49056DB3A4CE477CF74FA4E31D474A41B54"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
DISCOVERY_TERMINAL_SHA256 = "3E351BA4C03C2E08312D9D0CF099610DC847BCCF9A90B1401476C8EE36FB3BD2"
DISCOVERY_TRADES_SHA256 = "B46A3A3B18F354F2F5F72D74E59C909BDBCCE4F66E0752C98AF6E84C8A05BDF0"
DISCOVERY_VARIANCE_SR = 0.04661352120737083
DISCOVERY_TRIALS = 16
EXPECTED_DATES = 526
LOCAL_TZ = "Europe/Berlin"
PIP_SIZE = 0.0001
COSTS = {"x1": 1.50, "x1_5": 2.25, "x2": 3.00}
PERMUTATIONS = 10_000
PERMUTATION_SEED = 20_260_730
VALIDATION_START = pd.Timestamp("2021-01-01T00:00:00Z")
VALIDATION_END_EXCLUSIVE = pd.Timestamp("2025-01-01T00:00:00Z")
VERDICT_PASS = "PASS_VALIDATION_AUTHORIZE_FRESH_2025_CURRENT_HOLDOUT_SUCCESSOR_ONLY"
VERDICT_KILL = "KILL_VALIDATION_PRESSURE_CONTINUATION_HOLDOUT_REMAINS_SEALED"
VERDICT_STRUCTURAL = "INVALID_VALIDATION_SOURCE_OR_ENGINEERING"
CHART_NAMES = (
    "01_validation_equity_and_drawdown.png",
    "02_validation_yearly_performance.png",
    "03_discovery_validation_control_comparison.png",
    "04_monthly_stability_diagnostic.png",
    "05_validation_distributions_and_funnel.png",
)
ARTIFACT_PREFIX = "EURFXMOM001"
SCHEMA_PREFIX = "eurfxmom001"
DISPLAY_TAG = "EURFXMOM001"

REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    """Fail-closed authority, data or engineering violation."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D:, got {resolved}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("evaluator must contain exactly one valid sentinel")
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def latest_registry_row(path: Path, hypothesis_id: str) -> tuple[dict[str, Any], bytes]:
    latest: tuple[dict[str, Any], bytes] | None = None
    for raw in path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == hypothesis_id:
            latest = row, raw + b"\n"
    if latest is None:
        raise ContractError(f"registry missing {hypothesis_id}")
    return latest


def validate_authority(root: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise ContractError("registry sentinel is not armed")
    paths = {
        "plan": root / PLAN_REL,
        "evaluator": root / EVALUATOR_REL,
        "test": root / TEST_REL,
        "registry": root / REGISTRY_REL,
    }
    for label, path in paths.items():
        if not path.is_file():
            raise ContractError(f"missing {label}: {path}")
    if sha256_file(paths["plan"]) != PLAN_SHA256:
        raise ContractError("plan hash drift")
    evaluator_payload = paths["evaluator"].read_bytes()
    base_sha = normalized_evaluator_base_sha256(evaluator_payload)
    test_sha = sha256_file(paths["test"])
    row, raw = latest_registry_row(paths["registry"], HYPOTHESIS_ID)
    row_sha = sha256_bytes(raw)
    if row_sha != REVIEWED_REGISTRY_ROW_SHA256:
        raise ContractError("sentinel does not bind latest hypothesis row")
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise ContractError("registry state/plan is not validation-run eligible")
    for key in (
        "validation_evaluation_authorized",
        "performance_metrics_authorized",
        "economics_authorized",
        "outcome_prices_authorized",
        "post_entry_price_projection_authorized",
        "research_validation_access_authorized",
        "one_use",
    ):
        if validation.get(key) is not True:
            raise ContractError(f"required validation authority closed: {key}")
    if int(metrics.get("validation_attempts_consumed", -1)) != 0:
        raise ContractError("validation attempt already consumed")
    if ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("validation attempt ID already recorded")
    expected = {
        "validation_plan_sha256": PLAN_SHA256,
        "reviewed_evaluator_base_sha256": base_sha,
        "reviewed_test_sha256": test_sha,
        "signal_date_ledger_sha256": SIGNAL_SHA256,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "canonical_dsr_sha256": DSR_SHA256,
        "discovery_terminal_sha256": DISCOVERY_TERMINAL_SHA256,
        "discovery_trades_sha256": DISCOVERY_TRADES_SHA256,
    }
    for key, value in expected.items():
        if validation.get(key) != value:
            raise ContractError(f"registry binding mismatch: {key}")
    parent, _ = latest_registry_row(paths["registry"], "HYP-EURFXOFI-EURUSD-M1-016")
    if parent.get("state") != "killed" or parent.get("verdict") != "KILL_TRAIN_FLOW_REVERSAL_HOLDOUT_REMAINS_SEALED":
        raise ContractError("HYP016 discovery parent is not terminal")
    parent_validation = parent.get("validation", {})
    if parent_validation.get("attempt_terminal_sha256") != DISCOVERY_TERMINAL_SHA256:
        raise ContractError("HYP016 discovery terminal binding mismatch")
    if parent_validation.get("trades_sha256") != DISCOVERY_TRADES_SHA256:
        raise ContractError("HYP016 discovery trades binding mismatch")
    for key in (
        "research_holdout_access_authorized",
        "mql5_authorized",
        "mt5_authorized",
        "model0_authorized",
        "optimization_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if validation.get(key) is not False:
            raise ContractError(f"forbidden authority open: {key}")
    return {
        "registry_row_sha256": row_sha,
        "evaluator_base_sha256": base_sha,
        "evaluator_file_sha256": sha256_bytes(evaluator_payload),
        "test_sha256": test_sha,
    }


def load_module(path: Path, expected_hash: str, name: str) -> ModuleType:
    if sha256_file(path) != expected_hash:
        raise ContractError(f"{name} hash mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_validation_signal(path: Path) -> pd.DataFrame:
    if sha256_file(path) != SIGNAL_SHA256:
        raise ContractError("signal ledger hash mismatch")
    rows: list[dict[str, Any]] = []
    for raw in path.read_bytes().splitlines():
        item = json.loads(raw)
        if item.get("split") != "VALIDATION":
            continue
        rows.append(
            {
                "local_date": str(item["local_date"]),
                "pre_fix_pressure_pips": float(item["pre_fix_pressure_pips"]),
                "pressure_threshold_pips": float(item["pressure_threshold_pips"]),
                "ledger_reversal_direction": int(item["direction_from_pressure"]),
            }
        )
    frame = pd.DataFrame(rows).sort_values("local_date").reset_index(drop=True)
    if len(frame) != EXPECTED_DATES or frame["local_date"].duplicated().any():
        raise ContractError("validation signal population mismatch")
    if frame["local_date"].iloc[0] != "2021-01-04" or frame["local_date"].iloc[-1] != "2024-12-27":
        raise ContractError("validation signal boundary mismatch")
    pressure = frame["pre_fix_pressure_pips"].to_numpy(dtype=float)
    threshold = frame["pressure_threshold_pips"].to_numpy(dtype=float)
    if not np.isfinite(pressure).all() or not np.isfinite(threshold).all():
        raise ContractError("non-finite signal values")
    if not (np.abs(pressure) >= threshold).all() or (pressure == 0).any():
        raise ContractError("signal ledger violates frozen eligibility")
    if not (frame["ledger_reversal_direction"].to_numpy() == -np.sign(pressure)).all():
        raise ContractError("signal ledger pressure-direction mismatch")
    return frame


def load_validation_target(path: Path, manifest: Path) -> pd.DataFrame:
    if sha256_file(path) != PARQUET_SHA256 or sha256_file(manifest) != MANIFEST_SHA256:
        raise ContractError("target dataset hash mismatch")
    frame = pd.read_parquet(
        path,
        columns=["time_utc", "close"],
        filters=[
            ("time_utc", ">=", pd.Timestamp("2021-01-01")),
            ("time_utc", "<", pd.Timestamp("2025-01-01")),
        ],
    )
    if list(frame.columns) != ["time_utc", "close"] or frame.empty:
        raise ContractError("target projection schema/population mismatch")
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if times.isna().any() or closes.isna().any() or times.duplicated().any():
        raise ContractError("target time/price integrity failed")
    if not times.is_monotonic_increasing:
        raise ContractError("target timestamps are not increasing")
    if times.min() < VALIDATION_START or times.max() >= VALIDATION_END_EXCLUSIVE:
        raise ContractError("target projection crossed validation boundary")
    values = closes.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ContractError("target closes are invalid")
    return pd.DataFrame({"time_utc": times, "close": values})


def project_exact_targets(frame: pd.DataFrame) -> pd.DataFrame:
    local = frame["time_utc"].dt.tz_convert(LOCAL_TZ)
    slot = local.dt.strftime("%H:%M").map({"14:14": "entry", "15:59": "exit"}).fillna("")
    mask = (local.dt.weekday < 5) & slot.ne("")
    selected = pd.DataFrame(
        {
            "local_date": local[mask].dt.strftime("%Y-%m-%d").to_numpy(),
            "slot": slot[mask].to_numpy(),
            "close": frame.loc[mask, "close"].to_numpy(dtype=float),
        }
    )
    if selected.duplicated(["local_date", "slot"]).any():
        raise ContractError("duplicate validation target date/slot")
    pivot = selected.pivot(index="local_date", columns="slot", values="close")
    for name in ("entry", "exit"):
        if name not in pivot:
            pivot[name] = np.nan
    pivot = pivot[["entry", "exit"]].reset_index()
    pivot["post_fix_move_pips"] = (pivot["exit"] - pivot["entry"]) / PIP_SIZE
    return pivot


def build_trades(signal: pd.DataFrame, targets: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    merged = signal.merge(targets, on="local_date", how="left", validate="one_to_one")
    missing = merged[["entry", "exit", "post_fix_move_pips"]].isna().any(axis=1)
    if missing.any():
        dates = tuple(merged.loc[missing, "local_date"].astype(str))
        raise ContractError(f"selected validation dates missing target boundaries: {dates}")
    pressure = merged["pre_fix_pressure_pips"].to_numpy(dtype=float)
    direction = np.sign(pressure).astype(int)
    move = merged["post_fix_move_pips"].to_numpy(dtype=float)
    merged["direction"] = direction
    merged["pressure_continuation_primary_direction"] = direction
    merged["pressure_reversal_control_direction"] = -direction
    merged["pressure_continuation_primary_gross_pips"] = direction * move
    merged["pressure_reversal_control_gross_pips"] = -direction * move
    for label, cost in COSTS.items():
        merged[f"pressure_continuation_primary_net_{label}_pips"] = (
            merged["pressure_continuation_primary_gross_pips"] - cost
        )
        merged[f"pressure_reversal_control_net_{label}_pips"] = (
            merged["pressure_reversal_control_gross_pips"] - cost
        )
        merged[f"primary_net_{label}_pips"] = merged[
            f"pressure_continuation_primary_net_{label}_pips"
        ]
        merged[f"reverse_net_{label}_pips"] = merged[
            f"pressure_reversal_control_net_{label}_pips"
        ]
    merged["gross_pips"] = merged["pressure_continuation_primary_gross_pips"]
    merged["year"] = merged["local_date"].str[:4].astype(int)
    merged["month"] = merged["local_date"].str[:7]
    merged["weekday"] = pd.to_datetime(merged["local_date"]).dt.weekday
    merged["entry_local_hhmm"] = "14:14"
    merged["exit_local_hhmm"] = "15:59"
    funnel = {"selected_validation_dates": len(signal), "exact_target_dates": len(merged), "trades": len(merged)}
    return merged.sort_values("local_date").reset_index(drop=True), funnel


def profit_factor(values: Iterable[float]) -> float | None:
    array = np.asarray(list(values), dtype=float)
    wins = float(array[array > 0].sum())
    losses = float(-array[array < 0].sum())
    return wins / losses if wins > 0 and losses > 0 else None


def sign_flip_p_value(values: Sequence[float]) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        raise ContractError("invalid sign-flip input")
    observed = float(array.mean())
    rng = np.random.default_rng(PERMUTATION_SEED)
    exceed = 0
    for _ in range(PERMUTATIONS):
        candidate = float(np.mean(array * rng.choice(np.array([-1.0, 1.0]), size=array.size)))
        exceed += candidate >= observed
    return (1 + exceed) / (PERMUTATIONS + 1)


def arm_moments(values: Sequence[float]) -> dict[str, float | int]:
    series = pd.Series(np.asarray(values, dtype=float))
    std = float(series.std(ddof=1))
    if len(series) < 3 or not math.isfinite(std) or std <= 0:
        raise ContractError("invalid DSR arm")
    return {
        "n": len(series),
        "sr": float(series.mean()) / std,
        "skew": float(series.skew()),
        "kurtosis_non_excess": float(series.kurt()) + 3.0,
    }


def compute_dsr(values: Sequence[float], dsr_module: ModuleType) -> dict[str, Any]:
    moments = arm_moments(values)
    probability = float(
        dsr_module.dsr(
            float(moments["sr"]),
            int(moments["n"]),
            float(moments["skew"]),
            float(moments["kurtosis_non_excess"]),
            DISCOVERY_VARIANCE_SR,
            DISCOVERY_TRIALS,
        )
    )
    if not math.isfinite(probability):
        raise ContractError("non-finite DSR")
    return {
        "n_trials": DISCOVERY_TRIALS,
        "variance_sr_trials": DISCOVERY_VARIANCE_SR,
        "primary_dsr": probability,
        "validation_primary_moments": moments,
    }


def summarize_trades(
    trades: pd.DataFrame, funnel: dict[str, int], dsr_module: ModuleType
) -> dict[str, Any]:
    if len(trades) != EXPECTED_DATES:
        raise ContractError("validation trade population mismatch")
    primary = "pressure_continuation_primary"
    control = "pressure_reversal_control"
    arms: dict[str, Any] = {}
    for arm in (primary, control):
        arms[arm] = {
            "gross_profit_factor": profit_factor(trades[f"{arm}_gross_pips"]),
            "gross_expectancy_pips": float(trades[f"{arm}_gross_pips"].mean()),
            "profit_factor": {
                label: profit_factor(trades[f"{arm}_net_{label}_pips"])
                for label in COSTS
            },
            "expectancy_pips": {
                label: float(trades[f"{arm}_net_{label}_pips"].mean())
                for label in COSTS
            },
        }
    annual: dict[str, Any] = {}
    for year, group in trades.groupby("year"):
        values = group[f"{primary}_net_x1_pips"]
        annual[str(int(year))] = {
            "trades": len(group),
            "net_pips": float(values.sum()),
            "profit_factor": profit_factor(values),
            "expectancy_pips": float(values.mean()),
        }
    leave_one_year_out: dict[str, Any] = {}
    for year in sorted(trades["year"].unique()):
        values = trades.loc[trades["year"].ne(year), f"{primary}_net_x1_pips"]
        leave_one_year_out[str(int(year))] = {
            "trades": len(values),
            "profit_factor": profit_factor(values),
            "expectancy_pips": float(values.mean()),
        }
    elapsed_weeks = float(
        (VALIDATION_END_EXCLUSIVE - VALIDATION_START).total_seconds() / 604800.0
    )
    cadence = len(trades) / elapsed_weeks
    positive_years = sum(item["net_pips"] > 0 for item in annual.values())
    positive = [max(0.0, float(item["net_pips"])) for item in annual.values()]
    max_positive_year_share = max(positive) / sum(positive) if sum(positive) > 0 else 1.0
    p_value = sign_flip_p_value(trades[f"{primary}_net_x1_pips"])
    dsr = compute_dsr(trades[f"{primary}_net_x1_pips"], dsr_module)
    x1 = trades[f"{primary}_net_x1_pips"].to_numpy(dtype=float)
    equity = np.cumsum(x1)
    peak = np.maximum.accumulate(np.r_[0.0, equity])[-len(equity):]
    drawdown = equity - peak
    exact = bool(
        (trades["entry_local_hhmm"] == "14:14").all()
        and (trades["exit_local_hhmm"] == "15:59").all()
        and (
            trades[f"{primary}_direction"].to_numpy()
            == np.sign(trades["pre_fix_pressure_pips"].to_numpy()).astype(int)
        ).all()
        and (
            trades["pre_fix_pressure_pips"].abs()
            >= trades["pressure_threshold_pips"]
        ).all()
    )
    structural = {
        "exact_526_trades": len(trades) == EXPECTED_DATES,
        "target_population_reconciled": funnel["exact_target_dates"] == EXPECTED_DATES,
        "cadence_2_to_3": 2.0 <= cadence <= 3.0,
        "both_directions_ge_0_25": float((trades["direction"] == 1).mean()) >= 0.25
        and float((trades["direction"] == -1).mean()) >= 0.25,
        "exact_frozen_rule": exact,
    }
    pf = arms[primary]["profit_factor"]
    exp = arms[primary]["expectancy_pips"]
    economic = {
        "pf_x1_ge_1_30": pf["x1"] is not None and pf["x1"] >= 1.30,
        "pf_x1_5_ge_1_25": pf["x1_5"] is not None and pf["x1_5"] >= 1.25,
        "pf_x2_ge_1_00": pf["x2"] is not None and pf["x2"] >= 1.00,
        "expectancy_x1_gt_0": exp["x1"] > 0,
        "positive_years_ge_3_of_4": len(annual) == 4 and positive_years >= 3,
        "leave_one_year_out_pf_gt_1": all(
            item["profit_factor"] is not None and item["profit_factor"] > 1.0
            for item in leave_one_year_out.values()
        ),
        "sign_flip_x1_p_le_0_05": p_value <= 0.05,
        "dsr_ge_0_95": dsr["primary_dsr"] >= 0.95,
        "max_positive_year_share_le_0_35": max_positive_year_share <= 0.35,
    }
    return {
        "trade_count": len(trades),
        "first_local_date": str(trades["local_date"].min()),
        "last_local_date": str(trades["local_date"].max()),
        "elapsed_calendar_weeks": elapsed_weeks,
        "trades_per_elapsed_week": cadence,
        "long_share": float((trades["direction"] == 1).mean()),
        "short_share": float((trades["direction"] == -1).mean()),
        "funnel": funnel,
        "arms": arms,
        "annual_primary_x1": annual,
        "positive_years": positive_years,
        "leave_one_year_out_primary_x1": leave_one_year_out,
        "max_positive_year_share": max_positive_year_share,
        "sign_flip_x1_one_sided_p_value": p_value,
        "permutation_count": PERMUTATIONS,
        "permutation_seed": PERMUTATION_SEED,
        "deflated_sharpe": dsr,
        "max_drawdown_pips_x1": float(drawdown.min()),
        "structural_gates": structural,
        "economic_gates": economic,
        "structural_gate_pass_count": sum(structural.values()),
        "structural_gate_total": len(structural),
        "economic_gate_pass_count": sum(economic.values()),
        "economic_gate_total": len(economic),
    }


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def trade_rows(trades: pd.DataFrame) -> bytes:
    output: list[bytes] = []
    for raw in trades.to_dict(orient="records"):
        local_date = str(raw["local_date"])
        row: dict[str, Any] = {"trade_id": f"{ARTIFACT_PREFIX}-{local_date}", "local_date": local_date}
        for key, value in raw.items():
            if key == "local_date":
                continue
            if pd.isna(value):
                row[key] = None
            elif isinstance(value, (np.bool_, bool)):
                row[key] = bool(value)
            elif isinstance(value, (np.integer, int)):
                row[key] = int(value)
            elif isinstance(value, (np.floating, float)):
                row[key] = round(float(value), 10)
            else:
                row[key] = value
        output.append(canonical_json(row) + b"\n")
    return b"".join(output)


def _write_plot(fig: Any, path: Path) -> None:
    fig.update_layout(
        template="plotly_white",
        font={"family": "Arial", "size": 12},
        margin={"l": 60, "r": 30, "t": 90, "b": 65},
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    fig.write_image(str(path), width=1500, height=850, scale=1.25)


def render_charts(trades: pd.DataFrame, metrics: dict[str, Any], root: Path) -> list[Path]:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    primary = "pressure_continuation_primary"
    dates = pd.to_datetime(trades["local_date"])
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Cumulative PnL", "x1 drawdown"), row_heights=[0.68, 0.32])
    for label, column in (
        ("gross", f"{primary}_gross_pips"),
        ("x1 1.50 pips", f"{primary}_net_x1_pips"),
        ("x1.5 2.25 pips", f"{primary}_net_x1_5_pips"),
        ("x2 3.00 pips", f"{primary}_net_x2_pips"),
    ):
        fig.add_trace(go.Scatter(x=dates, y=trades[column].cumsum(), mode="lines", name=label), row=1, col=1)
    equity = trades[f"{primary}_net_x1_pips"].cumsum()
    drawdown = equity - equity.cummax().clip(lower=0)
    fig.add_trace(go.Scatter(x=dates, y=drawdown, mode="lines", fill="tozeroy", name="x1 drawdown"), row=2, col=1)
    fig.update_layout(title=f"{DISPLAY_TAG} validation equity and drawdown | n={len(trades):,}")
    chart1 = root / CHART_NAMES[0]
    _write_plot(fig, chart1)

    annual = pd.DataFrame(metrics["annual_primary_x1"]).T.reset_index(names="year")
    fig = make_subplots(rows=1, cols=3, subplot_titles=("x1 net pips", "x1 profit factor", "x1 expectancy"))
    fig.add_trace(go.Bar(x=annual["year"], y=annual["net_pips"], name="net pips"), row=1, col=1)
    fig.add_trace(go.Bar(x=annual["year"], y=annual["profit_factor"], name="PF"), row=1, col=2)
    fig.add_hline(y=1.0, line_dash="dash", line_color="black", row=1, col=2)
    fig.add_trace(go.Bar(x=annual["year"], y=annual["expectancy_pips"], name="expectancy"), row=1, col=3)
    fig.add_hline(y=0.0, line_dash="dash", line_color="black", row=1, col=3)
    fig.update_layout(title=f"{DISPLAY_TAG} validation annual stability after 1.50-pip cost")
    chart2 = root / CHART_NAMES[1]
    _write_plot(fig, chart2)

    labels = ["Discovery primary", "Validation primary", "Validation reverse"]
    discovery_pf = 4.31516762664312
    discovery_exp = 7.383881578947443
    validation_primary = metrics["arms"][primary]
    validation_reverse = metrics["arms"]["pressure_reversal_control"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("PF x1", "Expectancy x1 (pips)"))
    fig.add_trace(go.Bar(x=labels, y=[discovery_pf, validation_primary["profit_factor"]["x1"], validation_reverse["profit_factor"]["x1"]], name="PF"), row=1, col=1)
    fig.add_hline(y=1.0, line_dash="dash", line_color="black", row=1, col=1)
    fig.add_trace(go.Bar(x=labels, y=[discovery_exp, validation_primary["expectancy_pips"]["x1"], validation_reverse["expectancy_pips"]["x1"]], name="expectancy"), row=1, col=2)
    fig.add_hline(y=0.0, line_dash="dash", line_color="black", row=1, col=2)
    fig.update_layout(title="Frozen discovery signal versus unseen validation and exact reverse", showlegend=False)
    chart3 = root / CHART_NAMES[2]
    _write_plot(fig, chart3)

    monthly = trades.groupby("month")[f"{primary}_net_x1_pips"].agg(["sum", "mean", "count"]).reset_index()
    rolling = trades[f"{primary}_net_x1_pips"].rolling(60, min_periods=60).mean()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, subplot_titles=("Monthly x1 net pips", "Diagnostic-only rolling 60-trade x1 expectancy"))
    fig.add_trace(go.Bar(x=monthly["month"], y=monthly["sum"], name="monthly net"), row=1, col=1)
    fig.add_hline(y=0.0, line_dash="dash", line_color="black", row=1, col=1)
    fig.add_trace(go.Scatter(x=dates, y=rolling, mode="lines", name="rolling expectancy"), row=2, col=1)
    fig.add_hline(y=0.0, line_dash="dash", line_color="black", row=2, col=1)
    fig.update_layout(title="Validation stability diagnostics only - no filter authority")
    chart4 = root / CHART_NAMES[3]
    _write_plot(fig, chart4)

    funnel = metrics["funnel"]
    fig = make_subplots(rows=2, cols=2, subplot_titles=("Validation funnel", "Pre-fix pressure", "Holding return", "Primary x1 PnL"))
    fig.add_trace(go.Funnel(y=["Selected", "Exact target", "Trades"], x=[funnel["selected_validation_dates"], funnel["exact_target_dates"], funnel["trades"]], name="count"), row=1, col=1)
    fig.add_trace(go.Histogram(x=trades["pre_fix_pressure_pips"], nbinsx=45, name="pressure"), row=1, col=2)
    fig.add_trace(go.Histogram(x=trades["post_fix_move_pips"], nbinsx=45, name="return"), row=2, col=1)
    fig.add_trace(go.Histogram(x=trades[f"{primary}_net_x1_pips"], nbinsx=45, name="x1 pnl"), row=2, col=2)
    fig.update_layout(title=f"{DISPLAY_TAG} validation signal and distribution controls | trades={len(trades):,}", showlegend=False)
    chart5 = root / CHART_NAMES[4]
    _write_plot(fig, chart5)
    return [chart1, chart2, chart3, chart4, chart5]


def execute(root: Path) -> Path:
    root = require_d(root, "workspace")
    authority = validate_authority(root)
    discovery_terminal = require_d(root / DISCOVERY_TERMINAL_REL, "discovery terminal")
    discovery_trades = require_d(root / DISCOVERY_TRADES_REL, "discovery trades")
    if sha256_file(discovery_terminal) != DISCOVERY_TERMINAL_SHA256 or sha256_file(discovery_trades) != DISCOVERY_TRADES_SHA256:
        raise ContractError("discovery evidence hash mismatch")
    evidence = require_d(root / EVIDENCE_ROOT_REL, "evidence root")
    if evidence.exists():
        raise ContractError("one-shot evidence root already exists")
    evidence.mkdir(parents=True)
    started = evidence / "attempt_started.json"
    write_new(
        started,
        canonical_json(
            {
                "schema_version": f"{SCHEMA_PREFIX}_validation_attempt_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "started_at_utc": utc_now(),
                "plan_sha256": PLAN_SHA256,
                "registry_row_sha256": authority["registry_row_sha256"],
                "evaluator_base_sha256": authority["evaluator_base_sha256"],
                "evaluator_file_sha256": authority["evaluator_file_sha256"],
                "test_sha256": authority["test_sha256"],
                "validation_outcomes_opened": False,
                "holdout_outcomes_opened": False,
            }
        ) + b"\n",
    )
    run_log = evidence / "run_log.jsonl"
    write_new(run_log, canonical_json({"event": "attempt_started", "at_utc": utc_now()}) + b"\n")

    signal = load_validation_signal(require_d(root / SIGNAL_REL, "signal ledger"))
    target = load_validation_target(
        require_d(root / PARQUET_REL, "target parquet"),
        require_d(root / MANIFEST_REL, "target manifest"),
    )
    trades, funnel = build_trades(signal, project_exact_targets(target))
    dsr_module = load_module(require_d(root / DSR_REL, "DSR"), DSR_SHA256, "eurfxmom001_dsr")
    metrics = summarize_trades(trades, funnel, dsr_module)
    if metrics["structural_gate_pass_count"] < metrics["structural_gate_total"]:
        verdict = VERDICT_STRUCTURAL
    elif metrics["economic_gate_pass_count"] == metrics["economic_gate_total"]:
        verdict = VERDICT_PASS
    else:
        verdict = VERDICT_KILL

    ledger = evidence / "trades.jsonl"
    write_new(ledger, trade_rows(trades))
    charts = render_charts(trades, metrics, evidence)
    log_triage = evidence / "log_triage.json"
    write_new(
        log_triage,
        canonical_json(
            {
                "schema_version": f"{SCHEMA_PREFIX}_validation_log_triage.v1",
                "fatal_errors": 0,
                "warnings": 0,
                "attempt_completed": True,
                "validation_outcomes_opened": True,
                "holdout_outcomes_opened": False,
            }
        ) + b"\n",
    )
    with run_log.open("ab") as handle:
        handle.write(canonical_json({"event": "attempt_completed", "at_utc": utc_now(), "verdict": verdict, "trades": len(trades)}) + b"\n")
    terminal = evidence / "validation_terminal.json"
    terminal_payload = {
        "schema_version": f"{SCHEMA_PREFIX}_validation_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": utc_now(),
        "verdict": verdict,
        "engineering_valid": verdict != VERDICT_STRUCTURAL,
        "economic_edge_evaluated": verdict != VERDICT_STRUCTURAL,
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "registry_row_sha256": authority["registry_row_sha256"],
        "evaluator_path": EVALUATOR_REL,
        "evaluator_base_sha256": authority["evaluator_base_sha256"],
        "evaluator_file_sha256": authority["evaluator_file_sha256"],
        "test_path": TEST_REL,
        "test_sha256": authority["test_sha256"],
        "signal_ledger_path": SIGNAL_REL,
        "signal_ledger_sha256": SIGNAL_SHA256,
        "dataset_parquet_path": PARQUET_REL,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "dataset_manifest_path": MANIFEST_REL,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "canonical_dsr_path": DSR_REL,
        "canonical_dsr_sha256": DSR_SHA256,
        "discovery_terminal_path": DISCOVERY_TERMINAL_REL,
        "discovery_terminal_sha256": DISCOVERY_TERMINAL_SHA256,
        "discovery_trades_path": DISCOVERY_TRADES_REL,
        "discovery_trades_sha256": DISCOVERY_TRADES_SHA256,
        "target_projection": {
            "rows_read": len(target),
            "min_time_utc": target["time_utc"].min().isoformat(),
            "max_time_utc": target["time_utc"].max().isoformat(),
            "validation_only": True,
        },
        "attempt_started_sha256": sha256_file(started),
        "trades_path": str(ledger.relative_to(root)).replace("\\", "/"),
        "trades_sha256": sha256_file(ledger),
        "run_log_sha256": sha256_file(run_log),
        "log_triage_sha256": sha256_file(log_triage),
        "charts": [
            {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in charts
        ],
        "metrics": metrics,
        "forbidden_counters": {
            "train_outcomes_reopened": False,
            "holdout_outcomes_opened": False,
            "mt5_launches": 0,
            "mql5_files_created": 0,
            "model0_runs": 0,
            "optimization_trials": 0,
            "orders_submitted": 0,
            "paper_trading": False,
            "live_trading": False,
        },
        "authority_after_verdict": {
            "fresh_holdout_successor_may_be_preregistered": verdict == VERDICT_PASS,
            "holdout_authorized": False,
            "mql5_authorized": False,
            "model0_authorized": False,
            "optimization_authorized": False,
            "promotion_eligible": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
        },
    }
    write_new(terminal, canonical_json(terminal_payload) + b"\n")
    artifact_manifest = evidence / "artifact_manifest.json"
    artifacts = [started, ledger, run_log, log_triage, terminal, *charts]
    write_new(
        artifact_manifest,
        canonical_json(
            {
                "schema_version": f"{SCHEMA_PREFIX}_validation_artifact_manifest.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "generated_at_utc": utc_now(),
                "artifacts": [
                    {"path": str(path.relative_to(root)).replace("\\", "/"), "sha256": sha256_file(path), "bytes": path.stat().st_size}
                    for path in artifacts
                ],
            }
        ) + b"\n",
    )
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        terminal = execute(args.workspace.resolve())
    except ContractError as exc:
        print(f"{ARTIFACT_PREFIX}_ERROR {exc}", file=sys.stderr)
        return 2
    payload = json.loads(terminal.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    pf_x1 = metrics["arms"]["pressure_continuation_primary"]["profit_factor"]["x1"]
    print(
        f"{ARTIFACT_PREFIX}_RESULT verdict={payload['verdict']} trades={metrics['trade_count']} "
        f"pf_x1={pf_x1} economic_gates={metrics['economic_gate_pass_count']}/{metrics['economic_gate_total']}"
    )
    print(f"TERMINAL {terminal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
