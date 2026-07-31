#!/usr/bin/env python3
"""Run one stateless Grok vision review for each frozen HYP-002 chart.

The 12 decision-as-of images are reviewed outcome-blind before the 12 outcome
anatomy images. Every backend call receives exactly one inline PNG through the
grok-cli-runner ACP prompt-block transport. The script is read-only with
respect to strategy/economic evidence; it writes runner artifacts under
``.context`` and validated review packets under the existing forensic evidence
directory.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, NamedTuple

import jsonschema


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
EVIDENCE = (
    RESEARCH
    / "evidence"
    / "HYP-CME6E-RAWBREAK-BOOKTRANSITION-002_CHART_FORENSICS"
)
CHART_MANIFEST = EVIDENCE / "chart_manifest.json"
CONTEXT = ROOT / ".context" / "hyp002-grok-each-image-20260727"
VALIDATED = EVIDENCE / "grok_each_image_validated"
CAMPAIGN_MANIFEST = EVIDENCE / "grok_each_image_campaign.json"
CAMPAIGN_RESULT = EVIDENCE / "grok_each_image_results.json"
RUNNER = Path(
    r"C:\Users\ADMIN\.codex\skills\grok-cli-runner\scripts\run_grok_cli.py"
)
GROK_BIN = Path(r"C:\Users\ADMIN\.grok\bin\grok.exe")
GLOBAL_LOCK = ROOT / ".context" / "grok-global-concurrency-1.lock"
CAMPAIGN_ID = "HYP002_GROK_EACH_IMAGE_20260727"


class JobSpec(NamedTuple):
    job_id: str
    case_id: str
    position_id: str
    direction: str
    image_type: str
    image_path: str
    image_sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def jobs_from_manifest(manifest: dict[str, Any]) -> list[JobSpec]:
    rows = manifest.get("results")
    if not isinstance(rows, list) or len(rows) != 12:
        raise RuntimeError("chart manifest must contain exactly 12 frozen cases")
    jobs: list[JobSpec] = []
    for prefix, image_type, path_key, sha_key in (
        ("D", "DECISION_ASOF", "decision_chart", "decision_sha256"),
        ("O", "OUTCOME_ANATOMY", "outcome_chart", "outcome_sha256"),
    ):
        for index, row in enumerate(rows, 1):
            path = resolve_repo_path(str(row[path_key]))
            jobs.append(
                JobSpec(
                    job_id=f"{prefix}{index:02d}",
                    case_id=str(row["case_id"]),
                    position_id=str(row["position_id"]),
                    direction=str(row["direction"]),
                    image_type=image_type,
                    image_path=str(path),
                    image_sha256=str(row[sha_key]).upper(),
                )
            )
    if len({job.job_id for job in jobs}) != 24:
        raise RuntimeError("job IDs are not unique")
    if len({str(Path(job.image_path).resolve()) for job in jobs}) != 24:
        raise RuntimeError("campaign does not bind 24 distinct chart images")
    return jobs


def _common_properties(job: JobSpec) -> dict[str, Any]:
    return {
        "campaign_id": {"type": "string", "const": CAMPAIGN_ID},
        "job_id": {"type": "string", "const": job.job_id},
        "case_id": {"type": "string", "const": job.case_id},
        "position_id": {"type": "string", "const": job.position_id},
        "direction": {"type": "string", "const": job.direction},
        "image_type": {"type": "string", "const": job.image_type},
        "image_sha256": {"type": "string", "const": job.image_sha256},
        "image_opened": {"type": "boolean", "const": True},
        "visual_readability": {
            "type": "string",
            "enum": ["PASS", "PARTIAL", "FAIL"],
        },
        "observations": {
            "type": "array",
            "minItems": 3,
            "maxItems": 8,
            "items": {"type": "string", "minLength": 8},
        },
        "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
        "unknowns": {
            "type": "array",
            "maxItems": 6,
            "items": {"type": "string"},
        },
        "no_rule_or_rerun_authority": {"type": "boolean", "const": True},
    }


def result_schema(job: JobSpec) -> dict[str, Any]:
    properties = _common_properties(job)
    if job.image_type == "DECISION_ASOF":
        properties.update(
            {
                "outcome_blind": {"type": "boolean", "const": True},
                "trend_context": {"type": "string", "minLength": 10},
                "range_location": {"type": "string", "minLength": 10},
                "breakout_geometry": {"type": "string", "minLength": 10},
                "book_trace_context": {"type": "string", "minLength": 10},
                "break_freshness": {
                    "type": "string",
                    "enum": ["FRESH", "MATURE", "MIXED", "UNKNOWN"],
                },
                "entry_risk_flags": {
                    "type": "array",
                    "maxItems": 6,
                    "items": {"type": "string"},
                },
                "blind_prediction": {
                    "type": "string",
                    "enum": ["CONTINUATION", "FAILURE", "AMBIGUOUS"],
                },
                "evidence_boundary": {"type": "string", "minLength": 20},
            }
        )
    else:
        properties.update(
            {
                "outcome_visible": {"type": "boolean", "const": True},
                "actual_path_class": {
                    "type": "string",
                    "enum": [
                        "CLEAN_CONTINUATION",
                        "IMMEDIATE_FAILED_BREAK",
                        "WHIPSAW_NO_ACCEPTANCE",
                        "FAVORABLE_THEN_GIVEBACK",
                        "TIMEOUT_OR_DRIFT",
                        "OTHER_OR_AMBIGUOUS",
                    ],
                },
                "primary_layer": {
                    "type": "string",
                    "enum": [
                        "SETUP_ENTRY",
                        "EXIT_MANAGEMENT",
                        "WINNER_NO_FAILURE",
                        "EXECUTION_COST_UNKNOWN",
                        "AMBIGUOUS",
                    ],
                },
                "entry_context_assessment": {"type": "string", "minLength": 10},
                "path_anatomy": {"type": "string", "minLength": 10},
                "book_trace_relevance": {"type": "string", "minLength": 10},
                "exit_geometry_assessment": {"type": "string", "minLength": 10},
                "failure_mechanism": {"type": "string", "minLength": 10},
            }
        )
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def prompt_text(job: JobSpec) -> str:
    common = (
        f"You are the sole read-only forensic reviewer for {CAMPAIGN_ID}, job {job.job_id}.\n"
        "Inspect exactly the ONE attached PNG. Do not browse the repository, use web search, "
        "open any local path, invoke tools, edit files, suggest parameter tuning, or grant rerun, "
        "promotion, paper, or live authority. The image pixels are the only evidence.\n"
        f"Identity: case_id={job.case_id}; position_id={job.position_id}; "
        f"direction={job.direction}; image_type={job.image_type}; "
        f"image_sha256={job.image_sha256}.\n"
        "Set image_opened=true only after actually reading the attached pixels. Separate visible "
        "observations from inference and state unknowns. Return only the schema-constrained JSON.\n"
    )
    if job.image_type == "DECISION_ASOF":
        return common + (
            "This chart is outcome-blind and future-hidden. Do not guess from the case ID and do "
            "not claim knowledge of realized PnL. Review the visible pre-entry M1 price structure, "
            "H1 context, entry/SL/TP geometry, break freshness versus maturity, range location, and "
            "the CME 6E direction-aligned book trace. Make one blind prediction: CONTINUATION, "
            "FAILURE, or AMBIGUOUS, with calibrated confidence. This prediction is diagnostic only."
        )
    return common + (
        "This outcome-anatomy chart visibly includes the realized path and result. Describe the "
        "actual post-entry sequence, distinguish immediate failed break from clean continuation, "
        "whipsaw, or favorable-then-giveback, and assign the primary layer. Cost is not visually "
        "separable, so do not invent spread/commission causality. Explain whether the book trace "
        "visibly discriminated the path, without proposing a rescue rule."
    )


def prompt_blocks(job: JobSpec) -> list[dict[str, Any]]:
    image = Path(job.image_path)
    data = image.read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError(f"not a PNG: {image}")
    return [
        {"type": "text", "text": prompt_text(job)},
        {
            "type": "image",
            "data": base64.b64encode(data).decode("ascii"),
            "mimeType": "image/png",
        },
    ]


def request_payload(job: JobSpec, blocks_file: str, blocks_sha256: str) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "campaign_id": CAMPAIGN_ID,
        "job_id": job.job_id,
        "case_id": job.case_id,
        "position_id": job.position_id,
        "direction": job.direction,
        "image_type": job.image_type,
        "image": {"path": job.image_path, "sha256": job.image_sha256},
        "image_count": 1,
        "stateless": True,
        "outcome_blind": job.image_type == "DECISION_ASOF",
    }
    return {
        "task": f"hyp002-grok-one-image-{job.job_id.lower()}",
        "request": {
            "model": "grok-4.5",
            "reasoning_effort": "high",
            "input": [
                {
                    "role": "system",
                    "content": "Bounded read-only single-image trading chart forensics.",
                },
                {
                    "role": "user",
                    "content": "The complete task and the one image are attached through ACP blocks.",
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": f"hyp002_grok_{job.job_id.lower()}",
                    "schema": result_schema(job),
                },
            },
        },
        "meta": meta,
        "prompt_blocks_file": blocks_file,
        "prompt_blocks_sha256": blocks_sha256,
    }


def check_job_image(job: JobSpec) -> None:
    image = Path(job.image_path)
    if not image.is_file():
        raise FileNotFoundError(image)
    actual = sha256_file(image)
    if actual != job.image_sha256:
        raise RuntimeError(
            f"image SHA mismatch {job.job_id}: expected={job.image_sha256} actual={actual}"
        )


def campaign_jobs() -> list[JobSpec]:
    if not CHART_MANIFEST.is_file():
        raise FileNotFoundError(CHART_MANIFEST)
    jobs = jobs_from_manifest(load_json(CHART_MANIFEST))
    for job in jobs:
        check_job_image(job)
    return jobs


def campaign_manifest_payload(jobs: list[JobSpec]) -> dict[str, Any]:
    return {
        "schema_version": "hyp002_grok_each_image_campaign.v1",
        "campaign_id": CAMPAIGN_ID,
        "hypothesis_id": "HYP-CME6E-RAWBREAK-BOOKTRANSITION-002",
        "generated_at_utc": utc_now(),
        "chart_manifest": {
            "path": str(CHART_MANIFEST),
            "sha256": sha256_file(CHART_MANIFEST),
        },
        "execution_contract": {
            "backend": "grok-build",
            "model": "grok-4.5",
            "reasoning_effort": "high",
            "stateless": True,
            "global_concurrency": 1,
            "images_per_backend_job": 1,
            "decision_jobs_before_outcome_jobs": True,
            "web_search_disabled": True,
            "subagents_disabled": True,
            "strategy_writes_forbidden": True,
            "terminal_verdict_change_forbidden": True,
        },
        "jobs": [job._asdict() for job in jobs],
    }


def write_once(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != payload:
            raise RuntimeError(f"refusing to overwrite different artifact: {path}")
        return
    path.write_text(payload, encoding="utf-8")


def prepare_campaign() -> dict[str, Any]:
    jobs = campaign_jobs()
    payload = campaign_manifest_payload(jobs)
    # Timestamp is evidence metadata, not stable identity. Preserve the first packet.
    if CAMPAIGN_MANIFEST.exists():
        current = load_json(CAMPAIGN_MANIFEST)
        expected_jobs = [job._asdict() for job in jobs]
        if current.get("jobs") != expected_jobs:
            raise RuntimeError("existing campaign manifest does not match current charts")
        return current
    write_once(CAMPAIGN_MANIFEST, canonical_json(payload))
    return payload


def materialize(job: JobSpec, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=False)
    blocks_path = directory / "prompt-blocks.json"
    blocks_path.write_text(canonical_json(prompt_blocks(job)), encoding="utf-8")
    request = request_payload(job, blocks_path.name, sha256_file(blocks_path))
    request_path = directory / "grok-request.json"
    request_path.write_text(canonical_json(request), encoding="utf-8")
    return request_path


def fresh_attempt(job: JobSpec, kind: str) -> Path:
    base = CONTEXT / "jobs" / job.job_id
    base.mkdir(parents=True, exist_ok=True)
    used: list[int] = []
    pattern = re.compile(rf"attempt-(\d{{3,}})-{re.escape(kind)}$")
    for child in base.iterdir():
        match = pattern.fullmatch(child.name)
        if match:
            used.append(int(match.group(1)))
    return base / f"attempt-{max(used, default=0) + 1:03d}-{kind}"


@contextmanager
def backend_lock() -> Iterator[None]:
    GLOBAL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = GLOBAL_LOCK.open("a+b")
    handle.seek(0)
    if handle.read(1) == b"":
        handle.seek(0)
        handle.write(b"0")
        handle.flush()
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError(f"another Grok run holds {GLOBAL_LOCK}") from exc
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def wrapper_command(directory: Path, *, dry_run: bool, timeout: int) -> list[str]:
    command = [
        sys.executable,
        str(RUNNER),
        "--request-file",
        str(directory / "grok-request.json"),
        "--output-dir",
        str(directory),
        "--response-artifact",
        "grok-response.json",
        "--cwd",
        str(ROOT),
        "--grok-bin",
        str(GROK_BIN),
        "--permission-mode",
        "auto",
        "--no-plan",
        "--no-subagents",
        "--disable-web-search",
        "--max-turns",
        "4",
        "--timeout-seconds",
        str(timeout),
    ]
    if dry_run:
        command.append("--dry-run")
    return command


def _parse_result(response: dict[str, Any]) -> dict[str, Any]:
    output = response.get("output_text")
    if isinstance(output, dict):
        return output
    if isinstance(output, str) and output.strip():
        parsed = json.loads(output)
        if isinstance(parsed, dict):
            return parsed
    raise RuntimeError("response does not contain one whole JSON result")


def validate_dry_run(directory: Path) -> None:
    summary = load_json(directory / "summary.json")
    if summary.get("success") is not True or summary.get("dry_run") is not True:
        raise RuntimeError(f"dry-run failed: {summary.get('failure_reasons')}")
    if not isinstance(summary.get("dry_run_payload"), dict):
        raise RuntimeError("dry-run summary lacks dry_run_payload")
    if (directory / "grok-response.json").exists():
        raise RuntimeError("dry-run unexpectedly produced a response")


def validate_actual(job: JobSpec, directory: Path) -> dict[str, Any]:
    request_path = directory / "grok-request.json"
    prompt_path = directory / "prompt-blocks.json"
    summary_path = directory / "summary.json"
    response_path = directory / "grok-response.json"
    for path in (request_path, prompt_path, summary_path, response_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    request = load_json(request_path)
    summary = load_json(summary_path)
    response = load_json(response_path)
    required_summary = {
        "success": True,
        "response_non_empty": True,
        "response_useful": True,
        "stop_reason": "EndTurn",
        "model": "grok-4.5",
        "reasoning_effort": "high",
        "permission_mode": "auto",
        "no_plan": True,
        "no_subagents": True,
        "web_search_disabled": True,
        "dry_run": False,
        "prompt_transport": "acp_blocks_file",
    }
    bad = {
        key: (summary.get(key), expected)
        for key, expected in required_summary.items()
        if summary.get(key) != expected
    }
    if bad:
        raise RuntimeError(f"runner summary gates failed for {job.job_id}: {bad}")
    if (summary.get("failure_reasons") or []) != []:
        raise RuntimeError(f"runner retained failure reasons: {summary['failure_reasons']}")
    structured = summary.get("structured_output_validation") or {}
    if structured.get("passed") is not True:
        raise RuntimeError(f"structured output failed: {structured}")
    prompt_meta = summary.get("prompt_blocks") or {}
    if prompt_meta.get("image_count") != 1:
        raise RuntimeError(f"runner did not bind exactly one image: {prompt_meta}")
    if prompt_meta.get("decoded_image_bytes") != Path(job.image_path).stat().st_size:
        raise RuntimeError("runner decoded image byte count does not match source PNG")
    result = _parse_result(response)
    schema = request["request"]["response_format"]["json_schema"]["schema"]
    jsonschema.validate(instance=result, schema=schema)
    if result.get("image_opened") is not True:
        raise RuntimeError(f"{job.job_id} lacks image_opened=true")
    return {
        "schema_version": "hyp002_grok_each_image_validated_job.v1",
        "campaign_id": CAMPAIGN_ID,
        "job": job._asdict(),
        "attempt_dir": str(directory.resolve()),
        "request": {"path": str(request_path), "sha256": sha256_file(request_path)},
        "prompt_blocks": {"path": str(prompt_path), "sha256": sha256_file(prompt_path)},
        "summary": {"path": str(summary_path), "sha256": sha256_file(summary_path)},
        "response": {"path": str(response_path), "sha256": sha256_file(response_path)},
        "runner": {
            "model": summary.get("model"),
            "reasoning_effort": summary.get("reasoning_effort"),
            "stop_reason": summary.get("stop_reason"),
            "elapsed_seconds": summary.get("elapsed_seconds"),
            "total_cost_usd": summary.get("total_cost_usd"),
            "num_turns": summary.get("num_turns"),
            "prompt_transport": summary.get("prompt_transport"),
            "image_count": prompt_meta.get("image_count"),
            "decoded_image_bytes": prompt_meta.get("decoded_image_bytes"),
        },
        "result": result,
    }


def accepted_path(job: JobSpec) -> Path:
    return VALIDATED / "jobs" / f"{job.job_id}.json"


def publish_validated(job: JobSpec, record: dict[str, Any]) -> None:
    write_once(accepted_path(job), canonical_json(record))


def validate_accepted(job: JobSpec) -> dict[str, Any]:
    path = accepted_path(job)
    if not path.is_file():
        raise FileNotFoundError(path)
    accepted = load_json(path)
    current = validate_actual(job, Path(str(accepted["attempt_dir"])))
    if accepted != current:
        raise RuntimeError(f"accepted job drifted: {path}")
    return accepted


def run_all(*, dry_run: bool, timeout: int, retries: int) -> None:
    prepare_campaign()
    jobs = campaign_jobs()
    with backend_lock():
        for index, job in enumerate(jobs, 1):
            if not dry_run and accepted_path(job).exists():
                validate_accepted(job)
                print(f"SKIP_ACCEPTED {index:02d}/24 {job.job_id}", flush=True)
                continue
            last_error: Exception | None = None
            for attempt_index in range(retries + 1):
                kind = "dryrun" if dry_run else "actual"
                directory = fresh_attempt(job, kind)
                materialize(job, directory)
                print(
                    f"GROK_IMAGE_START {index:02d}/24 job={job.job_id} "
                    f"type={job.image_type} attempt={attempt_index + 1}",
                    flush=True,
                )
                completed = subprocess.run(
                    wrapper_command(directory, dry_run=dry_run, timeout=timeout),
                    cwd=str(ROOT),
                    check=False,
                )
                try:
                    if completed.returncode != 0:
                        raise RuntimeError(
                            f"wrapper exit={completed.returncode}; inspect {directory / 'summary.json'}"
                        )
                    if dry_run:
                        validate_dry_run(directory)
                    else:
                        record = validate_actual(job, directory)
                        publish_validated(job, record)
                    print(
                        f"GROK_IMAGE_ACCEPTED {index:02d}/24 job={job.job_id} dir={directory}",
                        flush=True,
                    )
                    last_error = None
                    break
                except Exception as exc:  # preserve artifacts, optionally retry fresh
                    last_error = exc
                    print(f"GROK_IMAGE_REJECTED job={job.job_id} error={exc}", flush=True)
            if last_error is not None:
                raise RuntimeError(f"job {job.job_id} failed acceptance") from last_error


def validate_campaign() -> dict[str, Any]:
    manifest = load_json(CHART_MANIFEST)
    jobs = campaign_jobs()
    accepted = [validate_accepted(job) for job in jobs]
    result_rows = [row["result"] for row in accepted]
    if len(result_rows) != 24 or not all(row.get("image_opened") is True for row in result_rows):
        raise RuntimeError("campaign does not have 24 accepted image-open attestations")
    if [row["job_id"] for row in result_rows] != [job.job_id for job in jobs]:
        raise RuntimeError("accepted result order/identity mismatch")
    manifest_rows = {str(row["case_id"]): row for row in manifest["results"]}
    decision_rows = [row for row in result_rows if row["image_type"] == "DECISION_ASOF"]
    outcome_rows = [row for row in result_rows if row["image_type"] == "OUTCOME_ANATOMY"]
    blind_scored = []
    for row in decision_rows:
        actual_win = float(manifest_rows[row["case_id"]]["net_R"]) > 0
        predicted = row["blind_prediction"]
        correct = (
            (predicted == "CONTINUATION" and actual_win)
            or (predicted == "FAILURE" and not actual_win)
        )
        blind_scored.append(
            {
                "case_id": row["case_id"],
                "prediction": predicted,
                "confidence": row["confidence"],
                "actual": "WIN" if actual_win else "LOSS",
                "correct_when_directional": correct if predicted != "AMBIGUOUS" else None,
            }
        )
    directional = [row for row in blind_scored if row["correct_when_directional"] is not None]
    generated_at = (
        str(load_json(CAMPAIGN_RESULT).get("generated_at_utc"))
        if CAMPAIGN_RESULT.exists()
        else utc_now()
    )
    payload = {
        "schema_version": "hyp002_grok_each_image_campaign_result.v1",
        "campaign_id": CAMPAIGN_ID,
        "generated_at_utc": generated_at,
        "coverage": {
            "backend_jobs": 24,
            "images_expected": 24,
            "images_opened": 24,
            "images_per_job": 1,
            "decision_images": 12,
            "outcome_images": 12,
            "all_runner_and_schema_gates_passed": True,
        },
        "blind_prediction": {
            "counts": dict(Counter(row["prediction"] for row in blind_scored)),
            "directional_predictions": len(directional),
            "directional_correct": sum(bool(row["correct_when_directional"]) for row in directional),
            "directional_accuracy": (
                sum(bool(row["correct_when_directional"]) for row in directional) / len(directional)
                if directional
                else None
            ),
            "cases": blind_scored,
        },
        "outcome_path_classes": dict(Counter(row["actual_path_class"] for row in outcome_rows)),
        "outcome_primary_layers": dict(Counter(row["primary_layer"] for row in outcome_rows)),
        "jobs": accepted,
        "authority": {
            "terminal_verdict_changed": False,
            "post_hoc_rule_authority": False,
            "rerun_or_promotion_authority": False,
        },
    }
    write_once(CAMPAIGN_RESULT, canonical_json(payload))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HYP-002 Grok one-image forensics")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    dry = sub.add_parser("dry-run")
    dry.add_argument("--timeout-seconds", type=int, default=300)
    actual = sub.add_parser("run")
    actual.add_argument("--timeout-seconds", type=int, default=300)
    actual.add_argument("--retries", type=int, default=0)
    sub.add_parser("validate")
    args = parser.parse_args()
    if args.command == "prepare":
        payload = prepare_campaign()
        print(
            f"HYP002_GROK_CAMPAIGN_PREPARED jobs={len(payload['jobs'])} "
            f"manifest={CAMPAIGN_MANIFEST}"
        )
    elif args.command == "dry-run":
        run_all(dry_run=True, timeout=args.timeout_seconds, retries=0)
        print("HYP002_GROK_DRY_RUN_OK jobs=24")
    elif args.command == "run":
        if args.retries < 0:
            parser.error("--retries cannot be negative")
        run_all(dry_run=False, timeout=args.timeout_seconds, retries=args.retries)
        print("HYP002_GROK_BACKEND_RUN_OK jobs=24")
    else:
        payload = validate_campaign()
        print(
            f"HYP002_GROK_CAMPAIGN_ACCEPTED images={payload['coverage']['images_opened']} "
            f"result={CAMPAIGN_RESULT}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
