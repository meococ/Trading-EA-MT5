#!/usr/bin/env python3
"""Fail-closed validation for HYP008 two-pass Grok forensics.

Validates runner truth, JSON Schema, request/input/image hashes, blind-pass
reference isolation, exact IDs, exact 100-case unions in both passes, and the
final 200-image/40-output synthesis contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import jsonschema

import build_hyp008_grok_requests as build


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


def verify_file(record: dict[str, Any], label: str) -> Path:
    if not isinstance(record, dict) or not record.get("path") or not record.get("sha256"):
        raise RuntimeError(f"{label} lacks path/sha256")
    path = Path(str(record["path"])).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"missing {label}: {path}")
    actual = sha256_file(path)
    expected = str(record["sha256"]).upper()
    if actual != expected:
        raise RuntimeError(f"{label} SHA mismatch expected={expected} actual={actual}: {path}")
    return path


def _result_from_response(response: dict[str, Any]) -> dict[str, Any]:
    output = response.get("output_text")
    if isinstance(output, dict):
        return output
    if isinstance(output, str) and output.strip():
        parsed = json.loads(output)
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError("grok-response.json lacks one whole JSON object in output_text")


def _runner_checks(summary: dict[str, Any], request: dict[str, Any]) -> None:
    required = {
        "success": True,
        "response_non_empty": True,
        "response_useful": True,
        "stop_reason": "EndTurn",
        "permission_mode": "auto",
        "no_plan": True,
        "no_subagents": True,
        "web_search_disabled": True,
        "dry_run": False,
    }
    bad = {key: (summary.get(key), expected) for key, expected in required.items() if summary.get(key) != expected}
    if bad:
        raise RuntimeError(f"runner summary gates failed: {bad}")
    if summary.get("session_id") or summary.get("resume") or summary.get("continue_session"):
        raise RuntimeError("forensic jobs must be stateless (no session/resume/continue)")
    structured = summary.get("structured_output_validation") or {}
    if structured.get("passed") is not True:
        raise RuntimeError(f"runner structured-output validation did not pass: {structured}")
    if (summary.get("failure_reasons") or []) != []:
        raise RuntimeError(f"runner retained failure reasons: {summary['failure_reasons']}")
    if request.get("request", {}).get("response_format", {}).get("type") != "json_schema":
        raise RuntimeError("request is not response_format=json_schema")


def _path_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for child in value.values():
            found.extend(_path_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_path_strings(child))
    elif isinstance(value, str):
        for match in re.finditer(r"[A-Za-z]:\\[^\r\n|]+", value):
            found.append(match.group(0).strip())
    return found


def _validate_blind_allowlist(request: dict[str, Any], request_path: Path) -> None:
    meta = request["meta"]
    input_paths = {str(verify_file(row, "Pass-A input file")) for row in meta["input_files"]}
    image_paths = {str(verify_file(row, "Pass-A image")) for row in meta["images"]}
    expected_inputs = {
        str(build.PLAN.resolve()),
        str(build.SOURCE.resolve()),
        str((request_path.parent / "job_input.json").resolve()),
    }
    if input_paths != expected_inputs:
        raise RuntimeError(f"Pass-A input allowlist mismatch: {sorted(input_paths)}")
    allowed = input_paths | image_paths
    for raw in _path_strings(request):
        # Prompt lines end at newline and may carry harmless punctuation.
        candidate = raw.rstrip(".,;:)]}").strip()
        try:
            resolved = str(Path(candidate).resolve())
        except OSError:
            continue
        if resolved not in allowed:
            raise RuntimeError(f"Pass-A request leaks non-allowlisted path: {candidate}")
    serialized = json.dumps(request, ensure_ascii=False).lower()
    forbidden = [
        "cases_random_100.csv", "selection_manifest.json", "chart_manifest.json",
        "population_forensic_supplement.json", "weekend_tail_supplement.csv",
        "hyp-vras-eurusd-m5-008_readout", "hyp-vras-eurusd-m5-008_forensic_analysis",
        "report.html", "lifecycletrades", "anatomy_m", "_anatomy.png",
    ]
    leaked = [token for token in forbidden if token in serialized]
    if leaked:
        raise RuntimeError(f"Pass-A request contains forbidden evidence reference(s): {leaked}")
    job_input = load_json(request_path.parent / "job_input.json")
    allowed_case_keys = {
        "case_id", "position_id", "entry_time_server", "entry_time_utc",
        "server_utc_offset_h", "direction", "side", "entry", "sl", "tp",
        "h1_close", "h1_ema", "rolling_vwap_48", "atr14", "spread_pips",
        "decision_asof",
    }
    for case in job_input.get("cases") or []:
        if set(case) - allowed_case_keys:
            raise RuntimeError(f"Pass-A blind ledger has forbidden fields: {set(case) - allowed_case_keys}")
    forbidden_case_fields = {
        "exit", "exit_time_server", "exit_time_utc", "net", "net_usd", "net_r",
        "label", "exact_exit_class", "exact_exit_comment", "holding_minutes",
        "active_stop_at_exit", "outcome", "winner", "loser",
    }
    for case in job_input.get("cases") or []:
        if forbidden_case_fields & {str(key).lower() for key in case}:
            raise RuntimeError("Pass-A blind ledger exposes outcome fields")


def validate_job(attempt_dir: Path) -> dict[str, Any]:
    directory = attempt_dir.resolve()
    request_path = directory / "grok-request.json"
    summary_path = directory / "summary.json"
    response_path = directory / "grok-response.json"
    for path in (request_path, summary_path, response_path):
        if not path.is_file():
            raise FileNotFoundError(f"missing job artifact: {path}")
    request = load_json(request_path)
    summary = load_json(summary_path)
    response = load_json(response_path)
    _runner_checks(summary, request)
    result = _result_from_response(response)
    schema = request["request"]["response_format"]["json_schema"]["schema"]
    jsonschema.validate(instance=result, schema=schema)

    meta = request.get("meta") or {}
    stage = str(meta.get("stage") or "")
    if stage not in {"pass-a", "pass-b"}:
        raise RuntimeError(f"job stage must be pass-a/pass-b, got {stage!r}")
    if meta.get("stateless") is not True or int(meta.get("image_count", -1)) != 5:
        raise RuntimeError("job must be stateless with image_count=5")
    expected_ids = list(map(str, meta.get("expected_case_ids") or []))
    expected_positions = list(map(int, meta.get("expected_position_ids") or []))
    if len(expected_ids) != 5 or len(set(expected_ids)) != 5 or len(expected_positions) != 5:
        raise RuntimeError("request does not bind exactly five unique cases")
    images = meta.get("images") or []
    if len(images) != 5:
        raise RuntimeError("request image metadata is not exact five")
    for index, image in enumerate(images):
        verify_file(image, f"{stage} image {index + 1}")
        if image.get("case_id") != expected_ids[index] or int(image.get("position_id")) != expected_positions[index]:
            raise RuntimeError(f"{stage} image identity/order mismatch at index {index}")
    for index, record in enumerate(meta.get("input_files") or []):
        verify_file(record, f"{stage} input file {index + 1}")

    coverage = result.get("coverage")
    required_coverage = {
        "expected_cases": 5,
        "expected_images": 5,
        "images_opened": 5,
        "all_cases_reported": True,
    }
    if coverage != required_coverage:
        raise RuntimeError(f"{stage} coverage mismatch: {coverage}")
    cases = result.get("cases") or []
    actual_ids = [str(row.get("case_id")) for row in cases]
    actual_positions = [int(row.get("position_id")) for row in cases]
    if actual_ids != expected_ids or actual_positions != expected_positions:
        raise RuntimeError(f"{stage} result ID/order mismatch")
    if not all(row.get("image_opened") is True for row in cases):
        raise RuntimeError(f"{stage} result lacks image_opened=true")

    if stage == "pass-a":
        if result.get("outcome_blind") is not True or meta.get("outcome_blind") is not True:
            raise RuntimeError("Pass A is not explicitly outcome blind")
        _validate_blind_allowlist(request, request_path)
    else:
        if result.get("stateless") is not True or result.get("blind_output_read") is not True:
            raise RuntimeError("Pass B did not attest stateless blind-output-first review")
        blind_path = verify_file(meta.get("blind_input") or {}, "validated Pass-A input")
        blind = load_json(blind_path)
        if blind.get("stage") != "pass-a" or blind.get("expected_case_ids") != expected_ids:
            raise RuntimeError("Pass B blind input does not match same job/case IDs")
        if Path(str(blind.get("attempt_dir"))).resolve() == directory:
            raise RuntimeError("Pass B reused Pass-A session directory")

    return {
        "schema_version": "vras_hyp008_validated_job.v1",
        "campaign_id": build.CAMPAIGN_ID,
        "stage": stage,
        "pass_id": meta["pass_id"],
        "job_id": meta["job_id"],
        "job_number": int(meta["job_number"]),
        "attempt_dir": str(directory),
        "request": str(request_path),
        "request_sha256": sha256_file(request_path),
        "summary": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "response": str(response_path),
        "response_sha256": sha256_file(response_path),
        "expected_case_ids": expected_ids,
        "expected_position_ids": expected_positions,
        "images": images,
        "input_files": meta.get("input_files") or [],
        "result": result,
    }


def publish(record: dict[str, Any], destination: Path) -> None:
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if destination.exists():
        current = destination.read_text(encoding="utf-8")
        if current != payload:
            raise RuntimeError(f"refusing to overwrite different accepted artifact: {destination}")
        return
    destination.write_text(payload, encoding="utf-8")


def _accepted_records(stage: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number in range(1, build.JOB_COUNT + 1):
        path = build.VALIDATED / stage / f"job-{number:02d}.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing accepted {stage} job: {path}")
        accepted = load_json(path)
        current = validate_job(Path(str(accepted["attempt_dir"])))
        if accepted != current:
            raise RuntimeError(f"accepted packet drifted from source attempt: {path}")
        records.append(accepted)
    return records


def validate_campaign(stage: str = "both") -> dict[str, Any]:
    selection = build.load_selection()
    expected_ids = list(map(str, selection["case_ids"]))
    expected_positions = list(map(int, selection["position_ids"]))
    stages = ["pass-a", "pass-b"] if stage == "both" else [stage]
    all_records: dict[str, list[dict[str, Any]]] = {}
    for current_stage in stages:
        records = _accepted_records(current_stage)
        ids = [case_id for record in records for case_id in record["expected_case_ids"]]
        positions = [position for record in records for position in record["expected_position_ids"]]
        images = [image for record in records for image in record["images"]]
        if ids != expected_ids or positions != expected_positions or len(set(ids)) != 100:
            raise RuntimeError(f"{current_stage} is not the exact frozen 100-case union/order")
        image_paths = [str(Path(image["path"]).resolve()) for image in images]
        if len(images) != 100 or len(set(image_paths)) != 100:
            raise RuntimeError(f"{current_stage} does not bind exactly 100 distinct images")
        all_records[current_stage] = records
    if stage == "both":
        ids_a = [x for record in all_records["pass-a"] for x in record["expected_case_ids"]]
        ids_b = [x for record in all_records["pass-b"] for x in record["expected_case_ids"]]
        if ids_a != ids_b:
            raise RuntimeError("Pass A and Pass B case unions/orders differ")
        all_images = [
            str(Path(image["path"]).resolve())
            for records in all_records.values() for record in records for image in record["images"]
        ]
        if len(all_images) != 200 or len(set(all_images)) != 200:
            raise RuntimeError("two-pass campaign does not bind exactly 200 distinct images")
    return {
        "status": "HYP008_GROK_CAMPAIGN_ACCEPTED",
        "stage": stage,
        "jobs": sum(len(rows) for rows in all_records.values()),
        "cases_per_pass": 100,
        "images": 200 if stage == "both" else 100,
        "same_case_union": True if stage == "both" else None,
    }


def validate_synthesis(attempt_dir: Path) -> dict[str, Any]:
    campaign = validate_campaign("both")
    directory = attempt_dir.resolve()
    request_path = directory / "grok-request.json"
    summary_path = directory / "summary.json"
    response_path = directory / "grok-response.json"
    request = load_json(request_path)
    summary = load_json(summary_path)
    response = load_json(response_path)
    _runner_checks(summary, request)
    meta = request.get("meta") or {}
    if meta.get("stage") != "synthesis" or int(meta.get("validated_output_count", -1)) != 40:
        raise RuntimeError("synthesis request does not bind 40 validated outputs")
    input_files = meta.get("input_files") or []
    if len(input_files) != 50:  # forty accepted outputs + ten evidence files
        raise RuntimeError(f"synthesis must bind exactly 50 inputs, got {len(input_files)}")
    for index, record in enumerate(input_files):
        verify_file(record, f"synthesis input {index + 1}")
    result = _result_from_response(response)
    schema = request["request"]["response_format"]["json_schema"]["schema"]
    jsonschema.validate(instance=result, schema=schema)
    expected_ids = list(map(str, build.load_selection()["case_ids"]))
    actual_ids = list(map(str, result.get("case_ids_seen") or []))
    if actual_ids != expected_ids or len(set(actual_ids)) != 100:
        raise RuntimeError("synthesis case IDs are not exact frozen order/union")
    expected_coverage = {
        "pass_a_jobs": 20, "pass_b_jobs": 20, "validated_outputs_read": 40,
        "pass_a_cases": 100, "pass_b_cases": 100, "images_opened": 200,
        "same_case_union": True,
    }
    if result.get("coverage") != expected_coverage:
        raise RuntimeError(f"synthesis coverage mismatch: {result.get('coverage')}")
    hypotheses = result.get("fresh_mechanism_hypotheses") or []
    if len(hypotheses) > 3:
        raise RuntimeError("synthesis proposed more than three fresh mechanisms")
    for index, hypothesis in enumerate(hypotheses, 1):
        if len(str(hypothesis.get("fresh_falsification_test") or "").strip()) < 20:
            raise RuntimeError(f"hypothesis {index} lacks a fresh falsification test")
        if len(str(hypothesis.get("why_not_posthoc_rescue") or "").strip()) < 20:
            raise RuntimeError(f"hypothesis {index} lacks why-not-posthoc justification")
    if result.get("proposed_parameter_changes") != []:
        raise RuntimeError("synthesis contains prohibited parameter/threshold changes")
    limits = result.get("limitations_acknowledged") or {}
    if not limits or not all(value is True for value in limits.values()) or len(limits) != 8:
        raise RuntimeError("synthesis did not acknowledge all eight explicit limitations")
    if "PARTIAL" not in str(result.get("validity_verdict") or "").upper():
        raise RuntimeError("synthesis validity must state matched-pair PARTIAL")
    if len(str(result.get("owner_summary_vi") or "").strip()) < 100:
        raise RuntimeError("owner_summary_vi is unexpectedly short")
    report = str(result.get("full_report_markdown") or "")
    if len(report.strip()) < 1200:
        raise RuntimeError("full_report_markdown is unexpectedly short")
    required_headings = [
        "## 1. Executive verdict",
        "## 2. Evidence integrity",
        "## 3. Population decomposition",
        "## 4. Winner and loser anatomy",
        "## 5. Logic and fidelity choke points",
        "## 6. Case chart manifest",
        "## 7. Conclusions and legal next work",
    ]
    missing_headings = [heading for heading in required_headings if heading not in report]
    if missing_headings:
        raise RuntimeError(f"full report misses analysis-contract headings: {missing_headings}")
    if "case_id | stratum | position_id | direction | entry | exit | net_R" not in report:
        raise RuntimeError("case-chart section lacks the required manifest column contract")
    if result.get("promotion_blocked") is not True or result.get("post_hoc_rescue_blocked") is not True:
        raise RuntimeError("synthesis illegally opens promotion/rescue")
    return {
        "schema_version": "vras_hyp008_validated_synthesis.v1",
        "campaign_id": build.CAMPAIGN_ID,
        "stage": "synthesis",
        "attempt_dir": str(directory),
        "request": str(request_path), "request_sha256": sha256_file(request_path),
        "summary": str(summary_path), "summary_sha256": sha256_file(summary_path),
        "response": str(response_path), "response_sha256": sha256_file(response_path),
        "campaign_validation": campaign,
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate HYP008 Grok forensics")
    sub = parser.add_subparsers(dest="command", required=True)
    job = sub.add_parser("job")
    job.add_argument("attempt_dir", type=Path)
    job.add_argument("--publish", type=Path)
    campaign = sub.add_parser("campaign")
    campaign.add_argument("--stage", choices=("pass-a", "pass-b", "both"), default="both")
    synthesis = sub.add_parser("synthesis")
    synthesis.add_argument("attempt_dir", type=Path)
    synthesis.add_argument("--publish", type=Path)
    args = parser.parse_args()
    if args.command == "job":
        record = validate_job(args.attempt_dir)
        if args.publish:
            publish(record, args.publish)
    elif args.command == "campaign":
        record = validate_campaign(args.stage)
    else:
        record = validate_synthesis(args.attempt_dir)
        if args.publish:
            publish(record, args.publish)
    print(json.dumps(record if args.command == "campaign" else {
        "status": "HYP008_GROK_VALIDATED", "stage": record["stage"],
        "job_id": record.get("job_id"), "attempt_dir": record["attempt_dir"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
