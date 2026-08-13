from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "quote_event_depth_transfer_003_design.py"
SPEC = importlib.util.spec_from_file_location("event_depth_transfer_003_quote", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_clock_population_is_exact_and_hash_bound() -> None:
    workspace = MODULE.workspace_from_source()
    rows = MODULE.read_design_clocks(workspace / MODULE.CLOCK_REL)
    assert len(rows) == 329
    assert rows[0]["event_clock_id"] == "EVT0001"
    assert rows[-1]["event_clock_id"] == "EVT0329"


def test_window_is_exactly_sixty_seconds() -> None:
    window = MODULE.build_window({
        "event_clock_id": "EVT0001", "event_time_utc": "2019-01-03T15:00:00.000Z",
    })
    assert window["start"] == "2019-01-03T15:00:00.000Z"
    assert window["end"] == "2019-01-03T15:01:00.000Z"


def test_summary_passes_only_complete_bounded_quote() -> None:
    quotes = [
        {"event_clock_id": f"EVT{i:04d}", "event_time_utc": f"2019-01-01T00:00:{i % 60:02d}.000Z",
         "estimated_usd": 0.013, "billable_bytes": 100, "metadata_attempt": 1}
        for i in range(1, 330)
    ]
    result = MODULE.summarize(quotes)
    assert result["gate_pass"] is True
    quotes[0]["estimated_usd"] = 0.021
    assert MODULE.summarize(quotes)["gate_pass"] is False


def test_quote_source_has_no_paid_data_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "timeseries.get_range(" not in source
    assert ".batch." not in source
    assert ".subscribe(" not in source
    assert "metadata.get_cost(" in source
    assert "metadata.get_billable_size(" in source

