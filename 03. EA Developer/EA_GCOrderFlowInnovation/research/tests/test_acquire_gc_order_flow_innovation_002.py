from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "acquire_gc_order_flow_innovation_002.py"
SPEC = importlib.util.spec_from_file_location("gc_ofi_acquire_002", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SUT
SPEC.loader.exec_module(SUT)


class FakeMetadata:
    def __init__(self) -> None:
        self.cost_calls: list[dict[str, object]] = []
        self.size_calls: list[dict[str, object]] = []

    def get_cost(self, **kwargs: object) -> float:
        self.cost_calls.append(kwargs)
        return {"definition": 0.00018, "status": 0.00022}[str(kwargs["schema"])]

    def get_billable_size(self, **kwargs: object) -> int:
        self.size_calls.append(kwargs)
        return {"definition": 113_360, "status": 59_200}[str(kwargs["schema"])]


class FakeTimeseries:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def get_range(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
        Path(str(kwargs["path"])).write_bytes(SUT._ZSTD_MAGIC + b"fixture")


class FakeClient:
    def __init__(self) -> None:
        self.metadata = FakeMetadata()
        self.timeseries = FakeTimeseries()


def test_request_contract_is_raw_id_reference_only() -> None:
    assert SUT.SCHEMAS == ("definition", "status")
    assert SUT.SYMBOLS == ("32257", "14651", "142620")
    for schema in SUT.SCHEMAS:
        assert SUT.request_args(schema) == {
            "dataset": "GLBX.MDP3", "schema": schema,
            "symbols": ["32257", "14651", "142620"],
            "stype_in": "instrument_id", "start": "2019-01-01T00:00:00.000Z",
            "end": "2019-04-01T00:00:00.000Z",
        }


def test_live_requote_is_two_free_schema_quotes() -> None:
    client = FakeClient()
    quotes, cost, size = SUT.live_requote(client)
    assert [item["schema"] for item in quotes] == ["definition", "status"]
    assert cost == pytest.approx(0.0004)
    assert size == 172_560
    assert len(client.metadata.cost_calls) == 2
    assert len(client.metadata.size_calls) == 2
    assert client.timeseries.calls == []


def test_download_one_is_serial_and_never_requests_tbbo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient()
    manifest = {"status": "READY", "downloads": [], "in_flight": None, "paid_timeseries_calls": 0, "paid_timeseries_attempts": 0}
    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(SUT, "validate_dbn_file", lambda path, schema: (3, {32257}))
    quote = {"schema": "definition", "estimated_usd": 0.00018, "billable_bytes": 113_360}
    result = SUT.download_one(client=client, schema="definition", quote=quote, root=tmp_path, manifest=manifest, manifest_path=manifest_path)
    assert result["schema"] == "definition"
    assert manifest["paid_timeseries_attempts"] == 1
    assert manifest["paid_timeseries_calls"] == 1
    assert len(client.timeseries.calls) == 1
    call = client.timeseries.calls[0]
    assert call["schema"] == "definition"
    assert call["stype_out"] == "instrument_id"
    assert "tbbo" not in json.dumps(call, default=str)


def test_remote_failure_preserves_inflight_and_forbids_success_count(tmp_path: Path) -> None:
    class BoomTimeseries:
        def get_range(self, **kwargs: object) -> None:
            raise RuntimeError("network")

    client = FakeClient()
    client.timeseries = BoomTimeseries()  # type: ignore[assignment]
    manifest = {"status": "READY", "downloads": [], "in_flight": None, "paid_timeseries_calls": 0, "paid_timeseries_attempts": 0}
    manifest_path = tmp_path / "manifest.json"
    quote = {"schema": "status", "estimated_usd": 0.00022, "billable_bytes": 59_200}
    with pytest.raises(SUT.AcquisitionError, match="paid request failed for status"):
        SUT.download_one(client=client, schema="status", quote=quote, root=tmp_path, manifest=manifest, manifest_path=manifest_path)
    frozen = json.loads(manifest_path.read_text(encoding="ascii"))
    assert frozen["in_flight"]["schema"] == "status"
    assert frozen["paid_timeseries_attempts"] == 1
    assert frozen["paid_timeseries_calls"] == 0


def test_source_contains_no_batch_or_subscription_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "client.batch" not in source
    assert "submit_job" not in source
    assert "client.live" not in source
    assert "Live(" not in source
