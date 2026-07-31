#!/usr/bin/env python3
"""HYP-EURFXIMM-002 exact successor with a public-arm terminal entrypoint."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence


HYPOTHESIS_ID = "HYP-EURFXIMM-EURUSD-M1-002"
ATTEMPT_ID = "EURFXIMM002-TRAIN-ECON-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXIMM-EURUSD-M1-002_TRAIN_ECONOMIC_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfximm_eurusd_002_train.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfximm_eurusd_002_train.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
PARENT_REL = BASE_REL + "evaluate_eurfximm_eurusd_001_train.py"
PARENT_SHA256 = "20C7B8A5CFCEDB7EB502A960BFCA26E78F5D42A36F5AD66ECDF059A130EB527B"
PLAN_SHA256 = "587D7269661E3C4BB28678B5E3B0A7DBFEEB4B2DC56A5C7A5D5965E9EEA921AB"


REVIEWED_REGISTRY_ROW_SHA256: str | None = "E54D5F21DB1C9EDB20A934E860C25801B3C194496AC4DE5744CA767EA5EB8F23"
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
        raise ContractError("HYPIMM001 parent wrapper hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfximm002_parent", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load HYPIMM001 parent wrapper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    module.DISPLAY_TAG = "HYPIMM002"
    module.ARTIFACT_PREFIX = "EURFXIMM002"
    module.SCHEMA_PREFIX = "eurfximm002"
    module.RUN_ELIGIBLE_STATE = "probe"
    module.ALLOWED_MISSING_TARGET_DATES = ("2017-09-28",)
    module.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
    return module


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace())
    args = parser.parse_args(argv)
    module = configure(args.workspace.resolve())
    try:
        terminal = module.execute(args.workspace.resolve())
    except module.ContractError as exc:
        print(f"EURFXIMM002_ERROR {exc}", file=sys.stderr)
        return 2
    payload = json.loads(terminal.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    pf_x1 = metrics["arms"]["flow_continuation_primary"]["profit_factor"]["x1"]
    print(
        f"EURFXIMM002_RESULT verdict={payload['verdict']} "
        f"trades={metrics['trade_count']} pf_x1={pf_x1} "
        f"economic_gates={metrics['economic_gate_pass_count']}/{metrics['economic_gate_total']}"
    )
    print(f"TERMINAL {terminal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
