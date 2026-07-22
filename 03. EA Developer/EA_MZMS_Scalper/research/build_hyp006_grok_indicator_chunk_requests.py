#!/usr/bin/env python3
"""Build four 25-image Grok request packets per indicator-forensics worker."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006"
CHUNK_SIZE = 10
CHUNK_COUNT = 10
EVIDENCE = (
    Path(__file__).resolve().parent
    / "evidence"
    / f"{HYPOTHESIS_ID}_GROK_INDICATOR_FORENSICS_200"
)
SOURCE = (
    ROOT
    / "02. AlphaFactory"
    / "runs"
    / "EA_MZMS_Scalper"
    / "20260721_190051"
    / "snapshot"
    / "source"
    / "EA_MZMS_Scalper.mq5"
)
READOUT = (
    ROOT
    / "03. EA Developer"
    / "EA_MZMS_Scalper"
    / "research"
    / "HYP-MZMS-MACD-HIST-SLOPE-XAUUSD-M5-006_READOUT.md"
)


def response_schema(worker: str, chunk_id: str, expected: int) -> dict:
    confidence = {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    return {
        "type": "object",
        "properties": {
            "worker_id": {"type": "string", "const": worker},
            "chunk_id": {"type": "string", "const": chunk_id},
            "validity_boundary": {"type": "string"},
            "image_inspection_supported": {"type": "boolean"},
            "coverage": {
                "type": "object",
                "properties": {
                    "expected_images": {"type": "integer", "const": expected},
                    "images_opened": {"type": "integer", "minimum": 0, "maximum": expected},
                    "all_cases_reported": {"type": "boolean"},
                },
                "required": ["expected_images", "images_opened", "all_cases_reported"],
                "additionalProperties": False,
            },
            "cases": {
                "type": "array",
                "minItems": expected,
                "maxItems": expected,
                "items": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string"},
                        "position_id": {"type": "integer"},
                        "image_opened": {"type": "boolean"},
                        "entry_price_context": {"type": "string"},
                        "indicator_strategy_context": {"type": "string"},
                        "outcome_path": {"type": "string"},
                        "primary_failure_mechanism": {"type": "string"},
                        "evidence_label": {
                            "type": "string",
                            "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"],
                        },
                        "confidence": confidence,
                        "fidelity_note": {"type": "string"},
                    },
                    "required": [
                        "case_id",
                        "position_id",
                        "image_opened",
                        "entry_price_context",
                        "indicator_strategy_context",
                        "outcome_path",
                        "primary_failure_mechanism",
                        "evidence_label",
                        "confidence",
                        "fidelity_note",
                    ],
                    "additionalProperties": False,
                },
            },
            "ranked_mechanisms": {
                "type": "array",
                "minItems": 1,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer", "minimum": 1, "maximum": 5},
                        "label": {"type": "string"},
                        "case_ids": {"type": "array", "items": {"type": "string"}},
                        "count_in_chunk": {"type": "integer", "minimum": 0, "maximum": expected},
                        "strategy_link": {"type": "string"},
                        "finding": {"type": "string"},
                        "confidence": confidence,
                    },
                    "required": [
                        "rank",
                        "label",
                        "case_ids",
                        "count_in_chunk",
                        "strategy_link",
                        "finding",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "indicator_strategy_findings": {
                "type": "array",
                "minItems": 2,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "surface": {"type": "string"},
                        "case_ids": {"type": "array", "items": {"type": "string"}},
                        "count_in_chunk": {"type": "integer", "minimum": 0, "maximum": expected},
                        "finding": {"type": "string"},
                        "confidence": confidence,
                    },
                    "required": ["surface", "case_ids", "count_in_chunk", "finding", "confidence"],
                    "additionalProperties": False,
                },
            },
            "logic_corrections": {"type": "array", "items": {"type": "string"}},
            "chunk_verdict": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "worker_id",
            "chunk_id",
            "validity_boundary",
            "image_inspection_supported",
            "coverage",
            "cases",
            "ranked_mechanisms",
            "indicator_strategy_findings",
            "logic_corrections",
            "chunk_verdict",
            "limitations",
        ],
        "additionalProperties": False,
    }


def main() -> None:
    chunks_root = EVIDENCE / "grok_chunks10"
    for worker, short in (("worker_a", "a"), ("worker_b", "b")):
        chart_dir = EVIDENCE / "charts" / worker
        casebook = json.loads((chart_dir / "casebook_manifest.json").read_text(encoding="utf-8"))
        results = casebook["results"]
        if len(results) != 100:
            raise RuntimeError(f"{worker} expected 100 images, found {len(results)}")
        for index in range(CHUNK_COUNT):
            chunk_number = index + 1
            chunk_id = f"chunk_{chunk_number:02d}"
            selected = results[index * CHUNK_SIZE : (index + 1) * CHUNK_SIZE]
            chunk_dir = chunks_root / worker / chunk_id
            chunk_dir.mkdir(parents=True, exist_ok=True)
            chunk_manifest = {
                "schema_version": "mzms_grok_indicator_chunk.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "worker": worker,
                "chunk_id": chunk_id,
                "validity_boundary": "INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99",
                "source_casebook": str(chart_dir / "casebook_manifest.json"),
                "image_count": len(selected),
                "images": [
                    {
                        **item,
                        "absolute_path": str(chart_dir / item["image"]),
                    }
                    for item in selected
                ],
                "indicator_fidelity_boundary": (
                    "Recomputed from post-run M5 bars; not MT5 CopyBuffer/tester parity. "
                    "Lifecycle and exact source are execution truth."
                ),
            }
            chunk_manifest_path = chunk_dir / "chunk_manifest.json"
            chunk_manifest_path.write_text(
                json.dumps(chunk_manifest, indent=2), encoding="utf-8"
            )

            request_dir = ROOT / ".context" / f"mzms-xau-indicator-{short}-s10-c{chunk_number:02d}"
            request_dir.mkdir(parents=True, exist_ok=True)
            prompt = (
                f"Inspect exactly {CHUNK_SIZE} indicator-rich XAUUSD M5 loser PNGs for {worker} {chunk_id}. "
                f"Read {chunk_manifest_path}, {EVIDENCE / 'selection_manifest.json'}, {READOUT}, "
                f"and exact source {SOURCE}. Open every absolute_path in the chunk manifest with "
                "image-capable inspection. Each PNG combines closed-bar decision and outcome regions "
                "with EMA200, MACD 12/26/9 histogram s3/s2/s1, RSI14 42-58, ADX14 gate 18, ATR14, "
                "entry/SL/TP/exit and hold. For every case explain the price/EMA context, how the "
                "active indicator cluster combines, and the loss path. A chart NON-PARITY label is "
                "post-run bar/formula fidelity evidence, not an EA logic violation. Lifecycle/source "
                "remain truth. Source SL is the farther of structure+buffer and 1.5 ATR; do not call "
                "it tight without case-specific evidence. Parent run is invalid at 98% history below "
                "the frozen 99% gate. Loser-only chunk counts are not population rates and cannot "
                f"authorize filters or tuned thresholds. Return exactly the {CHUNK_SIZE} manifest cases. If image "
                "inspection is unavailable, set image_inspection_supported=false and do not fabricate."
            )
            request = {
                "task": f"mzms-xau-indicator-{short}-{chunk_id}",
                "request": {
                    "reasoning_effort": "high",
                    "input": [
                        {
                            "role": "system",
                            "content": (
                                "You are a read-only senior systematic-trading chart forensic reviewer. "
                                "Use local evidence only; separate OBSERVED, STRONG_INFERENCE, HYPOTHESIS, UNKNOWN."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "indicator_forensics_chunk",
                            "schema": response_schema(worker, chunk_id, CHUNK_SIZE),
                        },
                    },
                },
                "meta": {
                    "purpose": f"{worker} indicator chart forensics {chunk_id}",
                    "sample_seed": 5600722,
                    "image_slice": f"{index * CHUNK_SIZE}:{(index + 1) * CHUNK_SIZE}",
                },
            }
            (request_dir / "grok-request.json").write_text(
                json.dumps(request, indent=2), encoding="utf-8"
            )
            print(
                f"CHUNK_REQUEST_OK worker={worker} chunk={chunk_id} images={CHUNK_SIZE} dir={request_dir}"
            )


if __name__ == "__main__":
    main()
