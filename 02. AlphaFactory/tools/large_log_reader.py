#!/usr/bin/env python3
"""Bounded-memory inspection for very large MT5/AlphaFactory text and CSV logs.

The CLI never prints raw unbounded log content. It writes compact, hash-bound
artifacts for inspect/search/window operations and prints only a one-line receipt.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
import re
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence


SCHEMA = "alpha-large-log-index-v1"
DEFAULT_PATTERNS = (
    ("fatal", r"(?i)\bfatal\b"),
    ("error", r"(?i)\berror\b"),
    ("warning", r"(?i)\bwarn(?:ing)?\b"),
    ("timeout", r"(?i)\btime(?:d)?\s*out\b"),
    ("rejected", r"(?i)\breject(?:ed|ion)?\b"),
)


def _utc_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max(0, max_chars - 16)] + "...[truncated]"


def detect_encoding(path: Path) -> str:
    with path.open("rb") as handle:
        sample = handle.read(65536)
    if sample.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if sample.startswith(codecs.BOM_UTF32_LE) or sample.startswith(codecs.BOM_UTF32_BE):
        return "utf-32"
    if sample.startswith(codecs.BOM_UTF16_LE) or sample.startswith(codecs.BOM_UTF16_BE):
        return "utf-16"
    try:
        sample.decode("utf-8", errors="strict")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def iter_lines(path: Path, encoding: str) -> Iterator[tuple[int, str]]:
    with path.open("r", encoding=encoding, errors="replace", newline="") as handle:
        for line_number, line in enumerate(handle, start=1):
            yield line_number, line.rstrip("\r\n")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def parse_patterns(values: Sequence[str] | None) -> list[tuple[str, str]]:
    if not values:
        return list(DEFAULT_PATTERNS)
    parsed: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, value in enumerate(values, start=1):
        if "=" in value:
            name, expression = value.split("=", 1)
        else:
            name, expression = f"pattern_{index}", value
        name = name.strip()
        expression = expression.strip()
        if not name or not expression:
            raise ValueError(f"Invalid pattern declaration: {value!r}")
        if name in seen:
            raise ValueError(f"Duplicate pattern name: {name}")
        re.compile(expression)
        seen.add(name)
        parsed.append((name, expression))
    return parsed


def inspect_log(
    path: Path,
    *,
    head_count: int = 20,
    tail_count: int = 20,
    patterns: Sequence[tuple[str, str]] = DEFAULT_PATTERNS,
    max_samples_per_pattern: int = 10,
    max_chars: int = 500,
) -> dict:
    path = path.resolve(strict=True)
    if not path.is_file():
        raise ValueError(f"Source is not a file: {path}")
    encoding = detect_encoding(path)
    compiled = [(name, expression, re.compile(expression)) for name, expression in patterns]
    counts = {name: 0 for name, _, _ in compiled}
    samples: dict[str, list[dict]] = {name: [] for name, _, _ in compiled}
    head: list[dict] = []
    tail: deque[dict] = deque(maxlen=max(0, tail_count))
    line_count = 0

    for line_number, text in iter_lines(path, encoding):
        line_count = line_number
        item = {"line": line_number, "text": _truncate(text, max_chars)}
        if len(head) < head_count:
            head.append(item)
        if tail_count:
            tail.append(item)
        for name, _, regex in compiled:
            if regex.search(text):
                counts[name] += 1
                if len(samples[name]) < max_samples_per_pattern:
                    samples[name].append(item)

    stat = path.stat()
    return {
        "schema_version": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(path),
            "size_bytes": stat.st_size,
            "last_write_utc": _utc_iso(stat.st_mtime),
            "sha256": sha256_file(path),
            "encoding": encoding,
            "line_count": line_count,
        },
        "bounds": {
            "head_lines": head_count,
            "tail_lines": tail_count,
            "max_samples_per_pattern": max_samples_per_pattern,
            "max_chars_per_line": max_chars,
        },
        "head": head,
        "tail": list(tail),
        "patterns": [
            {
                "name": name,
                "expression": expression,
                "count": counts[name],
                "samples": samples[name],
            }
            for name, expression, _ in compiled
        ],
    }


def search_log(
    path: Path,
    expression: str,
    *,
    context: int = 2,
    max_matches: int = 50,
    max_chars: int = 500,
) -> dict:
    path = path.resolve(strict=True)
    encoding = detect_encoding(path)
    regex = re.compile(expression)
    before: deque[dict] = deque(maxlen=context)
    stored: list[dict] = []
    active: list[dict] = []
    total_matches = 0
    line_count = 0

    for line_number, text in iter_lines(path, encoding):
        line_count = line_number
        item = {"line": line_number, "text": _truncate(text, max_chars)}
        still_active: list[dict] = []
        for block in active:
            block["lines"].append(item)
            block["remaining_after"] -= 1
            if block["remaining_after"] > 0:
                still_active.append(block)
        active = still_active

        if regex.search(text):
            total_matches += 1
            if len(stored) < max_matches:
                block = {
                    "match_line": line_number,
                    "lines": list(before) + [item],
                    "remaining_after": context,
                }
                stored.append(block)
                if context:
                    active.append(block)
        before.append(item)

    for block in stored:
        block.pop("remaining_after", None)
    stat = path.stat()
    return {
        "schema_version": "alpha-large-log-search-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(path),
            "size_bytes": stat.st_size,
            "last_write_utc": _utc_iso(stat.st_mtime),
            "sha256": sha256_file(path),
            "encoding": encoding,
            "line_count": line_count,
        },
        "query": {
            "expression": expression,
            "context": context,
            "max_matches": max_matches,
            "max_chars_per_line": max_chars,
        },
        "total_matches": total_matches,
        "stored_matches": len(stored),
        "truncated": total_matches > len(stored),
        "matches": stored,
    }


def read_window(path: Path, start: int, count: int, max_chars: int = 1000) -> dict:
    if start < 1:
        raise ValueError("start must be >= 1")
    if count < 1 or count > 500:
        raise ValueError("count must be between 1 and 500")
    path = path.resolve(strict=True)
    encoding = detect_encoding(path)
    end = start + count - 1
    lines: list[dict] = []
    for line_number, text in iter_lines(path, encoding):
        if line_number < start:
            continue
        if line_number > end:
            break
        lines.append({"line": line_number, "text": _truncate(text, max_chars)})
    stat = path.stat()
    return {
        "schema_version": "alpha-large-log-window-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "path": str(path),
            "size_bytes": stat.st_size,
            "last_write_utc": _utc_iso(stat.st_mtime),
            "encoding": encoding,
        },
        "request": {"start": start, "count": count, "max_chars_per_line": max_chars},
        "returned": len(lines),
        "lines": lines,
    }


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def _default_output(alpha_root: Path, source: Path, operation: str, source_sha: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", source.name)
    return alpha_root / "runtime" / "log_indexes" / source_sha[:12] / f"{safe_name}.{operation}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_cmd = sub.add_parser("inspect", help="Create a compact streaming index and samples")
    inspect_cmd.add_argument("path", type=Path)
    inspect_cmd.add_argument("--out", type=Path)
    inspect_cmd.add_argument("--head", type=int, default=20)
    inspect_cmd.add_argument("--tail", type=int, default=20)
    inspect_cmd.add_argument("--pattern", action="append")
    inspect_cmd.add_argument("--max-samples", type=int, default=10)
    inspect_cmd.add_argument("--max-chars", type=int, default=500)

    search_cmd = sub.add_parser("search", help="Search with capped matches and context windows")
    search_cmd.add_argument("path", type=Path)
    search_cmd.add_argument("expression")
    search_cmd.add_argument("--out", type=Path)
    search_cmd.add_argument("--context", type=int, default=2)
    search_cmd.add_argument("--max-matches", type=int, default=50)
    search_cmd.add_argument("--max-chars", type=int, default=500)

    window_cmd = sub.add_parser("window", help="Read at most 500 numbered lines")
    window_cmd.add_argument("path", type=Path)
    window_cmd.add_argument("--start", type=int, required=True)
    window_cmd.add_argument("--count", type=int, default=100)
    window_cmd.add_argument("--out", type=Path)
    window_cmd.add_argument("--max-chars", type=int, default=1000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    alpha_root = Path(__file__).resolve().parents[1]
    source = args.path.resolve(strict=True)

    if args.command == "inspect":
        if args.head < 0 or args.tail < 0 or args.max_samples < 0:
            raise ValueError("head, tail, and max-samples must be non-negative")
        if args.max_chars < 80 or args.max_chars > 5000:
            raise ValueError("max-chars must be between 80 and 5000")
        payload = inspect_log(
            source,
            head_count=args.head,
            tail_count=args.tail,
            patterns=parse_patterns(args.pattern),
            max_samples_per_pattern=args.max_samples,
            max_chars=args.max_chars,
        )
    elif args.command == "search":
        if args.context < 0 or args.context > 20:
            raise ValueError("context must be between 0 and 20")
        if args.max_matches < 1 or args.max_matches > 200:
            raise ValueError("max-matches must be between 1 and 200")
        payload = search_log(
            source,
            args.expression,
            context=args.context,
            max_matches=args.max_matches,
            max_chars=args.max_chars,
        )
    else:
        payload = read_window(source, args.start, args.count, max_chars=args.max_chars)

    source_sha = payload["source"].get("sha256") or sha256_file(source)
    payload["source"]["sha256"] = source_sha
    operation_key = args.command
    if args.command == "search":
        query_key = hashlib.sha256(
            f"{args.expression}|{args.context}|{args.max_matches}|{args.max_chars}".encode("utf-8")
        ).hexdigest()[:10]
        operation_key = f"search_{query_key}"
    elif args.command == "window":
        operation_key = f"window_{args.start}_{args.count}"
    output = args.out.resolve() if args.out else _default_output(alpha_root, source, operation_key, source_sha)
    _atomic_json(output, payload)
    print(
        "LARGE_LOG_ARTIFACT_CREATED "
        f"operation={args.command} path={output} source={source} "
        f"bytes={payload['source']['size_bytes']} sha256={source_sha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
