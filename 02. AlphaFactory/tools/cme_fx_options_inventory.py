#!/usr/bin/env python3
"""Inventory and fail-closed validate an Owner-supplied CME EUR/USD CVOL drop.

This tool never downloads market data and never writes outside the selected
workspace root. It hashes raw files, profiles plain CSV deliveries, and proves
whether the minimum EUVL component/coverage contract is present before any
research code may inspect outcomes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


SCHEMA_VERSION = "cme_fx_options_inventory.v1"
REQUIRED_CODES = ("EUVL", "EUUP", "EUDN", "EUSK", "EUAM", "EUCV")
OPTION_CHAIN_FIELDS = (
    "trade_date",
    "expiration",
    "strike",
    "option_type",
    "settlement",
    "volume",
    "open_interest",
    "implied_volatility",
)
OPTION_CHAIN_ALIASES = {
    "trade_date": {"DATE", "TRADEDATE", "ASOFDATE", "VALUATIONDATE", "OBSERVATIONDATE"},
    "expiration": {"EXPIRATION", "EXPIRATIONDATE", "EXPIRY", "CONTRACTMONTH"},
    "strike": {"STRIKE", "STRIKEPRICE"},
    "option_type": {"OPTIONTYPE", "PUTCALL", "RIGHT", "TYPE"},
    "settlement": {"SETTLE", "SETTLEMENT", "SETTLEMENTPRICE", "SETTLEPRICE"},
    "volume": {"VOLUME", "VOL"},
    "open_interest": {"OPENINTEREST", "OI", "INT"},
    "implied_volatility": {"IMPLIEDVOLATILITY", "IMPLIEDVOL", "IV", "VOLATILITY"},
}
REQUIRED_FROM = date(2020, 1, 2)  # 2020-01-01 was not a trading day.
REQUIRED_TO = date(2026, 6, 30)
ALLOWED_SUFFIXES = {
    ".csv",
    ".json",
    ".txt",
    ".dat",
    ".gz",
    ".zip",
    ".xlsx",
    ".pdf",
    ".md",
}
DOCUMENTATION_SUFFIXES = {".pdf", ".md"}
DATE_KEYS = {"DATE", "TRADEDATE", "ASOFDATE", "OBSERVATIONDATE", "VALUATIONDATE"}


def canonical_name(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_date(value: str) -> date | None:
    clean = value.strip()
    if not clean:
        return None
    for candidate in (clean[:10], clean):
        try:
            return date.fromisoformat(candidate)
        except ValueError:
            pass
    for pattern in ("%m/%d/%Y", "%Y%m%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(clean, pattern).date()
        except ValueError:
            pass
    return None


def raw_files(root: Path) -> list[Path]:
    raw = root / "raw"
    if not raw.is_dir():
        return []
    resolved_root = root.resolve()
    files: list[Path] = []
    for path in sorted(raw.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file():
            continue
        if path.is_symlink():
            raise ValueError(f"symlink raw input is forbidden: {path}")
        resolved = path.resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError(f"raw input escapes selected root: {path}") from exc
        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError(f"unsupported raw file extension: {path.name}")
        files.append(path)
    return files


def sniff_dialect(handle, sample_size: int = 65536):
    sample = handle.read(sample_size)
    handle.seek(0)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def profile_csv(path: Path, root: Path) -> dict:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        dialect = sniff_dialect(handle)
        reader = csv.DictReader(handle, dialect=dialect)
        columns = list(reader.fieldnames or [])
        normalized = {canonical_name(column): column for column in columns}
        option_columns = {
            logical: next((normalized[key] for key in aliases if key in normalized), None)
            for logical, aliases in OPTION_CHAIN_ALIASES.items()
        }
        date_column = option_columns["trade_date"] or next(
            (normalized[key] for key in DATE_KEYS if key in normalized), None
        )
        dates: list[date] = []
        row_count = 0
        for row in reader:
            row_count += 1
            if date_column:
                parsed = parse_date(row.get(date_column, "") or "")
                if parsed:
                    dates.append(parsed)
    present_codes = [code for code in REQUIRED_CODES if code in normalized]
    present_option_fields = [field for field in OPTION_CHAIN_FIELDS if option_columns[field]]
    has_chain_payload = any(field != "trade_date" for field in present_option_fields)
    if present_codes and has_chain_payload:
        dataset_role = "combined"
    elif present_codes:
        dataset_role = "cvol"
    elif has_chain_payload:
        dataset_role = "option_chain"
    else:
        dataset_role = "unknown"
    return {
        "path": path.relative_to(root).as_posix(),
        "format": "csv",
        "dataset_role": dataset_role,
        "delimiter": dialect.delimiter,
        "columns": columns,
        "present_codes": present_codes,
        "present_option_chain_fields": present_option_fields,
        "option_chain_columns": option_columns,
        "date_column": date_column,
        "row_count": row_count,
        "coverage_from": min(dates).isoformat() if dates else None,
        "coverage_to": max(dates).isoformat() if dates else None,
        "parsed_date_rows": len(dates),
    }


def build_inventory(root: Path | str) -> dict:
    selected_root = Path(root).resolve()
    files = raw_files(selected_root)
    data_files = [path for path in files if path.suffix.lower() not in DOCUMENTATION_SUFFIXES]
    entries = [
        {
            "path": path.relative_to(selected_root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "suffix": path.suffix.lower(),
            "kind": "documentation"
            if path.suffix.lower() in DOCUMENTATION_SUFFIXES
            else "raw_data",
        }
        for path in files
    ]
    profiles = [profile_csv(path, selected_root) for path in files if path.suffix.lower() == ".csv"]
    cvol_profiles = [p for p in profiles if p["dataset_role"] in {"cvol", "combined"}]
    chain_profiles = [p for p in profiles if p["dataset_role"] in {"option_chain", "combined"}]
    present = {code for profile in cvol_profiles for code in profile["present_codes"]}
    missing = [code for code in REQUIRED_CODES if code not in present]
    present_chain_fields = {
        field for profile in chain_profiles for field in profile["present_option_chain_fields"]
    }
    missing_chain_fields = [field for field in OPTION_CHAIN_FIELDS if field not in present_chain_fields]

    def coverage_for(selected: list[dict]) -> tuple[date | None, date | None, bool]:
        starts = [date.fromisoformat(p["coverage_from"]) for p in selected if p["coverage_from"]]
        ends = [date.fromisoformat(p["coverage_to"]) for p in selected if p["coverage_to"]]
        earliest = min(starts) if starts else None
        latest = max(ends) if ends else None
        passed = bool(earliest and latest and earliest <= REQUIRED_FROM and latest >= REQUIRED_TO)
        return earliest, latest, passed

    cvol_from, cvol_to, cvol_coverage_pass = coverage_for(cvol_profiles)
    chain_from, chain_to, chain_coverage_pass = coverage_for(chain_profiles)

    if not data_files:
        status = "MISSING_RAW_DATA"
    elif not profiles:
        status = "SCHEMA_REVIEW_REQUIRED"
    elif missing or missing_chain_fields:
        status = "SCHEMA_INCOMPLETE"
    elif not cvol_coverage_pass or not chain_coverage_pass:
        status = "COVERAGE_INCOMPLETE"
    else:
        status = "CONTRACT_READY"

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "dataset": {
            "name": "CME EUR/USD CVOL Daily Benchmarks plus full option chain",
            "underlying": "EUR/USD options on futures",
            "primary_code": "EUVL",
            "official_catalog": "https://datamine.new.cmegroup.com/",
            "official_methodology": "https://www.cmegroup.com/market-data/cme-group-benchmark-administration/files/cvol-methodology.pdf",
        },
        "contract": {
            "required_codes": list(REQUIRED_CODES),
            "required_option_chain_fields": list(OPTION_CHAIN_FIELDS),
            "required_from": REQUIRED_FROM.isoformat(),
            "required_to": REQUIRED_TO.isoformat(),
            "availability_rule": "Use final daily benchmark no earlier than the next EURUSD decision bar after official publication.",
            "storage_rule": "Raw and generated data remain under 02. AlphaFactory/external on D; never persist the corpus on C.",
        },
        "root": str(selected_root),
        "files": entries,
        "profiles": profiles,
        "validation": {
            "required_codes_present": not missing,
            "missing_codes": missing,
            "option_chain_schema_pass": not missing_chain_fields,
            "missing_option_chain_fields": missing_chain_fields,
            "cvol_coverage_from": cvol_from.isoformat() if cvol_from else None,
            "cvol_coverage_to": cvol_to.isoformat() if cvol_to else None,
            "cvol_coverage_pass": cvol_coverage_pass,
            "option_chain_coverage_from": chain_from.isoformat() if chain_from else None,
            "option_chain_coverage_to": chain_to.isoformat() if chain_to else None,
            "option_chain_coverage_pass": chain_coverage_pass,
            "research_authorized": False,
            "reason": "Inventory readiness is not hypothesis/prereg authorization.",
        },
    }


def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    alpha_root = Path(__file__).resolve().parents[1]
    default_root = alpha_root / "external" / "cme_fx_options_euro"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = args.manifest.resolve() if args.manifest else root / "acquisition_manifest.json"
    payload = build_inventory(root)
    write_json_atomic(manifest, payload)
    print(f"CME_FX_OPTIONS_INVENTORY status={payload['status']} files={len(payload['files'])}")
    print(f"manifest={manifest}")
    return 0 if payload["status"] == "CONTRACT_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
