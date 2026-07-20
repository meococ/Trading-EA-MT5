#!/usr/bin/env python3
"""Fail-closed validator for the FVG owner-label packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from casebook_contract import (
    HOLDOUT,
    PROTOCOL_PATH,
    SOURCE_PATH,
    STRATA,
    STUDY_ID,
    ContractError,
    assert_frozen_inputs,
    casebook_code_binding,
    load_json,
    packet_file_hashes,
    sha256_file,
    signal_identity,
)

FORBIDDEN_PACKET_HEADER_TOKENS = ("direction", "stratum", "category", "ea_", "outcome", "pnl", "return_r", "result")
FORBIDDEN_INTERNAL_OUTCOME_KEYS = {"outcome", "pnl", "return_r", "exit", "mfe", "mae", "win", "loss", "profit_factor"}


def _check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _contains_forbidden_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_INTERNAL_OUTCOME_KEYS:
                return str(key)
            found = _contains_forbidden_key(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _contains_forbidden_key(child)
            if found:
                return found
    return None


def validate(internal_path: Path, packet: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        protocol = assert_frozen_inputs()
    except Exception as exc:
        protocol = {}
        errors.append(f"frozen input failure: {exc}")
    try:
        internal = load_json(internal_path)
        manifest = load_json(packet / "PACKET_MANIFEST.json")
        chart_manifest = load_json(packet / "CHART_MANIFEST.json")
    except Exception as exc:
        return {"schema_version": "fvg_casebook_validation.v2", "study_id": STUDY_ID,
                "status": "FAIL", "errors": [f"required JSON load failed: {exc}"]}

    _check(internal.get("schema_version") == "fvg_casebook_internal.v2", "internal schema mismatch", errors)
    _check(manifest.get("schema_version") == "fvg_owner_label_packet.v2", "packet schema mismatch", errors)
    _check(chart_manifest.get("schema_version") == "fvg_blinded_chart_manifest.v1", "chart schema mismatch", errors)
    _check(all(x.get("study_id") == STUDY_ID for x in (internal, manifest, chart_manifest)), "study id mismatch", errors)
    _check(internal.get("outcome_columns_present") is False, "internal outcome declaration not false", errors)
    _check(internal.get("holdout_rows_loaded") == 0, "holdout_rows_loaded must be zero", errors)
    max_loaded = pd.Timestamp(internal.get("maximum_loaded_time_utc", "2100-01-01").replace("Z", ""))
    _check(max_loaded < HOLDOUT, "loaded data reached/crossed 2023 holdout", errors)
    forbidden = _contains_forbidden_key(internal.get("cases", []))
    _check(forbidden is None, f"internal outcome key present: {forbidden}", errors)

    cases = internal.get("cases", [])
    ids = [r.get("case_id") for r in cases]
    times = [r.get("decision_time_utc") for r in cases]
    _check(len(cases) == 400, f"case count expected 400 got {len(cases)}", errors)
    _check(len(set(ids)) == len(ids), "duplicate case id", errors)
    _check(len(set(times)) == len(times), "duplicate decision timestamp", errors)
    try:
        signals = [signal_identity(row) for row in cases]
        _check(len(set(signals)) == len(signals), "duplicate underlying FVG identity", errors)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"invalid underlying FVG identity: {exc}")
    _check(all(pd.Timestamp(t.replace("Z", "")) < HOLDOUT for t in times if isinstance(t, str)), "case at/after holdout", errors)
    split_counts = Counter(r.get("split") for r in cases)
    _check(split_counts == Counter({"calibration": 100, "evaluation": 300}), f"split counts invalid: {split_counts}", errors)
    _check(all(r.get("stratum") in STRATA for r in cases), "unknown stratum", errors)
    _check(all(r.get("direction") in (-1, 1) for r in cases), "invalid internal direction", errors)
    for row in cases:
        identity = {key: row.get(key) for key in ("case_id", "split", "decision_time_utc", "formed_time_utc",
                                                  "direction", "stratum", "bottom", "top")}
        wanted = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest().upper()
        _check(row.get("event_sha256") == wanted, f"event identity hash mismatch: {row.get('case_id')}", errors)

    binding = internal.get("source_binding", {})
    _check(binding.get("protocol_sha256") == sha256_file(PROTOCOL_PATH), "internal protocol hash stale", errors)
    _check(binding.get("protocol_declared_main_source_sha256") == sha256_file(SOURCE_PATH), "main source hash stale", errors)
    for bound_file in binding.get("files", []):
        bound_path = SOURCE_PATH.parents[2] / bound_file.get("path", "__missing__")
        _check(bound_path.is_file(), f"bound source file missing: {bound_file.get('path')}", errors)
        if bound_path.is_file():
            _check(sha256_file(bound_path) == bound_file.get("sha256"),
                   f"bound source file hash stale: {bound_file.get('path')}", errors)
    _check(internal.get("casebook_code_binding") == casebook_code_binding(), "casebook code binding stale", errors)
    _check(manifest.get("bindings", {}).get("internal_casebook_sha256") == sha256_file(internal_path), "internal casebook hash mismatch", errors)
    _check(manifest.get("bindings", {}).get("protocol_sha256") == sha256_file(PROTOCOL_PATH), "packet protocol hash mismatch", errors)
    _check(manifest.get("bindings", {}).get("source_sha256") == sha256_file(SOURCE_PATH), "packet source hash mismatch", errors)
    if protocol:
        _check(protocol["specimen"]["source_sha256"] == sha256_file(SOURCE_PATH), "source differs from protocol", errors)

    expected_files = manifest.get("files", [])
    current_files = packet_file_hashes(packet, {"PACKET_MANIFEST.json"})
    _check(expected_files == current_files, "packet file inventory/hash mismatch", errors)
    blinding = manifest.get("blinding", {})
    _check(all(blinding.get(k) is False for k in ("direction_present", "stratum_present", "ea_decision_present", "outcome_present", "future_bars_present")),
           "packet blinding declaration failed", errors)

    charts = chart_manifest.get("charts", [])
    _check(len(charts) == 400, f"chart count expected 400 got {len(charts)}", errors)
    chart_by_id = {r.get("case_id"): r for r in charts}
    _check(set(chart_by_id) == set(ids), "chart/case coverage mismatch", errors)
    for case in cases:
        chart = chart_by_id.get(case["case_id"], {})
        decision = pd.Timestamp(case["decision_time_utc"].replace("Z", ""))
        _check(chart.get("future_bars_drawn") == 0, f"future bar flag: {case['case_id']}", errors)
        _check(chart.get("decision_cutoff_utc") == case["decision_time_utc"], f"cutoff mismatch: {case['case_id']}", errors)
        for cutoff in chart.get("last_closed_bar_by_timeframe", {}).values():
            _check(pd.Timestamp(cutoff.replace("Z", "")) <= decision, f"future chart cutoff: {case['case_id']}", errors)
        chart_path = packet / chart.get("chart", "missing")
        _check(chart_path.is_file(), f"chart missing: {case['case_id']}", errors)
        if chart_path.is_file():
            _check(sha256_file(chart_path) == chart.get("sha256"), f"chart hash mismatch: {case['case_id']}", errors)

    for reviewer in (1, 2):
        overlay = packet / f"REVIEWER_{reviewer}_OVERLAY.csv"
        try:
            with overlay.open(newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                actual_headers = reader.fieldnames or []
                rows = list(reader)
            _check(not any(token in header.lower() for token in FORBIDDEN_PACKET_HEADER_TOKENS for header in actual_headers),
                   f"reviewer {reviewer} overlay leaks protected header", errors)
            _check(len(rows) == 400 and {r["case_id"] for r in rows} == set(ids), f"reviewer {reviewer} coverage mismatch", errors)
            _check(all(not r.get("setup_label", "").strip() for r in rows), f"reviewer {reviewer} template is not blank", errors)
            expected_by_id = {row["case_id"]: row for row in cases}
            for row in rows:
                case = expected_by_id.get(row.get("case_id", ""), {})
                expected_bindings = {
                    "schema_version": "fvg_reviewer_overlay.v2",
                    "study_id": STUDY_ID,
                    "source_sha256": sha256_file(SOURCE_PATH),
                    "internal_casebook_sha256": sha256_file(internal_path),
                    "event_sha256": case.get("event_sha256", "__missing__"),
                    "chart": f"charts/{row.get('case_id', '')}.png",
                }
                for key, wanted in expected_bindings.items():
                    _check(row.get(key, "") == wanted,
                           f"reviewer {reviewer} row binding mismatch {row.get('case_id')}: {key}", errors)
        except Exception as exc:
            errors.append(f"reviewer {reviewer} overlay read failed: {exc}")

    return {
        "schema_version": "fvg_casebook_validation.v2",
        "study_id": STUDY_ID,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "counts": {"cases": len(cases), "charts": len(charts), "calibration": split_counts.get("calibration", 0),
                   "evaluation": split_counts.get("evaluation", 0), "strata": dict(Counter(r.get("stratum") for r in cases))},
        "bindings": {"internal_sha256": sha256_file(internal_path), "packet_manifest_sha256": sha256_file(packet / "PACKET_MANIFEST.json")},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", type=Path, required=True)
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    result = validate(args.internal, args.packet)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
