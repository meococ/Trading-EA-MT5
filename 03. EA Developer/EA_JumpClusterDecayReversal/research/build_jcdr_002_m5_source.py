#!/usr/bin/env python3
"""One-shot, outcome-blind source probe for HYP-JCDR-EURUSD-M5-002.

This module deliberately reuses the reviewed JCDR001 source-safety primitives
(canonical JSON, immutable file reads, exact-once ledgers, public manifest
validation and outcome-field rejection). It replaces only the material decision
surface: exact-five-constituent UTC M5 construction and M5 event state.

Import and default CLI execution cannot read DESIGN data. Production requires
both ``--execute-probe`` and the exact latest preregistered registry-row SHA in
``REVIEWED_REGISTRY_ROW_SHA256``. The sentinel is disarmed by default.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
import os
import stat
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Sequence


HYPOTHESIS_ID = "HYP-JCDR-EURUSD-M5-002"
EA_NAME = "EA_JumpClusterDecayReversal"
FAMILY = "m5-jump-cluster-decay-reversal"
ATTEMPT_ID = "JCDR002-SOURCE-001"

PLAN_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/"
    "HYP-JCDR-EURUSD-M5-002_SOURCE_FEASIBILITY_PLAN.md"
)
PLAN_SHA256 = "EDC834C63CCDFC55F3A73F34E2FE6EB02DCD7A9B1DEB8F634FD7AC2EF88B2408"
BUILDER_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/"
    "build_jcdr_002_m5_source.py"
)
TEST_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/tests/"
    "test_build_jcdr_002_m5_source.py"
)
BASE_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/"
    "build_jcdr_001_source.py"
)
BASE_SHA256 = "B0ABCE7136A32FE014FF71C32DE2D18DE84941E0CC547731CCF4E5540588EEF7"
REVIEW_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/"
    "HYP-JCDR-EURUSD-M5-002_SOURCE_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REVIEW_SCHEMA = "jcdr_002_source_implementation_review_receipt.v1"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_JumpClusterDecayReversal/research/evidence/"
    "HYP-JCDR-EURUSD-M5-002_SOURCE_FEASIBILITY/JCDR002-SOURCE-001"
)

REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
REGISTRY_VALIDATOR_REL = "04. Memory/research/validate_candidate_registry.py"
REGISTRY_SCHEMA_REL = "04. Memory/research/CANDIDATE_REGISTRY.schema.json"
REGISTRY_VALIDATOR_SHA256 = "3290DD36F72BBA68D2BCE037E570DBD025561743D30531680E4CB297E796730C"
REGISTRY_SCHEMA_SHA256 = "B930C4B82535BE71C598D073F72FE51CF774048543B7EB21C51F671C64AF1392"

# This exact line is normalized to None when the reviewed builder SHA is
# calculated. Arming it changes execution authority without changing the
# reviewed computational-base digest.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None

UTC = timezone.utc
PIP = 0.0001
M5_MINUTES = 5
LOOKBACK_RETURNS = 48
JUMP_FLOOR_PIPS = 1.20
JUMP_SCALE_MULT = 3.0
CLUSTER_BARS = 15
MIN_CLUSTER_JUMPS = 3
COHERENCE_MIN = 0.80
MIN_DISPLACEMENT_PIPS = 4.0
DECAY_MAX_BARS = 10
RETRACE_MIN = 0.25
RETRACE_MAX = 1.00
NO_JUMP_LOOKBACK = 2
HORIZON_M1_BARS = 60
MIN_STOP_PIPS = 6.0
STOP_BUFFER_PIPS = 0.50
COST_PIPS = 1.50

DESIGN_START = date(2016, 1, 4)
DESIGN_END = date(2020, 12, 31)
ELAPSED_CALENDAR_WEEKS = (DESIGN_END - DESIGN_START).days / 7.0

ACCEPTANCE_CONTRACT = {
    "max_drawdown_pct": 8,
    "max_monte_carlo_p95_dd_pct": 8,
    "max_trades_per_week": 5,
    "min_cost_pf_x1_5": 1.25,
    "min_cost_pf_x2": 1.0,
    "min_profit_factor": 1.3,
    "min_trades_per_week": 2,
}
REGISTRY_REQUIRED_TRUE = {
    "source_feasibility_only",
    "source_run_authorized",
}
REGISTRY_BINDING_KEYS = {
    "source_feasibility_attempt_limit",
    "source_feasibility_attempt_id",
    "source_feasibility_evidence_root",
    "probe_status",
    "independent_implementation_review_status",
    "independent_pre_run_review_status",
    "independent_quant_prereg_review_status",
    "reviewed_builder_path",
    "reviewed_builder_base_sha256",
    "reviewed_test_path",
    "reviewed_test_sha256",
    "reviewed_base_path",
    "reviewed_base_sha256",
    "independent_review_receipt_path",
    "independent_review_receipt_schema",
    "independent_review_receipt_sha256",
    "design_m1_manifest_path",
    "design_m1_manifest_sha256",
    "design_m1_receipt_path",
    "design_m1_receipt_sha256",
    "design_m1_source_sha256",
    "registry_validator_path",
    "registry_validator_sha256",
    "registry_schema_path",
    "registry_schema_sha256",
}
def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _load_reviewed_base() -> object:
    """Load the frozen JCDR001 primitives without reading market data."""

    path = Path(__file__).with_name("build_jcdr_001_source.py")
    payload = path.read_bytes()
    if _sha256(payload) != BASE_SHA256:
        raise RuntimeError("JCDR001 reviewed base SHA mismatch")
    spec = importlib.util.spec_from_file_location("_jcdr001_reviewed_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load JCDR001 reviewed base")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


BASE = _load_reviewed_base()
ContractError = BASE.ContractError
REGISTRY_VALIDATION_KEYS = (
    REGISTRY_REQUIRED_TRUE | REGISTRY_BINDING_KEYS | set(BASE.SEALED_FALSE_FIELDS)
)


def _configure_base_for_m5() -> None:
    """Bind generic reviewed event/ledger primitives to the frozen M5 plan."""

    BASE.HYPOTHESIS_ID = HYPOTHESIS_ID
    BASE.EA_NAME = EA_NAME
    BASE.FAMILY = FAMILY
    BASE.ATTEMPT_ID = ATTEMPT_ID
    BASE.LOOKBACK_RETURNS = LOOKBACK_RETURNS
    BASE.JUMP_FLOOR_PIPS = JUMP_FLOOR_PIPS
    BASE.JUMP_SCALE_MULT = JUMP_SCALE_MULT
    BASE.CLUSTER_BARS = CLUSTER_BARS
    BASE.MIN_CLUSTER_JUMPS = MIN_CLUSTER_JUMPS
    BASE.COHERENCE_MIN = COHERENCE_MIN
    BASE.MIN_DISPLACEMENT_PIPS = MIN_DISPLACEMENT_PIPS
    BASE.DECAY_MAX_BARS = DECAY_MAX_BARS
    BASE.RETRACE_MIN = RETRACE_MIN
    BASE.RETRACE_MAX = RETRACE_MAX
    BASE.NO_JUMP_LOOKBACK = NO_JUMP_LOOKBACK
    # Ledger horizon remains 60 exact M1 starts; the event state is M5.
    BASE.HORIZON_BARS = HORIZON_M1_BARS
    BASE.MIN_STOP_PIPS = MIN_STOP_PIPS
    BASE.STOP_BUFFER_PIPS = STOP_BUFFER_PIPS
    BASE.COST_PIPS = COST_PIPS
    # The terminal JCDR001 base intentionally retains its historical registry
    # bindings. This successor binds the currently authoritative validator and
    # schema inside its isolated process before invoking the reviewed snapshot
    # validation primitive.
    BASE.REGISTRY_VALIDATOR_SHA256 = REGISTRY_VALIDATOR_SHA256
    BASE.REGISTRY_SCHEMA_SHA256 = REGISTRY_SCHEMA_SHA256

    def assign_source_signal_id(decision: datetime) -> str:
        identity = f"{HYPOTHESIS_ID}|SOURCE|{BASE._iso_z(decision)}".encode("ascii")
        return f"JCDR002-SRC-{BASE.sha256_bytes(identity)[:16]}"

    BASE.assign_source_signal_id = assign_source_signal_id


_configure_base_for_m5()


def _m5_group_start(value: datetime) -> datetime:
    at = BASE._as_utc(value)
    if at.second or at.microsecond:
        raise ContractError("M1 timestamp must be minute aligned")
    return at.replace(minute=at.minute - at.minute % M5_MINUTES)


def construct_exact_m5(
    m1_rows: Sequence[Mapping[str, object]],
) -> tuple[list[list[dict[str, object]]], dict[str, int]]:
    """Construct only exact UTC M5 bars and split at every incomplete group.

    The M5 ``time_utc`` is the fifth constituent's M1-open timestamp (g+4m).
    Consequently the existing reviewed next-minute availability rule maps to
    g+5m, exactly the next M5 open, without same-bar execution.
    """

    immutable = BASE._immutable_m1_copy(m1_rows)
    ordered = sorted(immutable, key=lambda row: BASE._as_utc(row["time_utc"]))
    times = [BASE._as_utc(row["time_utc"]) for row in ordered]
    if len(times) != len(set(times)):
        raise ContractError("duplicate M1 timestamps")

    groups: dict[datetime, list[dict[str, object]]] = {}
    for row in ordered:
        start = _m5_group_start(BASE._as_utc(row["time_utc"]))
        groups.setdefault(start, []).append(dict(row))

    complete_by_start: dict[datetime, dict[str, object]] = {}
    incomplete_groups = 0
    for start in sorted(groups):
        rows = sorted(groups[start], key=lambda row: BASE._as_utc(row["time_utc"]))
        expected = [start + timedelta(minutes=i) for i in range(M5_MINUTES)]
        observed = [BASE._as_utc(row["time_utc"]) for row in rows]
        if observed != expected:
            incomplete_groups += 1
            continue
        opens = [float(row["open"]) for row in rows]
        highs = [float(row["high"]) for row in rows]
        lows = [float(row["low"]) for row in rows]
        closes = [float(row["close"]) for row in rows]
        bar = {
            "time_utc": start + timedelta(minutes=M5_MINUTES - 1),
            "open": opens[0],
            "high": max(highs),
            "low": min(lows),
            "close": closes[-1],
            "m5_start_utc": start,
        }
        BASE._ohlc(bar)
        complete_by_start[start] = bar

    # Missing whole groups and partial groups both break continuity. Iterating
    # only complete starts with an exact +5m requirement provides that reset.
    segments: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    prior_start: datetime | None = None
    gap_breaks = 0
    for start in sorted(complete_by_start):
        bar = complete_by_start[start]
        if prior_start is None or start - prior_start == timedelta(minutes=M5_MINUTES):
            current.append(bar)
        else:
            if current:
                segments.append(current)
            current = [bar]
            gap_breaks += 1
        prior_start = start
    if current:
        segments.append(current)

    quality = {
        "input_m1_rows": len(ordered),
        "nonempty_aligned_m5_groups": len(groups),
        "complete_exact_five_m5_groups": len(complete_by_start),
        "incomplete_nonempty_m5_groups": incomplete_groups,
        "contiguous_m5_segments": len(segments),
        "m5_gap_breaks": gap_breaks,
    }
    if quality["complete_exact_five_m5_groups"] + incomplete_groups != len(groups):
        raise ContractError("M5 construction reconciliation failed")
    return segments, quality


def _rebind_candidate_ids(ledgers: Mapping[str, object]) -> dict[str, object]:
    """Replace the legacy JCDR001 display prefix and recompute reconciliation.

    The reviewed base already hashes the rebound HYPOTHESIS_ID into candidate
    identity; only its human-readable prefix was hard-coded. Recomputing the
    exact-once projection after replacement prevents a stale digest from
    certifying different durable identities.
    """

    result = dict(ledgers)
    rebound: dict[str, list[dict[str, object]]] = {}
    for arm in ("TRUE", "FOLLOW_CONTROL"):
        rows = result.get(arm)
        if type(rows) is not list:
            raise ContractError("ledger arm missing during identity rebind")
        rebound_rows: list[dict[str, object]] = []
        expected_prefix = f"JCDR001-{arm}-"
        target_prefix = f"JCDR002-{arm}-"
        for source in rows:
            if type(source) is not dict:
                raise ContractError("ledger row malformed during identity rebind")
            row = dict(source)
            candidate_id = row.get("candidate_id")
            if type(candidate_id) is not str or not candidate_id.startswith(expected_prefix):
                raise ContractError("legacy candidate identity shape changed")
            row["candidate_id"] = target_prefix + candidate_id[len(expected_prefix) :]
            rebound_rows.append(row)
        rebound[arm] = rebound_rows
        result[arm] = rebound_rows
    classifications = result.get("classifications")
    raw_count = result.get("raw_first_per_day_count")
    if type(classifications) is not list or type(raw_count) is not int:
        raise ContractError("ledger reconciliation inputs malformed")
    result["exact_once"] = BASE.reconcile_exact_once(
        classifications=classifications,
        true_rows=rebound["TRUE"],
        follow_rows=rebound["FOLLOW_CONTROL"],
        raw_first_per_day_count=raw_count,
    )
    BASE.assert_outcome_blind(result)
    return result


def _canonical_projection(report: Mapping[str, object]) -> dict[str, object]:
    stage0 = report.get("stage0")
    if type(stage0) is not dict:
        raise ContractError("source report lacks Stage-0")
    projection = {
        "hypothesis_id": report.get("hypothesis_id"),
        "attempt_id": report.get("attempt_id"),
        "arm_counts": report.get("arm_counts"),
        "population": report.get("population"),
        "construction_diagnostics": report.get("construction_diagnostics"),
        "formation_funnel": report.get("formation_funnel"),
        "horizon_funnel": report.get("horizon_funnel"),
        "raw_signal_classifications": report.get("raw_signal_classifications"),
        "exact_once": report.get("exact_once"),
        "signal_ledgers": report.get("signal_ledgers"),
        "stage0": {
            "verdict": stage0.get("verdict"),
            "gates": stage0.get("gates"),
            "metrics": stage0.get("metrics"),
        },
        "economics_authorized": report.get("economics_authorized"),
        "post_entry_ohlc_rows_read": report.get("post_entry_ohlc_rows_read"),
        "outcome_fields_emitted": report.get("outcome_fields_emitted"),
        "returns_computed": report.get("returns_computed"),
        "trades_simulated": report.get("trades_simulated"),
        "performance_trials_executed": report.get("performance_trials_executed"),
    }
    BASE.assert_outcome_blind(projection)
    return projection


def scan_source_once(m1_rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Pure source scan. Post-availability OHLC is never indexed or copied."""

    immutable = BASE._immutable_m1_copy(m1_rows)
    segments, quality = construct_exact_m5(immutable)
    observed_m1 = {BASE._as_utc(row["time_utc"]) for row in immutable}
    raw_signals, funnel = BASE.select_raw_signals(segments)
    ledgers = _rebind_candidate_ids(BASE.build_matched_ledgers(raw_signals, observed_m1))
    stage0 = BASE.evaluate_stage0_gates(
        true_signals=ledgers["TRUE"],
        follow_signals=ledgers["FOLLOW_CONTROL"],
        raw_first_per_day_count=int(ledgers["raw_first_per_day_count"]),
        horizon_records=ledgers["horizons"],
        formation_complete=int(quality["complete_exact_five_m5_groups"]),
        formation_scheduled=int(quality["nonempty_aligned_m5_groups"]),
        elapsed_weeks=ELAPSED_CALENDAR_WEEKS,
    )
    exact = ledgers["exact_once"]
    report = {
        "schema_version": "jcdr_002_m5_source_feasibility_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "ea_name": EA_NAME,
        "feature_family": FAMILY,
        "attempt_id": ATTEMPT_ID,
        "evidence_class": "OUTCOME_BLIND_SOURCE_AND_CADENCE_ONLY",
        "mechanism_status": "PLAUSIBLE_UNVALIDATED_FALSIFICATION_PRIOR",
        "literature_status": "JUMP_CLUSTERING_PRIOR_NOT_PRICE_REVERSAL_PROOF",
        "source_contract": {
            "design_start": DESIGN_START.isoformat(),
            "design_end": DESIGN_END.isoformat(),
            "elapsed_calendar_weeks": ELAPSED_CALENDAR_WEEKS,
            "m1_manifest_sha256": BASE.M1_MANIFEST_SHA256,
            "m1_receipt_sha256": BASE.M1_RECEIPT_SHA256,
            "m1_source_sha256": BASE.M1_SOURCE_SHA256,
            "plan_sha256": PLAN_SHA256,
            "reviewed_base_sha256": BASE_SHA256,
            "m5_exact_constituents": M5_MINUTES,
            "m5_decision_stamp_offset_minutes": 4,
            "availability_offset_from_decision_stamp_minutes": 1,
            "robust_scale_lookback_m5_returns": LOOKBACK_RETURNS,
            "jump_floor_pips": JUMP_FLOOR_PIPS,
            "jump_scale_mult": JUMP_SCALE_MULT,
            "cluster_m5_bars": CLUSTER_BARS,
            "min_cluster_jumps": MIN_CLUSTER_JUMPS,
            "coherence_min": COHERENCE_MIN,
            "min_displacement_pips": MIN_DISPLACEMENT_PIPS,
            "decay_max_m5_bars": DECAY_MAX_BARS,
            "retrace_band": [RETRACE_MIN, RETRACE_MAX],
            "horizon_m1_bars": HORIZON_M1_BARS,
            "ohlc_only_signal_inputs": True,
        },
        "arm_counts": {
            "TRUE_REVERSAL": len(ledgers["TRUE"]),
            "FOLLOW_CONTROL": len(ledgers["FOLLOW_CONTROL"]),
        },
        # Base ledgers retain arm labels TRUE/FOLLOW_CONTROL so the reviewed
        # exact-once reconciler remains byte-for-byte reusable.
        "signal_ledgers": {
            "TRUE": ledgers["TRUE"],
            "FOLLOW_CONTROL": ledgers["FOLLOW_CONTROL"],
        },
        "raw_signal_classifications": list(ledgers["classifications"]),
        "exact_once": {
            "raw_first_per_day_count": exact["raw_first_per_day_count"],
            "classification_count": exact["classification_count"],
            "executable_count": exact["executable_count"],
            "excluded_count": exact["excluded_count"],
            "raw_equals_classifications": exact["raw_equals_classifications"],
            "classifications_equal_executable_plus_excluded": exact[
                "classifications_equal_executable_plus_excluded"
            ],
            "max_one_decision_per_utc_date": exact["max_one_decision_per_utc_date"],
            "exact_once_reconciliation": exact["exact_once_reconciliation"],
            "classification_digest_sha256": exact["classification_digest_sha256"],
            "arm_identity_projection": exact["arm_identity_projection"],
        },
        "population": {
            "raw_first_per_day_count": ledgers["raw_first_per_day_count"],
            "horizon_excluded_count": ledgers["horizon_excluded_count"],
            "eligible_count": ledgers["eligible_count"],
        },
        "construction_diagnostics": quality,
        "formation_funnel": funnel,
        "horizon_funnel": {
            "raw_first_per_day": ledgers["raw_first_per_day_count"],
            "source_executable": sum(
                row.get("source_executable") is True for row in ledgers["horizons"]
            ),
            "horizon_incomplete": sum(
                row.get("source_executable") is not True for row in ledgers["horizons"]
            ),
        },
        "stage0": stage0,
        "economics_authorized": False,
        "future_economics_requires_separate_prereg": True,
        "source_pass_is_not_edge_evidence": True,
        "post_entry_ohlc_rows_read": 0,
        "outcome_fields_emitted": 0,
        "returns_computed": 0,
        "trades_simulated": 0,
        "performance_trials_executed": 0,
    }
    BASE.assert_outcome_blind(report)
    return report


def scan_source(m1_rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Run a deterministic independent replay over a deep immutable copy."""

    primary = scan_source_once(m1_rows)
    copy_rows = BASE._immutable_m1_copy(m1_rows)
    replay = scan_source_once(copy_rows)
    primary_projection = _canonical_projection(primary)
    replay_projection = _canonical_projection(replay)
    primary_bytes = BASE.canonical_json(primary_projection)
    replay_bytes = BASE.canonical_json(replay_projection)
    if primary_bytes != replay_bytes:
        raise ContractError("independent replay canonical projection mismatch")
    digest = BASE.sha256_bytes(primary_bytes)
    report = dict(primary)
    report["independent_replay"] = {
        "primary_canonical_digest_sha256": digest,
        "replay_canonical_digest_sha256": BASE.sha256_bytes(replay_bytes),
        "digests_equal": True,
        "exact_once_reconciliation": True,
    }
    BASE.assert_outcome_blind(report)
    return report


def _reviewed_builder_sha(payload: bytes) -> str:
    """Hash code with the one execution sentinel normalized to disarmed."""

    lines = payload.splitlines(keepends=True)
    prefix = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = "
    matches = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(matches) != 1:
        raise ContractError("builder sentinel line missing or duplicated")
    index = matches[0]
    newline = b"\r\n" if lines[index].endswith(b"\r\n") else b"\n"
    lines[index] = prefix + b"None" + newline
    return BASE.sha256_bytes(b"".join(lines))


def _latest_registry_row(registry_payload: bytes) -> tuple[dict[str, object], bytes]:
    latest: tuple[dict[str, object], bytes] | None = None
    rows, raw_rows = BASE.parse_registry_jsonl(registry_payload)
    for row, raw in zip(rows, raw_rows):
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            latest = (row, raw)
    if latest is None:
        raise ContractError("hypothesis registry row missing")
    if BASE.canonical_json(latest[0]) + b"\n" != latest[1]:
        raise ContractError("selected registry row is not canonical")
    return latest


def _validate_authority(
    registry_payload: bytes,
    *,
    builder_payload: bytes,
    test_payload: bytes,
    review_payload: bytes,
) -> tuple[dict[str, object], str]:
    row, raw = _latest_registry_row(registry_payload)
    raw_sha = BASE.sha256_bytes(raw)
    if REVIEWED_REGISTRY_ROW_SHA256 != raw_sha:
        raise ContractError("latest registry row does not match armed reviewed SHA")
    if (
        row.get("schema_version") != "alphafactory_candidate_registry.v1"
        or row.get("record_type") != "hypothesis_state"
        or row.get("hypothesis_id") != HYPOTHESIS_ID
        or row.get("ea_name") != EA_NAME
        or row.get("feature_family") != FAMILY
        or row.get("lane") != "EURUSD-M5-jump-cluster-decay-reversal-source-feasibility"
        or row.get("parent_candidate") != "HYP-JCDR-EURUSD-M1-001"
        or row.get("model") is not None
        or row.get("state") != "probe"
        or row.get("verdict") != "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN"
        or row.get("prereg_path") != PLAN_REL
        or row.get("prereg_sha256") != PLAN_SHA256
        or row.get("symbol") != "EURUSD"
        or row.get("timeframe") != "M5"
        or row.get("window") != {"from": "2016.01.04", "to": "2020.12.31"}
        or row.get("acceptance_contract") != ACCEPTANCE_CONTRACT
        or row.get("metrics") != BASE.SOURCE_ONLY_ZERO_METRICS
        or row.get("run_ids") != []
        or row.get("source_path") is not None
        or row.get("source_hash") is not None
    ):
        raise ContractError("registry identity/prereg authority mismatch")
    validation = row.get("validation")
    if type(validation) is not dict:
        raise ContractError("registry validation object missing")
    required = {
        "source_feasibility_only": True,
        "source_run_authorized": True,
        "source_feasibility_attempt_limit": 1,
        "source_feasibility_attempt_id": ATTEMPT_ID,
        "source_feasibility_evidence_root": EVIDENCE_ROOT_REL,
        "reviewed_builder_path": BUILDER_REL,
        "reviewed_builder_base_sha256": _reviewed_builder_sha(builder_payload),
        "reviewed_test_path": TEST_REL,
        "reviewed_test_sha256": BASE.sha256_bytes(test_payload),
        "reviewed_base_path": BASE_REL,
        "reviewed_base_sha256": BASE_SHA256,
        "independent_review_receipt_path": REVIEW_REL,
        "independent_review_receipt_schema": REVIEW_SCHEMA,
        "independent_review_receipt_sha256": BASE.sha256_bytes(review_payload),
        "design_m1_manifest_path": BASE.M1_MANIFEST_REL,
        "design_m1_manifest_sha256": BASE.M1_MANIFEST_SHA256,
        "design_m1_receipt_path": BASE.M1_RECEIPT_REL,
        "design_m1_receipt_sha256": BASE.M1_RECEIPT_SHA256,
        "design_m1_source_sha256": BASE.M1_SOURCE_SHA256,
        "probe_status": "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "independent_implementation_review_status": "PASS",
        "independent_pre_run_review_status": "PASS",
        "independent_quant_prereg_review_status": "PASS",
        "registry_validator_path": REGISTRY_VALIDATOR_REL,
        "registry_validator_sha256": REGISTRY_VALIDATOR_SHA256,
        "registry_schema_path": REGISTRY_SCHEMA_REL,
        "registry_schema_sha256": REGISTRY_SCHEMA_SHA256,
    }
    for key, expected in required.items():
        if validation.get(key) != expected:
            raise ContractError(f"registry authority mismatch: {key}")
    for key in BASE.SEALED_FALSE_FIELDS:
        if validation.get(key) is not False:
            raise ContractError(f"sealed registry permission not false: {key}")
    if set(validation) != REGISTRY_VALIDATION_KEYS:
        raise ContractError("registry validation field set mismatch")
    review = BASE.parse_canonical_object(review_payload, label="implementation review")
    expected_review = {
        "schema_version": REVIEW_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "review_status": "PASS",
        "reviewed_builder": {
            "path": BUILDER_REL,
            "base_sha256": _reviewed_builder_sha(builder_payload),
        },
        "reviewed_tests": {
            "path": TEST_REL,
            "sha256": BASE.sha256_bytes(test_payload),
        },
        "v1_plan": {"path": PLAN_REL, "sha256": PLAN_SHA256},
        "permissions": {
            "source_feasibility_run": True,
            "performance_or_economics": False,
            "mt5_or_mql5": False,
        },
    }
    if review != expected_review:
        raise ContractError("implementation review contract mismatch")
    BASE.assert_outcome_blind(review)
    return row, raw_sha


def _mkdir_evidence_root(workspace: Path, reviewed_row_sha: str) -> Path:
    relative = Path(EVIDENCE_ROOT_REL)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ContractError("invalid evidence-root contract")
    current = workspace
    for component in relative.parts[:-1]:
        current /= component
        try:
            os.mkdir(current)
        except FileExistsError:
            pass
        info = os.lstat(current)
        if not stat.S_ISDIR(info.st_mode) or current.is_symlink() or BASE._is_reparse(info):
            raise ContractError("evidence parent is not a private directory")
    root = current / relative.parts[-1]
    try:
        os.mkdir(root)
    except FileExistsError as exc:
        raise ContractError("one-shot evidence root already exists") from exc
    BASE._write_new_canonical(
        root / "attempt_started.json",
        {
            "schema_version": "jcdr_002_attempt_started.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "reviewed_registry_row_sha256": reviewed_row_sha,
            "status": "STARTED",
            "source_only_counters": BASE._executed_source_only_counters(),
            "sealed_permissions": BASE._sealed_permissions(),
        },
    )
    return root


def _persist_success(
    root: Path, report: Mapping[str, object], reviewed_row_sha: str
) -> dict[str, object]:
    BASE.assert_outcome_blind(report)
    started_sha = BASE.sha256_bytes(BASE._artifact_bytes(root / "attempt_started.json"))
    enriched = dict(report)
    enriched["artifact_binding"] = {
        "attempt_id": ATTEMPT_ID,
        "attempt_started_sha256": started_sha,
        "reviewed_registry_row_sha256": reviewed_row_sha,
    }
    enriched["source_only_counters"] = BASE._executed_source_only_counters()
    enriched["sealed_permissions"] = BASE._sealed_permissions()
    BASE.assert_outcome_blind(enriched)
    BASE._write_new_canonical(root / "jcdr_002_source_report.json", enriched)

    classifications = enriched.get("raw_signal_classifications")
    if type(classifications) is not list:
        raise ContractError("classifications missing")
    durable_classifications = [
        {
            "schema_version": "jcdr_002_source_classification_row.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "reviewed_registry_row_sha256": reviewed_row_sha,
            "attempt_started_sha256": started_sha,
            **row,
        }
        for row in classifications
    ]
    BASE.assert_outcome_blind(durable_classifications)
    BASE._write_new_jsonl(root / "jcdr_002_source_classifications.jsonl", durable_classifications)

    ledgers = enriched.get("signal_ledgers")
    if type(ledgers) is not dict or set(ledgers) != {"TRUE", "FOLLOW_CONTROL"}:
        raise ContractError("matched ledgers missing")
    durable_ledgers: list[dict[str, object]] = []
    for arm in ("TRUE", "FOLLOW_CONTROL"):
        rows = ledgers[arm]
        if type(rows) is not list:
            raise ContractError("ledger arm malformed")
        for row in rows:
            durable_ledgers.append(
                {
                    "schema_version": "jcdr_002_source_ledger_row.v1",
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "reviewed_registry_row_sha256": reviewed_row_sha,
                    "attempt_started_sha256": started_sha,
                    **row,
                }
            )
    BASE.assert_outcome_blind(durable_ledgers)
    BASE._write_new_jsonl(root / "jcdr_002_source_ledger.jsonl", durable_ledgers)

    first_hashes = BASE._existing_artifact_hashes(root)
    stage0 = enriched.get("stage0")
    verdict = stage0.get("verdict") if type(stage0) is dict else None
    if verdict == BASE.STAGE0_PASS:
        terminal_status = "PASS_SOURCE_FEASIBILITY"
    elif verdict == BASE.STAGE0_FAIL:
        terminal_status = "SOURCE_FAIL_NO_ECONOMICS_AUTHORITY"
    else:
        raise ContractError("invalid Stage-0 verdict")
    receipt = {
        "schema_version": "jcdr_002_source_feasibility_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha,
        "status": "NON_TERMINAL_SOURCE_RESULT_AWAITING_ATTEMPT_TERMINAL",
        "stage0_verdict": verdict,
        "terminal_is_sole_authoritative_completion": True,
        "artifact_hashes": first_hashes,
        "source_only_counters": BASE._executed_source_only_counters(),
        "sealed_permissions": BASE._sealed_permissions(),
    }
    BASE.assert_outcome_blind(receipt)
    BASE._write_new_canonical(root / "source_feasibility_receipt.json", receipt)
    terminal = {
        "schema_version": "jcdr_002_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha,
        "status": terminal_status,
        "stage0_verdict": verdict,
        "artifact_hashes": BASE._existing_artifact_hashes(root),
        "source_only_counters": BASE._executed_source_only_counters(),
        "sealed_permissions": BASE._sealed_permissions(),
        "sole_authoritative_completion": True,
    }
    BASE.assert_outcome_blind(terminal)
    BASE._write_new_canonical(root / "attempt_terminal.json", terminal)
    return enriched


def _persist_engineering_failure(root: Path, reviewed_row_sha: str, error: Exception) -> None:
    terminal = root / "attempt_terminal.json"
    if terminal.exists():
        return
    value = {
        "schema_version": "jcdr_002_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "reviewed_registry_row_sha256": reviewed_row_sha,
        "status": "ENGINEERING_INVALID_NO_MARKET_VERDICT",
        "reason": {"type": type(error).__name__, "message": str(error)[:1000]},
        "artifact_hashes": BASE._existing_artifact_hashes(root),
        "source_only_counters": BASE._executed_source_only_counters(),
        "sealed_permissions": BASE._sealed_permissions(),
        "sole_authoritative_completion": True,
    }
    BASE.assert_outcome_blind(value)
    BASE._write_new_canonical(terminal, value)


def execute_probe(*, workspace_root: Path, run_switch: bool) -> dict[str, object]:
    if run_switch is not True:
        raise ContractError("probe is disarmed; --execute-probe required")
    if not isinstance(REVIEWED_REGISTRY_ROW_SHA256, str) or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise ContractError("probe is disarmed; reviewed registry SHA absent")

    workspace = Path(workspace_root).absolute()
    builder_payload = BASE.stable_read_regular(workspace / BUILDER_REL, workspace)
    test_payload = BASE.stable_read_regular(workspace / TEST_REL, workspace)
    plan_payload = BASE.stable_read_regular(workspace / PLAN_REL, workspace)
    base_payload = BASE.stable_read_regular(workspace / BASE_REL, workspace)
    review_payload = BASE.stable_read_regular(workspace / REVIEW_REL, workspace)
    if BASE.sha256_bytes(plan_payload) != PLAN_SHA256:
        raise ContractError("frozen plan SHA mismatch")
    if BASE.sha256_bytes(base_payload) != BASE_SHA256:
        raise ContractError("reviewed JCDR001 base SHA mismatch")

    registry_payload = BASE.stable_read_regular(workspace / REGISTRY_REL, workspace)
    validator_payload = BASE.stable_read_regular(workspace / REGISTRY_VALIDATOR_REL, workspace)
    schema_payload = BASE.stable_read_regular(workspace / REGISTRY_SCHEMA_REL, workspace)
    BASE.validate_registry_snapshot(
        registry_payload=registry_payload,
        validator_payload=validator_payload,
        schema_payload=schema_payload,
        validator_path=workspace / REGISTRY_VALIDATOR_REL,
    )
    _, reviewed_row_sha = _validate_authority(
        registry_payload,
        builder_payload=builder_payload,
        test_payload=test_payload,
        review_payload=review_payload,
    )
    root = _mkdir_evidence_root(workspace, reviewed_row_sha)
    try:
        entries = BASE.validate_public_metadata(
            receipt_payload=BASE.stable_read_regular(workspace / BASE.M1_RECEIPT_REL, workspace),
            manifest_payload=BASE.stable_read_regular(workspace / BASE.M1_MANIFEST_REL, workspace),
            expected_receipt_sha256=BASE.M1_RECEIPT_SHA256,
            expected_manifest_sha256=BASE.M1_MANIFEST_SHA256,
        )
        m1_rows = BASE._load_public_rows(workspace=workspace, entries=entries)
        report = scan_source(m1_rows)
        return _persist_success(root, report, reviewed_row_sha)
    except Exception as exc:
        _persist_engineering_failure(root, reviewed_row_sha, exc)
        raise


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--execute-probe", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = execute_probe(workspace_root=args.workspace_root, run_switch=args.execute_probe)
    print(BASE.canonical_json(report).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
