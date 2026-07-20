#!/usr/bin/env python3
"""Outcome-blind parser for the single frozen HYP-018 collection run."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from calendar import monthrange
from datetime import datetime, timedelta
from pathlib import Path


HYPOTHESIS_ID = "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018"
EXPECTED_SOURCE_SHA256 = "41536FFC43BE85B1250A627197BD63FED5C7D5C7CF87D8965163F5449EACDA40"
EXPECTED_RECEIPT_SHA256 = "81CA0EB2871453D0DBD5B7D402E22224D63834A17F4AB201C55EBCBC30C14AA7"
EXPECTED_TICK_COVERAGE_SHA256 = "9A68530745B40F6B8E1AC4768F23FE6C052A2F99A5BC3654C4AF8A0E325191F6"
MIN_DEFINED_FRACTION = 0.99
MIN_SIGN_SHARE = 0.20
MIN_AGREE_CADENCE = 2.0
PARSER_SEED = 5600718
LONDON = (7 * 60, 11 * 60)
NEW_YORK = (13 * 60, 17 * 60)
ROOT = Path(r"D:\Trading EA MT5")
PACKAGE = ROOT / "03. EA Developer" / "EA_ICTFVGReportFidelity"
TICK_COVERAGE = PACKAGE / "research" / "evidence" / f"{HYPOTHESIS_ID}_TICK_COVERAGE.json"
BUILD_RECEIPT = PACKAGE / "research" / "evidence" / "20260719_HYP018_BUILD_TEST_RECEIPT.json"

TICK_COLUMNS = {
    "event_id", "decision_time", "confirmation_bar_time", "profile_bar_time",
    "direction", "valid_ticks", "invalid_ticks", "up_ticks", "down_ticks",
    "flat_ticks", "nonzero_ticks", "imbalance", "sign_agree", "first_mid",
    "last_mid", "path_length", "net_mid_change", "first_spread", "last_spread",
    "max_spread", "profile_identity_valid", "tick_provenance",
}
HUMAN_COLUMNS = {"decision_time", "direction", "valid", "context_state"}


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


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


def one_sidecar(run_dir: Path, pattern: str, sidecars: dict[str, dict]) -> tuple[Path, dict]:
    matches = list((run_dir / "logs").glob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected one {pattern} sidecar, found {len(matches)}")
    path = matches[0]
    if path.name not in sidecars:
        raise ValueError(f"sidecar is not sealed in manifest: {path.name}")
    seal = sidecars[path.name]
    if sha_file(path) != seal.get("sha256"):
        raise ValueError(f"sidecar hash mismatch: {path.name}")
    return path, seal


def lifecycle_data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = handle.readline().strip()
        if not header:
            raise ValueError("LifecycleTrades header is missing")
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


def load_tick_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    event_ids: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != TICK_COLUMNS:
            raise ValueError("TickInitiation schema differs from frozen allowlist")
        for raw in reader:
            event_id = raw["event_id"]
            if event_id in event_ids:
                raise ValueError(f"duplicate event_id: {event_id}")
            event_ids.add(event_id)
            direction = int(raw["direction"])
            nonzero = int(raw["nonzero_ticks"])
            imbalance = float(raw["imbalance"])
            defined = nonzero > 0 and math.isfinite(imbalance)
            derived_agree = defined and ((direction == 1 and imbalance > 0) or (direction == -1 and imbalance < 0))
            if int(raw["sign_agree"]) != int(derived_agree):
                raise ValueError(f"sign derivation mismatch: {event_id}")
            if raw["confirmation_bar_time"] != raw["profile_bar_time"]:
                raise ValueError(f"bar identity mismatch: {event_id}")
            if int(raw["profile_identity_valid"]) != 1:
                raise ValueError(f"profile identity flag failed: {event_id}")
            if raw["tick_provenance"] != "MODEL0_REAL_TICK_ONLINE_V1":
                raise ValueError(f"tick provenance mismatch: {event_id}")
            decision = parse_time(raw["decision_time"])
            confirmation = parse_time(raw["confirmation_bar_time"])
            if decision - confirmation != timedelta(minutes=5):
                raise ValueError(f"closed-bar interval mismatch: {event_id}")
            rows.append({
                "event_id": event_id,
                "decision_time": raw["decision_time"],
                "direction": direction,
                "defined": defined,
                "sign_agree": derived_agree,
                "year": decision.year,
                "session": session_name(decision),
            })
    return rows


def share_block(rows: list[dict]) -> dict:
    defined = [row for row in rows if row["defined"]]
    agree = sum(row["sign_agree"] for row in defined)
    nonagree = len(defined) - agree
    denominator = len(defined)
    return {
        "defined_rows": denominator,
        "sign_agree_rows": agree,
        "sign_nonagree_rows": nonagree,
        "sign_agree_share": agree / denominator if denominator else 0.0,
        "sign_nonagree_share": nonagree / denominator if denominator else 0.0,
    }


def analyze_core(run_dir: Path) -> dict:
    manifest, sealed = load_manifest(run_dir)
    required_patterns = sorted([
        "*_HumanContext_*.csv", "*_LifecycleTrades_*.csv",
        "*_RunMeta_*.json", "*_TickInitiation_*.csv",
    ])
    if manifest["required_sidecars"] != required_patterns:
        raise ValueError("required-sidecar contract mismatch")
    tick_path, tick_seal = one_sidecar(run_dir, "*_TickInitiation_*.csv", sealed)
    human_path, human_seal = one_sidecar(run_dir, "*_HumanContext_*.csv", sealed)
    lifecycle_path, lifecycle_seal = one_sidecar(run_dir, "*_LifecycleTrades_*.csv", sealed)
    meta_path, _ = one_sidecar(run_dir, "*_RunMeta_*.json", sealed)

    rows = load_tick_rows(tick_path)
    human_pairs = load_human_pairs(human_path)
    tick_pairs = Counter((row["decision_time"], row["direction"]) for row in rows)
    if human_pairs != tick_pairs:
        raise ValueError("HumanContext and TickInitiation decision identity differ")
    lifecycle_rows = lifecycle_data_rows(lifecycle_path)
    meta_raw = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    meta = {
        "run_id": meta_raw.get("run_id"),
        "hypothesis_id": meta_raw.get("hypothesis_id"),
        "ea_name": meta_raw.get("ea_name"),
        "symbol": meta_raw.get("symbol"),
        "signal_mode": meta_raw.get("signal_mode"),
        "promotion_eligible": meta_raw.get("promotion_eligible"),
        "tick_initiation_schema": meta_raw.get("tick_initiation_schema"),
        "diagnostic": {
            key: (meta_raw.get("diagnostic") or {}).get(key)
            for key in [
                "entries_attempted", "entries_opened", "context_confirmations",
                "human_context_snapshots", "tick_profiles_logged", "tick_profiles_defined",
                "tick_sign_agree", "tick_sign_nonagree", "tick_profile_identity_invalid",
            ]
        },
    }
    diagnostic = meta["diagnostic"]
    if any(diagnostic[key] is None for key in diagnostic):
        raise ValueError("RunMeta counter is missing")

    coverage = json.loads(TICK_COVERAGE.read_text(encoding="utf-8-sig"))
    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8-sig"))
    history_quality = int(str(manifest["history_quality"]).rstrip("%"))
    tester_ticks = int(str(manifest["ticks"]).replace(",", ""))
    start = datetime.strptime(manifest["from"], "%Y.%m.%d")
    finish = datetime.strptime(manifest["to"], "%Y.%m.%d") + timedelta(days=1)
    elapsed_weeks = (finish - start).total_seconds() / (7 * 86400)
    defined_rows = [row for row in rows if row["defined"]]
    agree_rows = [row for row in defined_rows if row["sign_agree"]]
    shares = {
        "pooled": share_block(rows),
        "2018-2022": share_block([row for row in rows if 2018 <= row["year"] <= 2022]),
        "2023-YTD": share_block([row for row in rows if row["year"] >= 2023]),
    }
    expected_years = list(range(2018, 2027))
    agree_years = sorted({row["year"] for row in agree_rows})
    agree_directions = sorted({row["direction"] for row in agree_rows})
    agree_sessions = sorted({row["session"] for row in agree_rows if row["session"] != "OTHER"})

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
    row_reconciliation_ok = (
        len(rows) == tick_seal.get("row_count") == human_seal.get("row_count")
        and lifecycle_rows == lifecycle_seal.get("row_count") == 0
        and diagnostic["context_confirmations"] == len(rows)
        and diagnostic["human_context_snapshots"] == len(rows)
        and diagnostic["tick_profiles_logged"] == len(rows)
        and diagnostic["tick_profiles_defined"] == len(defined_rows)
        and diagnostic["tick_sign_agree"] == len(agree_rows)
        and diagnostic["tick_sign_nonagree"] == len(defined_rows) - len(agree_rows)
    )
    materiality_ok = all(
        block["sign_agree_share"] >= MIN_SIGN_SHARE
        and block["sign_nonagree_share"] >= MIN_SIGN_SHARE
        for block in shares.values()
    )
    gates = {
        "engineering": {
            "pass": build.get("tests_passed") == 60
            and build.get("tests_failed") == 0
            and (build.get("compile") or {}).get("errors") == 0
            and (build.get("compile") or {}).get("warnings") == 0
            and (build.get("nonrepaint") or {}).get("status") == "PASS",
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
            and lifecycle_rows == 0,
        },
        "identity_and_reconciliation": {
            "pass": row_reconciliation_ok and diagnostic["tick_profile_identity_invalid"] == 0,
        },
        "defined_fraction": {
            "pass": len(defined_rows) / len(rows) >= MIN_DEFINED_FRACTION if rows else False,
        },
        "agree_density_and_coverage": {
            "pass": len(agree_rows) / elapsed_weeks >= MIN_AGREE_CADENCE
            and agree_directions == [-1, 1]
            and agree_sessions == ["LONDON", "NEW_YORK"]
            and agree_years == expected_years,
        },
        "materiality": {"pass": materiality_ok},
        "input_allowlist": {"pass": True},
    }
    return {
        "schema_version": "alphafactory_hyp018_collection_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": manifest["run_id"],
        "parser_seed": PARSER_SEED,
        "source_sha256": manifest["source_sha256"],
        "manifest_sha256": sha_file(run_dir / "run_manifest.json"),
        "sidecar_sha256": {name: item["sha256"] for name, item in sorted(sealed.items())},
        "allowed_inputs": [
            "run manifest identity, history quality, tick count, and sidecar seal",
            "TickInitiation frozen columns",
            "HumanContext decision_time, direction, valid, context_state",
            "RunMeta identity and frozen counters",
            "LifecycleTrades row count only",
            "engineering receipt and pre-run tick coverage",
        ],
        "counts": {
            "confirmation_rows": len(rows),
            "defined_rows": len(defined_rows),
            "sign_agree_rows": len(agree_rows),
            "sign_nonagree_rows": len(defined_rows) - len(agree_rows),
            "lifecycle_data_rows": lifecycle_rows,
            "tester_ticks": tester_ticks,
        },
        "elapsed_calendar_weeks": elapsed_weeks,
        "defined_fraction": len(defined_rows) / len(rows) if rows else 0.0,
        "sign_agree_cadence_per_week": len(agree_rows) / elapsed_weeks,
        "sign_agree_directions": agree_directions,
        "sign_agree_sessions": agree_sessions,
        "sign_agree_years": agree_years,
        "materiality_shares": shares,
        "gates": gates,
        "limitations": [
            "Quote-mid tick-rule imbalance is a broker-feed path proxy, not signed transaction flow or depth.",
            "This zero-trade collection does not estimate economic edge.",
            "Historical cost provenance remains independently unresolved.",
        ],
    }


def assert_no_forbidden_result_keys(value: object) -> None:
    forbidden_result_keys = {"pnl", "profit", "drawdown", "balance", "equity", "commission", "swap", "mfe", "mae"}
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if any(token in lowered for token in forbidden_result_keys):
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
        "PASS_OPEN_SEPARATE_PREOUTCOME_HYP019"
        if all_pass
        else "KILL_AT_HYP018_COLLECTION_DATA_DENSITY_OR_REDUNDANCY"
    )
    first["failed_gates"] = sorted(name for name, gate in first["gates"].items() if not gate["pass"])
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
    print(json.dumps({
        "output": str(args.output),
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
        "verdict": result["verdict"],
        "failed_gates": result["failed_gates"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
