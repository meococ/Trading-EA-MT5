#!/usr/bin/env python3
"""Build fail-closed, schema-constrained Grok requests for HYP008 forensics.

Pass A receives only five decision-as-of images and an outcome-free manifest.
Pass B is stateless and receives the accepted Pass-A packet plus the matching
five anatomy images.  Synthesis is available only after all forty batch outputs
have been accepted by ``validate_hyp008_grok_forensics.py``.

This module never calls Grok or MT5 and never changes the frozen sample.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
PACKAGE = RESEARCH.parent
EVIDENCE = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100"
SELECTION = EVIDENCE / "selection_manifest.json"
CASES_CSV = EVIDENCE / "cases_random_100.csv"
CHART_MANIFEST = EVIDENCE / "chart_manifest.json"
POPULATION = EVIDENCE / "population_forensic_supplement.json"
WEEKEND_TAILS = EVIDENCE / "weekend_tail_supplement.csv"
PLAN = RESEARCH / "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100_FORENSIC_PLAN.md"
READOUT_JSON = RESEARCH / "HYP-VRAS-EURUSD-M5-008_READOUT.json"
READOUT_MD = RESEARCH / "HYP-VRAS-EURUSD-M5-008_READOUT.md"
FORENSIC_ANALYSIS = RESEARCH / "HYP-VRAS-EURUSD-M5-008_FORENSIC_ANALYSIS.md"
NONREPAINT = RESEARCH / "evidence" / "HYP-VRAS-EURUSD-M5-008_NONREPAINT_AUDIT.json"
CONTEXT = ROOT / ".context" / "vras-hyp008-grok-random100"
VALIDATED = CONTEXT / "validated"

CAMPAIGN_ID = "HYP-VRAS-EURUSD-M5-008_GROK_RANDOM100"
HYPOTHESIS_ID = "HYP-VRAS-EURUSD-M5-008"
RUN_ID = "20260722_233420"
SOURCE = (
    ROOT / "02. AlphaFactory" / "runs" / "EA_VRAS_VolatilityNormalizedStop"
    / RUN_ID / "snapshot" / "source" / "EA_VRAS_VolatilityNormalizedStop.mq5"
)
JOB_SIZE = 5
JOB_COUNT = 20


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def resolve_bound_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")


def verify_binding(path: Path, expected: str, label: str) -> None:
    require_file(path, label)
    actual = sha256_file(path)
    if actual != expected.upper():
        raise RuntimeError(
            f"{label} SHA256 mismatch: expected={expected.upper()} actual={actual} path={path}"
        )


def load_selection() -> dict[str, Any]:
    require_file(SELECTION, "frozen selection manifest")
    selection = load_json(SELECTION)
    if selection.get("hypothesis_id") != HYPOTHESIS_ID or selection.get("run_id") != RUN_ID:
        raise RuntimeError("selection identity does not match HYP008 challenger run")
    case_ids = selection.get("case_ids")
    positions = selection.get("position_ids")
    if not isinstance(case_ids, list) or not isinstance(positions, list):
        raise RuntimeError("selection must contain case_ids and position_ids lists")
    if len(case_ids) != 100 or len(positions) != 100:
        raise RuntimeError(
            f"selection must remain exact random-100, got cases={len(case_ids)} positions={len(positions)}"
        )
    if len(set(map(str, case_ids))) != 100 or len(set(map(int, positions))) != 100:
        raise RuntimeError("selection case/position IDs are not unique")
    cases_binding = (selection.get("bindings") or {}).get("cases_csv") or {}
    if cases_binding.get("path") and cases_binding.get("sha256"):
        bound = resolve_bound_path(cases_binding["path"])
        if bound != CASES_CSV.resolve():
            raise RuntimeError(f"selection binds unexpected cases CSV: {bound}")
        verify_binding(bound, str(cases_binding["sha256"]), "cases CSV")
    return selection


def load_case_rows(selection: dict[str, Any]) -> dict[str, dict[str, str]]:
    require_file(CASES_CSV, "random-100 cases CSV")
    rows: dict[str, dict[str, str]] = {}
    with CASES_CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            case_id = str(row.get("case_id") or "")
            if not case_id or case_id in rows:
                raise RuntimeError(f"blank or duplicate case_id in cases CSV: {case_id!r}")
            rows[case_id] = dict(row)
    expected = list(map(str, selection["case_ids"]))
    if set(rows) != set(expected) or len(rows) != 100:
        raise RuntimeError("cases CSV does not exactly match frozen selection case union")
    for case_id, position in zip(expected, selection["position_ids"], strict=True):
        if int(float(rows[case_id]["position_id"])) != int(position):
            raise RuntimeError(f"position mismatch for {case_id}")
    return rows


def _layer(case: dict[str, Any], name: str, case_id: str) -> dict[str, Any]:
    value = case.get(name)
    if not isinstance(value, dict):
        raise RuntimeError(f"chart manifest {case_id} missing object {name}")
    if not value.get("path") or not value.get("sha256"):
        raise RuntimeError(f"chart manifest {case_id}.{name} needs path and sha256")
    path = resolve_bound_path(str(value["path"]))
    if path.suffix.lower() != ".png":
        raise RuntimeError(f"{case_id}.{name} is not PNG: {path}")
    verify_binding(path, str(value["sha256"]), f"{case_id}.{name} image")
    return {"path": str(path), "sha256": sha256_file(path)}


def load_charts(selection: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require_file(
        CHART_MANIFEST,
        "chart manifest (run the sibling renderer before request generation)",
    )
    manifest = load_json(CHART_MANIFEST)
    if manifest.get("schema_version") != "vras_hyp008_random100_charts.v1":
        raise RuntimeError(f"unexpected chart manifest schema: {manifest.get('schema_version')!r}")
    if int(manifest.get("case_count", -1)) != 100 or int(manifest.get("image_count", -1)) != 200:
        raise RuntimeError("chart manifest must declare case_count=100 and image_count=200")
    if list(map(str, manifest.get("case_ids") or [])) != list(map(str, selection["case_ids"])):
        raise RuntimeError("chart manifest top-level case_ids do not match frozen draw order")
    if not isinstance(manifest.get("input_bindings"), dict):
        raise RuntimeError("chart manifest lacks input_bindings object")
    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list):
        raise RuntimeError("chart_manifest.json must contain a cases list")
    by_id: dict[str, dict[str, Any]] = {}
    image_paths: list[str] = []
    for raw in raw_cases:
        if not isinstance(raw, dict):
            raise RuntimeError("chart manifest case must be an object")
        case_id = str(raw.get("case_id") or "")
        if not case_id or case_id in by_id:
            raise RuntimeError(f"blank or duplicate chart case_id: {case_id!r}")
        parity = raw.get("parity")
        if not isinstance(parity, dict):
            raise RuntimeError(f"chart manifest {case_id} missing parity object")
        required_parity = {
            "status": "PASS",
            "telemetry_status": "ORDER_ACCEPTED",
            "lifecycle_open_final_close": "PASS",
            "tester_report_close_comment": "PASS",
        }
        if any(parity.get(key) != value for key, value in required_parity.items()):
            raise RuntimeError(f"chart manifest {case_id} parity is not exact PASS: {parity}")
        decision_raw = raw.get("decision_asof") or {}
        anatomy_raw = raw.get("anatomy") or {}
        if decision_raw.get("case_id") != case_id or int(decision_raw.get("position_id", -1)) != int(raw["position_id"]):
            raise RuntimeError(f"chart manifest {case_id} decision identity mismatch")
        if anatomy_raw.get("case_id") != case_id or int(anatomy_raw.get("position_id", -1)) != int(raw["position_id"]):
            raise RuntimeError(f"chart manifest {case_id} anatomy identity mismatch")
        decision_contract = decision_raw.get("png_contract") or {}
        if (
            decision_raw.get("outcome_hidden") is not True
            or int(decision_raw.get("post_entry_bars", -1)) != 0
            or decision_contract.get("mode") != "decision_asof"
            or decision_contract.get("outcome_hidden") is not True
        ):
            raise RuntimeError(f"chart manifest {case_id} decision image may leak future/outcome")
        anatomy_contract = anatomy_raw.get("png_contract") or {}
        if anatomy_raw.get("outcome_aware") is not True or anatomy_contract.get("mode") != "anatomy":
            raise RuntimeError(f"chart manifest {case_id} anatomy contract mismatch")
        decision = _layer(raw, "decision_asof", case_id)
        anatomy = _layer(raw, "anatomy", case_id)
        image_paths.extend([decision["path"], anatomy["path"]])
        by_id[case_id] = {
            "case_id": case_id,
            "position_id": int(raw["position_id"]),
            "decision_asof": decision,
            "anatomy": anatomy,
            "parity": parity,
        }
    expected_ids = list(map(str, selection["case_ids"]))
    if len(by_id) != 100 or set(by_id) != set(expected_ids):
        raise RuntimeError("chart manifest must match the exact frozen 100-case union")
    for case_id, position in zip(expected_ids, selection["position_ids"], strict=True):
        if by_id[case_id]["position_id"] != int(position):
            raise RuntimeError(f"chart manifest position mismatch for {case_id}")
    if len(image_paths) != 200 or len(set(image_paths)) != 200:
        raise RuntimeError("chart manifest must bind exactly 200 distinct images")
    return by_id


def evidence_label_schema() -> dict[str, Any]:
    return {
        "type": "string",
        "enum": ["OBSERVED", "STRONG_INFERENCE", "HYPOTHESIS", "UNKNOWN"],
    }


def confidence_schema() -> dict[str, Any]:
    return {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]}


def pass_a_schema(job_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "campaign_id": {"type": "string", "const": CAMPAIGN_ID},
            "pass_id": {"type": "string", "const": "A"},
            "job_id": {"type": "string", "const": job_id},
            "outcome_blind": {"type": "boolean", "const": True},
            "coverage": {
                "type": "object",
                "properties": {
                    "expected_cases": {"type": "integer", "const": 5},
                    "expected_images": {"type": "integer", "const": 5},
                    "images_opened": {"type": "integer", "const": 5},
                    "all_cases_reported": {"type": "boolean", "const": True},
                },
                "required": ["expected_cases", "expected_images", "images_opened", "all_cases_reported"],
                "additionalProperties": False,
            },
            "cases": {
                "type": "array", "minItems": 5, "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string"},
                        "position_id": {"type": "integer"},
                        "image_opened": {"type": "boolean", "const": True},
                        "decision_context_summary": {"type": "string"},
                        "setup_geometry_observed": {"type": "string"},
                        "trend_location_observed": {"type": "string"},
                        "volatility_liquidity_context": {"type": "string"},
                        "entry_risk_flags": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                        "quality_assessment": {"type": "string", "enum": ["FAVORABLE", "MIXED", "ADVERSE", "UNKNOWN"]},
                        "evidence_label": evidence_label_schema(),
                        "confidence": confidence_schema(),
                        "unknowns": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": [
                        "case_id", "position_id", "image_opened", "decision_context_summary",
                        "setup_geometry_observed", "trend_location_observed",
                        "volatility_liquidity_context", "entry_risk_flags",
                        "quality_assessment", "evidence_label", "confidence", "unknowns",
                    ],
                    "additionalProperties": False,
                },
            },
            "recurring_blind_patterns": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            "limitations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["campaign_id", "pass_id", "job_id", "outcome_blind", "coverage", "cases", "recurring_blind_patterns", "limitations"],
        "additionalProperties": False,
    }


def pass_b_schema(job_id: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "campaign_id": {"type": "string", "const": CAMPAIGN_ID},
            "pass_id": {"type": "string", "const": "B"},
            "job_id": {"type": "string", "const": job_id},
            "stateless": {"type": "boolean", "const": True},
            "blind_output_read": {"type": "boolean", "const": True},
            "coverage": {
                "type": "object",
                "properties": {
                    "expected_cases": {"type": "integer", "const": 5},
                    "expected_images": {"type": "integer", "const": 5},
                    "images_opened": {"type": "integer", "const": 5},
                    "all_cases_reported": {"type": "boolean", "const": True},
                },
                "required": ["expected_cases", "expected_images", "images_opened", "all_cases_reported"],
                "additionalProperties": False,
            },
            "cases": {
                "type": "array", "minItems": 5, "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "case_id": {"type": "string"},
                        "position_id": {"type": "integer"},
                        "image_opened": {"type": "boolean", "const": True},
                        "blind_assessment_reconciled": {"type": "string"},
                        "actual_path_observed": {"type": "string"},
                        "exit_mechanism_observed": {"type": "string", "enum": ["INITIAL_SL", "MOVED_SL", "TARGET", "TIME_EXIT", "UNKNOWN"]},
                        "winner_loser_anatomy": {"type": "string"},
                        "matched_context_contrast": {"type": "string"},
                        "what_survives_outcome_view": {"type": "string"},
                        "evidence_label": evidence_label_schema(),
                        "confidence": confidence_schema(),
                        "fidelity_note": {"type": "string"},
                    },
                    "required": [
                        "case_id", "position_id", "image_opened", "blind_assessment_reconciled",
                        "actual_path_observed", "exit_mechanism_observed", "winner_loser_anatomy",
                        "matched_context_contrast", "what_survives_outcome_view",
                        "evidence_label", "confidence", "fidelity_note",
                    ],
                    "additionalProperties": False,
                },
            },
            "job_failure_mechanisms": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            "traits_disappearing_after_outcome_check": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
            "limitations": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["campaign_id", "pass_id", "job_id", "stateless", "blind_output_read", "coverage", "cases", "job_failure_mechanisms", "traits_disappearing_after_outcome_check", "limitations"],
        "additionalProperties": False,
    }


def synthesis_schema() -> dict[str, Any]:
    limitation_keys = [
        "stripped_proxy_not_full_vras",
        "server_and_utc_fixed",
        "exit_reason_report_bound",
        "moved_sl_not_be_timing_proof",
        "random100_one_weekend_full_population_tails_used",
        "matched_pair_binary_hash_validity_partial",
        "rejects_absent_from_random100",
        "threshold_tuning_prohibited",
    ]
    limitations = {
        "type": "object",
        "properties": {key: {"type": "boolean", "const": True} for key in limitation_keys},
        "required": limitation_keys,
        "additionalProperties": False,
    }
    mechanism = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "mechanism": {"type": "string"},
            "required_new_information_or_state": {"type": "string"},
            "fresh_falsification_test": {"type": "string"},
            "why_not_posthoc_rescue": {"type": "string"},
            "confidence": confidence_schema(),
        },
        "required": ["title", "mechanism", "required_new_information_or_state", "fresh_falsification_test", "why_not_posthoc_rescue", "confidence"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "campaign_id": {"type": "string", "const": CAMPAIGN_ID},
            "hypothesis_id": {"type": "string", "const": HYPOTHESIS_ID},
            "run_id": {"type": "string", "const": RUN_ID},
            "coverage": {
                "type": "object",
                "properties": {
                    "pass_a_jobs": {"type": "integer", "const": 20},
                    "pass_b_jobs": {"type": "integer", "const": 20},
                    "validated_outputs_read": {"type": "integer", "const": 40},
                    "pass_a_cases": {"type": "integer", "const": 100},
                    "pass_b_cases": {"type": "integer", "const": 100},
                    "images_opened": {"type": "integer", "const": 200},
                    "same_case_union": {"type": "boolean", "const": True},
                },
                "required": ["pass_a_jobs", "pass_b_jobs", "validated_outputs_read", "pass_a_cases", "pass_b_cases", "images_opened", "same_case_union"],
                "additionalProperties": False,
            },
            "case_ids_seen": {
                "type": "array",
                "const": list(map(str, load_selection()["case_ids"])),
            },
            "validity_verdict": {"type": "string"},
            "economic_verdict": {"type": "string"},
            "ranked_failure_mechanisms": {
                "type": "array", "minItems": 3, "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "rank": {"type": "integer", "minimum": 1, "maximum": 3},
                        "mechanism": {"type": "string"},
                        "population_support": {"type": "string"},
                        "random100_support": {"type": "string"},
                        "confidence": confidence_schema(),
                        "alternative_explanation": {"type": "string"},
                    },
                    "required": ["rank", "mechanism", "population_support", "random100_support", "confidence", "alternative_explanation"],
                    "additionalProperties": False,
                },
            },
            "winner_loser_anatomy": {"type": "string"},
            "matched_context_conclusion": {"type": "string"},
            "logic_and_fidelity_choke_points": {"type": "array", "items": {"type": "string"}},
            "cannot_conclude": {"type": "array", "items": {"type": "string"}},
            "fresh_mechanism_hypotheses": {"type": "array", "maxItems": 3, "items": mechanism},
            "proposed_parameter_changes": {"type": "array", "maxItems": 0},
            "limitations_acknowledged": limitations,
            "owner_summary_vi": {"type": "string"},
            "full_report_markdown": {"type": "string"},
            "promotion_blocked": {"type": "boolean", "const": True},
            "post_hoc_rescue_blocked": {"type": "boolean", "const": True},
        },
        "required": [
            "campaign_id", "hypothesis_id", "run_id", "coverage", "case_ids_seen",
            "validity_verdict", "economic_verdict", "ranked_failure_mechanisms",
            "winner_loser_anatomy", "matched_context_conclusion",
            "logic_and_fidelity_choke_points", "cannot_conclude",
            "fresh_mechanism_hypotheses", "proposed_parameter_changes", "limitations_acknowledged",
            "owner_summary_vi", "full_report_markdown", "promotion_blocked",
            "post_hoc_rescue_blocked",
        ],
        "additionalProperties": False,
    }


def _request(task: str, system: str, prompt: str, schema_name: str, schema: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "task": task,
        "request": {
            "reasoning_effort": "high",
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": schema},
            },
        },
        "meta": meta,
    }


def _write_request(output_dir: Path, request: dict[str, Any], job_input: dict[str, Any] | None = None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=False)
    if job_input is not None:
        input_path = output_dir / "job_input.json"
        input_path.write_text(json.dumps(job_input, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        request["meta"]["input_files"].append({"path": str(input_path), "sha256": sha256_file(input_path)})
    request_path = output_dir / "grok-request.json"
    request_path.write_text(json.dumps(request, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return request_path


def _job_slice(selection: dict[str, Any], job_number: int) -> tuple[str, list[str], list[int]]:
    if not 1 <= job_number <= JOB_COUNT:
        raise ValueError(f"job must be in 1..{JOB_COUNT}: {job_number}")
    start = (job_number - 1) * JOB_SIZE
    job_id = f"job-{job_number:02d}"
    return job_id, list(map(str, selection["case_ids"][start:start + 5])), list(map(int, selection["position_ids"][start:start + 5]))


def build_pass_a(output_dir: Path, job_number: int) -> Path:
    selection = load_selection()
    rows = load_case_rows(selection)  # parent-side read; only whitelisted entry fields leave here
    charts = load_charts(selection)
    job_id, case_ids, positions = _job_slice(selection, job_number)
    blind_fields = [
        "case_id", "position_id", "entry_time_server", "entry_time_utc",
        "server_utc_offset_h", "direction", "side", "entry", "sl", "tp",
        "h1_close", "h1_ema", "rolling_vwap_48", "atr14", "spread_pips",
    ]
    blind_cases: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    for case_id, position in zip(case_ids, positions, strict=True):
        image = {"case_id": case_id, "position_id": position, **charts[case_id]["decision_asof"]}
        images.append(image)
        blind = {key: rows[case_id].get(key, "") for key in blind_fields}
        blind["case_id"] = case_id
        blind["position_id"] = position
        blind["decision_asof"] = image
        blind_cases.append(blind)
    job_input = {
        "schema_version": "vras_hyp008_pass_a_input.v1",
        "campaign_id": CAMPAIGN_ID,
        "pass_id": "A",
        "job_id": job_id,
        "outcome_blind": True,
        "cases": blind_cases,
        "prohibited": [
            "outcomes", "net_r", "exit reason", "future bars", "anatomy images",
            "selection composition", "other local evidence files",
        ],
    }
    image_lines = "\n".join(f"- {x['case_id']} | position_id={x['position_id']} | PNG={x['path']}" for x in images)
    prompt = (
        f"Review exactly five frozen decision-as-of EURUSD M5 charts for {job_id}.\n"
        "Open every PNG. The charts end at entry and intentionally hide outcomes. Do not inspect "
        "the repository, selection CSV, chart manifest, anatomy images, future bars, reports, or any "
        "other file. Do not guess whether a case won or lost.\n\n"
        f"Outcome-free input manifest: {output_dir / 'job_input.json'}\n"
        f"Frozen forensic plan (protocol only): {PLAN}\n"
        f"Exact active source logic: {SOURCE}\n"
        f"Ordered images:\n{image_lines}\n\n"
        "Describe only entry-time price/indicator context visible in each image. Separate observed "
        "facts from inference, mark unknowns, and return the exact five IDs in order. "
        "Set image_opened=true only after opening that image."
    )
    meta = {
        "campaign_id": CAMPAIGN_ID, "stage": "pass-a", "pass_id": "A", "job_id": job_id,
        "job_number": job_number, "stateless": True, "outcome_blind": True,
        "expected_case_ids": case_ids, "expected_position_ids": positions,
        "images": images,
        "input_files": [
            {"path": str(PLAN), "sha256": sha256_file(PLAN)},
            {"path": str(SOURCE), "sha256": sha256_file(SOURCE)},
        ],
        "image_count": 5,
    }
    return _write_request(
        output_dir,
        _request(
            f"vras-hyp008-pass-a-{job_id}",
            "You are a read-only outcome-blind chart reviewer. Use only the five explicitly listed decision images. No web, subagents, repository browsing, outcome inference, or parameter advice.",
            prompt,
            "vras_hyp008_pass_a_job",
            pass_a_schema(job_id),
            meta,
        ),
        job_input,
    )


def _accepted_path(stage: str, job_number: int) -> Path:
    return VALIDATED / stage / f"job-{job_number:02d}.json"


def build_pass_b(output_dir: Path, job_number: int) -> Path:
    selection = load_selection()
    rows = load_case_rows(selection)
    charts = load_charts(selection)
    job_id, case_ids, positions = _job_slice(selection, job_number)
    blind_path = _accepted_path("pass-a", job_number)
    require_file(blind_path, f"validated Pass-A output for {job_id}")
    blind = load_json(blind_path)
    if blind.get("stage") != "pass-a" or blind.get("expected_case_ids") != case_ids:
        raise RuntimeError(f"validated Pass-A identity mismatch for {job_id}")
    cases: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    allowed_fields = [
        "case_id", "position_id", "entry_time_server", "exit_time_server",
        "entry_time_utc", "exit_time_utc", "server_utc_offset_h", "side", "direction",
        "entry", "sl", "tp", "exit", "initial_risk_account", "risk_pips", "net_usd",
        "net_r", "holding_minutes", "weekday_utc", "session_utc", "exact_exit_class",
        "exact_exit_comment", "active_stop_at_exit",
    ]
    for case_id, position in zip(case_ids, positions, strict=True):
        image = {"case_id": case_id, "position_id": position, **charts[case_id]["anatomy"]}
        images.append(image)
        row = {key: rows[case_id].get(key, "") for key in allowed_fields}
        row["case_id"] = case_id
        row["position_id"] = position
        row["anatomy"] = image
        cases.append(row)
    job_input = {
        "schema_version": "vras_hyp008_pass_b_input.v1",
        "campaign_id": CAMPAIGN_ID, "pass_id": "B", "job_id": job_id,
        "validated_blind_output": {"path": str(blind_path), "sha256": sha256_file(blind_path)},
        "cases": cases,
        "exit_reason_authority": "report closing-order comment joined to lifecycle final-close deal ID",
        "moved_sl_caveat": "MOVED_SL does not prove break-even modification timing or +1R trigger timing",
    }
    image_lines = "\n".join(f"- {x['case_id']} | position_id={x['position_id']} | PNG={x['path']}" for x in images)
    prompt = (
        f"Perform stateless outcome anatomy review for exactly five cases in {job_id}.\n"
        f"First read the validated blind Pass-A packet: {blind_path}\n"
        f"Then read the exact five-case input: {output_dir / 'job_input.json'}\n"
        f"Open all five anatomy PNGs:\n{image_lines}\n\n"
        "Reconcile blind assessment to actual path without rewriting what Pass A said. Exit class is "
        "report-bound. MOVED_SL proves only that the close-stop differs from initial stop; it does not "
        "prove break-even timing. Match/context statements are descriptive only. Return exact IDs in order. "
        "No threshold tuning, session/year/direction veto, rerun, rescue, promotion, or source edits. "
        "Emit exactly one JSON object matching the supplied schema, exactly once. Never repeat, concatenate, "
        "or restate the JSON object and emit no prose before or after it."
    )
    input_files = [
        {"path": str(blind_path), "sha256": sha256_file(blind_path)},
    ]
    meta = {
        "campaign_id": CAMPAIGN_ID, "stage": "pass-b", "pass_id": "B", "job_id": job_id,
        "job_number": job_number, "stateless": True,
        "expected_case_ids": case_ids, "expected_position_ids": positions,
        "images": images, "input_files": input_files, "image_count": 5,
        "blind_input": input_files[0],
        "selection_sha256": sha256_file(SELECTION),
        "chart_manifest_sha256": sha256_file(CHART_MANIFEST),
    }
    return _write_request(
        output_dir,
        _request(
            f"vras-hyp008-pass-b-{job_id}",
            "You are a separate stateless read-only trade-anatomy reviewer. Read the validated blind packet before opening the five anatomy images. Use local listed evidence only; no web, subagents, tuning, or post-hoc rescue.",
            prompt,
            "vras_hyp008_pass_b_job",
            pass_b_schema(job_id),
            meta,
        ),
        job_input,
    )


def _validated_outputs() -> list[Path]:
    paths = [
        _accepted_path(stage, job)
        for stage in ("pass-a", "pass-b")
        for job in range(1, JOB_COUNT + 1)
    ]
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "synthesis requires all 40 validated outputs; missing: " + ", ".join(missing[:5])
        )
    return paths


def build_synthesis(output_dir: Path) -> Path:
    selection = load_selection()
    _rows = load_case_rows(selection)
    _charts = load_charts(selection)
    validated = _validated_outputs()
    evidence_files = [
        POPULATION, WEEKEND_TAILS, READOUT_JSON, READOUT_MD, FORENSIC_ANALYSIS,
        SOURCE, NONREPAINT, PLAN, SELECTION, CHART_MANIFEST,
    ]
    for path in evidence_files:
        require_file(path, "synthesis evidence")
    inputs = [{"path": str(path), "sha256": sha256_file(path)} for path in [*validated, *evidence_files]]
    validated_lines = "\n".join(f"- {path}" for path in validated)
    evidence_lines = "\n".join(f"- {path}" for path in evidence_files)
    prompt = (
        "Synthesize the frozen HYP008 random-100 two-pass review. Read all forty validated outputs "
        "and all bound population/source/readout evidence listed below. Do not inspect unvalidated attempts.\n\n"
        f"Validated Pass-A/Pass-B outputs (40):\n{validated_lines}\n\n"
        f"Population, tails, readout, source, audit, plan and manifest evidence:\n{evidence_lines}\n\n"
        "Non-negotiable boundaries:\n"
        "- Current EA is a stripped H1-EMA + rolling-VWAP path proxy, not full VRAS.\n"
        "- Server timestamps and canonical UTC are distinct and fixed in the corrected ledger.\n"
        "- Exact exit reason is report-bound; MOVED_SL does not prove BE activation timing.\n"
        "- Random-100 contains only one weekend crossing; use full-population and weekend-tail supplements.\n"
        "- Source is identical but arm EX5 hashes differ, so matched-pair strict validity is PARTIAL.\n"
        "- Random-100 contains accepted trades only; rejected candidates are absent and counterfactual PnL is unknown.\n"
        "- HYP008 is terminal diagnostic evidence. No threshold tuning or post-hoc rescue.\n\n"
        "Return exact 100 case IDs in frozen order and coverage 20+20 jobs / 200 images. The full Markdown "
        "must use these exact seven headings: `## 1. Executive verdict`, `## 2. Evidence integrity`, "
        "`## 3. Population decomposition`, `## 4. Winner and loser anatomy`, "
        "`## 5. Logic and fidelity choke points`, `## 6. Case chart manifest`, and "
        "`## 7. Conclusions and legal next work`. Section 6 must use the contract columns "
        "`case_id | stratum | position_id | direction | entry | exit | net_R | context_reason | decision_chart | outcome_chart` "
        "or explicitly point to the complete validated manifest if a 100-row table would duplicate bound evidence. "
        "At most three fresh mechanism hypotheses are allowed. Each needs a genuinely fresh falsification test and an explicit "
        "why-not-posthoc-rescue explanation; returning zero is legal. Emit exactly one JSON object matching the supplied schema, "
        "exactly once. Never repeat, concatenate, or restate the JSON object and emit no prose before or after it."
    )
    meta = {
        "campaign_id": CAMPAIGN_ID, "stage": "synthesis", "stateless": True,
        "expected_case_ids": list(map(str, selection["case_ids"])),
        "expected_position_ids": list(map(int, selection["position_ids"])),
        "validated_output_count": 40, "expected_images_across_passes": 200,
        "input_files": inputs, "images": [], "image_count": 0,
    }
    return _write_request(
        output_dir,
        _request(
            "vras-hyp008-random100-synthesis",
            "You are the read-only Lead Quant synthesizer. Integrate only validated local evidence. Keep validity separate from economics, acknowledge every explicit limitation, and never convert outcome patterns into parameter changes.",
            prompt,
            "vras_hyp008_random100_synthesis",
            synthesis_schema(),
            meta,
        ),
    )


def check_inputs() -> dict[str, Any]:
    selection = load_selection()
    rows = load_case_rows(selection)
    charts = load_charts(selection)
    return {
        "status": "HYP008_GROK_INPUTS_OK",
        "cases": len(rows),
        "decision_images": len([x for x in charts.values() if x.get("decision_asof")]),
        "anatomy_images": len([x for x in charts.values() if x.get("anatomy")]),
        "total_images": len(charts) * 2,
        "selection_sha256": sha256_file(SELECTION),
        "chart_manifest_sha256": sha256_file(CHART_MANIFEST),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one HYP008 Grok request artifact")
    parser.add_argument("--stage", choices=("pass-a", "pass-b", "synthesis"))
    parser.add_argument("--job", type=int, help="1..20 for pass-a/pass-b")
    parser.add_argument("--output-dir", type=Path, help="fresh directory for this request")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        print(json.dumps(check_inputs(), indent=2))
        return 0
    if not args.stage or not args.output_dir:
        parser.error("--stage and --output-dir are required unless --check-only")
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise SystemExit(f"refusing to reuse request directory: {output_dir}")
    if args.stage in {"pass-a", "pass-b"} and args.job is None:
        parser.error("--job is required for pass-a/pass-b")
    if args.stage == "synthesis" and args.job is not None:
        parser.error("--job is invalid for synthesis")
    if args.stage == "pass-a":
        path = build_pass_a(output_dir, int(args.job))
    elif args.stage == "pass-b":
        path = build_pass_b(output_dir, int(args.job))
    else:
        path = build_synthesis(output_dir)
    print(json.dumps({"status": "GROK_REQUEST_BUILT", "stage": args.stage, "request": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
