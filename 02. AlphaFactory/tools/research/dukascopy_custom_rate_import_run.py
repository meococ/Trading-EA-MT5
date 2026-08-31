"""Run the source-only MTS005 custom-rate importer in portable MT5."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


class ImportRunError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(path: Path, expected: str, label: str) -> str:
    if not path.is_file():
        raise ImportRunError(f"{label} not found: {path}")
    actual = sha256_file(path)
    if len(expected) != 64 or actual != expected.upper():
        raise ImportRunError(f"{label} SHA256 mismatch: expected {expected}, got {actual}")
    return actual


def parse_receipt(path: Path) -> dict[str, object]:
    rows = list(csv.reader(path.read_text(encoding="cp1252").splitlines(), delimiter=";"))
    if not rows or rows[0][:3] != [
        "RECEIPT",
        "alphafactory_custom_rate_import_receipt.v1",
        "SOURCE_DATA_ONLY_NO_PERFORMANCE",
    ]:
        raise ImportRunError("custom-rate receipt header mismatch")
    fatals = [row for row in rows if row and row[0] == "FATAL"]
    summaries = [row for row in rows if len(row) >= 3 and row[:2] == ["SUMMARY", "PASS"]]
    specs = [row for row in rows if len(row) >= 9 and row[:2] == ["SPEC", "PASS"]]
    if fatals:
        raise ImportRunError(f"custom-rate importer failed: {fatals[-1]}")
    if len(summaries) != 1:
        raise ImportRunError(f"expected one PASS summary, got {len(summaries)}")
    if len(specs) != 1:
        raise ImportRunError(f"expected one PASS trade spec, got {len(specs)}")
    months = [row for row in rows if len(row) >= 3 and row[0] == "MONTH" and row[2] == "PASS"]
    summary = summaries[0]
    spec = specs[0]
    return {
        "row_count": len(rows),
        "month_pass_count": len(months),
        "custom_symbol": summary[2],
        "imported_months": int(summary[3]),
        "imported_h1": int(summary[4]),
        "imported_m1": int(summary[5]),
        "d1_bars": int(summary[6]),
        "h1_first_epoch": int(summary[7]),
        "source_contract_sha256": summary[8],
        "range_manifest_sha256": summary[9],
        "import_plan_sha256": summary[10],
        "trade_spec": {
            "custom_symbol": spec[2],
            "origin_symbol": spec[3],
            "currency_base": spec[4],
            "currency_profit": spec[5],
            "currency_margin": spec[6],
            "trade_calc_mode": int(spec[7]),
            "contract_size": float(spec[8]),
        },
    }


def parse_plan_identity(path: Path) -> str:
    rows = list(csv.reader(path.read_text(encoding="cp1252").splitlines(), delimiter=";"))
    if not rows or len(rows[0]) < 9 or rows[0][:2] != [
        "META",
        "alphafactory_custom_rate_import_plan.v1",
    ]:
        raise ImportRunError("active plan header mismatch")
    identity = rows[0][8]
    if len(identity) != 64:
        raise ImportRunError("active plan identity SHA256 is invalid")
    return identity


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run(args: argparse.Namespace) -> int:
    terminal_root = args.terminal_data_root.resolve()
    terminal = terminal_root / "terminal64.exe"
    if not terminal.is_file():
        raise ImportRunError(f"portable terminal not found: {terminal}")
    ex5_sha = require_sha(args.importer_ex5.resolve(), args.importer_ex5_sha256, "importer EX5")
    files_root = terminal_root / "MQL5" / "Files" / "AlphaFactoryCustomRateImport"
    active_plan = files_root / "active_plan.csv"
    plan_sha = require_sha(active_plan, args.active_plan_sha256, "active plan")
    plan_identity_sha = parse_plan_identity(active_plan)
    receipt = files_root / "active_receipt.csv"
    receipt.unlink(missing_ok=True)

    scripts = terminal_root / "MQL5" / "Scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    staged_ex5 = scripts / "AlphaFactoryCustomRateImport.ex5"
    shutil.copyfile(args.importer_ex5.resolve(), staged_ex5)
    if sha256_file(staged_ex5) != ex5_sha:
        raise ImportRunError("staged importer EX5 hash mismatch")

    config = terminal_root / "config" / "alphafactory_custom_rate_import.ini"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "\n".join(
            [
                "[Charts]",
                "MaxBars=1000000",
                "",
                "[StartUp]",
                "Script=AlphaFactoryCustomRateImport",
                f"Symbol={args.startup_symbol}",
                "Period=H1",
                "",
            ]
        ),
        encoding="utf-8",
    )

    process = subprocess.Popen(f'"{terminal}" /portable /config:"{config}"')
    deadline = time.time() + args.timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            break
        time.sleep(1.0)
    if process.poll() is None:
        process.kill()
        process.wait(30)
        raise ImportRunError(f"custom-rate importer timed out after {args.timeout_seconds}s")
    if not receipt.is_file():
        raise ImportRunError(f"custom-rate receipt not produced; terminal exit={process.returncode}")
    details = parse_receipt(receipt)
    if details["import_plan_sha256"] != plan_identity_sha:
        raise ImportRunError("receipt import-plan SHA256 mismatch")
    payload: dict[str, object] = {
        "schema_version": "mts005_custom_rate_import_run.v1",
        "hypothesis_id": "HYP-MULTI-TSMOM-D1-005",
        "status": "PASS_SOURCE_IMPORT",
        "authority": "SOURCE_DATA_ONLY_NO_PERFORMANCE",
        "terminal_exit_code": process.returncode,
        "terminal_root": terminal_root.as_posix(),
        "importer_ex5_path": args.importer_ex5.resolve().as_posix(),
        "importer_ex5_sha256": ex5_sha,
        "active_plan_path": active_plan.as_posix(),
        "active_plan_sha256": plan_sha,
        "plan_identity_sha256": plan_identity_sha,
        "mt5_receipt_path": receipt.as_posix(),
        "mt5_receipt_sha256": sha256_file(receipt),
        "readback": details,
        "economics_authorized": False,
        "performance_metrics_authorized": False,
    }
    write_json_atomic(args.output.resolve(), payload)
    print(json.dumps(payload, indent=2), flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MTS005 source-only MT5 custom-rate import")
    parser.add_argument("--terminal-data-root", type=Path, required=True)
    parser.add_argument("--importer-ex5", type=Path, required=True)
    parser.add_argument("--importer-ex5-sha256", required=True)
    parser.add_argument("--active-plan-sha256", required=True)
    parser.add_argument("--startup-symbol", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return run(build_parser().parse_args(argv))
    except ImportRunError as exc:
        print(f"FATAL {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
