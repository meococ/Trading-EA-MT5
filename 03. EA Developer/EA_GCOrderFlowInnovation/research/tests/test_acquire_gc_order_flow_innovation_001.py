from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "acquire_gc_order_flow_innovation_001.py"
)
SPEC = importlib.util.spec_from_file_location("gc_ofi_acquire_001", MODULE_PATH)
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


class FakeTimeseries:
    def __init__(self, manifest_path: Path, fail: bool = False) -> None:
        self.manifest_path = manifest_path
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def get_range(self, **kwargs: object) -> None:
        manifest = json.loads(self.manifest_path.read_text(encoding="ascii"))
        assert manifest["in_flight"] is not None
        self.calls.append(kwargs)
        if self.fail:
            raise RuntimeError("network")
        Path(str(kwargs["path"])).write_bytes(SUT._ZSTD_MAGIC + b"fixture")


class FakeClient:
    def __init__(
        self,
        costs: dict[str, float],
        sizes: dict[str, int],
        manifest_path: Path | None = None,
        fail: bool = False,
    ) -> None:
        self.metadata = FakeMetadata(costs, sizes)
        self.timeseries = (
            FakeTimeseries(manifest_path, fail) if manifest_path is not None else None
        )


def test_exact_request_contract_and_schema_order() -> None:
    assert SUT.SCHEMAS == ("tbbo", "definition", "status")
    for schema in SUT.SCHEMAS:
        assert SUT.request_args(schema) == {
            "dataset": "GLBX.MDP3",
            "schema": schema,
            "symbols": ["GC.v.0"],
            "stype_in": "continuous",
            "start": "2019-01-01T00:00:00.000Z",
            "end": "2019-04-01T00:00:00.000Z",
        }


def test_fresh_requote_passes_strictly_below_ten() -> None:
    client = FakeClient(
        {"tbbo": 8.9, "definition": 0.01, "status": 0.02},
        {"tbbo": 10, "definition": 1, "status": 1},
    )
    quotes, total, size = SUT.live_requote(client)
    assert [item["schema"] for item in quotes] == list(SUT.SCHEMAS)
    assert total == pytest.approx(8.93)
    assert size == 12
    assert len(client.metadata.cost_calls) == 3
    assert len(client.metadata.size_calls) == 3


def test_fresh_requote_blocks_at_ten() -> None:
    client = FakeClient(
        {"tbbo": 9.98, "definition": 0.01, "status": 0.01},
        {"tbbo": 10, "definition": 1, "status": 1},
    )
    with pytest.raises(SUT.AcquisitionError, match="strictly below USD 10"):
        SUT.live_requote(client)


def test_download_writes_inflight_before_exactly_one_paid_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "campaign"
    manifest_path = root / "download_manifest.json"
    manifest = {
        "status": "LIVE_QUOTED_NOT_DOWNLOADED",
        "downloads": [],
        "in_flight": None,
        "paid_timeseries_calls": 0,
    }
    SUT.write_json_atomic(manifest_path, manifest)
    client = FakeClient({}, {}, manifest_path)
    monkeypatch.setattr(SUT, "validate_dbn_file_v3", lambda path, schema: 7)
    item = SUT.download_one(
        client=client,
        schema="tbbo",
        quote={"estimated_usd": 8.9, "billable_bytes": 10},
        root=root,
        manifest=manifest,
        manifest_path=manifest_path,
    )
    assert len(client.timeseries.calls) == 1
    assert client.timeseries.calls[0]["stype_out"] == "instrument_id"
    assert item["records"] == 7
    assert manifest["paid_timeseries_calls"] == 1
    assert manifest["in_flight"] is None


def test_paid_failure_is_not_retried_and_keeps_inflight(
    tmp_path: Path,
) -> None:
    root = tmp_path / "campaign"
    manifest_path = root / "download_manifest.json"
    manifest = {
        "status": "LIVE_QUOTED_NOT_DOWNLOADED",
        "downloads": [],
        "in_flight": None,
        "paid_timeseries_calls": 0,
    }
    SUT.write_json_atomic(manifest_path, manifest)
    client = FakeClient({}, {}, manifest_path, fail=True)
    with pytest.raises(SUT.AcquisitionError, match="paid request failed"):
        SUT.download_one(
            client=client,
            schema="tbbo",
            quote={"estimated_usd": 8.9, "billable_bytes": 10},
            root=root,
            manifest=manifest,
            manifest_path=manifest_path,
        )
    assert len(client.timeseries.calls) == 1
    saved = json.loads(manifest_path.read_text(encoding="ascii"))
    assert saved["in_flight"]["schema"] == "tbbo"
    assert saved["paid_timeseries_calls"] == 0


def test_dbn_validator_rejects_non_zstd(tmp_path: Path) -> None:
    payload = tmp_path / "bad.dbn.zst.partial"
    payload.write_bytes(b"not-dbn")
    with pytest.raises(SUT.AcquisitionError, match="signature"):
        SUT.validate_dbn_file_v3(payload, "tbbo")


def test_owner_authority_keeps_outcomes_and_trading_closed() -> None:
    workspace = MODULE_PATH.resolve().parents[3]
    owner = SUT.validate_owner(workspace / SUT.OWNER_REL)
    assert owner["paid_source_acquisition_authorized"] is True
    assert owner["same_id_remote_retry_authorized"] is False
    assert owner["xauusd_outcome_authorized"] is False
    assert owner["mql5_authorized"] is False
    assert owner["live_trading_authorized"] is False

