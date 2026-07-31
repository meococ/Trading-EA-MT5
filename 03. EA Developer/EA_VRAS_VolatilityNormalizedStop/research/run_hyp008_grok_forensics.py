#!/usr/bin/env python3
"""Serial, resumable runner for the HYP008 two-pass Grok forensic pipeline.

Every wrapper invocation gets a newly materialized request and a new attempt
directory.  The default performs a no-call wrapper dry-run before each actual
job.  There is no backend/model/permission fallback and no parallel execution.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import build_hyp008_grok_requests as build
import validate_hyp008_grok_forensics as validate


RUNNER = Path(r"C:\Users\ADMIN\.codex\skills\grok-cli-runner\scripts\run_grok_cli.py")
ATTEMPTS = build.CONTEXT / "attempts"
GLOBAL_LOCK = build.ROOT / ".context" / "grok-global-concurrency-1.lock"


@contextmanager
def backend_lock() -> Iterator[None]:
    """Hold a non-blocking cross-process lock for global backend concurrency 1."""
    GLOBAL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    handle = GLOBAL_LOCK.open("a+b")
    handle.seek(0)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError(f"another Grok backend run holds {GLOBAL_LOCK}") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError(f"another Grok backend run holds {GLOBAL_LOCK}") from exc
        yield
    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _base(stage: str, job_number: int | None) -> Path:
    return ATTEMPTS / stage / (f"job-{job_number:02d}" if job_number is not None else "synthesis")


def fresh_attempt(stage: str, job_number: int | None, kind: str) -> Path:
    base = _base(stage, job_number)
    base.mkdir(parents=True, exist_ok=True)
    used: list[int] = []
    for child in base.iterdir():
        match = re.fullmatch(r"attempt-(\d{3,})-(?:dryrun|actual)", child.name)
        if match:
            used.append(int(match.group(1)))
    number = max(used, default=0) + 1
    return base / f"attempt-{number:03d}-{kind}"


def materialize(stage: str, job_number: int | None, directory: Path) -> Path:
    if stage == "pass-a":
        return build.build_pass_a(directory, int(job_number))
    if stage == "pass-b":
        return build.build_pass_b(directory, int(job_number))
    if stage == "synthesis":
        return build.build_synthesis(directory)
    raise ValueError(stage)


def runner_command(directory: Path, dry_run: bool, timeout: int, max_turns: int) -> list[str]:
    command = [
        sys.executable,
        str(RUNNER),
        "--request-file", str(directory / "grok-request.json"),
        "--output-dir", str(directory),
        "--response-artifact", "grok-response.json",
        "--cwd", str(build.ROOT),
        "--permission-mode", "auto",
        "--no-plan",
        "--no-subagents",
        "--disable-web-search",
        "--max-turns", str(max_turns),
        "--timeout-seconds", str(timeout),
    ]
    if dry_run:
        command.append("--dry-run")
    return command


def run_wrapper(directory: Path, dry_run: bool, timeout: int, max_turns: int) -> int:
    if not RUNNER.is_file():
        raise FileNotFoundError(f"canonical Grok wrapper missing: {RUNNER}")
    command = runner_command(directory, dry_run, timeout, max_turns)
    print("RUNNER", json.dumps(command, ensure_ascii=False))
    completed = subprocess.run(command, cwd=str(build.ROOT), check=False)
    return int(completed.returncode)


def validate_dry_run(directory: Path) -> None:
    summary_path = directory / "summary.json"
    if not summary_path.is_file():
        raise RuntimeError(f"dry-run summary missing: {summary_path}")
    summary = build.load_json(summary_path)
    if summary.get("success") is not True or summary.get("dry_run") is not True:
        raise RuntimeError(f"wrapper dry-run failed: {summary.get('failure_reasons')}")
    if not isinstance(summary.get("dry_run_payload"), dict):
        raise RuntimeError("wrapper dry-run lacks dry_run_payload")
    if (directory / "grok-response.json").exists():
        raise RuntimeError("dry-run unexpectedly created a Grok response")


def accepted_path(stage: str, job_number: int | None) -> Path:
    if stage == "synthesis":
        return build.VALIDATED / "synthesis.json"
    return build.VALIDATED / stage / f"job-{int(job_number):02d}.json"


def accepted_is_valid(stage: str, job_number: int | None) -> bool:
    path = accepted_path(stage, job_number)
    if not path.is_file():
        return False
    try:
        record = build.load_json(path)
        if stage == "synthesis":
            return validate.validate_synthesis(Path(str(record["attempt_dir"]))) == record
        return validate.validate_job(Path(str(record["attempt_dir"]))) == record
    except Exception as exc:  # report drift; do not silently reuse it
        print(f"ACCEPTED_INVALID path={path} error={exc}")
        return False


def execute_one(
    stage: str,
    job_number: int | None,
    *,
    dry_run_only: bool,
    preflight_dry_run: bool,
    retries: int,
    timeout: int,
    max_turns: int,
) -> bool:
    label = f"{stage}/{job_number:02d}" if job_number is not None else stage
    if not dry_run_only and accepted_is_valid(stage, job_number):
        print(f"SKIP_ACCEPTED {label}")
        return True

    if preflight_dry_run or dry_run_only:
        directory = fresh_attempt(stage, job_number, "dryrun")
        materialize(stage, job_number, directory)
        code = run_wrapper(directory, True, timeout, max_turns)
        if code != 0:
            raise RuntimeError(f"dry-run failed for {label} exit={code}")
        validate_dry_run(directory)
        print(f"DRY_RUN_OK {label} dir={directory}")
        if dry_run_only:
            return True

    for attempt in range(1, retries + 2):
        directory = fresh_attempt(stage, job_number, "actual")
        materialize(stage, job_number, directory)
        code = run_wrapper(directory, False, timeout, max_turns)
        if code == 0:
            try:
                if stage == "synthesis":
                    record = validate.validate_synthesis(directory)
                else:
                    record = validate.validate_job(directory)
                validate.publish(record, accepted_path(stage, job_number))
                print(f"ACCEPTED {label} dir={directory}")
                return True
            except Exception as exc:
                print(f"POST_VALIDATE_FAIL {label} attempt={attempt} error={exc}")
        else:
            print(f"RUN_FAIL {label} attempt={attempt} exit={code}")
        if attempt <= retries:
            print(f"RETRY_NEW_DIR_REQUEST {label} next_attempt={attempt + 1}")
    return False


def parse_jobs(raw: str | None) -> list[int]:
    if not raw:
        return list(range(1, build.JOB_COUNT + 1))
    jobs = [int(value.strip()) for value in raw.split(",") if value.strip()]
    if not jobs or any(job < 1 or job > build.JOB_COUNT for job in jobs):
        raise ValueError("--jobs must contain numbers in 1..20")
    if len(set(jobs)) != len(jobs):
        raise ValueError("--jobs contains duplicates")
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HYP008 Grok forensics serially")
    parser.add_argument("--stage", choices=("pass-a", "pass-b", "synthesis", "all"), default="all")
    parser.add_argument("--jobs", help="comma-separated subset for pass-a/pass-b")
    parser.add_argument("--dry-run-only", action="store_true", help="wrapper request dry-run; never call Grok")
    parser.add_argument("--skip-preflight-dry-run", action="store_true")
    parser.add_argument("--retries", type=int, default=0, help="retry count; every retry uses a new dir/request")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--max-turns", type=int, default=40)
    args = parser.parse_args()
    if args.retries < 0:
        parser.error("--retries cannot be negative")
    jobs = parse_jobs(args.jobs)
    if args.stage in {"synthesis", "all"} and args.jobs:
        parser.error("--jobs is not valid for synthesis/all")
    build.check_inputs()

    with backend_lock():
        if args.stage in {"pass-a", "all"}:
            for job in jobs:
                if not execute_one(
                    "pass-a", job, dry_run_only=args.dry_run_only,
                    preflight_dry_run=not args.skip_preflight_dry_run,
                    retries=args.retries, timeout=args.timeout_seconds,
                    max_turns=args.max_turns,
                ):
                    return 3
            if not args.dry_run_only and jobs == list(range(1, 21)):
                print(json.dumps(validate.validate_campaign("pass-a"), indent=2))

        if args.stage in {"pass-b", "all"}:
            for job in jobs:
                if not execute_one(
                    "pass-b", job, dry_run_only=args.dry_run_only,
                    preflight_dry_run=not args.skip_preflight_dry_run,
                    retries=args.retries, timeout=args.timeout_seconds,
                    max_turns=args.max_turns,
                ):
                    return 4
            if not args.dry_run_only and jobs == list(range(1, 21)):
                print(json.dumps(validate.validate_campaign("both"), indent=2))

        if args.stage in {"synthesis", "all"}:
            if not execute_one(
                "synthesis", None, dry_run_only=args.dry_run_only,
                preflight_dry_run=not args.skip_preflight_dry_run,
                retries=args.retries, timeout=args.timeout_seconds,
                max_turns=max(args.max_turns, 60),
            ):
                return 5
    print("HYP008_GROK_PIPELINE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
