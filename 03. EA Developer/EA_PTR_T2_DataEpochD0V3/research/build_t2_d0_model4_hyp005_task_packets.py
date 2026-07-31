#!/usr/bin/env python3
"""Build frozen HYP005 Model-4 packets through the reviewed T2 D0 builder."""

from __future__ import annotations

import hashlib
import importlib.util
import json
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
SOURCE = PACKAGE / "EA_PTR_T2_DataEpochD0V3.mq5"
PREREG = PACKAGE / "research" / "HYP-PTR-T2-DATA-EPOCH-D0-M5-005_PREREG.md"
EPOCH = WORKSPACE / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH_V3.json"
COST = PACKAGE / "research" / "COLLECTION_ONLY_COST_SOURCE_MANIFEST_MODEL4_HYP005.json"
EA_CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
REGISTRY = WORKSPACE / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
EPOCH_SHA = "AEBB0EC6AEBEBE5D0ECA81FC42CB1765CF67835BA1FC134D12827E7B87C3A43E"
SOURCE_SHA = "07EF04835CC7624FC8632A0B6E1958A754A93205FB679751B4748D45E6EA4B29"
HYPOTHESIS_ID = "HYP-PTR-T2-DATA-EPOCH-D0-M5-005"
PREREG_SHA = "A5C00BFEF60C3B2EC5F1DAA702E406EFB3B2F6C9A7E6A4C11A2D7A074C9D63BE"
COST_SHA = "ABDB28B038D468E650F89A8C854AC5BDAB6161DD31B0354A034344F974CBACD2"
CAMPAIGN_LEDGER = WORKSPACE / "04. Memory/research/CAMPAIGN_EXPOSURE.jsonl"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def assert_frozen_source_epoch_binding() -> None:
    if sha256(EPOCH) != EPOCH_SHA:
        raise RuntimeError("HYP005 epoch manifest SHA changed")
    if sha256(SOURCE) != SOURCE_SHA:
        raise RuntimeError("HYP005 source SHA changed")
    if sha256(PREREG) != PREREG_SHA:
        raise RuntimeError("HYP005 prereg SHA changed")
    if sha256(COST) != COST_SHA:
        raise RuntimeError("HYP005 collection cost manifest SHA changed")
    source = SOURCE.read_text(encoding="utf-8")
    if source.count(EPOCH_SHA) != 2:
        raise RuntimeError(
            "HYP005 source must bind the V3 epoch SHA exactly twice "
            "(input default and fail-closed Configure comparison)"
        )
    prereg = PREREG.read_text(encoding="utf-8")
    for token in (EPOCH_SHA, SOURCE_SHA, "generating based on real ticks"):
        if token not in prereg:
            raise RuntimeError(f"HYP005 prereg lacks frozen token {token!r}")
    cost = json.loads(COST.read_text(encoding="utf-8-sig"))
    if not (
        cost.get("authority") == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
        and cost.get("epoch_manifest_path")
        == "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_DATA_EPOCH_V3.json"
        and cost.get("epoch_manifest_sha256") == EPOCH_SHA
        and cost.get("performance_metrics_authorized") is False
        and cost.get("economics_authorized") is False
    ):
        raise RuntimeError("HYP005 collection cost manifest contract changed")


def assert_prelaunch_campaign_binding() -> str:
    records = CAMPAIGN_LEDGER.read_bytes().splitlines()
    if not records:
        raise RuntimeError("campaign exposure ledger is empty")
    row = json.loads(records[-1].decode("utf-8"))
    repair = row.get("data_repair")
    replacement = repair.get("replacement_prereg") if isinstance(repair, dict) else None
    bound = row.get("bound_data")
    budget = row.get("budget")
    split = row.get("split")
    if not (
        row.get("campaign_id") == "CAMPAIGN-PTR-E01"
        and row.get("generation") == 2
        and row.get("event") == "DATA_REPAIR"
        and row.get("phase") == "P4"
        and row.get("active_hypothesis_id") is None
        and isinstance(bound, dict)
        and bound.get("status") == "BOUND"
        and bound.get("manifest_sha256") == EPOCH_SHA
        and isinstance(replacement, dict)
        and replacement.get("hypothesis_id") == HYPOTHESIS_ID
        and replacement.get("sha256") == PREREG_SHA
        and isinstance(budget, dict)
        and budget.get("trial_spent") == 0
        and budget.get("alpha_ppm_spent") == 0
        and row.get("viewed_arms") == []
        and isinstance(split, dict)
        and split.get("state") == "SEALED"
        and split.get("opened_count") == 0
        and repair.get("economic_trials_consumed") == 0
        and repair.get("performance_metrics_authorized") is False
        and repair.get("economics_authorized") is False
    ):
        raise RuntimeError(
            "latest campaign row does not pre-bind HYP005/V3 with zero economic exposure"
        )
    return hashlib.sha256(records[-1]).hexdigest().upper()


def assert_registry_packet_authority(campaign_row_sha: str) -> None:
    records = REGISTRY.read_bytes().splitlines()
    if not records:
        raise RuntimeError("candidate registry is empty")
    row = json.loads(records[-1].decode("utf-8-sig"))
    validation = row.get("validation")
    if not isinstance(validation, dict):
        raise RuntimeError("latest HYP005 registry row lacks validation authority")
    expected = (
        row.get("hypothesis_id") == HYPOTHESIS_ID
        and row.get("state") == "screened"
        and row.get("source_path") == SOURCE.resolve().relative_to(WORKSPACE.resolve()).as_posix()
        and row.get("source_hash") == sha256(SOURCE)
        and row.get("prereg_path") == PREREG.resolve().relative_to(WORKSPACE.resolve()).as_posix()
        and row.get("prereg_sha256") == sha256(PREREG)
        and validation.get("data_epoch_contract_sha256") == sha256(EPOCH)
        and validation.get("cost_source_manifest_sha256") == sha256(COST)
        and validation.get("ea_contract_sha256") == sha256(EA_CONTRACT)
        and validation.get("packet_builder_wrapper_sha256")
        == sha256(Path(__file__).resolve())
        and validation.get("packet_builder_core_sha256") == sha256(BUILDER)
        and validation.get("campaign_prebinding_status") == "BOUND_DATA_REPAIR"
        and validation.get("campaign_data_repair_row_sha256") == campaign_row_sha
        and validation.get("task_packet_authorized_next") is True
        and validation.get("mt5_authorized") is False
        and validation.get("performance_metrics_authorized") is False
        and validation.get("economics_authorized") is False
    )
    if not expected:
        raise RuntimeError(
            "latest HYP005 registry row does not hash-bind packet authority"
        )


def main() -> int:
    assert_frozen_source_epoch_binding()
    campaign_row_sha = assert_prelaunch_campaign_binding()
    assert_registry_packet_authority(campaign_row_sha)
    spec = importlib.util.spec_from_file_location("t2_d0_packet_builder_hyp005", BUILDER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reviewed packet builder: {BUILDER}")
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    builder.PACKAGE = PACKAGE
    builder.PREFLIGHT = PACKAGE / "research" / "preflight" / "HYP-PTR-T2-DATA-EPOCH-D0-M5-005"
    builder.SOURCE = SOURCE
    builder.PREREG = PREREG
    builder.EA_CONTRACT = EA_CONTRACT
    builder.COST = COST
    builder.HYPOTHESIS_ID = HYPOTHESIS_ID
    builder.EA_NAME = "EA_PTR_T2_DataEpochD0V3"
    builder.EPOCH_SHA = EPOCH_SHA
    builder.AUTHORITY = "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    builder.MODEL = 4
    builder.SERVER_FINGERPRINT = "7AFEBB7D8511ECD0BA3A6BB20BE0A502372EC01001734019C6AFF45AE45152EE"
    builder.ACCOUNT_FINGERPRINT = "0635F9333630C605B51F8208861007B4267011E5F4D7C3C841309F04FE39BF02"
    return int(builder.main())


if __name__ == "__main__":
    raise SystemExit(main())
