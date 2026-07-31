#!/usr/bin/env python3
"""Build frozen HYP004 Model-4 packets through the reviewed T2 D0 builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
WORKSPACE = PACKAGE.parents[1]
BUILDER = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_PTR_T2_DataEpochD0V2"
    / "research"
    / "build_t2_d0_task_packets.py"
)


def main() -> int:
    spec = importlib.util.spec_from_file_location("t2_d0_packet_builder_model4", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reviewed packet builder: {BUILDER}")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    builder.PACKAGE = PACKAGE
    builder.PREFLIGHT = PACKAGE / "research" / "preflight" / "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
    builder.SOURCE = PACKAGE / "EA_PTR_T2_DataEpochD0V3.mq5"
    builder.PREREG = PACKAGE / "research" / "HYP-PTR-T2-DATA-EPOCH-D0-M5-004_PREREG.md"
    builder.EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
    builder.COST = PACKAGE / "research" / "COLLECTION_ONLY_COST_SOURCE_MANIFEST_MODEL4.json"
    builder.HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-004"
    builder.EA_NAME = "EA_PTR_T2_DataEpochD0V3"
    builder.EPOCH_SHA = "88F6281385DED567E05B23BB6347F2A91B768C8B5653DAC394751D06003901C8"
    builder.AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    builder.MODEL = 4
    builder.SERVER_FINGERPRINT = "7AFEBB7D8511ECD0BA3A6BB20BE0A502372EC01001734019C6AFF45AE45152EE"
    builder.ACCOUNT_FINGERPRINT = "0635F9333630C605B51F8208861007B4267011E5F4D7C3C841309F04FE39BF02"
    return int(builder.main())


if __name__ == "__main__":
    raise SystemExit(main())
