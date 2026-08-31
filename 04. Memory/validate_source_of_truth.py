#!/usr/bin/env python3
"""Validate local truth fail-closed while treating declared portable backups explicitly."""

from __future__ import annotations

import argparse
import json
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path, PurePosixPath


WORKSPACE = Path(__file__).resolve().parents[1]
JSON_PATH = Path(__file__).with_name("source_of_truth.json")
MARKDOWN_PATH = Path(__file__).with_name("source_of_truth.md")

LOCAL_STATUSES = {"authoritative", "evidence", "archive", "invalidated"}
BACKUP_ONLY_STATUS = "backup-only"
UNRESOLVED_STATUS = "unavailable-unresolved"
ALL_STATUSES = LOCAL_STATUSES | {BACKUP_ONLY_STATUS, UNRESOLVED_STATUS}
ROW_RE = re.compile(
    r"^\| `(?P<path>[^`]+)` \| (?P<status>[^|]+?) \| (?P<reason>.*) \|$"
)


def configure_console_output() -> None:
    """Keep fail-closed diagnostics printable on stock Windows consoles."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (AttributeError, OSError, ValueError):
                pass


def canonical_markdown_reason(value: str) -> str:
    return " ".join(value.split()).replace("|", r"\|")


def load_markdown_rows(path: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    rows: dict[str, tuple[str, str]] = {}
    errors: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        match = ROW_RE.match(line)
        if not match:
            continue
        relative_path = match.group("path")
        status = match.group("status").strip()
        reason = match.group("reason").strip()
        if relative_path in rows:
            errors.append(
                f"markdown duplicate path at line {line_number}: {relative_path}"
            )
        rows[relative_path] = (status, reason)
    return rows, errors


def validate(
    *,
    json_path: Path,
    markdown_path: Path,
    workspace: Path,
    strict_backups: bool,
) -> tuple[list[str], list[str], Counter[str], int]:
    errors: list[str] = []
    warnings: list[str] = []
    payload = json.loads(json_path.read_text(encoding="utf-8-sig"))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return ["entries must be a list"], warnings, Counter(), 0
    backup_roots = payload.get("backup_roots", {})
    if not isinstance(backup_roots, dict):
        errors.append("backup_roots must be an object")
        backup_roots = {}
    backup_root_modes = payload.get("backup_root_modes", {})
    if not isinstance(backup_root_modes, dict):
        errors.append("backup_root_modes must be an object")
        backup_root_modes = {}
    unavailable_optional_roots: set[str] = set()
    unavailable_error_roots: set[str] = set()

    json_rows: dict[str, tuple[str, str]] = {}
    status_counts: Counter[str] = Counter()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {index} is not an object")
            continue

        relative_path = entry.get("path")
        status = entry.get("status")
        reason = entry.get("reason")
        if not isinstance(relative_path, str) or not relative_path:
            errors.append(f"entry {index} has no non-empty path")
            continue
        pure_path = PurePosixPath(relative_path)
        if (
            Path(relative_path).is_absolute()
            or pure_path.is_absolute()
            or "\\" in relative_path
            or any(part in {"", ".", ".."} for part in pure_path.parts)
            or pure_path.as_posix() != relative_path
        ):
            errors.append(f"path is not normalized workspace-relative POSIX: {relative_path}")
            continue
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"entry {index} has no non-empty reason: {relative_path}")
            continue
        if relative_path in json_rows:
            errors.append(f"JSON duplicate path: {relative_path}")
        json_rows[relative_path] = (status, canonical_markdown_reason(reason))

        if status not in ALL_STATUSES:
            errors.append(f"unknown status {status!r}: {relative_path}")
            continue
        status_counts[status] += 1

        local_path = workspace / Path(*pure_path.parts)
        is_file = local_path.is_file()
        if status in LOCAL_STATUSES and not is_file:
            errors.append(
                f"locally required path is absent or not a file ({status}): {relative_path}"
            )
        elif status in {BACKUP_ONLY_STATUS, UNRESOLVED_STATUS}:
            original_status = entry.get("original_status")
            if original_status not in LOCAL_STATUSES:
                errors.append(
                    "backup-only entry needs original_status in "
                    f"{sorted(LOCAL_STATUSES)}: {relative_path}"
                )
            if local_path.exists():
                errors.append(
                    "non-local entry now exists locally and must be reclassified: "
                    f"{relative_path}"
                )
            backup_root_id = entry.get("backup_root_id")
            backup_root_value = backup_roots.get(backup_root_id)
            if not isinstance(backup_root_value, str) or not backup_root_value:
                errors.append(
                    f"invalid backup_root_id {backup_root_id!r}: {relative_path}"
                )
                continue
            backup_root_path = Path(backup_root_value)
            backup_mode = backup_root_modes.get(backup_root_id, "required")
            if backup_mode not in {"required", "optional"}:
                errors.append(
                    f"invalid backup root mode {backup_mode!r} for {backup_root_id!r}"
                )
                continue
            if not backup_root_path.is_dir():
                if backup_mode == "optional" and not strict_backups:
                    if str(backup_root_id) not in unavailable_optional_roots:
                        warnings.append(
                            "optional backup root is unavailable; backup hashes were not audited: "
                            f"{backup_root_id}={backup_root_path}"
                        )
                        unavailable_optional_roots.add(str(backup_root_id))
                    continue
                if str(backup_root_id) not in unavailable_error_roots:
                    errors.append(
                        f"backup root is unavailable ({backup_mode}): "
                        f"{backup_root_id}={backup_root_path}"
                    )
                    unavailable_error_roots.add(str(backup_root_id))
                continue
            backup_path = backup_root_path / Path(*pure_path.parts)
            if status == BACKUP_ONLY_STATUS:
                expected_hash = entry.get("backup_sha256")
                if not backup_path.is_file():
                    errors.append(f"backup file is absent: {backup_path}")
                elif not isinstance(expected_hash, str) or not re.fullmatch(
                    r"[A-F0-9]{64}", expected_hash
                ):
                    errors.append(f"invalid backup_sha256: {relative_path}")
                else:
                    actual_hash = hashlib.sha256(backup_path.read_bytes()).hexdigest().upper()
                    if actual_hash != expected_hash:
                        errors.append(
                            "backup hash mismatch for "
                            f"{relative_path}: expected={expected_hash}, actual={actual_hash}"
                        )
            elif backup_path.exists():
                errors.append(
                    "unresolved entry is now present at the declared backup root and "
                    f"must be reclassified: {relative_path}"
                )

    markdown_rows, markdown_errors = load_markdown_rows(markdown_path)
    errors.extend(markdown_errors)
    if not markdown_rows:
        errors.append("no registry rows found in source_of_truth.md")

    missing_from_markdown = sorted(set(json_rows) - set(markdown_rows))
    extra_in_markdown = sorted(set(markdown_rows) - set(json_rows))
    if missing_from_markdown:
        errors.append(
            "JSON paths missing from Markdown: " + ", ".join(missing_from_markdown)
        )
    if extra_in_markdown:
        errors.append(
            "Markdown paths missing from JSON: " + ", ".join(extra_in_markdown)
        )
    for relative_path in sorted(set(json_rows) & set(markdown_rows)):
        json_status, json_reason = json_rows[relative_path]
        markdown_status, markdown_reason = markdown_rows[relative_path]
        if json_status != markdown_status:
            errors.append(
                "status mismatch for "
                f"{relative_path}: JSON={json_status!r}, "
                f"Markdown={markdown_status!r}"
            )
        if json_reason != markdown_reason:
            errors.append(f"reason mismatch for {relative_path}")

    return errors, warnings, status_counts, len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, default=JSON_PATH)
    parser.add_argument("--markdown", type=Path, default=MARKDOWN_PATH)
    parser.add_argument("--workspace", type=Path, default=WORKSPACE)
    parser.add_argument(
        "--strict-backups",
        action="store_true",
        help="Fail when an optional external backup root is unavailable",
    )
    args = parser.parse_args()
    errors, warnings, status_counts, entry_count = validate(
        json_path=args.json.resolve(),
        markdown_path=args.markdown.resolve(),
        workspace=args.workspace.resolve(),
        strict_backups=args.strict_backups,
    )
    if errors:
        print(f"SOURCE_OF_TRUTH_FAIL: {len(errors)} error(s)")
        for error in errors:
            print(f"- {error}")
        return 1

    for warning in warnings:
        print(f"SOURCE_OF_TRUTH_WARN: {warning}")

    print(
        "SOURCE_OF_TRUTH_OK: "
        f"entries={entry_count} "
        f"local={sum(status_counts[s] for s in LOCAL_STATUSES)} "
        f"backup_only={status_counts[BACKUP_ONLY_STATUS]} "
        f"unavailable_unresolved={status_counts[UNRESOLVED_STATUS]} "
        f"optional_backup_warnings={len(warnings)}"
    )
    return 0


if __name__ == "__main__":
    configure_console_output()
    sys.exit(main())
