#!/usr/bin/env python3
"""Fail-closed validation for one five-image Grok result packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import jsonschema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_dir", type=Path)
    args = parser.parse_args()
    directory = args.batch_dir.resolve()
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    request = json.loads((directory / "grok-request.json").read_text(encoding="utf-8"))
    schema = json.loads((directory / "result_schema.json").read_text(encoding="utf-8"))
    result = json.loads((directory / "grok-analysis.json").read_text(encoding="utf-8"))

    if not summary.get("success") or not summary.get("response_useful") or summary.get("stop_reason") != "EndTurn":
        raise RuntimeError("Runner summary is not a useful EndTurn success")
    jsonschema.validate(result, schema)
    coverage = result["coverage"]
    if coverage != {
        "expected_images": 5,
        "images_opened": 5,
        "all_cases_reported": True,
        "entry_parity_manifests_checked": 5,
    }:
        raise RuntimeError(f"Coverage is not exact 5/5: {coverage}")
    cases = result["cases"]
    actual_ids = [case["case_id"] for case in cases]
    if actual_ids != request["meta"]["expected_case_ids"]:
        raise RuntimeError("Case ID order/coverage mismatch")
    actual_positions = [int(case["position_id"]) for case in cases]
    if actual_positions != request["meta"]["expected_position_ids"]:
        raise RuntimeError("Position ID order/coverage mismatch")
    if not all(case["image_opened"] for case in cases):
        raise RuntimeError("At least one case lacks image_opened=true")
    if len(set(actual_ids)) != 5:
        raise RuntimeError("Duplicate case ID in batch result")
    print(json.dumps({"status": "VRAS_GROK_BATCH_ACCEPTED", "batch": result["batch_id"], "images": 5}))


if __name__ == "__main__":
    main()
