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
from typing import BinaryIO, Iterable, Iterator, Sequence


SCHEMA = "alpha-large-log-index-v1"
DEFAULT_MAX_SCAN_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_FULL_SHA_BYTES = 512 * 1024 * 1024
FINGERPRINT_SAMPLE_BYTES = 64 * 1024
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
    if sample.startswith(codecs.BOM_UTF32_LE):
        return "utf-32-le"
    if sample.startswith(codecs.BOM_UTF32_BE):
        return "utf-32-be"
    if sample.startswith(codecs.BOM_UTF16_LE):
        return "utf-16-le"
    if sample.startswith(codecs.BOM_UTF16_BE):
        return "utf-16-be"
    try:
        sample.decode("utf-8", errors="strict")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


class _BoundedReader:
    """Binary wrapper that exposes at most ``remaining`` bytes to TextIOWrapper."""

    def __init__(self, handle: BinaryIO, remaining: int | None):
        self._handle = handle
        self._remaining = remaining

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if self._remaining is not None:
            if self._remaining <= 0:
                return b""
            if size < 0 or size > self._remaining:
                size = self._remaining
        data = self._handle.read(size)
        if self._remaining is not None:
            self._remaining -= len(data)
        return data

    def readinto(self, b: bytearray) -> int:
        data = self.read(len(b))
        n = len(data)
        b[:n] = data
        return n


def _encoding_layout(encoding: str) -> tuple[int, bytes, bytes]:
    """Return code-unit width, newline bytes, and BOM for fixed-width Unicode."""
    layouts = {
        "utf-16-le": (2, b"\n\x00", codecs.BOM_UTF16_LE),
        "utf-16-be": (2, b"\x00\n", codecs.BOM_UTF16_BE),
        "utf-32-le": (4, b"\n\x00\x00\x00", codecs.BOM_UTF32_LE),
        "utf-32-be": (4, b"\x00\x00\x00\n", codecs.BOM_UTF32_BE),
    }
    return layouts.get(encoding.lower(), (1, b"\n", b""))


def _seek_to_complete_line(
    raw: BinaryIO,
    encoding: str,
    start_byte: int,
    max_bytes: int | None,
) -> int | None:
    """Position at a complete line without reading beyond the requested byte window.

    MT5 journals are commonly UTF-16. Seeking to an arbitrary byte and then using
    the generic ``utf-16`` decoder fails because the slice no longer begins with a
    BOM. Fixed-width encodings also require code-unit alignment before searching
    for the next newline.
    """
    width, newline, bom = _encoding_layout(encoding)
    requested_end = None if max_bytes is None else start_byte + max_bytes

    aligned_start = start_byte - (start_byte % width)
    raw.seek(aligned_start)

    if start_byte == 0:
        if bom:
            prefix = raw.read(len(bom))
            if prefix != bom:
                raw.seek(0)
        return None if requested_end is None else max(0, requested_end - raw.tell())

    while requested_end is None or raw.tell() + width <= requested_end:
        unit = raw.read(width)
        if len(unit) < width or unit == newline:
            break

    return None if requested_end is None else max(0, requested_end - raw.tell())


def iter_lines(
    path: Path,
    encoding: str,
    *,
    start_byte: int = 0,
    max_bytes: int | None = None,
) -> Iterator[tuple[int, str]]:
    if start_byte < 0:
        raise ValueError("start-byte must be >= 0")
    if max_bytes is not None and max_bytes < 1:
        raise ValueError("max-bytes must be positive")
    with path.open("rb") as raw:
        remaining = _seek_to_complete_line(raw, encoding, start_byte, max_bytes)
        bounded = _BoundedReader(raw, remaining)
        handle = codecs.getreader(encoding)(bounded, errors="replace")
        for line_number, line in enumerate(handle, start=1):
            yield line_number, line.rstrip("\r\n")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_fingerprint(path: Path) -> dict:
    stat = path.stat()
    digest = hashlib.sha256()
    samples: list[dict] = []
    with path.open("rb") as handle:
        head = handle.read(min(FINGERPRINT_SAMPLE_BYTES, stat.st_size))
        digest.update(head)
        samples.append({"offset": 0, "length": len(head)})
        if stat.st_size > FINGERPRINT_SAMPLE_BYTES:
            tail_offset = max(0, stat.st_size - FINGERPRINT_SAMPLE_BYTES)
            handle.seek(tail_offset)
            tail = handle.read(FINGERPRINT_SAMPLE_BYTES)
            digest.update(tail)
            samples.append({"offset": tail_offset, "length": len(tail)})
    return {
        "algorithm": "sha256(size|mtime_ns|head_tail_samples)",
        "value": digest.hexdigest(),
        "sample_bytes": FINGERPRINT_SAMPLE_BYTES,
        "samples": samples,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def build_source_meta(
    path: Path,
    encoding: str,
    *,
    full_sha256: bool,
    max_full_sha_bytes: int,
    line_count: int | None = None,
) -> dict:
    stat = path.stat()
    if max_full_sha_bytes < 1:
        raise ValueError("max-full-sha-bytes must be positive")
    sha = None
    sha_status = "omitted_by_size"
    if full_sha256 or stat.st_size <= max_full_sha_bytes:
        sha = sha256_file(path)
        sha_status = "computed_full"
    return {
        "path": str(path),
        "size_bytes": stat.st_size,
        "last_write_utc": _utc_iso(stat.st_mtime),
        "sha256": sha,
        "sha256_status": sha_status,
        "bounded_fingerprint": bounded_fingerprint(path),
        "encoding": encoding,
        **({} if line_count is None else {"line_count": line_count}),
    }


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
    start_byte: int = 0,
    max_bytes: int | None = DEFAULT_MAX_SCAN_BYTES,
    full_sha256: bool = False,
    max_full_sha_bytes: int = DEFAULT_MAX_FULL_SHA_BYTES,
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

    for line_number, text in iter_lines(path, encoding, start_byte=start_byte, max_bytes=max_bytes):
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
    scan_end = stat.st_size if max_bytes is None else min(stat.st_size, start_byte + max_bytes)
    return {
        "schema_version": SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": build_source_meta(
            path,
            encoding,
            full_sha256=full_sha256,
            max_full_sha_bytes=max_full_sha_bytes,
            line_count=line_count,
        ),
        "bounds": {
            "start_byte": start_byte,
            "max_bytes": max_bytes,
            "scan_end_byte": scan_end,
            "scan_truncated": scan_end < stat.st_size,
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
    start_byte: int = 0,
    max_bytes: int | None = DEFAULT_MAX_SCAN_BYTES,
    full_sha256: bool = False,
    max_full_sha_bytes: int = DEFAULT_MAX_FULL_SHA_BYTES,
) -> dict:
    path = path.resolve(strict=True)
    encoding = detect_encoding(path)
    regex = re.compile(expression)
    before: deque[dict] = deque(maxlen=context)
    stored: list[dict] = []
    active: list[dict] = []
    total_matches = 0
    line_count = 0

    for line_number, text in iter_lines(path, encoding, start_byte=start_byte, max_bytes=max_bytes):
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
    scan_end = stat.st_size if max_bytes is None else min(stat.st_size, start_byte + max_bytes)
    return {
        "schema_version": "alpha-large-log-search-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": build_source_meta(
            path,
            encoding,
            full_sha256=full_sha256,
            max_full_sha_bytes=max_full_sha_bytes,
            line_count=line_count,
        ),
        "query": {
            "expression": expression,
            "context": context,
            "max_matches": max_matches,
            "max_chars_per_line": max_chars,
            "start_byte": start_byte,
            "max_bytes": max_bytes,
            "scan_end_byte": scan_end,
            "scan_truncated": scan_end < stat.st_size,
        },
        "total_matches": total_matches,
        "stored_matches": len(stored),
        "truncated": total_matches > len(stored),
        "matches": stored,
    }


def read_window(
    path: Path,
    start: int,
    count: int,
    max_chars: int = 1000,
    *,
    start_byte: int = 0,
    max_bytes: int | None = DEFAULT_MAX_SCAN_BYTES,
    full_sha256: bool = False,
    max_full_sha_bytes: int = DEFAULT_MAX_FULL_SHA_BYTES,
) -> dict:
    if start < 1:
        raise ValueError("start must be >= 1")
    if count < 1 or count > 500:
        raise ValueError("count must be between 1 and 500")
    path = path.resolve(strict=True)
    encoding = detect_encoding(path)
    end = start + count - 1
    lines: list[dict] = []
    for line_number, text in iter_lines(path, encoding, start_byte=start_byte, max_bytes=max_bytes):
        if line_number < start:
            continue
        if line_number > end:
            break
        lines.append({"line": line_number, "text": _truncate(text, max_chars)})
    stat = path.stat()
    scan_end = stat.st_size if max_bytes is None else min(stat.st_size, start_byte + max_bytes)
    return {
        "schema_version": "alpha-large-log-window-v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": build_source_meta(
            path,
            encoding,
            full_sha256=full_sha256,
            max_full_sha_bytes=max_full_sha_bytes,
        ),
        "request": {
            "start": start,
            "count": count,
            "max_chars_per_line": max_chars,
            "start_byte": start_byte,
            "max_bytes": max_bytes,
            "scan_end_byte": scan_end,
            "scan_truncated": scan_end < stat.st_size,
        },
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


def _add_bound_args(cmd: argparse.ArgumentParser) -> None:
    cmd.add_argument("--start-byte", type=int, default=0)
    cmd.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_SCAN_BYTES)
    cmd.add_argument("--allow-full-scan", action="store_true")
    cmd.add_argument("--full-sha256", action="store_true")
    cmd.add_argument("--max-full-sha-bytes", type=int, default=DEFAULT_MAX_FULL_SHA_BYTES)


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
    _add_bound_args(inspect_cmd)

    search_cmd = sub.add_parser("search", help="Search with capped matches and context windows")
    search_cmd.add_argument("path", type=Path)
    search_cmd.add_argument("expression")
    search_cmd.add_argument("--out", type=Path)
    search_cmd.add_argument("--context", type=int, default=2)
    search_cmd.add_argument("--max-matches", type=int, default=50)
    search_cmd.add_argument("--max-chars", type=int, default=500)
    _add_bound_args(search_cmd)

    window_cmd = sub.add_parser("window", help="Read at most 500 numbered lines")
    window_cmd.add_argument("path", type=Path)
    window_cmd.add_argument("--start", type=int, required=True)
    window_cmd.add_argument("--count", type=int, default=100)
    window_cmd.add_argument("--out", type=Path)
    window_cmd.add_argument("--max-chars", type=int, default=1000)
    _add_bound_args(window_cmd)
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
            start_byte=args.start_byte,
            max_bytes=None if args.allow_full_scan else args.max_bytes,
            full_sha256=args.full_sha256,
            max_full_sha_bytes=args.max_full_sha_bytes,
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
            start_byte=args.start_byte,
            max_bytes=None if args.allow_full_scan else args.max_bytes,
            full_sha256=args.full_sha256,
            max_full_sha_bytes=args.max_full_sha_bytes,
        )
    else:
        payload = read_window(
            source,
            args.start,
            args.count,
            max_chars=args.max_chars,
            start_byte=args.start_byte,
            max_bytes=None if args.allow_full_scan else args.max_bytes,
            full_sha256=args.full_sha256,
            max_full_sha_bytes=args.max_full_sha_bytes,
        )

    source_sha = payload["source"].get("sha256") or payload["source"]["bounded_fingerprint"]["value"]
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
    sha_status = payload["source"].get("sha256_status", "unknown")
    print(
        "LARGE_LOG_ARTIFACT_CREATED "
        f"operation={args.command} path={output} source={source} "
        f"bytes={payload['source']['size_bytes']} sha256_status={sha_status} identity={source_sha}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
