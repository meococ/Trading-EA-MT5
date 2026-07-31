#!/usr/bin/env python3
"""One-shot post-ECB-fix pressure-reversal evaluator."""

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
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EURFXREV-EURUSD-M1-001"
ATTEMPT_ID = "EURFXREV001-TRAIN-ECON-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXREV-EURUSD-M1-001_TRAIN_ECONOMIC_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfxrev_eurusd_001_train.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfxrev_eurusd_001_train.py"
PARENT_REL = BASE_REL + "evaluate_euusd_eurusd_001_train.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
PARQUET_REL = "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet"
MANIFEST_REL = "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json"
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"

LEDGERS = {
    "lojm001": ("03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001/trades.jsonl", "6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98"),
    "lofix002": ("03. EA Developer/EA_LondonFixHalfHourMomentum/research/evidence/HYP-LOFIX-USDJPY-M1-002/LOFIX002-TRAIN-ECON-001/trades.jsonl", "04270A2E9772A884322753701D55B6101109B1BA1E49ABFF59F89B882815A6DB"),
    "euusd_usdjpy001": (BASE_REL + "evidence/HYP-EUUSD-USDJPY-M1-001/EUUSD001-TRAIN-ECON-001/trades.jsonl", "18D8C2333FE421DFA279325D30A29D759AAD4333A304BA1FC68E7B485009E10C"),
    "euusd_eurusd001": (BASE_REL + "evidence/HYP-EUUSD-EURUSD-M1-001/EUEUR001-TRAIN-ECON-001/trades.jsonl", "204050AAA213DB1BC468FD022733425DC3E2E70EF33A742A0A7D620EF8B166E8"),
    "euvix002": (BASE_REL + "evidence/HYP-EUVIX-EURUSD-M1-002/EUVIX002-TRAIN-ECON-001/trades.jsonl", "B2C9CA21F80F307BDBCB9B8DFE34D4477D3B7CFF78B164823D6810563EA66F1E"),
}

PLAN_SHA256 = "8F62C3A5FB9C944EFF96C68904C7CFB57F84752C2455805538D84F352DAE8833"
PARENT_SHA256 = "0FB3FF4AE1326958FC911B7228DF9AF8526201A9506EF97C6DAFF7E9FBA9BFEE"
PARQUET_SHA256 = "C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6"
MANIFEST_SHA256 = "4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
LOCAL_TZ = "Europe/Berlin"
PIP_SIZE = 0.0001
COSTS = {"x1": 1.50, "x1_5": 2.25, "x2": 3.00}
LOOKBACK = 60
MIN_HISTORY = 40
PERMUTATIONS = 10_000
PERMUTATION_SEED = 20_260_729
DESIGN_START = pd.Timestamp("2016-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2020-12-31T23:59:59Z")
VERDICT_PASS = "PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY"
VERDICT_KILL = "KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED"
VERDICT_STRUCTURAL = "KILL_STRUCTURAL_NO_ECONOMICS_SURVIVOR"

REVIEWED_REGISTRY_ROW_SHA256: str | None = "BB5B8C2198B7892A857D67AF8D28E42BDB7C77154C851A74F17AC2AA78541404"
_SENTINEL_RE = re.compile(rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$')


class ContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
    if len(matches) != 1:
        raise ContractError("evaluator must contain exactly one valid sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D:")
    return resolved


def load_module(path: Path, expected_sha: str, name: str) -> ModuleType:
    if sha256_file(path) != expected_sha:
        raise ContractError(f"{name} hash mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_authority(workspace: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise ContractError("registry sentinel is not armed")
    paths = {"plan": workspace / PLAN_REL, "evaluator": workspace / EVALUATOR_REL, "test": workspace / TEST_REL, "registry": workspace / REGISTRY_REL}
    for label, path in paths.items():
        if not path.is_file():
            raise ContractError(f"{label} missing")
    if sha256_file(paths["plan"]) != PLAN_SHA256:
        raise ContractError("plan hash drift")
    payload = paths["evaluator"].read_bytes()
    base_sha = normalized_evaluator_base_sha256(payload)
    test_sha = sha256_file(paths["test"])
    candidates = []
    for raw in paths["registry"].read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            candidates.append((row, raw + b"\n"))
    if not candidates:
        raise ContractError("hypothesis absent from registry")
    row, line = candidates[-1]
    row_sha = sha256_bytes(line)
    if row_sha != REVIEWED_REGISTRY_ROW_SHA256:
        raise ContractError("sentinel is not latest hypothesis row")
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise ContractError("registry state or plan invalid")
    if validation.get("train_economic_evaluation_authorized") is not True or validation.get("one_use") is not True:
        raise ContractError("one-shot authority absent")
    if int(metrics.get("train_economic_attempts_consumed", -1)) != 0 or ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("attempt already consumed")
    expected = {
        "reviewed_evaluator_base_sha256": base_sha,
        "reviewed_test_sha256": test_sha,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "parent_evaluator_sha256": PARENT_SHA256,
        "canonical_dsr_sha256": DSR_SHA256,
    }
    for name, (_, ledger_sha) in LEDGERS.items():
        expected[f"prior_{name}_ledger_sha256"] = ledger_sha
    for key, value in expected.items():
        if validation.get(key) != value:
            raise ContractError(f"registry binding mismatch: {key}")
    for key in ("mql5_authorized", "model0_authorized", "optimization_authorized", "research_validation_access_authorized", "research_holdout_access_authorized", "paper_trading_authorized", "live_trading_authorized"):
        if validation.get(key) is not False:
            raise ContractError(f"forbidden authority open: {key}")
    return {"row_sha": row_sha, "base_sha": base_sha, "file_sha": sha256_bytes(payload), "test_sha": test_sha}


def build_trades_from_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if set(frame.columns) != {"time_utc", "close"}:
        raise ContractError("frame must contain exactly time_utc and close")
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if times.isna().any() or closes.isna().any() or times.duplicated().any() or not times.is_monotonic_increasing:
        raise ContractError("frame time/close integrity failed")
    if not np.isfinite(closes.to_numpy(dtype=float)).all() or (closes <= 0).any():
        raise ContractError("invalid close")
    local = times.dt.tz_convert(LOCAL_TZ)
    hhmm = local.dt.strftime("%H:%M")
    slots = hhmm.map({"07:59": "open", "14:14": "entry", "15:59": "exit"}).fillna("")
    mask = (local.dt.weekday < 5) & (slots != "")
    selected = pd.DataFrame({"local_date": local[mask].dt.date.to_numpy(), "slot": slots[mask].to_numpy(), "close": closes[mask].to_numpy(dtype=float)})
    if selected.duplicated(["local_date", "slot"]).any():
        raise ContractError("duplicate local date/slot")
    pivot = selected.pivot(index="local_date", columns="slot", values="close")
    for column in ("open", "entry", "exit"):
        if column not in pivot:
            pivot[column] = np.nan
    pivot = pivot[["open", "entry", "exit"]].dropna().sort_index()
    pressure = (pivot["entry"] - pivot["open"]) / PIP_SIZE
    threshold = pressure.abs().shift(1).rolling(LOOKBACK, min_periods=MIN_HISTORY).median()
    eligible = threshold.notna() & (pressure.abs() >= threshold) & (pressure != 0.0)
    pivot = pivot.loc[eligible].copy()
    pressure = pressure.loc[eligible]
    threshold = threshold.loc[eligible]
    direction = -np.sign(pressure.to_numpy()).astype(int)
    post_move = (pivot["exit"].to_numpy() - pivot["entry"].to_numpy()) / PIP_SIZE
    gross = direction * post_move
    trades = pd.DataFrame({
        "local_date": list(pivot.index), "year": [d.year for d in pivot.index], "weekday": [d.weekday() for d in pivot.index],
        "direction": direction, "entry_local_hhmm": ["14:14"] * len(pivot), "exit_local_hhmm": ["15:59"] * len(pivot),
        "open_close": pivot["open"].to_numpy(dtype=float), "entry_close": pivot["entry"].to_numpy(dtype=float), "exit_close": pivot["exit"].to_numpy(dtype=float),
        "pre_fix_pressure_pips": pressure.to_numpy(dtype=float), "pressure_threshold_pips": threshold.to_numpy(dtype=float),
        "post_fix_move_pips": post_move.astype(float), "gross_pips": gross.astype(float),
    })
    for label, cost in COSTS.items():
        trades[f"primary_net_{label}_pips"] = trades["gross_pips"] - cost
        trades[f"reverse_net_{label}_pips"] = -trades["gross_pips"] - cost
    return trades


def profit_factor(values: Iterable[float]) -> float | None:
    array = np.asarray(list(values), dtype=float)
    wins = float(array[array > 0].sum())
    losses = float(-array[array < 0].sum())
    return wins / losses if wins > 0 and losses > 0 else None


def sign_flip_p_value(values: Sequence[float], permutations: int = PERMUTATIONS, seed: int = PERMUTATION_SEED) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        raise ContractError("invalid sign-flip input")
    observed = float(array.mean())
    rng = np.random.default_rng(seed)
    exceed = sum(float(np.mean(array * rng.choice(np.array([-1.0, 1.0]), size=array.size))) >= observed for _ in range(permutations))
    return (1 + exceed) / (permutations + 1)


def read_pair(path: Path, expected_sha: str) -> tuple[np.ndarray, np.ndarray]:
    if sha256_file(path) != expected_sha:
        raise ContractError("prior ledger hash mismatch")
    primary, reverse = [], []
    for raw in path.read_bytes().splitlines():
        row = json.loads(raw)
        primary.append(float(row["primary_net_x1_pips"]))
        reverse.append(float(row["reverse_net_x1_pips"]))
    if len(primary) < 500 or len(primary) != len(reverse):
        raise ContractError("prior ledger population mismatch")
    return np.asarray(primary), np.asarray(reverse)


def load_prior_arms(workspace: Path) -> dict[str, np.ndarray]:
    arms = {}
    for name, (rel, expected_sha) in LEDGERS.items():
        primary, reverse = read_pair(require_d(workspace / rel, f"{name} ledger"), expected_sha)
        arms[f"{name}_primary"] = primary
        arms[f"{name}_reverse"] = reverse
    return arms


def arm_moments(values: Sequence[float]) -> dict[str, float | int]:
    series = pd.Series(np.asarray(values, dtype=float))
    std = float(series.std(ddof=1))
    if len(series) < 3 or not math.isfinite(std) or std <= 0:
        raise ContractError("invalid DSR arm")
    return {"n": len(series), "sr": float(series.mean()) / std, "skew": float(series.skew()), "kurtosis_non_excess": float(series.kurt()) + 3.0}


def compute_dsr(primary: Sequence[float], reverse: Sequence[float], prior: dict[str, np.ndarray], dsr: ModuleType) -> dict[str, object]:
    if len(prior) != 10:
        raise ContractError("prior arm universe mismatch")
    arms = {name: arm_moments(values) for name, values in prior.items()}
    arms["eurfxrev001_primary"] = arm_moments(primary)
    arms["eurfxrev001_reverse"] = arm_moments(reverse)
    variance = float(np.var([float(v["sr"]) for v in arms.values()], ddof=1))
    current = arms["eurfxrev001_primary"]
    value = float(dsr.dsr(float(current["sr"]), int(current["n"]), float(current["skew"]), float(current["kurtosis_non_excess"]), variance, len(arms)))
    if not math.isfinite(value):
        raise ContractError("non-finite DSR")
    return {"n_trials": len(arms), "variance_sr_trials": variance, "primary_dsr": value, "arms": arms}


def summarize_trades(trades: pd.DataFrame, prior: dict[str, np.ndarray], dsr: ModuleType, permutations: int = PERMUTATIONS) -> dict[str, object]:
    if trades.empty:
        return {"trade_count": 0, "source_gate_pass_count": 0, "source_gate_total": 5, "economic_gate_pass_count": 0, "economic_gate_total": 8}
    elapsed_weeks = float((DESIGN_END - DESIGN_START).total_seconds() / 604800)
    count = len(trades)
    cadence = count / elapsed_weeks
    year_count = {str(int(y)): int(len(g)) for y, g in trades.groupby("year")}
    max_year_share = max(year_count.values()) / count
    long_share = float((trades["direction"] == 1).mean())
    short_share = float((trades["direction"] == -1).mean())
    pf = {arm: {label: profit_factor(trades[f"{arm}_net_{label}_pips"]) for label in COSTS} for arm in ("primary", "reverse")}
    exp = {arm: {label: float(trades[f"{arm}_net_{label}_pips"].mean()) for label in COSTS} for arm in ("primary", "reverse")}
    annual = {str(int(y)): {"net_pips": float(g["primary_net_x1_pips"].sum()), "profit_factor": profit_factor(g["primary_net_x1_pips"])} for y, g in trades.groupby("year")}
    positive_years = sum(v["net_pips"] > 0 for v in annual.values())
    p_value = sign_flip_p_value(trades["gross_pips"], permutations=permutations)
    dsr_result = compute_dsr(trades["primary_net_x1_pips"], trades["reverse_net_x1_pips"], prior, dsr)
    exact = bool((trades["entry_local_hhmm"] == "14:14").all() and (trades["exit_local_hhmm"] == "15:59").all() and (trades["direction"] == -np.sign(trades["pre_fix_pressure_pips"])).all() and (trades["pre_fix_pressure_pips"].abs() >= trades["pressure_threshold_pips"]).all())
    structural = {"trade_count_ge_500": count >= 500, "cadence_2_to_3_5": 2 <= cadence <= 3.5, "max_year_share_le_0_30": max_year_share <= 0.30, "both_directions_ge_0_25": long_share >= 0.25 and short_share >= 0.25, "exact_rule": exact}
    p1, r1 = pf["primary"]["x1"], pf["reverse"]["x1"]
    economic = {
        "pf_x1_gt_1_30": p1 is not None and p1 > 1.30,
        "pf_x1_5_ge_1_25": pf["primary"]["x1_5"] is not None and pf["primary"]["x1_5"] >= 1.25,
        "pf_x2_ge_1_00": pf["primary"]["x2"] is not None and pf["primary"]["x2"] >= 1.0,
        "expectancy_x1_gt_0": exp["primary"]["x1"] > 0,
        "positive_years_ge_4_of_5": len(annual) == 5 and positive_years >= 4,
        "sign_flip_p_le_0_05": p_value <= 0.05,
        "dsr_ge_0_95": float(dsr_result["primary_dsr"]) >= 0.95,
        "beats_continuation_x1": p1 is not None and r1 is not None and p1 > r1 and exp["primary"]["x1"] > exp["reverse"]["x1"],
    }
    return {"trade_count": count, "first_local_date": min(trades["local_date"]).isoformat(), "last_local_date": max(trades["local_date"]).isoformat(), "elapsed_calendar_weeks": elapsed_weeks, "trades_per_elapsed_week": cadence, "year_count": year_count, "max_year_share": max_year_share, "long_share": long_share, "short_share": short_share, "gross_profit_factor": {"primary": profit_factor(trades["gross_pips"]), "reverse": profit_factor(-trades["gross_pips"])}, "gross_expectancy_pips": float(trades["gross_pips"].mean()), "profit_factor": pf, "expectancy_pips": exp, "annual_primary_x1": annual, "positive_years": positive_years, "sign_flip_one_sided_p_value": p_value, "deflated_sharpe": dsr_result, "structural_gates": structural, "economic_gates": economic, "source_gate_pass_count": sum(structural.values()), "source_gate_total": len(structural), "economic_gate_pass_count": sum(economic.values()), "economic_gate_total": len(economic)}


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def trade_rows(trades: pd.DataFrame) -> bytes:
    rows = []
    for row in trades.to_dict(orient="records"):
        day = row["local_date"].isoformat()
        payload = {"trade_id": f"EURFXREV001-{day}", "local_date": day}
        for key, value in row.items():
            if key == "local_date":
                continue
            if isinstance(value, (np.integer, int)):
                payload[key] = int(value)
            elif isinstance(value, (np.floating, float)):
                payload[key] = round(float(value), 10)
            else:
                payload[key] = value
        rows.append(canonical_json(payload) + b"\n")
    return b"".join(rows)


def render_chart(trades: pd.DataFrame, path: Path) -> None:
    import matplotlib.pyplot as plt
    equity_gross = trades["gross_pips"].cumsum()
    equity_net = trades["primary_net_x1_pips"].cumsum()
    annual = trades.groupby("year")["primary_net_x1_pips"].sum()
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    axes[0].plot(trades["local_date"], equity_gross, label="gross")
    axes[0].plot(trades["local_date"], equity_net, label="x1 net")
    axes[0].axhline(0, color="black", lw=.7); axes[0].legend(); axes[0].set_title("Cumulative pips")
    axes[1].bar(annual.index.astype(str), annual.values); axes[1].axhline(0, color="black", lw=.7); axes[1].set_title("Annual x1 net")
    axes[2].scatter(trades["pre_fix_pressure_pips"].abs(), trades["gross_pips"], s=7, alpha=.35)
    axes[2].axhline(0, color="black", lw=.7); axes[2].set_xlabel("|pre-fix pressure| pips"); axes[2].set_ylabel("post-fix reversal gross pips"); axes[2].set_title("Pressure vs reversal")
    fig.suptitle("HYP-EURFXREV-EURUSD-M1-001 TRAIN diagnostics")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def execute(workspace: Path) -> Path:
    workspace = require_d(workspace, "workspace")
    authority = validate_authority(workspace)
    parent = load_module(require_d(workspace / PARENT_REL, "parent evaluator"), PARENT_SHA256, "eurfxrev_parent")
    dsr = load_module(require_d(workspace / DSR_REL, "DSR"), DSR_SHA256, "eurfxrev_dsr")
    if sha256_file(workspace / PARQUET_REL) != PARQUET_SHA256 or sha256_file(workspace / MANIFEST_REL) != MANIFEST_SHA256:
        raise ContractError("dataset hash mismatch")
    evidence = require_d(workspace / EVIDENCE_ROOT_REL, "evidence root")
    if evidence.exists():
        raise ContractError("one-shot evidence root exists")
    started = evidence / "attempt_started.json"
    started_payload = {"schema_version": "eurfxrev001_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority["row_sha"], "evaluator_base_sha256": authority["base_sha"], "evaluator_file_sha256": authority["file_sha"], "test_sha256": authority["test_sha"], "validation_opened": False, "research_holdout_opened": False}
    write_new(started, canonical_json(started_payload) + b"\n")
    trades = build_trades_from_frame(parent.load_eurusd(workspace))
    prior = load_prior_arms(workspace)
    metrics = summarize_trades(trades, prior, dsr)
    verdict = VERDICT_STRUCTURAL if metrics["source_gate_pass_count"] < metrics["source_gate_total"] else VERDICT_PASS if metrics["economic_gate_pass_count"] == metrics["economic_gate_total"] else VERDICT_KILL
    ledger = evidence / "trades.jsonl"
    write_new(ledger, trade_rows(trades))
    chart = evidence / "eurfxrev_001_train_diagnostics.png"
    render_chart(trades, chart)
    terminal = evidence / "train_economic_terminal.json"
    terminal_payload = {"schema_version": "eurfxrev001_train_economic_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "verdict": verdict, "engineering_valid": True, "economic_edge_evaluated": verdict != VERDICT_STRUCTURAL, "plan_path": PLAN_REL, "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority["row_sha"], "evaluator_path": EVALUATOR_REL, "evaluator_base_sha256": authority["base_sha"], "evaluator_file_sha256": authority["file_sha"], "test_path": TEST_REL, "test_sha256": authority["test_sha"], "dataset_parquet_path": PARQUET_REL, "dataset_parquet_sha256": PARQUET_SHA256, "dataset_manifest_path": MANIFEST_REL, "dataset_manifest_sha256": MANIFEST_SHA256, "parent_evaluator_path": PARENT_REL, "parent_evaluator_sha256": PARENT_SHA256, "prior_ledgers": {name: {"path": rel, "sha256": sha} for name, (rel, sha) in LEDGERS.items()}, "canonical_dsr_path": DSR_REL, "canonical_dsr_sha256": DSR_SHA256, "attempt_started_sha256": sha256_file(started), "trades_path": str(ledger.relative_to(workspace)).replace("\\", "/"), "trades_sha256": sha256_file(ledger), "diagnostic_chart_path": str(chart.relative_to(workspace)).replace("\\", "/"), "diagnostic_chart_sha256": sha256_file(chart), "metrics": metrics, "forbidden_counters": {"bars_read_2021plus": 0, "research_validation_opened": False, "research_holdout_opened": False, "mt5_launches": 0, "mql5_files_created": 0, "model0_runs": 0, "model4_runs": 0, "optimization_trials": 0, "orders_submitted": 0, "paper_trading": False, "live_trading": False}, "authority_after_verdict": {"mql5_model0_packet_may_be_preregistered": verdict == VERDICT_PASS, "validation_authorized": False, "holdout_authorized": False, "optimization_authorized": False, "promotion_eligible": False, "paper_trading_authorized": False, "live_trading_authorized": False}}
    write_new(terminal, canonical_json(terminal_payload) + b"\n")
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    terminal = execute(args.workspace.resolve())
    result = json.loads(terminal.read_text(encoding="utf-8"))
    metrics = result["metrics"]
    print(f"EURFXREV001_RESULT verdict={result['verdict']} trades={metrics['trade_count']} pf_x1={metrics['profit_factor']['primary']['x1']:.6f} dsr={metrics['deflated_sharpe']['primary_dsr']:.6f}")
    print(f"TERMINAL {terminal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
