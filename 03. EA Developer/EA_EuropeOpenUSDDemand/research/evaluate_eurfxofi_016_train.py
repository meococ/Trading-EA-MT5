#!/usr/bin/env python3
"""HYP016 one-shot TRAIN evaluator using the reviewed HYP014 evaluator foundation."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-016"
ATTEMPT_ID = "EURFXOFI016-TRAIN-ECON-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-016_TRAIN_ECONOMIC_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfxofi_016_train.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfxofi_016_train.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
FOUNDATION_REL = BASE_REL + "evaluate_eurfxofi_014_train.py"
FOUNDATION_SHA256 = "ADFA888F7A05BA35C9009ED2A464B84A2321DCE47236DCD7EA39F857205795A6"
PLAN_SHA256 = "DC7A436F7B78F8F6353A401683B6E4A2A41876C2BB0A9A6284049A1D54FBD2B1"


REVIEWED_REGISTRY_ROW_SHA256: str | None = "DF21475753527321AF5ADBF8903D5046E4757D5240DA6C525F391CE197E48FBA"
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
    spec = importlib.util.spec_from_file_location("eurfxofi016_foundation", path)
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
    module.DISPLAY_TAG = "HYP016"
    module.ARTIFACT_PREFIX = "EURFXOFI016"
    module.SCHEMA_PREFIX = "eurfxofi016"
    module.RUN_ELIGIBLE_STATE = "probe"
    module.ALLOWED_MISSING_TARGET_DATES = ("2017-09-28",)
    module.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
    return module


def main() -> int:
    return int(configure().main())


if __name__ == "__main__":
    raise SystemExit(main())
