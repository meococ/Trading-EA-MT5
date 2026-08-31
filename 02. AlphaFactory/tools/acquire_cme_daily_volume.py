#!/usr/bin/env python3
"""Acquire outcome-blind CME daily volume workbooks from official FTP.

The initial research contract deliberately seals 2024-2025.  Files and the
hash-bound manifest must remain below AlphaFactory/external on D:.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ftplib
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple, Sequence


FTP_HOST = "ftp.cmegroup.com"
FTP_ROOT = "/pub/pub/pub/daily_volume"
SCHEMA_VERSION = "cme_daily_volume_acquisition.v1"
FILE_RE = re.compile(r"^daily_volume_(\d{4})(\d{2})(\d{2})\.xlsx$")


class RemoteFile(NamedTuple):
    name: str
    size_bytes: int | None

    @property
    def trade_date(self) -> str:
        match = FILE_RE.fullmatch(self.name)
        if not match:  # pragma: no cover - construction is guarded
            raise ValueError(f"invalid daily-volume file: {self.name}")
        return "-".join(match.groups())

    @property
    def year(self) -> int:
        return int(self.name[13:17])

    @property
    def remote_path(self) -> str:
        return f"{FTP_ROOT}/{self.name}"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def require_d_external(path: Path) -> Path:
    resolved = path.resolve()
    if os.name == "nt" and resolved.drive.upper() != "D:":
        raise ValueError(f"CME daily-volume corpus must be on D:, got {resolved}")
    expected = Path(__file__).resolve().parents[1] / "external"
    if expected.resolve() not in (resolved, *resolved.parents):
        raise ValueError(f"corpus must remain below {expected.resolve()}, got {resolved}")
    return resolved


def connect(timeout_seconds: int = 45) -> ftplib.FTP:
    ftp = ftplib.FTP(timeout=timeout_seconds)
    ftp.connect(FTP_HOST)
    ftp.login()
    ftp.voidcmd("TYPE I")
    return ftp


def inventory_remote(year_from: int, year_to: int) -> list[RemoteFile]:
    ftp = connect()
    rows: list[RemoteFile] = []
    try:
        try:
            entries = ftp.mlsd(FTP_ROOT)
            for name, facts in entries:
                match = FILE_RE.fullmatch(name)
                if not match:
                    continue
                year = int(match.group(1))
                if year_from <= year <= year_to:
                    raw_size = facts.get("size")
                    rows.append(RemoteFile(name, int(raw_size) if raw_size else None))
        except (ftplib.error_perm, AttributeError):
            for raw_name in ftp.nlst(FTP_ROOT):
                name = Path(raw_name).name
                match = FILE_RE.fullmatch(name)
                if match and year_from <= int(match.group(1)) <= year_to:
                    rows.append(RemoteFile(name, None))
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            ftp.close()
    return sorted(rows, key=lambda row: row.name)


def download_partition(remotes: Sequence[RemoteFile], raw_root: Path) -> list[dict]:
    ftp = connect()
    records: list[dict] = []
    try:
        for remote in remotes:
            destination = raw_root / str(remote.year) / remote.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if not destination.is_file() or (
                remote.size_bytes is not None and destination.stat().st_size != remote.size_bytes
            ):
                partial = destination.with_suffix(destination.suffix + ".part")
                partial.unlink(missing_ok=True)
                with partial.open("wb") as handle:
                    ftp.retrbinary(f"RETR {remote.remote_path}", handle.write, blocksize=256 * 1024)
                if remote.size_bytes is not None and partial.stat().st_size != remote.size_bytes:
                    raise OSError(
                        f"size mismatch for {remote.name}: {partial.stat().st_size} != {remote.size_bytes}"
                    )
                os.replace(partial, destination)
            records.append(
                {
                    "trade_date": remote.trade_date,
                    "remote_path": remote.remote_path,
                    "path": destination,
                    "size_bytes": destination.stat().st_size,
                    "sha256": sha256_file(destination),
                }
            )
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            ftp.close()
    return records


def acquire(root: Path, year_from: int, year_to: int, workers: int) -> dict:
    if year_to >= 2024:
        raise ValueError("holdout years 2024-2025 are sealed before the frozen probe")
    root = require_d_external(root)
    raw_root = root / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    remotes = inventory_remote(year_from, year_to)
    if not remotes:
        raise RuntimeError("official FTP inventory returned no matching files")
    worker_count = max(1, min(workers, len(remotes)))
    partitions = [remotes[index::worker_count] for index in range(worker_count)]
    records: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(download_partition, partition, raw_root) for partition in partitions]
        for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            records.extend(future.result())
            print(f"CME_DAILY_VOLUME_ACQUIRE partitions={completed}/{worker_count}")
    records.sort(key=lambda row: row["trade_date"])
    workspace = Path(__file__).resolve().parents[2]
    for row in records:
        row["path"] = Path(row["path"]).relative_to(workspace).as_posix()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "host": FTP_HOST,
            "root": FTP_ROOT,
            "official_page": "https://www.cmegroup.com/market-data/volume-open-interest.html",
        },
        "selection": {
            "year_from": year_from,
            "year_to": year_to,
            "all_daily_files": True,
            "holdout_2024_2025_acquired": False,
            "schema_only_samples_outside_window": ["2025-01-02"],
        },
        "file_count": len(records),
        "total_size_bytes": sum(row["size_bytes"] for row in records),
        "files": records,
        "price_outcomes_accessed": False,
        "research_authorized": False,
    }
    manifest = root / "source_manifest.json"
    temporary = manifest.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, manifest)
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    alpha_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=alpha_root / "external" / "cme_daily_volume")
    parser.add_argument("--year-from", type=int, default=2017)
    parser.add_argument("--year-to", type=int, default=2023)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.year_from > args.year_to:
        raise SystemExit("year-from must be <= year-to")
    payload = acquire(args.root, args.year_from, args.year_to, args.workers)
    print(
        "CME_DAILY_VOLUME_ACQUIRE "
        f"files={payload['file_count']} bytes={payload['total_size_bytes']} "
        f"manifest={Path(args.root) / 'source_manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
