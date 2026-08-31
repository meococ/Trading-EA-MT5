from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from audit_candidate_frontier import (
    DEFAULT_LINEAGE_OVERRIDES,
    DEFAULT_REGISTRY,
    RegistryAuditError,
    build_frontier,
    extract_parent_ids,
    load_lineage_overrides,
    load_registry,
)


def _row(hypothesis_id: str, **overrides):
    row = {
        "hypothesis_id": hypothesis_id,
        "ea_name": overrides.pop("ea_name", f"EA_{hypothesis_id}"),
        "state": overrides.pop("state", "probe"),
        "verdict": overrides.pop("verdict", "PROBE"),
        "validation": overrides.pop("validation", {}),
        "parent_candidate": overrides.pop("parent_candidate", None),
    }
    row.update(overrides)
    return row


def _annotate(rows):
    return [dict(row, _line_number=index) for index, row in enumerate(rows, 1)]


def test_latest_append_row_controls_hypothesis_state():
    rows = _annotate(
        [
            _row(
                "HYP-TEST-ONE-001",
                state="screened",
                validation={
                    "economics_authorized": True,
                    "performance_metrics_authorized": True,
                    "model0_authorized": True,
                },
            ),
            _row("HYP-TEST-ONE-001", state="parked", verdict="PARK"),
        ]
    )
    result = build_frontier(rows, "A" * 64)
    assert result["verdict"] == "NO_OPEN_ECONOMIC_CANDIDATE"
    assert result["terminal_frontier_count"] == 1


def test_terminal_child_removes_stale_parent_from_leaf_frontier():
    rows = _annotate(
        [
            _row(
                "HYP-TEST-PARENT-001",
                state="screened",
                validation={
                    "economics_authorized": True,
                    "performance_metrics_authorized": True,
                    "model0_authorized": True,
                },
            ),
            _row(
                "HYP-TEST-CHILD-002",
                state="killed",
                parent_candidate="successor to HYP-TEST-PARENT-001",
            ),
        ]
    )
    result = build_frontier(rows, "B" * 64)
    assert result["graph_leaves"] == 1
    assert result["open_economic"] == []
    assert result["terminal_frontier_count"] == 1


def test_collection_authority_never_becomes_economic_authority():
    rows = _annotate(
        [
            _row(
                "HYP-TEST-COLLECT-001",
                state="screened",
                verdict="DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
                validation={"data_acquisition_authorized": True},
            )
        ]
    )
    result = build_frontier(rows, "C" * 64)
    assert len(result["collection_only"]) == 1
    assert result["open_economic"] == []


def test_explicit_lineage_override_shadows_stale_collection_leaf():
    rows = _annotate(
        [
            _row(
                "HYP-TEST-SERIES-001",
                ea_name="EA_V1",
                state="screened",
                verdict="COLLECTION_ELIGIBLE",
            ),
            _row(
                "HYP-TEST-SERIES-002",
                ea_name="EA_V2",
                state="parked",
                verdict="TERMINAL_REVISION",
            ),
        ]
    )
    result = build_frontier(
        rows,
        "E" * 64,
        [
            {
                "parent_hypothesis_id": "HYP-TEST-SERIES-001",
                "superseding_hypothesis_id": "HYP-TEST-SERIES-002",
            }
        ],
    )
    assert result["graph_leaves"] == 1
    assert result["applied_lineage_override_count"] == 1
    assert result["collection_only"] == []
    assert result["terminal_frontier_count"] == 1


def test_explicit_economic_authority_is_required_for_open_candidate():
    rows = _annotate(
        [
            _row("HYP-TEST-STALE-001", state="screened"),
            _row(
                "HYP-TEST-OPEN-002",
                state="screened",
                validation={
                    "economics_authorized": True,
                    "performance_metrics_authorized": True,
                    "model0_performance_authorized": True,
                },
            ),
        ]
    )
    result = build_frontier(rows, "D" * 64)
    assert [row["hypothesis_id"] for row in result["open_economic"]] == [
        "HYP-TEST-OPEN-002"
    ]
    assert [row["hypothesis_id"] for row in result["stale_nonterminal"]] == [
        "HYP-TEST-STALE-001"
    ]


def test_one_true_authority_flag_is_not_open_economic_authority():
    rows = _annotate(
        [
            _row(
                "HYP-TEST-PARTIAL-001",
                state="screened",
                validation={"model0_performance_authorized": True},
            )
        ]
    )
    result = build_frontier(rows, "F" * 64)
    assert result["open_economic"] == []
    assert len(result["stale_nonterminal"]) == 1


def test_parent_extraction_handles_embedded_ids():
    assert extract_parent_ids(
        "HYP-TEST-ONE-001 plus successor HYP-TEST-TWO-002 (frozen)"
    ) == {"HYP-TEST-ONE-001", "HYP-TEST-TWO-002"}


def test_load_registry_hashes_exact_bytes_and_rejects_bad_json(tmp_path: Path):
    good = tmp_path / "good.jsonl"
    payload = json.dumps(_row("HYP-TEST-LOAD-001")) + "\n"
    good.write_text(payload, encoding="utf-8")
    rows, digest = load_registry(good)
    assert rows[0]["_line_number"] == 1
    assert digest == hashlib.sha256(good.read_bytes()).hexdigest().upper()

    bad = tmp_path / "bad.jsonl"
    bad.write_text("{bad json}\n", encoding="utf-8")
    with pytest.raises(RegistryAuditError, match="line 1: invalid JSON"):
        load_registry(bad)


def test_real_lineage_override_is_registry_and_receipt_bound():
    rows, digest = load_registry(DEFAULT_REGISTRY)
    edges = load_lineage_overrides(DEFAULT_LINEAGE_OVERRIDES, digest, rows)
    assert edges == [
        {
            "parent_hypothesis_id": "HYP-PTR-T2-DATA-EPOCH-D0-M5-001",
            "superseding_hypothesis_id": "HYP-PTR-T2-DATA-EPOCH-D0-M5-005",
            "authority_receipt_path": "04. Memory/research/20260813_UNRUN_EA_SHELF_DATABASE_AUDIT.md",
            "authority_receipt_sha256": "F6AEB7C8DD053EA886AF6C2B328551E5C848666C1D29EC8F83F862E0C3C4B6E0",
        }
    ]
    with pytest.raises(RegistryAuditError, match="registry SHA256"):
        load_lineage_overrides(DEFAULT_LINEAGE_OVERRIDES, "0" * 64, rows)
