#!/usr/bin/env python3
"""Acquire point-in-time CME SDR FX daily files from the official FTP service.

The downloader is deliberately outcome-blind. It acquires only source ZIPs and
writes a hash-bound manifest. By default it excludes the 2024-2025 holdout.
"""

from __future__ import annotations

import argparse
import ftplib
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, NamedTuple, Sequence


FTP_HOST = "ftp.cmegroup.com"
FTP_ROOT = "/sdr/fx"
SCHEMA_VERSION = "cme_sdr_fx_acquisition.v1"
DAILY_FILE_RE = re.compile(r"^RT\.FX\.(\d{8})(?:\.csv)?\.zip$")


class RemoteFile(NamedTuple):
    year: int
    month: int
    name: str
    size_bytes: int | None

    @property
    def remote_path(self) -> str:
        return f"{FTP_ROOT}/{self.year:04d}/{self.month:02d}/{self.name}"

    @property
    def trade_date(self) -> str:
        match = DAILY_FILE_RE.fullmatch(self.name)
        if not match:  # pragma: no cover - construction is guarded
            raise ValueError(f"not a daily CME SDR file: {self.name}")
        value = match.group(1)
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def is_daily_file(name: str) -> bool:
    """Reject hourly/intraday fragments; keep only the daily consolidated ZIP."""

    return DAILY_FILE_RE.fullmatch(Path(name).name) is not None


def select_even_sample(files: Sequence[RemoteFile], per_month: int) -> list[RemoteFile]:
    """Select deterministic interior quantiles without looking at file contents."""

    ordered = sorted(files, key=lambda item: item.name)
    if per_month <= 0 or per_month >= len(ordered):
        return ordered
    selected: list[RemoteFile] = []
    for index in range(per_month):
        position = ((index + 1) * (len(ordered) + 1) // (per_month + 1)) - 1
        position = max(0, min(position, len(ordered) - 1))
        candidate = ordered[position]
        if candidate not in selected:
            selected.append(candidate)
    return selected


def require_d_drive(path: Path) -> Path:
    resolved = path.resolve()
    if os.name == "nt" and resolved.drive.upper() != "D:":
        raise ValueError(f"CME SDR corpus must be stored on D:, got {resolved}")
    return resolved


def connect(timeout_seconds: int = 30) -> ftplib.FTP:
    ftp = ftplib.FTP(timeout=timeout_seconds)
    ftp.connect(FTP_HOST)
    ftp.login()
    ftp.voidcmd("TYPE I")
    return ftp


def list_month(ftp: ftplib.FTP, year: int, month: int) -> list[RemoteFile]:
    directory = f"{FTP_ROOT}/{year:04d}/{month:02d}"
    rows: list[RemoteFile] = []
    try:
        entries: Iterable[tuple[str, dict[str, str]]] = ftp.mlsd(directory)
        for name, facts in entries:
            if not is_daily_file(name):
                continue
            raw_size = facts.get("size")
            rows.append(RemoteFile(year, month, name, int(raw_size) if raw_size else None))
    except (ftplib.error_perm, AttributeError):
        for raw_name in ftp.nlst(directory):
            name = Path(raw_name).name
            if not is_daily_file(name):
                continue
            size: int | None = None
            try:
                size = ftp.size(raw_name)
            except ftplib.all_errors:
                pass
            rows.append(RemoteFile(year, month, name, size))
    return sorted(rows, key=lambda item: item.name)


def inventory_remote(year_from: int, year_to: int, sample_per_month: int) -> list[RemoteFile]:
    ftp = connect()
    selected: list[RemoteFile] = []
    try:
        for year in range(year_from, year_to + 1):
            for month in range(1, 13):
                files = list_month(ftp, year, month)
                selected.extend(select_even_sample(files, sample_per_month))
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            ftp.close()
    return selected


def download_one(
    ftp: ftplib.FTP,
    remote: RemoteFile,
    raw_root: Path,
    retries: int = 3,
) -> Path:
    destination = raw_root / f"{remote.year:04d}" / f"{remote.month:02d}" / remote.name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and (
        remote.size_bytes is None or destination.stat().st_size == remote.size_bytes
    ):
        return destination
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with partial.open("wb") as handle:
                ftp.retrbinary(f"RETR {remote.remote_path}", handle.write, blocksize=256 * 1024)
            if remote.size_bytes is not None and partial.stat().st_size != remote.size_bytes:
                raise OSError(
                    f"size mismatch for {remote.name}: {partial.stat().st_size} != {remote.size_bytes}"
                )
            os.replace(partial, destination)
            return destination
        except (OSError, *ftplib.all_errors) as exc:
            last_error = exc
            partial.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(attempt)
    raise RuntimeError(f"failed to acquire {remote.remote_path}: {last_error}")


def acquire(
    root: Path,
    year_from: int,
    year_to: int,
    sample_per_month: int,
) -> dict:
    if year_to >= 2024:
        raise ValueError("holdout years 2024+ are sealed during source feasibility")
    raw_root = root / "raw"
    remote_files = inventory_remote(year_from, year_to, sample_per_month)
    ftp = connect()
    records: list[dict] = []
    try:
        for index, remote in enumerate(remote_files, start=1):
            try:
                path = download_one(ftp, remote, raw_root)
            except (RuntimeError, EOFError):
                try:
                    ftp.close()
                except ftplib.all_errors:
                    pass
                ftp = connect()
                path = download_one(ftp, remote, raw_root)
            records.append(
                {
                    "trade_date": remote.trade_date,
                    "remote_path": remote.remote_path,
                    "path": path.relative_to(root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
            if index % 25 == 0 or index == len(remote_files):
                print(f"CME_SDR_FX_ACQUIRE progress={index}/{len(remote_files)}")
    finally:
        try:
            ftp.quit()
        except ftplib.all_errors:
            ftp.close()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "host": FTP_HOST,
            "root": FTP_ROOT,
            "official_page": "https://www.cmegroup.com/market-data/repository/data.html",
        },
        "selection": {
            "year_from": year_from,
            "year_to": year_to,
            "sample_per_month": sample_per_month,
            "policy": "all daily consolidated files" if sample_per_month <= 0 else "deterministic interior quantiles per calendar month",
            "hourly_fragments_excluded": True,
            "holdout_2024_2025_acquired": False,
        },
        "file_count": len(records),
        "total_size_bytes": sum(row["size_bytes"] for row in records),
        "files": records,
        "research_authorized": False,
        "reason": "Source acquisition and density inspection do not authorize outcome research.",
    }
    manifest = root / "source_manifest.json"
    temp = manifest.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, manifest)
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    alpha_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=alpha_root / "external" / "cme_sdr_fx")
    parser.add_argument("--year-from", type=int, default=2017)
    parser.add_argument("--year-to", type=int, default=2023)
    parser.add_argument(
        "--sample-per-month",
        type=int,
        default=3,
        help="0 downloads every daily consolidated file; positive values sample each month",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.year_from > args.year_to:
        raise SystemExit("year-from must be <= year-to")
    root = require_d_drive(args.root)
    root.mkdir(parents=True, exist_ok=True)
    payload = acquire(root, args.year_from, args.year_to, args.sample_per_month)
    print(
        "CME_SDR_FX_ACQUIRE "
        f"files={payload['file_count']} bytes={payload['total_size_bytes']} "
        f"manifest={root / 'source_manifest.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
