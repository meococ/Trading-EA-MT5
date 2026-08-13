#!/usr/bin/env python3
"""Outcome-blind acquisition revision for the EVT0001 MBP-10 depth pilot."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


HYPOTHESIS_ID = "HYP-EVENT-DEPTH-TRANSFER-EURUSD-TICK-002"
ACQUISITION_ID = "EVENTDEPTHTRANSFER002-MBP10-PILOT-001"
BASE_REL = "03. EA Developer/EA_EventDepthTransfer/research/"
PLAN_REL = BASE_REL + HYPOTHESIS_ID + "_PILOT_PREREG.md"
TOOL_REL = BASE_REL + "acquire_event_depth_transfer_002_pilot.py"
TEST_REL = BASE_REL + "tests/test_acquire_event_depth_transfer_002_pilot.py"
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_event_depth_transfer/"
    f"{HYPOTHESIS_ID}/{ACQUISITION_ID}"
)
END = "2019-01-03T15:01:00.000Z"
OWNER_CEILING_USD = 0.02
ENGINE_SHA256 = "D98340522620EB783762B4E8BDB8CAE99B71BEFE4F1D8D9A03EEE98E7F85B8F3"


def _load_engine() -> Any:
    path = Path(__file__).resolve().with_name("acquire_event_depth_transfer_001_pilot.py")
    spec = importlib.util.spec_from_file_location("event_depth_transfer_engine_v1", path)
    if not spec or not spec.loader:
        raise RuntimeError("cannot load reviewed acquisition engine")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if module.sha256_file(path) != ENGINE_SHA256:
        raise module.AcquisitionError("reviewed acquisition engine drifted")
    return module


ENGINE = _load_engine()
AcquisitionError = ENGINE.AcquisitionError


def configure_engine() -> Any:
    ENGINE.HYPOTHESIS_ID = HYPOTHESIS_ID
    ENGINE.ACQUISITION_ID = ACQUISITION_ID
    ENGINE.PLAN_REL = PLAN_REL
    ENGINE.TOOL_REL = TOOL_REL
    ENGINE.TEST_REL = TEST_REL
    ENGINE.OUTPUT_REL = OUTPUT_REL
    ENGINE.END = END
    ENGINE.OWNER_CEILING_USD = OWNER_CEILING_USD
    return ENGINE


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def validate_engine_registry_binding(workspace: Path) -> None:
    registry = workspace / ENGINE.REGISTRY_REL
    matches = []
    for raw in registry.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append(row)
    if not matches or matches[-1].get("validation", {}).get(
        "reviewed_engine_sha256"
    ) != ENGINE_SHA256:
        raise AcquisitionError("registry engine binding mismatch")


def request_args() -> dict[str, Any]:
    return configure_engine().request_args()


def execute(workspace: Path) -> Path:
    engine = configure_engine()
    validate_engine_registry_binding(workspace.resolve())
    return engine.execute(workspace.resolve())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        receipt_path = execute(args.workspace.resolve())
        receipt = json.loads(receipt_path.read_text(encoding="ascii"))
        print(
            "EVENT_DEPTH_TRANSFER_002_PILOT_OK "
            f"cost={receipt['live_estimated_usd']:.12f} "
            f"verdict={receipt['semantic_verdict']} "
            f"classification={receipt['classification']}"
        )
        print(f"RECEIPT {receipt_path}")
        return 0
    except AcquisitionError as exc:
        print(f"EVENT_DEPTH_TRANSFER_002_PILOT_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

