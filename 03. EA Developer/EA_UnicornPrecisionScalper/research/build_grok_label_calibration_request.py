#!/usr/bin/env python3
"""Build an inline, no-tool Grok request for a sealed label calibration sample."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def label_schema() -> dict[str, object]:
    tri = {"enum": ["yes", "no", "ambiguous"]}
    properties = {
        "event_id": {"type": "string"},
        "label_true_sweep_liquidity": tri,
        "label_true_displacement": tri,
        "label_true_mss_bos_close": tri,
        "label_valid_breaker": tri,
        "label_fvg_fresh_unfilled": tri,
        "label_micro_confirm_present": tri,
        "label_core_setup_accept": tri,
        "entry_readiness": {
            "enum": ["limit_candidate", "market_confirmed", "reject", "ambiguous"]
        },
        "primary_reject_reason": {"type": "string"},
        "notes": {"type": "string"},
        "confidence": {"enum": ["high", "medium", "low"]},
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-dir", type=Path, required=True)
    parser.add_argument("--objective-summary", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    objective = json.loads(args.objective_summary.read_text(encoding="utf-8"))
    objective_by_id = {row["event_id"]: row for row in objective["labels"]}
    candidates: dict[str, dict[str, object]] = {}
    for path in sorted(args.context_dir.glob("label_context_batch_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["rows"]:
            candidates[row["detector"]["event_id"]] = row

    survivors = [
        row for row in objective["labels"] if row["objective_core_ex_breaker"] == "yes"
    ][:3]
    rejects = [
        row for row in objective["labels"] if row["objective_core_ex_breaker"] == "no"
    ][:2]
    selected = survivors + rejects
    if len(selected) != 5:
        raise ValueError("calibration sample requires 3 survivors and 2 rejects")

    sample: list[dict[str, object]] = []
    for label in selected:
        source = candidates[label["event_id"]]
        sample.append(
            {
                "detector": source["detector"],
                "information_cutoff_utc": source["information_cutoff_utc"],
                "completed_bar_context": {
                    "m5": source["completed_bar_context"]["m5"][-20:],
                    "m15": source["completed_bar_context"]["m15"][-8:],
                },
            }
        )

    rubric = args.rubric.read_text(encoding="utf-8")
    inline = json.dumps(
        {
            "schema_version": "unicorn_grok_label_calibration_sample.v1",
            "authority": "AI_EXPLORATORY_PRE_OUTCOME_ONLY",
            "outcomes_included": False,
            "selection": "first 3 objective-surviving plus first 2 objective-rejected rows; objective labels hidden",
            "rows": sample,
        },
        separators=(",", ":"),
    )
    request = {
        "task": "unicorn-alert-label-calibration-05",
        "request": {
            "model": "grok-4.5",
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are an independent trading-pattern taxonomy reviewer. "
                        "All allowed rubric and bar data are inline in this request; "
                        "do not call tools, read files, browse, use outcomes, or infer "
                        "later bars. Your output is AI_EXPLORATORY, not human labels or "
                        "backtest authority. Apply the rubric literally and prefer "
                        "ambiguous over invented breaker facts."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "FROZEN RUBRIC:\n---\n"
                        + rubric
                        + "\n---\nSEALED SAMPLE JSON:\n---\n"
                        + inline
                        + "\n---\nReturn only the requested JSON object with exactly 5 "
                        "labels in sample order. FVG formation is not a micro-confirmation. "
                        "Derive final core acceptance exactly from the five core components."
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "unicorn_label_overlay",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "reviewer_id": {"type": "string"},
                            "reviewer_type": {"const": "AI_EXPLORATORY"},
                            "outcome_seen": {"const": False},
                            "labels": {"type": "array", "items": label_schema()},
                        },
                        "required": [
                            "reviewer_id",
                            "reviewer_type",
                            "outcome_seen",
                            "labels",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
        },
        "meta": {
            "authority": "AI_EXPLORATORY_PRE_OUTCOME_ONLY",
            "rubric_sha256": sha256_file(args.rubric),
            "context_manifest_sha256": sha256_file(args.context_dir / "manifest.json"),
            "objective_summary_sha256": sha256_file(args.objective_summary),
            "sample_event_ids": [row["detector"]["event_id"] for row in sample],
            "objective_labels_sent_to_reviewer": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(request, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"REQUEST={args.output}")
    print(f"REQUEST_SHA256={sha256_file(args.output)}")
    print(f"REQUEST_BYTES={args.output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
