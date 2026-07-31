#!/usr/bin/env python3
"""Assemble ten parity-checked indicator-rich charts into one Grok task."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-003_GROK_CHART_FORENSICS_10"
CHARTS = EVIDENCE / "indicator_rich_v2"
SELECTION = EVIDENCE / "selection_manifest.json"
CASES = EVIDENCE / "cases_selected_10.csv"
READOUT = RESEARCH / "HYP-VRAS-EURUSD-M5-003_READOUT.md"
PREREG = RESEARCH / "HYP-VRAS-EURUSD-M5-003_FROZEN_PREREG.md"
LOGIC = RESEARCH / "LOGIC_TO_CODE_MATRIX.md"
RUN = ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_RegimeAdaptiveScalperV3" / "20260722_103759"
SOURCE = RUN / "snapshot" / "source" / "EA_VRAS_RegimeAdaptiveScalperV3.mq5"
RUN_MANIFEST = RUN / "run_manifest.json"
LIFECYCLE = next((RUN / "logs").glob("*LifecycleTrades*.csv"))
RUN_META = next((RUN / "logs").glob("*RunMeta*.json"))
CONTEXT = ROOT / ".context" / "vras-003-grok-indicator-rich-10-20260722"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def response_schema() -> dict:
    confidence = {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}
    evidence = {
        "type": "string",
        "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"],
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
                    "expected_images": {"type": "integer", "const": 10},
                    "images_opened": {"type": "integer", "minimum": 0, "maximum": 10},
                    "all_cases_reported": {"type": "boolean"},
                    "entry_parity_manifests_checked": {"type": "integer", "minimum": 0, "maximum": 10},
                },
                "required": [
                    "expected_images",
                    "images_opened",
                    "all_cases_reported",
                    "entry_parity_manifests_checked",
                ],
                "additionalProperties": False,
            },
            "cases": {
                "type": "array",
                "minItems": 10,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string"},
                        "position_id": {"type": "integer"},
                        "image_opened": {"type": "boolean"},
                        "setup_and_price_location": {"type": "string"},
                        "indicator_state_at_entry": {"type": "string"},
                        "pre_entry_indicator_behavior": {"type": "string"},
                        "outcome_path": {"type": "string"},
                        "win_or_loss_mechanism": {"type": "string"},
                        "evidence_label": evidence,
                        "confidence": confidence,
                        "fidelity_note": {"type": "string"},
                    },
                    "required": [
                        "case_id",
                        "position_id",
                        "image_opened",
                        "setup_and_price_location",
                        "indicator_state_at_entry",
                        "pre_entry_indicator_behavior",
                        "outcome_path",
                        "win_or_loss_mechanism",
                        "evidence_label",
                        "confidence",
                        "fidelity_note",
                    ],
                    "additionalProperties": False,
                },
            },
            "ea_characteristics": {
                "type": "object",
                "properties": {
                    "core_identity": {"type": "string"},
                    "regime_state_machine": {"type": "string"},
                    "trend_branch": {"type": "string"},
                    "range_branch": {"type": "string"},
                    "vwap_system": {"type": "string"},
                    "adx_behavior": {"type": "string"},
                    "rsi_behavior": {"type": "string"},
                    "volatility_behavior": {"type": "string"},
                    "m15_bias_behavior": {"type": "string"},
                    "risk_and_sizing": {"type": "string"},
                    "stop_target_and_hold": {"type": "string"},
                    "winner_profile": {"type": "string"},
                    "loser_profile": {"type": "string"},
                    "execution_and_cost_profile": {"type": "string"},
                    "cadence_and_selectivity": {"type": "string"},
                    "fidelity_boundaries": {"type": "string"},
                },
                "required": [
                    "core_identity",
                    "regime_state_machine",
                    "trend_branch",
                    "range_branch",
                    "vwap_system",
                    "adx_behavior",
                    "rsi_behavior",
                    "volatility_behavior",
                    "m15_bias_behavior",
                    "risk_and_sizing",
                    "stop_target_and_hold",
                    "winner_profile",
                    "loser_profile",
                    "execution_and_cost_profile",
                    "cadence_and_selectivity",
                    "fidelity_boundaries",
                ],
                "additionalProperties": False,
            },
            "ranked_strengths": {
                "type": "array",
                "minItems": 2,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer"},
                        "characteristic": {"type": "string"},
                        "case_ids": {"type": "array", "items": {"type": "string"}},
                        "evidence_label": evidence,
                        "confidence": confidence,
                    },
                    "required": ["rank", "characteristic", "case_ids", "evidence_label", "confidence"],
                    "additionalProperties": False,
                },
            },
            "ranked_weaknesses": {
                "type": "array",
                "minItems": 3,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer"},
                        "characteristic": {"type": "string"},
                        "case_ids": {"type": "array", "items": {"type": "string"}},
                        "population_support": {"type": "string"},
                        "evidence_label": evidence,
                        "confidence": confidence,
                    },
                    "required": [
                        "rank",
                        "characteristic",
                        "case_ids",
                        "population_support",
                        "evidence_label",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "matched_comparisons": {
                "type": "array",
                "minItems": 1,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "properties": {
                        "case_ids": {"type": "array", "minItems": 2, "items": {"type": "string"}},
                        "shared_traits": {"type": "string"},
                        "observed_difference": {"type": "string"},
                        "what_disappears_after_matching": {"type": "string"},
                        "confidence": confidence,
                    },
                    "required": [
                        "case_ids",
                        "shared_traits",
                        "observed_difference",
                        "what_disappears_after_matching",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "logic_and_fidelity_choke_points": {
                "type": "array",
                "minItems": 3,
                "maxItems": 8,
                "items": {
                    "type": "object",
                    "properties": {
                        "source_location": {"type": "string"},
                        "artifact_evidence": {"type": "string"},
                        "mechanism": {"type": "string"},
                        "alternative_explanation": {"type": "string"},
                        "confidence": confidence,
                    },
                    "required": [
                        "source_location",
                        "artifact_evidence",
                        "mechanism",
                        "alternative_explanation",
                        "confidence",
                    ],
                    "additionalProperties": False,
                },
            },
            "cannot_conclude": {"type": "array", "items": {"type": "string"}},
            "legal_next_hypotheses": {
                "type": "array",
                "maxItems": 3,
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
            "owner_summary_vi",
            "run_identity",
            "validity_verdict",
            "economic_verdict",
            "coverage",
            "cases",
            "ea_characteristics",
            "ranked_strengths",
            "ranked_weaknesses",
            "matched_comparisons",
            "logic_and_fidelity_choke_points",
            "cannot_conclude",
            "legal_next_hypotheses",
            "terminal_conclusion",
            "full_report_markdown",
        ],
        "additionalProperties": False,
    }


def main() -> None:
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    cases = pd.read_csv(CASES).set_index("case_id")
    images: list[dict] = []
    for case_id in selection["case_ids"]:
        manifest_path = CHARTS / f"{case_id}_indicator_rich_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("entry_parity_pass") is not True:
            raise RuntimeError(f"Entry parity is not PASS for {case_id}")
        image_path = ROOT / manifest["image"]
        if sha256(image_path) != manifest["image_sha256"]:
            raise RuntimeError(f"Image hash mismatch for {case_id}")
        row = cases.loc[case_id]
        images.append(
            {
                "case_id": case_id,
                "position_id": int(row["position_id"]),
                "stratum": row["stratum"],
                "event": row["event"],
                "direction": int(row["direction"]),
                "entry_time_server": row["entry_time_server"],
                "exit_time_server": row["exit_time_server"],
                "entry": float(row["entry_price"]),
                "stop": float(row["stop_price"]),
                "target": float(row["target_price"]),
                "exit": float(row["exit_price"]),
                "net_R": float(row["net_R"]),
                "net_usd": float(row["net_usd"]),
                "context_reason": row["context_reason"],
                "absolute_image_path": str(image_path),
                "image_sha256": manifest["image_sha256"],
                "absolute_entry_parity_manifest": str(manifest_path),
                "entry_parity_pass": True,
            }
        )
    if len(images) != 10 or len({item["case_id"] for item in images}) != 10:
        raise RuntimeError("Indicator-rich casebook must contain ten unique cases")

    casebook = {
        "schema_version": "vras_indicator_rich_casebook.v1",
        "hypothesis_id": "HYP-VRAS-EURUSD-M5-003",
        "run_id": "20260722_103759",
        "sample_frozen_before_original_chart_view": True,
        "image_count": 10,
        "all_entry_parity_pass": True,
        "source_m1_clock": "broker_server_time",
        "continuous_series_boundary": "Parity-proven at entry; diagnostic outside the exact entry snapshot; outcome-aware images.",
        "images": images,
    }
    casebook_path = CHARTS / "indicator_rich_casebook_manifest.json"
    casebook_path.write_text(json.dumps(casebook, indent=2), encoding="utf-8")

    expected_ids = [item["case_id"] for item in images]
    expected_positions = [item["position_id"] for item in images]
    prompt = (
        "Own this complete read-only forensic review. Analyze exactly ten parity-checked indicator-rich charts for "
        "EA_VRAS_RegimeAdaptiveScalperV3 / HYP-VRAS-EURUSD-M5-003. Read the indicator-rich casebook "
        f"{casebook_path}, frozen selection {SELECTION}, frozen prereg {PREREG}, logic matrix {LOGIC}, terminal readout {READOUT}, "
        f"exact source {SOURCE}, run manifest {RUN_MANIFEST}, lifecycle {LIFECYCLE}, and RunMeta {RUN_META}. "
        "Open every absolute_image_path and inspect its price/VWAP surface, ADX, RSI, ATR/SD, M5/M15 VWAP-bias panel, "
        "entry/SL/TP/exit and pre/post-entry path. Check each entry parity manifest. Determine the EA's defining behavioral "
        "characteristics, indicator roles, regime behavior, winner and loser anatomy, matched contrasts, risk/exit profile, "
        "strengths, weaknesses, fidelity choke points and what cannot be inferred. Reconcile chart anecdotes to the 93-trade "
        "population; never use the stratified 10-case sample as a frequency estimate. The EA is terminal KILL and promotion-ineligible. "
        "Do not edit files, rerun MT5, tune thresholds, prescribe session/year vetoes, or rescue the killed object. Future ideas, if any, "
        "must be new mechanism-level hypotheses for fresh preregistered data. Write owner_summary_vi in Vietnamese and the full evidence "
        "report in English Markdown. Work autonomously and return only after all ten images are genuinely opened. "
        f"Expected case IDs in order: {expected_ids}; expected position IDs: {expected_positions}."
    )
    request = {
        "task": "vras-003-grok-indicator-rich-autonomous-10",
        "request": {
            "model": "grok-4.5",
            "reasoning_effort": "high",
            "input": [
                {
                    "role": "system",
                    "content": (
                        "You are the autonomous read-only lead quantitative forensic reviewer. Use only local bound evidence, "
                        "open all requested images, distinguish OBSERVED/STRONG_INFERENCE/HYPOTHESIS/UNKNOWN, and own the final report."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "vras_indicator_rich_autonomous_forensics",
                    "schema": response_schema(),
                },
            },
        },
        "meta": {
            "purpose": "Autonomous Grok review of ten VRAS indicator-rich charts",
            "authority": "ADVISORY_FORENSICS_ONLY",
            "expected_case_ids": expected_ids,
            "expected_position_ids": expected_positions,
            "casebook_sha256": sha256(casebook_path),
        },
    }
    CONTEXT.mkdir(parents=True, exist_ok=True)
    request_path = CONTEXT / "grok-request.json"
    request_path.write_text(json.dumps(request, indent=2), encoding="utf-8")
    print(json.dumps({"status": "VRAS_INDICATOR_RICH_GROK_REQUEST_READY", "images": 10, "casebook": str(casebook_path), "request": str(request_path)}, indent=2))


if __name__ == "__main__":
    main()
