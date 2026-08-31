from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


STARTUP_SOURCES = (
    ("01. GOAL/GOAL.md", "owner_goal"),
    ("INDEX.md", "workspace_map"),
)

ON_DEMAND_SOURCES = (
    ("05. Playbook/WORKFLOW.md", "execution_workflow"),
    ("04. Memory/source_of_truth.json", "canonical_path_registry"),
    (".codex/operator/STATUS.md", "non_authoritative_recovery_pointer"),
    ("04. Memory/hot.md", "non_authoritative_recent_cache"),
)

DEFERRED_CONTEXT = (
    ".codex/operator/EXPERIMENTS.jsonl",
    "04. Memory/research/CANDIDATE_REGISTRY.jsonl",
    "02. AlphaFactory/runs/",
    "02. AlphaFactory/runtime/",
    "03. EA Developer/<EA>/research/evidence/",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def contained_file(repo_root: Path, relative_path: str) -> Path:
    candidate = repo_root / relative_path
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"context source escapes repo root: {relative_path}") from exc
    return resolved


def describe_source(repo_root: Path, relative_path: str, role: str) -> dict[str, object]:
    path = contained_file(repo_root, relative_path)
    description: dict[str, object] = {
        "path": relative_path,
        "role": role,
        "exists": path.is_file(),
    }
    if path.is_file():
        description["bytes"] = path.stat().st_size
        description["sha256"] = sha256_file(path)
    return description


def run_git(repo_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def git_value(repo_root: Path, *arguments: str) -> str | None:
    result = run_git(repo_root, *arguments)
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def describe_git(repo_root: Path, max_dirty: int) -> tuple[dict[str, object], dict[str, object]]:
    commit = git_value(repo_root, "rev-parse", "HEAD")
    branch = git_value(repo_root, "symbolic-ref", "--quiet", "--short", "HEAD")
    upstream = git_value(repo_root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")

    ahead: int | None = None
    behind: int | None = None
    if commit and upstream:
        divergence = git_value(repo_root, "rev-list", "--left-right", "--count", f"HEAD...{upstream}")
        if divergence:
            parts = divergence.split()
            if len(parts) == 2:
                ahead, behind = (int(parts[0]), int(parts[1]))

    status_result = run_git(repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=normal")
    if status_result.returncode != 0:
        raise RuntimeError(status_result.stderr.strip() or "git status failed")
    status_records = [record for record in status_result.stdout.split("\0") if record]
    status_entries: list[dict[str, str]] = []
    index = 0
    while index < len(status_records):
        record = status_records[index]
        status = record[:2]
        entry = {"status": status, "path": record[3:] if len(record) > 3 else ""}
        if ("R" in status or "C" in status) and index + 1 < len(status_records):
            entry["source_path"] = status_records[index + 1]
            index += 1
        status_entries.append(entry)
        index += 1
    entries = status_entries[:max_dirty]

    repository = {
        "root": str(repo_root),
        "branch": branch or "DETACHED_OR_UNBORN",
        "commit": commit,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }
    worktree = {
        "dirty": bool(status_entries),
        "entry_count": len(status_entries),
        "entries": entries,
        "omitted_entries": max(0, len(status_entries) - len(entries)),
        "entry_limit": max_dirty,
    }
    return repository, worktree


def build_capsule(repo_root: Path, max_dirty: int) -> dict[str, object]:
    root = repo_root.resolve(strict=True)
    if not (root / ".git").exists():
        raise ValueError(f"not a Git worktree root: {root}")

    repository, worktree = describe_git(root, max_dirty)
    return {
        "schema_version": "alphafactory_context_capsule.v1",
        "read_only": True,
        "authority": "routing_only_no_execution_or_economic_authority",
        "repository": repository,
        "worktree": worktree,
        "context": {
            "startup": [describe_source(root, path, role) for path, role in STARTUP_SOURCES],
            "on_demand": [describe_source(root, path, role) for path, role in ON_DEMAND_SOURCES],
            "deferred_by_default": list(DEFERRED_CONTEXT),
            "selection_rule": "Open only the exact hypothesis, run, or evidence path needed for the current decision.",
        },
        "trust_boundary": {
            "repo_local_extensions_auto_executed": False,
            "external_code_rule": "Review source and obtain Owner scope before executing downloaded repo-local extensions or scripts.",
            "destructive_path_rule": "Resolve and verify containment under an allowed root before copy, move, archive, or delete.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Emit a bounded, read-only AlphaFactory context capsule.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Git worktree root (defaults to the repository containing this tool).",
    )
    parser.add_argument(
        "--max-dirty",
        type=int,
        default=12,
        choices=range(1, 51),
        metavar="1..50",
        help="Maximum number of dirty worktree entries included in the capsule.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        capsule = build_capsule(args.repo_root, args.max_dirty)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"CONTEXT_CAPSULE_FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(capsule, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
