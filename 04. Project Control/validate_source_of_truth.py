#!/usr/bin/env python3
"""Fail closed when the source-of-truth registry overstates local availability."""

from __future__ import annotations

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


def main() -> int:
    errors: list[str] = []
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        print("SOURCE_OF_TRUTH_FAIL: entries must be a list")
        return 1
    backup_roots = payload.get("backup_roots", {})
    if not isinstance(backup_roots, dict):
        errors.append("backup_roots must be an object")
        backup_roots = {}

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

        local_path = WORKSPACE / Path(*pure_path.parts)
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
            backup_path = Path(backup_root_value) / Path(*pure_path.parts)
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

    markdown_rows, markdown_errors = load_markdown_rows(MARKDOWN_PATH)
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

    if errors:
        print(f"SOURCE_OF_TRUTH_FAIL: {len(errors)} error(s)")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "SOURCE_OF_TRUTH_OK: "
        f"entries={len(entries)} "
        f"local={sum(status_counts[s] for s in LOCAL_STATUSES)} "
        f"backup_only={status_counts[BACKUP_ONLY_STATUS]} "
        f"unavailable_unresolved={status_counts[UNRESOLVED_STATUS]}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
