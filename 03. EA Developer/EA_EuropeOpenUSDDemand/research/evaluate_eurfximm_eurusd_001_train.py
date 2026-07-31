#!/usr/bin/env python3
"""HYP-EURFXIMM-001 one-shot lagged five-minute flow-impact evaluator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EURFXIMM-EURUSD-M1-001"
ATTEMPT_ID = "EURFXIMM001-TRAIN-ECON-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXIMM-EURUSD-M1-001_TRAIN_ECONOMIC_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfximm_eurusd_001_train.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfximm_eurusd_001_train.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
FOUNDATION_REL = BASE_REL + "evaluate_eurfxofi_014_train.py"
FOUNDATION_SHA256 = "ADFA888F7A05BA35C9009ED2A464B84A2321DCE47236DCD7EA39F857205795A6"
PLAN_SHA256 = "705063A0A39B31E8DB7EAC2F49531A50BE855B6A91061738D499AC43316D8329"
HYP016_LEDGER_REL = (
    BASE_REL
    + "evidence/HYP-EURFXOFI-EURUSD-M1-016/EURFXOFI016-TRAIN-ECON-001/trades.jsonl"
)
HYP016_LEDGER_SHA256 = "B46A3A3B18F354F2F5F72D74E59C909BDBCCE4F66E0752C98AF6E84C8A05BDF0"
HYP016_PRIOR_ARMS = (
    "flow_reversal_primary",
    "flow_continuation_control",
    "pressure_reversal_control",
    "pressure_continuation_control",
)
LEGACY_SUMMARY_ARMS = (
    "flow_reversal_primary",
    "flow_reversal_control",
    "pressure_continuation_control",
    "pressure_reversal_control",
)
PUBLIC_ARMS = (
    "flow_continuation_primary",
    "flow_reversal_control",
    "pressure_continuation_control",
    "pressure_reversal_control",
)
EXPECTED_TRADES = 608


REVIEWED_REGISTRY_ROW_SHA256: str | None = "CE54B64B7B3741A3980DAD5CDAE32A36FC81AE90EB86D2537F41302FC4856938"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    pass


class ArmMetrics(dict[str, Any]):
    """Expose one legacy read alias without serializing a fifth arm."""

    def __getitem__(self, key: str) -> Any:
        if key == "flow_reversal_primary" and key not in self:
            key = "flow_continuation_primary"
        return super().__getitem__(key)


def workspace() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
    if len(indices) != 1:
        raise ContractError("wrapper must contain exactly one review sentinel")
    index = indices[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return hashlib.sha256(b"".join(lines)).hexdigest().upper()


def load_foundation(root: Path) -> ModuleType:
    path = root / FOUNDATION_REL
    if not path.is_file() or sha256_file(path) != FOUNDATION_SHA256:
        raise ContractError("HYP014 evaluator foundation hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfximm001_foundation", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load HYP014 evaluator foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _project_train_targets(module: ModuleType, price_frame: pd.DataFrame) -> pd.DataFrame:
    if set(price_frame.columns) != {"time_utc", "close"}:
        raise module.ContractError("price frame projection mismatch")
    times = pd.to_datetime(price_frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(price_frame["close"], errors="coerce")
    local = times.dt.tz_convert(module.LOCAL_TZ)
    slot = local.dt.strftime("%H:%M").map({"14:15": "entry", "14:20": "exit"}).fillna("")
    mask = (local.dt.weekday < 5) & slot.ne("")
    selected = pd.DataFrame(
        {
            "local_date": local[mask].dt.strftime("%Y-%m-%d").to_numpy(),
            "slot": slot[mask].to_numpy(),
            "close": closes[mask].to_numpy(dtype=float),
        }
    )
    if selected.duplicated(["local_date", "slot"]).any():
        raise module.ContractError("duplicate target date/slot")
    pivot = selected.pivot(index="local_date", columns="slot", values="close")
    if not {"entry", "exit"}.issubset(pivot.columns):
        raise module.ContractError("target boundary columns absent")
    pivot = pivot[["entry", "exit"]].dropna().reset_index()
    pivot["immediate_move_pips"] = (pivot["exit"] - pivot["entry"]) / module.PIP_SIZE
    return pivot


def _build_trades(
    module: ModuleType,
    features: pd.DataFrame,
    signal_ledger: pd.DataFrame,
    targets: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    if len(features) != module.EXPECTED_TRAIN_DATES or len(signal_ledger) != module.EXPECTED_TRAIN_DATES:
        raise module.ContractError("build input TRAIN population mismatch")
    merged = signal_ledger.merge(features, on="local_date", how="inner", validate="one_to_one")
    if len(merged) != module.EXPECTED_TRAIN_DATES:
        raise module.ContractError("signal/source date join mismatch")
    merged = merged.merge(targets, on="local_date", how="left", validate="one_to_one")
    required = ["entry", "exit", "immediate_move_pips"]
    missing_target = int(merged[required].isna().any(axis=1).sum())
    source_empty = merged["source_empty"].astype(bool)
    zero_flow = merged["flow_signed"].fillna(0).eq(0)
    target_available = merged[required].notna().all(axis=1)
    eligible = ~source_empty & ~zero_flow & target_available
    funnel = {
        "selected_train_dates": int(len(merged)),
        "source_empty_dates": int(source_empty.sum()),
        "zero_signed_flow_dates": int((~source_empty & zero_flow).sum()),
        "missing_target_dates": missing_target,
        "trades": int(eligible.sum()),
    }
    missing_dates = tuple(sorted(merged.loc[~target_available, "local_date"].astype(str)))
    if missing_dates != tuple(sorted(module.ALLOWED_MISSING_TARGET_DATES)):
        raise module.ContractError(
            "selected TRAIN dates missing exact target boundaries; frozen set mismatch: "
            f"expected {module.ALLOWED_MISSING_TARGET_DATES}, got {missing_dates}"
        )
    trades = merged.loc[eligible].copy()
    if trades.empty:
        raise module.ContractError("no nonzero-flow TRAIN trades")
    flow_sign = np.sign(trades["flow_signed"].to_numpy(dtype=float)).astype(int)
    pressure_sign = np.sign(trades["pre_fix_pressure_pips"].to_numpy(dtype=float)).astype(int)
    if not np.isin(flow_sign, (-1, 1)).all() or not np.isin(pressure_sign, (-1, 1)).all():
        raise module.ContractError("non-binary flow/pressure sign after eligibility")
    directions = {
        "flow_continuation_primary": flow_sign,
        "flow_reversal_control": -flow_sign,
        "pressure_continuation_control": pressure_sign,
        "pressure_reversal_control": -pressure_sign,
    }
    move = trades["immediate_move_pips"].to_numpy(dtype=float)
    for arm, direction in directions.items():
        trades[f"{arm}_direction"] = direction
        trades[f"{arm}_gross_pips"] = direction * move
        for label, cost in module.COSTS.items():
            trades[f"{arm}_net_{label}_pips"] = trades[f"{arm}_gross_pips"] - cost
    # The immutable foundation reads this private compatibility alias in its
    # primary equity/annual chart code. It is removed from the emitted ledger.
    for suffix in ("direction", "gross_pips", "net_x1_pips", "net_x1_5_pips", "net_x2_pips"):
        trades[f"flow_reversal_primary_{suffix}"] = trades[f"flow_continuation_primary_{suffix}"]
    trades["post_fix_move_pips"] = trades["immediate_move_pips"]
    trades["direction"] = trades["flow_continuation_primary_direction"]
    trades["gross_pips"] = trades["flow_continuation_primary_gross_pips"]
    for label in module.COSTS:
        trades[f"primary_net_{label}_pips"] = trades[f"flow_continuation_primary_net_{label}_pips"]
        trades[f"reverse_net_{label}_pips"] = trades[f"flow_reversal_control_net_{label}_pips"]
    trades["year"] = trades["local_date"].str[:4].astype(int)
    trades["weekday"] = pd.to_datetime(trades["local_date"]).dt.weekday
    trades["flow_pressure_agree"] = flow_sign == pressure_sign
    trades["entry_local_hhmm"] = "14:15"
    trades["exit_local_hhmm"] = "14:20"
    return trades.sort_values("local_date").reset_index(drop=True), funnel


def _load_prior_arms(module: ModuleType, root: Path, paired_loader: Any) -> dict[str, np.ndarray]:
    arms = paired_loader(root)
    if len(arms) != 12:
        raise module.ContractError("paired prior DSR universe is not 12 arms")
    path = module.require_d(root / HYP016_LEDGER_REL, "HYP016 multi-arm ledger")
    if module.sha256_file(path) != HYP016_LEDGER_SHA256:
        raise module.ContractError("HYP016 multi-arm ledger hash mismatch")
    multi: dict[str, list[float]] = {name: [] for name in HYP016_PRIOR_ARMS}
    for raw in path.read_bytes().splitlines():
        row = json.loads(raw)
        for name in HYP016_PRIOR_ARMS:
            multi[name].append(float(row[f"{name}_net_x1_pips"]))
    if any(len(values) < 500 for values in multi.values()):
        raise module.ContractError("HYP016 prior-arm population mismatch")
    for name, values in multi.items():
        arms[f"eurfxofi016_{name}"] = np.asarray(values, dtype=float)
    if len(arms) != 16:
        raise module.ContractError("prior DSR universe is not 16 arms")
    return arms


def _compute_dsr(
    module: ModuleType,
    trades: pd.DataFrame,
    prior: dict[str, np.ndarray],
    dsr_module: ModuleType,
) -> dict[str, Any]:
    arms = {name: module.arm_moments(values) for name, values in prior.items()}
    for arm in LEGACY_SUMMARY_ARMS:
        arms[f"{module.SCHEMA_PREFIX}_{arm}"] = module.arm_moments(
            trades[f"{arm}_net_x1_pips"]
        )
    if len(arms) != 20:
        raise module.ContractError("DSR universe is not 20 arms")
    values = [float(item["sr"]) for item in arms.values()]
    variance = float(np.var(values, ddof=1))
    primary = arms[f"{module.SCHEMA_PREFIX}_flow_reversal_primary"]
    value = float(
        dsr_module.dsr(
            float(primary["sr"]),
            int(primary["n"]),
            float(primary["skew"]),
            float(primary["kurtosis_non_excess"]),
            variance,
            len(arms),
        )
    )
    if not math.isfinite(value):
        raise module.ContractError("non-finite DSR")
    return {
        "n_trials": len(arms),
        "variance_sr_trials": variance,
        "primary_dsr": value,
        "arms": arms,
    }


def _summarize(
    module: ModuleType,
    original: Any,
    trades: pd.DataFrame,
    funnel: dict[str, int],
    prior: dict[str, np.ndarray],
    dsr_module: ModuleType,
    permutations: int,
) -> dict[str, Any]:
    module.ARMS = LEGACY_SUMMARY_ARMS
    metrics = original(trades, funnel, prior, dsr_module, permutations=permutations)
    old = metrics["arms"].pop("flow_reversal_primary")
    metrics["arms"] = ArmMetrics(
        {"flow_continuation_primary": old, **metrics["arms"]}
    )
    exact = bool(
        (trades["entry_local_hhmm"] == "14:15").all()
        and (trades["exit_local_hhmm"] == "14:20").all()
        and (
            trades["flow_continuation_primary_direction"].to_numpy()
            == np.sign(trades["flow_signed"].to_numpy()).astype(int)
        ).all()
        and (trades["flow_signed"] != 0).all()
    )
    metrics["structural_gates"]["exact_frozen_rule"] = exact
    metrics["structural_gates"]["exact_608_trades"] = len(trades) == EXPECTED_TRADES
    metrics["structural_gate_pass_count"] = sum(metrics["structural_gates"].values())
    metrics["structural_gate_total"] = len(metrics["structural_gates"])
    module.ARMS = PUBLIC_ARMS
    return metrics


def _trade_rows(module: ModuleType, original: Any, trades: pd.DataFrame) -> bytes:
    compatibility = [
        "post_fix_move_pips",
        "flow_reversal_primary_direction",
        "flow_reversal_primary_gross_pips",
        "flow_reversal_primary_net_x1_pips",
        "flow_reversal_primary_net_x1_5_pips",
        "flow_reversal_primary_net_x2_pips",
    ]
    return original(trades.drop(columns=compatibility))


def configure(root: Path | None = None) -> ModuleType:
    base = root or workspace()
    module = load_foundation(base)
    module.HYPOTHESIS_ID = HYPOTHESIS_ID
    module.ATTEMPT_ID = ATTEMPT_ID
    module.PLAN_REL = PLAN_REL
    module.EVALUATOR_REL = EVALUATOR_REL
    module.TEST_REL = TEST_REL
    module.EVIDENCE_ROOT_REL = EVIDENCE_ROOT_REL
    module.PLAN_SHA256 = PLAN_SHA256
    module.DISPLAY_TAG = "HYPIMM001"
    module.ARTIFACT_PREFIX = "EURFXIMM001"
    module.SCHEMA_PREFIX = "eurfximm001"
    module.RUN_ELIGIBLE_STATE = "probe"
    module.ALLOWED_MISSING_TARGET_DATES = ("2017-09-28",)
    module.VERDICT_PASS = "PASS_TRAIN_IMMEDIATE_FLOW_CONTINUATION_AUTHORIZE_FRESH_VALIDATION_SUCCESSOR_ONLY"
    module.VERDICT_KILL = "KILL_TRAIN_IMMEDIATE_FLOW_CONTINUATION_HOLDOUT_REMAINS_SEALED"
    module.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
    paired_loader = module.load_prior_arms
    original_summary = module.summarize_trades
    original_trade_rows = module.trade_rows
    module.project_train_targets = lambda frame: _project_train_targets(module, frame)
    module.build_trades = lambda features, signal, targets: _build_trades(
        module, features, signal, targets
    )
    module.load_prior_arms = lambda workspace_root: _load_prior_arms(
        module, workspace_root, paired_loader
    )
    module.compute_dsr = lambda trades, prior, dsr: _compute_dsr(
        module, trades, prior, dsr
    )
    module.summarize_trades = (
        lambda trades, funnel, prior, dsr, permutations=module.PERMUTATIONS: _summarize(
            module,
            original_summary,
            trades,
            funnel,
            prior,
            dsr,
            permutations,
        )
    )
    module.trade_rows = lambda trades: _trade_rows(module, original_trade_rows, trades)
    module.ARMS = PUBLIC_ARMS
    return module


def main() -> int:
    return int(configure().main())


if __name__ == "__main__":
    raise SystemExit(main())
