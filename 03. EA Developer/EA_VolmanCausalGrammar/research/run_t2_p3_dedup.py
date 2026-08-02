"""Run frozen T2/P3 D7 and D8 identity comparisons without market outcomes.

The runner reads only completed bar fields, prior identity records and bound
provenance.  It never reads excursions, trades, fills, PnL or reports, and it
never grants EA build or economic authority.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

from t2_dedup_mirrors import (
    BOUND_ECRS_NEWS_SOURCE,
    BOUND_D7_STAGE0_FIRST_UTC,
    BOUND_D7_STAGE0_LAST_UTC,
    BOUND_D7_STAGE0_RECORD_COUNT,
    CONTRACT_SHA256,
    ECRS_IDENTITY_FIELDS,
    NORMALIZED_OVERLAP_FIELDS,
    SCC_CONTROL_FIELDS,
    EcrsBar,
    IdentityContractError,
    SccPathBar,
    assert_full_ledger_manifest,
    compare_d7_primary_full_ledgers,
    compare_full_ledgers,
    emit_ecrs_v1_identities,
    emit_scc_challenger_identities,
    emit_scc_control_identities,
    emit_t2_pbp_like_identities,
    identity_ledger_sha256,
    identity_time_range,
    load_bound_news_calendar,
    load_contract,
    reject_outcome_fields,
    sha256_file,
    verify_contract_bindings,
    verify_sha256,
)
from t2_grammar_reference import (
    PRODUCER_SPEC_SHA256,
    Bar,
    BrokerSchedule,
    emit_t2_d7_structural_identities,
    verify_producer_spec,
)


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STAGE0_BARS_PATH = (
    REPO_ROOT
    / "03. EA Developer/EA_ECRS_CompressionReleaseScalper/research/preflight/stage0_bars_m5.parquet"
)
STAGE0_BARS_SHA256 = "A2DDF0D423D188B7BA708ECF4386180853867982123C38418D43A2CE89053532"
SCHEDULE_PATH = HERE / "t2_d7_eurusd_schedule_v1.json"
SCHEDULE_SHA256 = "4174A31D8839761A5FE64A9DDD0C3A5A7088A9B44552A5738A3EF070B23F2418"
EXECUTION_FREEZE_PATH = (
    REPO_ROOT
    / "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_EXECUTION_FREEZE_V1.json"
)
EXECUTION_FREEZE_SCHEMA = "t2_p3_execution_freeze.v1"
SCC_CONTROL_PATH = (
    REPO_ROOT
    / "03. EA Developer/EA_SweepCascadeContinuation/research/evidence/"
    "HYP-SCC-EURUSD-M5-001_STAGE0/stage0_control_breaks.csv"
)
SCC_CONTROL_SHA256 = "CF8002A8FDF617A3E8A216C65DEB6F8A0004B3B8DA16BCD1093A2B505CE50441"
SCC_CHALLENGER_PATH = (
    REPO_ROOT
    / "03. EA Developer/EA_SweepCascadeContinuation/research/evidence/"
    "HYP-SCC-EURUSD-M5-001_STAGE0/stage0_scc_candidates.csv"
)
SCC_CHALLENGER_SHA256 = "86493403CBFEA636E845AD4127FB96876D58DE90DCC608C017F4CF8C37B66F63"
EURUSD_TICK_SIZE = 0.00001
REQUIRED_BAR_FIELDS = {
    "time_utc",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "spread",
    "minute_count",
}

EXECUTION_FREEZE_BINDING_PATHS = {
    "p3_contract": "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P3_DEDUP_CONTRACT_V2.json",
    "p0_charter": "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P0_CHARTER.json",
    "p2_formal_spec": "04. Memory/research/PRO_TRADER_REPLACEMENT_E02_T2_P2_FORMAL_SPEC.md",
    "ecrs_v1_reference": "03. EA Developer/EA_ECRS_CompressionReleaseScalper/research/preflight/stage0_scan.py",
    "ecrs_v2_diagnostic_only": "03. EA Developer/EA_ECRS_CompressionReleaseScalper/research/preflight/stage0_scan_v2.py",
    "indicator_reference": "02. AlphaFactory/tools/research/indicators.py",
    "ecrs_news_csv": "02. AlphaFactory/data/forexfactory/EURUSD/news_events/forexfactory_high_impact_eurusd_2019_2022.csv",
    "ecrs_news_manifest": "02. AlphaFactory/data/forexfactory/EURUSD/news_events/manifest.json",
    "scc_reference": "03. EA Developer/EA_SweepCascadeContinuation/research/scc_stage0_probe.py",
    "scc_probe_plan": "03. EA Developer/EA_SweepCascadeContinuation/research/HYP-SCC-EURUSD-M5-001_PROBE_PLAN.md",
    "stage0_bars": "03. EA Developer/EA_ECRS_CompressionReleaseScalper/research/preflight/stage0_bars_m5.parquet",
    "scc_control_csv": "03. EA Developer/EA_SweepCascadeContinuation/research/evidence/HYP-SCC-EURUSD-M5-001_STAGE0/stage0_control_breaks.csv",
    "scc_challenger_csv": "03. EA Developer/EA_SweepCascadeContinuation/research/evidence/HYP-SCC-EURUSD-M5-001_STAGE0/stage0_scc_candidates.csv",
    "runner": "03. EA Developer/EA_VolmanCausalGrammar/research/run_t2_p3_dedup.py",
    "grammar": "03. EA Developer/EA_VolmanCausalGrammar/research/t2_grammar_reference.py",
    "dedup": "03. EA Developer/EA_VolmanCausalGrammar/research/t2_dedup_mirrors.py",
    "schedule": "03. EA Developer/EA_VolmanCausalGrammar/research/t2_d7_eurusd_schedule_v1.json",
    "grammar_tests": "03. EA Developer/EA_VolmanCausalGrammar/research/test_t2_grammar_reference.py",
    "dedup_tests": "03. EA Developer/EA_VolmanCausalGrammar/research/test_t2_dedup_mirrors.py",
}


def verify_execution_freeze(
    manifest_path: Path = EXECUTION_FREEZE_PATH,
    *,
    require_committed: bool = True,
) -> dict[str, Any]:
    """Verify the independent pre-exposure seal and every file it binds."""
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    exact_fields = {
        "schema_version",
        "campaign",
        "generation",
        "phase",
        "status",
        "authority",
        "frozen_at_utc",
        "real_t2_identity_count_exposed",
        "output_directory",
        "test_gate",
        "prior_scc_replay_gate",
        "bindings",
        "prohibitions",
    }
    if set(document) != exact_fields:
        raise IdentityContractError("execution freeze requires the exact top-level schema")
    if (
        document["schema_version"] != EXECUTION_FREEZE_SCHEMA
        or document["campaign"] != "PRO_TRADER_REPLACEMENT"
        or document["generation"] != "T2"
        or document["phase"] != "P3_OUTCOME_BLIND_DEDUP"
        or document["status"] != "FROZEN_PRE_REAL_T2_IDENTITY_COUNT"
        or document["authority"] != "P3_IDENTITY_ONLY_NO_BUILD_NO_ECONOMICS"
        or document["real_t2_identity_count_exposed"] is not False
    ):
        raise IdentityContractError("execution freeze status/authority mismatch")
    try:
        frozen_at = datetime.fromisoformat(document["frozen_at_utc"].replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise IdentityContractError("execution freeze timestamp is invalid") from exc
    if frozen_at.tzinfo is None:
        raise IdentityContractError("execution freeze timestamp must be timezone-aware")
    if frozen_at.astimezone(timezone.utc) > datetime.now(timezone.utc):
        raise IdentityContractError("execution freeze timestamp is in the future")
    if document["output_directory"] != (
        "03. EA Developer/EA_VolmanCausalGrammar/research/evidence/T2_P3_DEDUP_V1"
    ):
        raise IdentityContractError("execution freeze output directory mismatch")
    if document["test_gate"] != {
        "command": "python -m pytest -q 03. EA Developer/EA_VolmanCausalGrammar",
        "expected_passed": 49,
    }:
        raise IdentityContractError("execution freeze test gate mismatch")
    if document["prior_scc_replay_gate"] != {
        "authority": "PRIOR_SCC_IDENTITY_REPLAY_ONLY_NO_T2_COUNT",
        "source_rows": BOUND_D7_STAGE0_RECORD_COUNT,
        "control_records": 1242,
        "challenger_records": 286,
    }:
        raise IdentityContractError("execution freeze prior SCC replay gate mismatch")
    prohibitions = document["prohibitions"]
    if not isinstance(prohibitions, list) or set(prohibitions) != {
        "NO_MARKET_OUTCOMES_OR_PNL",
        "NO_THRESHOLD_OR_EVENT_KEY_CHANGES_AFTER_EXPOSURE",
        "NO_EA_BUILD_AUTHORITY",
        "NO_ECONOMIC_AUTHORITY",
        "NO_OVERWRITE_OF_RESULT_PACKET",
    }:
        raise IdentityContractError("execution freeze prohibitions mismatch")

    bindings = document["bindings"]
    if not isinstance(bindings, dict) or set(bindings) != set(EXECUTION_FREEZE_BINDING_PATHS):
        raise IdentityContractError("execution freeze binding set mismatch")
    verified: dict[str, str] = {}
    for name, relative_path in EXECUTION_FREEZE_BINDING_PATHS.items():
        binding = bindings[name]
        if not isinstance(binding, dict) or set(binding) != {"path", "sha256", "role"}:
            raise IdentityContractError(f"execution freeze binding schema mismatch: {name}")
        if binding["path"] != relative_path:
            raise IdentityContractError(f"execution freeze path mismatch: {name}")
        if not isinstance(binding["role"], str) or not binding["role"]:
            raise IdentityContractError(f"execution freeze role is missing: {name}")
        expected_sha = binding["sha256"]
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9A-F]{64}", expected_sha):
            raise IdentityContractError(f"execution freeze SHA is invalid: {name}")
        verified[name] = verify_sha256(REPO_ROOT / relative_path, expected_sha)

    git_head = None
    if require_committed:
        try:
            manifest_relative = str(manifest_path.relative_to(REPO_ROOT)).replace("\\", "/")
        except ValueError as exc:
            raise IdentityContractError("committed execution freeze must live inside the repository") from exc
        tracked_paths = [manifest_relative, *EXECUTION_FREEZE_BINDING_PATHS.values()]
        git_head = _require_committed_clean_freeze(tracked_paths)
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "git_head": git_head,
        "bindings": verified,
    }


def _require_committed_clean_freeze(relative_paths: Sequence[str]) -> str:
    head = _git_text("rev-parse", "HEAD")
    for relative_path in relative_paths:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative_path],
            cwd=REPO_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if tracked.returncode != 0:
            raise IdentityContractError(f"execution freeze path is not committed: {relative_path}")
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *relative_paths],
        cwd=REPO_ROOT,
        check=False,
    )
    if dirty.returncode != 0:
        raise IdentityContractError("execution freeze paths differ from committed HEAD")
    return head


def _git_text(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise IdentityContractError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def verify_execution_bindings(*, require_committed: bool = True) -> dict[str, Any]:
    execution_freeze = verify_execution_freeze(require_committed=require_committed)
    contract = load_contract()
    verified = verify_contract_bindings(contract, root=REPO_ROOT)
    verified["p2_runtime"] = verify_producer_spec()
    verified["stage0_bars"] = verify_sha256(STAGE0_BARS_PATH, STAGE0_BARS_SHA256)
    verified["d7_schedule"] = verify_sha256(SCHEDULE_PATH, SCHEDULE_SHA256)
    verified["scc_control_csv"] = verify_sha256(SCC_CONTROL_PATH, SCC_CONTROL_SHA256)
    verified["scc_challenger_csv"] = verify_sha256(
        SCC_CHALLENGER_PATH,
        SCC_CHALLENGER_SHA256,
    )
    verified["execution_freeze_manifest"] = execution_freeze["manifest_sha256"]
    verified["execution_freeze_git_head"] = execution_freeze["git_head"]
    return verified


def load_d7_schedule() -> BrokerSchedule:
    payload = SCHEDULE_PATH.read_bytes()
    verify_sha256(SCHEDULE_PATH, SCHEDULE_SHA256)
    document = json.loads(payload.decode("utf-8"))
    required = {
        "schema_version",
        "authority",
        "symbol",
        "timeframe",
        "bar_clock",
        "source_clock",
        "weekend_coverage_only",
        "scheduled_closed_indices",
        "symbol_remap_indices",
        "unlisted_non_300_second_intervals",
        "notes",
    }
    if set(document) != required:
        raise IdentityContractError("D7 schedule requires the exact frozen schema")
    if (
        document["symbol"] != "EURUSD"
        or document["timeframe"] != "M5"
        or document["bar_clock"] != "UTC"
        or document["weekend_coverage_only"] is not True
        or document["unlisted_non_300_second_intervals"]
        != "UNEXPECTED_GAP_RESET_WARMUP_50"
    ):
        raise IdentityContractError("D7 schedule scope/policy mismatch")
    scheduled = _nonnegative_index_set(document["scheduled_closed_indices"], "scheduled")
    remaps = _nonnegative_index_set(document["symbol_remap_indices"], "remap")
    return BrokerSchedule.from_bytes(
        "EURUSD",
        "UTC",
        payload,
        scheduled_closed_indices=scheduled,
        weekend_coverage_only=True,
        remap_indices=remaps,
    )


def _nonnegative_index_set(values: Any, name: str) -> frozenset[int]:
    if not isinstance(values, list) or any(type(value) is not int or value < 0 for value in values):
        raise IdentityContractError(f"D7 schedule {name} indices are invalid")
    if len(values) != len(set(values)):
        raise IdentityContractError(f"D7 schedule {name} indices contain duplicates")
    return frozenset(values)


def load_bound_stage0_bars() -> tuple[list[Bar], list[EcrsBar], list[SccPathBar], dict[str, Any]]:
    verify_sha256(STAGE0_BARS_PATH, STAGE0_BARS_SHA256)
    frame = pd.read_parquet(STAGE0_BARS_PATH)
    reject_outcome_fields({str(column): None for column in frame.columns})
    missing = sorted(REQUIRED_BAR_FIELDS - set(frame.columns))
    if missing:
        raise IdentityContractError(f"bound stage0 bars missing required fields: {missing}")
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="raise")
    if times.isna().any() or not times.is_monotonic_increasing or times.duplicated().any():
        raise IdentityContractError("bound stage0 UTC clock is null, duplicate or nonmonotonic")
    if times.empty:
        raise IdentityContractError("bound stage0 bar source is empty")
    if times.iloc[-1] >= pd.Timestamp("2023-01-01", tz="UTC"):
        raise IdentityContractError("bound stage0 source crossed the sealed 2023 holdout")
    if times.iloc[0] > pd.Timestamp("2018-12-31", tz="UTC"):
        raise IdentityContractError("bound stage0 source lacks pre-2019 warmup history")
    if times.iloc[-1] < pd.Timestamp("2022-12-30", tz="UTC"):
        raise IdentityContractError("bound stage0 source does not cover the frozen 2019-2022 window")

    numeric = frame[["open", "high", "low", "close", "tick_volume", "spread", "minute_count"]].apply(
        pd.to_numeric,
        errors="coerce",
    )
    if numeric.isna().any().any():
        raise IdentityContractError("bound stage0 source contains nonnumeric required fields")
    frame = frame.copy()
    frame["time_utc"] = times
    for column in numeric.columns:
        frame[column] = numeric[column]

    structural: list[Bar] = []
    ecrs: list[EcrsBar] = []
    scc_path: list[SccPathBar] = []
    for row in frame[list(REQUIRED_BAR_FIELDS)].itertuples(index=False):
        when = row.time_utc.to_pydatetime().astimezone(timezone.utc)
        structural.append(Bar(when, row.open, row.high, row.low, row.close))
        ecrs.append(
            EcrsBar(
                when,
                row.open,
                row.high,
                row.low,
                row.close,
                row.tick_volume,
                row.spread,
            )
        )
        if when >= datetime(2019, 1, 1, tzinfo=timezone.utc):
            scc_path.append(
                SccPathBar(
                    when,
                    row.high,
                    row.low,
                    row.close,
                    complete=float(row.minute_count) == 5.0,
                )
            )
    metadata = {
        "path": str(STAGE0_BARS_PATH),
        "sha256": STAGE0_BARS_SHA256,
        "rows": len(frame),
        "first_utc": _utc_text(structural[0].utc_open),
        "last_utc": _utc_text(structural[-1].utc_open),
        "columns_read": sorted(REQUIRED_BAR_FIELDS),
    }
    return structural, ecrs, scc_path, metadata


def _load_scc_records(path: Path, expected_sha: str, *, challenger: bool) -> list[dict[str, Any]]:
    verify_sha256(path, expected_sha)
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            record: dict[str, Any] = {
                "symbol": "EURUSD",
                "timeframe": "M5",
                "pivot_side": row["pivot_side"],
                "pivot_index": int(row["pivot_index"]),
                "pivot_confirm_time_utc": row["pivot_confirm_time_utc"],
                "pivot_price": float(row["pivot_price"]),
                "break_time_utc": row["break_time_utc"],
                "direction": row["direction"],
                "tick_size": EURUSD_TICK_SIZE,
            }
            if challenger:
                record.update(
                    {
                        "hold_time_utc": row["hold_time_utc"],
                        "retest_time_utc": row["retest_time_utc"],
                        "passage_lag": int(row["passage_lag"]),
                    }
                )
            records.append(record)
    if not records:
        raise IdentityContractError(f"bound SCC source is empty: {path}")
    return records


def _manifest(
    *,
    source: str,
    producer: str,
    population_kind: str,
    records: Sequence[Mapping[str, Any]],
    source_sha256: str,
    producer_sha256: str,
    source_record_count: int,
    source_first_utc: str,
    source_last_utc: str,
    news_calendar_source: str = "not_applicable",
    fatal_gate_kind: str = "NONE",
) -> dict[str, Any]:
    identity_first, identity_last = identity_time_range(records)
    manifest = {
        "source": source,
        "producer": producer,
        "population_kind": population_kind,
        "complete_population": True,
        "sampled_casebook": False,
        "contract_sha256": CONTRACT_SHA256,
        "record_count": len(records),
        "news_calendar_source": news_calendar_source,
        "fatal_gate_kind": fatal_gate_kind,
        "ledger_sha256": identity_ledger_sha256(records),
        "source_sha256": source_sha256,
        "producer_sha256": producer_sha256,
        "source_record_count": source_record_count,
        "source_first_utc": source_first_utc,
        "source_last_utc": source_last_utc,
        "identity_first_utc": identity_first,
        "identity_last_utc": identity_last,
        "generation_mode": "BOUND_FULL_REPLAY",
    }
    assert_full_ledger_manifest(manifest, records=records)
    return manifest


def run_identity_comparisons() -> dict[str, Any]:
    bindings = verify_execution_bindings()
    schedule = load_d7_schedule()
    structural_bars, ecrs_bars, scc_path, data_metadata = load_bound_stage0_bars()
    calendar = load_bound_news_calendar()

    # Validate the already-known prior SCC surface before exposing any new T2
    # identity count.  A broken prior binding must fail this run pre-exposure.
    scc_control_records = _load_scc_records(
        SCC_CONTROL_PATH,
        SCC_CONTROL_SHA256,
        challenger=False,
    )
    scc_challenger_records = _load_scc_records(
        SCC_CHALLENGER_PATH,
        SCC_CHALLENGER_SHA256,
        challenger=True,
    )
    scc_control = emit_scc_control_identities(
        scc_control_records,
        source_bars=scc_path,
    )
    scc_challenger = emit_scc_challenger_identities(
        scc_challenger_records,
        source_bars=scc_path,
    )
    assert_scc_challenger_strict_subset(scc_control, scc_challenger)

    t2_result = emit_t2_d7_structural_identities(
        structural_bars,
        symbol="EURUSD",
        tick=EURUSD_TICK_SIZE,
        schedule=schedule,
    )
    t2_events = list(t2_result.events)
    ecrs_events = emit_ecrs_v1_identities(
        ecrs_bars,
        symbol="EURUSD",
        news_calendar=calendar,
    )
    t2_manifest = _manifest(
        source="bound_stage0_bars_m5_full",
        producer="t2_grammar_reference.emit_t2_d7_structural_identities",
        population_kind="T2_STRUCTURAL_A0_A3",
        records=t2_events,
        source_sha256=STAGE0_BARS_SHA256,
        producer_sha256=sha256_file(HERE / "t2_grammar_reference.py"),
        source_record_count=data_metadata["rows"],
        source_first_utc=data_metadata["first_utc"],
        source_last_utc=data_metadata["last_utc"],
    )
    ecrs_manifest = _manifest(
        source="bound_stage0_bars_m5_full",
        producer="t2_dedup_mirrors.emit_ecrs_v1_identities",
        population_kind="D7_ECRS_V1_EXACT",
        records=ecrs_events,
        source_sha256=STAGE0_BARS_SHA256,
        producer_sha256=sha256_file(HERE / "t2_dedup_mirrors.py"),
        source_record_count=data_metadata["rows"],
        source_first_utc=data_metadata["first_utc"],
        source_last_utc=data_metadata["last_utc"],
        news_calendar_source=BOUND_ECRS_NEWS_SOURCE,
        fatal_gate_kind="D7_ECRS_PRIMARY",
    )
    d7 = compare_d7_primary_full_ledgers(
        t2_events,
        ecrs_events,
        left_manifest=t2_manifest,
        right_manifest=ecrs_manifest,
    )

    pbp_events = emit_t2_pbp_like_identities(t2_result.pbp_audits)
    pbp_break = [event for event in pbp_events if event["subset"] == "PBP_BREAK_WINDOW"]
    pbp_contact = [event for event in pbp_events if event["subset"] == "PBP_TOMBSTONE_CONTACT"]
    d8_break, d8_break_t2_manifest, d8_break_scc_manifest = _compare_d8(
        pbp_break,
        scc_control,
        "T2_PBP_BREAK_WINDOW",
        "SCC_CONTROL_BREAK",
        "T2_HARD_PBP_BREAK_EXCLUSION_ONLY",
        "SCC_CONFIRMED_PIVOT_BREAK_ONLY",
        SCC_CONTROL_SHA256,
    )
    d8_contact, d8_contact_t2_manifest, d8_contact_scc_manifest = _compare_d8(
        pbp_contact,
        scc_challenger,
        "T2_PBP_TOMBSTONE_CONTACT",
        "SCC_CHALLENGER_RETEST",
        "T2_BARRIER_TOMBSTONE_CONTACT_ONLY",
        "SCC_FIRST_PASSAGE_RETEST_ONLY",
        SCC_CHALLENGER_SHA256,
    )

    d7_gate = (
        "PASS_D7_JACCARD_NOT_ABOVE_0_50"
        if d7.jaccard <= 0.50
        else "BLOCK_D7_CAUSAL_RESIDUAL_REVIEW_REQUIRED"
    )
    return {
        "schema_version": "t2_p3_dedup_result.v1",
        "authority": "P3_IDENTITY_ONLY_NO_BUILD_NO_ECONOMICS",
        "created_at_utc": _utc_text(datetime.now(timezone.utc)),
        "contract_sha256": CONTRACT_SHA256,
        "producer_spec_sha256": PRODUCER_SPEC_SHA256,
        "runner_sha256": sha256_file(Path(__file__)),
        "grammar_sha256": sha256_file(HERE / "t2_grammar_reference.py"),
        "dedup_sha256": sha256_file(HERE / "t2_dedup_mirrors.py"),
        "bindings": bindings,
        "data": data_metadata,
        "schedule_sha256": schedule.schedule_sha256,
        "t2_stats": t2_result.stats,
        "d7_gate": d7_gate,
        "d7": asdict(d7),
        "d8_break": asdict(d8_break),
        "d8_contact": asdict(d8_contact),
        "build_authorized": False,
        "economic_authority": "NONE",
        "artifacts": {
            "t2_events": t2_events,
            "t2_rejects": [asdict(value) for value in t2_result.rejects],
            "t2_pbp_audits": [asdict(value) for value in t2_result.pbp_audits],
            "ecrs_events": ecrs_events,
            "pbp_events": pbp_events,
            "pbp_break_events": pbp_break,
            "pbp_contact_events": pbp_contact,
            "scc_control": scc_control,
            "scc_challenger": scc_challenger,
            "t2_manifest": t2_manifest,
            "ecrs_manifest": ecrs_manifest,
            "d8_break_t2_manifest": d8_break_t2_manifest,
            "d8_break_scc_manifest": d8_break_scc_manifest,
            "d8_contact_t2_manifest": d8_contact_t2_manifest,
            "d8_contact_scc_manifest": d8_contact_scc_manifest,
        },
    }


def verify_prior_scc_replay() -> dict[str, Any]:
    """Replay only the already-known SCC source; do not emit any new T2 count."""
    bindings = verify_execution_bindings()
    _structural, _ecrs, scc_path, metadata = load_bound_stage0_bars()
    control_records = _load_scc_records(
        SCC_CONTROL_PATH,
        SCC_CONTROL_SHA256,
        challenger=False,
    )
    challenger_records = _load_scc_records(
        SCC_CHALLENGER_PATH,
        SCC_CHALLENGER_SHA256,
        challenger=True,
    )
    control = emit_scc_control_identities(control_records, source_bars=scc_path)
    challenger = emit_scc_challenger_identities(
        challenger_records,
        source_bars=scc_path,
    )
    assert_scc_challenger_strict_subset(control, challenger)
    return {
        "authority": "PRIOR_SCC_IDENTITY_REPLAY_ONLY_NO_T2_COUNT",
        "bindings": bindings,
        "source_rows": metadata["rows"],
        "scc_control_records": len(control),
        "scc_challenger_records": len(challenger),
        "challenger_strict_subset_of_control": True,
    }


def assert_scc_challenger_strict_subset(
    control: Sequence[Mapping[str, Any]],
    challenger: Sequence[Mapping[str, Any]],
) -> None:
    """Enforce the frozen SCC treatment-origin subset invariant."""
    control_keys = {
        tuple(record[field] for field in SCC_CONTROL_FIELDS)
        for record in control
    }
    challenger_keys = {
        tuple(record[field] for field in SCC_CONTROL_FIELDS)
        for record in challenger
    }
    if not challenger_keys < control_keys:
        missing = sorted(challenger_keys - control_keys)
        relation = "equal" if challenger_keys == control_keys else "not_subset"
        raise IdentityContractError(
            "SCC challenger origins must be a strict subset of control "
            f"relation={relation} missing_count={len(missing)}"
        )


def _compare_d8(
    t2: Sequence[Mapping[str, Any]],
    scc: Sequence[Mapping[str, Any]],
    t2_kind: str,
    scc_kind: str,
    t2_reason: str,
    scc_reason: str,
    scc_source_sha256: str,
):
    t2_source_first = BOUND_D7_STAGE0_FIRST_UTC
    t2_source_last = BOUND_D7_STAGE0_LAST_UTC
    scc_first, scc_last = identity_time_range(scc)
    left_manifest = _manifest(
        source="t2_complete_pbp_audit_ledger",
        producer="t2_dedup_mirrors.emit_t2_pbp_like_identities",
        population_kind=t2_kind,
        records=t2,
        source_sha256=STAGE0_BARS_SHA256,
        producer_sha256=sha256_file(HERE / "t2_dedup_mirrors.py"),
        source_record_count=BOUND_D7_STAGE0_RECORD_COUNT,
        source_first_utc=t2_source_first,
        source_last_utc=t2_source_last,
    )
    right_manifest = _manifest(
        source="bound_scc_stage0_complete_identity_ledger",
        producer="t2_dedup_mirrors.scc_identity_mirror",
        population_kind=scc_kind,
        records=scc,
        source_sha256=scc_source_sha256,
        producer_sha256=sha256_file(HERE / "t2_dedup_mirrors.py"),
        source_record_count=len(scc),
        source_first_utc=scc_first,
        source_last_utc=scc_last,
    )
    comparison = compare_full_ledgers(
        t2,
        scc,
        key_fields=NORMALIZED_OVERLAP_FIELDS,
        left_manifest=left_manifest,
        right_manifest=right_manifest,
        allowed_fields=(set(t2[0]) if t2 else set()) | (set(scc[0]) if scc else set()),
        left_only_reason_code=t2_reason,
        right_only_reason_code=scc_reason,
    )
    return comparison, left_manifest, right_manifest


def write_result_packet(result: Mapping[str, Any], output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise IdentityContractError(f"refusing to overwrite nonempty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = dict(result["artifacts"])
    assert_full_ledger_manifest(
        artifacts["t2_manifest"],
        records=artifacts["t2_events"],
    )
    assert_full_ledger_manifest(
        artifacts["ecrs_manifest"],
        records=artifacts["ecrs_events"],
    )
    manifest_ledger_pairs = {
        "d8_break_t2_manifest": "pbp_break_events",
        "d8_break_scc_manifest": "scc_control",
        "d8_contact_t2_manifest": "pbp_contact_events",
        "d8_contact_scc_manifest": "scc_challenger",
    }
    for manifest_key, ledger_key in manifest_ledger_pairs.items():
        assert_full_ledger_manifest(
            artifacts[manifest_key],
            records=artifacts[ledger_key],
        )
    file_map = {
        "t2_events": "t2_structural_full.jsonl",
        "t2_rejects": "t2_reject_full.jsonl",
        "t2_pbp_audits": "t2_pbp_audit_full.jsonl",
        "ecrs_events": "ecrs_v1_full.jsonl",
        "pbp_events": "t2_pbp_identity_full.jsonl",
        "pbp_break_events": "t2_pbp_break_full.jsonl",
        "pbp_contact_events": "t2_pbp_contact_full.jsonl",
        "scc_control": "scc_control_full.jsonl",
        "scc_challenger": "scc_challenger_full.jsonl",
    }
    written: dict[str, dict[str, Any]] = {}
    for key, filename in file_map.items():
        path = output_dir / filename
        _atomic_jsonl(path, artifacts[key])
        written[key] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "records": len(artifacts[key]),
        }
    for key, filename in (
        ("t2_manifest", "t2_manifest.json"),
        ("ecrs_manifest", "ecrs_manifest.json"),
        ("d8_break_t2_manifest", "d8_break_t2_manifest.json"),
        ("d8_break_scc_manifest", "d8_break_scc_manifest.json"),
        ("d8_contact_t2_manifest", "d8_contact_t2_manifest.json"),
        ("d8_contact_scc_manifest", "d8_contact_scc_manifest.json"),
    ):
        path = output_dir / filename
        _atomic_json(path, artifacts[key])
        written[key] = {
            "path": str(path),
            "sha256": sha256_file(path),
            "records": 1,
        }
    public_result = {key: value for key, value in result.items() if key != "artifacts"}
    public_result["written_artifacts"] = written
    _atomic_json(output_dir / "result.json", public_result)
    receipt = {
        "result_path": str(output_dir / "result.json"),
        "result_sha256": sha256_file(output_dir / "result.json"),
        "artifacts": written,
    }
    _atomic_json(output_dir / "receipt.json", receipt)
    return receipt


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_text(path, json.dumps(value, indent=2, sort_keys=True, default=_json_default) + "\n")


def _atomic_jsonl(path: Path, rows: Iterable[Any]) -> None:
    payload = "".join(
        json.dumps(row, sort_keys=True, default=_json_default, separators=(",", ":")) + "\n"
        for row in rows
    )
    _atomic_text(path, payload)


def _atomic_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return _utc_text(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _utc_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Verify every frozen binding without emitting or counting identities.",
    )
    parser.add_argument(
        "--verify-prior-scc",
        action="store_true",
        help="Replay only the bound prior SCC identities; do not scan T2.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.verify_only:
        print(json.dumps(verify_execution_bindings(), indent=2, sort_keys=True))
        return 0
    if args.verify_prior_scc:
        print(json.dumps(verify_prior_scc_replay(), indent=2, sort_keys=True))
        return 0
    if args.output_dir is None:
        raise SystemExit("--output-dir is required unless --verify-only is used")
    result = run_identity_comparisons()
    receipt = write_result_packet(result, args.output_dir.resolve())
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
