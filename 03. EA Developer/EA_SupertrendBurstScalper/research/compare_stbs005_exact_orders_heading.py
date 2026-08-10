#!/usr/bin/env python3
"""One-shot exact-heading revision over the frozen HYP004 comparator."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = ROOT / "03. EA Developer/EA_SupertrendBurstScalper/research"
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-005"
FAILED_HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-004"
ATTEMPT_ID = "STBS005-COMPARATOR-001"
VERDICT = "ENGINEERING_VALID_STBS_MODEL0_SIGNAL_ATR_GEOMETRY_AUDIT_PASS"
AUTHORITY = "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
OUTPUT_DIR = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-005/STBS005-COMPARATOR-001"
BASE_PATH = RESEARCH / "compare_stbs004_existing_run.py"
BASE_SHA256 = "00D140BEBAB567678F96E4C581C6871D410C18C488BF1330FDEFC2EBEC44677B"
PREREG_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-005_EXACT_ORDERS_HEADING_PREREG.md"
PREREG_SHA256 = "866527BBC08BAB4E7127F4198083D1798229010C7EC8A9099996DAF685083B06"
TEST_PATH = RESEARCH / "tests/test_stbs005_exact_orders_heading_comparator.py"
TEST_SHA256 = "E4E602E719249335EA447964A86F50ACF93415E3D6CB6F5AD361EDA4134FA2DC"
REVIEW_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-005_PRE_COMPARATOR_REVIEW.md"
HYP004_TERMINAL_ROW_SHA256 = "74C14309567C96AC54A0DEACE93B08B7487D016752EF262D52830476C9DCF252"
HYP004_START_PATH = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-004/STBS004-COMPARATOR-001/attempt_started.json"
HYP004_START_SHA256 = "50D5C69C6DB4A5D60180C7ACB56A6901AC679B12FDE5A924164561553148534F"
HYP004_TERMINAL_PATH = RESEARCH / "evidence/HYP-STBS-XAUUSD-M15-004/STBS004-COMPARATOR-001/attempt_terminal.json"
HYP004_TERMINAL_SHA256 = "905A1C5C899F52B3EF879A95563C462A250E6D73CC810F39CEB40536B93CA16D"
HYP004_FAILURE_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-004_COMPARATOR_FAILURE.md"
HYP004_FAILURE_SHA256 = "E4EC24C6A60BD0BF5985FCB2EA89318987F3454D324308FD0C1782C402F00837"
HYP004_REVIEW_PATH = RESEARCH / "HYP-STBS-XAUUSD-M15-004_POST_FAILURE_REVIEW.md"
HYP004_REVIEW_SHA256 = "FD2C41DD682CC48A71400438C5CF5996346AADA35DA0C2F9678E7F89F4BE185A"
SUPPORTED_ORDERS_HEADINGS = ("Orders", "C\u00e1c l\u1ec7nh \u0111\u1eb7t")
EXPECTED_COLSPANS = [1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


BASE_RAW = BASE_PATH.read_bytes()


def load_base():
    if sha256_bytes(BASE_RAW) != BASE_SHA256:
        raise ValueError("frozen HYP004 comparator dependency hash drift")
    name = "stbs005_hyp004_comparator_dependency"
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
    raw, row = BASE.latest_registry_row(registry_raw, HYPOTHESIS_ID)
    failed_raw, failed = BASE.latest_registry_row(registry_raw, FAILED_HYPOTHESIS_ID)
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    issued = datetime.fromisoformat(str(row.get("updated_at_utc", "")).replace("Z", "+00:00"))
    checks = {
        "state": row.get("state") == "screened",
        "model": row.get("model") == 0,
        "verdict": row.get("verdict") == "FROZEN_STBS005_EXACT_ORDERS_HEADING_COMPARATOR_AUTHORIZED",
        "source": row.get("source_hash") == BASE.SOURCE_SHA256,
        "prereg_path": row.get("prereg_path") == PREREG_PATH.relative_to(ROOT).as_posix(),
        "prereg_sha": row.get("prereg_sha256") == PREREG_SHA256,
        "authority": validation.get("authority") == AUTHORITY,
        "comparator": validation.get("comparator_execution_authorized") is True,
        "attempt": validation.get("comparator_attempt_id") == ATTEMPT_ID,
        "limit": validation.get("comparator_attempt_limit") == 1,
        "unconsumed": metrics.get("comparator_attempts_consumed") == 0,
        "self_path": validation.get("reviewed_comparator_path") == Path(__file__).resolve().relative_to(ROOT).as_posix(),
        "self_sha": validation.get("reviewed_comparator_sha256") == sha256_bytes(self_raw),
        "base_path": validation.get("reviewed_hyp004_comparator_path") == BASE_PATH.relative_to(ROOT).as_posix(),
        "base_sha": validation.get("reviewed_hyp004_comparator_sha256") == BASE_SHA256,
        "test_path": validation.get("reviewed_test_path") == TEST_PATH.relative_to(ROOT).as_posix(),
        "test_sha": validation.get("reviewed_test_sha256") == TEST_SHA256,
        "review_path": validation.get("independent_review_path") == REVIEW_PATH.relative_to(ROOT).as_posix(),
        "review_sha": re.fullmatch(r"[A-F0-9]{64}", str(validation.get("independent_review_sha256", ""))) is not None,
        "evidence_root": validation.get("comparator_evidence_root") == OUTPUT_DIR.relative_to(ROOT).as_posix(),
        "nonfuture": issued <= datetime.now(timezone.utc),
        "hyp004_state": failed.get("state") == "killed",
        "hyp004_verdict": failed.get("verdict") == "KILL_EXACT_ORDERS_HEADING_ENCODING_PREDICATE",
        "hyp004_raw": sha256_bytes(failed_raw) == HYP004_TERMINAL_ROW_SHA256,
        "hyp004_bound": validation.get("hyp004_terminal_row_sha256") == HYP004_TERMINAL_ROW_SHA256,
        "hyp004_start": validation.get("hyp004_attempt_start_sha256") == HYP004_START_SHA256,
        "hyp004_terminal": validation.get("hyp004_attempt_terminal_sha256") == HYP004_TERMINAL_SHA256,
        "hyp004_failure": validation.get("hyp004_failure_document_sha256") == HYP004_FAILURE_SHA256,
        "hyp004_review": validation.get("hyp004_post_failure_review_sha256") == HYP004_REVIEW_SHA256,
        "no_other_authority": all(validation.get(name) is False for name in FALSE_AUTHORITIES),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    if failed_checks:
        raise ValueError(f"HYP005 comparator authority failed: {failed_checks}")
    return row, {
        "registry_sha256": sha256_bytes(registry_raw),
        "latest_row_sha256": sha256_bytes(raw),
        "hyp004_terminal_row_sha256": sha256_bytes(failed_raw),
        "comparator_sha256": sha256_bytes(self_raw),
        "base_comparator_sha256": BASE_SHA256,
    }


def parse_colspans(cells: list[tuple[str, str]]) -> list[int] | None:
    return BASE.parse_colspans(cells)


def orders_section_is_empty(html: str) -> bool:
    bold = list(re.finditer(r"<b>(.*?)</b>", html, re.I | re.S))
    supported = [match for match in bold if match.group(1).strip() in SUPPORTED_ORDERS_HEADINGS]
    if len(supported) != 1:
        return False
    start = supported[0]
    deals = [match for match in bold if match.start() > start.end() and match.group(1).strip() == "Deals"]
    if len(deals) != 1:
        return False
    section = html[start.end() : deals[0].start()]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", section, re.I | re.S)
    if len(rows) != 2:
        return False
    cell_re = re.compile(r"<td([^>]*)>(.*?)</td>", re.I | re.S)
    header, spacer = cell_re.findall(rows[0]), cell_re.findall(rows[1])
    if (
        len(header) != 11
        or parse_colspans(header) != EXPECTED_COLSPANS
        or sum(EXPECTED_COLSPANS) != 13
        or not all(re.fullmatch(r"\s*<b>.*?</b>\s*", inner, re.I | re.S) for _, inner in header)
    ):
        return False
    return (
        len(spacer) == 1
        and parse_colspans(spacer) == [1]
        and re.sub(r"<[^>]+>", "", spacer[0][1]).strip() == ""
    )


def revise_report(base_report: dict[str, Any]) -> dict[str, Any]:
    if base_report.get("schema_version") != "stbs004_existing_run_comparator_report.v1":
        raise ValueError("inherited comparator report schema mismatch")
    report = dict(base_report)
    report["schema_version"] = "stbs005_exact_orders_heading_comparator_report.v1"
    report["heading_revision"] = "EXACT_ENGLISH_OR_NFC_VIETNAMESE_NO_NORMALIZATION"
    return report


def execute(registry: Path) -> dict[str, Any]:
    row, authority = validate_authority(registry.resolve())
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)
    started_path = OUTPUT_DIR / "attempt_started.json"
    terminal_path = OUTPUT_DIR / "attempt_terminal.json"
    BASE.write_exclusive(
        started_path,
        BASE.json_bytes({
            "schema_version": "stbs005_comparator_started.v1",
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
        for label, (path, expected) in BASE.STATIC_BINDINGS.items():
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
            ("hyp004_start", HYP004_START_PATH, HYP004_START_SHA256),
            ("hyp004_terminal", HYP004_TERMINAL_PATH, HYP004_TERMINAL_SHA256),
            ("hyp004_failure", HYP004_FAILURE_PATH, HYP004_FAILURE_SHA256),
            ("hyp004_review", HYP004_REVIEW_PATH, HYP004_REVIEW_SHA256),
        )
        dynamic_paths = [path.resolve() for _, path, _ in dynamic_bindings]
        static_paths = {path.resolve() for path, _ in BASE.STATIC_BINDINGS.values()}
        if (
            len(dynamic_paths) != len(set(dynamic_paths))
            or any(path in static_paths for path in dynamic_paths)
            or any(ROOT.resolve() not in path.parents for path in dynamic_paths)
        ):
            raise ValueError("dynamic HYP005 package paths are not unique/disjoint/rooted")
        for label, path, expected in dynamic_bindings:
            raw = path.read_bytes()
            actual = sha256_bytes(raw)
            if actual != expected:
                raise ValueError(f"{label} changed")
            captured[label] = raw
            bindings.append({"label": label, "path": path.resolve().as_posix(), "sha256": actual})

        captured["base_comparator"] = BASE_RAW
        bindings.append({
            "label": "base_comparator",
            "path": BASE_PATH.resolve().as_posix(),
            "sha256": sha256_bytes(BASE_RAW),
        })

        BASE.HYPOTHESIS_ID = HYPOTHESIS_ID
        BASE.ATTEMPT_ID = ATTEMPT_ID
        BASE.VERDICT = VERDICT
        BASE.orders_section_is_empty = orders_section_is_empty
        first = revise_report(BASE.analyze(captured))
        second = revise_report(BASE.analyze(captured))
        first_raw = BASE.json_bytes(first)
        if first_raw != BASE.json_bytes(second):
            raise ValueError("same-capture deterministic replay mismatch")

        report_path = OUTPUT_DIR / "stbs005_existing_run_comparator_report.json"
        BASE.write_exclusive(report_path, first_raw)
        receipt = {
            "schema_version": "stbs005_existing_run_comparator_receipt.v1",
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
        receipt_path = OUTPUT_DIR / "stbs005_existing_run_comparator_receipt.json"
        BASE.write_exclusive(receipt_path, BASE.json_bytes(receipt))
        BASE.write_exclusive(
            terminal_path,
            BASE.json_bytes({
                "schema_version": "stbs005_comparator_terminal.v1",
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
            BASE.write_exclusive(
                terminal_path,
                BASE.json_bytes({
                    "schema_version": "stbs005_comparator_terminal.v1",
                    "hypothesis_id": HYPOTHESIS_ID,
                    "attempt_id": ATTEMPT_ID,
                    "status": "FAILED",
                    "verdict": "STBS005_COMPARATOR_FAILED_ATTEMPT_CONSUMED",
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
    parser.add_argument(
        "--registry",
        type=Path,
        default=ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
    )
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    print(json.dumps(execute(args.registry), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
