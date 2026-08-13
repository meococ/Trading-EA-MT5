"""Build a hash-verified MT5 custom-rate import plan for MTS005 Jetta H1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
from datetime import date, datetime, timezone
from pathlib import Path


AFRATE_HEADER = struct.Struct("<QQ")
AFRATE_RECORD = struct.Struct("<qddddqiq")
AFRATE_MAGIC = 0x4146524154453100
AUTHORITY = "SOURCE_DATA_ONLY_NO_PERFORMANCE"
CONTRACT_SCHEMA = "alphafactory_dukascopy_jetta_h1_source_contract.v1"
RECEIPT_SCHEMA = "alphafactory_dukascopy_jetta_h1_month.v1"


class RateImportPlanError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest().upper()


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RateImportPlanError(f"JSON root must be an object: {path}")
    return payload


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with partial.open("wb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())
    partial.replace(path)


def ensure_link_or_copy(source: Path, target: Path, expected_sha: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not target.is_file() or sha256_file(target) != expected_sha:
            raise RateImportPlanError(f"existing target mismatch: {target}")
        return
    try:
        os.link(source, target)
    except OSError:
        partial = target.with_name(target.name + ".partial")
        with source.open("rb") as src, partial.open("wb") as dst:
            for block in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        partial.replace(target)
    if sha256_file(target) != expected_sha:
        raise RateImportPlanError(f"created target hash mismatch: {target}")


def month_iter(from_day: date, to_exclusive: date):
    current = date(from_day.year, from_day.month, 1)
    while current < to_exclusive:
        yield current.year, current.month
        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )


def inspect_rates(path: Path, expected_count: int, point: float) -> tuple[int, int]:
    expected_size = AFRATE_HEADER.size + expected_count * AFRATE_RECORD.size
    if path.stat().st_size != expected_size:
        raise RateImportPlanError(f"AFRATE1 size mismatch: {path}")
    first = 0
    previous = 0
    with path.open("rb") as source:
        magic, count = AFRATE_HEADER.unpack(source.read(AFRATE_HEADER.size))
        if magic != AFRATE_MAGIC or count != expected_count:
            raise RateImportPlanError(f"AFRATE1 header mismatch: {path}")
        for index in range(expected_count):
            row = AFRATE_RECORD.unpack(source.read(AFRATE_RECORD.size))
            epoch, open_, high, low, close, tick_volume, spread, real_volume = row
            if (
                epoch <= previous
                or epoch % 3600 != 0
                or open_ <= 0.0
                or high + point / 1000.0 < max(open_, close)
                or low - point / 1000.0 > min(open_, close)
                or tick_volume < 1
                or spread < 1
                or real_volume < 0
            ):
                raise RateImportPlanError(f"invalid AFRATE1 row {index}: {path}")
            if index == 0:
                first = epoch
            previous = epoch
        if source.read(1):
            raise RateImportPlanError(f"AFRATE1 trailing data: {path}")
    return first, previous


def resolve_custom_symbol(contract_symbol: str, override: str | None) -> str:
    selected = override or contract_symbol
    if not re.fullmatch(
        r"(?:AFD_[A-Z0-9]+_DUKA_TSMOM_V[0-9]+|[A-Z0-9]{6}_AFD_TSMOM_V[0-9]+)",
        selected,
    ):
        raise RateImportPlanError(f"invalid custom symbol identity: {selected}")
    return selected


def build(args: argparse.Namespace) -> int:
    contract_path = args.contract.resolve()
    actual_contract_sha = sha256_file(contract_path)
    if actual_contract_sha != args.contract_sha256.upper():
        raise RateImportPlanError("source contract SHA256 mismatch")
    contract = load_json(contract_path)
    if (
        contract.get("schema_version") != CONTRACT_SCHEMA
        or contract.get("authority") != AUTHORITY
        or contract.get("economics_authorized") is not False
    ):
        raise RateImportPlanError("source contract authority mismatch")
    rows = contract.get("symbols")
    if not isinstance(rows, list):
        raise RateImportPlanError("source contract symbols missing")
    selected = [
        row
        for row in rows
        if isinstance(row, dict) and row.get("source_symbol") == args.symbol.upper()
    ]
    if len(selected) != 1:
        raise RateImportPlanError(f"expected one symbol row for {args.symbol}")
    row = selected[0]
    symbol = str(row["source_symbol"])
    custom_symbol = resolve_custom_symbol(str(row["custom_symbol"]), args.custom_symbol)
    origin_symbol = str(row["origin_symbol"])
    digits = int(row["digits"])
    point = 10.0 ** (-digits)
    from_day = date.fromisoformat(str(row["history_from"]))
    to_exclusive = date.fromisoformat(str(row["history_to_exclusive"]))
    data_root = args.data_root.resolve()
    terminal_root = args.terminal_data_root.resolve()
    files_root = terminal_root / "MQL5" / "Files" / "AlphaFactoryCustomRateImport"
    import_id = f"HYP-MTS005-{symbol}"

    month_rows: list[dict[str, object]] = []
    total_h1 = 0
    first_epoch = 0
    last_epoch = 0
    for year, month in month_iter(from_day, to_exclusive):
        receipt_path = data_root / "receipts" / symbol / f"{year:04d}" / f"{month:02d}.json"
        binary_path = data_root / "decoded" / symbol / f"{year:04d}" / f"{month:02d}.afrates"
        if not receipt_path.is_file() or not binary_path.is_file():
            raise RateImportPlanError(f"missing frozen source month: {symbol} {year}-{month:02d}")
        receipt = load_json(receipt_path)
        binary = receipt.get("binary")
        binding = receipt.get("source_contract")
        if not isinstance(binary, dict) or not isinstance(binding, dict):
            raise RateImportPlanError(f"invalid source receipt: {receipt_path}")
        expected_sha = str(binary.get("sha256", ""))
        count = int(binary.get("count", -1))
        if (
            receipt.get("schema_version") != RECEIPT_SCHEMA
            or receipt.get("authority") != AUTHORITY
            or receipt.get("status") != "PASS"
            or receipt.get("symbol") != symbol
            or binding.get("sha256") != actual_contract_sha
            or sha256_file(binary_path) != expected_sha
        ):
            raise RateImportPlanError(f"source receipt binding mismatch: {receipt_path}")
        observed_first, observed_last = inspect_rates(binary_path, count, point)
        if (
            observed_first != int(binary.get("first_epoch", -1))
            or observed_last != int(binary.get("last_epoch", -1))
        ):
            raise RateImportPlanError(f"source boundary mismatch: {receipt_path}")
        target = files_root / import_id / f"{year:04d}-{month:02d}.afrates"
        ensure_link_or_copy(binary_path, target, expected_sha)
        month_rows.append(
            {
                "year_month": f"{year:04d}-{month:02d}",
                "sha256": expected_sha,
                "count": count,
                "first_epoch": observed_first,
                "last_epoch": observed_last,
                "relative_path": (
                    f"AlphaFactoryCustomRateImport\\{import_id}\\{year:04d}-{month:02d}.afrates"
                ),
            }
        )
        total_h1 += count
        if first_epoch == 0:
            first_epoch = observed_first
        last_epoch = observed_last

    if not month_rows or total_h1 < 1:
        raise RateImportPlanError("source range has no H1 bars")
    manifest = {
        "schema_version": "alphafactory_dukascopy_jetta_h1_range_manifest.v1",
        "authority": AUTHORITY,
        "economics_authorized": False,
        "hypothesis_id": "HYP-MULTI-TSMOM-D1-005",
        "source_contract_sha256": actual_contract_sha,
        "symbol": symbol,
        "custom_symbol": custom_symbol,
        "month_count": len(month_rows),
        "h1_bar_count": total_h1,
        "synthetic_m1_control_bar_count": total_h1 * 4,
        "first_h1_epoch": first_epoch,
        "last_h1_epoch": last_epoch,
        "months": month_rows,
    }
    manifest_path = data_root / "manifests" / f"{symbol}.range_manifest.v1.json"
    atomic_write(
        manifest_path,
        (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
    )
    manifest_sha = sha256_file(manifest_path)
    plan_identity = {
        "schema_version": "alphafactory_custom_rate_import_plan_identity.v1",
        "source_contract_sha256": actual_contract_sha,
        "range_manifest_sha256": manifest_sha,
        "custom_symbol": custom_symbol,
        "origin_symbol": origin_symbol,
        "month_count": len(month_rows),
        "rate_mode": "REUSE_VERIFY" if args.reuse_existing_rates else "REPLACE",
    }
    plan_sha = sha256_json(plan_identity)
    range_from = int(datetime(from_day.year, from_day.month, from_day.day, tzinfo=timezone.utc).timestamp())
    range_to = int(datetime(to_exclusive.year, to_exclusive.month, to_exclusive.day, tzinfo=timezone.utc).timestamp()) - 1
    lines = [
        ";".join(
            [
                "META",
                "alphafactory_custom_rate_import_plan.v1",
                custom_symbol,
                origin_symbol,
                str(digits),
                f"{point:.{digits}f}",
                actual_contract_sha,
                manifest_sha,
                plan_sha,
                str(len(month_rows)),
                str(range_from),
                str(range_to),
                str(total_h1),
                str(total_h1 * 4),
                str(first_epoch),
                str(last_epoch),
                "REUSE_VERIFY" if args.reuse_existing_rates else "REPLACE",
            ]
        )
    ]
    for item in month_rows:
        lines.append(
            ";".join(
                [
                    "MONTH",
                    str(item["year_month"]),
                    str(item["relative_path"]),
                    str(item["sha256"]),
                    str(item["count"]),
                    str(item["first_epoch"]),
                    str(item["last_epoch"]),
                ]
            )
        )
    lines.append("END")
    active_plan = files_root / "active_plan.csv"
    atomic_write(active_plan, ("\n".join(lines) + "\n").encode("ascii"))
    print(
        json.dumps(
            {
                "status": "PASS_SOURCE_ONLY",
                "symbol": symbol,
                "custom_symbol": custom_symbol,
                "active_plan": active_plan.as_posix(),
                "active_plan_sha256": sha256_file(active_plan),
                "plan_identity_sha256": plan_sha,
                "range_manifest": manifest_path.as_posix(),
                "range_manifest_sha256": manifest_sha,
                "month_count": len(month_rows),
                "h1_bar_count": total_h1,
                "synthetic_m1_control_bar_count": total_h1 * 4,
                "rate_mode": "REUSE_VERIFY" if args.reuse_existing_rates else "REPLACE",
                "economics_authorized": False,
            },
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build MTS005 MT5 custom-rate import plan")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--terminal-data-root", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--custom-symbol")
    parser.add_argument("--reuse-existing-rates", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return build(build_parser().parse_args(argv))
    except RateImportPlanError as exc:
        print(f"FATAL {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
