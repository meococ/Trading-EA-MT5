from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "quote_gc_order_flow_innovation_002.py"
SPEC = importlib.util.spec_from_file_location("gc_ofi_quote_002", MODULE_PATH)
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
    return FakeClient({"definition": 0.01, "status": 0.02}, {"definition": 100_000, "status": 200_000})


def test_request_contract_uses_only_inherited_raw_ids() -> None:
    assert SUT.SCHEMAS == ("definition", "status")
    assert SUT.SYMBOLS == ("32257", "14651", "142620")
    for schema in SUT.SCHEMAS:
        args = SUT.request_args(schema)
        assert args == {
            "dataset": "GLBX.MDP3",
            "schema": schema,
            "symbols": ["32257", "14651", "142620"],
            "stype_in": "instrument_id",
            "start": "2019-01-01T00:00:00.000Z",
            "end": "2019-04-01T00:00:00.000Z",
        }
        assert "GC.v.0" not in json.dumps(args)
        assert "XAUUSD" not in json.dumps(args)


def test_free_quote_never_calls_timeseries_or_batch() -> None:
    client = good_client()
    quoted = SUT.quote_client(client)
    total_cost, total_bytes = SUT.validate_quote(quoted)
    assert total_cost == pytest.approx(0.03)
    assert total_bytes == 300_000
    assert len(client.metadata.cost_calls) == 2
    assert len(client.metadata.size_calls) == 2
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "client.timeseries" not in source
    assert "client.batch" not in source


def test_quote_fails_closed_at_or_above_ten_usd() -> None:
    client = FakeClient({"definition": 9.99, "status": 0.01}, {"definition": 1, "status": 1})
    with pytest.raises(SUT.QuoteError, match="strictly below USD 10"):
        SUT.validate_quote(SUT.quote_client(client))


def test_quote_fails_on_nonpositive_schema_payload() -> None:
    client = FakeClient({"definition": 0.01, "status": 0.01}, {"definition": 0, "status": 1})
    with pytest.raises(SUT.QuoteError, match="definition"):
        SUT.quote_client(client)


def test_atomic_json_is_canonical(tmp_path: Path) -> None:
    output = tmp_path / "receipt.json"
    SUT.write_json_atomic(output, {"z": 1, "a": False})
    assert output.read_bytes() == b'{"a":false,"z":1}\n'
