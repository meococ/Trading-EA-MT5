#!/usr/bin/env python3
"""Run the corrected HYP-004 Grok ACP visual batches serially and fail closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_status(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def tighten_single_json_transport(
    batch_dir: Path,
    request: dict[str, object],
    retry_number: int,
) -> None:
    """Bound response verbosity after Grok duplicated a JSON object.

    This changes only the transport/output-shape budget. The bound cases,
    images, visual fields, mechanism enum and evidence contract stay fixed.
    """

    source_blocks = Path(str(request["prompt_blocks_file"])).resolve()
    blocks = json.loads(source_blocks.read_text(encoding="utf-8-sig"))
    if (
        not isinstance(blocks, list)
        or len(blocks) != 11
        or not isinstance(blocks[0], dict)
        or blocks[0].get("type") != "text"
    ):
        raise ValueError("Expected one text plus ten image ACP blocks")
    recovery_instruction = (
        "\n\nOUTPUT-TRANSPORT RECOVERY: Return exactly one compact JSON object and "
        "stop. Never repeat, restate, or append a second object. For each case, "
        "decision_observations and anatomy_observations must each contain "
        "exactly one concise sentence. batch_findings must contain exactly two "
        "concise strings. All required visual transcriptions and booleans remain "
        "mandatory."
    )
    blocks[0]["text"] = str(blocks[0]["text"]) + recovery_instruction
    retry_blocks = batch_dir / f"grok-prompt-blocks-retry{retry_number}.json"
    retry_blocks.write_text(
        json.dumps(blocks, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    request["prompt_blocks_file"] = str(retry_blocks.resolve())
    request["prompt_blocks_sha256"] = sha256(retry_blocks)

    schema = request["request"]["response_format"]["json_schema"]["schema"]
    case_schema = schema["properties"]["case_reviews"]["items"]["properties"]
    for field in ("decision_observations", "anatomy_observations"):
        case_schema[field]["maxItems"] = 1
        case_schema[field]["items"]["maxLength"] = 320
    findings = schema["properties"]["batch_findings"]
    findings["minItems"] = 2
    findings["maxItems"] = 2
    findings["items"]["maxLength"] = 320


def prepare_invocation(batch_dir: Path) -> tuple[Path, Path, int]:
    original_request = batch_dir / "grok-request.json"
    first_run = batch_dir / "run"
    if not first_run.exists():
        return original_request, first_run, 0

    run_number = 2
    while (batch_dir / f"run{run_number}").exists():
        run_number += 1
    retry_number = run_number - 1
    retry_path = batch_dir / f"grok-request-retry{retry_number}.json"
    request = json.loads(original_request.read_text(encoding="utf-8-sig"))
    original_sha = sha256(original_request)
    previous_run = first_run if run_number == 2 else batch_dir / f"run{run_number - 1}"
    previous_summary_path = previous_run / "summary.json"
    previous_summary = (
        json.loads(previous_summary_path.read_text(encoding="utf-8-sig"))
        if previous_summary_path.is_file()
        else {}
    )
    structured_error = str(
        (previous_summary.get("structured_output_validation") or {}).get("error")
        or ""
    )
    previous_stderr_path = previous_run / "run.err"
    previous_stderr = (
        previous_stderr_path.read_text(encoding="utf-8-sig", errors="replace")
        if previous_stderr_path.is_file()
        else ""
    )
    previous_request_path = Path(str(previous_summary.get("request_file") or ""))
    previous_request = (
        json.loads(previous_request_path.read_text(encoding="utf-8-sig"))
        if previous_request_path.is_file()
        else {}
    )
    output_transport_amended = (
        "exactly one JSON instance" in structured_error
        or "max_tokens_truncation" in previous_stderr
        or (previous_request.get("recovery") or {}).get(
            "output_transport_amended"
        )
        is True
    )
    if output_transport_amended:
        tighten_single_json_transport(batch_dir, request, retry_number)
    request["task"] = f"{request['task']}-retry{retry_number}"
    request["recovery"] = {
        "retry_number": retry_number,
        "created_at_utc": utc_now(),
        "source_request": str(original_request.resolve()),
        "source_request_sha256": original_sha,
        "reason": "prior backend invocation did not pass runner acceptance",
        "contract_changed": False,
        "output_transport_amended": output_transport_amended,
    }
    retry_path.write_text(
        json.dumps(request, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return retry_path, batch_dir / f"run{run_number}", retry_number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-root", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--start-batch", type=int, default=2)
    parser.add_argument("--end-batch", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--max-turns", type=int, default=2)
    args = parser.parse_args()

    context_root = args.context_root.resolve()
    workspace = args.workspace.resolve()
    runner = args.runner.resolve()
    if not (1 <= args.start_batch <= args.end_batch <= 20):
        raise SystemExit("Batch bounds must satisfy 1 <= start <= end <= 20")
    if not runner.is_file():
        raise SystemExit(f"Grok runner not found: {runner}")

    status_path = context_root / "campaign_status.json"
    status: dict[str, object] = {
        "schema_version": "scc_grok_acp_campaign_status.v1",
        "started_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "state": "RUNNING",
        "global_concurrency": 1,
        "start_batch": args.start_batch,
        "end_batch": args.end_batch,
        "completed_batches": [],
        "current_batch": None,
        "failure": None,
    }
    write_status(status_path, status)

    completed: list[dict[str, object]] = []
    for number in range(args.start_batch, args.end_batch + 1):
        batch_id = f"batch{number:02d}"
        batch_dir = context_root / batch_id
        request_path, run_dir, retry_number = prepare_invocation(batch_dir)
        status["current_batch"] = batch_id
        status["updated_at_utc"] = utc_now()
        write_status(status_path, status)

        command = [
            sys.executable,
            str(runner),
            "--request-file",
            str(request_path),
            "--output-dir",
            str(run_dir),
            "--cwd",
            str(workspace),
            "--model",
            "grok-4.5",
            "--reasoning-effort",
            "high",
            "--permission-mode",
            "dontAsk",
            "--no-subagents",
            "--disable-web-search",
            "--max-turns",
            str(args.max_turns),
            "--timeout-seconds",
            str(args.timeout_seconds),
        ]
        started = utc_now()
        result = subprocess.run(
            command,
            cwd=workspace,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        summary_path = run_dir / "summary.json"
        summary = (
            json.loads(summary_path.read_text(encoding="utf-8-sig"))
            if summary_path.is_file()
            else {}
        )
        accepted = (
            result.returncode == 0
            and summary.get("success") is True
            and summary.get("response_useful") is True
            and summary.get("stop_reason") == "EndTurn"
            and (summary.get("structured_output_validation") or {}).get("passed")
            is True
            and (summary.get("prompt_blocks") or {}).get("image_count") == 10
            and summary.get("prompt_transport") == "acp_blocks_file"
        )
        row = {
            "batch_id": batch_id,
            "retry_number": retry_number,
            "request_file": str(request_path),
            "run_dir": str(run_dir),
            "started_at_utc": started,
            "finished_at_utc": utc_now(),
            "runner_exit_code": result.returncode,
            "runner_accepted": accepted,
            "elapsed_seconds": summary.get("elapsed_seconds"),
            "cost_usd": summary.get("total_cost_usd"),
            "input_tokens": (summary.get("usage") or {}).get("input_tokens"),
            "output_tokens": (summary.get("usage") or {}).get("output_tokens"),
        }
        completed.append(row)
        status["completed_batches"] = completed
        status["current_batch"] = None
        status["updated_at_utc"] = utc_now()
        if not accepted:
            status["state"] = "FAILED_CLOSED"
            status["failure"] = row
            write_status(status_path, status)
            print(f"SCC_GROK_ACP_CAMPAIGN_FAILED batch={batch_id}", flush=True)
            return 1
        write_status(status_path, status)
        print(
            "SCC_GROK_ACP_BATCH_OK "
            f"batch={batch_id} elapsed={row['elapsed_seconds']} cost={row['cost_usd']}",
            flush=True,
        )

    status["state"] = "RUNNER_ACCEPTED_PENDING_SEMANTIC_QC"
    status["finished_at_utc"] = utc_now()
    status["updated_at_utc"] = utc_now()
    write_status(status_path, status)
    print(
        "SCC_GROK_ACP_CAMPAIGN_RUNNER_OK "
        f"batches={len(completed)} semantic_qc=PENDING",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
