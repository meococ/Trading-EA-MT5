#!/usr/bin/env python3
"""Extract outcome-blind CME 6E full-break-bar transition features."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence


WORKSPACE = Path(__file__).resolve().parents[3]
MODULE_PATH = Path(__file__).resolve()
PACKAGE = MODULE_PATH.parents[1]
DATA_ROOT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "databento"
    / "cme_6e_breakbar_transition_design"
)
PLAN_PATH = DATA_ROOT / "source_plan.json"
MANIFEST_PATH = DATA_ROOT / "download_manifest.json"
VALIDATION_PATH = DATA_ROOT / "validation_receipt.json"
RAW_ROOT = DATA_ROOT / "raw"
OUTPUT_PATH = DATA_ROOT / "book_transition_features_source_only.csv"
RECEIPT_PATH = DATA_ROOT / "book_transition_feature_receipt.json"
FOUNDATION_PATH = PACKAGE / "research" / "extract_cme6e_raw_break_features.py"
ACQUISITION_PATH = PACKAGE / "research" / "acquire_cme6e_breakbar_transition_design.py"

PLAN_ID = "C57B0AF9CAAB52095629C4D6F3BE449EA23629E02F9FA30C4F54C5CC164A1D1C"
PLAN_SHA256 = "BF478C4FF9B181E0BC7C38E55C9613D69B44DBF348CBC351EC0909583E25D7F6"
FOUNDATION_SHA256 = "34A668CF89FEB9ED5A0D74E41E35B6C6B19E810E5BF6CC02AA6F36EE4FDBC4BB"
ACQUISITION_SHA256 = "3814D025278F2F7FEE0DB42F4E5CF8FEFBB94D9136C396D0F3832E0C74BB2F4C"
EXPECTED_ROWS = 565
EXPECTED_BILLABLE = 561
EXPECTED_METADATA_EMPTY = 4
MIN_CAUSAL_RECORDS = 30
MIN_EARLY_RECORDS = 5
MIN_LATE_RECORDS = 5
MIN_FINAL30_RECORDS = 3
MAX_SPREAD_TICKS = 2.0
MAX_STALENESS_MS = 10_000.0
SECOND_NS = 1_000_000_000

FIELDS = [
    "position_id",
    "direction",
    "break_bar_open",
    "actual_decision",
    "start",
    "end",
    "duration_seconds",
    "filename",
    "source_status",
    "causal_records",
    "records_early_60s",
    "records_late_60s",
    "records_final_30s",
    "aligned_imbalance_last",
    "aligned_imbalance_median_early60",
    "aligned_imbalance_median_late60",
    "aligned_imbalance_transition",
    "aligned_persistence_full",
    "aligned_persistence_final30",
    "spread_ticks_last",
    "staleness_ms",
    "book_transition_score",
    "quality_eligible",
    "quality_reason",
]


class FeatureError(RuntimeError):
    """Fail-closed source-feature error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FeatureError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FeatureError(f"expected JSON object: {path}")
    return value


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def _load_foundation():
    if sha256_file(FOUNDATION_PATH) != FOUNDATION_SHA256:
        raise FeatureError("fixed-point feature foundation SHA mismatch")
    spec = importlib.util.spec_from_file_location("raw_break_feature_foundation", FOUNDATION_PATH)
    if spec is None or spec.loader is None:
        raise FeatureError("cannot load fixed-point feature foundation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


foundation = _load_foundation()


def _iso_ns(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(parsed.timestamp() * SECOND_NS)


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _observation(message: Any) -> dict[str, float] | None:
    return foundation._observation(message)


def quality_eligibility(row: dict[str, Any]) -> tuple[bool, str]:
    if row.get("source_status") != "nonempty":
        return False, str(row.get("source_status", "SOURCE_UNAVAILABLE")).upper()
    if int(row.get("causal_records", 0)) < MIN_CAUSAL_RECORDS:
        return False, "INSUFFICIENT_CAUSAL_RECORDS"
    if int(row.get("records_early_60s", 0)) < MIN_EARLY_RECORDS:
        return False, "INSUFFICIENT_EARLY_RECORDS"
    if int(row.get("records_late_60s", 0)) < MIN_LATE_RECORDS:
        return False, "INSUFFICIENT_LATE_RECORDS"
    if int(row.get("records_final_30s", 0)) < MIN_FINAL30_RECORDS:
        return False, "INSUFFICIENT_FINAL30_RECORDS"
    spread = row.get("spread_ticks_last")
    if not _finite(spread) or float(spread) > MAX_SPREAD_TICKS:
        return False, "WIDE_OR_INVALID_SPREAD"
    staleness = row.get("staleness_ms")
    if not _finite(staleness) or float(staleness) > MAX_STALENESS_MS:
        return False, "STALE_BOOK"
    if not _finite(row.get("book_transition_score")):
        return False, "INVALID_SCORE"
    return True, "PASS"


def compute_feature_row(
    request: dict[str, Any], messages: Iterable[Any]
) -> dict[str, Any]:
    start_ns = _iso_ns(str(request["start"]))
    end_ns = _iso_ns(str(request["end"]))
    direction_sign = 1.0 if request["direction"] == "BUY" else -1.0
    observations: list[dict[str, float]] = []
    for message in messages:
        observation = _observation(message)
        if observation is None:
            continue
        if observation["ts_event"] < start_ns or observation["ts_recv"] < start_ns:
            continue
        if observation["ts_event"] >= end_ns or observation["ts_recv"] >= end_ns:
            continue
        observations.append(observation)
    observations.sort(key=lambda item: (item["ts_recv"], item["ts_event"]))
    early = [item for item in observations if item["ts_recv"] < start_ns + 60 * SECOND_NS]
    late = [item for item in observations if item["ts_recv"] >= end_ns - 60 * SECOND_NS]
    final30 = [item for item in observations if item["ts_recv"] >= end_ns - 30 * SECOND_NS]
    row: dict[str, Any] = {field: request.get(field) for field in FIELDS}
    row.update(
        {
            "position_id": str(request["position_id"]),
            "source_status": "nonempty",
            "causal_records": len(observations),
            "records_early_60s": len(early),
            "records_late_60s": len(late),
            "records_final_30s": len(final30),
            "aligned_imbalance_last": None,
            "aligned_imbalance_median_early60": None,
            "aligned_imbalance_median_late60": None,
            "aligned_imbalance_transition": None,
            "aligned_persistence_full": None,
            "aligned_persistence_final30": None,
            "spread_ticks_last": None,
            "staleness_ms": None,
            "book_transition_score": None,
        }
    )
    if observations and early and late and final30:
        aligned = [direction_sign * item["imbalance"] for item in observations]
        early_values = [direction_sign * item["imbalance"] for item in early]
        late_values = [direction_sign * item["imbalance"] for item in late]
        final_values = [direction_sign * item["imbalance"] for item in final30]
        early_median = float(median(early_values))
        late_median = float(median(late_values))
        transition = late_median - early_median
        persistence = sum(value > 0 for value in aligned) / len(aligned)
        final_persistence = sum(value > 0 for value in final_values) / len(final_values)
        score = (
            0.50 * max(-1.0, min(1.0, transition))
            + 0.25 * late_median
            + 0.25 * (2.0 * persistence - 1.0)
        )
        row.update(
            {
                "aligned_imbalance_last": aligned[-1],
                "aligned_imbalance_median_early60": early_median,
                "aligned_imbalance_median_late60": late_median,
                "aligned_imbalance_transition": transition,
                "aligned_persistence_full": persistence,
                "aligned_persistence_final30": final_persistence,
                "spread_ticks_last": observations[-1]["spread_ticks"],
                "staleness_ms": (end_ns - observations[-1]["ts_recv"]) / 1_000_000.0,
                "book_transition_score": score,
            }
        )
    eligible, reason = quality_eligibility(row)
    row["quality_eligible"] = eligible
    row["quality_reason"] = reason
    return row


def _unavailable_row(request: dict[str, Any], status: str) -> dict[str, Any]:
    row = {field: None for field in FIELDS}
    for field in (
        "position_id",
        "direction",
        "break_bar_open",
        "actual_decision",
        "start",
        "end",
        "duration_seconds",
        "filename",
    ):
        row[field] = request[field]
    row["position_id"] = str(row["position_id"])
    row["source_status"] = status
    row["causal_records"] = 0
    row["records_early_60s"] = 0
    row["records_late_60s"] = 0
    row["records_final_30s"] = 0
    row["quality_eligible"] = False
    row["quality_reason"] = status.upper()
    return row


def load_source_contract() -> dict[str, Any]:
    if sha256_file(PLAN_PATH) != PLAN_SHA256:
        raise FeatureError("source plan SHA mismatch")
    if sha256_file(ACQUISITION_PATH) != ACQUISITION_SHA256:
        raise FeatureError("acquisition tool SHA mismatch")
    plan = load_json(PLAN_PATH)
    manifest = load_json(MANIFEST_PATH)
    receipt = load_json(VALIDATION_PATH)
    if plan.get("plan_id") != PLAN_ID or manifest.get("plan_id") != PLAN_ID:
        raise FeatureError("source identity mismatch")
    if receipt.get("plan_id") != PLAN_ID:
        raise FeatureError("validation receipt plan mismatch")
    if receipt.get("status") != "RAW_DESIGN_SOURCE_HASH_VALIDATION_PASS":
        raise FeatureError("raw source validation did not pass")
    if receipt.get("source_plan_sha256") != PLAN_SHA256:
        raise FeatureError("validation receipt source-plan SHA mismatch")
    if receipt.get("manifest_sha256") != sha256_file(MANIFEST_PATH):
        raise FeatureError("validation receipt manifest SHA mismatch")
    if receipt.get("response_files") != EXPECTED_BILLABLE:
        raise FeatureError("validated response coverage mismatch")
    if receipt.get("planned_metadata_empty_windows") != EXPECTED_METADATA_EMPTY:
        raise FeatureError("metadata-empty coverage mismatch")
    if receipt.get("outcome_fields_used") is not False:
        raise FeatureError("source validation is not outcome-blind")
    if receipt.get("sealed_oos_opened") is not False:
        raise FeatureError("source validation opened prior-hypothesis outcomes")
    downloads = manifest.get("downloads")
    if not isinstance(downloads, list) or len(downloads) != EXPECTED_BILLABLE:
        raise FeatureError("download manifest coverage mismatch")
    for item in downloads:
        path = RAW_ROOT / str(item.get("filename", ""))
        if not path.is_file():
            raise FeatureError(f"raw response missing: {path}")
        if path.stat().st_size != int(item.get("bytes", -1)):
            raise FeatureError(f"raw response byte mismatch: {path}")
        if sha256_file(path) != str(item.get("sha256", "")):
            raise FeatureError(f"raw response SHA mismatch: {path}")
    return {"plan": plan, "manifest": manifest, "receipt": receipt}


def extract_features(contract: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        import databento as db
    except ImportError as exc:
        raise FeatureError("Databento SDK is required for feature extraction") from exc
    plan = contract["plan"]
    downloads = {str(item["filename"]): item for item in contract["manifest"]["downloads"]}
    rows: list[dict[str, Any]] = []
    for request in plan["requests"]:
        download = downloads.get(str(request["filename"]))
        if not isinstance(download, dict):
            raise FeatureError(f"manifest response missing: {request['filename']}")
        if download.get("source_empty") is True:
            rows.append(_unavailable_row(request, "source_empty"))
            continue
        path = RAW_ROOT / str(request["filename"])
        try:
            rows.append(compute_feature_row(request, db.DBNStore.from_file(path)))
        except Exception as exc:
            raise FeatureError(f"feature decode failed for {path}: {exc}") from exc
    for request in plan["metadata_empty_windows"]:
        rows.append(_unavailable_row(request, "metadata_empty"))
    rows.sort(key=lambda item: (str(item["end"]), int(item["position_id"])))
    if len(rows) != EXPECTED_ROWS or len({row["position_id"] for row in rows}) != EXPECTED_ROWS:
        raise FeatureError("source-only feature coverage mismatch")
    return rows


def write_csv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    partial = path.with_suffix(path.suffix + ".partial")
    with partial.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(partial, path)


def build_receipt(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible_scores = [
        float(row["book_transition_score"])
        for row in rows
        if row.get("quality_eligible") is True
    ]
    if not eligible_scores:
        raise FeatureError("no quality-eligible source rows")
    reasons = Counter(str(row["quality_reason"]) for row in rows)
    return {
        "schema_version": "cme6e_breakbar_transition_feature_receipt.v1",
        "generated_at_utc": utc_now(),
        "status": "SOURCE_ONLY_FEATURE_EXTRACTION_PASS",
        "candidate_identity": "CME_GLOBEX_6E_MBP10_RAW_BREAK_BREAKBAR_TRANSITION",
        "plan_id": PLAN_ID,
        "source_plan_sha256": PLAN_SHA256,
        "download_manifest_sha256": sha256_file(MANIFEST_PATH),
        "raw_validation_receipt_sha256": sha256_file(VALIDATION_PATH),
        "feature_foundation_sha256": FOUNDATION_SHA256,
        "extractor_sha256": sha256_file(MODULE_PATH),
        "output_path": str(OUTPUT_PATH.relative_to(WORKSPACE)).replace("\\", "/"),
        "output_sha256": sha256_file(OUTPUT_PATH),
        "rows": len(rows),
        "quality_eligible_rows": len(eligible_scores),
        "quality_reason_counts": dict(sorted(reasons.items())),
        "source_only_median_score": float(median(eligible_scores)),
        "score_formula": "0.50*clip(late60_median-early60_median,-1,1)+0.25*late60_median+0.25*(2*full_bar_positive_persistence-1)",
        "outcome_fields_used": False,
        "outcomes_opened": False,
        "prior_hypothesis_oos_opened": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    del argv
    try:
        contract = load_source_contract()
        rows = extract_features(contract)
        write_csv_atomic(OUTPUT_PATH, rows)
        receipt = build_receipt(rows)
        write_json_atomic(RECEIPT_PATH, receipt)
        print(
            "CME6E_BREAKBAR_FEATURES_OK "
            f"rows={receipt['rows']} quality={receipt['quality_eligible_rows']} "
            f"median_score={receipt['source_only_median_score']:.12f} "
            "outcomes_opened=false"
        )
        print(f"output={OUTPUT_PATH}")
        print(f"receipt={RECEIPT_PATH}")
        return 0
    except FeatureError as exc:
        print(f"CME6E_BREAKBAR_FEATURES_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
