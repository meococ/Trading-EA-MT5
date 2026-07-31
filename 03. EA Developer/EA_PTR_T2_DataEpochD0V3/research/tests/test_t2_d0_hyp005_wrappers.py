from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


RESEARCH = Path(__file__).resolve().parents[1]


def load(name: str, filename: str):
    path = RESEARCH / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_hyp005_builder_binds_source_epoch_prereg_and_cost_manifest() -> None:
    module = load(
        "hyp005_builder",
        "build_t2_d0_model4_hyp005_task_packets.py",
    )

    assert sha(module.SOURCE) == module.SOURCE_SHA
    assert sha(module.EPOCH) == module.EPOCH_SHA
    module.assert_frozen_source_epoch_binding()
    source = module.SOURCE.read_text(encoding="utf-8")
    assert source.count(module.EPOCH_SHA) == 2
    wrapper = (RESEARCH / "build_t2_d0_model4_hyp005_task_packets.py").read_text(
        encoding="utf-8"
    )
    assert "HYP-PTR-T2-DATA-EPOCH-D0-M5-005" in wrapper
    assert "COLLECTION_ONLY_COST_SOURCE_MANIFEST_MODEL4_HYP005.json" in wrapper


def test_hyp005_builder_rejects_source_without_double_epoch_binding(
    tmp_path: Path, monkeypatch
) -> None:
    module = load(
        "hyp005_builder_tamper",
        "build_t2_d0_model4_hyp005_task_packets.py",
    )
    epoch = tmp_path / "epoch.json"
    epoch.write_text("{}\n", encoding="utf-8")
    epoch_sha = sha(epoch)
    source = tmp_path / "source.mq5"
    source.write_text(f'input string manifest="{epoch_sha}";\n', encoding="utf-8")
    prereg = tmp_path / "prereg.md"
    prereg.write_text(
        f"{epoch_sha}\n{sha(source)}\ngenerating based on real ticks\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "EPOCH", epoch)
    monkeypatch.setattr(module, "EPOCH_SHA", epoch_sha)
    monkeypatch.setattr(module, "SOURCE", source)
    monkeypatch.setattr(module, "SOURCE_SHA", sha(source))
    monkeypatch.setattr(module, "PREREG", prereg)
    monkeypatch.setattr(module, "PREREG_SHA", sha(prereg))

    with pytest.raises(RuntimeError, match="exactly twice"):
        module.assert_frozen_source_epoch_binding()


def test_hyp005_builder_rejects_token_preserving_prereg_tamper(
    tmp_path: Path, monkeypatch
) -> None:
    module = load(
        "hyp005_builder_prereg_tamper",
        "build_t2_d0_model4_hyp005_task_packets.py",
    )
    prereg = tmp_path / "prereg.md"
    prereg.write_text(
        module.PREREG.read_text(encoding="utf-8") + "\nTOKEN_PRESERVING_TAMPER\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "PREREG", prereg)

    with pytest.raises(RuntimeError, match="prereg SHA changed"):
        module.assert_frozen_source_epoch_binding()


def test_hyp005_builder_requires_latest_zero_exposure_campaign_binding(
    tmp_path: Path, monkeypatch
) -> None:
    module = load(
        "hyp005_builder_campaign",
        "build_t2_d0_model4_hyp005_task_packets.py",
    )
    ledger = tmp_path / "campaign.jsonl"
    row = {
        "campaign_id": "CAMPAIGN-PTR-E01",
        "generation": 2,
        "event": "DATA_REPAIR",
        "phase": "P4",
        "active_hypothesis_id": None,
        "budget": {"trial_spent": 0, "alpha_ppm_spent": 0},
        "viewed_arms": [],
        "split": {"state": "SEALED", "opened_count": 0},
        "bound_data": {
            "status": "BOUND",
            "manifest_sha256": module.EPOCH_SHA,
        },
        "data_repair": {
            "replacement_prereg": {
                "hypothesis_id": module.HYPOTHESIS_ID,
                "sha256": module.PREREG_SHA,
            },
            "economic_trials_consumed": 0,
            "performance_metrics_authorized": False,
            "economics_authorized": False,
        },
    }
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
    monkeypatch.setattr(module, "CAMPAIGN_LEDGER", ledger)

    assert module.assert_prelaunch_campaign_binding() == hashlib.sha256(
        ledger.read_bytes().splitlines()[-1]
    ).hexdigest().upper()

    row["event"] = "GOVERNANCE_CORRECTION"
    ledger.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not pre-bind"):
        module.assert_prelaunch_campaign_binding()


def test_hyp005_builder_requires_registry_hash_bound_packet_authority(
    tmp_path: Path, monkeypatch
) -> None:
    module = load(
        "hyp005_builder_registry",
        "build_t2_d0_model4_hyp005_task_packets.py",
    )
    campaign_sha = "A" * 64
    row = {
        "hypothesis_id": module.HYPOTHESIS_ID,
        "state": "screened",
        "source_path": module.SOURCE.resolve().relative_to(module.WORKSPACE.resolve()).as_posix(),
        "source_hash": sha(module.SOURCE),
        "prereg_path": module.PREREG.resolve().relative_to(module.WORKSPACE.resolve()).as_posix(),
        "prereg_sha256": sha(module.PREREG),
        "validation": {
            "data_epoch_contract_sha256": sha(module.EPOCH),
            "cost_source_manifest_sha256": sha(module.COST),
            "ea_contract_sha256": sha(module.EA_CONTRACT),
            "packet_builder_wrapper_sha256": sha(
                RESEARCH / "build_t2_d0_model4_hyp005_task_packets.py"
            ),
            "packet_builder_core_sha256": sha(module.BUILDER),
            "campaign_prebinding_status": "BOUND_DATA_REPAIR",
            "campaign_data_repair_row_sha256": campaign_sha,
            "task_packet_authorized_next": True,
            "mt5_authorized": False,
            "performance_metrics_authorized": False,
            "economics_authorized": False,
        },
    }
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    monkeypatch.setattr(module, "REGISTRY", registry)

    module.assert_registry_packet_authority(campaign_sha)
    row["prereg_sha256"] = "B" * 64
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="does not hash-bind packet authority"):
        module.assert_registry_packet_authority(campaign_sha)


def test_hyp005_appender_and_rebind_wrappers_are_data_only() -> None:
    appender = load(
        "hyp005_appender",
        "append_t2_data_epoch_model4_hyp005_evidence.py",
    )
    rebind = load(
        "hyp005_rebind",
        "rebind_t2_d0_model4_hyp005_packet_identity.py",
    )

    assert appender.CORE.HYPOTHESIS_ID == "HYP-PTR-T2-DATA-EPOCH-D0-M5-005"
    assert appender.CORE.MODEL == 4
    assert appender.CORE.AUTHORITY == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
    assert appender.CORE.EPOCH_CONTRACT_PATH.endswith("_V3.json")
    assert appender.CORE.EVIDENCE_LEDGER_PATH.endswith("_V3.jsonl")
    assert rebind.CORE.HYPOTHESIS_ID == "HYP-PTR-T2-DATA-EPOCH-D0-M5-005"
    assert rebind.CORE.MODEL == 4
    assert rebind.CORE.AUTHORITY == "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
