#!/usr/bin/env python3
"""Outcome-blind parser for the single frozen HYP-026 collection run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from calendar import monthrange, timegm
from datetime import datetime, timedelta
from pathlib import Path


HYPOTHESIS_ID = "HYP-ICT-FVG-PIVOT-RECLAIM-DWELL-COLLECT-EURUSD-M5-026"
EXPECTED_SOURCE_SHA256 = "227A52E93713731EF639D9484DABC89B85006660F436C0F232117C60F1528127"
EXPECTED_RECEIPT_SHA256 = "7837739CC7FDED1ECE0C09EB66840466413AFC12C898706217EF4605422BF108"
EXPECTED_TICK_COVERAGE_SHA256 = "9A68530745B40F6B8E1AC4768F23FE6C052A2F99A5BC3654C4AF8A0E325191F6"
MIN_DEFINED_FRACTION = 0.99
MIN_LABEL_SHARE = 0.20
MIN_LABEL_CADENCE = 2.0
PARSER_SEED = 5600726
LONDON = (7 * 60, 11 * 60)
NEW_YORK = (13 * 60, 17 * 60)
ROOT = Path(r"D:\Trading EA MT5")
PACKAGE = ROOT / "03. EA Developer" / "EA_ICTFVGReportFidelity"
TICK_COVERAGE = (
    PACKAGE
    / "research"
    / "evidence"
    / "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018_TICK_COVERAGE.json"
)
BUILD_RECEIPT = PACKAGE / "research" / "evidence" / "20260719_HYP026_BUILD_TEST_RECEIPT.json"

LEVEL_COLUMNS = {
    "event_id",
    "decision_time",
    "decision_msc",
    "sweep_time",
    "confirmation_bar_time",
    "direction",
    "level",
    "interval_start_msc",
    "last_valid_msc",
    "valid_ticks",
    "invalid_ticks",
    "first_favorable_msc",
    "favorable_ms",
    "adverse_ms",
    "total_ms",
    "max_gap_ms",
    "resilience_label",
    "side_at_seal",
    "interval_identity_valid",
    "duration_identity_valid",
    "tick_provenance",
}
HUMAN_COLUMNS = {"decision_time", "direction", "valid", "context_state"}
LABELS = ("FAVORABLE_DOMINANT", "ADVERSE_DOMINANT")


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def parse_time(value: str) -> datetime:
    return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")


def last_sunday(year: int, month: int, hour: int) -> datetime:
    value = datetime(year, month, monthrange(year, month)[1], hour)
    return value - timedelta(days=(value.weekday() + 1) % 7)


def nth_sunday(year: int, month: int, occurrence: int, hour: int) -> datetime:
    first = datetime(year, month, 1, hour)
    days_to_sunday = (6 - first.weekday()) % 7
    return first + timedelta(days=days_to_sunday + 7 * (occurrence - 1))


def server_to_utc(server_time: datetime) -> datetime:
    year = server_time.year
    if year >= 2024:
        utc_guess = server_time - timedelta(hours=2)
        is_dst = nth_sunday(year, 3, 2, 7) <= utc_guess < nth_sunday(year, 11, 1, 6)
    else:
        is_dst = last_sunday(year, 3, 3) <= server_time < last_sunday(year, 10, 4)
    return server_time - timedelta(hours=2 + int(is_dst))


def session_name(server_time: datetime) -> str:
    utc = server_to_utc(server_time)
    minute = utc.hour * 60 + utc.minute
    if LONDON[0] <= minute < LONDON[1]:
        return "LONDON"
    if NEW_YORK[0] <= minute < NEW_YORK[1]:
        return "NEW_YORK"
    return "OTHER"


def load_manifest(run_dir: Path) -> tuple[dict, dict[str, dict]]:
    raw = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8-sig"))
    selected = {
        "schema_version": raw.get("schema_version"),
        "run_id": raw.get("run_id"),
        "hypothesis_id": raw.get("hypothesis_id"),
        "run_role": raw.get("run_role"),
        "ea_name": raw.get("ea_name"),
        "symbol": raw.get("symbol"),
        "period": raw.get("period"),
        "from": raw.get("from"),
        "to": raw.get("to"),
        "model": raw.get("model"),
        "source_sha256": raw.get("source_sha256"),
        "contract_receipt_sha256": raw.get("contract_receipt_sha256"),
        "required_sidecars": raw.get("required_sidecars"),
        "history_quality": (raw.get("fingerprint_basis") or {}).get("history_quality"),
        "ticks": (raw.get("fingerprint_basis") or {}).get("ticks"),
    }
    sidecars = {Path(item["path"]).name: item for item in raw.get("sidecars", [])}
    return selected, sidecars


def one_sidecar(run_dir: Path, pattern: str, sealed: dict[str, dict]) -> tuple[Path, dict]:
    matches = list((run_dir / "logs").glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one {pattern} sidecar, found {len(matches)}")
    path = matches[0]
    if path.name not in sealed:
        raise ValueError(f"sidecar is not sealed in manifest: {path.name}")
    seal = sealed[path.name]
    if sha_file(path) != seal.get("sha256"):
        raise ValueError(f"sidecar hash mismatch: {path.name}")
    return path, seal


def data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        if not handle.readline().strip():
            raise ValueError(f"sidecar header is missing: {path.name}")
        return sum(1 for line in handle if line.strip())


def load_human_pairs(path: Path) -> Counter[tuple[str, int]]:
    pairs: Counter[tuple[str, int]] = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not HUMAN_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("HumanContext allowlist columns are missing")
        for row in reader:
            if row["valid"] != "1":
                raise ValueError("invalid HumanContext row in frozen collection")
            pairs[(row["decision_time"], int(row["direction"]))] += 1
    return pairs


def load_level_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    event_ids: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != LEVEL_COLUMNS:
            raise ValueError("LevelPath schema differs from frozen allowlist")
        for raw in reader:
            event_id = raw["event_id"]
            if event_id in event_ids:
                raise ValueError(f"duplicate event_id: {event_id}")
            event_ids.add(event_id)
            direction = int(raw["direction"])
            if direction not in (-1, 1):
                raise ValueError(f"invalid direction: {event_id}")
            level = float(raw["level"])
            if not math.isfinite(level) or level <= 0:
                raise ValueError(f"invalid structural level: {event_id}")
            decision = parse_time(raw["decision_time"])
            sweep = parse_time(raw["sweep_time"])
            confirmation = parse_time(raw["confirmation_bar_time"])
            decision_msc = int(raw["decision_msc"])
            interval_start_msc = int(raw["interval_start_msc"])
            last_valid_msc = int(raw["last_valid_msc"])
            first_favorable_msc = int(raw["first_favorable_msc"])
            valid_ticks = int(raw["valid_ticks"])
            invalid_ticks = int(raw["invalid_ticks"])
            favorable_ms = int(raw["favorable_ms"])
            adverse_ms = int(raw["adverse_ms"])
            total_ms = int(raw["total_ms"])
            max_gap_ms = int(raw["max_gap_ms"])
            start_identity_valid = interval_start_msc == int(
                timegm((sweep + timedelta(minutes=5)).timetuple()) * 1000
            )
            interval_identity_valid = (
                start_identity_valid
                and decision_msc == timegm(decision.timetuple()) * 1000
                and interval_start_msc <= last_valid_msc < decision_msc
            )
            if not start_identity_valid:
                raise ValueError(f"sweep-close interval mismatch: {event_id}")
            if decision - confirmation != timedelta(minutes=5):
                raise ValueError(f"confirmation-close interval mismatch: {event_id}")
            if any(
                value < 0
                for value in (
                    valid_ticks,
                    invalid_ticks,
                    favorable_ms,
                    adverse_ms,
                    total_ms,
                    max_gap_ms,
                )
            ):
                raise ValueError(f"invalid path fields: {event_id}")
            if int(raw["interval_identity_valid"]) != int(interval_identity_valid):
                raise ValueError(f"interval identity derivation mismatch: {event_id}")
            duration_identity_valid = (
                interval_identity_valid
                and first_favorable_msc >= interval_start_msc
                and first_favorable_msc <= last_valid_msc
                and total_ms > 0
                and total_ms == favorable_ms + adverse_ms
                and total_ms == decision_msc - first_favorable_msc
            )
            if int(raw["duration_identity_valid"]) != int(duration_identity_valid):
                raise ValueError(f"duration identity derivation mismatch: {event_id}")
            if raw["tick_provenance"] != "MODEL0_REAL_TICK_TIME_MSC_LEVEL_RESILIENCE_V1":
                raise ValueError(f"tick provenance mismatch: {event_id}")
            derived_label = "UNDEFINED"
            if duration_identity_valid and favorable_ms > adverse_ms:
                derived_label = "FAVORABLE_DOMINANT"
            elif duration_identity_valid and adverse_ms > favorable_ms:
                derived_label = "ADVERSE_DOMINANT"
            if raw["resilience_label"] != derived_label:
                raise ValueError(f"resilience label derivation mismatch: {event_id}")
            defined = derived_label in LABELS
            rows.append(
                {
                    "event_id": event_id,
                    "decision_time": raw["decision_time"],
                    "direction": direction,
                    "defined": defined,
                    "identity_valid": interval_identity_valid,
                    "duration_identity_valid": duration_identity_valid,
                    "label": derived_label,
                    "year": decision.year,
                    "session": session_name(decision),
                    "favorable_ms": favorable_ms,
                    "adverse_ms": adverse_ms,
                    "total_ms": total_ms,
                    "max_gap_ms": max_gap_ms,
                    "max_gap_share": max_gap_ms / total_ms if total_ms else None,
                    "valid_ticks": valid_ticks,
                }
            )
    return rows


def label_block(rows: list[dict]) -> dict:
    defined = [row for row in rows if row["defined"]]
    counts = Counter(row["label"] for row in defined)
    total = len(defined)
    return {
        "defined_rows": total,
        "favorable_dominant_rows": counts["FAVORABLE_DOMINANT"],
        "adverse_dominant_rows": counts["ADVERSE_DOMINANT"],
        "favorable_dominant_share": counts["FAVORABLE_DOMINANT"] / total if total else 0.0,
        "adverse_dominant_share": counts["ADVERSE_DOMINANT"] / total if total else 0.0,
    }


def analyze_core(run_dir: Path) -> dict:
    manifest, sealed = load_manifest(run_dir)
    required_patterns = sorted(
        [
            "*_HumanContext_*.csv",
            "*_LevelPath_*.csv",
            "*_LevelResilience_*.csv",
            "*_LifecycleTrades_*.csv",
            "*_RunMeta_*.json",
            "*_TickInitiation_*.csv",
        ]
    )
    if manifest["required_sidecars"] != required_patterns:
        raise ValueError("required-sidecar contract mismatch")
    resilience_path, resilience_seal = one_sidecar(
        run_dir, "*_LevelResilience_*.csv", sealed
    )
    level_path, level_seal = one_sidecar(run_dir, "*_LevelPath_*.csv", sealed)
    human_path, human_seal = one_sidecar(run_dir, "*_HumanContext_*.csv", sealed)
    lifecycle_path, lifecycle_seal = one_sidecar(run_dir, "*_LifecycleTrades_*.csv", sealed)
    tick_path, tick_seal = one_sidecar(run_dir, "*_TickInitiation_*.csv", sealed)
    meta_path, _ = one_sidecar(run_dir, "*_RunMeta_*.json", sealed)

    rows = load_level_rows(resilience_path)
    human_pairs = load_human_pairs(human_path)
    resilience_pairs = Counter((row["decision_time"], row["direction"]) for row in rows)
    if human_pairs != resilience_pairs:
        raise ValueError("HumanContext and LevelResilience decision identity differ")
    lifecycle_rows = data_rows(lifecycle_path)
    tick_rows = data_rows(tick_path)
    level_path_rows = data_rows(level_path)
    meta_raw = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    counter_names = [
        "entries_attempted",
        "entries_opened",
        "context_confirmations",
        "human_context_snapshots",
        "tick_profiles_logged",
        "level_paths_logged",
        "resilience_logged",
        "resilience_defined",
        "resilience_favorable_dominant",
        "resilience_adverse_dominant",
        "resilience_identity_invalid",
        "resilience_duration_invalid",
    ]
    diagnostic = {key: (meta_raw.get("diagnostic") or {}).get(key) for key in counter_names}
    if any(value is None for value in diagnostic.values()):
        raise ValueError("RunMeta counter is missing")

    coverage = json.loads(TICK_COVERAGE.read_text(encoding="utf-8-sig"))
    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8-sig"))
    history_quality = int(str(manifest["history_quality"]).rstrip("%"))
    tester_ticks = int(str(manifest["ticks"]).replace(",", ""))
    start = datetime.strptime(manifest["from"], "%Y.%m.%d")
    finish = datetime.strptime(manifest["to"], "%Y.%m.%d") + timedelta(days=1)
    elapsed_weeks = (finish - start).total_seconds() / (7 * 86400)
    label_rows = {label: [row for row in rows if row["label"] == label] for label in LABELS}
    shares = {
        "pooled": label_block(rows),
        "2018-2022": label_block([row for row in rows if 2018 <= row["year"] <= 2022]),
        "2023-YTD": label_block([row for row in rows if row["year"] >= 2023]),
    }
    expected_years = list(range(2018, 2027))
    defined_rows = [row for row in rows if row["defined"]]
    coverage_by_label = {
        label: {
            "directions": sorted({row["direction"] for row in label_rows[label]}),
            "sessions": sorted(
                {row["session"] for row in label_rows[label] if row["session"] != "OTHER"}
            ),
            "years": sorted({row["year"] for row in label_rows[label]}),
            "cadence_per_week": len(label_rows[label]) / elapsed_weeks,
        }
        for label in LABELS
    }
    identity_ok = (
        manifest["hypothesis_id"] == HYPOTHESIS_ID
        and manifest["run_role"] == "control"
        and manifest["ea_name"] == "EA_ICTFVGReportFidelity"
        and manifest["symbol"] == "EURUSD"
        and manifest["period"] == "M5"
        and manifest["from"] == "2018.01.01"
        and manifest["to"] == "2026.07.19"
        and manifest["model"] == 0
        and manifest["source_sha256"] == EXPECTED_SOURCE_SHA256
        and manifest["contract_receipt_sha256"] == EXPECTED_RECEIPT_SHA256
    )
    counts = Counter(row["label"] for row in defined_rows)
    derived_identity_invalid = sum(not row["identity_valid"] for row in rows)
    derived_duration_invalid = sum(not row["duration_identity_valid"] for row in rows)
    reconciliation_ok = (
        len(rows) == resilience_seal.get("row_count") == human_seal.get("row_count")
        and lifecycle_rows == lifecycle_seal.get("row_count") == 0
        and tick_rows == tick_seal.get("row_count") == 0
        and level_path_rows == level_seal.get("row_count") == 0
        and diagnostic["context_confirmations"] == len(rows)
        and diagnostic["human_context_snapshots"] == len(rows)
        and diagnostic["tick_profiles_logged"] == 0
        and diagnostic["level_paths_logged"] == 0
        and diagnostic["resilience_logged"] == len(rows)
        and diagnostic["resilience_defined"] == len(defined_rows)
        and diagnostic["resilience_favorable_dominant"] == counts["FAVORABLE_DOMINANT"]
        and diagnostic["resilience_adverse_dominant"] == counts["ADVERSE_DOMINANT"]
        and diagnostic["resilience_identity_invalid"] == derived_identity_invalid
        and diagnostic["resilience_duration_invalid"] == derived_duration_invalid
    )
    materiality_ok = all(
        block["favorable_dominant_share"] >= MIN_LABEL_SHARE
        and block["adverse_dominant_share"] >= MIN_LABEL_SHARE
        for block in shares.values()
    )
    density_coverage_ok = all(
        coverage_by_label[label]["cadence_per_week"] >= MIN_LABEL_CADENCE
        and coverage_by_label[label]["directions"] == [-1, 1]
        and coverage_by_label[label]["sessions"] == ["LONDON", "NEW_YORK"]
        and coverage_by_label[label]["years"] == expected_years
        for label in LABELS
    )
    gates = {
        "engineering": {
            "pass": (build.get("package_regression") or {}).get("passed") == 105
            and (build.get("package_regression") or {}).get("failed") == 0
            and (build.get("compile") or {}).get("errors") == 0
            and (build.get("compile") or {}).get("warnings") == 0
            and (build.get("nonrepaint") or {}).get("status") == "PASS"
            and (build.get("source") or {}).get("sha256") == EXPECTED_SOURCE_SHA256,
        },
        "run_identity_and_real_ticks": {
            "pass": identity_ok
            and history_quality >= 99
            and tester_ticks > 0
            and sha_file(TICK_COVERAGE) == EXPECTED_TICK_COVERAGE_SHA256
            and coverage.get("missing_months") == []
            and coverage.get("monthly_files") == 103,
        },
        "zero_trade": {
            "pass": diagnostic["entries_attempted"] == 0
            and diagnostic["entries_opened"] == 0
            and lifecycle_rows == 0
            and tick_rows == 0
            and level_path_rows == 0,
        },
        "identity_and_reconciliation": {
            "pass": reconciliation_ok
            and all(row["duration_identity_valid"] for row in defined_rows),
        },
        "defined_fraction": {
            "pass": len(defined_rows) / resilience_seal.get("row_count", 0) >= MIN_DEFINED_FRACTION
            if resilience_seal.get("row_count", 0)
            else False,
        },
        "label_density_and_coverage": {"pass": density_coverage_ok},
        "materiality": {"pass": materiality_ok},
        "input_allowlist": {"pass": True},
    }
    return {
        "schema_version": "alphafactory_hyp026_collection_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": manifest["run_id"],
        "parser_seed": PARSER_SEED,
        "source_sha256": manifest["source_sha256"],
        "manifest_sha256": sha_file(run_dir / "run_manifest.json"),
        "sidecar_sha256": {name: item["sha256"] for name, item in sorted(sealed.items())},
        "allowed_inputs": [
            "run manifest identity, history quality, tick count and sidecar seal",
            "LevelResilience frozen columns",
            "HumanContext decision_time, direction, valid and context_state",
            "RunMeta identity and frozen counters",
            "LifecycleTrades, TickInitiation and LevelPath row counts only",
            "engineering receipt and pre-run tick coverage",
        ],
        "counts": {
            "confirmation_rows": len(rows),
            "defined_rows": len(defined_rows),
            "favorable_dominant_rows": counts["FAVORABLE_DOMINANT"],
            "adverse_dominant_rows": counts["ADVERSE_DOMINANT"],
            "lifecycle_data_rows": lifecycle_rows,
            "tick_initiation_data_rows": tick_rows,
            "level_path_data_rows": level_path_rows,
            "tester_ticks": tester_ticks,
        },
        "elapsed_calendar_weeks": elapsed_weeks,
        "defined_fraction": len(defined_rows) / resilience_seal.get("row_count", 1),
        "label_coverage": coverage_by_label,
        "materiality_shares": shares,
        "gates": gates,
        "limitations": [
            "Pivot-relative quote-mid dwell is a broker-feed path proxy, not signed transaction flow or depth.",
            "Last-valid-side carry assigns sparse quote gaps to the prior side; gap telemetry is diagnostic only and cannot rescue the hypothesis.",
            "This zero-trade collection does not estimate economic edge.",
            "Historical cost provenance remains independently unresolved.",
        ],
    }


def assert_no_forbidden_result_keys(value: object) -> None:
    forbidden = {
        "pnl", "profit", "drawdown", "balance", "equity", "commission",
        "swap", "mfe", "mae", "exit", "future_price",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            if any(token in key.lower() for token in forbidden):
                raise ValueError(f"forbidden result key: {key}")
            assert_no_forbidden_result_keys(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_forbidden_result_keys(child)


def build_result(run_dir: Path) -> dict:
    first = analyze_core(run_dir)
    second = analyze_core(run_dir)
    deterministic = canonical_bytes(first) == canonical_bytes(second)
    first["gates"]["deterministic_replay"] = {"pass": deterministic}
    all_pass = all(gate["pass"] for gate in first["gates"].values())
    first["verdict"] = (
        "PASS_OPEN_SEPARATE_PRE_ECONOMIC_HYP027"
        if all_pass
        else "KILL_AT_HYP026_COLLECTION_DATA_DENSITY_OR_REDUNDANCY"
    )
    first["failed_gates"] = sorted(
        name for name, gate in first["gates"].items() if not gate["pass"]
    )
    assert_no_forbidden_result_keys(first)
    return first


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build_result(args.run_dir.resolve())
    payload = canonical_bytes(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": hashlib.sha256(payload).hexdigest().upper(),
                "verdict": result["verdict"],
                "failed_gates": result["failed_gates"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

