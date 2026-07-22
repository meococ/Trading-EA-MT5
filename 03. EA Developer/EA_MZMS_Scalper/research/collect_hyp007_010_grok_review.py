#!/usr/bin/env python3
"""Fail-closed collector for HYP-007..010 Grok vision chunk reviews.

Writes validated_results_400.json and synthesis_input.json only when all 40
chunks pass runner/schema/image/coverage/order/hash checks. Does not invent
prose findings.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
EVIDENCE = RESEARCH / "evidence" / "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400"
CHUNKS_ROOT = EVIDENCE / "grok_review_chunks10"
CASEBOOK = EVIDENCE / "casebook_manifest.json"
SELECTION = EVIDENCE / "selection_manifest.json"
CAMPAIGN_METRICS = EVIDENCE / "campaign_metrics.json"
LIFECYCLE = EVIDENCE / "lifecycle_reconciliation.json"
CONTEXT = ROOT / ".context"
OUT_VALIDATED = EVIDENCE / "validated_results_400.json"
OUT_SYNTHESIS_INPUT = EVIDENCE / "synthesis_input.json"

TASK_PREFIX = "mzms-xau-007-010-vision"
SHORT_IDS = ("007", "008", "009", "010")
HYP_BY_SHORT = {
    "007": "HYP-MZMS-XAU-M5-007",
    "008": "HYP-MZMS-XAU-M5-008",
    "009": "HYP-MZMS-XAU-M5-009",
    "010": "HYP-MZMS-XAU-M5-010",
}
CHUNK_IDS = [f"chunk_{i:02d}" for i in range(1, 11)]
VALIDITY_BOUNDARY = "INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def expected_manifest(short_id: str, chunk_id: str) -> dict[str, Any]:
    path = CHUNKS_ROOT / short_id / chunk_id / "chunk_manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"missing chunk manifest: {path}")
    return load_json(path)


def expected_case_records(short_id: str, chunk_id: str) -> list[dict[str, Any]]:
    manifest = expected_manifest(short_id, chunk_id)
    rows = []
    for item in manifest["images"]:
        rows.append(
            {
                "case_id": str(item["case_id"]),
                "case_kind": str(item["case_kind"]),
                "position_id": item.get("position_id"),
                "sha256": str(item.get("sha256") or "").upper(),
                "absolute_path": str(item.get("absolute_path") or ""),
            }
        )
    return rows


def normalize_position(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("position_id cannot be bool")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value != int(value):
            raise ValueError(f"non-integer position_id: {value}")
        return int(value)
    text = str(value).strip()
    if text.lower() in {"", "null", "none", "nan"}:
        return None
    return int(float(text))


def short_from_hypothesis(hypothesis_id: str) -> str:
    return hypothesis_id.rsplit("-", 1)[-1]


def valid_candidate(summary_path: Path) -> tuple[bool, str, dict[str, Any] | None]:
    try:
        summary = load_json(summary_path)
    except Exception as exc:  # pragma: no cover - diagnostic path
        return False, f"unreadable_summary:{exc}", None

    validation = summary.get("structured_output_validation") or {}
    instance = validation.get("instance")
    if summary.get("success") is not True:
        return False, "runner_not_success", None
    if validation.get("passed") is not True or not isinstance(instance, dict):
        return False, "schema_not_passed", None

    hypothesis_id = str(instance.get("hypothesis_id") or "")
    chunk_id = str(instance.get("chunk_id") or "")
    if hypothesis_id not in HYP_BY_SHORT.values():
        return False, "bad_hypothesis", None
    if not re.fullmatch(r"chunk_\d{2}", chunk_id):
        return False, "bad_chunk", None
    short_id = short_from_hypothesis(hypothesis_id)
    if short_id not in SHORT_IDS:
        return False, "bad_short_id", None

    if instance.get("image_inspection_supported") is not True:
        return False, "image_inspection_not_supported", None

    coverage = instance.get("coverage") or {}
    if coverage != {
        "expected_images": 10,
        "images_opened": 10,
        "all_cases_reported": True,
    }:
        return False, "coverage_not_10_of_10", None

    cases = instance.get("cases") or []
    if not isinstance(cases, list) or len(cases) != 10:
        return False, "cases_not_exactly_10", None

    expected = expected_case_records(short_id, chunk_id)
    actual_ids = [str(row.get("case_id")) for row in cases]
    expected_ids = [row["case_id"] for row in expected]
    if actual_ids != expected_ids:
        return False, "case_order_or_id_mismatch", None

    for row, exp in zip(cases, expected):
        if row.get("image_opened") is not True:
            return False, f"case_image_not_opened:{exp['case_id']}", None
        if str(row.get("case_kind")) != exp["case_kind"]:
            return False, f"case_kind_mismatch:{exp['case_id']}", None
        try:
            actual_pos = normalize_position(row.get("position_id"))
        except Exception:
            return False, f"bad_position_id:{exp['case_id']}", None
        expected_pos = normalize_position(exp["position_id"])
        if actual_pos != expected_pos:
            return False, f"position_id_mismatch:{exp['case_id']}", None
        if exp["case_kind"] == "OFFLINE_NEAR_MISS_DIAGNOSTIC" and actual_pos is not None:
            return False, f"near_miss_position_not_null:{exp['case_id']}", None
        if exp["case_kind"] == "EXECUTED" and actual_pos is None:
            return False, f"executed_position_null:{exp['case_id']}", None

    # Hash check: request meta image hashes must match frozen chunk manifest.
    request_path = summary_path.parent / "grok-request.json"
    if not request_path.exists():
        return False, "missing_request_artifact", None
    try:
        request = load_json(request_path)
    except Exception as exc:  # pragma: no cover
        return False, f"unreadable_request:{exc}", None
    meta = request.get("meta") or {}
    meta_ids = [str(x) for x in meta.get("case_ids") or []]
    meta_sha = [str(x).upper() for x in meta.get("image_sha256") or []]
    if meta_ids != expected_ids:
        return False, "request_meta_case_ids_mismatch", None
    expected_sha = [row["sha256"] for row in expected]
    if meta_sha != expected_sha:
        return False, "request_meta_image_hash_mismatch", None
    manifest_path = CHUNKS_ROOT / short_id / chunk_id / "chunk_manifest.json"
    declared = str(meta.get("chunk_manifest_sha256") or "").upper()
    if declared and declared != sha256_file(manifest_path):
        return False, "chunk_manifest_hash_mismatch", None

    ranked = instance.get("ranked_mechanisms") or []
    if not isinstance(ranked, list) or not ranked:
        return False, "ranked_mechanisms_missing", None
    for item in ranked:
        cited = [str(x) for x in item.get("case_ids") or []]
        if not cited or any(case_id not in expected_ids for case_id in cited):
            return False, "ranked_mechanism_case_id_outside_chunk", None

    classification = instance.get("classification_summary") or {}
    required_class_keys = {
        "bad_entry_or_adverse_selection",
        "normal_stochastic_loss",
        "good_rejected_near_miss",
        "cadence_bottleneck",
    }
    if set(classification.keys()) < required_class_keys:
        return False, "classification_summary_incomplete", None
    for key in required_class_keys:
        values = classification.get(key) or []
        if any(str(case_id) not in expected_ids for case_id in values):
            return False, f"classification_case_outside_chunk:{key}", None

    return True, "ok", {
        "summary": summary,
        "instance": instance,
        "short_id": short_id,
        "hypothesis_id": hypothesis_id,
        "chunk_id": chunk_id,
        "expected_ids": expected_ids,
        "expected_sha": expected_sha,
    }


def discover() -> tuple[dict[str, dict[str, dict[str, Any]]], list[dict[str, Any]]]:
    accepted: dict[str, dict[str, dict[str, Any]]] = {
        short: {} for short in SHORT_IDS
    }
    audit: list[dict[str, Any]] = []
    for short in SHORT_IDS:
        for task_dir in sorted(CONTEXT.glob(f"{TASK_PREFIX}-{short}-c*")):
            summary_path = task_dir / "summary.json"
            if not summary_path.exists():
                audit.append(
                    {
                        "task_dir": str(task_dir),
                        "summary": str(summary_path),
                        "accepted": False,
                        "reason": "summary_missing",
                    }
                )
                continue
            ok, reason, payload = valid_candidate(summary_path)
            audit.append(
                {
                    "task_dir": str(task_dir),
                    "summary": str(summary_path),
                    "accepted": ok,
                    "reason": reason,
                    "hypothesis_id": None if payload is None else payload["hypothesis_id"],
                    "chunk_id": None if payload is None else payload["chunk_id"],
                }
            )
            if not ok or payload is None:
                continue
            if payload["short_id"] != short:
                continue
            chunk_id = payload["chunk_id"]
            current = accepted[short].get(chunk_id)
            if current is None or summary_path.stat().st_mtime > Path(
                current["summary_path"]
            ).stat().st_mtime:
                accepted[short][chunk_id] = {
                    "summary_path": str(summary_path),
                    "task_dir": str(task_dir),
                    "summary": payload["summary"],
                    "instance": payload["instance"],
                    "hypothesis_id": payload["hypothesis_id"],
                    "expected_ids": payload["expected_ids"],
                    "expected_sha": payload["expected_sha"],
                }
    return accepted, audit


def consolidate(
    accepted: dict[str, dict[str, dict[str, Any]]],
    audit: list[dict[str, Any]],
) -> dict[str, Any]:
    missing: dict[str, list[str]] = {}
    for short in SHORT_IDS:
        have = set(accepted[short])
        need = set(CHUNK_IDS)
        if have != need:
            missing[short] = sorted(need - have)
    if missing:
        raise RuntimeError(f"incomplete validated Grok coverage: {missing}")

    cases_by_hyp: dict[str, list[dict[str, Any]]] = {}
    chunk_findings: list[dict[str, Any]] = []
    evidence_counts: dict[str, dict[str, Any]] = {}
    runner_totals: dict[str, dict[str, Any]] = {}
    mechanism_counter: dict[str, Counter] = {
        hyp: Counter() for hyp in HYP_BY_SHORT.values()
    }
    class_counter: dict[str, Counter] = {
        hyp: Counter() for hyp in HYP_BY_SHORT.values()
    }

    for short in SHORT_IDS:
        hyp_id = HYP_BY_SHORT[short]
        cases: list[dict[str, Any]] = []
        elapsed = cost = 0.0
        turns = 0
        task_dirs: list[str] = []
        evidence_label_counts: Counter = Counter()
        confidence_counts: Counter = Counter()
        kind_counts: Counter = Counter()
        for chunk_id in CHUNK_IDS:
            item = accepted[short][chunk_id]
            instance = item["instance"]
            summary = item["summary"]
            chunk_cases = instance["cases"]
            cases.extend(chunk_cases)
            elapsed += float(summary.get("elapsed_seconds") or 0)
            cost += float(summary.get("total_cost_usd") or 0)
            turns += int(summary.get("num_turns") or 0)
            task_dirs.append(item["task_dir"])
            for case in chunk_cases:
                evidence_label_counts[str(case.get("evidence_label"))] += 1
                confidence_counts[str(case.get("confidence"))] += 1
                kind_counts[str(case.get("case_kind"))] += 1
            for mech in instance.get("ranked_mechanisms") or []:
                label = str(mech.get("label") or "").strip()
                if label:
                    mechanism_counter[hyp_id][label] += int(
                        mech.get("count_in_chunk") or len(mech.get("case_ids") or [])
                    )
            classification = instance.get("classification_summary") or {}
            for key, values in classification.items():
                class_counter[hyp_id][key] += len(values or [])
            chunk_findings.append(
                {
                    "hypothesis_id": hyp_id,
                    "short_id": short,
                    "chunk_id": chunk_id,
                    "summary_path": item["summary_path"],
                    "task_dir": item["task_dir"],
                    "chunk_verdict": instance.get("chunk_verdict"),
                    "limitations": instance.get("limitations") or [],
                    "ranked_mechanisms": instance.get("ranked_mechanisms") or [],
                    "classification_summary": classification,
                    "fresh_hypothesis_candidates": instance.get(
                        "fresh_hypothesis_candidates"
                    )
                    or [],
                    "case_ids": [str(c["case_id"]) for c in chunk_cases],
                }
            )
        if len(cases) != 100:
            raise RuntimeError(f"{hyp_id} expected 100 cases, got {len(cases)}")
        ids = [str(c["case_id"]) for c in cases]
        if len(set(ids)) != 100:
            raise RuntimeError(f"{hyp_id} case IDs not unique")
        expected_all = []
        for chunk_id in CHUNK_IDS:
            expected_all.extend(
                [row["case_id"] for row in expected_case_records(short, chunk_id)]
            )
        if ids != expected_all:
            raise RuntimeError(f"{hyp_id} consolidated case order mismatch")
        cases_by_hyp[hyp_id] = cases
        evidence_counts[hyp_id] = {
            "validated_images": 100,
            "validated_chunks": 10,
            "case_kind_counts": dict(sorted(kind_counts.items())),
            "evidence_label_counts": dict(sorted(evidence_label_counts.items())),
            "confidence_counts": dict(sorted(confidence_counts.items())),
            "ranked_mechanism_label_counts_nonexclusive": dict(
                mechanism_counter[hyp_id].most_common()
            ),
            "classification_case_counts_nonexclusive": dict(
                sorted(class_counter[hyp_id].items())
            ),
        }
        runner_totals[hyp_id] = {
            "validated_images": 100,
            "validated_chunks": 10,
            "elapsed_seconds": round(elapsed, 3),
            "total_cost_usd": round(cost, 6),
            "num_turns": turns,
            "task_dirs": task_dirs,
        }

    campaign = load_json(CAMPAIGN_METRICS) if CAMPAIGN_METRICS.exists() else {}
    return {
        "schema_version": "mzms_hyp007_010_grok_review_validated_400.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "campaign": "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400",
        "validity_boundary": VALIDITY_BOUNDARY,
        "economic_authority": "DIAGNOSTIC_ONLY",
        "promotion_blocked": True,
        "post_hoc_rescue_blocked": True,
        "coverage": runner_totals,
        "evidence_counts": evidence_counts,
        "chunk_findings": chunk_findings,
        "cases": cases_by_hyp,
        "bindings": {
            "casebook": str(CASEBOOK),
            "casebook_sha256": sha256_file(CASEBOOK) if CASEBOOK.exists() else None,
            "selection": str(SELECTION),
            "selection_sha256": sha256_file(SELECTION) if SELECTION.exists() else None,
            "campaign_metrics": str(CAMPAIGN_METRICS),
            "campaign_metrics_sha256": (
                sha256_file(CAMPAIGN_METRICS) if CAMPAIGN_METRICS.exists() else None
            ),
            "lifecycle_reconciliation": str(LIFECYCLE),
            "lifecycle_reconciliation_sha256": (
                sha256_file(LIFECYCLE) if LIFECYCLE.exists() else None
            ),
            "chunks_root": str(CHUNKS_ROOT),
        },
        "campaign_metrics_snapshot": campaign.get("hypotheses", {}),
        "discovery_audit": audit,
        "notes": [
            "Collector does not invent prose findings.",
            "Validated packet is machine-readable only; owner prose comes from a separate synthesis Grok call.",
            "98% history quality remains diagnostic-only and cannot promote.",
        ],
    }


def build_synthesis_input(packet: dict[str, Any]) -> dict[str, Any]:
    """Machine-readable synthesis input only; no invented prose."""
    return {
        "schema_version": "mzms_hyp007_010_grok_review_synthesis_input.v1",
        "created_at_utc": packet["created_at_utc"],
        "campaign": packet["campaign"],
        "validity_boundary": packet["validity_boundary"],
        "economic_authority": packet["economic_authority"],
        "promotion_blocked": True,
        "post_hoc_rescue_blocked": True,
        "per_hypothesis_evidence_counts": packet["evidence_counts"],
        "coverage": packet["coverage"],
        "chunk_findings": packet["chunk_findings"],
        "campaign_metrics_snapshot": packet["campaign_metrics_snapshot"],
        "bindings": packet["bindings"],
        "case_id_index": {
            hyp_id: [str(case["case_id"]) for case in cases]
            for hyp_id, cases in packet["cases"].items()
        },
        "required_synthesis_rules": [
            "Compare all four mechanisms using validated findings + campaign metrics only.",
            "Label conclusions OBSERVED/STRONG_INFERENCE/HYPOTHESIS/UNKNOWN.",
            "Economic and cadence verdicts are diagnostic shape only at 98%<99%.",
            "Never post-hoc rescue HYP-007..010 via thresholds/session/year/direction/BE.",
            "History-quality-invalid results cannot become promotion evidence.",
            "At most four genuinely new prereg candidates, or recommend stop.",
            "Owner-facing Markdown must be Vietnamese.",
        ],
    }


def status_report(accepted: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    return {
        short: {
            "validated_chunks": len(accepted[short]),
            "missing_chunks": sorted(set(CHUNK_IDS) - set(accepted[short])),
            "present_chunks": sorted(accepted[short]),
        }
        for short in SHORT_IDS
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect and validate 40 HYP-007..010 Grok vision chunks"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate coverage without writing output packets",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print per-hypothesis accepted chunk status and exit 0 even if incomplete",
    )
    args = parser.parse_args()
    accepted, audit = discover()
    if args.status:
        report = status_report(accepted)
        print(json.dumps(report, indent=2))
        total = sum(len(v) for v in accepted.values())
        print(f"STATUS validated_chunks={total}/40")
        return 0
    try:
        packet = consolidate(accepted, audit)
    except RuntimeError as exc:
        report = status_report(accepted)
        print(json.dumps(report, indent=2))
        print(f"COLLECT_FAIL {exc}")
        return 2
    synthesis_input = build_synthesis_input(packet)
    if not args.check_only:
        OUT_VALIDATED.write_text(
            json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        OUT_SYNTHESIS_INPUT.write_text(
            json.dumps(synthesis_input, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    print(
        "GROK_REVIEW_400_OK "
        + " ".join(
            f"{short}={len(accepted[short])}"
            for short in SHORT_IDS
        )
        + " total=40"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
