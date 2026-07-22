#!/usr/bin/env python3
"""Build 40 Grok vision-review request packets for the frozen 400-case corpus.

Produces exactly 10 chunks of 10 PNGs for each of HYP-MZMS-XAU-M5-007..010 in
stable casebook order, plus one separate synthesis request template.

Does not open images, invoke Grok, or touch EA/backtest surfaces.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
EVIDENCE = RESEARCH / "evidence" / "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400"
CASEBOOK = EVIDENCE / "casebook_manifest.json"
SELECTION = EVIDENCE / "selection_manifest.json"
CAMPAIGN_METRICS = EVIDENCE / "campaign_metrics.json"
LIFECYCLE = EVIDENCE / "lifecycle_reconciliation.json"
PREREG = RESEARCH / "HYP-MZMS-XAU-M5-007-010_FROZEN_PREREG.md"
DESIGN = RESEARCH / "HYP-MZMS-XAU-M5-007-010_GROK_DESIGN_CANDIDATE.md"
SOURCE = RESEARCH / "source_snapshots" / "EA_MZMS_Scalper_HYP-MZMS-XAU-M5-007-010.mq5"
CONTEXT = ROOT / ".context"
CHUNKS_ROOT = EVIDENCE / "grok_review_chunks10"

CHUNK_SIZE = 10
CHUNK_COUNT = 10
HYPOTHESES: list[dict[str, str]] = [
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-007",
        "short": "007",
        "mechanism": (
            "Donchian fresh-impulse initiation with expanding ATR and rising mid-band ADX "
            "(InpSignalMode=2)"
        ),
    },
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-008",
        "short": "008",
        "mechanism": (
            "EMA20/EMA100 trend pullback and closed-bar pivot reclaim "
            "(InpSignalMode=3)"
        ),
    },
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-009",
        "short": "009",
        "mechanism": (
            "Bollinger/ATR compression followed by closed-bar envelope breakout "
            "(InpSignalMode=4)"
        ),
    },
    {
        "hypothesis_id": "HYP-MZMS-XAU-M5-010",
        "short": "010",
        "mechanism": (
            "RSI/wick/ADX-roll exhaustion rejection mean reversion "
            "(InpSignalMode=5)"
        ),
    },
]

VALIDITY_BOUNDARY = "INVALID_ENGINEERING_RUN_HISTORY_QUALITY_98_BELOW_99"
TASK_PREFIX = "mzms-xau-007-010-vision"
SCHEMA_VERSION = "mzms_hyp007_010_grok_review_chunk.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases_csv(hypothesis_id: str) -> dict[str, dict[str, Any]]:
    short = hypothesis_id.rsplit("-", 1)[-1]
    path = EVIDENCE / hypothesis_id / "cases.csv"
    by_id: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            case_id = str(row["case_id"])
            position_raw = (row.get("position_id") or "").strip()
            if position_raw and position_raw.lower() not in {"nan", "none", "null"}:
                position_id: int | None = int(float(position_raw))
            else:
                position_id = None
            by_id[case_id] = {
                "case_id": case_id,
                "case_kind": str(row["case_kind"]),
                "hypothesis_id": str(row["hypothesis_id"]),
                "run_id": str(row.get("run_id") or ""),
                "side": str(row.get("side") or ""),
                "direction": row.get("direction") or "",
                "stratum": row.get("stratum") or "",
                "anomaly_tag": row.get("anomaly_tag") or "",
                "image": str(row["image"]),
                "image_sha256": str(row.get("image_sha256") or "").upper(),
                "position_id": position_id,
                "entry_time_server": row.get("entry_time_server") or "",
                "decision_bar_server": row.get("decision_bar_server") or "",
                "decision_bar_utc": row.get("decision_bar_utc") or "",
                "failed_gates": row.get("failed_gates") or "",
                "active_gates": row.get("active_gates") or "",
                "normalized_distance": row.get("normalized_distance") or "",
                "near_miss_rank": row.get("near_miss_rank") or "",
                "net_usd": row.get("net_usd") or "",
                "net_R": row.get("net_R") or "",
                "hold_minutes": row.get("hold_minutes") or "",
                "trade_fields_forbidden": str(row.get("trade_fields_forbidden") or "").lower()
                in {"1", "true", "yes"},
                "short": short,
            }
    return by_id


def response_schema(hypothesis_id: str, chunk_id: str, expected: int = CHUNK_SIZE) -> dict[str, Any]:
    confidence = {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    evidence_label = {
        "type": "string",
        "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"],
    }
    return {
        "type": "object",
        "properties": {
            "hypothesis_id": {"type": "string", "const": hypothesis_id},
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
                        "case_kind": {
                            "type": "string",
                            "enum": ["EXECUTED", "OFFLINE_NEAR_MISS_DIAGNOSTIC"],
                        },
                        "position_id": {"type": ["integer", "null"]},
                        "image_opened": {"type": "boolean"},
                        "price_structure_observed": {"type": "string"},
                        "indicator_gate_observed": {"type": "string"},
                        "path_observed": {"type": "string"},
                        "primary_mechanism": {"type": "string"},
                        "evidence_label": evidence_label,
                        "confidence": confidence,
                        "fidelity_note": {"type": "string"},
                    },
                    "required": [
                        "case_id",
                        "case_kind",
                        "position_id",
                        "image_opened",
                        "price_structure_observed",
                        "indicator_gate_observed",
                        "path_observed",
                        "primary_mechanism",
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
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer", "minimum": 1, "maximum": 6},
                        "label": {"type": "string"},
                        "case_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                        "count_in_chunk": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": expected,
                        },
                        "finding": {"type": "string"},
                        "confidence": confidence,
                    },
                    "required": [
                        "rank",
                        "label",
                        "case_ids",
                        "count_in_chunk",
                        "finding",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "classification_summary": {
                "type": "object",
                "properties": {
                    "bad_entry_or_adverse_selection": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "normal_stochastic_loss": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "good_rejected_near_miss": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "cadence_bottleneck": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "bad_entry_or_adverse_selection",
                    "normal_stochastic_loss",
                    "good_rejected_near_miss",
                    "cadence_bottleneck",
                ],
                "additionalProperties": False,
            },
            "fresh_hypothesis_candidates": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "mechanism": {"type": "string"},
                        "why_not_rescue": {"type": "string"},
                        "cited_case_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "confidence": confidence,
                    },
                    "required": [
                        "title",
                        "mechanism",
                        "why_not_rescue",
                        "cited_case_ids",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "chunk_verdict": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "hypothesis_id",
            "chunk_id",
            "validity_boundary",
            "image_inspection_supported",
            "coverage",
            "cases",
            "ranked_mechanisms",
            "classification_summary",
            "fresh_hypothesis_candidates",
            "chunk_verdict",
            "limitations",
        ],
        "additionalProperties": False,
    }


def synthesis_response_schema() -> dict[str, Any]:
    confidence = {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    evidence_label = {
        "type": "string",
        "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"],
    }
    return {
        "type": "object",
        "properties": {
            "campaign_id": {
                "type": "string",
                "const": "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400",
            },
            "validity_boundary": {"type": "string"},
            "promotion_blocked": {"type": "boolean", "const": True},
            "post_hoc_rescue_blocked": {"type": "boolean", "const": True},
            "per_hypothesis": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "hypothesis_id": {"type": "string"},
                        "mechanism_name": {"type": "string"},
                        "economic_shape_diagnostic": {"type": "string"},
                        "cadence_verdict": {"type": "string"},
                        "dominant_failure_anatomy": {"type": "string"},
                        "supported_by_case_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "evidence_label": evidence_label,
                        "confidence": confidence,
                    },
                    "required": [
                        "hypothesis_id",
                        "mechanism_name",
                        "economic_shape_diagnostic",
                        "cadence_verdict",
                        "dominant_failure_anatomy",
                        "supported_by_case_ids",
                        "evidence_label",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "cross_mechanism_comparison": {
                "type": "object",
                "properties": {
                    "strongest_mechanism": {"type": "string"},
                    "weakest_mechanism": {"type": "string"},
                    "comparison_finding": {"type": "string"},
                    "evidence_label": evidence_label,
                    "confidence": confidence,
                },
                "required": [
                    "strongest_mechanism",
                    "weakest_mechanism",
                    "comparison_finding",
                    "evidence_label",
                    "confidence",
                ],
                "additionalProperties": False,
            },
            "fresh_prereg_candidates": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "mechanism": {"type": "string"},
                        "why_materially_new": {"type": "string"},
                        "why_not_007_010_rescue": {"type": "string"},
                        "cited_evidence": {"type": "string"},
                        "confidence": confidence,
                    },
                    "required": [
                        "title",
                        "mechanism",
                        "why_materially_new",
                        "why_not_007_010_rescue",
                        "cited_evidence",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "stop_recommendation": {
                "type": "object",
                "properties": {
                    "recommend_stop": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["recommend_stop", "reason"],
                "additionalProperties": False,
            },
            "owner_facing_markdown_vi": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "campaign_id",
            "validity_boundary",
            "promotion_blocked",
            "post_hoc_rescue_blocked",
            "per_hypothesis",
            "cross_mechanism_comparison",
            "fresh_prereg_candidates",
            "stop_recommendation",
            "owner_facing_markdown_vi",
            "limitations",
        ],
        "additionalProperties": False,
    }


def chunk_prompt(
    *,
    hypothesis: dict[str, str],
    chunk_id: str,
    chunk_manifest_path: Path,
    images: list[dict[str, Any]],
) -> str:
    hyp_id = hypothesis["hypothesis_id"]
    short = hypothesis["short"]
    mechanism = hypothesis["mechanism"]
    image_lines = "\n".join(
        (
            f"- {row['case_id']} | case_kind={row['case_kind']} | "
            f"position_id={row['position_id'] if row['position_id'] is not None else 'null'} | "
            f"PNG={row['absolute_path']}"
        )
        for row in images
    )
    return (
        f"Inspect exactly {CHUNK_SIZE} frozen XAUUSD M5 forensics PNGs for {hyp_id} {chunk_id}.\n"
        f"Mechanism under review: {mechanism}.\n"
        f"Open every absolute PNG path below with local image-capable inspection. "
        f"Do not summarize from filenames or metadata alone.\n"
        f"Manifest: {chunk_manifest_path}\n"
        f"Casebook: {CASEBOOK}\n"
        f"Selection: {SELECTION}\n"
        f"Campaign metrics: {CAMPAIGN_METRICS}\n"
        f"Lifecycle reconciliation: {LIFECYCLE}\n"
        f"Prereg: {PREREG}\n"
        f"Design: {DESIGN}\n"
        f"Exact source snapshot: {SOURCE}\n"
        f"Hypothesis cases.csv: {EVIDENCE / hyp_id / 'cases.csv'}\n\n"
        f"Ordered absolute images for this chunk only:\n{image_lines}\n\n"
        "Hard evidence boundaries (non-negotiable):\n"
        "1) History quality is 98% below the frozen 99% gate => DIAGNOSTIC ONLY. "
        "This sample cannot promote, go live, or authorize economic authority.\n"
        "2) Offline recomputed indicators on the charts are visualization/near-miss ranking "
        "only; they are NOT MT5 CopyBuffer/tester parity.\n"
        "3) Executed-trade truth is StateTelemetry + Lifecycle, not recomputed indicators.\n"
        "4) For OFFLINE_NEAR_MISS_DIAGNOSTIC cases, future-context candles after the decision "
        "boundary are path context only, NOT hypothetical PnL and not an unfilled trade outcome.\n"
        "5) position_id must be null for near-misses; integer only for EXECUTED cases.\n"
        "6) Propose only materially fresh mechanisms as hypotheses. Never recommend threshold "
        "tuning, session/year/direction veto, BE/trailing/timeout rescue, or any post-hoc "
        f"rescue of {short}/007..010.\n\n"
        "For every case return: case_id, case_kind, position_id, image_opened=true if opened, "
        "price_structure_observed, indicator_gate_observed, path_observed "
        "(executed outcome path OR near-miss future context), primary_mechanism, "
        "evidence_label in {OBSERVED,STRONG_INFERENCE,HYPOTHESIS,UNKNOWN}, confidence, "
        "and fidelity_note.\n"
        "At chunk level: rank recurring mechanisms with cited case_ids; classify cases into "
        "bad_entry_or_adverse_selection vs normal_stochastic_loss vs good_rejected_near_miss "
        "vs cadence_bottleneck; list at most three fresh hypothesis candidates with why_not_rescue.\n"
        f"Return exactly the {CHUNK_SIZE} ordered manifest cases. If image inspection is "
        "unavailable, set image_inspection_supported=false and do not fabricate observations."
    )


def build_chunk_request(
    *,
    hypothesis: dict[str, str],
    chunk_number: int,
    selected: list[dict[str, Any]],
    case_lookup: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    hyp_id = hypothesis["hypothesis_id"]
    short = hypothesis["short"]
    chunk_id = f"chunk_{chunk_number:02d}"
    images: list[dict[str, Any]] = []
    for item in selected:
        case = case_lookup[item["case_id"]]
        abs_path = str(Path(item["path"]).resolve())
        images.append(
            {
                "case_id": item["case_id"],
                "case_kind": item["case_kind"],
                "hypothesis_id": hyp_id,
                "image": item["image"],
                "absolute_path": abs_path,
                "sha256": str(item.get("sha256") or case.get("image_sha256") or "").upper(),
                "position_id": case["position_id"],
                "side": case.get("side") or "",
                "stratum": case.get("stratum") or "",
                "anomaly_tag": case.get("anomaly_tag") or "",
                "decision_bar_server": case.get("decision_bar_server") or "",
                "decision_bar_utc": case.get("decision_bar_utc") or "",
                "failed_gates": case.get("failed_gates") or "",
                "active_gates": case.get("active_gates") or "",
                "normalized_distance": case.get("normalized_distance") or "",
                "near_miss_rank": case.get("near_miss_rank") or "",
                "net_usd": case.get("net_usd") or "",
                "net_R": case.get("net_R") or "",
                "hold_minutes": case.get("hold_minutes") or "",
                "trade_fields_forbidden": case.get("trade_fields_forbidden", False),
            }
        )

    chunk_dir = CHUNKS_ROOT / short / chunk_id
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_manifest = {
        "schema_version": SCHEMA_VERSION,
        "campaign": "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400",
        "hypothesis_id": hyp_id,
        "short_id": short,
        "chunk_id": chunk_id,
        "chunk_number": chunk_number,
        "validity_boundary": VALIDITY_BOUNDARY,
        "mechanism": hypothesis["mechanism"],
        "source_casebook": str(CASEBOOK),
        "source_selection": str(SELECTION),
        "source_cases_csv": str(EVIDENCE / hyp_id / "cases.csv"),
        "image_count": len(images),
        "expected_case_ids": [row["case_id"] for row in images],
        "expected_position_ids": [row["position_id"] for row in images],
        "images": images,
        "indicator_fidelity_boundary": (
            "Offline recomputed indicators are visualization/near-miss ranking only. "
            "Not MT5 CopyBuffer parity. Execution truth = StateTelemetry + Lifecycle. "
            "Near-miss future context is not hypothetical PnL."
        ),
        "history_quality_boundary": "98% < 99% => DIAGNOSTIC ONLY; cannot promote/live.",
    }
    chunk_manifest_path = chunk_dir / "chunk_manifest.json"
    chunk_manifest_path.write_text(
        json.dumps(chunk_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    request_dir = CONTEXT / f"{TASK_PREFIX}-{short}-c{chunk_number:02d}"
    request_dir.mkdir(parents=True, exist_ok=True)
    prompt = chunk_prompt(
        hypothesis=hypothesis,
        chunk_id=chunk_id,
        chunk_manifest_path=chunk_manifest_path,
        images=images,
    )
    request = {
        "task": f"{TASK_PREFIX}-{short}-{chunk_id}",
        "request": {
            "reasoning_effort": "high",
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are a read-only senior systematic-trading chart forensic reviewer. "
                        "Use local evidence only. Open every absolute PNG path with image-capable "
                        "inspection. Separate OBSERVED, STRONG_INFERENCE, HYPOTHESIS, UNKNOWN. "
                        "Never invent promotion authority or post-hoc threshold rescue."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "hyp007_010_vision_chunk",
                    "schema": response_schema(hyp_id, chunk_id, CHUNK_SIZE),
                },
            },
        },
        "meta": {
            "purpose": f"{hyp_id} vision review {chunk_id}",
            "campaign": "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400",
            "hypothesis_id": hyp_id,
            "short_id": short,
            "chunk_id": chunk_id,
            "chunk_number": chunk_number,
            "case_ids": [row["case_id"] for row in images],
            "position_ids": [row["position_id"] for row in images],
            "case_kinds": [row["case_kind"] for row in images],
            "image_paths": [row["absolute_path"] for row in images],
            "image_sha256": [row["sha256"] for row in images],
            "chunk_manifest": str(chunk_manifest_path),
            "chunk_manifest_sha256": sha256_file(chunk_manifest_path),
            "casebook_sha256": sha256_file(CASEBOOK),
            "selection_sha256": sha256_file(SELECTION),
            "validity_boundary": VALIDITY_BOUNDARY,
            "promotion_blocked": True,
            "post_hoc_rescue_blocked": True,
        },
    }
    request_path = request_dir / "grok-request.json"
    request_path.write_text(
        json.dumps(request, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return request, chunk_manifest, request_path


def build_synthesis_request() -> Path:
    validated_results = EVIDENCE / "validated_results_400.json"
    synthesis_input = EVIDENCE / "synthesis_input.json"
    request_dir = CONTEXT / f"{TASK_PREFIX}-synthesis"
    request_dir.mkdir(parents=True, exist_ok=True)
    prompt = (
        "You are a separate, read-only Grok synthesis reviewer for the frozen MZMS "
        "XAUUSD M5 four-mechanism campaign HYP-MZMS-XAU-M5-007..010.\n\n"
        "Read these local artifacts only:\n"
        f"- validated chunk packet: {validated_results}\n"
        f"- machine synthesis input: {synthesis_input}\n"
        f"- campaign metrics: {CAMPAIGN_METRICS}\n"
        f"- lifecycle reconciliation: {LIFECYCLE}\n"
        f"- casebook: {CASEBOOK}\n"
        f"- selection: {SELECTION}\n"
        f"- prereg: {PREREG}\n"
        f"- design: {DESIGN}\n"
        f"- source snapshot: {SOURCE}\n\n"
        "Task: compare all four mechanisms using ONLY validated visual findings plus "
        "frozen campaign metrics. Write strict JSON per schema AND a Vietnamese "
        "owner-facing Markdown report in field owner_facing_markdown_vi.\n\n"
        "The Markdown must include: evidence-labelled conclusions; economic and cadence "
        "verdicts per hypothesis as diagnostic shape only; supported failure anatomy; "
        "strongest vs weakest mechanism; and at most four genuinely new prereg candidates "
        "OR an explicit stop recommendation.\n\n"
        "Hard prohibitions:\n"
        "1) history quality 98% < 99% => DIAGNOSTIC ONLY; promotion_blocked must remain true; "
        "history-quality-invalid results cannot become promotion evidence.\n"
        "2) post_hoc_rescue_blocked must remain true; do not rescue, retune, re-threshold, "
        "session/year/direction-veto, or re-run HYP-007..010.\n"
        "3) Do not invent case IDs, counts, or findings not present in validated results / "
        "campaign metrics.\n"
        "4) Fresh candidates must be materially new mechanisms, not threshold/session/BE "
        "rescue of 007..010.\n"
        "5) Use local evidence only; no web; no subagents; no EA edits."
    )
    request = {
        "task": f"{TASK_PREFIX}-synthesis",
        "request": {
            "reasoning_effort": "high",
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are a read-only Lead Quant synthesis reviewer. Integrate validated "
                        "chart forensics with frozen campaign metrics. Never invent promotion "
                        "authority or post-hoc rescue of killed/invalid objects."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "hyp007_010_vision_synthesis",
                    "schema": synthesis_response_schema(),
                },
            },
        },
        "meta": {
            "purpose": "four-mechanism validated visual synthesis + Vietnamese owner report",
            "campaign": "HYP-MZMS-XAU-M5-007-010_GROK_FORENSICS_400",
            "validated_results": str(validated_results),
            "synthesis_input": str(synthesis_input),
            "campaign_metrics": str(CAMPAIGN_METRICS),
            "prereg": str(PREREG),
            "design": str(DESIGN),
            "source": str(SOURCE),
            "depends_on": "all 40 chunk reviews collected and validated",
            "promotion_blocked": True,
            "post_hoc_rescue_blocked": True,
            "validity_boundary": VALIDITY_BOUNDARY,
        },
    }
    request_path = request_dir / "grok-request.json"
    request_path.write_text(
        json.dumps(request, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return request_path


def build_all() -> dict[str, Any]:
    if not CASEBOOK.exists():
        raise FileNotFoundError(f"missing frozen casebook: {CASEBOOK}")
    casebook = load_json(CASEBOOK)
    results = casebook.get("results") or []
    if len(results) != 400:
        raise RuntimeError(f"casebook expected 400 results, found {len(results)}")

    by_hyp: dict[str, list[dict[str, Any]]] = {
        item["hypothesis_id"]: [] for item in HYPOTHESES
    }
    for row in results:
        hyp_id = str(row["hypothesis_id"])
        if hyp_id not in by_hyp:
            raise RuntimeError(f"unexpected hypothesis in casebook: {hyp_id}")
        by_hyp[hyp_id].append(row)

    created: list[dict[str, Any]] = []
    for hypothesis in HYPOTHESES:
        hyp_id = hypothesis["hypothesis_id"]
        short = hypothesis["short"]
        ordered = by_hyp[hyp_id]
        if len(ordered) != 100:
            raise RuntimeError(f"{hyp_id} expected 100 cases, found {len(ordered)}")
        case_lookup = load_cases_csv(hyp_id)
        for index in range(CHUNK_COUNT):
            chunk_number = index + 1
            selected = ordered[index * CHUNK_SIZE : (index + 1) * CHUNK_SIZE]
            if len(selected) != CHUNK_SIZE:
                raise RuntimeError(
                    f"{hyp_id} chunk {chunk_number} expected {CHUNK_SIZE}, got {len(selected)}"
                )
            for item in selected:
                if item["case_id"] not in case_lookup:
                    raise RuntimeError(
                        f"casebook case missing from cases.csv: {item['case_id']}"
                    )
                if not Path(item["path"]).exists():
                    raise RuntimeError(f"missing PNG: {item['path']}")
            request, chunk_manifest, request_path = build_chunk_request(
                hypothesis=hypothesis,
                chunk_number=chunk_number,
                selected=selected,
                case_lookup=case_lookup,
            )
            created.append(
                {
                    "hypothesis_id": hyp_id,
                    "short_id": short,
                    "chunk_id": chunk_manifest["chunk_id"],
                    "request_path": str(request_path),
                    "task_dir": str(request_path.parent),
                    "case_ids": chunk_manifest["expected_case_ids"],
                    "image_count": CHUNK_SIZE,
                }
            )
            print(
                "CHUNK_REQUEST_OK "
                f"hyp={short} chunk={chunk_manifest['chunk_id']} "
                f"images={CHUNK_SIZE} dir={request_path.parent}"
            )

    synthesis_path = build_synthesis_request()
    print(f"SYNTHESIS_REQUEST_OK path={synthesis_path}")
    summary = {
        "schema_version": "mzms_hyp007_010_grok_review_request_build.v1",
        "chunk_requests": len(created),
        "expected_chunk_requests": 40,
        "synthesis_request": str(synthesis_path),
        "chunks": created,
        "context_prefix": TASK_PREFIX,
        "chunks_root": str(CHUNKS_ROOT),
        "casebook_sha256": sha256_file(CASEBOOK),
        "selection_sha256": sha256_file(SELECTION),
        "campaign_metrics_sha256": sha256_file(CAMPAIGN_METRICS),
    }
    index_path = EVIDENCE / "grok_review_request_index.json"
    index_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if len(created) != 40:
        raise RuntimeError(f"expected 40 chunk requests, built {len(created)}")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build 40 HYP-007..010 Grok vision chunk requests + synthesis template"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate frozen corpus shape without writing request artifacts",
    )
    args = parser.parse_args()
    if args.check_only:
        casebook = load_json(CASEBOOK)
        if int(casebook.get("image_count") or 0) != 400:
            raise SystemExit("casebook image_count != 400")
        print("CHECK_ONLY_OK image_count=400")
        return 0
    summary = build_all()
    print(
        "BUILD_HYP007_010_GROK_REVIEW_REQUESTS_OK "
        f"chunks={summary['chunk_requests']} synthesis=1"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
