from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "quote_gc_order_flow_innovation_001.py"
)
SPEC = importlib.util.spec_from_file_location("gc_ofi_quote_001", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUT
SPEC.loader.exec_module(SUT)


class FakeMetadata:
    def __init__(self, costs: dict[str, float], sizes: dict[str, int]) -> None:
        self.costs = costs
        self.sizes = sizes
        self.cost_calls: list[dict[str, object]] = []
        self.size_calls: list[dict[str, object]] = []

    def get_cost(self, **kwargs: object) -> float:
        self.cost_calls.append(kwargs)
        return self.costs[str(kwargs["schema"])]

    def get_billable_size(self, **kwargs: object) -> int:
        self.size_calls.append(kwargs)
        return self.sizes[str(kwargs["schema"])]


class FakeClient:
    def __init__(self, costs: dict[str, float], sizes: dict[str, int]) -> None:
        self.metadata = FakeMetadata(costs, sizes)


def good_client() -> FakeClient:
    return FakeClient(
        {"tbbo": 8.9, "definition": 0.01, "status": 0.02},
        {"tbbo": 800_000_000, "definition": 100_000, "status": 200_000},
    )


def test_request_contract_is_exact_and_has_no_target_outcome() -> None:
    assert SUT.SCHEMAS == ("tbbo", "definition", "status")
    for schema in SUT.SCHEMAS:
        args = SUT.request_args(schema)
        assert args == {
            "dataset": "GLBX.MDP3",
            "schema": schema,
            "symbols": ["GC.v.0"],
            "stype_in": "continuous",
            "start": "2019-01-01T00:00:00.000Z",
            "end": "2019-04-01T00:00:00.000Z",
        }
        assert "XAUUSD" not in json.dumps(args)


def test_free_quote_calls_each_schema_once_and_never_calls_timeseries() -> None:
    client = good_client()
    quoted = SUT.quote_client(client)
    total_cost, total_bytes = SUT.validate_quote(quoted)
    assert total_cost == pytest.approx(8.93)
    assert total_bytes == 800_300_000
    assert [item["schema"] for item in quoted] == list(SUT.SCHEMAS)
    assert len(client.metadata.cost_calls) == 3
    assert len(client.metadata.size_calls) == 3
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "client.timeseries" not in source
    assert "client.batch" not in source


def test_quote_fails_closed_at_or_above_ten_usd() -> None:
    client = FakeClient(
        {"tbbo": 9.97, "definition": 0.01, "status": 0.02},
        {"tbbo": 1, "definition": 1, "status": 1},
    )
    with pytest.raises(SUT.QuoteError, match="strictly below USD 10"):
        SUT.validate_quote(SUT.quote_client(client))


def test_quote_fails_on_zero_schema_payload() -> None:
    client = FakeClient(
        {"tbbo": 8.0, "definition": 0.01, "status": 0.01},
        {"tbbo": 10, "definition": 0, "status": 10},
    )
    with pytest.raises(SUT.QuoteError, match="definition"):
        SUT.quote_client(client)


def test_atomic_json_is_canonical(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    SUT.write_json_atomic(output, {"z": 1, "a": False})
    assert output.read_bytes() == b'{"a":false,"z":1}\n'
    assert not output.with_suffix(".json.tmp").exists()
