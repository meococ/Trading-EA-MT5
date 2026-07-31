#!/usr/bin/env python3
"""Fail closed unless both HYP-004 random-100 chart layers are complete."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


POINT_SIZE = 0.00001
MAX_MEDIAN_DISTANCE_POINTS = 5.0
MAX_P90_DISTANCE_POINTS = 10.0
MAX_SINGLE_DISTANCE_POINTS = 20.0

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_case_time_alignment(
    sample_rows: list[dict[str, str]], bars_path: Path
) -> tuple[dict[str, float | int], list[str]]:
    bars = pd.read_parquet(bars_path, columns=["time_utc", "low", "high"])
    bars["time_utc"] = pd.to_datetime(bars["time_utc"])
    bars = bars.drop_duplicates("time_utc", keep=False).set_index("time_utc")
    distances: list[float] = []
    errors: list[str] = []
    missing = 0
    for row in sample_rows:
        for event, time_field, price_field in (
            ("entry", "entry_time_utc", "entry"),
            ("exit", "exit_time_utc", "exit"),
        ):
            event_time = pd.Timestamp(row[time_field]).floor("min")
            if event_time not in bars.index:
                missing += 1
                errors.append(
                    f"time alignment:{row['case_id']}:{event}: missing UTC M1 bar"
                )
                continue
            bar = bars.loc[event_time]
            price = float(row[price_field])
            low = float(bar["low"])
            high = float(bar["high"])
            distance = max(low - price, price - high, 0.0) / POINT_SIZE
            distances.append(distance)

    if distances:
        series = pd.Series(distances, dtype="float64")
        stats: dict[str, float | int] = {
            "events_expected": len(sample_rows) * 2,
            "events_matched": len(distances),
            "events_missing": missing,
            "median_distance_points": round(float(series.median()), 6),
            "p90_distance_points": round(float(series.quantile(0.90)), 6),
            "max_distance_points": round(float(series.max()), 6),
        }
    else:
        stats = {
            "events_expected": len(sample_rows) * 2,
            "events_matched": 0,
            "events_missing": missing,
            "median_distance_points": float("inf"),
            "p90_distance_points": float("inf"),
            "max_distance_points": float("inf"),
        }

    if (
        stats["events_matched"] != stats["events_expected"]
        or float(stats["median_distance_points"]) > MAX_MEDIAN_DISTANCE_POINTS
        or float(stats["p90_distance_points"]) > MAX_P90_DISTANCE_POINTS
        or float(stats["max_distance_points"]) > MAX_SINGLE_DISTANCE_POINTS
    ):
        errors.append(
            "clock/price alignment failed: "
            f"matched={stats['events_matched']}/{stats['events_expected']} "
            f"median={stats['median_distance_points']}pt "
            f"p90={stats['p90_distance_points']}pt "
            f"max={stats['max_distance_points']}pt"
        )
    return stats, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--random-root",
        type=Path,
        help="Optional corrected-casebook root; defaults to random100_forensics.",
    )
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[3]
    root = (
        args.random_root.resolve()
        if args.random_root is not None
        else (
            workspace
            / "03. EA Developer"
            / "EA_SweepCascadeContinuation"
            / "research"
            / "evidence"
            / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
            / "random100_forensics"
        )
    )
    cases_path = root / "random100_cases.csv"
    sample_manifest = root / "random100_sample_manifest.json"
    decision_path = root / "decision_asof" / "cases_manifest.json"
    anatomy_path = root / "anatomy" / "cases_manifest.json"
    output_path = root / "random100_casebook_qc.json"
    bars_path = (
        workspace
        / "02. AlphaFactory"
        / "data"
        / "fivepercent"
        / "EURUSD"
        / "EURUSD_M1_2015_now.parquet"
    )

    with cases_path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample_rows = list(csv.DictReader(handle))
    expected_ids = [row["case_id"] for row in sample_rows]
    if len(expected_ids) != 100 or len(set(expected_ids)) != 100:
        raise SystemExit("Sample must contain exactly 100 unique case IDs")

    manifests = {
        "decision_asof": json.loads(decision_path.read_text(encoding="utf-8-sig")),
        "anatomy": json.loads(anatomy_path.read_text(encoding="utf-8-sig")),
    }
    errors: list[str] = []
    time_alignment, alignment_errors = validate_case_time_alignment(
        sample_rows, bars_path
    )
    errors.extend(alignment_errors)
    layer_receipts: dict[str, object] = {}
    for layer, manifest in manifests.items():
        expected_mode = "asof" if layer == "decision_asof" else "anatomy"
        if manifest.get("schema_version") != "chart_case_render.v2":
            errors.append(f"{layer}: bad schema")
        if manifest.get("mode") != expected_mode:
            errors.append(f"{layer}: bad mode")
        if manifest.get("time_col") != "time_utc":
            errors.append(f"{layer}: time_col must be time_utc")
        if str(manifest.get("bars_sha256", "")).upper() != sha256(bars_path):
            errors.append(f"{layer}: bars hash mismatch")
        if str(manifest.get("cases_sha256", "")).upper() != sha256(cases_path):
            errors.append(f"{layer}: cases hash mismatch")
        results = manifest.get("results")
        if not isinstance(results, list) or len(results) != 100:
            errors.append(f"{layer}: expected 100 results")
            results = results if isinstance(results, list) else []
        result_ids = [str(row.get("case_id")) for row in results]
        if result_ids != expected_ids:
            errors.append(f"{layer}: case IDs/order do not match frozen sample")

        png_dir = decision_path.parent if layer == "decision_asof" else anatomy_path.parent
        pngs = sorted(png_dir.glob("*.png"))
        if len(pngs) != 100:
            errors.append(f"{layer}: expected exactly 100 PNGs, got {len(pngs)}")
        total_bytes = 0
        for row in results:
            case_id = str(row.get("case_id"))
            if row.get("status") != "RENDERED":
                errors.append(f"{layer}:{case_id}: not rendered")
                continue
            png = png_dir / str(row.get("png", ""))
            if not png.is_file():
                errors.append(f"{layer}:{case_id}: missing PNG")
                continue
            total_bytes += png.stat().st_size
            if sha256(png) != str(row.get("sha256", "")).upper():
                errors.append(f"{layer}:{case_id}: PNG hash mismatch")
            context = row.get("context") or {}
            if context.get("timeframe") != "H1":
                errors.append(f"{layer}:{case_id}: H1 context missing")
            if context.get("entry_position") != "center":
                errors.append(f"{layer}:{case_id}: entry is not centered")
            if context.get("decision_state_cutoff_enforced") is not True:
                errors.append(f"{layer}:{case_id}: decision cutoff missing")
            if layer == "decision_asof":
                for key in ("outcome_hidden", "net_r_hidden", "label_hidden_in_image"):
                    if row.get(key) is not True:
                        errors.append(f"{layer}:{case_id}: {key} must be true")
                if context.get("future_region_hidden") is not True:
                    errors.append(f"{layer}:{case_id}: future region is visible")
                if context.get("post_entry_bars_drawn") != 0:
                    errors.append(f"{layer}:{case_id}: post-entry bars are visible")
            else:
                for key in (
                    "entry_marker_rendered",
                    "sl_line_rendered",
                    "tp_line_rendered",
                    "exit_marker_rendered",
                ):
                    if row.get(key) is not True:
                        errors.append(f"{layer}:{case_id}: {key} must be true")
                if context.get("post_entry_outcome_region") is not True:
                    errors.append(f"{layer}:{case_id}: outcome region missing")
                if not isinstance(context.get("post_entry_bars_drawn"), int) or context.get(
                    "post_entry_bars_drawn"
                ) <= 0:
                    errors.append(f"{layer}:{case_id}: post-entry H1 bars missing")
        layer_receipts[layer] = {
            "manifest_path": manifest_path.relative_to(workspace).as_posix()
            if (manifest_path := decision_path if layer == "decision_asof" else anatomy_path)
            else "",
            "manifest_sha256": sha256(manifest_path),
            "results": len(results),
            "pngs": len(pngs),
            "total_png_bytes": total_bytes,
        }

    if errors:
        for error in errors[:50]:
            print(f"SCC_RANDOM100_CASEBOOK_ERROR {error}")
        raise SystemExit(1)

    receipt = {
        "schema_version": "scc_random100_casebook_qc.v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_id": "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004",
        "run_id": "20260725_210811",
        "status": "PASS",
        "cases": 100,
        "image_layers": 2,
        "total_pngs": 200,
        "time_alignment": {
            "time_col": "time_utc",
            "bars_path": bars_path.relative_to(workspace).as_posix(),
            "bars_sha256": sha256(bars_path),
            **time_alignment,
        },
        "sample_manifest": {
            "path": sample_manifest.relative_to(workspace).as_posix(),
            "sha256": sha256(sample_manifest),
        },
        "layers": layer_receipts,
        "case_ids_in_frozen_order": expected_ids,
        "errors": [],
    }
    output_path.write_text(
        json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        "SCC_RANDOM100_CASEBOOK_OK "
        f"cases=100 pngs=200 receipt_sha256={sha256(output_path)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
