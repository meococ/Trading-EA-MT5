#!/usr/bin/env python3
"""Create 20 hash-bound Grok image-review packets for the frozen random-100 sample."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


HYPOTHESIS_ID = "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004"
RUN_ID = "20260725_210811"
BATCH_SIZE = 5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def binding(workspace: Path, path: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(workspace).as_posix(),
        "absolute_path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def acp_image_block(path: Path, *, case_id: str, view: str) -> dict[str, object]:
    if path.suffix.casefold() != ".png":
        raise ValueError(f"Only PNG casebook images are supported: {path}")
    data = path.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"Casebook image is not a valid PNG payload: {path}")
    return {
        "type": "image",
        "data": base64.b64encode(data).decode("ascii"),
        "mimeType": "image/png",
        "uri": path.resolve().as_uri(),
        "_meta": {
            "case_id": case_id,
            "view": view,
            "sha256": sha256(path),
        },
    }


def response_schema(batch_id: str, case_ids: list[str]) -> dict[str, object]:
    return {
        "name": f"scc_random100_{batch_id}",
        "schema": {
            "type": "object",
            "properties": {
                "batch_id": {"type": "string", "const": batch_id},
                "coverage": {
                    "type": "object",
                    "properties": {
                        "expected_cases": {"type": "integer", "const": 5},
                        "reviewed_cases": {"type": "integer", "const": 5},
                        "decision_images_opened": {"type": "integer", "const": 5},
                        "anatomy_images_opened": {"type": "integer", "const": 5},
                    },
                    "required": [
                        "expected_cases",
                        "reviewed_cases",
                        "decision_images_opened",
                        "anatomy_images_opened",
                    ],
                    "additionalProperties": False,
                },
                "case_reviews": {
                    "type": "array",
                    "minItems": 5,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "case_id": {"type": "string", "enum": case_ids},
                            "sample_rank": {"type": "integer"},
                            "position_id": {"type": "integer"},
                            "decision_image_opened": {"type": "boolean", "const": True},
                            "anatomy_image_opened": {"type": "boolean", "const": True},
                            "visible_direction": {
                                "type": "string",
                                "enum": ["LONG", "SHORT"],
                            },
                            "visible_entry_price": {"type": "number"},
                            "visible_exit_price": {"type": "number"},
                            "visible_exit_class": {
                                "type": "string",
                                "enum": ["SL_LIKE", "TP_LIKE", "TIMEOUT_OR_OTHER"],
                            },
                            "visible_h1_range_position": {"type": "number"},
                            "decision_future_hidden_seen": {
                                "type": "boolean",
                                "const": True,
                            },
                            "anatomy_outcome_region_seen": {
                                "type": "boolean",
                                "const": True,
                            },
                            "unsupported_indicator_panels_claimed": {
                                "type": "boolean",
                                "const": False,
                            },
                            "decision_observations": {
                                "type": "array",
                                "minItems": 1,
                                "items": {"type": "string"},
                            },
                            "anatomy_observations": {
                                "type": "array",
                                "minItems": 1,
                                "items": {"type": "string"},
                            },
                            "mechanism": {
                                "type": "string",
                                "enum": [
                                    "IMMEDIATE_CONTINUATION_EXPANSION",
                                    "TIGHT_STOP_MICROSTRUCTURE_FAILURE",
                                    "NO_FOLLOWTHROUGH_TIMEOUT",
                                    "MIXED_OR_OTHER",
                                    "UNCLEAR",
                                ],
                            },
                            "evidence_class": {
                                "type": "string",
                                "enum": [
                                    "OBSERVED",
                                    "STRONG_INFERENCE",
                                    "HYPOTHESIS",
                                    "UNKNOWN",
                                ],
                            },
                            "data_quality_note": {"type": "string"},
                        },
                        "required": [
                            "case_id",
                            "sample_rank",
                            "position_id",
                            "decision_image_opened",
                            "anatomy_image_opened",
                            "visible_direction",
                            "visible_entry_price",
                            "visible_exit_price",
                            "visible_exit_class",
                            "visible_h1_range_position",
                            "decision_future_hidden_seen",
                            "anatomy_outcome_region_seen",
                            "unsupported_indicator_panels_claimed",
                            "decision_observations",
                            "anatomy_observations",
                            "mechanism",
                            "evidence_class",
                            "data_quality_note",
                        ],
                        "additionalProperties": False,
                    },
                },
                "batch_findings": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                },
                "no_tuning_applied": {"type": "boolean", "const": True},
            },
            "required": [
                "batch_id",
                "coverage",
                "case_reviews",
                "batch_findings",
                "no_tuning_applied",
            ],
            "additionalProperties": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--random-root",
        type=Path,
        help="Optional corrected-casebook root; defaults to random100_forensics.",
    )
    parser.add_argument(
        "--context-root",
        type=Path,
        help="Optional Grok context root; defaults to .context/scc-hyp004-random100-gfi.",
    )
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[3]
    evidence = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "research"
        / "evidence"
        / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
    )
    random_root = (
        args.random_root.resolve()
        if args.random_root is not None
        else evidence / "random100_forensics"
    )
    context_root = (
        args.context_root.resolve()
        if args.context_root is not None
        else workspace / ".context" / "scc-hyp004-random100-gfi"
    )
    context_root.mkdir(parents=True, exist_ok=True)

    sample_csv = random_root / "random100_cases.csv"
    sample_manifest = random_root / "random100_sample_manifest.json"
    qc_receipt = random_root / "random100_casebook_qc.json"
    decision_manifest_path = random_root / "decision_asof" / "cases_manifest.json"
    anatomy_manifest_path = random_root / "anatomy" / "cases_manifest.json"
    pair_analysis = evidence / "pair_analysis.json"
    path_geometry = evidence / "path_geometry_analysis_v2.json"
    readout = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "research"
        / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_READOUT.md"
    )
    prereg = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "research"
        / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_FROZEN_PREREG.md"
    )
    source = (
        workspace
        / "03. EA Developer"
        / "EA_SweepCascadeContinuation"
        / "EA_SweepCascadeContinuation.mq5"
    )
    analysis_contract = (
        Path.home()
        / ".agents"
        / "skills"
        / "grok-ea-trade-forensics"
        / "references"
        / "analysis_contract.md"
    )

    with sample_csv.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 100:
        raise SystemExit(f"Expected 100 frozen cases, got {len(rows)}")
    decision_manifest = json.loads(decision_manifest_path.read_text(encoding="utf-8-sig"))
    anatomy_manifest = json.loads(anatomy_manifest_path.read_text(encoding="utf-8-sig"))
    decision_by_id = {row["case_id"]: row for row in decision_manifest["results"]}
    anatomy_by_id = {row["case_id"]: row for row in anatomy_manifest["results"]}

    common_bindings = {
        "frozen_prereg": binding(workspace, prereg),
        "terminal_readout": binding(workspace, readout),
        "pair_analysis": binding(workspace, pair_analysis),
        "path_geometry": binding(workspace, path_geometry),
        "source_mql5": binding(workspace, source),
        "sample_manifest": binding(workspace, sample_manifest),
        "sample_csv": binding(workspace, sample_csv),
        "casebook_qc": binding(workspace, qc_receipt),
        "decision_manifest": binding(workspace, decision_manifest_path),
        "anatomy_manifest": binding(workspace, anatomy_manifest_path),
        "analysis_contract": {
            "absolute_path": str(analysis_contract),
            "bytes": analysis_contract.stat().st_size,
            "sha256": sha256(analysis_contract),
        },
    }

    index_rows: list[dict[str, object]] = []
    for batch_number, start in enumerate(range(0, 100, BATCH_SIZE), start=1):
        batch_id = f"batch{batch_number:02d}"
        batch_dir = context_root / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)
        batch_rows = rows[start : start + BATCH_SIZE]
        cases: list[dict[str, object]] = []
        for row in batch_rows:
            case_id = row["case_id"]
            decision_png = random_root / "decision_asof" / decision_by_id[case_id]["png"]
            anatomy_png = random_root / "anatomy" / anatomy_by_id[case_id]["png"]
            cases.append(
                {
                    "case_id": case_id,
                    "sample_rank": int(row["sample_rank"]),
                    "position_id": int(row["position_id"]),
                    "direction": row["direction_label"],
                    "entry_time_utc": row["entry_time_utc"],
                    "exit_time_utc": row["exit_time_utc"],
                    "net_account": float(row["net_account"]),
                    "net_R": float(row["net_R"]),
                    "reason_class": row["reason"],
                    "decision_image": binding(workspace, decision_png),
                    "anatomy_image": binding(workspace, anatomy_png),
                }
            )
        packet = {
            "schema_version": "scc_grok_visual_batch.v2",
            "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hypothesis_id": HYPOTHESIS_ID,
            "run_id": RUN_ID,
            "batch_id": batch_id,
            "role": "READ_ONLY_VISUAL_FORENSIC_REVIEWER",
            "visual_correction": {
                "casebook_version": "CLOCK_CORRECTED_V2",
                "lifecycle_source_clock": "FivePercent broker server time",
                "casebook_clock": "UTC after canonical server-to-UTC conversion",
                "old_visual_reviews_authority": "INVALID_FOR_PATH_SHAPE",
            },
            "prohibitions": [
                "Do not modify repository files.",
                "Do not create scripts or derived datasets.",
                "Do not tune thresholds or propose same-ID rescue rules.",
                "Do not use anatomy outcome information to claim decision-time predictability.",
            ],
            "common_bindings": common_bindings,
            "cases": cases,
        }
        packet_path = batch_dir / "batch_packet.json"
        packet_path.write_text(
            json.dumps(packet, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        case_ids = [case["case_id"] for case in cases]
        image_blocks: list[dict[str, object]] = []
        image_map_lines: list[str] = []
        image_number = 1
        for case in cases:
            case_id = str(case["case_id"])
            decision_png = Path(str(case["decision_image"]["absolute_path"]))
            anatomy_png = Path(str(case["anatomy_image"]["absolute_path"]))
            image_map_lines.append(
                f"[Image #{image_number}] = {case_id} decision_asof (outcome-blind)"
            )
            image_blocks.append(
                acp_image_block(decision_png, case_id=case_id, view="decision")
            )
            image_number += 1
            image_map_lines.append(
                f"[Image #{image_number}] = {case_id} anatomy (outcome-disclosing)"
            )
            image_blocks.append(
                acp_image_block(anatomy_png, case_id=case_id, view="anatomy")
            )
            image_number += 1

        prompt = (
            "Act as a bounded read-only Grok visual forensic reviewer for an MT5 EA. "
            f"Open and read the exact task packet at {packet_path}. "
            "This prompt contains ten inline ACP image blocks with actual PNG pixels; they "
            "are not local-path references. Inspect BOTH the decision and anatomy attachment "
            "for every one of the five cases. Use this exact attachment map:\n"
            + "\n".join(image_map_lines)
            + "\nRead the bound sample manifest, pair analysis, terminal "
            "readout, path-geometry postmortem, frozen prereg, source MQL5 and analysis "
            "contract as needed. "
            "Decision images are outcome-blind and may support entry-context observations. "
            "Anatomy images disclose outcome and may only support path/exit explanation. "
            "This is the clock-corrected V2 casebook. Do not reuse or paraphrase any "
            "mechanism label or visual narrative from the original misaligned casebook; "
            "inspect these ten V2 images from scratch. For every case, transcribe from "
            "the pixels the LONG/SHORT title, entry price, exit price, exit class, and "
            "the H1 box value 'Entry loc vs closed 20-bar range'. Confirm the visible "
            "FUTURE HIDDEN and POST-ENTRY OUTCOME regions. The casebook has M5 and H1 "
            "panels only; no M15, MACD, RSI, ADX, FVG, order-block or confluence "
            "indicator panel is rendered, and the H1 EMA context says NOT_REQUESTED. "
            "Keep observed facts separate from inference. Do not create or modify files, "
            "do not run ad-hoc analysis scripts, do not recommend disabling same-sample "
            "buckets, and do not tune or rescue the terminal HYP-004 strategy. "
            f"Return exactly one JSON object for {batch_id} covering these exact IDs: "
            + ", ".join(case_ids)
            + ". Each case must appear exactly once and both image-open booleans must be true "
            "only after actual visual inspection."
        )
        prompt_blocks = [
            {
                "type": "text",
                "text": (
                    "You are a read-only MT5 trade-forensics reviewer. Follow the supplied "
                    "evidence contract and return only the requested structured final result.\n\n"
                    + prompt
                ),
            },
            *image_blocks,
        ]
        prompt_blocks_path = batch_dir / "grok-prompt-blocks.json"
        prompt_blocks_path.write_text(
            json.dumps(prompt_blocks, separators=(",", ":"), allow_nan=False),
            encoding="utf-8",
        )
        request = {
            "task": f"scc-hyp004-random100-{batch_id}",
            "prompt_blocks_file": str(prompt_blocks_path),
            "prompt_blocks_sha256": sha256(prompt_blocks_path),
            "request": {
                "reasoning_effort": "high",
                "input": [
                    {
                        "role": "system",
                        "content": (
                            "You are a read-only MT5 trade-forensics reviewer. "
                            "Follow the supplied evidence contract and return only the "
                            "requested structured final result."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": response_schema(batch_id, case_ids),
                },
            },
            "meta": {
                "hypothesis_id": HYPOTHESIS_ID,
                "run_id": RUN_ID,
                "batch_id": batch_id,
                "batch_packet": str(packet_path),
                "batch_packet_sha256": sha256(packet_path),
                "prompt_blocks": str(prompt_blocks_path),
                "prompt_blocks_sha256": sha256(prompt_blocks_path),
                "case_ids": case_ids,
            },
        }
        request_path = batch_dir / "grok-request.json"
        request_path.write_text(
            json.dumps(request, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        index_rows.append(
            {
                "batch_id": batch_id,
                "request": binding(workspace, request_path),
                "packet": binding(workspace, packet_path),
                "prompt_blocks": binding(workspace, prompt_blocks_path),
                "case_ids": case_ids,
            }
        )

    index = {
        "schema_version": "scc_grok_visual_batch_index.v2",
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": RUN_ID,
        "batches": 20,
        "cases_per_batch": 5,
        "total_cases": 100,
        "total_images_to_open": 200,
        "image_transport": "ACP inline base64 image blocks",
        "global_concurrency": 1,
        "rows": index_rows,
    }
    index_path = context_root / "batch_index.json"
    index_path.write_text(
        json.dumps(index, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        "SCC_RANDOM100_GROK_BATCHES_OK "
        f"batches=20 cases=100 images=200 image_transport=ACP_INLINE "
        f"index_sha256={sha256(index_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
