#!/usr/bin/env python3
"""One-shot point-bounded geometry revision over the frozen HYP005 comparator."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "03. EA Developer/EA_SupertrendBurstScalper/research"
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-006"
FAILED_HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-005"
ATTEMPT_ID = "STBS006-COMPARATOR-001"
VERDICT = "ENGINEERING_VALID_STBS_MODEL0_SIGNAL_ATR_POINT_BOUNDED_GEOMETRY_AUDIT_PASS"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
OUTPUT_DIR = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-006/STBS006-COMPARATOR-001"
BASE_PATH = RESEARCH / "compare_stbs005_exact_orders_heading.py"
BASE_SHA256 = "F55AF249A00D905DA1E183FC3CECE3F5D74D45965C9AC416AE15F8EADBFF77ED"
PREREG_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-006_POINT_BOUNDED_GEOMETRY_PREREG.md"
PREREG_SHA256 = "F9084DC6CFA8DAD0BFF1E0349710FC4A7C1F58CD8751B123E11403D26D5296BD"
TEST_PATH = RESEARCH / "tests/test_stbs006_point_bounded_geometry_comparator.py"
TEST_SHA256 = "4412C56A32F5D84FE967CCAC0473F1F0B685A2A2880F55F4459FAD4EFB7F20B4"
REVIEW_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-006_PRE_COMPARATOR_REVIEW.md"
HYP005_TERMINAL_ROW_SHA256 = "179BD0163632218A026E433FC68E416CF49EEE9BE8613593A1AF40ABA6261942"
HYP005_START_PATH = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-005/STBS005-COMPARATOR-001/attempt_started.json"
HYP005_START_SHA256 = "B43F8B50DB8E9BADB4F6B7C6814FD91BAA7702B2458C9B5DD756B2C708E83EAA"
HYP005_TERMINAL_PATH = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-005/STBS005-COMPARATOR-001/attempt_terminal.json"
HYP005_TERMINAL_SHA256 = "D0DA049862B26BAD9897798FF344B6944BCFADD970FF532D66AEB04B42356DF2"
HYP005_FAILURE_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-005_COMPARATOR_FAILURE.md"
HYP005_FAILURE_SHA256 = "2CA213847823372C480B8E965A608FD56467D5EB13EDDAEC0A45D5BD363ED5AE"
HYP005_REVIEW_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-005_POST_FAILURE_REVIEW.md"
HYP005_REVIEW_SHA256 = "22FC569727E2E98637203B22E177252FF6AC005CD4FD619453AE37CD70B31572"
POINT = 0.01
TOL = 0.5e-8 + 1e-9


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


BASE_RAW = BASE_PATH.read_bytes()


def load_base():
    if sha256_bytes(BASE_RAW) != BASE_SHA256:
        raise ValueError("frozen HYP005 comparator dependency hash drift")
    name = "stbs006_hyp005_comparator_dependency"
    module = types.ModuleType(name)
    module.__file__ = str(BASE_PATH)
    module.__package__ = ""
    sys.modules[name] = module
    exec(compile(BASE_RAW, str(BASE_PATH), "exec"), module.__dict__)
    return module


BASE = load_base()
FALSE_AUTHORITIES = BASE.FALSE_AUTHORITIES


def validate_authority(registry: Path) -> tuple[dict[str, Any], dict[str, str]]:
    self_raw = Path(__file__).resolve().read_bytes()
    registry_raw = registry.read_bytes()
    raw, row = BASE.BASE.latest_registry_row(registry_raw, HYPOTHESIS_ID)
    failed_raw, failed = BASE.BASE.latest_registry_row(registry_raw, FAILED_HYPOTHESIS_ID)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    issued = datetime.fromisoformat(str(row.get("updated_at_utc", "")).replace("Z", "+00:00"))
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_STBS006_POINT_BOUNDED_GEOMETRY_COMPARATOR_AUTHORIZED",
        "source": row.get("source_hash") == BASE.BASE.SOURCE_SHA256,
        "prereg_path": row.get("prereg_path") == PREREG_PATH.relative_to(ROOT).as_posix(),
        "prereg_sha": row.get("prereg_sha256") == PREREG_SHA256,
        "authority": validation.get("authority") == AUTHORITY,
        "comparator": validation.get("comparator_execution_authorized") is True,
        "attempt": validation.get("comparator_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("comparator_attempt_limit") == 1,
        "unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "self_path": validation.get("reviewed_comparator_path") == Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "self_sha": validation.get("reviewed_comparator_sha256") == sha256_bytes(self_raw),
        "base_path": validation.get("reviewed_hyp005_comparator_path") == BASE_PATH.relative_to(ROOT).as_posix(),
        "base_sha": validation.get("reviewed_hyp005_comparator_sha256") == BASE_SHA256,
        "test_path": validation.get("reviewed_test_path") == TEST_PATH.relative_to(ROOT).as_posix(),
        "test_sha": validation.get("reviewed_test_sha256") == TEST_SHA256,
        "review_path": validation.get("independent_review_path") == REVIEW_PATH.relative_to(ROOT).as_posix(),
        "review_sha": re.fullmatch(r"[A-F0-9]{64}", str(validation.get("independent_review_sha256", ""))) is not None,
        "evidence_root": validation.get("comparator_evidence_root") == OUTPUT_DIR.relative_to(ROOT).as_posix(),
        "nonfuture": issued <= datetime.now(timezone.utc),
        "hyp005_state": failed.get("state") == "killed",
        "hyp005_verdict": failed.get("verdict") == "KILL_EXACT_GEOMETRY_FROM_ROUNDED_ATR_TELEMETRY",
        "hyp005_raw": sha256_bytes(failed_raw) == HYP005_TERMINAL_ROW_SHA256,
        "hyp005_bound": validation.get("hyp005_terminal_row_sha256") == HYP005_TERMINAL_ROW_SHA256,
        "hyp005_start": validation.get("hyp005_attempt_start_sha256") == HYP005_START_SHA256,
        "hyp005_terminal": validation.get("hyp005_attempt_terminal_sha256") == HYP005_TERMINAL_SHA256,
        "hyp005_failure": validation.get("hyp005_failure_document_sha256") == HYP005_FAILURE_SHA256,
        "hyp005_review": validation.get("hyp005_post_failure_review_sha256") == HYP005_REVIEW_SHA256,
        "point": validation.get("geometry_point") == POINT,
        "tolerance": validation.get("geometry_tolerance") == TOL,
        "no_other_authority": all(validation.get(name) is False for name in FALSE_AUTHORITIES),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise ValueError(f"HYP006 comparator authority failed: {failed_checks}")
    return row, {
        "registry_sha256": sha256_bytes(registry_raw),
        "latest_row_sha256": sha256_bytes(raw),
        "hyp005_terminal_row_sha256": sha256_bytes(failed_raw),
        "comparator_sha256": sha256_bytes(self_raw),
        "base_comparator_sha256": BASE_SHA256,
    }


def point_bounded_geometry_contract_checks(
    direction: str,
    atr: float,
    entry: float,
    stop: float,
    target: float,
) -> dict[str, bool]:
    finite_positive = all(math.isfinite(value) and value > 0.0 for value in (atr, entry, stop, target))
    if direction == "LONG":
        sided = stop < entry < target
    elif direction == "SHORT":
        sided = target < entry < stop
    else:
        sided = False
    point_aligned = finite_positive and all(
        abs(value - round(value / POINT) * POINT) <= TOL
        for value in (entry, stop, target)
    )
    risk = abs(entry - stop) if finite_positive else math.nan
    reward = abs(target - entry) if finite_positive else math.nan
    stop_excess = risk - atr
    target_excess = reward - 1.5 * risk
    return {
        "direction": direction in ("LONG", "SHORT"),
        "finite_positive": finite_positive,
        "sided": sided,
        "point_aligned": point_aligned,
        "stop_interval": finite_positive and -TOL <= stop_excess <= POINT + TOL,
        "target_interval": finite_positive and -TOL <= target_excess <= POINT + TOL,
    }


def revise_report(base_report: dict[str, Any]) -> dict[str, Any]:
    if base_report.get("schema_version") != "stbs004_existing_run_comparator_report.v1":
        raise ValueError("inherited comparator report schema mismatch")
    report = dict(base_report)
    report["schema_version"] = "stbs006_point_bounded_geometry_comparator_report.v1"
    report["verdict"] = VERDICT
    report["orders_heading_contract"] = "EXACT_ENGLISH_OR_NFC_VIETNAMESE_NO_NORMALIZATION"
    report["point_bounded_telemetry_consistency"] = True
    report["geometry_point"] = POINT
    report["geometry_tolerance"] = TOL
    report["exact_raw_double_geometry_proven"] = False
    report["runtime_tick_size_proven"] = False
    report["exact_position_sizing_proven"] = False
    return report


def execute(registry: Path) -> dict[str, Any]:
    row, authority = validate_authority(registry.resolve())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    started_path = OUTPUT_DIR / "attempt_started.json"
    terminal_path = OUTPUT_DIR / "attempt_terminal.json"
    BASE.BASE.write_exclusive(
        started_path,
        BASE.BASE.json_bytes({
            "schema_version": "stbs006_comparator_started.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "same_id_retry_authorized": False,
            **authority,
        }),
    )
    try:
        captured: dict[str, bytes] = {}
        bindings: list[dict[str, str]] = []
        for label, (path, expected) in BASE.BASE.STATIC_BINDINGS.items():
            raw = path.read_bytes()
            actual = sha256_bytes(raw)
            if actual != expected:
                raise ValueError(f"{label} changed: expected {expected}, got {actual}")
            captured[label] = raw
            bindings.append({"label": label, "path": path.resolve().as_posix(), "sha256": actual})
        validation = row["validation"]
        dynamic_bindings = (
            ("prereg", PREREG_PATH, PREREG_SHA256),
            ("reviewed_test", TEST_PATH, TEST_SHA256),
            ("independent_review", REVIEW_PATH, str(validation["independent_review_sha256"])),
            ("hyp005_start", HYP005_START_PATH, HYP005_START_SHA256),
            ("hyp005_terminal", HYP005_TERMINAL_PATH, HYP005_TERMINAL_SHA256),
            ("hyp005_failure", HYP005_FAILURE_PATH, HYP005_FAILURE_SHA256),
            ("hyp005_review", HYP005_REVIEW_PATH, HYP005_REVIEW_SHA256),
        )
        dynamic_paths = [path.resolve() for _, path, _ in dynamic_bindings]
        static_paths = {path.resolve() for path, _ in BASE.BASE.STATIC_BINDINGS.values()}
        if (
            len(dynamic_paths) != len(set(dynamic_paths))
            or any(path in static_paths for path in dynamic_paths)
            or any(ROOT.resolve() not in path.parents for path in dynamic_paths)
        ):
            raise ValueError("dynamic HYP006 package paths are not unique/disjoint/rooted")
        for label, path, expected in dynamic_bindings:
            raw = path.read_bytes()
            actual = sha256_bytes(raw)
            if actual != expected:
                raise ValueError(f"{label} changed")
            captured[label] = raw
            bindings.append({"label": label, "path": path.resolve().as_posix(), "sha256": actual})

        captured["hyp005_comparator"] = BASE_RAW
        bindings.append({"label": "hyp005_comparator", "path": BASE_PATH.resolve().as_posix(), "sha256": sha256_bytes(BASE_RAW)})
        captured["hyp004_comparator"] = BASE.BASE_RAW
        bindings.append({"label": "hyp004_comparator", "path": BASE.BASE_PATH.resolve().as_posix(), "sha256": sha256_bytes(BASE.BASE_RAW)})

        manifest = BASE.BASE.decode_json(captured["run_manifest"], "run manifest")
        if manifest.get("contract_symbol_geometry") != {"digits": 2, "point": POINT, "pip_size": 0.01}:
            raise ValueError("manifest symbol point/digits geometry mismatch")
        if not callable(BASE.BASE.event_identity_checks):
            raise ValueError("inherited event-identity gate is unavailable")
        BASE.BASE.HYPOTHESIS_ID = HYPOTHESIS_ID
        BASE.BASE.ATTEMPT_ID = ATTEMPT_ID
        BASE.BASE.VERDICT = VERDICT
        BASE.BASE.orders_section_is_empty = BASE.orders_section_is_empty
        BASE.BASE.geometry_contract_checks = point_bounded_geometry_contract_checks
        first = revise_report(BASE.BASE.analyze(captured))
        second = revise_report(BASE.BASE.analyze(captured))
        first_raw = BASE.BASE.json_bytes(first)
        if first_raw != BASE.BASE.json_bytes(second):
            raise ValueError("same-capture deterministic replay mismatch")

        report_path = OUTPUT_DIR / "stbs006_existing_run_comparator_report.json"
        BASE.BASE.write_exclusive(report_path, first_raw)
        receipt = {
            "schema_version": "stbs006_existing_run_comparator_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "verdict": VERDICT,
            "authority": authority,
            "attempt_started_sha256": sha256_bytes(started_path.read_bytes()),
            "report_sha256": sha256_bytes(first_raw),
            "bindings": bindings,
            "deterministic_replay": "PASS",
            "trades_executed": 0,
            "performance_metrics_authorized": False,
            "economics_evaluated": False,
            "same_id_retry_authorized": False,
            "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        receipt_path = OUTPUT_DIR / "stbs006_existing_run_comparator_receipt.json"
        BASE.BASE.write_exclusive(receipt_path, BASE.BASE.json_bytes(receipt))
        BASE.BASE.write_exclusive(
            terminal_path,
            BASE.BASE.json_bytes({
                "schema_version": "stbs006_comparator_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "status": "COMPLETE",
                "verdict": VERDICT,
                "attempt_started_sha256": receipt["attempt_started_sha256"],
                "report_sha256": receipt["report_sha256"],
                "receipt_sha256": sha256_bytes(receipt_path.read_bytes()),
                "same_id_retry_authorized": False,
                "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }),
        )
        return {
            "report": report_path.as_posix(),
            "report_sha256": receipt["report_sha256"],
            "receipt": receipt_path.as_posix(),
            "receipt_sha256": sha256_bytes(receipt_path.read_bytes()),
            "terminal": terminal_path.as_posix(),
            "terminal_sha256": sha256_bytes(terminal_path.read_bytes()),
            "verdict": VERDICT,
        }
    except BaseException as exc:
        if not terminal_path.exists():
            BASE.BASE.write_exclusive(
                terminal_path,
                BASE.BASE.json_bytes({
                    "schema_version": "stbs006_comparator_terminal.v1",
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "status": "FAILED",
                    "verdict": "STBS006_COMPARATOR_FAILED_ATTEMPT_CONSUMED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "same_id_retry_authorized": False,
                    "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                }),
            )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--registry", type=Path, default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    print(json.dumps(execute(args.registry), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
