#!/usr/bin/env python3
"""Outcome-blind gate analyzer for HYP-QPF-EURUSD-M1-003.

HYP003 is an engineering-only identity/input-binding reissue. Its source gates
must remain byte-for-byte those independently reviewed for HYP002, so this
adapter hash-pins and reuses that analyzer while changing only the hypothesis
identity.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


HYPOTHESIS_ID = "HYP-QPF-EURUSD-M1-003"
BASE_PATH = Path(__file__).with_name("analyze_qpf_002_source.py")
BASE_SHA256 = "EE10620EEC5121DF16CC97208967F550B762551953F83F4B82FC72BF3CF8DB83"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


if _sha256(BASE_PATH) != BASE_SHA256:
    raise RuntimeError("frozen HYP002 analyzer dependency hash mismatch")

_SPEC = importlib.util.spec_from_file_location("qpf_002_frozen_base", BASE_PATH)
_BASE = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_BASE)
_BASE.HYPOTHESIS_ID = HYPOTHESIS_ID

SCHEMA_VERSION = _BASE.SCHEMA_VERSION
EXPECTED_YEARS = _BASE.EXPECTED_YEARS
FORBIDDEN_COLUMNS = _BASE.FORBIDDEN_COLUMNS
REQUIRED_COLUMNS = _BASE.REQUIRED_COLUMNS
sha256 = _BASE.sha256
analyze = _BASE.analyze


def main() -> int:
    return _BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
