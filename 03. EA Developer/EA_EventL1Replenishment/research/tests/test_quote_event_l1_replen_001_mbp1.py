from __future__ import annotations

from datetime import datetime
import importlib.util
from pathlib import Path
import re
import sys

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "quote_event_l1_replen_001_mbp1.py"
SPEC = importlib.util.spec_from_file_location("event_l1_replen_001_quote", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_build_window_is_exact_half_open_120_seconds() -> None:
    row = {
        "request_id": "EVT0001", "event_clock_id": "EVT0001", "split": "DESIGN",
        "event_time_utc": "2019-01-03T15:00:00.000Z",
    }
    window = MODULE.build_window(row)
    assert window["start"] == "2019-01-03T15:00:00.000Z"
    assert window["end"] == "2019-01-03T15:02:00.000Z"


def test_live_clock_population_is_exact_design_only_and_pilot_is_first() -> None:
    rows = MODULE.load_design_clocks(MODULE.workspace_from_source() / MODULE.CLOCK_REL)
    assert len(rows) == 329
    assert rows[0]["event_clock_id"] == "EVT0001"
    assert {datetime.fromisoformat(row["event_time_utc"].replace("Z", "+00:00")).year for row in rows} == {2019, 2020}


def test_quote_all_uses_mbp1_metadata_only_and_sorts() -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class Metadata:
        def get_cost(self, **kwargs):
            calls.append(("cost", kwargs)); return 0.02
        def get_billable_size(self, **kwargs):
            calls.append(("size", kwargs)); return 456

    class Client:
        metadata = Metadata()

    windows = [MODULE.build_window({
        "request_id": event_id, "event_clock_id": event_id, "split": "DESIGN",
        "event_time_utc": event_time,
    }) for event_id, event_time in (
        ("EVT0002", "2019-01-04T13:30:00.000Z"),
        ("EVT0001", "2019-01-03T15:00:00.000Z"),
    )]
    result = MODULE.quote_all(lambda: Client(), windows, workers=1)
    assert [row["request_id"] for row in result] == ["EVT0001", "EVT0002"]
    assert len(calls) == 4
    for name, kwargs in calls:
        assert kwargs["schema"] == "mbp-1"
        assert kwargs["symbols"] == ["6E.v.0"]
        if name == "cost":
            assert kwargs["mode"] == "historical-streaming"


@pytest.mark.parametrize("workers", [0, 17])
def test_worker_count_is_bounded(workers: int) -> None:
    with pytest.raises(MODULE.QuoteError, match="workers"):
        MODULE.quote_all(lambda: object(), [], workers)


def test_normalized_hash_ignores_only_registry_sentinel() -> None:
    raw = MODULE_PATH.read_bytes()
    base = MODULE.normalized_tool_base_sha256(raw)
    unarmed = re.sub(
        rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")$',
        b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None", raw,
        count=1, flags=re.MULTILINE,
    )
    assert MODULE.normalized_tool_base_sha256(unarmed) == base


def test_quote_source_has_no_payload_execution_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert ".timeseries." not in source
    assert ".batch." not in source
    assert "get_range(" not in source
    assert "submit_job(" not in source


def test_authority_fails_closed_when_unarmed(monkeypatch) -> None:
    monkeypatch.setattr(MODULE, "REVIEWED_REGISTRY_ROW_SHA256", None)
    with pytest.raises(MODULE.QuoteError, match="sentinel"):
        MODULE.validate_authority(MODULE.workspace_from_source())


def test_api_key_is_not_embedded() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "DATABENTO_API_KEY" in source
    assert not any(token.startswith("db-") and len(token) > 24
                   for token in source.replace('"', " ").replace("'", " ").split())

