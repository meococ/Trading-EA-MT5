#!/usr/bin/env python3
"""Rebind a HYP005 Model-4 packet through the reviewed D0 identity tool."""

from __future__ import annotations

import importlib.util
from pathlib import Path


CORE_PATH = Path(__file__).with_name("rebind_t2_d0_packet_identity.py")
SPEC = importlib.util.spec_from_file_location("rebind_t2_d0_hyp005_core", CORE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load reviewed identity tool: {CORE_PATH}")
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)

CORE.AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
CORE.HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-005"
CORE.EA_NAME = "EA_PTR_T2_DataEpochD0V3"
CORE.MODEL = 4


if __name__ == "__main__":
    raise SystemExit(CORE.main())
