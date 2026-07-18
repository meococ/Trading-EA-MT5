#!/usr/bin/env python3
"""Profile CME SDR FX option schema and density without joining price outcomes."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


SCHEMA_VERSION = "cme_sdr_fx_options_profile.v1"
MAJOR_CURRENCIES = {"USD", "EUR", "GBP", "JPY"}
PAIR_RE = re.compile(r"\b(USD|EUR|GBP|JPY)[/ _-]?(USD|EUR|GBP|JPY)\b", re.IGNORECASE)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_pair(first: str, second: str) -> str | None:
    left = (first or "").strip().upper()
    right = (second or "").strip().upper()
    if left == right or left not in MAJOR_CURRENCIES or right not in MAJOR_CURRENCIES:
        return None
    return left + right


def pair_from_modern(row: dict[str, str]) -> str | None:
    for field in ("exchangeRateBasis", "productName", "fisn", "upiUnderlierName"):
        value = row.get(field, "") or ""
        match = PAIR_RE.search(value)
        if match:
            return canonical_pair(match.group(1), match.group(2))
    call_currencies = [
        row.get("leg1CallCurrency", ""),
        row.get("leg2CallCurrency", ""),
    ]
    put_currencies = [
        row.get("leg1PutCurrency", ""),
        row.get("leg2PutCurrency", ""),
    ]
    populated = [value for value in call_currencies + put_currencies if value]
    unique = list(dict.fromkeys(value.strip().upper() for value in populated))
    if len(unique) == 2:
        return canonical_pair(unique[0], unique[1])
    return None


def iter_zip_rows(path: Path) -> tuple[str, list[str], Iterable[dict[str, str]]]:
    archive = zipfile.ZipFile(path)
    names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
    if len(names) != 1:
        archive.close()
        raise ValueError(f"expected one CSV in {path.name}, found {len(names)}")
    raw = archive.read(names[0])
    archive.close()
    text = io.StringIO(raw.decode("utf-8-sig"), newline="")
    reader = csv.DictReader(text)
    columns = list(reader.fieldnames or [])
    schema = "legacy" if "Contract Type" in columns else "cftc_standardized"
    return schema, columns, list(reader)


def profile_file(path: Path, trade_date: str) -> dict:
    schema, columns, rows = iter_zip_rows(path)
    option_rows = 0
    new_option_rows = 0
    major_new_option_rows = 0
    pairs: Counter[str] = Counter()
    for row in rows:
        if schema == "legacy":
            is_option = "OPTION" in (row.get("Contract Type", "") or "").upper() or bool(
                (row.get("Option Type", "") or "").strip()
            )
            is_new = (row.get("Event", "") or "").strip().upper() == "NEW TRADE"
            pair = canonical_pair(row.get("Currency 1", ""), row.get("Currency 2", ""))
        else:
            is_option = "OPTION" in (row.get("instrumentType", "") or "").upper() or bool(
                (row.get("optionType", "") or "").strip()
            )
            action = (row.get("action", "") or "").strip().upper()
            event = (row.get("event", "") or "").strip().upper()
            is_new = action in {"NEWT", "NEW"} and event in {"", "TRAD"}
            pair = pair_from_modern(row)
        if not is_option:
            continue
        option_rows += 1
        if not is_new:
            continue
        new_option_rows += 1
        if pair:
            major_new_option_rows += 1
            pairs[pair] += 1
    has_timestamp = (
        "Dissemination Time" in columns
        if schema == "legacy"
        else "disseminationTimestamp" in columns
    )
    has_option_type = "Option Type" in columns if schema == "legacy" else "optionType" in columns
    has_buyer_seller_aggressor = any(
        name.lower() in {"buyer", "seller", "side", "aggressor", "buy_sell"} for name in columns
    )
    return {
        "trade_date": trade_date,
        "path": path.as_posix(),
        "schema": schema,
        "row_count": len(rows),
        "option_rows": option_rows,
        "new_option_rows": new_option_rows,
        "major_new_option_rows": major_new_option_rows,
        "major_pairs": dict(sorted(pairs.items())),
        "has_dissemination_timestamp": has_timestamp,
        "has_option_type": has_option_type,
        "has_buyer_seller_aggressor": has_buyer_seller_aggressor,
    }


def split_summary(files: list[dict]) -> dict:
    pair_days: set[tuple[str, str]] = set()
    active_dates: set[str] = set()
    pairs: Counter[str] = Counter()
    for item in files:
        for pair, count in item["major_pairs"].items():
            if count > 0:
                pair_days.add((item["trade_date"], pair))
                active_dates.add(item["trade_date"])
                pairs[pair] += count
    sampled_day_count = len(files)
    sampled_week_equivalent = sampled_day_count / 5.0 if sampled_day_count else 0.0
    pair_days_per_week = len(pair_days) / sampled_week_equivalent if sampled_week_equivalent else 0.0
    active_days_per_week = len(active_dates) / sampled_week_equivalent if sampled_week_equivalent else 0.0
    return {
        "sampled_day_count": sampled_day_count,
        "sampled_week_equivalent": sampled_week_equivalent,
        "days_with_major_new_option": len(active_dates),
        "unique_major_pair_days": len(pair_days),
        "major_new_option_rows": sum(item["major_new_option_rows"] for item in files),
        "estimated_pair_days_per_week": pair_days_per_week,
        "estimated_one_trade_max_per_day_per_week": active_days_per_week,
        "major_pair_rows": dict(sorted(pairs.items())),
        "raw_pair_days_2_to_5": 2.0 <= pair_days_per_week <= 5.0,
        "cadence_2_to_5_pass": 2.0 <= active_days_per_week <= 5.0,
    }


def build_profile(root: Path) -> dict:
    manifest_path = root / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results: list[dict] = []
    mismatches: list[str] = []
    for record in manifest["files"]:
        path = root / record["path"]
        digest = sha256_file(path)
        if digest != record["sha256"]:
            mismatches.append(record["path"])
            continue
        item = profile_file(path, record["trade_date"])
        item["path"] = record["path"]
        results.append(item)
    grouped: dict[int, list[dict]] = defaultdict(list)
    for item in results:
        grouped[int(item["trade_date"][:4])].append(item)
    by_year = {
        str(year): {
            "files": len(items),
            "rows": sum(item["row_count"] for item in items),
            "option_rows": sum(item["option_rows"] for item in items),
            "new_option_rows": sum(item["new_option_rows"] for item in items),
            "major_new_option_rows": sum(item["major_new_option_rows"] for item in items),
            "days_with_major_new_option": sum(item["major_new_option_rows"] > 0 for item in items),
        }
        for year, items in sorted(grouped.items())
    }
    train = [item for item in results if int(item["trade_date"][:4]) <= 2021]
    validation = [item for item in results if 2022 <= int(item["trade_date"][:4]) <= 2023]
    train_summary = split_summary(train)
    validation_summary = split_summary(validation)
    schema_contract_pass = bool(results) and all(
        item["has_dissemination_timestamp"] and item["has_option_type"] for item in results
    )
    aggressor_present = any(item["has_buyer_seller_aggressor"] for item in results)
    validation_continuity_pass = all(
        by_year.get(str(year), {}).get("days_with_major_new_option", 0) > 0
        for year in (2022, 2023)
    )
    density_pass = train_summary["cadence_2_to_5_pass"] and validation_summary[
        "cadence_2_to_5_pass"
    ] and validation_continuity_pass
    if mismatches:
        status = "FAIL_HASH_MISMATCH"
    elif not schema_contract_pass:
        status = "FAIL_SCHEMA_CONTRACT"
    elif not validation_continuity_pass:
        status = "FAIL_TEMPORAL_CONTINUITY"
    elif not density_pass:
        status = "FAIL_CADENCE"
    else:
        status = "PASS_ACTIVITY_BREAKOUT_FEASIBILITY"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status,
        "root": str(root),
        "source_manifest": {
            "path": "source_manifest.json",
            "sha256": sha256_file(manifest_path),
            "expected_files": manifest["file_count"],
            "profiled_files": len(results),
            "hash_mismatches": mismatches,
        },
        "scope": {
            "price_outcomes_accessed": 0,
            "holdout_2024_2025_files_accessed": 0,
            "signed_demand_thesis_authorized": False,
            "buyer_seller_aggressor_present": aggressor_present,
            "allowed_thesis_if_density_passes": "prior-day unsigned major-FX option activity conditions a next-session price-defined breakout",
        },
        "by_year": by_year,
        "train_2017_2021": train_summary,
        "internal_validation_2022_2023": validation_summary,
        "schema_contract_pass": schema_contract_pass,
        "validation_continuity_pass": validation_continuity_pass,
        "density_pass": density_pass,
        "research_authorized": False,
        "reason": "A feasibility pass would still require registry and frozen preregistration before any price-outcome join.",
        "files": results,
    }


def write_json_atomic(path: Path, payload: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    alpha_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=alpha_root / "external" / "cme_sdr_fx")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / "schema_density_profile.json"
    payload = build_profile(root)
    write_json_atomic(output, payload)
    print(
        "CME_SDR_FX_PROFILE "
        f"status={payload['status']} "
        f"train_tpw={payload['train_2017_2021']['estimated_one_trade_max_per_day_per_week']:.3f} "
        f"validation_tpw={payload['internal_validation_2022_2023']['estimated_one_trade_max_per_day_per_week']:.3f}"
    )
    print(f"output={output}")
    return 0 if payload["status"] == "PASS_ACTIVITY_BREAKOUT_FEASIBILITY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
