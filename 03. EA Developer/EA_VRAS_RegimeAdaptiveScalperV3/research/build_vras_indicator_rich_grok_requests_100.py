#!/usr/bin/env python3
"""Build twenty five-image Grok packets plus one final synthesis packet."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-003_GROK_CHART_FORENSICS_100"
CHARTS = EVIDENCE / "indicator_rich"
CASES = EVIDENCE / "cases_all_100.csv"
SELECTION = EVIDENCE / "selection_manifest.json"
CASEBOOK = EVIDENCE / "indicator_rich_casebook_manifest.json"
PREREG = RESEARCH / "HYP-VRAS-EURUSD-M5-003_FROZEN_PREREG.md"
LOGIC = RESEARCH / "LOGIC_TO_CODE_MATRIX.md"
READOUT = RESEARCH / "HYP-VRAS-EURUSD-M5-003_READOUT.md"
RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_RegimeAdaptiveScalperV3" / "20260722_103759"
SOURCE = RUN / "snapshot" / "source" / "EA_VRAS_RegimeAdaptiveScalperV3.mq5"
RUN_MANIFEST = RUN / "run_manifest.json"
LIFECYCLE = next((RUN / "logs").glob("*LifecycleTrades*.csv"))
RUN_META = next((RUN / "logs").glob("*RunMeta*.json"))
CONTEXT = ROOT / ".context" / "vras-003-grok-indicator-rich-100-20260722"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def finite_or_none(value: object) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def batch_schema(batch_id: str, expected_ids: list[str]) -> dict:
    confidence = {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    evidence = {"type": "string", "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"]}
    return {
        "type": "object",
        "properties": {
            "batch_id": {"type": "string", "const": batch_id},
            "coverage": {
                "type": "object",
                "properties": {
                    "expected_images": {"type": "integer", "const": 5},
                    "images_opened": {"type": "integer", "minimum": 0, "maximum": 5},
                    "all_cases_reported": {"type": "boolean"},
                    "entry_parity_manifests_checked": {"type": "integer", "minimum": 0, "maximum": 5},
                },
                "required": ["expected_images", "images_opened", "all_cases_reported", "entry_parity_manifests_checked"],
                "additionalProperties": False,
            },
            "cases": {
                "type": "array",
                "minItems": 5,
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string", "enum": expected_ids},
                        "case_kind": {"type": "string", "enum": ["TRADE", "REJECTED_CANDIDATE"]},
                        "position_id": {"type": "integer"},
                        "image_opened": {"type": "boolean"},
                        "price_and_setup": {"type": "string"},
                        "indicator_state_and_trajectory": {"type": "string"},
                        "post_decision_path": {"type": "string"},
                        "mechanism_assessment": {"type": "string"},
                        "evidence_label": evidence,
                        "confidence": confidence,
                        "fidelity_note": {"type": "string"},
                    },
                    "required": [
                        "case_id", "case_kind", "position_id", "image_opened", "price_and_setup",
                        "indicator_state_and_trajectory", "post_decision_path", "mechanism_assessment",
                        "evidence_label", "confidence", "fidelity_note"
                    ],
                    "additionalProperties": False,
                },
            },
            "batch_patterns": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "finding": {"type": "string"},
                        "case_ids": {"type": "array", "items": {"type": "string", "enum": expected_ids}},
                        "evidence_label": evidence,
                        "confidence": confidence,
                    },
                    "required": ["finding", "case_ids", "evidence_label", "confidence"],
                    "additionalProperties": False,
                },
            },
            "batch_limitations": {"type": "array", "items": {"type": "string"}},
            "batch_verdict": {"type": "string"},
        },
        "required": ["batch_id", "coverage", "cases", "batch_patterns", "batch_limitations", "batch_verdict"],
        "additionalProperties": False,
    }


def synthesis_schema(expected_ids: list[str]) -> dict:
    confidence = {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    evidence = {"type": "string", "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"]}
    ranked = {
        "type": "array",
        "minItems": 3,
        "maxItems": 10,
        "items": {
            "type": "object",
            "properties": {
                "rank": {"type": "integer"},
                "finding": {"type": "string"},
                "case_ids": {"type": "array", "items": {"type": "string", "enum": expected_ids}},
                "population_support": {"type": "string"},
                "evidence_label": evidence,
                "confidence": confidence,
            },
            "required": ["rank", "finding", "case_ids", "population_support", "evidence_label", "confidence"],
            "additionalProperties": False,
        },
    }
    return {
        "type": "object",
        "properties": {
            "owner_summary_vi": {"type": "string"},
            "run_identity": {"type": "string"},
            "validity_verdict": {"type": "string"},
            "economic_verdict": {"type": "string"},
            "coverage": {
                "type": "object",
                "properties": {
                    "expected_images": {"type": "integer", "const": 100},
                    "images_opened": {"type": "integer", "minimum": 0, "maximum": 100},
                    "trade_images": {"type": "integer", "const": 93},
                    "rejected_candidate_images": {"type": "integer", "const": 7},
                    "batches_complete": {"type": "integer", "minimum": 0, "maximum": 20},
                    "entry_parity_manifests_checked": {"type": "integer", "minimum": 0, "maximum": 100},
                    "all_case_ids_reconciled": {"type": "boolean"},
                },
                "required": [
                    "expected_images", "images_opened", "trade_images", "rejected_candidate_images",
                    "batches_complete", "entry_parity_manifests_checked", "all_case_ids_reconciled"
                ],
                "additionalProperties": False,
            },
            "case_ids_seen": {
                "type": "array", "minItems": 100, "maxItems": 100,
                "items": {"type": "string", "enum": expected_ids},
            },
            "ea_characteristics": {
                "type": "object",
                "properties": {
                    "core_identity": {"type": "string"},
                    "regime_state_machine": {"type": "string"},
                    "trend_branch": {"type": "string"},
                    "range_branch": {"type": "string"},
                    "entry_selectivity": {"type": "string"},
                    "risk_and_sizing": {"type": "string"},
                    "stop_target_and_time_exit": {"type": "string"},
                    "execution_and_cost": {"type": "string"},
                    "winner_profile": {"type": "string"},
                    "loser_profile": {"type": "string"},
                    "cadence_profile": {"type": "string"},
                    "fidelity_boundaries": {"type": "string"},
                },
                "required": [
                    "core_identity", "regime_state_machine", "trend_branch", "range_branch", "entry_selectivity",
                    "risk_and_sizing", "stop_target_and_time_exit", "execution_and_cost", "winner_profile",
                    "loser_profile", "cadence_profile", "fidelity_boundaries"
                ],
                "additionalProperties": False,
            },
            "indicator_findings": {
                "type": "object",
                "properties": {
                    "session_vwap_and_sd": {"type": "string"},
                    "anchored_vwap": {"type": "string"},
                    "adx_hysteresis": {"type": "string"},
                    "rsi": {"type": "string"},
                    "atr_and_sd_floor": {"type": "string"},
                    "m15_bias": {"type": "string"},
                },
                "required": ["session_vwap_and_sd", "anchored_vwap", "adx_hysteresis", "rsi", "atr_and_sd_floor", "m15_bias"],
                "additionalProperties": False,
            },
            "rejected_candidate_behavior": {"type": "string"},
            "ranked_strengths": ranked,
            "ranked_weaknesses": ranked,
            "source_and_fidelity_choke_points": ranked,
            "cannot_conclude": {"type": "array", "items": {"type": "string"}},
            "legal_next_hypotheses": {
                "type": "array", "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "mechanism": {"type": "string"},
                        "fresh_data_falsification": {"type": "string"},
                        "why_not_posthoc_rescue": {"type": "string"},
                    },
                    "required": ["title", "mechanism", "fresh_data_falsification", "why_not_posthoc_rescue"],
                    "additionalProperties": False,
                },
            },
            "terminal_conclusion": {"type": "string"},
            "full_report_markdown": {"type": "string"},
        },
        "required": [
            "owner_summary_vi", "run_identity", "validity_verdict", "economic_verdict", "coverage", "case_ids_seen",
            "ea_characteristics", "indicator_findings", "rejected_candidate_behavior", "ranked_strengths",
            "ranked_weaknesses", "source_and_fidelity_choke_points", "cannot_conclude", "legal_next_hypotheses",
            "terminal_conclusion", "full_report_markdown"
        ],
        "additionalProperties": False,
    }


def main() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    cases = pd.read_csv(CASES).set_index("case_id")
    image_rows: list[dict] = []
    for case_id in selection["case_ids"]:
        manifest_path = CHARTS / f"{case_id}_indicator_rich_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("entry_parity_pass") is not True or len(manifest.get("entry_parity", {})) != 9:
            raise RuntimeError(f"Entry parity is not 9/9 PASS for {case_id}")
        image_path = ROOT / manifest["image"]
        if sha256(image_path) != manifest["image_sha256"]:
            raise RuntimeError(f"Image hash mismatch for {case_id}")
        row = cases.loc[case_id]
        image_rows.append(
            {
                "case_id": case_id,
                "case_kind": row["case_kind"],
                "position_id": int(row["position_id"]),
                "event": row["event"],
                "stratum": row["stratum"],
                "context_reason": row["context_reason"],
                "entry_time_server": row["entry_time_server"],
                "exit_or_observation_end_server": row["exit_time_server"],
                "direction": int(row["direction"]),
                "entry": float(row["entry_price"]),
                "stop": float(row["stop_price"]),
                "target": float(row["target_price"]),
                "net_R": finite_or_none(row["net_R"]),
                "net_usd": finite_or_none(row["net_usd"]),
                "exit_class": row["exit_class"],
                "absolute_image_path": str(image_path),
                "image_sha256": manifest["image_sha256"],
                "absolute_entry_parity_manifest": str(manifest_path),
                "entry_parity_pass": True,
            }
        )
    if len(image_rows) != 100 or len({row["case_id"] for row in image_rows}) != 100:
        raise RuntimeError("Casebook must contain 100 unique images")

    casebook = {
        "schema_version": "vras_indicator_rich_casebook.v2",
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-003",
        "run_id": "20260722_103759",
        "image_count": 100,
        "executed_trade_image_count": 93,
        "rejected_candidate_image_count": 7,
        "economic_sample_size": 93,
        "all_entry_parity_pass_9_of_9": True,
        "anti_inflation_rule": selection["anti_inflation_rule"],
        "continuous_series_boundary": "Entry snapshot parity is exact; continuous trajectories outside entry are diagnostic and every chart is outcome-aware.",
        "images": image_rows,
    }
    CASEBOOK.write_text(json.dumps(casebook, indent=2), encoding="utf-8")
    CONTEXT.mkdir(parents=True, exist_ok=True)

    batch_summaries: list[str] = []
    batch_results: list[str] = []
    for batch_number in range(1, 21):
        batch_id = f"B{batch_number:02d}"
        rows = image_rows[(batch_number - 1) * 5 : batch_number * 5]
        expected_ids = [row["case_id"] for row in rows]
        batch_dir = CONTEXT / f"batch-{batch_number:02d}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        packet = {
            "schema_version": "vras_indicator_rich_batch.v2",
            "batch_id": batch_id,
            "casebook": str(CASEBOOK),
            "cases": rows,
        }
        packet_path = batch_dir / "batch_manifest.json"
        packet_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")
        result_path = batch_dir / "grok-analysis.json"
        schema_path = batch_dir / "result_schema.json"
        schema_path.write_text(json.dumps(batch_schema(batch_id, expected_ids), indent=2), encoding="utf-8")
        prompt = (
            f"Autonomously perform read-only chart forensics for VRAS batch {batch_id}. Read batch manifest {packet_path}, "
            f"the full casebook {CASEBOOK}, frozen selection {SELECTION}, prereg {PREREG}, logic matrix {LOGIC}, terminal "
            f"population readout {READOUT}, exact source {SOURCE}, run manifest {RUN_MANIFEST}, lifecycle {LIFECYCLE}, and RunMeta {RUN_META}. "
            "Open all five absolute_image_path files and check all five entry-parity manifests. Inspect price/VWAP surface, "
            "ADX, RSI, ATR/SD, M15 bias, decision geometry, and subsequent path. For TRADE cases explain win/loss mechanism; "
            "for REJECTED_CANDIDATE cases explain only the gate and observed post-reject path, never counterfactual PnL. Keep "
            "each case concise but specific. Do not edit files, tune, rerun, rescue, or make frequency estimates from this batch. "
            "The 93 trades are the full economic population; seven rejects are diagnostics only. During the investigation, do not "
            "emit progress, draft JSON, or placeholder fields. Use tool calls and internal reasoning until the work is complete. You "
            f"may write exactly one artifact and no other file: {result_path}. Its required JSON Schema is {schema_path}. Write it only "
            "after opening all images and completing the analysis. Then respond with one short completion sentence pointing to that file. "
            f"Exact ordered IDs: {expected_ids}."
        )
        request = {
            "task": f"vras-003-indicator-rich-{batch_id.lower()}",
            "request": {
                "model": "grok-4.5",
                "reasoning_effort": "high",
                "input": [
                    {"role": "system", "content": "You are an autonomous quantitative chart-forensics reviewer. Own this five-image packet and distinguish observation from inference. Do not edit product/research files; your only authorized write is the explicitly named grok-analysis.json result artifact."},
                    {"role": "user", "content": prompt},
                ],
            },
            "meta": {
                "authority": "ADVISORY_FORENSICS_ONLY",
                "batch_id": batch_id,
                "expected_case_ids": expected_ids,
                "expected_position_ids": [row["position_id"] for row in rows],
                "batch_manifest_sha256": sha256(packet_path),
            },
        }
        (batch_dir / "grok-request.json").write_text(json.dumps(request, indent=2), encoding="utf-8")
        batch_summaries.append(str(batch_dir / "summary.json"))
        batch_results.append(str(result_path))

    expected_ids = [row["case_id"] for row in image_rows]
    synthesis_dir = CONTEXT / "synthesis"
    synthesis_dir.mkdir(parents=True, exist_ok=True)
    synthesis_result = synthesis_dir / "grok-synthesis.json"
    synthesis_schema_path = synthesis_dir / "result_schema.json"
    synthesis_schema_path.write_text(json.dumps(synthesis_schema(expected_ids), indent=2), encoding="utf-8")
    synthesis_prompt = (
        "Own the final autonomous synthesis of the VRAS 100-image review. Read all twenty Grok batch analysis files and their runner "
        "summaries listed below, "
        f"plus casebook {CASEBOOK}, selection {SELECTION}, prereg {PREREG}, logic matrix {LOGIC}, terminal readout {READOUT}, exact "
        f"source {SOURCE}, run manifest {RUN_MANIFEST}, lifecycle {LIFECYCLE}, and RunMeta {RUN_META}. Batch analyses: {batch_results}. "
        f"Runner summaries: {batch_summaries}. First fail closed unless every runner summary is useful EndTurn success and every batch "
        "analysis reports coverage 5/5, all five image_opened values true, exact IDs reconcile once, and all five parity manifests checked. "
        "Then synthesize the EA's actual behavioral "
        "characteristics across the full 93-trade census and the seven separately labelled rejected-candidate diagnostics. Explain "
        "indicator roles and trajectories, regime state machine, entry selectivity, risk/exit anatomy, winner versus loser profiles, "
        "execution/cost and fidelity choke points, strengths, weaknesses, and what cannot be concluded. Use terminal population metrics "
        "for frequency/economics; never treat the seven rejects as trades. The object remains terminal KILL and promotion-ineligible. "
        "No threshold tuning, session/year veto, rerun, source edit, or post-hoc rescue. owner_summary_vi must be Vietnamese and the full "
        "report English Markdown. case_ids_seen must contain each of the exact 100 IDs once, in casebook order. During investigation, "
        f"do not emit progress, draft JSON, or placeholders. You may write exactly one artifact and no other file: {synthesis_result}. "
        f"Its required JSON Schema is {synthesis_schema_path}. Write it only after the complete synthesis, then respond with one short "
        "completion sentence pointing to that file."
    )
    synthesis_request = {
        "task": "vras-003-indicator-rich-100-synthesis",
        "request": {
            "model": "grok-4.5",
            "reasoning_effort": "high",
            "input": [
                {"role": "system", "content": "You are the autonomous lead quantitative forensic synthesizer. Verify coverage first, then own the final evidence report without post-hoc rescue. Do not edit product/research files; your only authorized write is the explicitly named grok-synthesis.json result artifact."},
                {"role": "user", "content": synthesis_prompt},
            ],
        },
        "meta": {
            "authority": "ADVISORY_SYNTHESIS_ONLY",
            "expected_case_ids": expected_ids,
            "expected_batch_summaries": batch_summaries,
            "expected_batch_results": batch_results,
            "casebook_sha256": sha256(CASEBOOK),
        },
    }
    (synthesis_dir / "grok-request.json").write_text(json.dumps(synthesis_request, indent=2), encoding="utf-8")
    print(json.dumps({"status": "VRAS_GROK_100_REQUESTS_READY", "images": 100, "batches": 20, "casebook": str(CASEBOOK), "context": str(CONTEXT)}, indent=2))


if __name__ == "__main__":
    main()
