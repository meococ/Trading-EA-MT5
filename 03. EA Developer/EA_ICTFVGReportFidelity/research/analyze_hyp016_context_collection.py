#!/usr/bin/env python3
"""Validate HYP-016R1 without opening any economic outcome.

Allowed inputs are the run manifest, RunMeta, HumanContext ledger, and the
LifecycleTrades header/row count. The MT5 report is deliberately never opened.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(r"D:\Trading EA MT5")
HYPOTHESIS_ID = "HYP-ICT-FVG-HIGHRECALL-CONTEXT-COLLECT-EURUSD-M5-016R1"
SOURCE_SHA256 = "8A472364351B9F4C49206F81CD621D9F0FB076BA74E51EE29E0D917C25A2F79E"
NATURAL_STATES = {"EXTERNAL_SWEEP_WITH_ROOM", "INTERNAL_SWEEP_WITH_ROOM"}
FORBIDDEN_COLUMNS = {
    "outcome",
    "pnl",
    "profit",
    "net",
    "commission",
    "swap",
    "mfe",
    "mae",
    "exit_price",
    "exit_time",
    "close_reason",
    "achieved_r",
    "result",
}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def load_clock_module():
    path = ROOT / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
    spec = importlib.util.spec_from_file_location("fivepercent_server_clock", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load FivePercent server clock")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return path, module


def history_quality_number(raw: object) -> float:
    text = str(raw).strip().rstrip("%")
    return float(text)


def classify_session(utc_naive: datetime) -> str:
    minute = utc_naive.hour * 60 + utc_naive.minute
    if 7 * 60 <= minute < 11 * 60:
        return "LONDON"
    if 13 * 60 <= minute < 17 * 60:
        return "NEW_YORK"
    return "OUTSIDE"


def count_data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        total = sum(1 for _ in handle)
    return max(0, total - 1)


def find_sidecar(run_dir: Path, manifest: dict, marker: str) -> Path:
    matches = []
    for item in manifest.get("sidecars") or []:
        rel = str(item.get("path", ""))
        if marker in Path(rel).name:
            path = run_dir / rel
            if not path.is_file():
                raise ValueError(f"manifest sidecar is missing: {rel}")
            if sha_file(path) != str(item.get("sha256", "")).upper():
                raise ValueError(f"manifest sidecar hash mismatch: {rel}")
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(f"expected one accepted {marker} sidecar, found {len(matches)}")
    return matches[0]


def analyze(run_dir: Path) -> dict:
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    context_path = find_sidecar(run_dir, manifest, "_HumanContext_")
    lifecycle_path = find_sidecar(run_dir, manifest, "_LifecycleTrades_")
    runmeta_path = find_sidecar(run_dir, manifest, "_RunMeta_")
    runmeta = json.loads(runmeta_path.read_text(encoding="utf-8-sig"))
    diagnostic = runmeta.get("diagnostic") or {}

    clock_path, clock = load_clock_module()
    row_count = 0
    valid_count = 0
    invalid_count = 0
    duplicate_event_ids = 0
    duplicate_tuples = 0
    event_ids: set[str] = set()
    identity_rows: set[tuple[str, str, str, str]] = set()
    direction_counts: Counter[str] = Counter()
    session_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    natural_direction_counts: Counter[str] = Counter()
    natural_session_counts: Counter[str] = Counter()
    natural_year_counts: Counter[str] = Counter()
    natural_count = 0
    first_utc: datetime | None = None
    last_utc: datetime | None = None

    with context_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        forbidden_present = sorted(set(columns) & FORBIDDEN_COLUMNS)
        required = {"event_id", "decision_time", "reason", "direction", "valid", "context_state"}
        if not required.issubset(columns):
            raise ValueError(f"HumanContext schema missing {sorted(required - set(columns))}")
        for row in reader:
            row_count += 1
            event_id = row["event_id"]
            identity = (row["decision_time"], row["direction"], row["reason"], event_id)
            if event_id in event_ids:
                duplicate_event_ids += 1
            event_ids.add(event_id)
            if identity in identity_rows:
                duplicate_tuples += 1
            identity_rows.add(identity)

            server_time = datetime.strptime(row["decision_time"], "%Y.%m.%d %H:%M:%S")
            utc_time = clock.server_to_utc(server_time)
            session = classify_session(utc_time)
            year = str(utc_time.year)
            direction = row["direction"]
            state = row["context_state"]
            direction_counts[direction] += 1
            session_counts[session] += 1
            year_counts[year] += 1
            state_counts[state] += 1
            if row["valid"] == "1":
                valid_count += 1
            else:
                invalid_count += 1
            if row["valid"] == "1" and state in NATURAL_STATES:
                natural_count += 1
                natural_direction_counts[direction] += 1
                natural_session_counts[session] += 1
                natural_year_counts[year] += 1
            first_utc = utc_time if first_utc is None or utc_time < first_utc else first_utc
            last_utc = utc_time if last_utc is None or utc_time > last_utc else last_utc

    if first_utc is None or last_utc is None:
        elapsed_weeks = 0.0
    else:
        elapsed_weeks = (last_utc - first_utc).total_seconds() / (7 * 24 * 3600)
    collection_cadence = row_count / elapsed_weeks if elapsed_weeks > 0 else 0.0
    natural_cadence = natural_count / elapsed_weeks if elapsed_weeks > 0 else 0.0
    complete_fraction = valid_count / row_count if row_count else 0.0
    expected_years = [str(year) for year in range(int(min(year_counts)), int(max(year_counts)) + 1)] if year_counts else []
    history_quality = history_quality_number(
        (manifest.get("fingerprint_basis") or {}).get("history_quality", "nan")
    )
    lifecycle_rows = count_data_rows(lifecycle_path)

    gates = {
        "manifest_identity": (
            manifest.get("run_id") == run_dir.name
            and manifest.get("hypothesis_id") == HYPOTHESIS_ID
            and manifest.get("ea_name") == "EA_ICTFVGReportFidelity"
            and manifest.get("symbol") == "EURUSD"
            and manifest.get("period") == "M5"
            and manifest.get("from") == "2018.01.01"
            and manifest.get("to") == "2026.07.19"
            and manifest.get("telemetry_profile") == "lifecycle-v3"
            and manifest.get("source_sha256") == SOURCE_SHA256
            and len(manifest.get("sidecars") or []) == 3
        ),
        "runmeta_identity": (
            runmeta.get("hypothesis_id") == HYPOTHESIS_ID
            and runmeta.get("ea_name") == "EA_ICTFVGReportFidelity"
            and runmeta.get("symbol") == "EURUSD"
            and runmeta.get("telemetry_profile") == "lifecycle-v3"
            and runmeta.get("signal_mode") == 0
            and runmeta.get("human_context_schema") == "human-context-v1"
            and runmeta.get("human_context_observe_only") is True
        ),
        "history_quality_ge_99pct": history_quality >= 99.0,
        "zero_trades": (
            int(diagnostic.get("entries_attempted", -1)) == 0
            and int(diagnostic.get("entries_opened", -1)) == 0
            and lifecycle_rows == 0
        ),
        "context_counter_reconciliation": row_count
        == int(diagnostic.get("human_context_snapshots", -1))
        + int(diagnostic.get("human_context_invalid", -1)),
        "event_ids_unique": duplicate_event_ids == 0 and duplicate_tuples == 0,
        "both_directions": all(direction_counts.get(value, 0) > 0 for value in ("-1", "1")),
        "both_sessions": (
            session_counts.get("LONDON", 0) > 0
            and session_counts.get("NEW_YORK", 0) > 0
        ),
        "all_available_years": all(year_counts.get(year, 0) > 0 for year in expected_years),
        "complete_fraction_ge_99pct": complete_fraction >= 0.99,
        "no_outcome_columns": not forbidden_present,
        "collection_cadence_ge_2_per_week": collection_cadence >= 2.0,
        "natural_policy_cadence_ge_2_per_week": natural_cadence >= 2.0,
        "natural_policy_both_directions": all(
            natural_direction_counts.get(value, 0) > 0 for value in ("-1", "1")
        ),
        "natural_policy_both_sessions": all(
            natural_session_counts.get(value, 0) > 0 for value in ("LONDON", "NEW_YORK")
        ),
        "natural_policy_all_years": all(
            natural_year_counts.get(year, 0) > 0 for year in expected_years
        ),
    }
    result = {
        "schema_version": "hyp016r1_outcome_blind_collection_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": run_dir.name,
        "access_boundary": {
            "report_opened": False,
            "economic_outcome_opened": False,
            "allowed_inputs": [
                "run_manifest identity/fingerprint_basis/sidecar hashes",
                "RunMeta identity and diagnostic counters",
                "HumanContext ledger",
                "LifecycleTrades header and row count",
            ],
        },
        "input_hashes": {
            "run_manifest": sha_file(manifest_path),
            "run_meta": sha_file(runmeta_path),
            "human_context": sha_file(context_path),
            "lifecycle_trades": sha_file(lifecycle_path),
            "server_clock": sha_file(clock_path),
        },
        "coverage": {
            "rows": row_count,
            "valid": valid_count,
            "invalid": invalid_count,
            "complete_fraction": complete_fraction,
            "first_decision_utc": first_utc.isoformat() if first_utc else None,
            "last_decision_utc": last_utc.isoformat() if last_utc else None,
            "elapsed_calendar_weeks": elapsed_weeks,
            "collection_cadence_per_week": collection_cadence,
            "directions": dict(sorted(direction_counts.items())),
            "sessions": dict(sorted(session_counts.items())),
            "years": dict(sorted(year_counts.items())),
            "context_states": dict(sorted(state_counts.items())),
            "duplicate_event_ids": duplicate_event_ids,
            "duplicate_identity_rows": duplicate_tuples,
            "forbidden_columns_present": forbidden_present,
            "history_quality_pct": history_quality,
            "lifecycle_data_rows": lifecycle_rows,
        },
        "natural_policy": {
            "rule": "valid==1 AND context_state in {EXTERNAL_SWEEP_WITH_ROOM,INTERNAL_SWEEP_WITH_ROOM}",
            "rows": natural_count,
            "cadence_per_week": natural_cadence,
            "directions": dict(sorted(natural_direction_counts.items())),
            "sessions": dict(sorted(natural_session_counts.items())),
            "years": dict(sorted(natural_year_counts.items())),
        },
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "verdict": (
            "PASS_OUTCOME_BLIND_COLLECTION_OPEN_HYP017_PREREG"
            if all(gates.values())
            else "FRONTIER_CONTEXT_POLICY_OR_COLLECTION_GATE_FAILED_NO_ECONOMIC_RUN"
        ),
        "promotion_eligible": False,
    }
    result["canonical_result_sha256"] = canonical_sha(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run.resolve())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "sha256": sha_file(args.out), "verdict": result["verdict"]}))
    return 0 if result["all_gates_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
