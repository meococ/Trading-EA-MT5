#!/usr/bin/env python3
"""Validate Grok exploratory label output and compare it to objective precheck."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


FIELDS = (
    "label_true_sweep_liquidity",
    "label_true_displacement",
    "label_true_mss_bos_close",
    "label_valid_breaker",
    "label_fvg_fresh_unfilled",
    "label_micro_confirm_present",
    "label_core_setup_accept",
)
ALLOWED = {"yes", "no", "ambiguous"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_output_text(text: str) -> dict[str, object]:
    stripped = text.strip()
    if stripped.startswith("```json") and stripped.endswith("```"):
        stripped = stripped[len("```json") : -len("```")].strip()
    return json.loads(stripped)


def cohen_kappa(left: list[str], right: list[str]) -> dict[str, float]:
    if len(left) != len(right) or not left:
        raise ValueError("kappa inputs must be equal and non-empty")
    observed = sum(a == b for a, b in zip(left, right, strict=True)) / len(left)
    left_counts = Counter(left)
    right_counts = Counter(right)
    expected = sum(
        left_counts[label] / len(left) * right_counts[label] / len(right)
        for label in ALLOWED
    )
    kappa = 1.0 if expected == 1.0 and observed == 1.0 else (observed - expected) / (1.0 - expected)
    return {"observed_agreement": round(observed, 6), "cohen_kappa": round(kappa, 6)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objective-summary", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--runner-summary", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    objective = json.loads(args.objective_summary.read_text(encoding="utf-8"))
    objective_by_id = {row["event_id"]: row for row in objective["labels"]}
    request = json.loads(args.request.read_text(encoding="utf-8"))
    expected_ids = request["meta"]["sample_event_ids"]
    response_artifact = json.loads(args.response.read_text(encoding="utf-8"))
    overlay = parse_output_text(response_artifact["output_text"])
    runner = json.loads(args.runner_summary.read_text(encoding="utf-8"))

    if not runner.get("success") or runner.get("exit_code") != 0:
        raise ValueError("Grok runner did not succeed")
    if overlay.get("reviewer_type") != "AI_EXPLORATORY" or overlay.get("outcome_seen") is not False:
        raise ValueError("Grok authority/outcome flags are invalid")
    labels = overlay.get("labels") or []
    actual_ids = [row.get("event_id") for row in labels]
    if actual_ids != expected_ids:
        raise ValueError("Grok label identities/order do not match sealed sample")
    for row in labels:
        for field in FIELDS:
            if row.get(field) not in ALLOWED:
                raise ValueError(f"invalid {field} for {row.get('event_id')}")

    agreements: dict[str, object] = {}
    for field in FIELDS:
        left = [objective_by_id[event_id][field] for event_id in expected_ids]
        right = [row[field] for row in labels]
        agreements[field] = cohen_kappa(left, right)

    disagreements: list[dict[str, object]] = []
    for row in labels:
        event_id = row["event_id"]
        differing = {
            field: {"objective": objective_by_id[event_id][field], "grok": row[field]}
            for field in FIELDS
            if objective_by_id[event_id][field] != row[field]
        }
        if differing:
            disagreements.append(
                {
                    "event_id": event_id,
                    "differences": differing,
                    "grok_notes": row.get("notes", ""),
                }
            )

    result = {
        "schema_version": "unicorn_grok_label_calibration_analysis.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "authority": "AI_EXPLORATORY_PRE_OUTCOME_ONLY",
        "outcomes_seen": False,
        "human_label_gate_satisfied": False,
        "sample_size": len(expected_ids),
        "sample_is_random": False,
        "sample_design": "3 objective survivors plus 2 objective rejects; objective labels hidden from Grok",
        "grok_model": response_artifact.get("model"),
        "grok_stop_reason": response_artifact["response"]["parsed_stdout"].get("stopReason"),
        "runner_success": runner["success"],
        "artifacts": {
            "request_sha256": sha256_file(args.request),
            "response_sha256": sha256_file(args.response),
            "runner_summary_sha256": sha256_file(args.runner_summary),
            "objective_summary_sha256": sha256_file(args.objective_summary),
        },
        "agreements": agreements,
        "disagreements": disagreements,
        "interpretation": (
            "The sample is calibration only. Final-core kappa below 0.70 or any "
            "material MSS/breaker disagreement confirms that AI review cannot clear "
            "the frozen human-label gate."
        ),
        "grok_overlay": overlay,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "grok_overlay"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

