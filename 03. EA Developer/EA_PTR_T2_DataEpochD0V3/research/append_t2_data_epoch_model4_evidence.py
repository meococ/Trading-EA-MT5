#!/usr/bin/env python3
"""Append one HYP004 Model-4 T2 data-epoch evidence row through the reviewed V3 appender."""

from __future__ import annotations

import importlib.util
from pathlib import Path


CORE_PATH = Path(__file__).with_name("append_t2_data_epoch_evidence.py")
SPEC = importlib.util.spec_from_file_location("append_t2_data_epoch_evidence_core", CORE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load reviewed data-epoch appender: {CORE_PATH}")
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)

CORE.HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
CORE.EA_NAME = "EA_PTR_T2_DataEpochD0V3"
CORE.EPOCH_CONTRACT_PATH = "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH_V2.json"
CORE.EVIDENCE_LEDGER_PATH = "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EVIDENCE_V2.jsonl"
CORE.EPOCH_SHA256 = "88F6281385DED567E05B23BB6347F2A91B768C8B5653DAC394751D06003901C8"
CORE.AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
CORE.MODEL = 4


if __name__ == "__main__":
    raise SystemExit(CORE.main())
