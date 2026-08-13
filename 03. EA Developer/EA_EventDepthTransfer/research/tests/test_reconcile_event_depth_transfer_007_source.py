from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "reconcile_event_depth_transfer_007_source.py"
SPEC = importlib.util.spec_from_file_location("event_depth_transfer_007", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_owner_authority_is_explicit_and_opens_no_new_spend_or_live() -> None:
    workspace = MODULE.workspace_from_source()
    authority = MODULE.validate_authority(workspace / MODULE.AUTHORITY_REL)
    assert authority["authority_scope"]["artifact_integrity_reconciliation_authorized"] is True
    assert authority["authority_scope"]["additional_spend_authorized"] is False
    assert authority["authority_scope"]["live_trading_authorized"] is False
    assert authority["spend_reconciliation"]["aggregate_worst_case_quoted_exposure_usd"] < 10


def test_input_hashes_and_population_are_frozen() -> None:
    parent, child, receipt, ledger = MODULE.load_inputs(MODULE.workspace_from_source())
    assert sum(item["status"] == "COMPLETE" for item in parent["entries"]) == 256
    assert sum(item["status"] == "COMPLETE" for item in child["entries"]) == 63
    assert receipt["outcome_prices_read"] is False
    assert len(ledger) == 329


def test_reconciliation_verifies_every_complete_artifact_and_balances() -> None:
    clean, summary = MODULE.reconcile(MODULE.workspace_from_source())
    assert len(clean) == 329
    assert summary["verified_complete_files"] == 319
    assert summary["gate_pass"] is True
    assert summary["classification_counts"] == {"CONTINUATION": 146, "REVERSAL": 172}
    assert summary["direction_counts"] == {"-1": 156, "0": 11, "1": 162}


def test_reconciler_has_no_network_or_paid_surface() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "import databento" not in source.lower()
    assert "timeseries.get_range" not in source
    assert "metadata.get_cost" not in source
    assert 'glob("*.partial")' not in source
    assert 'rglob("*.partial")' not in source
