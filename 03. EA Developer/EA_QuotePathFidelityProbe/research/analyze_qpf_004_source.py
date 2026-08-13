#!/usr/bin/env python3
"""Outcome-blind frozen gate analyzer for HYP-QPF-EURUSD-M1-004."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


HYPOTHESIS_ID = "HYP-QPF-EURUSD-M1-004"
BASE_PATH = Path(__file__).with_name("analyze_qpf_002_source.py")
BASE_SHA256 = "EE10620EEC5121DF16CC97208967F550B762551953F83F4B82FC72BF3CF8DB83"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


if _sha256(BASE_PATH) != BASE_SHA256:
    raise RuntimeError("frozen source-gate analyzer hash mismatch")

_SPEC = importlib.util.spec_from_file_location("qpf_002_frozen_for_004", BASE_PATH)
_BASE = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_BASE)
_BASE.HYPOTHESIS_ID = HYPOTHESIS_ID

SCHEMA_VERSION = _BASE.SCHEMA_VERSION
EXPECTED_YEARS = _BASE.EXPECTED_YEARS
sha256 = _BASE.sha256
analyze = _BASE.analyze


def main() -> int:
    return _BASE.main()


if __name__ == "__main__":
    raise SystemExit(main())
