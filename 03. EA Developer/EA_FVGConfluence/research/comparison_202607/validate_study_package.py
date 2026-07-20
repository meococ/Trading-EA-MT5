#!/usr/bin/env python3
"""Validate immutable study inputs and the fresh source-to-binary receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


STUDY_ID = "STUDY-FVG-COMPARE-EURUSD-M5-001"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(workspace: Path, package: Path) -> dict[str, Any]:
    protocol_path = package / "BENCHMARK_PROTOCOL_V1.json"
    receipt_path = package / "evidence" / "20260718_SOURCE_BINARY_RECEIPT.json"
    protocol = read_json(protocol_path)
    receipt = read_json(receipt_path)

    require(protocol.get("study_id") == STUDY_ID, "protocol study_id mismatch")
    require(receipt.get("study_id") == STUDY_ID, "receipt study_id mismatch")
    require(
        protocol["specimen"]["terminal_state_must_remain"] == "killed",
        "terminal hypothesis state was relaxed",
    )
    require(protocol["authority"]["model0_authorized"] is False, "Model 0 unlocked")
    require(
        protocol["authority"]["economic_run_authorized"] is False,
        "economic run unlocked",
    )
    require(protocol["authority"]["promotion_eligible"] is False, "promotion unlocked")
    require(
        protocol["public_performance"]["minimum_eligible_accounts"] == 5,
        "public cohort minimum drifted",
    )
    require(
        protocol["public_performance"]["grade_c_rankable"] is False,
        "Grade C ranking was enabled",
    )
    require(receipt["validation"]["model0_authorized"] is False, "Model 0 unlocked")
    require(receipt["validation"]["promotion_eligible"] is False, "promotion unlocked")
    require(
        receipt["validation"]["historical_binary_receipt_reused"] is False,
        "historical binary receipt was reused",
    )

    expected_static = {
        package / "BENCHMARK_PROTOCOL_V1.md": receipt["protocol"]["markdown_sha256"],
        protocol_path: receipt["protocol"]["json_sha256"],
        package / "ARCHITECTURE_MATRIX.md": receipt["protocol"]["architecture_matrix_sha256"],
    }
    checked: list[dict[str, Any]] = []
    for path, expected in expected_static.items():
        actual = sha256(path)
        require(actual == expected, f"hash mismatch: {path}")
        checked.append({"path": str(path), "sha256": actual})

    for row in receipt["source_closure"]["files"]:
        path = workspace / Path(row["path"])
        require(path.stat().st_size == row["bytes"], f"byte-size mismatch: {path}")
        actual = sha256(path)
        require(actual == row["sha256"], f"source-closure hash mismatch: {path}")
        checked.append({"path": str(path), "sha256": actual})

    compile_row = receipt["compile"]
    for path_key, size_key, hash_key in (
        ("binary_path", "binary_bytes", "binary_sha256"),
        ("log_path", "log_bytes", "log_sha256"),
    ):
        path = workspace / Path(compile_row[path_key])
        require(path.stat().st_size == compile_row[size_key], f"byte-size mismatch: {path}")
        actual = sha256(path)
        require(actual == compile_row[hash_key], f"compile artifact hash mismatch: {path}")
        checked.append({"path": str(path), "sha256": actual})

    report_path = workspace / Path(protocol["report"]["path"])
    require(report_path.stat().st_size == protocol["report"]["bytes"], "report size mismatch")
    require(sha256(report_path) == protocol["report"]["sha256"], "report hash mismatch")

    manifest_path = workspace / Path(protocol["data"]["manifest_path"])
    require(
        sha256(manifest_path) == protocol["data"]["manifest_sha256"],
        "data manifest hash mismatch",
    )
    require(protocol["data"]["spread_cost_usable"] is False, "unverified cost was promoted")

    nonrepaint_path = package / "evidence" / "20260718_NONREPAINT_REVALIDATION.json"
    nonrepaint = read_json(nonrepaint_path)
    require(nonrepaint["status"] == "PASS_ENGINEERING_ONLY", "non-repaint gate failed")
    require(
        nonrepaint["source_sha256"] == protocol["specimen"]["source_sha256"],
        "non-repaint source identity mismatch",
    )
    prior_audit_path = workspace / Path(nonrepaint["prior_same_source_audit"]["path"])
    require(
        sha256(prior_audit_path) == nonrepaint["prior_same_source_audit"]["sha256"],
        "prior same-source non-repaint audit hash mismatch",
    )
    require(nonrepaint["fresh_scan"]["explicit_bar_zero_decision_matches"] == 0,
            "fresh scan found an explicit bar-zero decision")

    return {
        "schema_version": "fvg_comparison_validation.v1",
        "study_id": STUDY_ID,
        "verdict": "PASS",
        "checked_artifacts": checked,
        "economic_run_authorized": False,
        "promotion_eligible": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.workspace.resolve(), args.package.resolve())
        exit_code = 0
    except (KeyError, OSError, TypeError, ValueError) as exc:
        result = {
            "schema_version": "fvg_comparison_validation.v1",
            "study_id": STUDY_ID,
            "verdict": "FAIL",
            "error": str(exc),
            "economic_run_authorized": False,
            "promotion_eligible": False,
        }
        exit_code = 2
    rendered = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
