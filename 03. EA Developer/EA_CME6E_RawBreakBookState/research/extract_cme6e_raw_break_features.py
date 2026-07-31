#!/usr/bin/env python3
"""Extract outcome-blind CME 6E MBP-10 features for raw BREAK DESIGN decisions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "cme6e_raw_break_book_features.v1"
RECEIPT_SCHEMA_VERSION = "cme6e_raw_break_book_feature_receipt.v1"
TICK_SIZE = 0.00005
LAST_WINDOW_NS = 30_000_000_000
PRIOR_WINDOW_NS = 60_000_000_000
MIN_CAUSAL_RECORDS = 10
MIN_LAST30_RECORDS = 5
MAX_SPREAD_TICKS = 2.0
MAX_STALENESS_MS = 10_000.0

WORKSPACE = Path(__file__).resolve().parents[3]
MODULE_PATH = Path(__file__).resolve()
DATA_ROOT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "databento"
    / "cme_6e_raw_break_design"
)
SOURCE_PLAN_PATH = DATA_ROOT / "source_plan.json"
MANIFEST_PATH = DATA_ROOT / "download_manifest.json"
VALIDATION_RECEIPT_PATH = DATA_ROOT / "validation_receipt.json"
EXECUTION_PATH = DATA_ROOT / "execution_authorization.json"
STDERR_PATH = DATA_ROOT / "acquisition.stderr.log"
RAW_ROOT = DATA_ROOT / "raw"
DEFAULT_OUTPUT = DATA_ROOT / "book_features_source_only.csv"
DEFAULT_RECEIPT = DATA_ROOT / "book_features_source_only_receipt.json"

SOURCE_PLAN_SHA256 = "B780B7A4AD0F0C8B7CDF6A109DE41754C5F9CD88856D464085EE69513A1E24D5"
MANIFEST_SHA256 = "7C83A964551B7A1F82E483173879A4468A076DA1D2D823E8C8F99A8A3034D38F"
VALIDATION_RECEIPT_SHA256 = (
    "DC383862412E22652FBAA48365CB64D2453200C2727EF1B23AEFFEDD3D57FFFC"
)
EXECUTION_SHA256 = "6DB132CFD14BDFC8072AB0E2E5FA0F1176EAAC3181A7DFED3DEAE1E7952BACA5"
STDERR_SHA256 = "7ECFE1DAFA60E287985341177EB4AA1BC998F178870C91C14302ECAB5D8515B1"
PLAN_ID = "1825DC77A35F2794051BD83E5A35ED87C8952049FB08B47BEA1AF34E1802D98F"
EXECUTION_ID = "8AC05E8CEF942F62BD47C144BF529A6DA48A9F727298CCCCDC127E65303B4536"

FIELDS = [
    "position_id",
    "direction",
    "start",
    "end",
    "filename",
    "source_status",
    "degraded_source_date",
    "causal_records",
    "records_last_30s",
    "records_prior_30s",
    "aligned_imbalance_last",
    "aligned_imbalance_median_30s",
    "aligned_imbalance_change_30s",
    "aligned_persistence_30s",
    "spread_ticks_last",
    "staleness_ms",
    "book_alignment_score",
    "quality_eligible",
    "quality_reason",
]


class FeatureError(RuntimeError):
    """Fail-closed source feature error."""


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
        raise FeatureError(f"expected JSON object in {path}")
    return value


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def _verify_file(path: Path, expected_sha256: str) -> None:
    if not path.is_file():
        raise FeatureError(f"bound source artifact is absent: {path}")
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise FeatureError(
            f"bound source SHA mismatch for {path}: expected {expected_sha256}, got {actual}"
        )


def load_source_contract() -> dict[str, Any]:
    bindings = (
        (SOURCE_PLAN_PATH, SOURCE_PLAN_SHA256),
        (MANIFEST_PATH, MANIFEST_SHA256),
        (VALIDATION_RECEIPT_PATH, VALIDATION_RECEIPT_SHA256),
        (EXECUTION_PATH, EXECUTION_SHA256),
        (STDERR_PATH, STDERR_SHA256),
    )
    for path, expected in bindings:
        _verify_file(path, expected)
    plan = load_json(SOURCE_PLAN_PATH)
    manifest = load_json(MANIFEST_PATH)
    receipt = load_json(VALIDATION_RECEIPT_PATH)
    execution = load_json(EXECUTION_PATH)
    if plan.get("plan_id") != PLAN_ID or manifest.get("plan_id") != PLAN_ID:
        raise FeatureError("source plan identity mismatch")
    if execution.get("execution_id") != EXECUTION_ID:
        raise FeatureError("execution identity mismatch")
    if receipt.get("status") != "RAW_DESIGN_SOURCE_HASH_VALIDATION_PASS":
        raise FeatureError("raw source validation receipt is not PASS")
    if receipt.get("manifest_sha256") != MANIFEST_SHA256:
        raise FeatureError("validation receipt manifest binding mismatch")
    if receipt.get("outcome_fields_used") is not False:
        raise FeatureError("source validation receipt is not outcome-blind")
    if receipt.get("sealed_oos_opened") is not False:
        raise FeatureError("source validation receipt opened sealed OOS")
    if len(plan.get("requests", [])) != 541:
        raise FeatureError("source plan billable request coverage mismatch")
    if len(plan.get("metadata_empty_windows", [])) != 6:
        raise FeatureError("source plan metadata-empty coverage mismatch")
    if len(manifest.get("downloads", [])) != 541:
        raise FeatureError("download manifest response coverage mismatch")
    degraded_dates = set(
        re.findall(r"(\d{4}-\d{2}-\d{2}) \(degraded\)", STDERR_PATH.read_text("utf-8"))
    )
    if degraded_dates != {
        "2019-01-15",
        "2019-02-22",
        "2020-02-27",
        "2020-06-30",
        "2020-07-01",
    }:
        raise FeatureError("unexpected degraded-source date set")
    return {
        "plan": plan,
        "manifest": manifest,
        "receipt": receipt,
        "execution": execution,
        "degraded_dates": degraded_dates,
    }


def _iso_ns(value: str) -> int:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return int(parsed.timestamp() * 1_000_000_000)


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _normalize_price(value: Any) -> float:
    price = float(value)
    # databento_dbn exposes fixed-point prices in 1e-9 units even though repr()
    # renders decimal prices. Synthetic/unit inputs already use decimal units.
    return price / 1_000_000_000.0 if abs(price) > 1_000_000.0 else price


def _observation(message: Any) -> dict[str, float] | None:
    try:
        levels = list(message.levels)[:5]
        if len(levels) < 5:
            return None
        best = levels[0]
        bid = _normalize_price(best.bid_px)
        ask = _normalize_price(best.ask_px)
        bid_size = sum(max(0.0, float(level.bid_sz)) for level in levels)
        ask_size = sum(max(0.0, float(level.ask_sz)) for level in levels)
        total = bid_size + ask_size
        if not all(math.isfinite(value) for value in (bid, ask, bid_size, ask_size)):
            return None
        if bid <= 0 or ask <= bid or total <= 0:
            return None
        return {
            "ts_event": float(message.ts_event),
            "ts_recv": float(message.ts_recv),
            "imbalance": (bid_size - ask_size) / total,
            "spread_ticks": (ask - bid) / TICK_SIZE,
        }
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def compute_feature_row(
    request: dict[str, Any],
    messages: Iterable[Any],
    *,
    degraded_dates: set[str],
) -> dict[str, Any]:
    end_ns = _iso_ns(str(request["end"]))
    direction_sign = 1.0 if request["direction"] == "BUY" else -1.0
    observations: list[dict[str, float]] = []
    for message in messages:
        observation = _observation(message)
        if observation is None:
            continue
        if observation["ts_event"] >= end_ns or observation["ts_recv"] >= end_ns:
            continue
        observations.append(observation)
    observations.sort(key=lambda item: (item["ts_recv"], item["ts_event"]))
    last30 = [item for item in observations if item["ts_recv"] >= end_ns - LAST_WINDOW_NS]
    prior30 = [
        item
        for item in observations
        if end_ns - PRIOR_WINDOW_NS <= item["ts_recv"] < end_ns - LAST_WINDOW_NS
    ]
    end_dates = {str(request["start"])[:10], str(request["end"])[:10]}
    row: dict[str, Any] = {
        "position_id": str(request["position_id"]),
        "direction": request["direction"],
        "start": request["start"],
        "end": request["end"],
        "filename": request["filename"],
        "source_status": "nonempty",
        "degraded_source_date": bool(end_dates & degraded_dates),
        "causal_records": len(observations),
        "records_last_30s": len(last30),
        "records_prior_30s": len(prior30),
        "aligned_imbalance_last": None,
        "aligned_imbalance_median_30s": None,
        "aligned_imbalance_change_30s": None,
        "aligned_persistence_30s": None,
        "spread_ticks_last": None,
        "staleness_ms": None,
        "book_alignment_score": None,
    }
    if observations and last30:
        last_value = direction_sign * observations[-1]["imbalance"]
        last30_values = [direction_sign * item["imbalance"] for item in last30]
        median_last30 = float(median(last30_values))
        median_prior30 = (
            float(median(direction_sign * item["imbalance"] for item in prior30))
            if prior30
            else median_last30
        )
        change = median_last30 - median_prior30
        persistence = sum(value > 0 for value in last30_values) / len(last30_values)
        score = (
            0.50 * median_last30
            + 0.25 * (2.0 * persistence - 1.0)
            + 0.25 * max(-1.0, min(1.0, change))
        )
        row.update(
            {
                "aligned_imbalance_last": last_value,
                "aligned_imbalance_median_30s": median_last30,
                "aligned_imbalance_change_30s": change,
                "aligned_persistence_30s": persistence,
                "spread_ticks_last": observations[-1]["spread_ticks"],
                "staleness_ms": (end_ns - observations[-1]["ts_recv"]) / 1_000_000.0,
                "book_alignment_score": score,
            }
        )
    eligible, reason = quality_eligibility(row)
    row["quality_eligible"] = eligible
    row["quality_reason"] = reason
    return row


def quality_eligibility(row: dict[str, Any]) -> tuple[bool, str]:
    if row.get("source_status") != "nonempty":
        return False, str(row.get("source_status", "SOURCE_UNAVAILABLE")).upper()
    if row.get("degraded_source_date") is True:
        return False, "DEGRADED_SOURCE_DATE"
    if int(row.get("causal_records", 0)) < MIN_CAUSAL_RECORDS:
        return False, "INSUFFICIENT_CAUSAL_RECORDS"
    if int(row.get("records_last_30s", 0)) < MIN_LAST30_RECORDS:
        return False, "INSUFFICIENT_LAST30_RECORDS"
    spread = row.get("spread_ticks_last")
    if not _finite(spread) or float(spread) > MAX_SPREAD_TICKS:
        return False, "WIDE_OR_INVALID_SPREAD"
    staleness = row.get("staleness_ms")
    if not _finite(staleness) or float(staleness) > MAX_STALENESS_MS:
        return False, "STALE_BOOK"
    if not _finite(row.get("book_alignment_score")):
        return False, "INVALID_SCORE"
    return True, "PASS"


def _unavailable_row(request: dict[str, Any], status: str) -> dict[str, Any]:
    row = {field: None for field in FIELDS}
    for field in ("position_id", "direction", "start", "end", "filename"):
        row[field] = request[field]
    row["position_id"] = str(row["position_id"])
    row["source_status"] = status
    row["degraded_source_date"] = False
    row["causal_records"] = 0
    row["records_last_30s"] = 0
    row["records_prior_30s"] = 0
    row["quality_eligible"] = False
    row["quality_reason"] = status.upper()
    return row


def extract_features(contract: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        import databento as db
    except ImportError as exc:
        raise FeatureError("Databento SDK is required for DBN feature extraction") from exc
    plan = contract["plan"]
    manifest = contract["manifest"]
    downloads = {str(item["filename"]): item for item in manifest["downloads"]}
    rows: list[dict[str, Any]] = []
    for request in plan["requests"]:
        download = downloads.get(str(request["filename"]))
        if not isinstance(download, dict):
            raise FeatureError(f"manifest response missing for {request['filename']}")
        if download.get("source_empty") is True:
            rows.append(_unavailable_row(request, "source_empty"))
            continue
        path = RAW_ROOT / str(request["filename"])
        try:
            store = db.DBNStore.from_file(path)
            row = compute_feature_row(
                request, store, degraded_dates=contract["degraded_dates"]
            )
        except Exception as exc:
            raise FeatureError(f"feature decode failed for {path}: {exc}") from exc
        rows.append(row)
    for request in plan["metadata_empty_windows"]:
        rows.append(_unavailable_row(request, "metadata_empty"))
    rows.sort(key=lambda item: (str(item["end"]), int(item["position_id"])))
    if len(rows) != 547 or len({row["position_id"] for row in rows}) != 547:
        raise FeatureError("source-only feature population coverage mismatch")
    return rows


def write_csv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def build_receipt(rows: list[dict[str, Any]], output: Path) -> dict[str, Any]:
    reasons = Counter(str(row["quality_reason"]) for row in rows)
    years: dict[str, dict[str, int]] = {}
    for row in rows:
        year = str(row["end"])[:4]
        bucket = years.setdefault(year, {"rows": 0, "quality_eligible": 0})
        bucket["rows"] += 1
        bucket["quality_eligible"] += int(row["quality_eligible"] is True)
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "status": "SOURCE_ONLY_FEATURE_EXTRACTION_PASS",
        "plan_id": PLAN_ID,
        "execution_id": EXECUTION_ID,
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "manifest_sha256": MANIFEST_SHA256,
        "validation_receipt_sha256": VALIDATION_RECEIPT_SHA256,
        "execution_authorization_sha256": EXECUTION_SHA256,
        "acquisition_stderr_sha256": STDERR_SHA256,
        "feature_tool_sha256": sha256_file(MODULE_PATH),
        "feature_csv_path": str(output.relative_to(WORKSPACE)).replace("\\", "/"),
        "feature_csv_sha256": sha256_file(output),
        "rows": len(rows),
        "quality_eligible": sum(row["quality_eligible"] is True for row in rows),
        "quality_reasons": dict(sorted(reasons.items())),
        "year_counts": years,
        "degraded_dates": [
            "2019-01-15",
            "2019-02-22",
            "2020-02-27",
            "2020-06-30",
            "2020-07-01",
        ],
        "score_formula": (
            "0.50*aligned_median_5level_imbalance_last30s + "
            "0.25*(2*aligned_positive_persistence_last30s-1) + "
            "0.25*clip(aligned_median_imbalance_last30s-minus-prior30s,-1,1)"
        ),
        "quality_contract": {
            "min_causal_records": MIN_CAUSAL_RECORDS,
            "min_last30_records": MIN_LAST30_RECORDS,
            "max_spread_ticks": MAX_SPREAD_TICKS,
            "max_staleness_ms": MAX_STALENESS_MS,
            "degraded_dates_excluded": True,
        },
        "outcome_fields_used": False,
        "sealed_oos_opened": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        contract = load_source_contract()
        rows = extract_features(contract)
        write_csv_atomic(args.output, rows)
        receipt = build_receipt(rows, args.output)
        write_json_atomic(args.receipt, receipt)
        print(
            "CME6E_RAW_BREAK_FEATURES "
            f"status={receipt['status']} rows={receipt['rows']} "
            f"quality_eligible={receipt['quality_eligible']} "
            f"outcome_fields_used=false sealed_oos_opened=false"
        )
        print(f"features={args.output}")
        print(f"receipt={args.receipt}")
        return 0
    except FeatureError as exc:
        print(f"CME6E_RAW_BREAK_FEATURES_BLOCKED reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
