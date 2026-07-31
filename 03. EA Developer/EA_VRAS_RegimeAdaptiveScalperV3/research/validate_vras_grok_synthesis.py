#!/usr/bin/env python3
"""Fail-closed validation for the final Grok 100-image synthesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("synthesis_dir", type=Path)
    args = parser.parse_args()
    directory = args.synthesis_dir.resolve()
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    request = json.loads((directory / "grok-request.json").read_text(encoding="utf-8"))
    schema = json.loads((directory / "result_schema.json").read_text(encoding="utf-8"))
    result = json.loads((directory / "grok-synthesis.json").read_text(encoding="utf-8"))

    if not summary.get("success") or not summary.get("response_useful") or summary.get("stop_reason") != "EndTurn":
        raise RuntimeError("Synthesis runner is not a useful EndTurn success")
    jsonschema.validate(result, schema)
    expected = request["meta"]["expected_case_ids"]
    actual = result["case_ids_seen"]
    if actual != expected or len(set(actual)) != 100:
        raise RuntimeError("Synthesis case IDs do not reconcile exactly once in casebook order")
    coverage = result["coverage"]
    required = {
        "expected_images": 100,
        "images_opened": 100,
        "trade_images": 93,
        "rejected_candidate_images": 7,
        "batches_complete": 20,
        "entry_parity_manifests_checked": 100,
        "all_case_ids_reconciled": True,
    }
    if coverage != required:
        raise RuntimeError(f"Synthesis coverage mismatch: {coverage}")
    if len(result["owner_summary_vi"].strip()) < 100:
        raise RuntimeError("Vietnamese owner summary is unexpectedly short")
    if len(result["full_report_markdown"].strip()) < 1000:
        raise RuntimeError("Full report is unexpectedly short")
    print(json.dumps({"status": "VRAS_GROK_SYNTHESIS_ACCEPTED", "images": 100, "batches": 20}))


if __name__ == "__main__":
    main()
