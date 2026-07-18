from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "02. AlphaFactory" / "tools" / "databento_fx_options_acquire.py"


def load_module():
    spec = importlib.util.spec_from_file_location("databento_fx_options_acquire", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeMetadata:
    def list_datasets(self, **_kwargs):
        return ["GLBX.MDP3"]

    def list_schemas(self, **_kwargs):
        return ["definition", "statistics", "trades"]

    def get_dataset_range(self, **_kwargs):
        return {"start": "2010-06-06", "end": "2026-07-16"}

    def get_cost(self, *, schema, **_kwargs):
        return {"definition": 1.25, "statistics": 2.75}[schema]

    def get_billable_size(self, *, schema, **_kwargs):
        return {"definition": 1_000, "statistics": 2_000}[schema]


class FakeSymbology:
    def resolve(self, **_kwargs):
        return {
            "result": {"EUU.OPT": [{"d0": "2020-01-02", "s": "EUUH0 C1100"}]},
            "partial": [],
            "not_found": ["XT.OPT"],
        }


class FakeBatch:
    def __init__(self):
        self.calls = []

    def submit_job(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": f"job-{kwargs['schema']}"}


class FakeClient:
    def __init__(self):
        self.metadata = FakeMetadata()
        self.symbology = FakeSymbology()
        self.batch = FakeBatch()


def test_plan_uses_free_discovery_and_contains_no_api_key() -> None:
    module = load_module()
    plan = module.build_plan(FakeClient())

    assert plan["status"] == "ESTIMATED_NOT_SUBMITTED"
    assert plan["symbology"]["resolved_option_parents"] == ["EUU.OPT"]
    assert plan["estimated_total_usd"] == 4.0
    assert plan["estimated_total_billable_size"] == 3_000
    assert plan["api_key_stored"] is False
    assert "db-" not in json.dumps(plan)


def test_plan_hash_detects_mutation() -> None:
    module = load_module()
    plan = module.build_plan(FakeClient())
    plan["estimated_total_usd"] = 0.01

    with pytest.raises(module.AcquisitionError, match="hash mismatch"):
        module.submit_plan(FakeClient(), plan, approved_max_usd=10.0)


def test_submit_blocks_before_job_when_live_cost_exceeds_owner_ceiling() -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_plan(client)

    with pytest.raises(module.AcquisitionError, match="exceeds approved ceiling"):
        module.submit_plan(client, plan, approved_max_usd=3.99)

    assert client.batch.calls == []


def test_submit_uses_batch_csv_month_splits_after_explicit_ceiling() -> None:
    module = load_module()
    client = FakeClient()
    plan = module.build_plan(client)

    result = module.submit_plan(client, plan, approved_max_usd=4.50)

    assert result["status"] == "SUBMITTED_NOT_DOWNLOADED"
    assert [item["job_id"] for item in result["jobs"]] == [
        "job-definition",
        "job-statistics",
    ]
    assert len(client.batch.calls) == 2
    assert all(call["encoding"] == "csv" for call in client.batch.calls)
    assert all(call["compression"] == "zstd" for call in client.batch.calls)
    assert all(call["split_duration"] == "month" for call in client.batch.calls)
    assert all(call["stype_in"] == "parent" for call in client.batch.calls)


def test_key_is_never_read_from_a_tracked_file(monkeypatch) -> None:
    module = load_module()
    monkeypatch.delenv("DATABENTO_API_KEY", raising=False)
    monkeypatch.setattr(module, "read_user_environment", lambda _name: None)

    with pytest.raises(module.AcquisitionError, match="never paste"):
        module.load_api_key()
