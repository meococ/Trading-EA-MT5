#!/usr/bin/env python3
"""One-shot TRAIN evaluator wrapper for HYP-LOMX-MULTI-M1-002."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Iterable


BASE_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "evaluate_lomx_001_train.py"
)
HYPOTHESIS_ID = "HYP-LOMX-MULTI-M1-002"
ATTEMPT_ID = "LOMX002-TRAIN-EVAL-001"
PLAN_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "HYP-LOMX-MULTI-M1-002_TRAIN_PROBE_PLAN.md"
)
SCRIPT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "evaluate_lomx_002_train.py"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)


def _load_base():
    path = Path(__file__).with_name("evaluate_lomx_001_train.py")
    spec = importlib.util.spec_from_file_location("lomx_001_evaluator_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load HYP001 evaluator base")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_base()
ContractError = base.ContractError


def configure_base() -> None:
    base.HYPOTHESIS_ID = HYPOTHESIS_ID
    base.ATTEMPT_ID = ATTEMPT_ID
    base.PLAN_REL = PLAN_REL
    base.SCRIPT_REL = SCRIPT_REL
    base.EVIDENCE_ROOT_REL = EVIDENCE_ROOT_REL


def verify_base_binding(workspace: Path) -> None:
    row, _ = base.latest_registry_row(workspace / base.REGISTRY_REL)
    validation = row.get("validation") or {}
    if validation.get("reviewed_evaluator_base_path") != BASE_REL:
        raise ContractError("evaluator base path mismatch")
    expected = str(validation.get("reviewed_evaluator_base_sha256", "")).upper()
    if base.sha256_file(workspace / BASE_REL) != expected:
        raise ContractError("evaluator base SHA mismatch")


def main(argv: Iterable[str] | None = None) -> int:
    configure_base()
    args = base.build_parser().parse_args(list(argv) if argv is not None else None)
    if not args.production:
        raise ContractError("production is disarmed; pass --production")
    if not args.reviewed_registry_row_sha256:
        raise ContractError("reviewed registry row SHA is required")
    workspace = Path(args.workspace)
    verify_base_binding(workspace)
    terminal = base.evaluate(
        workspace,
        reviewed_registry_sha=str(args.reviewed_registry_row_sha256),
    )
    print(json.dumps(terminal, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"LOMX002_EVALUATOR_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
