#!/usr/bin/env python3
"""HYP015 one-shot TRAIN evaluator using the reviewed HYP014 evaluator foundation."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-015"
ATTEMPT_ID = "EURFXOFI015-TRAIN-ECON-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-015_TRAIN_ECONOMIC_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfxofi_015_train.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfxofi_015_train.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
FOUNDATION_REL = BASE_REL + "evaluate_eurfxofi_014_train.py"
FOUNDATION_SHA256 = "F8DF1D7446BA3FFE87BD15E221BDE1384610BAA7D8133117B82B6A3F1278B80F"
PLAN_SHA256 = "CA00DB55EB9185925801558D9A50B824ADCA680EB61D2B287012CD8B9D75CCAA"


REVIEWED_REGISTRY_ROW_SHA256: str | None = "10C9AEAD4CCC84E6962AFBB73BD50DD25C67B227D62AC684EF887421B6B95A49"
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


def load_foundation(root: Path) -> ModuleType:
    path = root / FOUNDATION_REL
    if not path.is_file() or sha256_file(path) != FOUNDATION_SHA256:
        raise ContractError("HYP014 evaluator foundation hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfxofi015_foundation", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load HYP014 evaluator foundation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    module.DISPLAY_TAG = "HYP015"
    module.ARTIFACT_PREFIX = "EURFXOFI015"
    module.SCHEMA_PREFIX = "eurfxofi015"
    module.RUN_ELIGIBLE_STATE = "probe"
    module.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
    return module


def main() -> int:
    return int(configure().main())


if __name__ == "__main__":
    raise SystemExit(main())
