#!/usr/bin/env python3
"""Collect MT5-native Sonic R screenshot outputs into one run artifact folder."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="AlphaFactory run directory.")
    parser.add_argument(
        "--staging-dir",
        type=Path,
        help="Defaults to inferred MQL5/Files.",
    )
    parser.add_argument("--request-subdir", default="SonicR_CaseSnapshot")
    parser.add_argument("--out-dir", type=Path, help="Defaults to <run>/analysis/native_mt5_casebook.")
    parser.add_argument("--cleanup-staging", action="store_true", help="Remove copied PNGs from MQL5/Files after collection.")
    parser.add_argument("--min-image-bytes", type=int, default=20_000)
    parser.add_argument("--max-total-mb", type=float, default=25.0)
    return parser.parse_args()


def infer_mql5_files() -> Path:
    cwd = Path.cwd().resolve()
    chain = [cwd, *cwd.parents]
    for path in chain:
        if path.name.lower() == "mql5":
            return path / "Files"
    return cwd


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def fail(manifest_path: Path, manifest: Dict[str, Any], status: str, reason: str, extra: Dict[str, Any] | None = None) -> int:
    manifest["capture_status"] = status
    manifest["failure_reason"] = reason
    if extra:
        manifest.update(extra)
    write_json(manifest_path, manifest)
    payload = {"status": "failed", "capture_status": status, "reason": reason}
    if extra:
        payload.update(extra)
    print(json.dumps(payload, indent=2))
    return 2


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    staging_dir = (args.staging_dir or infer_mql5_files()).resolve()
    request_dir = staging_dir / args.request_subdir
    shots_csv = request_dir / "shots.csv"
    out_dir = (args.out_dir or (run_dir / "analysis" / "native_mt5_casebook")).resolve()
    screenshots_dir = out_dir / "screenshots"
    manifest_path = out_dir / "manifest.json"

    manifest = load_json(manifest_path)
    manifest.setdefault("schema_version", "sonic_mt5_snapshot_cases.v1")
    manifest.setdefault("run_id", run_dir.name)
    manifest["collector"] = "sonic_collect_mt5_snapshots.py"
    manifest["staging_dir"] = str(staging_dir)
    manifest["shots_csv"] = str(shots_csv)

    if not shots_csv.exists():
        manifest["capture_status"] = "PENDING_MT5_SCRIPT_RUN"
        manifest["collected_images"] = 0
        write_json(manifest_path, manifest)
        print(json.dumps({"status": "pending", "reason": "shots.csv not found", "shots_csv": str(shots_csv)}, indent=2))
        return 0

    request_cases = out_dir / "cases.csv"
    if not request_cases.exists():
        request_cases = request_dir / "cases.csv"
    if not request_cases.exists():
        return fail(manifest_path, manifest, "FAILED_MISSING_CASES", "cases.csv not found for snapshot request")

    if shots_csv.stat().st_mtime < request_cases.stat().st_mtime:
        return fail(
            manifest_path,
            manifest,
            "FAILED_STALE_SHOTS",
            "shots.csv is older than cases.csv",
            {
                "cases_csv": str(request_cases),
                "cases_mtime": request_cases.stat().st_mtime,
                "shots_mtime": shots_csv.stat().st_mtime,
            },
        )

    rows = read_csv(shots_csv)
    expected_rows = read_csv(request_cases)
    expected_case_ids = [row.get("case_id", "").strip() for row in expected_rows]
    shot_case_ids = [row.get("case_id", "").strip() for row in rows]
    manifest["expected_cases"] = len(expected_case_ids)
    manifest["shots_rows"] = len(rows)
    if shot_case_ids != expected_case_ids:
        return fail(
            manifest_path,
            manifest,
            "FAILED_CASE_MISMATCH",
            "shots.csv case ids do not match the prepared cases.csv",
            {
                "cases_csv": str(request_cases),
                "expected_case_ids": expected_case_ids,
                "shot_case_ids": shot_case_ids,
            },
        )

    copied: List[Dict[str, Any]] = []
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        png_name = row.get("png_file", "").strip()
        status = row.get("status", "")
        if not png_name or status != "OK":
            copied.append({**row, "copied": "0", "sha256": "", "bytes": "", "target_path": ""})
            continue
        source = staging_dir / png_name
        if not source.exists():
            copied.append({**row, "copied": "0", "sha256": "", "bytes": "", "target_path": "", "missing_source": str(source)})
            continue
        target = screenshots_dir / png_name
        shutil.copy2(source, target)
        copied.append(
            {
                **row,
                "copied": "1",
                "sha256": sha256_file(target),
                "bytes": target.stat().st_size,
                "target_path": str(target),
            }
        )

    sha_path = out_dir / "sha256.csv"
    columns = [
        "case_id",
        "symbol",
        "timeframe",
        "event_time",
        "direction",
        "entry_reason",
        "sample_reason",
        "realized_r",
        "pnl_net",
        "png_file",
        "status",
        "copied",
        "sha256",
        "bytes",
        "target_path",
        "missing_source",
    ]
    write_csv(sha_path, copied, columns)

    ok_shots = [row for row in rows if row.get("status", "") == "OK"]
    copied_rows = [row for row in copied if row.get("copied") == "1"]
    missing_rows = [row for row in copied if row.get("status", "") == "OK" and row.get("copied") != "1"]
    small_rows = [
        row
        for row in copied_rows
        if str(row.get("bytes", "")).isdigit() and int(row["bytes"]) < args.min_image_bytes
    ]
    total_bytes = sum(int(row.get("bytes", 0)) for row in copied_rows if str(row.get("bytes", "")).isdigit())
    max_total_bytes = int(args.max_total_mb * 1024 * 1024)

    manifest["collected_images"] = len(copied_rows)
    manifest["sha256_csv"] = str(sha_path)
    manifest["screenshots_dir"] = str(screenshots_dir)
    manifest["min_image_bytes"] = args.min_image_bytes
    manifest["max_total_mb"] = args.max_total_mb
    manifest["total_image_bytes"] = total_bytes

    if len(ok_shots) != len(rows) or len(copied_rows) != len(rows):
        write_json(manifest_path, manifest)
        return fail(
            manifest_path,
            manifest,
            "FAILED_PARTIAL_CAPTURE",
            "not every prepared case produced a copied OK screenshot",
            {"rows": len(rows), "ok_shots": len(ok_shots), "copied": len(copied_rows), "missing": len(missing_rows)},
        )
    if missing_rows:
        write_json(manifest_path, manifest)
        return fail(manifest_path, manifest, "FAILED_MISSING_IMAGES", "one or more OK screenshots were missing from staging")
    if small_rows:
        write_json(manifest_path, manifest)
        return fail(
            manifest_path,
            manifest,
            "FAILED_SMALL_IMAGES",
            "one or more screenshots are below the minimum byte gate",
            {"small_case_ids": [row.get("case_id", "") for row in small_rows]},
        )
    if total_bytes > max_total_bytes:
        write_json(manifest_path, manifest)
        return fail(
            manifest_path,
            manifest,
            "FAILED_SIZE_CAP",
            "snapshot image payload exceeds the configured byte cap",
            {"total_image_bytes": total_bytes, "max_total_bytes": max_total_bytes},
        )

    manifest["capture_status"] = "COLLECTED"
    write_json(manifest_path, manifest)

    if args.cleanup_staging:
        for row in copied_rows:
            png_name = row.get("png_file", "").strip()
            if png_name:
                (staging_dir / png_name).unlink(missing_ok=True)

    print(json.dumps({"status": "ok", "rows": len(rows), "copied": manifest["collected_images"], "sha256_csv": str(sha_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
