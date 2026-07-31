#!/usr/bin/env python3
"""HYP002 one-shot validation wrapper over the reviewed HYP001 foundation."""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType


HYPOTHESIS_ID = "HYP-EURFXMOM-EURUSD-M1-002"
ATTEMPT_ID = "EURFXMOM002-VALIDATION-001"
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXMOM-EURUSD-M1-002_VALIDATION_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfxmom_eurusd_002_validation.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfxmom_eurusd_002_validation.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"
FOUNDATION_REL = BASE_REL + "evaluate_eurfxmom_eurusd_001_validation.py"
FOUNDATION_SHA256 = "3B7ACBEB9C2420DF9C9A288BBC6F5E2A1ABF9539BFE6970CB21DF3FC2C3804AD"
PLAN_SHA256 = "AA69DA46D7D18C7C14DA74A1F4405CBE4F7345E76E80AFC7AB6BF2781A48940C"

REVIEWED_REGISTRY_ROW_SHA256: str | None = None
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
    matches = [
        index
        for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("wrapper must contain exactly one review sentinel")
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return hashlib.sha256(b"".join(lines)).hexdigest().upper()


def load_foundation(root: Path) -> ModuleType:
    path = root / FOUNDATION_REL
    if not path.is_file() or sha256_file(path) != FOUNDATION_SHA256:
        raise ContractError("HYP001 validation foundation hash mismatch")
    spec = importlib.util.spec_from_file_location("eurfxmom002_foundation", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load HYP001 validation foundation")
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
    module.ARTIFACT_PREFIX = "EURFXMOM002"
    module.SCHEMA_PREFIX = "eurfxmom002"
    module.DISPLAY_TAG = "EURFXMOM002"
    module.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
    return module


def main() -> int:
    return int(configure().main())


if __name__ == "__main__":
    raise SystemExit(main())
