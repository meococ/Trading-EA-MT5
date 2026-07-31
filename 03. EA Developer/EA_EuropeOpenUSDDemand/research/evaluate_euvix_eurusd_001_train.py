#!/usr/bin/env python3
"""One-shot lagged-VIX TRAIN evaluator for HYP-EUVIX-EURUSD-M1-001."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EUVIX-EURUSD-M1-001"
ATTEMPT_ID = "EUVIX001-TRAIN-ECON-001"
PLAN_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/HYP-EUVIX-EURUSD-M1-001_TRAIN_ECONOMIC_PROBE_PLAN.md"
PLAN_SHA256 = "2E91AE2F91901A97E1B81F68E0F697CF280A1DB4719AE6D13A07FE71629F08F9"
EVALUATOR_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evaluate_euvix_eurusd_001_train.py"
TEST_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/tests/test_evaluate_euvix_eurusd_001_train.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
LOJM_LEDGER_REL = "03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001/trades.jsonl"
LOFIX_LEDGER_REL = "03. EA Developer/EA_LondonFixHalfHourMomentum/research/evidence/HYP-LOFIX-USDJPY-M1-002/LOFIX002-TRAIN-ECON-001/trades.jsonl"
EUJPY_LEDGER_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUUSD-USDJPY-M1-001/EUUSD001-TRAIN-ECON-001/trades.jsonl"
PARENT_LEDGER_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUUSD-EURUSD-M1-001/EUEUR001-TRAIN-ECON-001/trades.jsonl"
PARENT_EVALUATOR_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evaluate_euusd_eurusd_001_train.py"
VIX_CSV_REL = "02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.csv"
VIX_MANIFEST_REL = "02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.manifest.json"
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
EVIDENCE_ROOT_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUVIX-EURUSD-M1-001/EUVIX001-TRAIN-ECON-001"

LOJM_LEDGER_SHA256 = "6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98"
LOFIX_LEDGER_SHA256 = "04270A2E9772A884322753701D55B6101109B1BA1E49ABFF59F89B882815A6DB"
EUJPY_LEDGER_SHA256 = "18D8C2333FE421DFA279325D30A29D759AAD4333A304BA1FC68E7B485009E10C"
PARENT_LEDGER_SHA256 = "204050AAA213DB1BC468FD022733425DC3E2E70EF33A742A0A7D620EF8B166E8"
PARENT_EVALUATOR_SHA256 = "0FB3FF4AE1326958FC911B7228DF9AF8526201A9506EF97C6DAFF7E9FBA9BFEE"
VIX_CSV_SHA256 = "2280FF566149A58E2FD3B137686D94D9C0E6E2C884C2A77BC02BA7FFB7F6B248"
VIX_MANIFEST_SHA256 = "864AEA48C737A091D7DE0C5503C72551015C4C20EEF70814595A5CD34B80BA7C"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
DESIGN_START = pd.Timestamp("2016-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2020-12-31T23:59:59Z")
COSTS = {"x1": 1.50, "x1_5": 2.25, "x2": 3.00}
PARENT_PF_X1 = 0.9687234884904704
PARENT_EXPECTANCY_X1 = -0.29868827160493405
PERMUTATIONS = 10_000
PERMUTATION_SEED = 20_260_729
CHUNK_SIZE = 1024 * 1024

VERDICT_PASS = "PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY"
VERDICT_KILL = "KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED"
VERDICT_STRUCTURAL = "KILL_STRUCTURAL_NO_ECONOMICS_SURVIVOR"

REVIEWED_REGISTRY_ROW_SHA256: str | None = "91B3F56D47127D18A3A01E8426768703C9B93B74FEEEBAB21F8255483AA33F1E"
_SENTINEL_RE = re.compile(rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$')


class ContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class Authority:
    row_sha256: str
    evaluator_base_sha256: str
    evaluator_file_sha256: str
    test_sha256: str


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
    if len(matches) != 1:
        raise ContractError("evaluator must contain exactly one valid sentinel")
    i = matches[0]
    newline = b"\n" if lines[i].endswith(b"\n") else b""
    lines[i] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d_side(path: Path, *, label: str) -> Path:
    resolved = Path(path).resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D: storage")
    return resolved


def load_parent_module(workspace: Path) -> ModuleType:
    path = require_d_side(workspace / PARENT_EVALUATOR_REL, label="parent evaluator")
    if sha256_file(path) != PARENT_EVALUATOR_SHA256:
        raise ContractError("parent evaluator hash mismatch")
    spec = importlib.util.spec_from_file_location("euvix_bound_parent", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load parent evaluator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_authority(workspace: Path) -> Authority:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise ContractError("evaluator registry sentinel is not armed")
    plan, evaluator, test, registry = workspace / PLAN_REL, workspace / EVALUATOR_REL, workspace / TEST_REL, workspace / REGISTRY_REL
    for label, path in (("plan", plan), ("evaluator", evaluator), ("test", test), ("registry", registry)):
        if not path.is_file():
            raise ContractError(f"{label} file is missing")
    if sha256_file(plan) != PLAN_SHA256:
        raise ContractError("plan hash drift")
    payload = evaluator.read_bytes()
    base_sha, file_sha, test_sha = normalized_evaluator_base_sha256(payload), sha256_bytes(payload), sha256_file(test)
    candidates = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError("registry contains invalid JSONL") from exc
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            candidates.append((row, raw + b"\n"))
    if not candidates:
        raise ContractError("hypothesis absent from registry")
    row, line = candidates[-1]
    row_sha = sha256_bytes(line)
    if row_sha != REVIEWED_REGISTRY_ROW_SHA256:
        raise ContractError("armed row is not latest")
    validation, metrics = row.get("validation"), row.get("metrics")
    if type(validation) is not dict or type(metrics) is not dict:
        raise ContractError("registry authority fields missing")
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise ContractError("registry state or plan mismatch")
    if validation.get("train_economic_evaluation_authorized") is not True or validation.get("one_use") is not True:
        raise ContractError("one-use economic authority missing")
    if int(metrics.get("train_economic_attempts_consumed", -1)) != 0 or ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("attempt already consumed")
    expected = {"reviewed_evaluator_base_sha256": base_sha, "reviewed_test_sha256": test_sha, "prior_lojm_ledger_sha256": LOJM_LEDGER_SHA256, "prior_lofix_ledger_sha256": LOFIX_LEDGER_SHA256, "prior_euusd_usdjpy_ledger_sha256": EUJPY_LEDGER_SHA256, "parent_eurusd_ledger_sha256": PARENT_LEDGER_SHA256, "parent_evaluator_sha256": PARENT_EVALUATOR_SHA256, "vix_csv_sha256": VIX_CSV_SHA256, "vix_manifest_sha256": VIX_MANIFEST_SHA256, "canonical_dsr_sha256": DSR_SHA256}
    for key, value in expected.items():
        if validation.get(key) != value:
            raise ContractError(f"registry binding mismatch: {key}")
    for key in ("mql5_authorized", "model0_authorized", "optimization_authorized", "research_validation_access_authorized", "research_holdout_access_authorized", "paper_trading_authorized", "live_trading_authorized"):
        if validation.get(key) is not False:
            raise ContractError(f"forbidden authority is not false: {key}")
    return Authority(row_sha, base_sha, file_sha, test_sha)


def load_parent_ledger(workspace: Path) -> pd.DataFrame:
    path = require_d_side(workspace / PARENT_LEDGER_REL, label="parent ledger")
    if sha256_file(path) != PARENT_LEDGER_SHA256:
        raise ContractError("parent ledger hash mismatch")
    try:
        frame = pd.DataFrame(json.loads(line) for line in path.read_text().splitlines())
    except (json.JSONDecodeError, OSError) as exc:
        raise ContractError("parent ledger invalid") from exc
    required = {"local_date", "year", "weekday", "direction", "entry_local_hhmm", "exit_local_hhmm", "gross_pips", "primary_net_x1_pips", "primary_net_x1_5_pips", "primary_net_x2_pips", "reverse_net_x1_pips", "reverse_net_x1_5_pips", "reverse_net_x2_pips"}
    if len(frame) != 1296 or not required.issubset(frame.columns):
        raise ContractError("parent ledger population/schema mismatch")
    frame["trade_date"] = pd.to_datetime(frame["local_date"], errors="coerce")
    if frame["trade_date"].isna().any() or frame["trade_date"].duplicated().any() or not frame["trade_date"].is_monotonic_increasing:
        raise ContractError("parent dates invalid")
    if not (frame["direction"] == "SHORT").all() or not (frame["entry_local_hhmm"] == "07:59").all() or not (frame["exit_local_hhmm"] == "14:14").all():
        raise ContractError("parent execution contract drift")
    gross = pd.to_numeric(frame["gross_pips"], errors="coerce")
    if gross.isna().any() or not np.isfinite(gross).all():
        raise ContractError("parent gross PnL invalid")
    for label, cost in COSTS.items():
        if not np.allclose(frame[f"primary_net_{label}_pips"], gross - cost) or not np.allclose(frame[f"reverse_net_{label}_pips"], -gross - cost):
            raise ContractError("parent cost columns drift")
    return frame


def load_vix(workspace: Path) -> pd.DataFrame:
    csv_path = require_d_side(workspace / VIX_CSV_REL, label="VIX CSV")
    manifest_path = require_d_side(workspace / VIX_MANIFEST_REL, label="VIX manifest")
    if sha256_file(csv_path) != VIX_CSV_SHA256 or sha256_file(manifest_path) != VIX_MANIFEST_SHA256:
        raise ContractError("VIX hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("csv_sha256") != VIX_CSV_SHA256 or manifest.get("row_count") != 1281 or manifest.get("feature_only_preoutcome_checks", {}).get("target_returns_joined_or_read") is not False:
        raise ContractError("VIX manifest contract mismatch")
    frame = pd.read_csv(csv_path)
    if list(frame.columns) != ["observation_date", "VIXCLS"] or len(frame) != 1281:
        raise ContractError("VIX CSV schema/population mismatch")
    frame["vix_date"] = pd.to_datetime(frame["observation_date"], errors="coerce")
    frame["vix_close"] = pd.to_numeric(frame["VIXCLS"], errors="coerce")
    if frame[["vix_date", "vix_close"]].isna().any().any() or frame["vix_date"].duplicated().any() or not frame["vix_date"].is_monotonic_increasing:
        raise ContractError("VIX values or dates invalid")
    if not np.isfinite(frame["vix_close"]).all() or (frame["vix_close"] <= 0).any():
        raise ContractError("VIX closes invalid")
    frame["vix_threshold"] = frame["vix_close"].shift(1).rolling(252, min_periods=60).median()
    return frame[["vix_date", "vix_close", "vix_threshold"]]


def select_high_vix(parent: pd.DataFrame, vix: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    merged = pd.merge_asof(parent.sort_values("trade_date"), vix, left_on="trade_date", right_on="vix_date", direction="backward", allow_exact_matches=False)
    mapping_coverage = float(merged["vix_close"].notna().mean())
    selected = merged[merged["vix_threshold"].notna() & (merged["vix_close"] >= merged["vix_threshold"])].copy()
    selected["vix_lag_days"] = (selected["trade_date"] - selected["vix_date"]).dt.days
    if selected.empty or (selected["vix_lag_days"] < 1).any():
        raise ContractError("selected VIX mapping violates strict lag")
    return selected, mapping_coverage


def profit_factor(values: Iterable[float]) -> float | None:
    array = np.asarray(list(values), dtype=float)
    wins, losses = float(array[array > 0].sum()), float(-array[array < 0].sum())
    return wins / losses if wins > 0 and losses > 0 else None


def sign_flip_p_value(values: Sequence[float], *, permutations: int, seed: int) -> float:
    array = np.asarray(values, dtype=float)
    observed = float(array.mean())
    rng = np.random.default_rng(seed)
    exceed = sum(float(np.mean(array * rng.choice(np.array([-1.0, 1.0]), size=len(array)))) >= observed for _ in range(permutations))
    return (1 + exceed) / (permutations + 1)


def _read_pair(path: Path, expected_sha: str) -> tuple[np.ndarray, np.ndarray]:
    if sha256_file(path) != expected_sha:
        raise ContractError("prior ledger hash mismatch")
    primary, reverse = [], []
    for raw in path.read_bytes().splitlines():
        row = json.loads(raw); primary.append(float(row["primary_net_x1_pips"])); reverse.append(float(row["reverse_net_x1_pips"]))
    if len(primary) < 1000 or len(primary) != len(reverse):
        raise ContractError("prior ledger population mismatch")
    return np.asarray(primary), np.asarray(reverse)


def load_prior_arms(workspace: Path) -> dict[str, np.ndarray]:
    specs = [("lojm001", LOJM_LEDGER_REL, LOJM_LEDGER_SHA256), ("lofix002", LOFIX_LEDGER_REL, LOFIX_LEDGER_SHA256), ("euusd_usdjpy_001", EUJPY_LEDGER_REL, EUJPY_LEDGER_SHA256), ("euusd_eurusd_001", PARENT_LEDGER_REL, PARENT_LEDGER_SHA256)]
    arms = {}
    for name, rel, sha in specs:
        primary, reverse = _read_pair(require_d_side(workspace / rel, label=name), sha)
        arms[f"{name}_primary"] = primary; arms[f"{name}_reverse"] = reverse
    return arms


def _moments(values: Sequence[float]) -> dict[str, float | int]:
    series = pd.Series(np.asarray(values, dtype=float)); std = float(series.std(ddof=1))
    if len(series) < 3 or std <= 0 or not np.isfinite(series).all():
        raise ContractError("DSR arm invalid")
    return {"n": len(series), "sr": float(series.mean()) / std, "skew": float(series.skew()), "kurtosis_non_excess": float(series.kurt()) + 3}


def compute_dsr(primary: Sequence[float], reverse: Sequence[float], prior: dict[str, np.ndarray], module: ModuleType) -> dict[str, object]:
    if len(prior) != 8:
        raise ContractError("prior DSR arm universe mismatch")
    arms = {name: _moments(values) for name, values in prior.items()}
    arms["euvix001_primary"], arms["euvix001_reverse"] = _moments(primary), _moments(reverse)
    variance = float(np.var([float(x["sr"]) for x in arms.values()], ddof=1)); current = arms["euvix001_primary"]
    value = float(module.dsr(float(current["sr"]), int(current["n"]), float(current["skew"]), float(current["kurtosis_non_excess"]), variance, len(arms)))
    if not math.isfinite(value):
        raise ContractError("DSR non-finite")
    return {"n_trials": len(arms), "variance_sr_trials": variance, "expected_max_sr": float(module.expected_max_sharpe(variance, len(arms))), "primary_dsr": value, "arms": arms}


def summarize(selected: pd.DataFrame, *, mapping_coverage: float, prior: dict[str, np.ndarray], dsr_module: ModuleType, permutations: int = PERMUTATIONS, seed: int = PERMUTATION_SEED) -> dict[str, object]:
    count = len(selected); elapsed_weeks = float((DESIGN_END - DESIGN_START).total_seconds() / 604800); cadence = count / elapsed_weeks
    year_count = {str(int(y)): int(v) for y, v in selected.groupby("year").size().items()}; max_year_share = max(year_count.values()) / count
    pf, expectancy = {"primary": {}, "reverse": {}}, {"primary": {}, "reverse": {}}
    for arm in ("primary", "reverse"):
        for label in COSTS:
            values = selected[f"{arm}_net_{label}_pips"]; pf[arm][label] = profit_factor(values); expectancy[arm][label] = float(values.mean())
    annual = {str(int(y)): float(g["primary_net_x1_pips"].sum()) for y, g in selected.groupby("year")}; positive_years = sum(x > 0 for x in annual.values())
    p_value = sign_flip_p_value(selected["gross_pips"], permutations=permutations, seed=seed)
    dsr = compute_dsr(selected["primary_net_x1_pips"], selected["reverse_net_x1_pips"], prior, dsr_module)
    structural = {"selected_trades_ge_500": count >= 500, "vix_mapping_coverage_ge_0_95": mapping_coverage >= .95, "cadence_2_to_5": 2 <= cadence <= 5, "each_year_ge_30": len(year_count) == 5 and min(year_count.values()) >= 30, "max_year_share_le_0_40": max_year_share <= .40}
    primary_x1, reverse_x1 = pf["primary"]["x1"], pf["reverse"]["x1"]
    economic = {"pf_x1_gt_1_30": primary_x1 is not None and primary_x1 > 1.30, "pf_x1_5_ge_1_25": pf["primary"]["x1_5"] is not None and pf["primary"]["x1_5"] >= 1.25, "pf_x2_ge_1_00": pf["primary"]["x2"] is not None and pf["primary"]["x2"] >= 1, "expectancy_x1_gt_0": expectancy["primary"]["x1"] > 0, "positive_years_ge_4_of_5": len(annual) == 5 and positive_years >= 4, "sign_flip_p_le_0_05": p_value <= .05, "dsr_ge_0_95": float(dsr["primary_dsr"]) >= .95, "beats_reverse_and_parent_x1": primary_x1 is not None and reverse_x1 is not None and primary_x1 > reverse_x1 and expectancy["primary"]["x1"] > expectancy["reverse"]["x1"] and primary_x1 > PARENT_PF_X1 and expectancy["primary"]["x1"] > PARENT_EXPECTANCY_X1}
    return {"trade_count": count, "parent_trade_count": 1296, "vix_mapping_coverage": mapping_coverage, "elapsed_calendar_weeks": elapsed_weeks, "trades_per_elapsed_week": cadence, "year_count": year_count, "max_year_share": max_year_share, "gross_profit_factor": {"primary": profit_factor(selected["gross_pips"]), "reverse": profit_factor(-selected["gross_pips"])}, "gross_expectancy_pips": float(selected["gross_pips"].mean()), "profit_factor": pf, "expectancy_pips": expectancy, "annual_primary_x1_net_pips": annual, "positive_years": positive_years, "sign_flip_one_sided_p_value": p_value, "permutation_count": permutations, "permutation_seed": seed, "deflated_sharpe": dsr, "structural_gates": structural, "economic_gates": economic, "source_gate_pass_count": sum(structural.values()), "source_gate_total": len(structural), "economic_gate_pass_count": sum(economic.values()), "economic_gate_total": len(economic)}


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle: handle.write(payload)


def trade_rows(selected: pd.DataFrame) -> bytes:
    lines = []
    for row in selected.itertuples(index=False):
        payload = {"trade_id": f"EUVIX001-{row.local_date}", "local_date": row.local_date, "year": int(row.year), "weekday": int(row.weekday), "direction": "SHORT", "entry_local_hhmm": row.entry_local_hhmm, "exit_local_hhmm": row.exit_local_hhmm, "gross_pips": round(float(row.gross_pips), 10), "primary_net_x1_pips": round(float(row.primary_net_x1_pips), 10), "primary_net_x1_5_pips": round(float(row.primary_net_x1_5_pips), 10), "primary_net_x2_pips": round(float(row.primary_net_x2_pips), 10), "reverse_net_x1_pips": round(float(row.reverse_net_x1_pips), 10), "reverse_net_x1_5_pips": round(float(row.reverse_net_x1_5_pips), 10), "reverse_net_x2_pips": round(float(row.reverse_net_x2_pips), 10), "vix_observation_date": row.vix_date.date().isoformat(), "vix_close": float(row.vix_close), "vix_trailing_prior_252_median": float(row.vix_threshold), "vix_lag_days": int(row.vix_lag_days)}
        lines.append(canonical_json(payload) + b"\n")
    return b"".join(lines)


def execute(workspace: Path) -> Path:
    workspace = require_d_side(workspace, label="workspace"); authority = validate_authority(workspace); parent_module = load_parent_module(workspace)
    helper = parent_module.load_common(workspace).load_helper(workspace); dsr_module = helper.load_dsr_module(workspace); prior = load_prior_arms(workspace)
    evidence = require_d_side(workspace / EVIDENCE_ROOT_REL, label="evidence root")
    if evidence.exists(): raise ContractError("one-shot evidence root already exists")
    started_path = evidence / "attempt_started.json"
    started = {"schema_version": "euvix001_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority.row_sha256, "evaluator_base_sha256": authority.evaluator_base_sha256, "evaluator_file_sha256": authority.evaluator_file_sha256, "test_sha256": authority.test_sha256, "parent_ledger_sha256": PARENT_LEDGER_SHA256, "vix_csv_sha256": VIX_CSV_SHA256, "vix_manifest_sha256": VIX_MANIFEST_SHA256, "canonical_dsr_sha256": DSR_SHA256, "validation_opened": False, "research_holdout_opened": False}
    write_new(started_path, canonical_json(started) + b"\n")
    selected, coverage = select_high_vix(load_parent_ledger(workspace), load_vix(workspace)); metrics = summarize(selected, mapping_coverage=coverage, prior=prior, dsr_module=dsr_module)
    verdict = VERDICT_STRUCTURAL if metrics["source_gate_pass_count"] < metrics["source_gate_total"] else VERDICT_PASS if metrics["economic_gate_pass_count"] == metrics["economic_gate_total"] else VERDICT_KILL
    trades_path = evidence / "trades.jsonl"; write_new(trades_path, trade_rows(selected)); terminal_path = evidence / "train_economic_terminal.json"
    terminal = {"schema_version": "euvix001_train_economic_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "verdict": verdict, "engineering_valid": True, "economic_edge_evaluated": verdict != VERDICT_STRUCTURAL, "plan_path": PLAN_REL, "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority.row_sha256, "evaluator_path": EVALUATOR_REL, "evaluator_base_sha256": authority.evaluator_base_sha256, "evaluator_file_sha256": authority.evaluator_file_sha256, "test_path": TEST_REL, "test_sha256": authority.test_sha256, "parent_ledger_path": PARENT_LEDGER_REL, "parent_ledger_sha256": PARENT_LEDGER_SHA256, "vix_csv_path": VIX_CSV_REL, "vix_csv_sha256": VIX_CSV_SHA256, "vix_manifest_path": VIX_MANIFEST_REL, "vix_manifest_sha256": VIX_MANIFEST_SHA256, "attempt_started_sha256": sha256_file(started_path), "trades_path": str(trades_path.relative_to(workspace)).replace("\\", "/"), "trades_sha256": sha256_file(trades_path), "metrics": metrics, "forbidden_counters": {"validation_opened": False, "research_holdout_opened": False, "mt5_launches": 0, "mql5_files_created": 0, "model0_runs": 0, "optimization_trials": 0, "paid_requests_made": 0, "orders_submitted": 0, "paper_trading": False, "live_trading": False}, "authority_after_verdict": {"mql5_model0_packet_may_be_preregistered": verdict == VERDICT_PASS, "validation_authorized": False, "holdout_authorized": False, "optimization_authorized": False, "promotion_eligible": False, "paper_trading_authorized": False, "live_trading_authorized": False}}
    write_new(terminal_path, canonical_json(terminal) + b"\n"); return terminal_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--workspace", type=Path, default=workspace_from_source()); args = parser.parse_args()
    path = execute(args.workspace.resolve()); terminal = json.loads(path.read_text()); metrics = terminal["metrics"]
    print(f"EUVIX001_RESULT verdict={terminal['verdict']} trades={metrics['trade_count']} pf_x1={metrics['profit_factor']['primary']['x1']:.6f} dsr={metrics['deflated_sharpe']['primary_dsr']:.6f}"); print(f"TERMINAL {path}"); return 0


if __name__ == "__main__": raise SystemExit(main())
