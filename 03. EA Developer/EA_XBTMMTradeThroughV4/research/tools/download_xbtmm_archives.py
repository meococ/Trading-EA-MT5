#!/usr/bin/env python3
"""Resumable, hash-ledgered acquisition of official BitMEX DESIGN archives.

This tool is intentionally unable to request validation or holdout dates.  It
downloads only quote/trade source files; it never computes a strategy outcome.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


SCHEMA = "xbtmm_archive_ledger.v1"
DESIGN_START = date(2018, 1, 1)
DESIGN_END = date(2021, 12, 31)
KINDS = ("quote", "trade")
DEFAULT_BASE_URL = "https://s3-eu-west-1.amazonaws.com/public.bitmex.com/data"
CHUNK_BYTES = 1024 * 1024


class IntegrityError(RuntimeError):
    """Fail-closed archive or ledger integrity error."""


@dataclass(frozen=True)
class WorkItem:
    utc_day: date
    kind: str

    @property
    def token(self) -> str:
        return self.utc_day.strftime("%Y%m%d")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def canonical_without_record_hash(record: dict) -> str:
    payload = {key: value for key, value in record.items() if key != "record_sha256"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def seal_record(record: dict) -> dict:
    sealed = dict(record)
    sealed["record_sha256"] = text_sha256(canonical_without_record_hash(sealed))
    return sealed


def load_ledger(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records: list[dict] = []
    expected_previous = "0" * 64
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.endswith("\n"):
                raise IntegrityError(f"ledger line {line_number} is not newline-terminated")
            record = json.loads(raw)
            if record.get("schema_version") != SCHEMA:
                raise IntegrityError(f"ledger line {line_number} has wrong schema")
            if record.get("sequence") != line_number:
                raise IntegrityError(f"ledger line {line_number} has wrong sequence")
            if record.get("previous_record_sha256") != expected_previous:
                raise IntegrityError(f"ledger line {line_number} breaks the hash chain")
            actual = text_sha256(canonical_without_record_hash(record))
            if record.get("record_sha256") != actual:
                raise IntegrityError(f"ledger line {line_number} record hash mismatch")
            expected_previous = actual
            records.append(record)
    return records


def append_ledger(path: Path, records: list[dict], record: dict) -> dict:
    previous = records[-1]["record_sha256"] if records else "0" * 64
    pending = {
        "schema_version": SCHEMA,
        "sequence": len(records) + 1,
        "previous_record_sha256": previous,
        **record,
    }
    sealed = seal_record(pending)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(sealed, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    records.append(sealed)
    return sealed


def iter_days(start: date, end: date) -> Iterable[date]:
    if start < DESIGN_START or end > DESIGN_END or start > end:
        raise ValueError(
            f"requested window must stay inside DESIGN {DESIGN_START}..{DESIGN_END}"
        )
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def archive_path(root: Path, item: WorkItem) -> Path:
    return (
        root
        / "raw"
        / f"{item.utc_day.year:04d}"
        / f"{item.utc_day.month:02d}"
        / f"{item.kind}-{item.token}.csv.gz"
    )


def archive_url(base_url: str, item: WorkItem) -> str:
    return f"{base_url.rstrip('/')}/{item.kind}/{item.token}.csv.gz"


def validate_gzip(path: Path) -> None:
    with gzip.open(path, "rb") as handle:
        for _ in iter(lambda: handle.read(CHUNK_BYTES), b""):
            pass


def last_complete_by_key(records: list[dict]) -> dict[tuple[str, str], dict]:
    latest: dict[tuple[str, str], dict] = {}
    for record in records:
        if record.get("status") == "COMPLETE":
            latest[(record["utc_day"], record["kind"])] = record
    return latest


def verify_bound_existing(path: Path, record: dict) -> bool:
    if not path.exists():
        return False
    actual_bytes = path.stat().st_size
    if actual_bytes != record["bytes"]:
        raise IntegrityError(f"bound archive byte mismatch: {path}")
    actual_sha = sha256(path)
    if actual_sha != record["sha256"]:
        raise IntegrityError(f"bound archive SHA-256 mismatch: {path}")
    return True


def download_or_adopt(
    root: Path,
    base_url: str,
    item: WorkItem,
    bound_record: dict | None,
    adopt_existing: bool,
    timeout_seconds: int,
) -> dict | None:
    destination = archive_path(root, item)
    if bound_record is not None and verify_bound_existing(destination, bound_record):
        return None
    if destination.exists():
        if not adopt_existing:
            raise IntegrityError(f"unledgered archive exists; use --adopt-existing: {destination}")
        validate_gzip(destination)
        return {
            "utc_day": item.token,
            "kind": item.kind,
            "url": archive_url(base_url, item),
            "path": str(destination.resolve()),
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
            "etag": None,
            "last_modified": None,
            "origin": "ADOPTED_EXISTING",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETE",
        }

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    resume_at = partial.stat().st_size if partial.exists() else 0
    headers = {"User-Agent": "AlphaFactory-XBTMM-source-acquisition/1.0"}
    if resume_at:
        headers["Range"] = f"bytes={resume_at}-"
    request = urllib.request.Request(archive_url(base_url, item), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = getattr(response, "status", response.getcode())
            append = resume_at > 0 and status == 206
            if resume_at > 0 and status == 200:
                append = False
                resume_at = 0
            if status not in (200, 206):
                raise IntegrityError(f"unexpected HTTP status {status} for {request.full_url}")
            mode = "ab" if append else "wb"
            with partial.open(mode) as output:
                for chunk in iter(lambda: response.read(CHUNK_BYTES), b""):
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
    except urllib.error.HTTPError as exc:
        raise IntegrityError(f"HTTP {exc.code} for {request.full_url}") from exc
    except urllib.error.URLError as exc:
        raise IntegrityError(f"download failed for {request.full_url}: {exc.reason}") from exc

    validate_gzip(partial)
    partial.replace(destination)
    return {
        "utc_day": item.token,
        "kind": item.kind,
        "url": archive_url(base_url, item),
        "path": str(destination.resolve()),
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
        "etag": etag,
        "last_modified": last_modified,
        "origin": "DOWNLOADED",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE",
    }


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--from", dest="start", type=parse_day, required=True)
    parser.add_argument("--to", dest="end", type=parse_day, required=True)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--adopt-existing", action="store_true")
    args = parser.parse_args()

    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be between 1 and 16")
    days = list(iter_days(args.start, args.end))
    ledger_path = args.root / "archive_ledger.jsonl"
    records = load_ledger(ledger_path)
    bound = last_complete_by_key(records)
    work = [WorkItem(day, kind) for day in days for kind in KINDS]
    append_lock = threading.Lock()
    failures: list[str] = []
    completed = skipped = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_map = {
            pool.submit(
                download_or_adopt,
                args.root,
                args.base_url,
                item,
                bound.get((item.token, item.kind)),
                args.adopt_existing,
                args.timeout_seconds,
            ): item
            for item in work
        }
        for future in as_completed(future_map):
            item = future_map[future]
            try:
                result = future.result()
                if result is None:
                    skipped += 1
                    continue
                with append_lock:
                    append_ledger(ledger_path, records, result)
                completed += 1
                print(f"COMPLETE {item.token} {item.kind} {result['sha256']}", flush=True)
            except Exception as exc:  # noqa: BLE001 - aggregate all source failures
                failures.append(f"{item.token} {item.kind}: {exc}")
                print(f"FAILED {failures[-1]}", flush=True)

    summary = {
        "schema_version": "xbtmm_archive_acquisition_summary.v1",
        "requested_from": args.start.isoformat(),
        "requested_to": args.end.isoformat(),
        "calendar_days": len(days),
        "archives_expected": len(work),
        "archives_completed": completed,
        "archives_verified_existing": skipped,
        "failures": failures,
        "ledger": str(ledger_path.resolve()),
        "ledger_records": len(records),
        "ledger_tip_sha256": records[-1]["record_sha256"] if records else None,
        "source_gate_pass": not failures and completed + skipped == len(work),
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["source_gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
