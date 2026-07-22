#!/usr/bin/env python3
"""Resumable sequential batch driver for HYP-007..010 Grok vision chunks.

Invokes only the grok-cli-runner wrapper. Skips a chunk only when its current
summary proves success=true, structured schema passed, image inspection true,
coverage 10/10, and exact ordered manifest case IDs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RESEARCH = Path(__file__).resolve().parent
CONTEXT = ROOT / ".context"
RUNNER = Path(r"C:\Users\ADMIN\.codex\skills\grok-cli-runner\scripts\run_grok_cli.py")
COLLECTOR = RESEARCH / "collect_hyp007_010_grok_review.py"
TASK_PREFIX = "mzms-xau-007-010-vision"
SHORT_IDS = ("007", "008", "009", "010")
CHUNK_COUNT = 10
PERMISSION_MODES = ("auto", "bypassPermissions")
DEFAULT_PERMISSION_MODE = "bypassPermissions"


def load_module_collector():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "collect_hyp007_010_grok_review", COLLECTOR
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def task_dir(short_id: str, chunk_number: int) -> Path:
    return CONTEXT / f"{TASK_PREFIX}-{short_id}-c{chunk_number:02d}"


def enumerate_chunks(
    only_short: str | None = None,
    only_chunks: list[int] | None = None,
) -> list[tuple[str, int, Path]]:
    rows: list[tuple[str, int, Path]] = []
    shorts = (only_short,) if only_short else SHORT_IDS
    chunk_numbers = only_chunks or list(range(1, CHUNK_COUNT + 1))
    for short in shorts:
        for number in chunk_numbers:
            path = task_dir(short, number)
            rows.append((short, number, path))
    return rows


def chunk_already_valid(collector_mod: Any, path: Path) -> tuple[bool, str]:
    summary_path = path / "summary.json"
    if not summary_path.exists():
        return False, "summary_missing"
    ok, reason, _payload = collector_mod.valid_candidate(summary_path)
    return ok, reason


def build_runner_cmd(
    path: Path,
    *,
    permission_mode: str,
    dry_run: bool,
    timeout_seconds: int,
    max_turns: int,
) -> list[str]:
    """Build the exact run_grok_cli argv for one chunk.

    Local read-only image corpus defaults to bypassPermissions so the vision
    agent can open PNGs without interactive approval. --always-approve is
    attached only for that mode; auto keeps the stricter transport.
    """
    if permission_mode not in PERMISSION_MODES:
        raise ValueError(
            f"permission_mode must be one of {PERMISSION_MODES}, got {permission_mode!r}"
        )
    request = path / "grok-request.json"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--request-file",
        str(request),
        "--output-dir",
        str(path),
        "--response-artifact",
        "grok-response.json",
        "--cwd",
        str(ROOT),
        "--permission-mode",
        permission_mode,
        "--no-plan",
        "--no-subagents",
        "--disable-web-search",
        "--max-turns",
        str(max_turns),
        "--timeout-seconds",
        str(timeout_seconds),
    ]
    if permission_mode == "bypassPermissions":
        cmd.append("--always-approve")
    if dry_run:
        cmd.append("--dry-run")
    return cmd


def run_one(
    path: Path,
    *,
    permission_mode: str = DEFAULT_PERMISSION_MODE,
    dry_run: bool,
    timeout_seconds: int,
    max_turns: int,
) -> int:
    request = path / "grok-request.json"
    if not request.exists():
        print(f"MISSING_REQUEST {request}")
        return 2
    if not RUNNER.exists():
        print(f"MISSING_RUNNER {RUNNER}")
        return 2
    cmd = build_runner_cmd(
        path,
        permission_mode=permission_mode,
        dry_run=dry_run,
        timeout_seconds=timeout_seconds,
        max_turns=max_turns,
    )
    print("RUN", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=str(ROOT))
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sequential resumable HYP-007..010 Grok vision batch"
    )
    parser.add_argument(
        "--short",
        choices=SHORT_IDS,
        help="Limit to one hypothesis short id (007/008/009/010)",
    )
    parser.add_argument(
        "--chunks",
        help="Comma-separated chunk numbers, e.g. 1,2,10",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if current summary already validates",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to grok-cli-runner (no backend call)",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=1800,
        help="Wrapper process timeout per chunk (default 1800)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=40,
        help="Grok max turns per chunk (default 40 for image review)",
    )
    parser.add_argument(
        "--permission-mode",
        choices=PERMISSION_MODES,
        default=DEFAULT_PERMISSION_MODE,
        help=(
            "Permission mode passed exactly to run_grok_cli "
            f"(default {DEFAULT_PERMISSION_MODE}; local read-only image corpus). "
            "When bypassPermissions is selected, also pass --always-approve."
        ),
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="Print skip/run plan without invoking Grok",
    )
    args = parser.parse_args()
    only_chunks = None
    if args.chunks:
        only_chunks = [int(x.strip()) for x in args.chunks.split(",") if x.strip()]
        for number in only_chunks:
            if number < 1 or number > CHUNK_COUNT:
                raise SystemExit(f"chunk number out of range 1..{CHUNK_COUNT}: {number}")

    collector_mod = load_module_collector()
    plan = enumerate_chunks(args.short, only_chunks)
    skipped = 0
    ran = 0
    failed = 0
    for short, number, path in plan:
        label = f"{short}/chunk_{number:02d}"
        if not args.force:
            ok, reason = chunk_already_valid(collector_mod, path)
            if ok:
                print(f"SKIP_VALID {label} reason={reason}")
                skipped += 1
                continue
            print(f"NEED_RUN {label} reason={reason}")
        else:
            print(f"FORCE_RUN {label}")
        if args.status_only:
            continue
        code = run_one(
            path,
            permission_mode=args.permission_mode,
            dry_run=args.dry_run,
            timeout_seconds=args.timeout_seconds,
            max_turns=args.max_turns,
        )
        ran += 1
        if code != 0:
            print(f"CHUNK_FAIL {label} exit={code}")
            failed += 1
            # sequential fail-stop keeps resume simple and avoids burn
            print(
                json.dumps(
                    {
                        "stopped_at": label,
                        "ran": ran,
                        "skipped": skipped,
                        "failed": failed,
                        "remaining": len(plan) - skipped - ran,
                    },
                    indent=2,
                )
            )
            return code
        # post-run hard validation for real runs
        if not args.dry_run:
            ok, reason = chunk_already_valid(collector_mod, path)
            if not ok:
                print(f"POST_VALIDATE_FAIL {label} reason={reason}")
                failed += 1
                return 3
            print(f"CHUNK_OK {label}")
        else:
            print(f"DRY_RUN_DONE {label}")

    print(
        json.dumps(
            {
                "plan_size": len(plan),
                "skipped_valid": skipped,
                "ran": ran,
                "failed": failed,
                "status_only": args.status_only,
                "dry_run": args.dry_run,
            },
            indent=2,
        )
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
