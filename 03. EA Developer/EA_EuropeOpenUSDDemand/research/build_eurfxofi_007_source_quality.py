#!/usr/bin/env python3
"""Validate HYP006 TBBO source and materialize outcome-blind HYP007 features.

The `extract` command requires a final, registry-authorized HYP006 manifest and
the Databento Python runtime. The `render` command consumes only the resulting
Parquet/JSON and can run in a Plotly/Kaleido-capable Python runtime. Neither
command reads EURUSD targets or trading outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-007"
PARENT_ID = "HYP-EURFXOFI-EURUSD-M1-006"
PLAN_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
    "HYP-EURFXOFI-EURUSD-M1-007_SOURCE_QUALITY_PLAN.md"
)
TOOL_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
    "build_eurfxofi_007_source_quality.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
LEDGER_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-002/"
    "EURFXOFI002-SIGNAL-DATE-SELECTION-001/signal_dates.jsonl"
)
SOURCE_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-006/EURFXOFI006-TBBO-SOURCE-001"
)
OUTPUT_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-007/EURFXOFI007-SOURCE-QUALITY-001"
)
LEDGER_SHA256 = "EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
PLAN_SHA256 = "9B0DA2A7BFB6679E882E2D136E0956FB7CE8DB19E528DE8ABFF52C18576D90F7"
EXPECTED_SPLITS = {"TRAIN": 630, "VALIDATION": 526, "HOLDOUT": 203}
EXPECTED_DATES = 1359
TICK_SIZE = 0.00005
FINAL_PARENT_STATUS = "DOWNLOADED_RAW_SOURCE_QUALITY_REQUIRED"
FEATURE_NAME = "source_features.parquet"
SUMMARY_NAME = "source_quality_summary.json"
ARTIFACT_MANIFEST_NAME = "artifact_manifest.json"
READOUT_NAME = "HYP-EURFXOFI-EURUSD-M1-007_SOURCE_QUALITY_READOUT.md"
CHART_NAMES = (
    "01_coverage_by_year.png",
    "02_quality_distributions.png",
    "03_signed_flow_by_year_split.png",
    "04_within_window_trajectory.png",
    "05_missingness_calendar.png",
)


class SourceQualityError(RuntimeError):
    """Fail-closed source-quality error."""


@dataclass(frozen=True)
class WindowSpec:
    request_id: str
    local_date: str
    split: str
    start: str
    end: str
    filename: str | None
    source_empty: bool
    expected_bytes: int
    expected_sha256: str | None
    expected_records: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def workspace() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise SourceQualityError(f"{label} must stay on D:, got {resolved}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temp, path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceQualityError(f"cannot read valid JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SourceQualityError(f"expected JSON object in {path}")
    return payload


def latest_registry_row(path: Path, hypothesis_id: str) -> dict[str, Any]:
    latest: dict[str, Any] | None = None
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SourceQualityError(f"invalid registry JSON line {line_number}: {exc}") from exc
        if row.get("hypothesis_id") == hypothesis_id:
            latest = row
    if latest is None:
        raise SourceQualityError(f"registry has no row for {hypothesis_id}")
    return latest


def verify_authority(root: Path, manifest_path: Path) -> dict[str, Any]:
    plan_path = root / PLAN_REL
    tool_path = root / TOOL_REL
    ledger_path = root / LEDGER_REL
    checks = (
        (plan_path, PLAN_SHA256, "HYP007 plan"),
        (ledger_path, LEDGER_SHA256, "HYP002 date ledger"),
    )
    for path, expected, label in checks:
        if not path.is_file():
            raise SourceQualityError(f"missing {label}: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise SourceQualityError(f"{label} SHA mismatch: expected {expected}, got {actual}")

    registry = root / REGISTRY_REL
    row = latest_registry_row(registry, HYPOTHESIS_ID)
    validation = row.get("validation", {})
    if row.get("state") != "probe":
        raise SourceQualityError(f"latest HYP007 state must be probe, got {row.get('state')!r}")
    if validation.get("source_quality_run_authorized") is not True:
        raise SourceQualityError("HYP007 source-quality run is not authorized")
    if validation.get("outcome_prices_authorized") is not False:
        raise SourceQualityError("HYP007 must keep outcome prices explicitly closed")
    if validation.get("economics_authorized") is not False:
        raise SourceQualityError("HYP007 must keep economics explicitly closed")
    if validation.get("source_quality_plan_sha256") != PLAN_SHA256:
        raise SourceQualityError("registry HYP007 plan hash mismatch")
    tool_hash = sha256_file(tool_path)
    if validation.get("source_quality_tool_sha256") != tool_hash:
        raise SourceQualityError("registry HYP007 tool hash mismatch")
    manifest_hash = sha256_file(manifest_path)
    if validation.get("parent_manifest_sha256") != manifest_hash:
        raise SourceQualityError("registry HYP007 parent manifest hash mismatch")

    parent = latest_registry_row(registry, PARENT_ID)
    parent_validation = parent.get("validation", {})
    if parent.get("state") != "parked":
        raise SourceQualityError("HYP006 must be parked before HYP007 source run")
    if parent_validation.get("final_manifest_sha256") != manifest_hash:
        raise SourceQualityError("HYP006 terminal row does not bind final manifest")
    return {"row": row, "parent": parent, "manifest_sha256": manifest_hash}


def load_ledger(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    split_counts = {key: 0 for key in EXPECTED_SPLITS}
    dates: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        request_id = str(raw.get("request_id", ""))
        local_date = str(raw.get("local_date", ""))
        split = str(raw.get("split", ""))
        if not request_id or not local_date or split not in EXPECTED_SPLITS:
            raise SourceQualityError(f"invalid ledger identity at line {line_number}")
        if request_id in rows or local_date in dates:
            raise SourceQualityError(f"duplicate ledger request/date at line {line_number}")
        rows[request_id] = {
            "request_id": request_id,
            "local_date": local_date,
            "split": split,
        }
        dates.add(local_date)
        split_counts[split] += 1
    if len(rows) != EXPECTED_DATES or split_counts != EXPECTED_SPLITS:
        raise SourceQualityError(
            f"ledger population mismatch: rows={len(rows)} splits={split_counts}"
        )
    return rows


def reconcile_manifest(
    manifest: dict[str, Any], ledger: dict[str, dict[str, str]], source_root: Path
) -> list[WindowSpec]:
    if manifest.get("status") != FINAL_PARENT_STATUS:
        raise SourceQualityError(
            f"parent manifest not terminal: expected {FINAL_PARENT_STATUS}, "
            f"got {manifest.get('status')!r}"
        )
    if manifest.get("in_flight") not in (None, {}):
        raise SourceQualityError("parent manifest still has an in-flight request")
    if manifest.get("outcome_fields_used") is not False:
        raise SourceQualityError("parent manifest outcome_fields_used must be false")

    specs: list[WindowSpec] = []
    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for item in manifest.get("downloads", []):
        request_id = str(item.get("request_id", ""))
        filename = str(item.get("filename", ""))
        if request_id not in ledger or request_id in seen_ids:
            raise SourceQualityError(f"unknown/duplicate completed request {request_id!r}")
        if not filename or filename in seen_files:
            raise SourceQualityError(f"missing/duplicate filename for {request_id}")
        if str(item.get("local_date")) != ledger[request_id]["local_date"]:
            raise SourceQualityError(f"date mismatch for {request_id}")
        if str(item.get("split")) != ledger[request_id]["split"]:
            raise SourceQualityError(f"split mismatch for {request_id}")
        if item.get("source_empty") is not False:
            raise SourceQualityError(f"completed file unexpectedly source-empty: {request_id}")
        specs.append(
            WindowSpec(
                request_id=request_id,
                local_date=ledger[request_id]["local_date"],
                split=ledger[request_id]["split"],
                start=str(item.get("start")),
                end=str(item.get("end")),
                filename=filename,
                source_empty=False,
                expected_bytes=int(item.get("bytes", -1)),
                expected_sha256=str(item.get("sha256", "")),
                expected_records=int(item.get("records", -1)),
            )
        )
        seen_ids.add(request_id)
        seen_files.add(filename)

    for item in manifest.get("source_empty_windows", []):
        request_id = str(item.get("request_id", ""))
        if request_id not in ledger or request_id in seen_ids:
            raise SourceQualityError(f"unknown/duplicate empty request {request_id!r}")
        specs.append(
            WindowSpec(
                request_id=request_id,
                local_date=ledger[request_id]["local_date"],
                split=ledger[request_id]["split"],
                start=str(item.get("start")),
                end=str(item.get("end")),
                filename=None,
                source_empty=True,
                expected_bytes=0,
                expected_sha256=None,
                expected_records=0,
            )
        )
        seen_ids.add(request_id)

    if seen_ids != set(ledger):
        missing = sorted(set(ledger) - seen_ids)
        raise SourceQualityError(f"manifest does not cover exact ledger; missing={missing[:5]}")
    actual_files = {path.name for path in source_root.glob("*.dbn.zst")}
    if actual_files != seen_files:
        raise SourceQualityError(
            f"DBN file set mismatch: missing={sorted(seen_files-actual_files)[:5]} "
            f"extra={sorted(actual_files-seen_files)[:5]}"
        )
    return sorted(specs, key=lambda value: value.local_date)


def empty_feature_row(spec: WindowSpec) -> dict[str, Any]:
    row: dict[str, Any] = {
        "request_id": spec.request_id,
        "local_date": spec.local_date,
        "split": spec.split,
        "start_utc": spec.start,
        "end_utc": spec.end,
        "filename": None,
        "source_empty": True,
        "records": 0,
        "first_event_utc": None,
        "last_event_utc": None,
        "coverage_span_seconds": None,
        "terminal_silence_seconds": None,
        "buy_trade_count": 0,
        "sell_trade_count": 0,
        "unclassified_trade_count": 0,
        "buy_volume": 0.0,
        "sell_volume": 0.0,
        "unclassified_volume": 0.0,
        "classified_volume": 0.0,
        "total_volume": 0.0,
        "classified_volume_share": None,
        "flow_signed": None,
        "flow_imbalance": None,
        "first_trade_price": None,
        "last_trade_price": None,
        "trade_price_move_ticks": None,
        "vwap_trade_price": None,
        "median_spread_ticks": None,
        "p95_spread_ticks": None,
        "locked_records": 0,
        "crossed_records": 0,
        "median_book_size_imbalance": None,
        "flow_acceleration": None,
        "late_flow_share": None,
    }
    for bin_number in (1, 2, 3):
        row.update(
            {
                f"bin{bin_number}_trade_count": 0,
                f"bin{bin_number}_buy_volume": 0.0,
                f"bin{bin_number}_sell_volume": 0.0,
                f"bin{bin_number}_unclassified_volume": 0.0,
                f"bin{bin_number}_classified_volume": 0.0,
                f"bin{bin_number}_flow_signed": None,
                f"bin{bin_number}_flow_imbalance": None,
            }
        )
    return row


def _side_labels(series: Any) -> Any:
    return series.astype(str).str.upper().str.strip().replace(
        {"BID": "B", "ASK": "A", "NONE": "N", "NAN": "N", "": "N"}
    )


def aggregate_window_frame(frame: Any, spec: WindowSpec) -> dict[str, Any]:
    """Aggregate one normalized TBBO DataFrame without any target data."""
    import numpy as np
    import pandas as pd

    if spec.source_empty:
        if len(frame) != 0:
            raise SourceQualityError(f"source-empty {spec.request_id} has records")
        return empty_feature_row(spec)
    if len(frame) != spec.expected_records:
        raise SourceQualityError(
            f"record count mismatch {spec.request_id}: expected {spec.expected_records}, got {len(frame)}"
        )

    data = frame.reset_index()
    required = {
        "ts_event",
        "side",
        "price",
        "size",
        "bid_px_00",
        "ask_px_00",
        "bid_sz_00",
        "ask_sz_00",
    }
    missing = required - set(data.columns)
    if missing:
        raise SourceQualityError(f"{spec.request_id} missing TBBO fields {sorted(missing)}")
    if "action" in data.columns and not _side_labels(data["action"]).isin({"T", "TRADE"}).all():
        raise SourceQualityError(f"{spec.request_id} contains non-trade TBBO action")

    data["ts_event"] = pd.to_datetime(data["ts_event"], utc=True)
    start = pd.Timestamp(spec.start)
    end = pd.Timestamp(spec.end)
    if ((data["ts_event"] < start) | (data["ts_event"] >= end)).any():
        raise SourceQualityError(f"{spec.request_id} has event outside frozen window")
    data = data.sort_values(["ts_event"], kind="stable").reset_index(drop=True)
    sides = _side_labels(data["side"])
    if not sides.isin({"A", "B", "N"}).all():
        bad = sorted(set(sides[~sides.isin({"A", "B", "N"})]))
        raise SourceQualityError(f"{spec.request_id} has unsupported side values {bad}")

    for name in ("price", "size", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    if data[["price", "size"]].isna().any().any() or (data["size"] < 0).any():
        raise SourceQualityError(f"{spec.request_id} has invalid trade price/size")
    valid_book = data[["bid_px_00", "ask_px_00"]].notna().all(axis=1)
    crossed = valid_book & (data["bid_px_00"] > data["ask_px_00"])
    if crossed.any():
        raise SourceQualityError(f"{spec.request_id} contains crossed book records")
    locked = valid_book & (data["bid_px_00"] == data["ask_px_00"])

    sizes = data["size"].astype(float)
    signed = np.where(sides.eq("B"), sizes, np.where(sides.eq("A"), -sizes, 0.0))
    data["signed_volume"] = signed
    elapsed = (data["ts_event"] - start).dt.total_seconds()
    data["bin"] = np.minimum((elapsed // 5).astype(int) + 1, 3)

    buy_mask = sides.eq("B")
    sell_mask = sides.eq("A")
    unknown_mask = sides.eq("N")
    buy_volume = float(sizes[buy_mask].sum())
    sell_volume = float(sizes[sell_mask].sum())
    unknown_volume = float(sizes[unknown_mask].sum())
    classified_volume = buy_volume + sell_volume
    total_volume = classified_volume + unknown_volume
    flow_signed = buy_volume - sell_volume
    flow_imbalance = flow_signed / classified_volume if classified_volume > 0 else math.nan
    spread_ticks = (data.loc[valid_book, "ask_px_00"] - data.loc[valid_book, "bid_px_00"]) / TICK_SIZE
    size_denominator = data["bid_sz_00"] + data["ask_sz_00"]
    size_valid = data[["bid_sz_00", "ask_sz_00"]].notna().all(axis=1) & (size_denominator > 0)
    book_imbalance = (
        (data.loc[size_valid, "bid_sz_00"] - data.loc[size_valid, "ask_sz_00"])
        / size_denominator.loc[size_valid]
    )
    first_event = data["ts_event"].iloc[0]
    last_event = data["ts_event"].iloc[-1]
    price_weights = sizes.where(sizes > 0, 0.0)
    weight_sum = float(price_weights.sum())

    row = {
        "request_id": spec.request_id,
        "local_date": spec.local_date,
        "split": spec.split,
        "start_utc": spec.start,
        "end_utc": spec.end,
        "filename": spec.filename,
        "source_empty": False,
        "records": int(len(data)),
        "first_event_utc": first_event.isoformat(),
        "last_event_utc": last_event.isoformat(),
        "coverage_span_seconds": float((last_event - first_event).total_seconds()),
        "terminal_silence_seconds": float((end - last_event).total_seconds()),
        "buy_trade_count": int(buy_mask.sum()),
        "sell_trade_count": int(sell_mask.sum()),
        "unclassified_trade_count": int(unknown_mask.sum()),
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "unclassified_volume": unknown_volume,
        "classified_volume": classified_volume,
        "total_volume": total_volume,
        "classified_volume_share": classified_volume / total_volume if total_volume > 0 else math.nan,
        "flow_signed": flow_signed,
        "flow_imbalance": flow_imbalance,
        "first_trade_price": float(data["price"].iloc[0]),
        "last_trade_price": float(data["price"].iloc[-1]),
        "trade_price_move_ticks": float((data["price"].iloc[-1] - data["price"].iloc[0]) / TICK_SIZE),
        "vwap_trade_price": float((data["price"] * price_weights).sum() / weight_sum) if weight_sum > 0 else math.nan,
        "median_spread_ticks": float(spread_ticks.median()) if len(spread_ticks) else math.nan,
        "p95_spread_ticks": float(spread_ticks.quantile(0.95)) if len(spread_ticks) else math.nan,
        "locked_records": int(locked.sum()),
        "crossed_records": 0,
        "median_book_size_imbalance": float(book_imbalance.median()) if len(book_imbalance) else math.nan,
    }
    for bin_number in (1, 2, 3):
        mask = data["bin"].eq(bin_number)
        bin_sides = sides[mask]
        bin_sizes = sizes[mask]
        bin_buy = float(bin_sizes[bin_sides.eq("B")].sum())
        bin_sell = float(bin_sizes[bin_sides.eq("A")].sum())
        bin_unknown = float(bin_sizes[bin_sides.eq("N")].sum())
        bin_classified = bin_buy + bin_sell
        row.update(
            {
                f"bin{bin_number}_trade_count": int(mask.sum()),
                f"bin{bin_number}_buy_volume": bin_buy,
                f"bin{bin_number}_sell_volume": bin_sell,
                f"bin{bin_number}_unclassified_volume": bin_unknown,
                f"bin{bin_number}_classified_volume": bin_classified,
                f"bin{bin_number}_flow_signed": bin_buy - bin_sell,
                f"bin{bin_number}_flow_imbalance": (bin_buy - bin_sell) / bin_classified
                if bin_classified > 0
                else math.nan,
            }
        )
    row["flow_acceleration"] = (
        row["bin3_flow_imbalance"] - row["bin1_flow_imbalance"]
        if not math.isnan(row["bin3_flow_imbalance"]) and not math.isnan(row["bin1_flow_imbalance"])
        else math.nan
    )
    row["late_flow_share"] = (
        row["bin3_classified_volume"] / classified_volume if classified_volume > 0 else math.nan
    )
    return row


def validate_and_decode_file(path: Path, spec: WindowSpec) -> dict[str, Any]:
    if path.stat().st_size != spec.expected_bytes:
        raise SourceQualityError(f"byte-size mismatch for {spec.request_id}")
    actual_hash = sha256_file(path)
    if actual_hash != spec.expected_sha256:
        raise SourceQualityError(f"SHA256 mismatch for {spec.request_id}")
    try:
        import databento as db

        frame = db.DBNStore.from_file(path).to_df(
            price_type="float", pretty_ts=True, map_symbols=False, schema="tbbo"
        )
    except Exception as exc:
        raise SourceQualityError(f"DBN decode failed for {spec.request_id}: {exc}") from exc
    return aggregate_window_frame(frame, spec)


def source_summary(rows: Any, manifest: dict[str, Any], manifest_hash: str) -> dict[str, Any]:
    import pandas as pd

    populated = rows.loc[~rows["source_empty"]]
    split_counts = {str(k): int(v) for k, v in rows.groupby("split").size().to_dict().items()}
    selected_by_year = {
        str(k): int(v) for k, v in rows.groupby(rows["local_date"].str[:4]).size().to_dict().items()
    }
    total_volume = float(populated["total_volume"].sum())
    classified_volume = float(populated["classified_volume"].sum())
    usable = populated["classified_volume"].gt(0)
    summary = {
        "schema_version": "eurfxofi007_source_quality.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": utc_now(),
        "outcome_fields_used": False,
        "economics_executed": False,
        "parent_manifest_sha256": manifest_hash,
        "live_estimated_total_usd": float(manifest.get("live_estimated_total_usd", math.nan)),
        "selected_windows": int(len(rows)),
        "populated_windows": int(len(populated)),
        "source_empty_windows": int(rows["source_empty"].sum()),
        "split_counts": split_counts,
        "selected_by_year": selected_by_year,
        "decoded_records": int(populated["records"].sum()),
        "downloaded_compressed_bytes": int(sum(int(x.get("bytes", 0)) for x in manifest.get("downloads", []))),
        "total_aggressive_volume": total_volume,
        "classified_aggressive_volume": classified_volume,
        "classified_volume_ratio": classified_volume / total_volume if total_volume > 0 else math.nan,
        "usable_nonempty_windows": int(usable.sum()),
        "usable_nonempty_window_ratio": float(usable.mean()) if len(usable) else math.nan,
        "unclassified_trade_records": int(populated["unclassified_trade_count"].sum()),
        "locked_book_records": int(populated["locked_records"].sum()),
        "crossed_book_records": int(populated["crossed_records"].sum()),
        "median_records_per_populated_window": float(populated["records"].median()),
        "median_volume_per_populated_window": float(populated["total_volume"].median()),
        "median_spread_ticks": float(populated["median_spread_ticks"].median()),
    }
    gates = {
        "exact_population": len(rows) == EXPECTED_DATES,
        "exact_splits": split_counts == EXPECTED_SPLITS,
        "no_crossed_books": summary["crossed_book_records"] == 0,
        "classified_window_ratio_ge_0_99": summary["usable_nonempty_window_ratio"] >= 0.99,
        "classified_volume_ratio_ge_0_95": summary["classified_volume_ratio"] >= 0.95,
        "owner_ceiling_respected": summary["live_estimated_total_usd"] <= 2.25,
    }
    summary["gates"] = gates
    summary["verdict"] = "PASS_SOURCE_QUALITY" if all(gates.values()) else "FAIL_SOURCE_QUALITY_INVALID"
    return summary


def extract() -> Path:
    import pandas as pd

    root = workspace()
    source_root = require_d(root / SOURCE_REL, "source root")
    output_root = require_d(root / OUTPUT_REL, "output root")
    manifest_path = source_root / "download_manifest.json"
    authority = verify_authority(root, manifest_path)
    manifest = load_json(manifest_path)
    ledger = load_ledger(root / LEDGER_REL)
    specs = reconcile_manifest(manifest, ledger, source_root)
    output_root.mkdir(parents=True, exist_ok=True)
    if any(output_root.iterdir()):
        raise SourceQualityError(f"output root must be empty for one-shot extract: {output_root}")

    rows: list[dict[str, Any]] = []
    for index, spec in enumerate(specs, 1):
        if spec.source_empty:
            rows.append(empty_feature_row(spec))
        else:
            assert spec.filename is not None
            rows.append(validate_and_decode_file(source_root / spec.filename, spec))
        if index % 100 == 0:
            print(f"SOURCE_QUALITY_PROGRESS {index}/{len(specs)}", flush=True)
    frame = pd.DataFrame(rows).sort_values("local_date").reset_index(drop=True)
    summary = source_summary(frame, manifest, authority["manifest_sha256"])

    features_path = output_root / FEATURE_NAME
    temp_features = features_path.with_suffix(".parquet.tmp")
    frame.to_parquet(temp_features, index=False)
    os.replace(temp_features, features_path)
    write_json_atomic(output_root / SUMMARY_NAME, summary)
    print(
        f"SOURCE_QUALITY_EXTRACT_{summary['verdict']} rows={len(frame)} "
        f"records={summary['decoded_records']} output={output_root}"
    )
    return output_root


def _write_plot(fig: Any, path: Path) -> None:
    fig.update_layout(
        template="plotly_white",
        font={"family": "Arial", "size": 12},
        margin={"l": 60, "r": 30, "t": 85, "b": 55},
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    fig.write_image(str(path), width=1500, height=850, scale=1.25)


def render() -> Path:
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    root = workspace()
    output_root = require_d(root / OUTPUT_REL, "output root")
    features_path = output_root / FEATURE_NAME
    summary_path = output_root / SUMMARY_NAME
    if not features_path.is_file() or not summary_path.is_file():
        raise SourceQualityError("extract artifacts are missing")
    frame = pd.read_parquet(features_path)
    summary = load_json(summary_path)
    if len(frame) != EXPECTED_DATES or summary.get("outcome_fields_used") is not False:
        raise SourceQualityError("render input contract mismatch")
    frame["year"] = frame["local_date"].str[:4]
    frame["month"] = frame["local_date"].str[:7]
    populated = frame.loc[~frame["source_empty"]].copy()

    yearly = frame.groupby("year").agg(selected=("request_id", "size"), populated=("source_empty", lambda x: int((~x).sum())))
    yearly_records = populated.groupby("year").agg(records=("records", "sum"), volume=("total_volume", "sum"))
    yearly = yearly.join(yearly_records, how="left").fillna(0)
    fig = make_subplots(rows=2, cols=2, subplot_titles=("Selected vs populated windows", "Decoded records", "Aggressive volume", "Source-empty windows"))
    fig.add_trace(go.Bar(x=yearly.index, y=yearly["selected"], name="Selected"), row=1, col=1)
    fig.add_trace(go.Bar(x=yearly.index, y=yearly["populated"], name="Populated"), row=1, col=1)
    fig.add_trace(go.Bar(x=yearly.index, y=yearly["records"], name="Records"), row=1, col=2)
    fig.add_trace(go.Bar(x=yearly.index, y=yearly["volume"], name="Contracts"), row=2, col=1)
    fig.add_trace(go.Bar(x=yearly.index, y=yearly["selected"]-yearly["populated"], name="Empty"), row=2, col=2)
    fig.update_layout(title=f"HYP007 source coverage | n={len(frame):,} windows")
    _write_plot(fig, output_root / CHART_NAMES[0])

    fig = make_subplots(rows=2, cols=2, subplot_titles=("Records/window", "Volume/window", "Classified volume share", "Median spread (ticks)"))
    for column, row, col, label in (
        ("records", 1, 1, "records"),
        ("total_volume", 1, 2, "contracts"),
        ("classified_volume_share", 2, 1, "ratio"),
        ("median_spread_ticks", 2, 2, "ticks"),
    ):
        values = populated[column].dropna()
        fig.add_trace(go.Histogram(x=values, nbinsx=45, name=label), row=row, col=col)
    fig.update_layout(title=f"HYP007 source quality distributions | populated n={len(populated):,}", showlegend=False)
    _write_plot(fig, output_root / CHART_NAMES[1])

    fig = px.box(
        populated,
        x="year",
        y="flow_imbalance",
        color="split",
        points=False,
        category_orders={"split": ["TRAIN", "VALIDATION", "HOLDOUT"]},
        title=f"Signed aggressive-flow imbalance by year and sealed split | n={len(populated):,}",
    )
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    _write_plot(fig, output_root / CHART_NAMES[2])

    trajectory_rows: list[dict[str, Any]] = []
    for split, group in populated.groupby("split"):
        for bin_number in (1, 2, 3):
            trajectory_rows.append(
                {
                    "split": split,
                    "bin": f"{(bin_number-1)*5}-{bin_number*5}s",
                    "buy_volume": float(group[f"bin{bin_number}_buy_volume"].sum()),
                    "sell_volume": float(group[f"bin{bin_number}_sell_volume"].sum()),
                    "median_imbalance": float(group[f"bin{bin_number}_flow_imbalance"].median()),
                }
            )
    trajectory = pd.DataFrame(trajectory_rows)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Aggressive buy/sell volume", "Median signed imbalance"))
    for split in ("TRAIN", "VALIDATION", "HOLDOUT"):
        block = trajectory.loc[trajectory["split"].eq(split)]
        fig.add_trace(go.Bar(x=block["bin"], y=block["buy_volume"], name=f"{split} buy"), row=1, col=1)
        fig.add_trace(go.Bar(x=block["bin"], y=-block["sell_volume"], name=f"{split} sell"), row=1, col=1)
        fig.add_trace(go.Scatter(x=block["bin"], y=block["median_imbalance"], mode="lines+markers", name=f"{split} imbalance"), row=1, col=2)
    fig.add_hline(y=0, line_dash="dash", line_color="black", row=1, col=2)
    fig.update_layout(title="Frozen 3 x 5-second TBBO trajectory (source only)")
    _write_plot(fig, output_root / CHART_NAMES[3])

    calendar = frame.assign(status=np.where(frame["source_empty"], 0, 1)).pivot_table(index=frame["local_date"].str[:4], columns=frame["local_date"].str[5:7], values="status", aggfunc="mean")
    fig = go.Figure(go.Heatmap(z=calendar.values, x=calendar.columns, y=calendar.index, zmin=0, zmax=1, colorscale=[[0, "#d73027"], [1, "#1a9850"]], colorbar={"title": "usable share"}))
    fig.update_layout(title=f"Monthly source availability | selected n={len(frame):,}", xaxis_title="Month", yaxis_title="Year")
    _write_plot(fig, output_root / CHART_NAMES[4])

    readout_path = output_root / READOUT_NAME
    readout = f"""# HYP007 TBBO source-quality readout

Verdict: `{summary['verdict']}`. This is source engineering evidence only; no
EURUSD target return or economic performance was opened.

- Selected/populated/source-empty windows: {summary['selected_windows']} / {summary['populated_windows']} / {summary['source_empty_windows']}.
- Split counts: {summary['split_counts']}.
- Decoded records: {summary['decoded_records']:,}.
- Downloaded compressed bytes: {summary['downloaded_compressed_bytes']:,}.
- Live acquisition estimate: USD {summary['live_estimated_total_usd']:.12f} under the Owner USD2.25 ceiling.
- Classified aggressive-volume ratio: {summary['classified_volume_ratio']:.6%}.
- Usable populated-window ratio: {summary['usable_nonempty_window_ratio']:.6%}.
- Locked/crossed book records: {summary['locked_book_records']} / {summary['crossed_book_records']}.
- Median records, volume and spread per populated window: {summary['median_records_per_populated_window']:.2f}, {summary['median_volume_per_populated_window']:.2f}, {summary['median_spread_ticks']:.4f} ticks.

The next permitted step, only if every source gate passes, is a fresh
TRAIN-only economics preregistration. Validation and holdout returns remain
sealed.
"""
    readout_path.write_text(readout, encoding="utf-8")

    artifact_paths = [features_path, summary_path, readout_path] + [output_root / name for name in CHART_NAMES]
    artifact_manifest = {
        "schema_version": "eurfxofi007_artifact_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": utc_now(),
        "outcome_fields_used": False,
        "artifacts": [
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in artifact_paths
        ],
    }
    write_json_atomic(output_root / ARTIFACT_MANIFEST_NAME, artifact_manifest)
    print(f"SOURCE_QUALITY_RENDER_OK charts={len(CHART_NAMES)} output={output_root}")
    return output_root


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("extract", "render"))
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        output = extract() if args.command == "extract" else render()
    except SourceQualityError as exc:
        print(f"SOURCE_QUALITY_ERROR {exc}", file=sys.stderr)
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
