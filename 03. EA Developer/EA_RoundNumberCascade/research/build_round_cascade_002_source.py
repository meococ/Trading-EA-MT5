#!/usr/bin/env python3
"""HYP002 engineering-repair entrypoint over the reviewed HYP001 scanner core.

The inherited core is exact-SHA bound and import-inert.  This wrapper changes
only hypothesis/authority artifact identity and the preregistered binary-float
quote-grid decoder.  Signal rules, source gates, custody and lifecycle remain
the reviewed HYP001 implementation.
"""

from __future__ import annotations

import hashlib
import os
import stat
from decimal import Decimal
from pathlib import Path
from typing import Any


BASE_IMPLEMENTATION_PATH = Path(__file__).with_name("build_round_cascade_001_source.py")
BASE_IMPLEMENTATION_SHA256 = "EC695AB543BE3B34EA73ED8FF23FDD58C90BA15B768042362FDF32CAA36A62ED"
_base_info = BASE_IMPLEMENTATION_PATH.lstat()
if (
    BASE_IMPLEMENTATION_PATH.is_symlink()
    or not stat.S_ISREG(_base_info.st_mode)
    or _base_info.st_nlink != 1
):
    raise RuntimeError("reviewed HYP001 scanner core must be a single-link regular file")
_base_payload = BASE_IMPLEMENTATION_PATH.read_bytes()
if hashlib.sha256(_base_payload).hexdigest().upper() != BASE_IMPLEMENTATION_SHA256:
    raise RuntimeError("reviewed HYP001 scanner core SHA256 mismatch")

import build_round_cascade_001_source as _base


HYPOTHESIS_ID = "HYP-ROUND-CASCADE-EURUSD-M5-002"
PLAN_REL = "03. EA Developer/EA_RoundNumberCascade/research/HYP-ROUND-CASCADE-EURUSD-M5-002_PROBE_PLAN.md"
FROZEN_PLAN_SHA256 = "CFA9EE2B7D58923F8091152BD7AC01F11674BE8AFC276A599979CD9B425DD52E"
BUILDER_REL = "03. EA Developer/EA_RoundNumberCascade/research/build_round_cascade_002_source.py"
TEST_REL = "03. EA Developer/EA_RoundNumberCascade/research/tests/test_build_round_cascade_002_source.py"
INDEPENDENT_REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/"
    "HYP-ROUND-CASCADE-EURUSD-M5-002_INDEPENDENT_SOURCE_REVIEW_RECEIPT.json"
)
INDEPENDENT_REVIEW_SCHEMA = "round_cascade_002_independent_source_review.v1"
ATTEMPT_ID = "HYP002-SOURCE-PREFLIGHT-001"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_RoundNumberCascade/research/evidence/"
    "HYP-ROUND-CASCADE-EURUSD-M5-002_SOURCE_FEASIBILITY/"
    f"{ATTEMPT_ID}"
)
FLOAT_GRID_TOLERANCE_POINTS = Decimal("0.000001")

# Independent review replaces this exact sentinel only after registry authority.
REVIEWED_REGISTRY_ROW_SHA256: str | None = "D93A3317B2669EC60014ECE3CC85FDD10F997581FCAB18F0EE2F491063A3C5F4"


def price_to_points(price: Any) -> int:
    """Normalize binary-float noise without widening the five-digit grid."""

    try:
        value = Decimal(str(price))
    except Exception as exc:
        raise _base.ContractError(f"invalid price: {price!r}") from exc
    if not value.is_finite() or value <= 0:
        raise _base.ContractError(f"invalid price: {price!r}")
    points = value / _base.QUOTE_POINT
    nearest = points.to_integral_value()
    if abs(points - nearest) > FLOAT_GRID_TOLERANCE_POINTS:
        raise _base.ContractError(f"price is outside quote-point grid: {price!r}")
    return int(nearest)


_base.HYPOTHESIS_ID = HYPOTHESIS_ID
_base.PLAN_REL = PLAN_REL
_base.FROZEN_PLAN_SHA256 = FROZEN_PLAN_SHA256
_base.BUILDER_REL = BUILDER_REL
_base.TEST_REL = TEST_REL
_base.INDEPENDENT_REVIEW_RECEIPT_REL = INDEPENDENT_REVIEW_RECEIPT_REL
_base.INDEPENDENT_REVIEW_SCHEMA = INDEPENDENT_REVIEW_SCHEMA
_base.ATTEMPT_ID = ATTEMPT_ID
_base.EVIDENCE_ROOT_REL = EVIDENCE_ROOT_REL
_base.REVIEWED_REGISTRY_ROW_SHA256 = REVIEWED_REGISTRY_ROW_SHA256
_base.price_to_points = price_to_points
_base.__file__ = __file__

# Re-export the reviewed surface so the focused HYP002 tests remain identical.
for _name in dir(_base):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_base, _name)

# Preserve the wrapper's own reviewed authority constants after the re-export.
globals().update(
    {
        "BASE_IMPLEMENTATION_PATH": BASE_IMPLEMENTATION_PATH,
        "BASE_IMPLEMENTATION_SHA256": BASE_IMPLEMENTATION_SHA256,
        "HYPOTHESIS_ID": HYPOTHESIS_ID,
        "PLAN_REL": PLAN_REL,
        "FROZEN_PLAN_SHA256": FROZEN_PLAN_SHA256,
        "BUILDER_REL": BUILDER_REL,
        "TEST_REL": TEST_REL,
        "INDEPENDENT_REVIEW_RECEIPT_REL": INDEPENDENT_REVIEW_RECEIPT_REL,
        "INDEPENDENT_REVIEW_SCHEMA": INDEPENDENT_REVIEW_SCHEMA,
        "ATTEMPT_ID": ATTEMPT_ID,
        "EVIDENCE_ROOT_REL": EVIDENCE_ROOT_REL,
        "FLOAT_GRID_TOLERANCE_POINTS": FLOAT_GRID_TOLERANCE_POINTS,
        "REVIEWED_REGISTRY_ROW_SHA256": REVIEWED_REGISTRY_ROW_SHA256,
        "price_to_points": price_to_points,
    }
)


if __name__ == "__main__":
    raise SystemExit(_base.main())
