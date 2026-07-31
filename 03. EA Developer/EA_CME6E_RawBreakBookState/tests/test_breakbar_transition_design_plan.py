from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


PACKAGE = Path(__file__).resolve().parents[1]
MODULE_PATH = PACKAGE / "research" / "plan_cme6e_breakbar_transition_design.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "plan_cme6e_breakbar_transition_design", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_new_design_uses_actual_entry_clock_and_no_outcome_fields() -> None:
    module = load_module()
    requests = module.read_design_requests()

    assert len(requests) == 565
    assert set().union(*(item.keys() for item in requests)) == {
        "position_id",
        "direction",
        "break_bar_open",
        "actual_decision",
        "start",
        "end",
        "duration_seconds",
        "filename",
    }
    assert {item["actual_decision"][:4] for item in requests} == {"2021", "2022"}
    assert len({(item["position_id"], item["actual_decision"]) for item in requests}) == 565
    assert {int(item["duration_seconds"]) for item in requests} == {300, 330}
    assert sum(int(item["duration_seconds"]) == 300 for item in requests) == 564
    assert all(item["start"] == item["break_bar_open"] for item in requests)
    assert all(item["end"] == item["actual_decision"] for item in requests)


def test_plan_is_metadata_only_hash_bound_and_owner_approval_gated() -> None:
    module = load_module()
    requests = module.read_design_requests()
    quotes = [
        {
            "position_id": item["position_id"],
            "estimated_cost_usd": 0.001,
            "billable_bytes": 1000,
        }
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

    assert plan["estimated_cost_usd"] == pytest.approx(0.565)
    assert plan["recommended_owner_ceiling_usd"] == 1.13
    assert plan["input"]["fields_used"] == [
        "position_id",
        "decision_time",
        "open_time",
        "direction",
    ]
    assert plan["input"]["outcome_fields_used"] is False
    assert plan["clock_semantics"]["feature_window_start_role"] == "BREAK_BAR_OPEN"
    assert plan["clock_semantics"]["feature_window_end_role"] == "ACTUAL_NEXT_BAR_DECISION_ENTRY"
    assert plan["prior_hypothesis"]["hypothesis_id"] == "HYP-CME6E-RAWBREAK-BOOKSTATE-001"
    assert plan["prior_hypothesis"]["oos_opened_under_prior_id"] is False
    assert plan["tool"]["sha256"] == module.sha256_file(module.MODULE_PATH)
    assert plan["download_authorized"] is False
    assert plan["paid_request_made"] is False

    plan["live_quotes"][0]["estimated_cost_usd"] = 9.0
    with pytest.raises(module.PlanError, match="hash mismatch"):
        module.validate_plan(plan)


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


def test_quote_surface_cannot_make_a_paid_timeseries_call() -> None:
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
    assert all(
        call["mode"] == "historical-streaming"
        for client in clients
        for call in client.metadata.cost_calls
    )
    assert all(not hasattr(client, "timeseries") for client in clients)
