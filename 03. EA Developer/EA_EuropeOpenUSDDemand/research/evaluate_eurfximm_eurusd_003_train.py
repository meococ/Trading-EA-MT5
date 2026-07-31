#!/usr/bin/env python3
"""HYP-EURFXIMM-003 exact empty-missing-set / 609-trade successor."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence


HYPOTHESIS_ID = "HYP-EURFXIMM-EURUSD-M1-003"
ATTEMPT_ID = "EURFXIMM003-TRAIN-ECON-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXIMM-EURUSD-M1-003_TRAIN_ECONOMIC_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfximm_eurusd_003_train.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfximm_eurusd_003_train.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PARENT_REL = BASE_REL + "evaluate_eurfximm_eurusd_002_train.py"
PARENT_SHA256 = "37DD4A715BFA1B27FB0B0E9A82D438BBE0DE4B3F6E69F414BC00986898330696"
PLAN_SHA256 = "60EAE1B889D73225ADBF62BF4F3CB51FC529D8000BAE75DD1AFC3D5D17AE37AF"
EXPECTED_TRADES = 609


REVIEWED_REGISTRY_ROW_SHA256: str | None = "C593532C977E7B53FBF265A727051F45439F57A0E2C0924A336EA220A17D2FD0"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    pass


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


def load_parent(root: Path) -> ModuleType:
    path = root / PARENT_REL
    if not path.is_file() or sha256_file(path) != PARENT_SHA256:
        raise ContractError("HYPIMM002 parent wrapper hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfximm003_parent", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load HYPIMM002 parent wrapper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _correct_summary(original: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
    metrics = original(*args, **kwargs)
    gates = metrics["structural_gates"]
    gates.pop("exact_608_trades", None)
    trades = args[0]
    gates["exact_609_trades"] = len(trades) == EXPECTED_TRADES
    metrics["structural_gate_pass_count"] = sum(gates.values())
    metrics["structural_gate_total"] = len(gates)
    return metrics


def configure(root: Path | None = None) -> ModuleType:
    base = root or workspace()
    parent = load_parent(base)
    module = parent.configure(base)
    module.HYPOTHESIS_ID = HYPOTHESIS_ID
    module.ATTEMPT_ID = ATTEMPT_ID
    module.PLAN_REL = PLAN_REL
    module.EVALUATOR_REL = EVALUATOR_REL
    module.TEST_REL = TEST_REL
    module.EVIDENCE_ROOT_REL = EVIDENCE_ROOT_REL
    module.PLAN_SHA256 = PLAN_SHA256
    module.DISPLAY_TAG = "HYPIMM003"
    module.ARTIFACT_PREFIX = "EURFXIMM003"
    module.SCHEMA_PREFIX = "eurfximm003"
    module.RUN_ELIGIBLE_STATE = "probe"
    module.ALLOWED_MISSING_TARGET_DATES = ()
    module.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
    original_summary = module.summarize_trades
    module.summarize_trades = lambda *args, **kwargs: _correct_summary(
        original_summary, *args, **kwargs
    )
    return module


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace())
    args = parser.parse_args(argv)
    module = configure(args.workspace.resolve())
    try:
        terminal = module.execute(args.workspace.resolve())
    except module.ContractError as exc:
        print(f"EURFXIMM003_ERROR {exc}", file=sys.stderr)
        return 2
    payload = json.loads(terminal.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    pf_x1 = metrics["arms"]["flow_continuation_primary"]["profit_factor"]["x1"]
    print(
        f"EURFXIMM003_RESULT verdict={payload['verdict']} "
        f"trades={metrics['trade_count']} pf_x1={pf_x1} "
        f"economic_gates={metrics['economic_gate_pass_count']}/{metrics['economic_gate_total']}"
    )
    print(f"TERMINAL {terminal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
