#!/usr/bin/env python3
"""Prepare a compact Sonic R case list for MT5-native chart screenshots."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


OUTPUT_COLUMNS = [
    "case_id",
    "symbol",
    "timeframe",
    "event_time",
    "direction",
    "entry_price",
    "stop_loss",
    "target_price",
    "entry_reason",
    "realized_r",
    "pnl_net",
    "session_bucket",
    "h1_bias",
    "h4_bias",
    "dragon_slope_atr",
    "trend_slope_atr",
    "pvsra_bias",
    "pvsra_event",
    "pvsra_grade",
    "level_zone",
    "level_distance_pips",
    "sample_reason",
    "source_case_id",
    "note",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="AlphaFactory run directory.")
    parser.add_argument(
        "--casebook-dir",
        type=Path,
        help="Defaults to <run>/analysis/entry_asof_casebook.",
    )
    parser.add_argument("--sample-reason", default="top_loss", help="Comma-separated case sample reasons.")
    parser.add_argument("--max-cases", type=int, default=5)
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Defaults to the terminal MQL5/Files/SonicR_CaseSnapshot folder inferred from cwd.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        help="Defaults to <run>/analysis/native_mt5_casebook for traceable run artifacts.",
    )
    parser.add_argument("--out-name", default="cases.csv")
    return parser.parse_args()


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def infer_mql5_files() -> Path:
    cwd = Path.cwd().resolve()
    parts = [p.name.lower() for p in [cwd, *cwd.parents]]
    if "mql5" in parts:
        index = parts.index("mql5")
        mql5_dir = [cwd, *cwd.parents][index]
        return mql5_dir / "Files" / "SonicR_CaseSnapshot"
    return cwd / "SonicR_CaseSnapshot"


def safe_id(value: str, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", value or "").strip("_")
    if not text:
        text = fallback
    return text[:48]


def selected_cases(rows: Sequence[Dict[str, str]], sample_reasons: Iterable[str], max_cases: int) -> List[Dict[str, str]]:
    reasons = {reason.strip() for reason in sample_reasons if reason.strip()}
    selected = [row for row in rows if row.get("sample_reason", "") in reasons]
    if not selected:
        selected = list(rows)
    return selected[: max(0, max_cases)]


def output_row(row: Dict[str, str], index: int) -> Dict[str, str]:
    source_case_id = row.get("case_id", "")
    case_id = safe_id(source_case_id, f"case_{index:03d}")
    note = (
        f"{row.get('mode', '')} {row.get('direction', '')} "
        f"R={row.get('realized_r', '')} PnL={row.get('pnl_net', '')}"
    ).strip()
    return {
        "case_id": case_id,
        "symbol": row.get("symbol", "XAUUSD"),
        "timeframe": row.get("timeframe", "PERIOD_M5"),
        "event_time": row.get("entry_server_ts", ""),
        "direction": row.get("direction", ""),
        "entry_price": row.get("entry_price", ""),
        "stop_loss": row.get("stop_loss", ""),
        "target_price": row.get("target_price", ""),
        "entry_reason": row.get("entry_reason", ""),
        "realized_r": row.get("realized_r", ""),
        "pnl_net": row.get("pnl_net", ""),
        "session_bucket": row.get("session_bucket", ""),
        "h1_bias": row.get("h1_bias", ""),
        "h4_bias": row.get("h4_bias", ""),
        "dragon_slope_atr": row.get("dragon_slope_atr", ""),
        "trend_slope_atr": row.get("trend_slope_atr", ""),
        "pvsra_bias": row.get("pvsra_bias", ""),
        "pvsra_event": row.get("pvsra_event", ""),
        "pvsra_grade": row.get("pvsra_grade", ""),
        "level_zone": row.get("level_zone", ""),
        "level_distance_pips": row.get("level_distance_pips", ""),
        "sample_reason": row.get("sample_reason", ""),
        "source_case_id": source_case_id,
        "note": note,
    }


def write_csv(path: Path, rows: Sequence[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_readme(path: Path, payload: Dict[str, Any]) -> None:
    text = [
        "# Sonic R MT5 Snapshot Cases",
        "",
        f"- Run: `{payload['run_id']}`",
        f"- Cases CSV: `{payload['cases_csv']}`",
        f"- Run artifact CSV: `{payload.get('artifact_cases_csv', '')}`",
        f"- Selected cases: `{payload['selected_cases']}`",
        "",
        "## MT5 Steps",
        "",
        "1. Compile and run `SonicR_CaseSnapshot.mq5` from MT5 Scripts.",
        "2. Keep `InpCasesFile=SonicR_CaseSnapshot\\cases.csv`.",
        "3. The script opens the chart, adds Dragon/Trend EMAs, draws entry/SL/TP/context, and writes PNG files into `MQL5\\Files`.",
        "4. Use the generated `shots.csv` to map PNG files back to case ids.",
        "",
        "This is for visual audit only. It does not promote a strategy candidate.",
        "",
    ]
    path.write_text("\n".join(text), encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    casebook_dir = (args.casebook_dir or (run_dir / "analysis" / "entry_asof_casebook")).resolve()
    cases_path = casebook_dir / "cases.csv"
    if not cases_path.exists():
        raise FileNotFoundError(cases_path)

    rows = read_csv(cases_path)
    picked = selected_cases(rows, args.sample_reason.split(","), args.max_cases)
    output_rows = [output_row(row, index + 1) for index, row in enumerate(picked)]

    out_dir = (args.out_dir or infer_mql5_files()).resolve()
    artifact_dir = (args.artifact_dir or (run_dir / "analysis" / "native_mt5_casebook")).resolve()
    out_csv = out_dir / args.out_name
    artifact_csv = artifact_dir / args.out_name
    write_csv(out_csv, output_rows)
    write_csv(artifact_csv, output_rows)

    manifest = {
        "schema_version": "sonic_mt5_snapshot_cases.v1",
        "run_id": run_dir.name,
        "source_cases_csv": str(cases_path),
        "cases_csv": str(out_csv),
        "artifact_cases_csv": str(artifact_csv),
        "mt5_files_dir": str(out_dir),
        "artifact_dir": str(artifact_dir),
        "selected_cases": len(output_rows),
        "sample_reason": args.sample_reason,
        "max_cases": args.max_cases,
        "role": "MT5-native screenshot request list; visual audit only.",
        "visual_scope": "post-entry MT5 chart audit; not no-future entry-as-of proof.",
        "capture_status": "REQUEST_PREPARED",
        "expected_shots_csv": str(out_dir / "shots.csv"),
        "expected_png_location": str(out_dir.parent),
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_cases_sha256": sha256_file(cases_path),
        "staged_cases_sha256": sha256_file(out_csv),
        "artifact_cases_sha256": sha256_file(artifact_csv),
    }
    write_json(out_dir / "manifest.json", manifest)
    write_readme(out_dir / "README.md", manifest)
    write_json(artifact_dir / "manifest.json", manifest)
    write_readme(artifact_dir / "README.md", manifest)

    print(
        json.dumps(
            {
                "status": "ok",
                "cases": len(output_rows),
                "out_csv": str(out_csv),
                "artifact_csv": str(artifact_csv),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
