#!/usr/bin/env python3
"""Fail-only Q1-2019 GC TBBO/definition/status source-integrity analyzer."""

from __future__ import annotations

import argparse
from array import array
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-GC-OFI-INNOV-XAU-M5-003"
RUN_ID = "GCOFI003-Q1-2019-SOURCE-INTEGRITY-001"
DATASET = "GLBX.MDP3"
START_NS = 1_546_300_800_000_000_000
END_NS = 1_554_076_800_000_000_000
DAY_NS = 86_400_000_000_000
BIN_NS = 300_000_000_000
TICK_RAW = 100_000_000
REPLAY_SESSION_LIMIT = 25
MIN_AB_SHARE = 0.99
BAD_FLAG_MASK = 8 | 4
INSTRUMENT_IDS = (32_257, 14_651, 142_620)
EXPECTED_RAW_SYMBOL = {32_257: "GCG9", 14_651: "GCJ9", 142_620: "GCM9"}

BASE_REL = "03. EA Developer/EA_GCOrderFlowInnovation/research/"
PREREG_REL = BASE_REL + HYPOTHESIS_ID + "_SOURCE_INTEGRITY_PREREG.md"
REVIEW_REL = BASE_REL + HYPOTHESIS_ID + "_GROK_V3_REDTEAM_RECEIPT.md"
TOOL_REL = BASE_REL + "analyze_gc_source_integrity_003.py"
TEST_REL = BASE_REL + "tests/test_analyze_gc_source_integrity_003.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
CONDITION_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-003/GCOFI003-Q1-2019-DATASET-CONDITION-001/"
    "dataset_condition_receipt.json"
)
TBBO_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-001/GCOFI001-Q1-2019-SOURCE-PILOT-001/raw/tbbo.dbn.zst"
)
DEFINITION_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-002/GCOFI002-Q1-2019-REF-SOURCE-001/raw/definition.dbn.zst"
)
STATUS_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    "HYP-GC-OFI-INNOV-XAU-M5-002/GCOFI002-Q1-2019-REF-SOURCE-001/raw/status.dbn.zst"
)
REFERENCE_REL = "04. Memory/research/gc_signed_flow_estimator_reference.py"
REFERENCE_TEST_REL = "04. Memory/research/tests/test_gc_signed_flow_estimator_reference.py"
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/gc_order_flow_innovation/"
    f"{HYPOTHESIS_ID}/{RUN_ID}/source_integrity_result.json"
)

EXPECTED_HASHES = {
    PREREG_REL: "5A604E980542450026F48D622B96F5BA7EA57FD5212913297E8FB2C27F78CE84",
    REVIEW_REL: "158568A54B176029A0B6DA1F83451E73B717BDA83C6E9D7F49004E4DBBA4FC09",
    CONDITION_REL: "03675D70570B3A2429AD259D00C0CFE79FB7E79A82FB8E4143075BA790632972",
    TBBO_REL: "6E0AD7D7893A7475DECAA6C71042139474AAE136BAC77FCBF96584FEB789BAEB",
    DEFINITION_REL: "F3D611000866D8ACB45CB9636307410F91674EDB1B1609B9F4BB867CE5E144CB",
    STATUS_REL: "B20CE73170247CADF96179137D9729EBBC771B3DD831019CFFA2E0951B6D59BE",
    REFERENCE_REL: "48D4ABC930329803AD03587B8EA5C6814A06B89BE7B7AE8CE39CAA444FB29FE2",
    REFERENCE_TEST_REL: "33FE9648545B71CC955C3750E5C6C4A0D03B6B79EBC7339339BA3ED99513725E",
}

EXPECTED_MAPPINGS = {
    "GC.v.0": [
        ("2019-01-01", "2019-02-01", "32257"),
        ("2019-02-01", "2019-03-31", "14651"),
        ("2019-03-31", "2019-04-01", "142620"),
    ]
}


class IntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class StatusEvent:
    recv_ns: int
    event_ns: int
    day: int
    is_trading: str
    is_quoting: str
    trading_event: int
    synthetic_reset: bool = False


@dataclass(frozen=True)
class StatusCheckpoint:
    recv_ns: int
    day: int
    active: bool
    session_id: int | None


@dataclass
class BinState:
    instrument_id: int
    session_id: int
    bin_start_ns: int
    signed_count: int = 0
    first_bid: int = 0
    first_ask: int = 0
    last_bid: int = 0
    last_ask: int = 0
    contains_first_after_reset: bool = False
    start_sign_index: int = -1
    end_sign_index: int = -1


@dataclass
class SessionData:
    instrument_id: int
    session_id: int
    signs: array


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(canonical_json(value) + b"\n")
    tmp.replace(path)


def epoch_day(iso_date: str) -> int:
    return date.fromisoformat(iso_date).toordinal() - date(1970, 1, 1).toordinal()


def iso_day(day: int) -> str:
    return date.fromordinal(day + date(1970, 1, 1).toordinal()).isoformat()


def expected_instrument(day: int) -> int | None:
    if epoch_day("2019-01-01") <= day < epoch_day("2019-02-01"):
        return 32_257
    if epoch_day("2019-02-01") <= day < epoch_day("2019-03-31"):
        return 14_651
    if epoch_day("2019-03-31") <= day < epoch_day("2019-04-01"):
        return 142_620
    return None


def bbo_valid(bid: int, ask: int) -> bool:
    return isinstance(bid, int) and isinstance(ask, int) and bid > 0 and ask > 0 and bid < ask


def share(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        raise IntegrityError("nonpositive coverage denominator")
    return numerator / denominator


def apply_status_value(previous: str | None, update: str) -> str | None:
    if update in ("Y", "N"):
        return update
    if update == "~":
        return previous
    raise IntegrityError(f"unknown status value: {update!r}")


def status_value_from_dbn(value: bool | None) -> str:
    """Restore the DBN TriState wire semantics hidden by the Python bool adapter."""
    if value is None:
        return "~"
    if type(value) is bool:
        return "Y" if value else "N"
    raise IntegrityError(f"unknown DBN status adapter value: {value!r}")


def mapping_tuple(metadata: Any) -> dict[str, list[tuple[str, str, str]]]:
    return {
        str(key): [
            (str(item["start_date"]), str(item["end_date"]), str(item["symbol"]))
            for item in values
        ]
        for key, values in metadata.mappings.items()
    }


def validate_metadata(store: Any, schema: str) -> None:
    metadata = store.metadata
    actual_schema = getattr(metadata.schema, "value", str(metadata.schema)).lower()
    if (
        int(metadata.version) != 3
        or metadata.dataset != DATASET
        or actual_schema != schema
        or int(metadata.start) != START_NS
        or int(metadata.end) != END_NS
    ):
        raise IntegrityError(f"DBN metadata mismatch: {schema}")
    ids = {int(value["symbol"]) for values in metadata.mappings.values() for value in values}
    if not ids.issubset(set(INSTRUMENT_IDS)):
        raise IntegrityError(f"DBN mapping identity mismatch: {schema}")


def load_conditions(path: Path) -> tuple[dict[int, str], list[int]]:
    receipt = json.loads(path.read_text(encoding="ascii"))
    rows = receipt.get("conditions", [])
    conditions: dict[int, str] = {}
    for row in rows:
        day = epoch_day(str(row["date"]))
        condition = str(row["condition"]).lower()
        if day in conditions or condition not in ("available", "degraded"):
            raise IntegrityError("condition tape duplicate/unknown")
        conditions[day] = condition
    degraded = sorted(day for day, condition in conditions.items() if condition == "degraded")
    expected_degraded = [epoch_day(value) for value in ("2019-01-15", "2019-02-22", "2019-03-13", "2019-03-26")]
    if degraded != expected_degraded:
        raise IntegrityError("degraded-date contract mismatch")
    return conditions, degraded


def latest_degraded_before(day: int, degraded: list[int]) -> int | None:
    index = bisect_right(degraded, day) - 1
    return degraded[index] if index >= 0 else None


def load_reference(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("gc_ofi_reference_bound", path)
    if spec is None or spec.loader is None:
        raise IntegrityError("cannot load estimator reference")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_registry(workspace: Path) -> dict[str, str]:
    rows = []
    for raw in (workspace / REGISTRY_REL).read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                rows.append((row, raw + b"\n"))
    if not rows:
        raise IntegrityError("HYP003 absent from registry")
    row, row_bytes = rows[-1]
    validation = row.get("validation", {})
    bindings = {
        "source_integrity_prereg_sha256": sha256_file(workspace / PREREG_REL),
        "grok_v3_review_sha256": sha256_file(workspace / REVIEW_REL),
        "dataset_condition_receipt_sha256": sha256_file(workspace / CONDITION_REL),
        "tbbo_sha256": sha256_file(workspace / TBBO_REL),
        "definition_sha256": sha256_file(workspace / DEFINITION_REL),
        "status_sha256": sha256_file(workspace / STATUS_REL),
        "estimator_sha256": sha256_file(workspace / REFERENCE_REL),
        "estimator_test_sha256": sha256_file(workspace / REFERENCE_TEST_REL),
        "reviewed_analyzer_sha256": sha256_file(workspace / TOOL_REL),
        "reviewed_analyzer_test_sha256": sha256_file(workspace / TEST_REL),
    }
    if (
        row.get("state") != "probe"
        or row.get("verdict") != "AUTHORIZE_Q1_SOURCE_INTEGRITY_READOUT_NO_CADENCE"
        or validation.get("source_integrity_run_authorized") is not True
        or validation.get("candidate_event_predicate_authorized") is not False
    ):
        raise IntegrityError("registry source-readout authority mismatch")
    for key, value in bindings.items():
        if validation.get(key) != value:
            raise IntegrityError(f"registry binding mismatch: {key}")
    for field in (
        "event_cadence_authorized", "xauusd_outcome_authorized", "economics_authorized",
        "mql5_authorized", "mt5_authorized", "optimization_authorized",
        "research_validation_access_authorized", "research_holdout_access_authorized",
        "paper_trading_authorized", "live_trading_authorized", "market_edge_claim_authorized",
    ):
        if validation.get(field) is not False:
            raise IntegrityError(f"forbidden authority open: {field}")
    return {**bindings, "registry_row_sha256": hashlib.sha256(row_bytes).hexdigest().upper()}


def load_definitions(path: Path) -> tuple[dict[int, int], dict[str, Any]]:
    import databento as db

    store = db.DBNStore.from_file(path)
    validate_metadata(store, "definition")
    earliest: dict[int, int] = {}
    records = 0
    conflicts = 0
    for record in store:
        records += 1
        instrument = int(record.instrument_id)
        if instrument not in INSTRUMENT_IDS:
            conflicts += 1
            continue
        earliest[instrument] = min(earliest.get(instrument, int(record.ts_recv)), int(record.ts_recv))
        if (
            str(record.raw_symbol) != EXPECTED_RAW_SYMBOL[instrument]
            or str(record.security_type) != "FUT"
            or str(record.asset) != "GC"
            or str(record.instrument_class) != "F"
            or str(record.currency) != "USD"
            or int(record.min_price_increment) != TICK_RAW
            or int(record.activation) >= int(record.expiration)
        ):
            conflicts += 1
    if records <= 0 or set(earliest) != set(INSTRUMENT_IDS):
        raise IntegrityError("definition identity/coverage missing")
    return earliest, {"records": records, "conflicting_records": conflicts}


def load_status_events(path: Path, conditions: dict[int, str], degraded: list[int]) -> tuple[dict[int, list[StatusCheckpoint]], dict[tuple[int, int], tuple[int, int | None]], dict[str, Any]]:
    import databento as db

    store = db.DBNStore.from_file(path)
    validate_metadata(store, "status")
    raw: dict[int, list[StatusEvent]] = defaultdict(list)
    records = 0
    unknown_condition_rows = 0
    for record in store:
        records += 1
        instrument = int(record.instrument_id)
        if instrument not in INSTRUMENT_IDS:
            raise IntegrityError("status instrument outside allowlist")
        recv_ns = int(record.ts_recv)
        day = recv_ns // DAY_NS
        if day not in conditions:
            unknown_condition_rows += 1
        raw[instrument].append(
            StatusEvent(
                recv_ns=recv_ns,
                event_ns=int(record.ts_event),
                day=day,
                is_trading=status_value_from_dbn(record.is_trading),
                is_quoting=status_value_from_dbn(record.is_quoting),
                trading_event=int(record.trading_event),
            )
        )
    checkpoints: dict[int, list[StatusCheckpoint]] = {}
    bounds: dict[tuple[int, int], tuple[int, int | None]] = {}
    ordering_violations = 0
    active_sessions = 0
    for instrument in INSTRUMENT_IDS:
        events = list(raw[instrument])
        for day in degraded:
            events.append(StatusEvent(day * DAY_NS, day * DAY_NS, day, "~", "~", -1, True))
            events.append(StatusEvent((day + 1) * DAY_NS, (day + 1) * DAY_NS, day + 1, "~", "~", -1, True))
        events.sort(key=lambda item: (item.recv_ns, 0 if item.synthetic_reset else 1, item.event_ns))
        previous_recv = -1
        trading: str | None = None
        quoting: str | None = None
        active = False
        session_id: int | None = None
        next_session = 0
        output: list[StatusCheckpoint] = []
        for event in events:
            if event.recv_ns < previous_recv:
                ordering_violations += 1
            previous_recv = event.recv_ns
            if event.synthetic_reset or conditions.get(event.day) == "degraded":
                if active and session_id is not None:
                    start, _ = bounds[(instrument, session_id)]
                    bounds[(instrument, session_id)] = (start, event.event_ns)
                trading = None
                quoting = None
                active = False
                session_id = None
                output.append(StatusCheckpoint(event.recv_ns, event.day, False, None))
                continue
            trading = apply_status_value(trading, event.is_trading)
            quoting = apply_status_value(quoting, event.is_quoting)
            new_active = trading == "Y" and quoting == "Y"
            change_session = event.trading_event == 2
            if active and session_id is not None and (not new_active or change_session):
                start, _ = bounds[(instrument, session_id)]
                bounds[(instrument, session_id)] = (start, event.event_ns)
                session_id = None
            if new_active and (not active or change_session):
                next_session += 1
                session_id = next_session
                bounds[(instrument, session_id)] = (event.event_ns, None)
                active_sessions += 1
            active = new_active
            output.append(StatusCheckpoint(event.recv_ns, event.day, active, session_id))
        checkpoints[instrument] = output
    return checkpoints, bounds, {
        "records": records,
        "unknown_condition_rows": unknown_condition_rows,
        "ordering_violations": ordering_violations,
        "active_sessions": active_sessions,
    }


def group_summary(groups: dict[str, list[int]]) -> list[dict[str, Any]]:
    output = []
    for key in sorted(groups):
        total_count, ab_count, total_volume, ab_volume = groups[key]
        output.append({
            "key": key,
            "trade_count": total_count,
            "ab_count_share": share(ab_count, total_count),
            "contract_volume": total_volume,
            "ab_volume_share": share(ab_volume, total_volume),
        })
    return output


def bin_is_valid(bin_state: BinState, bounds: dict[tuple[int, int], tuple[int, int | None]]) -> tuple[bool, str]:
    start, end = bounds.get((bin_state.instrument_id, bin_state.session_id), (0, None))
    effective_end = END_NS if end is None else end
    if bin_state.bin_start_ns < start or bin_state.bin_start_ns + BIN_NS > effective_end:
        return False, "status_boundary"
    if bin_state.contains_first_after_reset:
        return False, "first_after_reset"
    if not bbo_valid(bin_state.first_bid, bin_state.first_ask) or not bbo_valid(bin_state.last_bid, bin_state.last_ask):
        return False, "invalid_edge_bbo"
    return True, "valid"


def analyze_tbbo(
    path: Path,
    conditions: dict[int, str],
    degraded: list[int],
    definition_earliest: dict[int, int],
    checkpoints: dict[int, list[StatusCheckpoint]],
    bounds: dict[tuple[int, int], tuple[int, int | None]],
) -> tuple[dict[str, Any], dict[tuple[int, int], SessionData], dict[tuple[int, int, int], BinState], list[str]]:
    import databento as db

    store = db.DBNStore.from_file(path)
    validate_metadata(store, "tbbo")
    if mapping_tuple(store.metadata) != EXPECTED_MAPPINGS:
        raise IntegrityError("continuous mapping mismatch")
    failures: list[str] = []
    cp_index = {instrument: -1 for instrument in INSTRUMENT_IDS}
    cp_current: dict[int, StatusCheckpoint | None] = {instrument: None for instrument in INSTRUMENT_IDS}
    previous_recv = -1
    previous_event_seq: dict[int, tuple[int, int]] = {}
    first_trade_recv: dict[int, int] = {}
    first_signed_seen: set[tuple[int, int]] = set()
    sessions: dict[tuple[int, int], SessionData] = {}
    bins: dict[tuple[int, int, int], BinState] = {}
    groups_date: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    groups_instrument: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    groups_session: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    metrics = defaultdict(int)
    metrics["records_total"] = 0
    for record in store:
        metrics["records_total"] += 1
        recv_ns = int(record.ts_recv)
        day = recv_ns // DAY_NS
        condition = conditions.get(day)
        if condition is None:
            metrics["rows_missing_condition"] += 1
            continue
        if condition != "available":
            metrics["rows_excluded_degraded"] += 1
            metrics["volume_excluded_degraded"] += int(record.size)
            continue
        instrument = int(record.instrument_id)
        metrics["eligible_rows"] += 1
        size = int(record.size)
        metrics["eligible_volume"] += size
        if recv_ns < previous_recv:
            metrics["global_recv_order_violations"] += 1
        previous_recv = recv_ns
        if instrument not in INSTRUMENT_IDS or expected_instrument(day) != instrument:
            metrics["mapping_violations"] += 1
            continue
        first_trade_recv[instrument] = min(first_trade_recv.get(instrument, recv_ns), recv_ns)
        event_seq = (int(record.ts_event), int(record.sequence))
        previous = previous_event_seq.get(instrument)
        if previous is not None:
            if event_seq == previous:
                metrics["duplicate_event_keys"] += 1
            elif event_seq < previous:
                metrics["event_order_violations"] += 1
        previous_event_seq[instrument] = event_seq
        if str(record.action) != "T" or int(record.price) <= 0 or size <= 0:
            metrics["invalid_trade_records"] += 1
        if int(record.flags) & BAD_FLAG_MASK:
            metrics["bad_quality_flag_records"] += 1
        side = str(record.side)
        if side not in ("A", "B", "N"):
            metrics["unknown_side_records"] += 1
            side = "N"
        is_ab = side in ("A", "B")
        if is_ab:
            metrics["ab_rows"] += 1
            metrics["ab_volume"] += size
        else:
            metrics["n_rows"] += 1
            metrics["n_volume"] += size
        for group in (
            groups_date[iso_day(day)],
            groups_instrument[str(instrument)],
        ):
            group[0] += 1
            group[2] += size
            if is_ab:
                group[1] += 1
                group[3] += size
        if not is_ab:
            continue
        cps = checkpoints[instrument]
        index = cp_index[instrument]
        while index + 1 < len(cps) and cps[index + 1].recv_ns <= recv_ns:
            index += 1
        cp_index[instrument] = index
        checkpoint = cps[index] if index >= 0 else None
        cp_current[instrument] = checkpoint
        last_bad_day = latest_degraded_before(day, degraded)
        covered = (
            checkpoint is not None
            and checkpoint.active
            and checkpoint.session_id is not None
            and (last_bad_day is None or checkpoint.day > last_bad_day)
        )
        if not covered:
            metrics["signed_status_uncovered_rows"] += 1
            metrics["signed_status_uncovered_volume"] += size
            continue
        session_id = int(checkpoint.session_id)
        session_key = (instrument, session_id)
        group = groups_session[f"{instrument}:{session_id}"]
        group[0] += 1
        group[1] += 1
        group[2] += size
        group[3] += size
        sign = 1 if side == "B" else -1
        session = sessions.get(session_key)
        if session is None:
            session = SessionData(instrument, session_id, array("b"))
            sessions[session_key] = session
        session.signs.append(sign)
        sign_index = len(session.signs) - 1
        bin_start = (int(record.ts_event) // BIN_NS) * BIN_NS
        bin_key = (instrument, session_id, bin_start)
        level = record.levels[0]
        bid = int(level.bid_px)
        ask = int(level.ask_px)
        state = bins.get(bin_key)
        is_first = session_key not in first_signed_seen
        if state is None:
            state = BinState(
                instrument_id=instrument,
                session_id=session_id,
                bin_start_ns=bin_start,
                signed_count=1,
                first_bid=bid,
                first_ask=ask,
                last_bid=bid,
                last_ask=ask,
                contains_first_after_reset=is_first,
                start_sign_index=sign_index,
                end_sign_index=sign_index,
            )
            bins[bin_key] = state
        else:
            state.signed_count += 1
            state.last_bid = bid
            state.last_ask = ask
            state.end_sign_index = sign_index
            state.contains_first_after_reset = state.contains_first_after_reset or is_first
        first_signed_seen.add(session_key)
    for instrument, first_recv in first_trade_recv.items():
        if definition_earliest.get(instrument, END_NS + 1) > first_recv:
            metrics["definition_after_first_trade"] += 1
    bin_reasons = defaultdict(int)
    for state in bins.values():
        _, reason = bin_is_valid(state, bounds)
        bin_reasons[reason] += 1
    ab_count_share = share(metrics["ab_rows"], metrics["eligible_rows"])
    ab_volume_share = share(metrics["ab_volume"], metrics["eligible_volume"])
    status_count_share = share(metrics["ab_rows"] - metrics["signed_status_uncovered_rows"], metrics["ab_rows"])
    status_volume_share = share(metrics["ab_volume"] - metrics["signed_status_uncovered_volume"], metrics["ab_volume"])
    fatal_fields = (
        "rows_missing_condition", "global_recv_order_violations", "mapping_violations",
        "duplicate_event_keys", "event_order_violations", "invalid_trade_records",
        "bad_quality_flag_records", "unknown_side_records", "signed_status_uncovered_rows",
        "definition_after_first_trade",
    )
    for field in fatal_fields:
        if metrics[field] != 0:
            failures.append(f"{field}={metrics[field]}")
    if ab_count_share < MIN_AB_SHARE:
        failures.append(f"ab_count_share={ab_count_share:.12f}<0.99")
    if ab_volume_share < MIN_AB_SHARE:
        failures.append(f"ab_volume_share={ab_volume_share:.12f}<0.99")
    if bin_reasons["valid"] <= 0:
        failures.append("no_valid_source_bins")
    result = {
        **dict(metrics),
        "ab_count_share": ab_count_share,
        "ab_volume_share": ab_volume_share,
        "signed_status_count_coverage": status_count_share,
        "signed_status_volume_coverage": status_volume_share,
        "bin_counts": dict(sorted(bin_reasons.items())),
        "by_date": group_summary(groups_date),
        "by_instrument": group_summary(groups_instrument),
        "by_session": group_summary(groups_session),
    }
    return result, sessions, bins, failures


def replay_signature(
    reference: Any,
    sessions: dict[tuple[int, int], SessionData],
    bins: dict[tuple[int, int, int], BinState],
    bounds: dict[tuple[int, int], tuple[int, int | None]],
) -> tuple[str, int, int]:
    signature_rows: list[dict[str, Any]] = []
    compared_bins = 0
    compared_sessions = 0
    for instrument in INSTRUMENT_IDS:
        candidates = [
            session for (inst, _), session in sessions.items()
            if inst == instrument and bounds.get((inst, session.session_id), (0, None))[1] is not None
        ]
        candidates.sort(key=lambda item: (bounds[(instrument, item.session_id)][0], item.session_id))
        candidates = candidates[:REPLAY_SESSION_LIMIT]
        completed: list[Any] = []
        transition_counts = {(-1, -1): 0, (-1, 1): 0, (1, -1): 0, (1, 1): 0}
        prior_u: list[float] = []
        for session in candidates:
            signs = list(session.signs)
            independent_available = (
                transition_counts[(-1, -1)] + transition_counts[(-1, 1)] >= 10_000
                and transition_counts[(1, -1)] + transition_counts[(1, 1)] >= 10_000
                and len(prior_u) >= 1_000
            )
            try:
                params = reference.freeze_session_parameters(
                    instrument_id=str(instrument),
                    session_ordinal=session.session_id,
                    completed_sessions=completed,
                )
                reference_available = True
            except reference.EstimatorUnavailable:
                params = None
                reference_available = False
            if independent_available != reference_available:
                raise IntegrityError("reference/incremental availability mismatch")
            valid_u: list[float] = []
            if reference_available and params is not None:
                expected = {}
                for previous in (-1, 1):
                    denominator = transition_counts[(previous, -1)] + transition_counts[(previous, 1)]
                    expected[previous] = (
                        transition_counts[(previous, 1)] - transition_counts[(previous, -1)]
                    ) / denominator
                mean_u = sum(prior_u) / len(prior_u)
                sigma = math.sqrt(sum((value - mean_u) ** 2 for value in prior_u) / len(prior_u))
                for previous in (-1, 1):
                    if not math.isclose(expected[previous], params.expectations[previous], rel_tol=0.0, abs_tol=1e-12):
                        raise IntegrityError("reference expectation mismatch")
                if not math.isclose(sigma, params.sigma, rel_tol=0.0, abs_tol=1e-12):
                    raise IntegrityError("reference sigma mismatch")
                innovations = reference.session_innovations(signs, params.expectations)
                independent_innovations: list[float | None] = [None]
                for index in range(1, len(signs)):
                    independent_innovations.append(signs[index] - expected[signs[index - 1]])
                session_bins = [
                    state for (inst, sid, _), state in bins.items()
                    if inst == instrument and sid == session.session_id
                ]
                session_bins.sort(key=lambda item: item.bin_start_ns)
                for state in session_bins:
                    valid, _ = bin_is_valid(state, bounds)
                    if not valid:
                        continue
                    start = state.start_sign_index
                    end = state.end_sign_index + 1
                    try:
                        u_ref, x_ref = reference.aggregate_complete_bin(signs[start:end], innovations[start:end])
                    except reference.EstimatorUnavailable:
                        continue
                    values = [float(value) for value in independent_innovations[start:end] if value is not None]
                    if len(values) != end - start:
                        continue
                    n = end - start
                    u_ind = sum(values) / math.sqrt(n)
                    x_ind = sum(signs[start:end]) / math.sqrt(n)
                    if not math.isclose(u_ref, u_ind, rel_tol=0.0, abs_tol=1e-12) or not math.isclose(x_ref, x_ind, rel_tol=0.0, abs_tol=1e-12):
                        raise IntegrityError("reference bin aggregation mismatch")
                    r_value = ((state.last_bid + state.last_ask) - (state.first_bid + state.first_ask)) / (2 * TICK_RAW)
                    valid_u.append(u_ref)
                    compared_bins += 1
                    signature_rows.append({
                        "instrument_id": instrument,
                        "session_id": session.session_id,
                        "bin_start_ns": state.bin_start_ns,
                        "u": format(u_ref, ".17g"),
                        "x": format(x_ref, ".17g"),
                        "r": format(r_value, ".17g"),
                        "sigma": format(params.sigma, ".17g"),
                    })
                compared_sessions += 1
            completed.append(
                reference.CompletedSession(
                    instrument_id=str(instrument),
                    session_ordinal=session.session_id,
                    signs=tuple(signs),
                    valid_u_bins=tuple(valid_u),
                )
            )
            prior_u.extend(valid_u)
            for previous, current in zip(signs, signs[1:]):
                transition_counts[(previous, current)] += 1
    digest = hashlib.sha256(canonical_json(signature_rows)).hexdigest().upper()
    return digest, compared_sessions, compared_bins


def execute(workspace: Path) -> Path:
    workspace = workspace.resolve()
    if workspace.drive.upper() != "D:":
        raise IntegrityError("workspace must stay on D:")
    for relative, expected in EXPECTED_HASHES.items():
        path = workspace / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise IntegrityError(f"bound artifact drift: {relative}")
    authority = validate_registry(workspace)
    output = workspace / OUTPUT_REL
    if output.exists():
        raise IntegrityError("same-ID source result already exists")
    conditions, degraded = load_conditions(workspace / CONDITION_REL)
    definition_earliest, definition_metrics = load_definitions(workspace / DEFINITION_REL)
    checkpoints, bounds, status_metrics = load_status_events(workspace / STATUS_REL, conditions, degraded)
    tbbo_metrics, sessions, bins, failures = analyze_tbbo(
        workspace / TBBO_REL, conditions, degraded, definition_earliest, checkpoints, bounds
    )
    if definition_metrics["conflicting_records"]:
        failures.append(f"definition_conflicting_records={definition_metrics['conflicting_records']}")
    if status_metrics["unknown_condition_rows"]:
        failures.append(f"status_unknown_condition_rows={status_metrics['unknown_condition_rows']}")
    if status_metrics["ordering_violations"]:
        failures.append(f"status_ordering_violations={status_metrics['ordering_violations']}")
    replay = {
        "executed": False,
        "signature_first": None,
        "signature_second": None,
        "deterministic_equal": False,
        "reference_equal": False,
        "compared_sessions": 0,
        "compared_bins": 0,
        "tail_predicate_evaluated": False,
        "candidate_event_count_emitted": False,
    }
    if not failures:
        reference = load_reference(workspace / REFERENCE_REL)
        first = replay_signature(reference, sessions, bins, bounds)
        second = replay_signature(reference, sessions, bins, bounds)
        replay.update({
            "executed": True,
            "signature_first": first[0],
            "signature_second": second[0],
            "deterministic_equal": first[0] == second[0],
            "reference_equal": True,
            "compared_sessions": first[1],
            "compared_bins": first[2],
        })
        if first != second or first[1] <= 0 or first[2] <= 0:
            failures.append("deterministic_replay_gate_failed")
    verdict = "PASS_Q1_SOURCE_INTEGRITY_CADENCE_STILL_CLOSED" if not failures else "KILL_SOURCE_INTEGRITY_HYP003"
    result = {
        "schema_version": "gc_order_flow_innovation_source_integrity.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "verdict": verdict,
        "failures": failures,
        "bindings": authority,
        "conditions": {
            "available_dates": sum(value == "available" for value in conditions.values()),
            "degraded_dates": [iso_day(value) for value in degraded],
            "degraded_dates_remain_in_later_calendar_denominator": True,
        },
        "definition": definition_metrics,
        "status": status_metrics,
        "tbbo": tbbo_metrics,
        "replay": replay,
        "candidate_event_predicate_evaluated": False,
        "event_cadence_read": False,
        "xauusd_outcome_read": False,
        "economics_executed": False,
        "mql5_created": False,
        "mt5_launched": False,
        "optimization_executed": False,
        "validation_accessed": False,
        "holdout_accessed": False,
        "paper_trading_authorized": False,
        "live_trading_authorized": False,
        "market_edge_claim_authorized": False,
    }
    write_json_atomic(output, result)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        output = execute(args.workspace)
        result = json.loads(output.read_text(encoding="ascii"))
        print(f"GCOFI003_SOURCE_RESULT verdict={result['verdict']} failures={len(result['failures'])}")
        print(f"RESULT {output}")
        return 0
    except IntegrityError as exc:
        print(f"GCOFI003_SOURCE_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
