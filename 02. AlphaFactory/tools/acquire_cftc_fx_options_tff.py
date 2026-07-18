#!/usr/bin/env python3
"""Acquire official CFTC TFF futures-only and combined annual archives.

This is a source-data acquisition step only. It downloads bytes and records
their hashes/ZIP members; it does not parse positioning or price outcomes.
The output root must remain on D: so MT5/research data is not written to C:.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(r"D:\Trading EA MT5")
DEFAULT_ROOT = WORKSPACE / "02. AlphaFactory" / "external" / "cftc_fx_options_tff" / "raw"
DEFAULT_YEARS = tuple(range(2017, 2024))
URLS = {
    "futures_only": "https://www.cftc.gov/files/dea/history/fut_fin_txt_{year}.zip",
    "futures_options_combined": "https://www.cftc.gov/files/dea/history/com_fin_txt_{year}.zip",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def ensure_d_drive(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise SystemExit(f"output_root_must_be_on_D:{resolved}")
    return resolved


def download_atomic(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AlphaFactory-CFTC-Research/1.0 (+local audit)"},
    )
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temp_path.open("wb") as output:
            if getattr(response, "status", 200) != 200:
                raise RuntimeError(f"http_status:{response.status}:{url}")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        with zipfile.ZipFile(temp_path) as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise RuntimeError(f"zip_crc_failure:{bad_member}:{url}")
        temp_path.replace(destination)
    finally:
        temp_path.unlink(missing_ok=True)


def acquire(root: Path, years: tuple[int, ...], refresh: bool) -> dict:
    root = ensure_d_drive(root)
    root.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    for year in years:
        for dataset, template in URLS.items():
            url = template.format(year=year)
            destination = root / Path(url).name
            if refresh or not destination.is_file():
                download_atomic(url, destination)
            with zipfile.ZipFile(destination) as archive:
                members = [
                    {
                        "name": item.filename,
                        "uncompressed_bytes": item.file_size,
                        "crc32": f"{item.CRC:08X}",
                    }
                    for item in archive.infolist()
                    if not item.is_dir()
                ]
            records.append(
                {
                    "dataset": dataset,
                    "year": year,
                    "url": url,
                    "path": destination.relative_to(WORKSPACE).as_posix(),
                    "bytes": destination.stat().st_size,
                    "sha256": sha256_file(destination),
                    "zip_members": members,
                }
            )
    manifest = {
        "schema_version": "alphafactory_cftc_tff_source_manifest.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "purpose": "pre_outcome_source_acquisition_only_no_price_or_performance_read",
        "official_archive_index": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm",
        "years": list(years),
        "holdout_years_downloaded": [],
        "records": records,
    }
    manifest_path = root.parent / "source_manifest.json"
    temp_path = manifest_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(manifest_path)
    return {"manifest": str(manifest_path), "records": len(records), "root": str(root)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--years", nargs="+", type=int, default=list(DEFAULT_YEARS))
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    years = tuple(sorted(set(args.years)))
    if not years or min(years) < 2006 or max(years) > 2023:
        raise SystemExit("acquisition_years_must_remain_within_2006_2023_holdout_sealed")
    print(json.dumps(acquire(args.root, years, args.refresh), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
