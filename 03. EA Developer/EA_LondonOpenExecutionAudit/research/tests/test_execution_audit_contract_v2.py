from __future__ import annotations

import copy
import dataclasses
import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[2]
WORKSPACE = PACKAGE.parents[1]
RESEARCH = PACKAGE / "research"
VALIDATOR = RESEARCH / "validate_execution_audit_v2.py"
RUN_ROOT = WORKSPACE / "02. AlphaFactory" / "runs" / "EA_LondonOpenExecutionAudit"
RUNS = {
    "EURUSD_MIDDAY_CONT": RUN_ROOT / "20260730_190022",
    "GBPUSD_MIDDAY_REV": RUN_ROOT / "20260730_190128",
    "GBPUSD_LATE_FIX_REV": RUN_ROOT / "20260730_190227",
    "GBPUSD_FULL_SESSION_REV": RUN_ROOT / "20260730_190328",
}


def load_validator():
    if str(RESEARCH) not in sys.path:
        sys.path.insert(0, str(RESEARCH))
    spec = importlib.util.spec_from_file_location("audit_validator_v2", VALIDATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def validator():
    return load_validator()


@pytest.mark.parametrize("scenario", list(RUNS))
def test_actual_authorized_model0_run_passes_v2(validator, scenario: str) -> None:
    result = validator.validate_scenario_v2(scenario, RUNS[scenario])
    assert result.passed, result.errors


@pytest.mark.parametrize(
    ("key", "bad_value", "needle"),
    [
        ("run_id", "SUBSTITUTED_RUN", "manifest.run_id mismatch"),
        ("model", 1, "manifest.model mismatch"),
        ("from", "2017.01.01", "manifest.from mismatch"),
        ("to", "2021.12.31", "manifest.to mismatch"),
        ("source_sha256", "0" * 64, "manifest.source_sha256 mismatch"),
        ("contract_receipt_sha256", "0" * 64, "manifest receipt hash mismatch"),
    ],
)
def test_provenance_rejects_wrong_model_window_source_receipt_or_run(
    validator, monkeypatch, key: str, bad_value, needle: str
) -> None:
    original = validator.load_json

    def mutated(path, errors, label):
        payload = original(path, errors, label)
        if label == "run manifest":
            payload = copy.deepcopy(payload)
            payload[key] = bad_value
        return payload

    monkeypatch.setattr(validator, "load_json", mutated)
    errors, _ = validator.validate_provenance(
        "EURUSD_MIDDAY_CONT", RUNS["EURUSD_MIDDAY_CONT"]
    )
    assert any(needle in error for error in errors), errors


def test_receipt_binding_cannot_omit_a_frozen_field(validator, monkeypatch) -> None:
    original = validator.load_json

    def mutated(path, errors, label):
        payload = original(path, errors, label)
        if label == "execution receipt":
            payload = copy.deepcopy(payload)
            payload["binding"].pop("model")
        return payload

    monkeypatch.setattr(validator, "load_json", mutated)
    errors, _ = validator.validate_provenance(
        "EURUSD_MIDDAY_CONT", RUNS["EURUSD_MIDDAY_CONT"]
    )
    assert any("receipt.binding.model mismatch" in error for error in errors), errors


def test_identity_rejects_substituted_deal_id_with_same_count(validator, monkeypatch) -> None:
    original = validator.v1.parse_mt5_deals

    def corrupted(path):
        deals = original(path)
        index = next(i for i, deal in enumerate(deals) if deal.symbol == "EURUSD")
        deals[index] = dataclasses.replace(deals[index], deal_id=deals[index].deal_id + 999_999)
        return deals

    monkeypatch.setattr(validator.v1, "parse_mt5_deals", corrupted)
    errors, _ = validator.validate_identity(
        "EURUSD_MIDDAY_CONT", RUNS["EURUSD_MIDDAY_CONT"]
    )
    assert any("report deal ID set differs" in error for error in errors), errors


def test_identity_rejects_changed_price_with_same_ids_and_counts(validator, monkeypatch) -> None:
    original = validator.v1.parse_mt5_deals

    def corrupted(path):
        deals = original(path)
        index = next(i for i, deal in enumerate(deals) if deal.symbol == "EURUSD")
        deals[index] = dataclasses.replace(deals[index], price=deals[index].price + 0.0001)
        return deals

    monkeypatch.setattr(validator.v1, "parse_mt5_deals", corrupted)
    errors, _ = validator.validate_identity(
        "EURUSD_MIDDAY_CONT", RUNS["EURUSD_MIDDAY_CONT"]
    )
    assert any("report/decision price mismatch" in error for error in errors), errors


def test_identity_rejects_execution_rejection_even_if_success_counts_survive(
    validator, monkeypatch
) -> None:
    original = validator.v1.read_csv

    def corrupted(path):
        rows = original(path)
        if "_DecisionTelemetry_" in path.name:
            rejected = copy.deepcopy(next(row for row in rows if row["event"] == "ENTRY_REQUEST"))
            rejected.update(event="ENTRY_REJECT", status="REJECTED", reason="synthetic audit test")
            rows.append(rejected)
        return rows

    monkeypatch.setattr(validator.v1, "read_csv", corrupted)
    errors, _ = validator.validate_identity(
        "EURUSD_MIDDAY_CONT", RUNS["EURUSD_MIDDAY_CONT"]
    )
    assert any("rejected/nonterminal" in error for error in errors), errors


@pytest.mark.parametrize("event", ["ENTRY_SUBMIT", "EXIT_SUBMIT"])
def test_identity_rejects_same_count_submit_identity_corruption(
    validator, monkeypatch, event: str
) -> None:
    original = validator.v1.read_csv

    def corrupted(path):
        rows = original(path)
        if "_DecisionTelemetry_" in path.name:
            row = next(item for item in rows if item["event"] == event)
            row["order_id"] = str(int(row["order_id"]) + 999_999)
            row["deal_id"] = str(int(row["deal_id"]) + 888_888)
            row["actual_deal_price"] = str(float(row["actual_deal_price"]) + 0.0001)
            row["volume"] = str(float(row["volume"]) * 2.0)
            row["position_id"] = str(int(row["position_id"]) + 777_777)
        return rows

    monkeypatch.setattr(validator.v1, "read_csv", corrupted)
    errors, _ = validator.validate_identity(
        "EURUSD_MIDDAY_CONT", RUNS["EURUSD_MIDDAY_CONT"]
    )
    stage = event.split("_", 1)[0]
    assert any(f"{stage} submit/deal order_id mismatch" in error for error in errors), errors
    assert any(f"{stage} submit/deal deal_id mismatch" in error for error in errors), errors
    assert any(f"{stage} submit/deal actual price mismatch" in error for error in errors), errors
    assert any(f"{stage} request/submit/deal volume mismatch" in error for error in errors), errors
    if stage == "ENTRY":
        assert any("ENTRY request/submit position sentinel mismatch" in error for error in errors)
    else:
        assert any("EXIT request/submit/deal position identity mismatch" in error for error in errors)


def test_europe_dst_boundaries_are_explicit(validator) -> None:
    assert not validator.europe_dst_utc(datetime(2020, 3, 29, 0, 59))
    assert validator.europe_dst_utc(datetime(2020, 3, 29, 1, 0))
    assert validator.europe_dst_utc(datetime(2020, 10, 25, 0, 59))
    assert not validator.europe_dst_utc(datetime(2020, 10, 25, 1, 0))
