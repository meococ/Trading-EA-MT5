"""Build a hash-verified MT5 custom-tick import plan from BI5 daily receipts.

The builder is deliberately outcome blind.  It validates only source identity,
daily hashes, tick boundaries and minute coverage, then hard-links immutable
``AFDTICK1`` files into one portable terminal's ``MQL5/Files`` tree.  The MT5
script performs its own exact tick readback before emitting a PASS receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


AFD_HEADER = struct.Struct("<QQ")
AFD_RECORD = struct.Struct("<qdd")
AFD_MAGIC = 0x4146445449434B31
AUTHORITY = "SOURCE_DATA_ONLY_NO_PERFORMANCE"


class ImportPlanError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with partial.open("wb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())
    partial.replace(path)


def load_json(path: Path) -> dict[str, object]:
    parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(parsed, dict):
        raise ImportPlanError(f"JSON root must be an object: {path}")
    return parsed


def inspect_binary(path: Path, expected_count: int) -> tuple[int, int, int, set[int]]:
    size = path.stat().st_size
    expected_size = AFD_HEADER.size + expected_count * AFD_RECORD.size
    if size != expected_size:
        raise ImportPlanError(f"binary size mismatch: {path}: {size}/{expected_size}")
    minutes: set[int] = set()
    first_msc = 0
    last_msc = 0
    previous = -1
    with path.open("rb") as source:
        magic, count = AFD_HEADER.unpack(source.read(AFD_HEADER.size))
        if magic != AFD_MAGIC or count != expected_count:
            raise ImportPlanError(f"binary header mismatch: {path}")
        for index in range(expected_count):
            payload = source.read(AFD_RECORD.size)
            if len(payload) != AFD_RECORD.size:
                raise ImportPlanError(f"truncated record {index}: {path}")
            time_msc, bid, ask = AFD_RECORD.unpack(payload)
            if time_msc < previous or bid <= 0.0 or ask < bid:
                raise ImportPlanError(f"invalid tick record {index}: {path}")
            previous = time_msc
            if index == 0:
                first_msc = time_msc
            last_msc = time_msc
            minutes.add(time_msc // 60_000)
        if source.read(1):
            raise ImportPlanError(f"trailing binary data: {path}")
    return expected_count, first_msc, last_msc, minutes


def ensure_hard_link(source: Path, target: Path, expected_sha256: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not target.is_file() or sha256_file(target) != expected_sha256:
            raise ImportPlanError(f"existing import target mismatch: {target}")
        return
    try:
        os.link(source, target)
    except OSError:
        # Different volumes cannot hard-link; a byte copy remains deterministic.
        partial = target.with_name(target.name + ".partial")
        with source.open("rb") as src, partial.open("wb") as dst:
            for block in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(block)
            dst.flush()
            os.fsync(dst.fileno())
        partial.replace(target)
    if sha256_file(target) != expected_sha256:
        raise ImportPlanError(f"created import target hash mismatch: {target}")


def build(args: argparse.Namespace) -> int:
    contract_path = args.contract.resolve()
    contract_sha = sha256_file(contract_path)
    if contract_sha != args.contract_sha256.upper():
        raise ImportPlanError(
            f"contract SHA256 mismatch: {contract_sha}/{args.contract_sha256.upper()}"
        )
    contract = load_json(contract_path)
    if (
        contract.get("schema_version") != "alphafactory_dukascopy_source_contract.v2"
        or contract.get("authority") != AUTHORITY
        or contract.get("economics_authorized") is not False
    ):
        raise ImportPlanError("source contract authority mismatch")
    rows = contract.get("symbols")
    if not isinstance(rows, list):
        raise ImportPlanError("source contract symbols missing")
    selected = [row for row in rows if isinstance(row, dict) and row.get("source_symbol") == args.symbol]
    if len(selected) != 1:
        raise ImportPlanError(f"expected exactly one contract row for {args.symbol}")
    row = selected[0]
    source_symbol = str(row["source_symbol"])
    custom_symbol = str(row["custom_symbol"])
    origin_symbol = str(row["origin_symbol"])
    digits = int(row["digits"])
    point = 10.0 ** (-digits)
    from_day = date.fromisoformat(str(row["history_from"]))
    to_exclusive = date.fromisoformat(str(row["history_to_exclusive"]))

    data_root = args.data_root.resolve()
    terminal_root = args.terminal_data_root.resolve()
    import_id = f"HYP-MTS004-{source_symbol}"
    files_root = terminal_root / "MQL5" / "Files" / "AlphaFactoryCustomImport"
    import_root = files_root / import_id
    manifest_days: list[dict[str, object]] = []
    all_minutes: set[int] = set()

    day = from_day
    while day < to_exclusive:
        stem = Path(f"{day.year:04d}/{day.month:02d}")
        receipt_path = data_root / source_symbol / "receipts" / stem / f"{day}.json"
        binary_path = data_root / source_symbol / "decoded" / stem / f"{day}.afdticks"
        if not receipt_path.is_file() or not binary_path.is_file():
            raise ImportPlanError(f"missing frozen source day: {source_symbol} {day}")
        receipt = load_json(receipt_path)
        binary = receipt.get("binary")
        binding = receipt.get("source_contract")
        if not isinstance(binary, dict) or not isinstance(binding, dict):
            raise ImportPlanError(f"invalid receipt shape: {receipt_path}")
        expected_count = int(binary.get("count", -1))
        expected_sha = str(binary.get("sha256", ""))
        if (
            receipt.get("schema_version") != "alphafactory_dukascopy_bi5_day.v2"
            or receipt.get("authority") != AUTHORITY
            or receipt.get("status") != "PASS"
            or receipt.get("symbol") != source_symbol
            or receipt.get("date_utc") != day.isoformat()
            or binding.get("sha256") != contract_sha
            or sha256_file(binary_path) != expected_sha
        ):
            raise ImportPlanError(f"receipt binding mismatch: {receipt_path}")
        count, first_msc, last_msc, minutes = inspect_binary(binary_path, expected_count)
        if count == 0 and (int(binary.get("first_time_msc", 0)) != 0 or int(binary.get("last_time_msc", 0)) != 0):
            raise ImportPlanError(f"empty-day boundary mismatch: {receipt_path}")
        if count > 0 and (
            first_msc != int(binary.get("first_time_msc", -1))
            or last_msc != int(binary.get("last_time_msc", -1))
        ):
            raise ImportPlanError(f"binary boundary mismatch: {receipt_path}")
        target = import_root / f"{day}.afdticks"
        ensure_hard_link(binary_path, target, expected_sha)
        all_minutes.update(minutes)
        manifest_days.append(
            {
                "date_utc": day.isoformat(),
                "binary_path": binary_path.as_posix(),
                "binary_sha256": expected_sha,
                "tick_count": count,
                "first_time_msc": first_msc,
                "last_time_msc": last_msc,
                "import_relative_path": f"AlphaFactoryCustomImport\\{import_id}\\{day}.afdticks",
            }
        )
        day += timedelta(days=1)

    if not all_minutes:
        raise ImportPlanError(f"source range contains no ticks: {source_symbol}")
    range_manifest = {
        "schema_version": "alphafactory_dukascopy_range_manifest.v2",
        "authority": AUTHORITY,
        "economics_authorized": False,
        "source_contract_sha256": contract_sha,
        "symbol": source_symbol,
        "custom_symbol": custom_symbol,
        "day_count": len(manifest_days),
        "tick_count": sum(int(item["tick_count"]) for item in manifest_days),
        "m1_bar_count": len(all_minutes),
        "m1_first_epoch": min(all_minutes) * 60,
        "days": manifest_days,
    }
    manifest_path = data_root / source_symbol / "range_manifest.v2.json"
    manifest_payload = (
        json.dumps(range_manifest, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    atomic_write(manifest_path, manifest_payload)
    manifest_sha = sha256_file(manifest_path)
    plan_identity = {
        "schema_version": "alphafactory_custom_tick_import_plan_identity.v2",
        "source_contract_sha256": contract_sha,
        "range_manifest_sha256": manifest_sha,
        "custom_symbol": custom_symbol,
        "origin_symbol": origin_symbol,
        "day_count": len(manifest_days),
    }
    plan_identity_sha = sha256_json(plan_identity)
    range_from_sec = int(datetime(from_day.year, from_day.month, from_day.day, tzinfo=timezone.utc).timestamp())
    range_to_sec = int(
        datetime(to_exclusive.year, to_exclusive.month, to_exclusive.day, tzinfo=timezone.utc).timestamp()
    ) - 1
    lines = [
        ";".join(
            [
                "META",
                "alphafactory_custom_tick_import_plan.v1",
                custom_symbol,
                origin_symbol,
                str(digits),
                f"{point:.{digits}f}",
                f"{point:.{digits}f}",
                contract_sha,
                manifest_sha,
                plan_identity_sha,
                str(len(manifest_days)),
                str(range_from_sec),
                str(range_to_sec),
                str(len(all_minutes)),
                str(min(all_minutes) * 60),
            ]
        )
    ]
    for item in manifest_days:
        day_start = int(
            datetime.fromisoformat(str(item["date_utc"])).replace(tzinfo=timezone.utc).timestamp()
        )
        lines.append(
            ";".join(
                [
                    "DAY",
                    str(item["date_utc"]),
                    str(item["import_relative_path"]),
                    str(item["binary_sha256"]),
                    str(item["tick_count"]),
                    str(day_start * 1000),
                    str((day_start + 86400) * 1000 - 1),
                    str(item["first_time_msc"]),
                    str(item["last_time_msc"]),
                ]
            )
        )
    lines.append("END")
    plan_path = files_root / "active_plan.csv"
    atomic_write(plan_path, ("\n".join(lines) + "\n").encode("ascii"))
    receipt = {
        "schema_version": "alphafactory_custom_tick_plan_build.v2",
        "authority": AUTHORITY,
        "economics_authorized": False,
        "symbol": source_symbol,
        "custom_symbol": custom_symbol,
        "source_contract_sha256": contract_sha,
        "range_manifest_path": manifest_path.as_posix(),
        "range_manifest_sha256": manifest_sha,
        "plan_identity_sha256": plan_identity_sha,
        "active_plan_path": plan_path.as_posix(),
        "active_plan_sha256": sha256_file(plan_path),
        "day_count": len(manifest_days),
        "tick_count": range_manifest["tick_count"],
        "m1_bar_count": len(all_minutes),
        "m1_first_epoch": min(all_minutes) * 60,
    }
    output = args.receipt.resolve()
    atomic_write(
        output,
        (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"),
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--contract", required=True, type=Path)
    result.add_argument("--contract-sha256", required=True)
    result.add_argument("--data-root", required=True, type=Path)
    result.add_argument("--terminal-data-root", required=True, type=Path)
    result.add_argument("--symbol", required=True)
    result.add_argument("--receipt", required=True, type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return build(args)


if __name__ == "__main__":
    sys.exit(main())
