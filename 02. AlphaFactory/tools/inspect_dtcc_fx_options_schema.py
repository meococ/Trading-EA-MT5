#!/usr/bin/env python3
"""Acquire four official DTCC CFTC FX cumulative files for schema feasibility.

This is source inspection only: no MT5 initialization, FX bars, forward returns,
or performance metrics. Samples span the legacy, 2020, rewrite, and phase-2
report layouts while remaining on D:.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import tempfile
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(r"D:\Trading EA MT5")
ROOT = WORKSPACE / "02. AlphaFactory" / "external" / "dtcc_fx_options_sdr" / "schema_samples"
SAMPLES = {
    "2018-01-02": "https://kgc0418-tdw-data2-0.s3.amazonaws.com/slices/CUMULATIVE_FOREX_2018_01_02.zip",
    "2020-12-01": "https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/CFTC_CUMULATIVE_FOREX_2020_12_01.zip",
    "2023-01-03": "https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/CFTC_CUMULATIVE_FOREX_2023_01_03.zip",
    "2024-07-16": "https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/CFTC_CUMULATIVE_FOREX_2024_07_16.zip",
    "2025-01-02": "https://kgc0418-tdw-data-0.s3.amazonaws.com/cftc/eod/CFTC_CUMULATIVE_FOREX_2025_01_02.zip",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def ensure_d(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise RuntimeError(f"schema_samples_must_be_on_D:{resolved}")
    return resolved


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "AlphaFactory-DTCC-Schema/1.0"})
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temp_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        with zipfile.ZipFile(temp_path) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"zip_crc_error:{bad}")
        temp_path.replace(destination)
    finally:
        temp_path.unlink(missing_ok=True)


def head_metadata(url: str) -> dict[str, str | int | None]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AlphaFactory-DTCC-Schema/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return {
            "http_status": int(getattr(response, "status", 200)),
            "content_length": int(response.headers.get("Content-Length", "0")),
            "storage_class": response.headers.get("x-amz-storage-class"),
            "restore": response.headers.get("x-amz-restore"),
            "last_modified": response.headers.get("Last-Modified"),
            "etag": response.headers.get("ETag"),
        }


def normalized(row: dict[str, str], *names: str) -> str:
    lowered = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lowered.get(name.lower())
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def inspect_zip(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != 1:
            raise RuntimeError(f"unexpected_members:{path}:{members}")
        with archive.open(members[0]) as binary:
            reader = csv.DictReader(io.TextIOWrapper(binary, encoding="utf-8-sig", errors="replace", newline=""))
            headers = list(reader.fieldnames or [])
            product_names: Counter[str] = Counter()
            option_types: Counter[str] = Counter()
            call_currencies: Counter[str] = Counter()
            put_currencies: Counter[str] = Counter()
            rows = 0
            option_like_rows = 0
            examples: list[dict[str, str]] = []
            for row in reader:
                rows += 1
                product = normalized(row, "Product name", "Product Name")
                option_type = normalized(row, "Option Type", "Option type")
                call_currency = normalized(row, "Call currency-Leg 1", "Call Currency", "Call currency")
                put_currency = normalized(row, "Put currency-Leg 1", "Put Currency", "Put currency")
                if product:
                    product_names[product] += 1
                if option_type:
                    option_types[option_type] += 1
                if call_currency:
                    call_currencies[call_currency] += 1
                if put_currency:
                    put_currencies[put_currency] += 1
                if option_type or call_currency or put_currency or "option" in product.lower():
                    option_like_rows += 1
                    if len(examples) < 5:
                        examples.append(
                            {
                                "product_name": product,
                                "option_type": option_type,
                                "call_currency": call_currency,
                                "put_currency": put_currency,
                                "notional_leg_1": normalized(row, "Notional amount-Leg 1", "Notional Amount 1", "Notional Amount"),
                                "execution_timestamp": normalized(row, "Execution Timestamp", "Execution Time Stamp"),
                                "dissemination_timestamp": normalized(row, "Dissemination Timestamp"),
                                "strike_price": normalized(row, "Strike Price"),
                                "action_type": normalized(row, "Action type", "Action Type"),
                                "event_type": normalized(row, "Event type", "Event Type"),
                            }
                        )
    return {
        "member": members[0],
        "rows": rows,
        "headers": headers,
        "header_count": len(headers),
        "option_like_rows": option_like_rows,
        "top_product_names": product_names.most_common(20),
        "option_types": option_types.most_common(20),
        "call_currencies": call_currencies.most_common(20),
        "put_currencies": put_currencies.most_common(20),
        "examples": examples,
    }


def main() -> int:
    root = ensure_d(ROOT)
    root.mkdir(parents=True, exist_ok=True)
    records = []
    for sample_date, url in SAMPLES.items():
        path = root / Path(url).name
        metadata = head_metadata(url)
        archived = metadata["storage_class"] in {"GLACIER", "DEEP_ARCHIVE"} and not metadata["restore"]
        if archived:
            records.append(
                {
                    "sample_date": sample_date,
                    "url": url,
                    "availability": "OBJECT_EXISTS_BUT_ARCHIVED_GET_UNAVAILABLE",
                    "downloaded": False,
                    "head_metadata": metadata,
                    "path": None,
                    "bytes": None,
                    "sha256": None,
                    "schema": None,
                }
            )
            continue
        if not path.is_file():
            download(url, path)
        records.append(
            {
                "sample_date": sample_date,
                "url": url,
                "availability": "PUBLIC_GET_AVAILABLE",
                "downloaded": True,
                "head_metadata": metadata,
                "path": path.relative_to(WORKSPACE).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "schema": inspect_zip(path),
            }
        )
    result = {
        "schema_version": "alphafactory_dtcc_fx_sdr_schema_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "purpose": "source_schema_feasibility_only_no_price_outcomes",
        "official_dashboard": "https://pddata.dtcc.com/ppd/cftcdashboard",
        "official_user_guide": "https://kgc0418-tdw-data-0.s3.amazonaws.com/gtr/static/gtr/docs/RT_PPD_quick_ref_guide.pdf",
        "mt5_initialized": False,
        "price_bars_loaded": 0,
        "performance_metrics_produced": False,
        "historical_window_verdict": "FAIL_7_YEAR_ACCESS_OBJECTS_BEFORE_2024_07_ARE_DEEP_ARCHIVE_WITHOUT_RESTORE",
        "records": records,
    }
    output = root.parent / "schema_probe.json"
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "records": len(records), "available": sum(1 for row in records if row["downloaded"]), "archived": sum(1 for row in records if not row["downloaded"]), "option_like_rows": {row["sample_date"]: row["schema"]["option_like_rows"] for row in records if row["schema"] is not None}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
