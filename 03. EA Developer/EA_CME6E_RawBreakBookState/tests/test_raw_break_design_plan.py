from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "plan_cme6e_raw_break_design.py"


def load_module():
    spec = importlib.util.spec_from_file_location("plan_cme6e_raw_break_design", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_design_population_is_identity_only_and_oos_sealed() -> None:
    module = load_module()
    requests = module.read_design_requests()

    assert len(requests) == 547
    assert set().union(*(item.keys() for item in requests)) == {
        "position_id",
        "direction",
        "start",
        "end",
        "filename",
    }
    assert {item["end"][:4] for item in requests} == {"2019", "2020"}
    assert len({(item["position_id"], item["end"]) for item in requests}) == 547


def test_plan_is_hash_bound_outcome_blind_and_requires_new_approval() -> None:
    module = load_module()
    requests = module.read_design_requests()
    quotes = [
        {"position_id": item["position_id"], "estimated_cost_usd": 0.001, "billable_bytes": 1000}
        for item in requests
    ]
    plan = module.build_plan(
        requests,
        quotes,
        quote_provenance={
            "mode": "unit_test",
            "network_calls": 0,
            "paid_request_made": False,
        },
    )

    assert plan["estimated_cost_usd"] == pytest.approx(0.547)
    assert plan["recommended_owner_ceiling_usd"] == 1.10
    assert plan["input"]["outcome_fields_used"] is False
    assert plan["tool"]["sha256"] == module.sha256_file(module.MODULE_PATH)
    assert plan["quote_provenance"]["network_calls"] == 0
    assert plan["sealed_oos_quoted"] is False
    assert plan["download_authorized"] is False
    assert plan["paid_request_made"] is False

    plan["requests"][0]["end"] = "2099-01-01T00:00:00Z"
    with pytest.raises(module.PlanError, match="hash mismatch"):
        module.validate_plan(plan)


def test_saved_quotes_can_be_reused_only_from_the_hash_bound_receipt() -> None:
    module = load_module()
    quotes, provenance = module.load_reusable_quotes(
        module.REUSABLE_QUOTE_PATH,
        module.REUSABLE_QUOTE_SHA256,
    )

    assert len(quotes) == 547
    assert provenance["mode"] == "hash_bound_metadata_quote_reuse"
    assert provenance["network_calls"] == 0
    assert provenance["paid_request_made"] is False

    with pytest.raises(module.PlanError, match="SHA mismatch"):
        module.load_reusable_quotes(module.REUSABLE_QUOTE_PATH, "0" * 64)


class FakeMetadata:
    def __init__(self) -> None:
        self.cost_calls: list[dict] = []
        self.size_calls: list[dict] = []

    def get_cost(self, **kwargs):
        self.cost_calls.append(kwargs)
        return 0.001

    def get_billable_size(self, **kwargs):
        self.size_calls.append(kwargs)
        return 1000


class FakeClient:
    def __init__(self) -> None:
        self.metadata = FakeMetadata()


def test_quote_surface_has_no_timeseries_or_paid_call() -> None:
    module = load_module()
    requests = module.read_design_requests()[:2]
    clients: list[FakeClient] = []

    def factory() -> FakeClient:
        client = FakeClient()
        clients.append(client)
        return client

    quotes = module.quote_requests(requests, client_factory=factory, workers=1)
    assert len(quotes) == 2
    assert sum(len(client.metadata.cost_calls) for client in clients) == 2
    assert all(call["mode"] == "historical-streaming" for client in clients for call in client.metadata.cost_calls)
    assert all(not hasattr(client, "timeseries") for client in clients)
