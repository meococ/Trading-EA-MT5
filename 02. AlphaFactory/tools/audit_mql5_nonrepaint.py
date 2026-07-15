#!/usr/bin/env python3
"""Fail-closed static audit of run-snapshotted MQL5 closed-bar invariants."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "alphafactory_nonrepaint_audit.v1"
BAR_FUNCTIONS = {"iOpen", "iHigh", "iLow", "iClose", "iVolume"}
COPY_FUNCTIONS = {
    "CopyRates",
    "CopyBuffer",
    "CopyTime",
    "CopyOpen",
    "CopyHigh",
    "CopyLow",
    "CopyClose",
    "CopyTickVolume",
    "CopyRealVolume",
}
EXTREME_FUNCTIONS = {"iHighest", "iLowest"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def sanitize_mql(text: str) -> str:
    """Remove comments/string contents while preserving offsets and newlines."""
    out = list(text)
    index = 0
    state = "code"
    quote = ""
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                out[index] = out[index + 1] = " "
                index += 2
                state = "line_comment"
                continue
            if char == "/" and nxt == "*":
                out[index] = out[index + 1] = " "
                index += 2
                state = "block_comment"
                continue
            if char in {'"', "'"}:
                quote = char
                out[index] = " "
                index += 1
                state = "string"
                continue
        elif state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                out[index] = " "
        elif state == "block_comment":
            if char == "*" and nxt == "/":
                out[index] = out[index + 1] = " "
                index += 2
                state = "code"
                continue
            if char != "\n":
                out[index] = " "
        elif state == "string":
            if char == "\\" and nxt:
                out[index] = out[index + 1] = " "
                index += 2
                continue
            if char == quote:
                state = "code"
            if char != "\n":
                out[index] = " "
        index += 1
    return "".join(out)


def split_args(body: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    for index, char in enumerate(body):
        if char in "([{":
            depth += 1
        elif char in ")]}" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            args.append(body[start:index].strip())
            start = index + 1
    args.append(body[start:].strip())
    return args


def iter_calls(text: str):
    function_names = sorted(COPY_FUNCTIONS | BAR_FUNCTIONS | EXTREME_FUNCTIONS | {"iTime"})
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, function_names)) + r")\s*\(")
    for match in pattern.finditer(text):
        open_index = text.find("(", match.start())
        depth = 1
        index = open_index + 1
        while index < len(text) and depth:
            if text[index] == "(":
                depth += 1
            elif text[index] == ")":
                depth -= 1
            index += 1
        if depth:
            yield match.group(1), match.start(), "", False
        else:
            yield match.group(1), match.start(), text[open_index + 1 : index - 1], True


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def is_literal_zero(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    return bool(re.fullmatch(r"(?:\(?0(?:\.0*)?\)?|0[Ll])", compact))


def is_literal_closed_bar_shift(value: str) -> bool:
    """Only a provably positive integer shift satisfies the static gate."""
    compact = re.sub(r"\s+", "", value)
    return bool(re.fullmatch(r"\(?[1-9]\d*[Ll]?\)?", compact))


def allowed_new_bar_gate(text: str, call_offset: int) -> bool:
    line_start = text.rfind("\n", 0, call_offset) + 1
    window = text[line_start : min(len(text), call_offset + 700)]
    assignment = re.search(
        r"\b(?:datetime|long|int)\s+(?P<current>[A-Za-z_]\w*)\s*=\s*iTime\s*\([^;]+\)\s*;",
        window,
        flags=re.DOTALL,
    )
    if not assignment:
        return False
    current = re.escape(assignment.group("current"))
    comparison = re.search(
        rf"if\s*\(\s*{current}\s*==\s*(?P<stored>[A-Za-z_]\w*)\s*\)\s*\{{?[^}}]{{0,300}}\breturn\s*;",
        window,
        flags=re.DOTALL,
    )
    if not comparison:
        return False
    stored = re.escape(comparison.group("stored"))
    return bool(re.search(rf"\b{stored}\s*=\s*{current}\s*;", window, flags=re.DOTALL))


def audit_file(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    original = path.read_text(encoding="utf-8-sig", errors="strict")
    text = sanitize_mql(original)
    findings: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []

    for function, offset, body, complete in iter_calls(text):
        line = line_number(text, offset)
        if not complete:
            findings.append(
                {"path": str(path), "line": line, "rule": "unclosed_call", "function": function}
            )
            continue
        args = split_args(body)
        if function in COPY_FUNCTIONS:
            if len(args) < 3:
                findings.append(
                    {"path": str(path), "line": line, "rule": "unparseable_copy_call", "function": function}
                )
            elif is_literal_zero(args[2]):
                findings.append(
                    {"path": str(path), "line": line, "rule": "bar_zero_copy", "function": function}
                )
            elif not is_literal_closed_bar_shift(args[2]):
                findings.append(
                    {
                        "path": str(path),
                        "line": line,
                        "rule": "unproven_closed_bar_shift",
                        "function": function,
                        "shift_expression": args[2],
                    }
                )
        elif function in BAR_FUNCTIONS:
            if len(args) < 3:
                findings.append(
                    {"path": str(path), "line": line, "rule": "unparseable_series_call", "function": function}
                )
            elif is_literal_zero(args[2]):
                findings.append(
                    {"path": str(path), "line": line, "rule": "bar_zero_series", "function": function}
                )
            elif not is_literal_closed_bar_shift(args[2]):
                findings.append(
                    {
                        "path": str(path),
                        "line": line,
                        "rule": "unproven_closed_bar_shift",
                        "function": function,
                        "shift_expression": args[2],
                    }
                )
        elif function in EXTREME_FUNCTIONS:
            if len(args) < 5:
                findings.append(
                    {"path": str(path), "line": line, "rule": "unparseable_extreme_call", "function": function}
                )
            elif is_literal_zero(args[4]):
                findings.append(
                    {"path": str(path), "line": line, "rule": "bar_zero_extreme_window", "function": function}
                )
            elif not is_literal_closed_bar_shift(args[4]):
                findings.append(
                    {
                        "path": str(path),
                        "line": line,
                        "rule": "unproven_closed_bar_shift",
                        "function": function,
                        "shift_expression": args[4],
                    }
                )
        elif function == "iTime" and len(args) >= 3 and is_literal_zero(args[2]):
            record = {"path": str(path), "line": line, "rule": "iTime_zero", "function": function}
            if allowed_new_bar_gate(text, offset):
                record["disposition"] = "allowed_new_bar_gate"
                allowed.append(record)
            else:
                findings.append(record)
        elif function == "iTime" and len(args) >= 3 and not is_literal_closed_bar_shift(args[2]):
            findings.append(
                {
                    "path": str(path),
                    "line": line,
                    "rule": "unproven_closed_bar_shift",
                    "function": function,
                    "shift_expression": args[2],
                }
            )

    direct_series = re.compile(r"\b(?:Open|High|Low|Close|Time|Volume)\s*\[\s*0\s*\]")
    for match in direct_series.finditer(text):
        findings.append(
            {
                "path": str(path),
                "line": line_number(text, match.start()),
                "rule": "direct_bar_zero_array",
                "function": match.group(0),
            }
        )
    return findings, allowed


def resolve_snapshot_files(manifest_path: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    run_dir = manifest_path.parent.resolve()
    snapshot_root = Path(str(manifest.get("snapshot_root") or "")).resolve()
    if not snapshot_root.is_relative_to(run_dir):
        raise ValueError("snapshot_root escapes the run directory")
    refs: list[dict[str, str]] = []
    source_path = Path(str(manifest.get("source_snapshot") or "")).resolve()
    source_hash = str(manifest.get("source_sha256") or "")
    refs.append({"path": str(source_path), "sha256": source_hash})
    include_refs = manifest.get("include_snapshots")
    if not isinstance(include_refs, list):
        raise ValueError("include_snapshots must be a list")
    for item in include_refs:
        if not isinstance(item, dict):
            raise ValueError("include snapshot entry must be an object")
        refs.append(
            {
                "path": str(Path(str(item.get("snapshot_path") or "")).resolve()),
                "sha256": str(item.get("sha256") or ""),
            }
        )
    for ref in refs:
        path = Path(ref["path"])
        if not path.is_file() or not path.is_relative_to(snapshot_root):
            raise ValueError(f"snapshot file is absent or escapes snapshot_root: {path}")
        if not re.fullmatch(r"[A-Fa-f0-9]{64}", ref["sha256"]):
            raise ValueError(f"invalid declared SHA256: {path}")
        actual = sha256_file(path)
        if actual != ref["sha256"].upper():
            raise ValueError(f"snapshot SHA256 mismatch: {path}")
    return refs


def run(manifest_path: Path, output_path: Path) -> int:
    manifest_path = manifest_path.resolve()
    manifest = load_json(manifest_path)
    refs = resolve_snapshot_files(manifest_path, manifest)
    findings: list[dict[str, Any]] = []
    allowed: list[dict[str, Any]] = []
    for ref in refs:
        file_findings, file_allowed = audit_file(Path(ref["path"]))
        findings.extend(file_findings)
        allowed.extend(file_allowed)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not findings else "FAIL",
        "hypothesis_id": manifest.get("hypothesis_id"),
        "run_id": manifest.get("run_id"),
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "audited_files": refs,
        "findings": findings,
        "allowed_new_bar_gates": allowed,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0 if payload["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        output_path = Path(args.out)
        code = run(Path(args.manifest), output_path)
        print(output_path.read_text(encoding="utf-8"), end="")
        return code
    except Exception as exc:
        print(f"NONREPAINT_AUDIT_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
