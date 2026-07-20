#!/usr/bin/env python3
"""Evaluate the frozen two-reviewer label gate without loading outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from casebook_contract import ALLOWED_LABELS, SOURCE_PATH, STUDY_ID, load_json, sha256_file
from validate_casebook import FORBIDDEN_PACKET_HEADER_TOKENS, validate


MIN_COMPARABLE_COVERAGE = 0.80
MIN_RESOLVED_COVERAGE = 0.60


def _load_overlay(path: Path, expected_cases: dict[str, dict[str, Any]],
                  internal_sha256: str) -> tuple[dict[str, dict[str, str]], list[str]]:
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        headers = reader.fieldnames or []
        rows = list(reader)
    if any(token in h.lower() for token in FORBIDDEN_PACKET_HEADER_TOKENS for h in headers):
        errors.append("overlay contains protected direction/category/EA/outcome header")
    if "case_id" not in headers or "setup_label" not in headers:
        errors.append("overlay missing case_id/setup_label")
    ids = [r.get("case_id", "") for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate case_id in overlay")
    expected_ids = set(expected_cases)
    if set(ids) != expected_ids or len(rows) != len(expected_ids):
        errors.append("overlay does not have complete exact case coverage")
    for row in rows:
        case_id = row.get("case_id", "")
        expected_case = expected_cases.get(case_id, {})
        bindings = {
            "schema_version": "fvg_reviewer_overlay.v2",
            "study_id": STUDY_ID,
            "source_sha256": sha256_file(SOURCE_PATH),
            "internal_casebook_sha256": internal_sha256,
            "event_sha256": expected_case.get("event_sha256", "__missing__"),
            "chart": f"charts/{case_id}.png",
        }
        for key, wanted in bindings.items():
            if row.get(key, "") != wanted:
                errors.append(f"row binding mismatch for {case_id}: {key}")
        label = row.get("setup_label", "").strip().upper()
        if label not in ALLOWED_LABELS:
            errors.append(f"invalid/blank label for {row.get('case_id')}: {label!r}")
        row["setup_label"] = label
    return {r.get("case_id", ""): r for r in rows}, errors


def _qualification(attestation_path: Path, expected_reviewer_id: str) -> tuple[bool, dict[str, Any], dict[str, str], list[str]]:
    errors: list[str] = []
    att = load_json(attestation_path)
    try:
        years = float(att.get("ict_fvg_experience_years", ""))
        months = float(att.get("verified_live_history_months", "") or 0)
        trades = int(att.get("journaled_trade_count", "") or 0)
    except (TypeError, ValueError):
        years, months, trades = 0.0, 0.0, 0
        errors.append("qualification numeric fields are invalid")
    qualified = years >= 3 and (months >= 24 or trades >= 500)
    if not qualified:
        errors.append("reviewer qualification below 3 years plus 24 live months or 500 journaled trades")
    for key in ("reviewer_name", "qualification_evidence_reference", "signed_name", "signed_date_utc"):
        if not str(att.get(key, "")).strip():
            errors.append(f"attestation field blank: {key}")
    for key in ("attests_independent_review_without_outcomes", "attests_no_second_reviewer_labels_seen"):
        if att.get(key) is not True:
            errors.append(f"attestation not affirmed: {key}")
    if att.get("schema_version") != "fvg_reviewer_attestation.v2":
        errors.append("attestation schema mismatch")
    if att.get("study_id") != STUDY_ID or att.get("reviewer_id") != expected_reviewer_id:
        errors.append("attestation study/reviewer identity mismatch")
    identity = {
        "reviewer_id": str(att.get("reviewer_id", "")).strip(),
        "reviewer_name": str(att.get("reviewer_name", "")).strip().casefold(),
        "signed_name": str(att.get("signed_name", "")).strip().casefold(),
        "qualification_evidence_reference": str(att.get("qualification_evidence_reference", "")).strip().casefold(),
    }
    return qualified and not errors, {"years": years, "verified_live_months": months,
                                     "journaled_trades": trades, "role": "pro_trader" if qualified else "experienced_reviewer"}, identity, errors


def cohen_kappa(labels_a: list[str], labels_b: list[str]) -> float | None:
    if len(labels_a) != len(labels_b) or not labels_a:
        return None
    n = len(labels_a)
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    values = ("ACCEPT", "REJECT")
    expected = sum((labels_a.count(v) / n) * (labels_b.count(v) / n) for v in values)
    if expected >= 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def reliability_coverage(comparable_n: int, resolved_n: int, total_n: int) -> dict[str, Any]:
    comparable_ratio = comparable_n / total_n if total_n else 0.0
    resolved_ratio = resolved_n / total_n if total_n else 0.0
    return {
        "comparable_n": comparable_n,
        "comparable_ratio": comparable_ratio,
        "comparable_floor": MIN_COMPARABLE_COVERAGE,
        "comparable_pass": comparable_ratio >= MIN_COMPARABLE_COVERAGE,
        "resolved_n": resolved_n,
        "resolved_ratio": resolved_ratio,
        "resolved_floor": MIN_RESOLVED_COVERAGE,
        "resolved_pass": resolved_ratio >= MIN_RESOLVED_COVERAGE,
    }


def run_gate(internal_path: Path, packet: Path, reviewer_1: Path, reviewer_2: Path,
             attestation_1: Path, attestation_2: Path) -> dict[str, Any]:
    errors: list[str] = []
    baseline = validate(internal_path, packet)
    if baseline["status"] != "PASS":
        errors.append("immutable blank packet baseline validation failed")
    internal = load_json(internal_path)
    cases = {r["case_id"]: r for r in internal.get("cases", [])}
    expected = set(cases)
    internal_sha256 = sha256_file(internal_path)
    a, e1 = _load_overlay(reviewer_1, cases, internal_sha256)
    b, e2 = _load_overlay(reviewer_2, cases, internal_sha256)
    q1, q1_info, identity_1, qe1 = _qualification(attestation_1, "REVIEWER_1")
    q2, q2_info, identity_2, qe2 = _qualification(attestation_2, "REVIEWER_2")
    errors.extend([f"reviewer_1: {e}" for e in e1 + qe1])
    errors.extend([f"reviewer_2: {e}" for e in e2 + qe2])
    distinct_reviewers = all(
        identity_1[key] and identity_2[key] and identity_1[key] != identity_2[key]
        for key in ("reviewer_id", "reviewer_name", "signed_name", "qualification_evidence_reference")
    )
    if not distinct_reviewers:
        errors.append("reviewer identities/evidence are not independently distinct")

    comparable = [cid for cid in sorted(expected)
                  if a.get(cid, {}).get("setup_label") in {"ACCEPT", "REJECT"}
                  and b.get(cid, {}).get("setup_label") in {"ACCEPT", "REJECT"}]
    kappa = cohen_kappa([a[c]["setup_label"] for c in comparable], [b[c]["setup_label"] for c in comparable])
    kappa_pass = kappa is not None and kappa >= 0.70
    if not kappa_pass:
        errors.append(f"Cohen kappa below 0.70 or not estimable: {kappa}")

    resolved = [cid for cid in comparable if a[cid]["setup_label"] == b[cid]["setup_label"]]
    coverage = reliability_coverage(len(comparable), len(resolved), len(expected))
    if not coverage["comparable_pass"]:
        errors.append(f"comparable coverage below {MIN_COMPARABLE_COVERAGE:.0%}: {coverage['comparable_ratio']:.3f}")
    if not coverage["resolved_pass"]:
        errors.append(f"resolved coverage below {MIN_RESOLVED_COVERAGE:.0%}: {coverage['resolved_ratio']:.3f}")
    human_accept = {cid for cid in resolved if a[cid]["setup_label"] == "ACCEPT"}
    ea_accept = {cid for cid in resolved if bool(cases[cid].get("ea_accept"))}
    union = human_accept | ea_accept
    jaccard = len(human_accept & ea_accept) / len(union) if union else 1.0
    disagreement = (sum((cid in human_accept) != (cid in ea_accept) for cid in resolved) / len(resolved)) if resolved else 0.0
    distinct_pass = jaccard <= 0.70 or disagreement >= 0.20
    if not distinct_pass:
        errors.append(f"material distinctness failed: jaccard={jaccard:.6f}, disagreement={disagreement:.6f}")

    gate_pass = (baseline["status"] == "PASS" and not e1 and not e2 and q1 and q2
                 and distinct_reviewers and coverage["comparable_pass"] and coverage["resolved_pass"]
                 and kappa_pass and distinct_pass)
    return {
        "schema_version": "fvg_human_label_gate.v2",
        "study_id": STUDY_ID,
        "status": "PASS" if gate_pass else "FAIL",
        "outcomes_loaded": False,
        "outcome_join_performed": False,
        "complete_coverage": len(a) == len(b) == len(expected) == 400 and not e1 and not e2,
        "allowed_labels": sorted(ALLOWED_LABELS),
        "reviewer_qualification": {"distinct_reviewers": distinct_reviewers,
                                   "reviewer_1": {"pass": q1, **q1_info}, "reviewer_2": {"pass": q2, **q2_info}},
        "reliability": {**coverage, "cohen_kappa": kappa, "kappa_floor": 0.70, "kappa_pass": kappa_pass,
                        "pass": coverage["comparable_pass"] and coverage["resolved_pass"] and kappa_pass},
        "material_distinctness": {"resolved_n": len(resolved), "human_accept_n": len(human_accept),
                                     "ea_accept_n": len(ea_accept), "accept_set_jaccard": jaccard,
                                     "jaccard_ceiling": 0.70, "consensus_vs_ea_disagreement": disagreement,
                                     "disagreement_floor": 0.20, "pass": distinct_pass},
        "bindings": {"internal_casebook_sha256": sha256_file(internal_path),
                     "packet_manifest_sha256": sha256_file(packet / "PACKET_MANIFEST.json"),
                     "reviewer_1_sha256": sha256_file(reviewer_1), "reviewer_2_sha256": sha256_file(reviewer_2),
                     "attestation_1_sha256": sha256_file(attestation_1), "attestation_2_sha256": sha256_file(attestation_2)},
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", type=Path, required=True)
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--reviewer-1", type=Path, required=True)
    ap.add_argument("--reviewer-2", type=Path, required=True)
    ap.add_argument("--attestation-1", type=Path, required=True)
    ap.add_argument("--attestation-2", type=Path, required=True)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    report = run_gate(args.internal, args.packet, args.reviewer_1, args.reviewer_2,
                      args.attestation_1, args.attestation_2)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
