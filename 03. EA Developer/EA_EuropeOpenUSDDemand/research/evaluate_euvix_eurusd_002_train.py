#!/usr/bin/env python3
"""Pre-outcome V2 evaluator for HYP-EUVIX-EURUSD-M1-002."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EUVIX-EURUSD-M1-002"
ATTEMPT_ID = "EUVIX002-TRAIN-ECON-001"
PLAN_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/HYP-EUVIX-EURUSD-M1-002_TRAIN_ECONOMIC_PROBE_PLAN_V2.md"
PLAN_SHA256 = "26CB850427719016E61AA73C1AC673A602E34FF7AE7510387A4398E5C087FAE6"
EVALUATOR_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evaluate_euvix_eurusd_002_train.py"
TEST_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/tests/test_evaluate_euvix_eurusd_002_train.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
V1_EVALUATOR_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evaluate_euvix_eurusd_001_train.py"
V1_EVALUATOR_SHA256 = "9F02D64C25CED62559B56CF2ED5F913AF205E073E9D5CF80E1EE6481F06E8C7F"
V1_STARTED_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUVIX-EURUSD-M1-001/EUVIX001-TRAIN-ECON-001/attempt_started.json"
V1_STARTED_SHA256 = "8F4CB0C02F0F38ADFBF1A45EFDD1A1CB2D25378DCFABBF568539C61D3EAEFD6F"
V1_ABORT_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUVIX-EURUSD-M1-001/EUVIX001-TRAIN-ECON-001/engineering_abort.json"
V1_ABORT_SHA256 = "7C988710F998D6FE2ADCFDECF303EF4A13E4EF531629B93EF0D5CFAE570D9CD0"
VIX_CSV_REL = "02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.csv"
VIX_CSV_SHA256 = "2280FF566149A58E2FD3B137686D94D9C0E6E2C884C2A77BC02BA7FFB7F6B248"
VIX_MANIFEST_REL = "02. AlphaFactory/data/fred/VIXCLS/VIXCLS_2015-12-01_2020-12-31.manifest.v2.json"
VIX_MANIFEST_SHA256 = "4E9FBF69D30143A03297CD9C4B0FB1455A83F221AF207A3966E670B2822AB74A"
EVIDENCE_ROOT_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/HYP-EUVIX-EURUSD-M1-002/EUVIX002-TRAIN-ECON-001"
CHUNK_SIZE = 1024 * 1024

VERDICT_PASS = "PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY"
VERDICT_KILL = "KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED"
VERDICT_STRUCTURAL = "KILL_STRUCTURAL_NO_ECONOMICS_SURVIVOR"

REVIEWED_REGISTRY_ROW_SHA256: str | None = "1A88694B96C67AD9FB472EF204F295C8C5B342B83754A9EEB535291D2C839368"
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


def load_v1(workspace: Path) -> ModuleType:
    path = require_d_side(workspace / V1_EVALUATOR_REL, label="V1 evaluator")
    if sha256_file(path) != V1_EVALUATOR_SHA256:
        raise ContractError("V1 evaluator hash mismatch")
    spec = importlib.util.spec_from_file_location("euvix002_bound_v1", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load V1 evaluator")
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
        row = json.loads(raw)
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
        raise ContractError("one-use authority missing")
    if int(metrics.get("train_economic_attempts_consumed", -1)) != 0 or ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("attempt already consumed")
    expected = {"reviewed_evaluator_base_sha256": base_sha, "reviewed_test_sha256": test_sha, "v1_evaluator_sha256": V1_EVALUATOR_SHA256, "v1_attempt_started_sha256": V1_STARTED_SHA256, "v1_engineering_abort_sha256": V1_ABORT_SHA256, "vix_csv_sha256": VIX_CSV_SHA256, "vix_manifest_v2_sha256": VIX_MANIFEST_SHA256}
    for key, value in expected.items():
        if validation.get(key) != value:
            raise ContractError(f"registry binding mismatch: {key}")
    for key in ("mql5_authorized", "model0_authorized", "optimization_authorized", "research_validation_access_authorized", "research_holdout_access_authorized", "paper_trading_authorized", "live_trading_authorized"):
        if validation.get(key) is not False:
            raise ContractError(f"forbidden authority is not false: {key}")
    return Authority(row_sha, base_sha, file_sha, test_sha)


def load_vix_v2(workspace: Path) -> pd.DataFrame:
    csv_path = require_d_side(workspace / VIX_CSV_REL, label="VIX CSV")
    manifest_path = require_d_side(workspace / VIX_MANIFEST_REL, label="VIX V2 manifest")
    if sha256_file(csv_path) != VIX_CSV_SHA256 or sha256_file(manifest_path) != VIX_MANIFEST_SHA256:
        raise ContractError("VIX V2 hash mismatch")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("csv_sha256") != VIX_CSV_SHA256 or manifest.get("raw_row_count") != 1328 or manifest.get("valid_numeric_close_count") != 1281 or manifest.get("missing_close_count") != 47:
        raise ContractError("VIX V2 manifest count mismatch")
    if manifest.get("feature_only_preoutcome_checks", {}).get("target_returns_joined_or_read") is not False:
        raise ContractError("VIX V2 manifest outcome-blind flag invalid")
    raw = pd.read_csv(csv_path)
    if list(raw.columns) != ["observation_date", "VIXCLS"] or len(raw) != 1328:
        raise ContractError("VIX raw schema/population mismatch")
    raw["vix_date"] = pd.to_datetime(raw["observation_date"], errors="coerce")
    raw["vix_close"] = pd.to_numeric(raw["VIXCLS"], errors="coerce")
    if raw["vix_date"].isna().any() or int(raw["vix_close"].isna().sum()) != 47:
        raise ContractError("VIX missing-value contract mismatch")
    frame = raw.dropna(subset=["vix_close"])[["vix_date", "vix_close"]].sort_values("vix_date").reset_index(drop=True)
    if len(frame) != 1281 or frame["vix_date"].duplicated().any() or not frame["vix_date"].is_monotonic_increasing:
        raise ContractError("VIX valid population invalid")
    if not np.isfinite(frame["vix_close"]).all() or (frame["vix_close"] <= 0).any():
        raise ContractError("VIX valid closes invalid")
    frame["vix_threshold"] = frame["vix_close"].shift(1).rolling(252, min_periods=60).median()
    return frame


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def execute(workspace: Path) -> Path:
    workspace = require_d_side(workspace, label="workspace")
    authority = validate_authority(workspace)
    v1 = load_v1(workspace)
    for rel, sha, label in ((V1_STARTED_REL, V1_STARTED_SHA256, "V1 attempt"), (V1_ABORT_REL, V1_ABORT_SHA256, "V1 abort")):
        if sha256_file(require_d_side(workspace / rel, label=label)) != sha:
            raise ContractError(f"{label} hash mismatch")
    evidence = require_d_side(workspace / EVIDENCE_ROOT_REL, label="evidence root")
    if evidence.exists():
        raise ContractError("one-shot evidence root already exists")
    started_path = evidence / "attempt_started.json"
    started = {"schema_version": "euvix002_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority.row_sha256, "evaluator_base_sha256": authority.evaluator_base_sha256, "evaluator_file_sha256": authority.evaluator_file_sha256, "test_sha256": authority.test_sha256, "v1_evaluator_sha256": V1_EVALUATOR_SHA256, "v1_attempt_started_sha256": V1_STARTED_SHA256, "v1_engineering_abort_sha256": V1_ABORT_SHA256, "vix_csv_sha256": VIX_CSV_SHA256, "vix_manifest_v2_sha256": VIX_MANIFEST_SHA256, "validation_opened": False, "research_holdout_opened": False}
    write_new(started_path, canonical_json(started) + b"\n")
    parent = v1.load_parent_ledger(workspace)
    selected, coverage = v1.select_high_vix(parent, load_vix_v2(workspace))
    parent_module = v1.load_parent_module(workspace)
    dsr_module = parent_module.load_common(workspace).load_helper(workspace).load_dsr_module(workspace)
    prior = v1.load_prior_arms(workspace)
    metrics = v1.summarize(selected, mapping_coverage=coverage, prior=prior, dsr_module=dsr_module)
    verdict = VERDICT_STRUCTURAL if metrics["source_gate_pass_count"] < metrics["source_gate_total"] else VERDICT_PASS if metrics["economic_gate_pass_count"] == metrics["economic_gate_total"] else VERDICT_KILL
    trades_path = evidence / "trades.jsonl"
    write_new(trades_path, v1.trade_rows(selected))
    terminal_path = evidence / "train_economic_terminal.json"
    terminal = {"schema_version": "euvix002_train_economic_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "verdict": verdict, "engineering_valid": True, "economic_edge_evaluated": verdict != VERDICT_STRUCTURAL, "plan_path": PLAN_REL, "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority.row_sha256, "evaluator_path": EVALUATOR_REL, "evaluator_base_sha256": authority.evaluator_base_sha256, "evaluator_file_sha256": authority.evaluator_file_sha256, "test_path": TEST_REL, "test_sha256": authority.test_sha256, "v1_evaluator_path": V1_EVALUATOR_REL, "v1_evaluator_sha256": V1_EVALUATOR_SHA256, "v1_attempt_started_sha256": V1_STARTED_SHA256, "v1_engineering_abort_sha256": V1_ABORT_SHA256, "vix_csv_path": VIX_CSV_REL, "vix_csv_sha256": VIX_CSV_SHA256, "vix_manifest_v2_path": VIX_MANIFEST_REL, "vix_manifest_v2_sha256": VIX_MANIFEST_SHA256, "attempt_started_sha256": sha256_file(started_path), "trades_path": str(trades_path.relative_to(workspace)).replace("\\", "/"), "trades_sha256": sha256_file(trades_path), "metrics": metrics, "forbidden_counters": {"validation_opened": False, "research_holdout_opened": False, "mt5_launches": 0, "mql5_files_created": 0, "model0_runs": 0, "optimization_trials": 0, "orders_submitted": 0, "paper_trading": False, "live_trading": False}, "authority_after_verdict": {"mql5_model0_packet_may_be_preregistered": verdict == VERDICT_PASS, "validation_authorized": False, "holdout_authorized": False, "optimization_authorized": False, "promotion_eligible": False, "paper_trading_authorized": False, "live_trading_authorized": False}}
    write_new(terminal_path, canonical_json(terminal) + b"\n")
    return terminal_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    path = execute(args.workspace.resolve())
    terminal = json.loads(path.read_text())
    metrics = terminal["metrics"]
    print(f"EUVIX002_RESULT verdict={terminal['verdict']} trades={metrics['trade_count']} pf_x1={metrics['profit_factor']['primary']['x1']:.6f} dsr={metrics['deflated_sharpe']['primary_dsr']:.6f}")
    print(f"TERMINAL {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
