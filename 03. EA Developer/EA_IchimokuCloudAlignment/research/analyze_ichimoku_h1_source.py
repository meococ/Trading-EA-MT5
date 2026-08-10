#!/usr/bin/env python3
"""Outcome-blind native-H1 Ichimoku full-alignment source analyzer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


BASE_PATH = Path(__file__).resolve().with_name("analyze_ichimoku_source.py")
BASE_SPEC = importlib.util.spec_from_file_location("ichimoku_m5_formula_dependency", BASE_PATH)
assert BASE_SPEC and BASE_SPEC.loader
base = importlib.util.module_from_spec(BASE_SPEC)
BASE_SPEC.loader.exec_module(base)

HYPOTHESIS_ID = "HYP-ICH-XAUUSD-H1-001"
ATTEMPT_ID = "ICHH1001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "173C83B52F017035B27564CB019C1B775E4A955ED22B655B6B9F5B36E674F1FF"
BASE_SHA256 = "F9BAF1626EF05A623C49B16B817D405AE1C9689845E5E5E8F8E5E23F937C8114"
DATA_SHA256 = "B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"
MIN_ROWS = 25_000


def validate_selected_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(base.REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, base.REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    if ((data["time_utc"] < base.DESIGN_START) | (data["time_utc"] >= base.DESIGN_END)).any():
        raise ValueError("reader materialized rows outside the frozen design window")
    data = data.reset_index(drop=True)
    if len(data) < MIN_ROWS:
        raise ValueError(f"design rows {len(data)} below {MIN_ROWS}")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and strictly increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and strictly increasing")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    if not data["symbol"].eq("XAUUSD").all():
        raise ValueError("rows are not exclusively XAUUSD")
    if not data["timeframe"].eq("H1").all():
        raise ValueError("rows are not exclusively H1")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    return data


def analyze_frame(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    for column in ("high", "low", "close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    indicator = base.calculate_ichimoku(data)
    tenkan = indicator["tenkan"]
    kijun = indicator["kijun"]
    span_a = indicator["displayed_span_a"]
    span_b = indicator["displayed_span_b"]
    feature_valid = indicator["feature_valid"]

    raw_long = (
        feature_valid
        & (tenkan.shift(1) <= kijun.shift(1))
        & (tenkan > kijun)
        & (data["close"] > span_a)
        & (data["close"] > span_b)
        & (span_a > span_b)
    )
    raw_short = (
        feature_valid
        & (tenkan.shift(1) >= kijun.shift(1))
        & (tenkan < kijun)
        & (data["close"] < span_a)
        & (data["close"] < span_b)
        & (span_a < span_b)
    )
    conflicts = raw_long & raw_short
    raw_long &= ~conflicts
    raw_short &= ~conflicts
    raw_mask = raw_long | raw_short
    exact_next = (data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(hours=1)
    event_mask = raw_mask & exact_next

    events: list[dict[str, Any]] = []
    for index in data.index[event_mask]:
        bar_time = data.at[index, "time_utc"]
        events.append(
            {
                "hypothesis_id": HYPOTHESIS_ID,
                "source_bar_time_utc": bar_time.isoformat().replace("+00:00", "Z"),
                "decision_time_utc": (bar_time + pd.Timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
                "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
                "prior_tenkan": base.finite_float(tenkan.shift(1).loc[index]),
                "prior_kijun": base.finite_float(kijun.shift(1).loc[index]),
                "tenkan": base.finite_float(tenkan.loc[index]),
                "kijun": base.finite_float(kijun.loc[index]),
                "displayed_span_a": base.finite_float(span_a.loc[index]),
                "displayed_span_b": base.finite_float(span_b.loc[index]),
                "source_close": base.finite_float(data.at[index, "close"]),
            }
        )

    raw_count = int(raw_mask.sum())
    count = len(events)
    gap_rejected = raw_count - count
    elapsed_weeks = (base.DESIGN_END - base.DESIGN_START).total_seconds() / 604800.0
    cadence = count / elapsed_weeks
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = sum(row["direction"] == "SHORT" for row in events)
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    feature_coverage = int(feature_valid.iloc[base.WARMUP_ROWS:].sum()) / max(len(data) - base.WARMUP_ROWS, 1)
    next_coverage = count / max(raw_count, 1)
    event_years = pd.Series([pd.Timestamp(row["source_bar_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, Any]] = {}
    for year in range(2018, 2023):
        year_count = int((event_years == year).sum()) if count else 0
        weeks = base.year_weeks(year)
        yearly[str(year)] = {
            "events": year_count,
            "elapsed_weeks": weeks,
            "cadence_per_week": year_count / weeks,
            "share": year_count / count if count else 0.0,
        }
    max_year_share = max((row["share"] for row in yearly.values()), default=0.0)
    gates = {
        "minimum_design_rows": len(data) >= MIN_ROWS,
        "feature_coverage": feature_coverage >= base.MIN_FEATURE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= base.MIN_RAW_EVENT_NEXT_COVERAGE,
        "minimum_events": count >= base.MIN_EVENTS,
        "pooled_cadence": base.MIN_CADENCE <= cadence <= base.MAX_CADENCE,
        "direction_balance": long_share >= base.MIN_DIRECTION_SHARE and short_share >= base.MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= base.MAX_YEAR_SHARE,
        "each_year_cadence": all(base.MIN_YEAR_CADENCE <= row["cadence_per_week"] <= base.MAX_YEAR_CADENCE for row in yearly.values()),
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "ichimoku_native_h1_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_NATIVE_H1_ICHIMOKU_FULL_ALIGNMENT_AND_CADENCE_ONLY",
        "window": {"from": base.DESIGN_START.isoformat(), "to_exclusive": base.DESIGN_END.isoformat()},
        "parameters": {"timeframe":"H1","tenkan":9,"kijun":26,"span_b":52,"displacement":26},
        "funnel": {
            "design_rows":int(len(data)),"feature_usable_rows":int(feature_valid.sum()),"raw_events":raw_count,"executable_events":count,"gap_rejected_events":gap_rejected,"direction_conflicts":int(conflicts.sum()),"long_events":longs,"short_events":shorts
        },
        "metrics": {
            "elapsed_weeks":elapsed_weeks,"feature_coverage":feature_coverage,"raw_event_exact_next_coverage":next_coverage,"event_cadence_per_week":cadence,"long_share":long_share,"short_share":short_share,"max_year_event_share":max_year_share
        },
        "yearly":yearly,
        "gates":gates,
        "all_gates_pass":passed,
        "verdict":"SCREENED_SOURCE_PASS_NATIVE_H1_MQL5_IICHIMOKU_BUILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_NATIVE_H1_ICHIMOKU_FULL_ALIGNMENT",
        "prohibitions": {
            "post_event_ohlc_read":False,"returns_computed":False,"trades_simulated":False,"economics_executed":False,"validation_opened":False,"holdout_opened":False,"mql5_build_authorized_by_attempt":passed,"economic_build_authorized":False,"live_trading_authorized":False
        },
    }
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != base.EVENT_KEYS:
            raise ValueError(f"event-ledger keys differ from allowlist: {sorted(set(row))}")
    if report["prohibitions"]["post_event_ohlc_read"] is not False:
        raise ValueError("outcome-blind report contract failed")


def validate_manifest(manifest_path: Path, data_path: Path) -> None:
    if base.sha256_file(manifest_path) != base.MANIFEST_SHA256:
        raise ValueError("manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")]
    if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
        raise ValueError("manifest does not bind frozen H1 data")
    if not data_path.as_posix().endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"):
        raise ValueError("unexpected H1 data path")


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing registry authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "probe":row.get("state")=="probe",
        "verdict":row.get("verdict")=="FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg":row.get("prereg_sha256")==PREREG_SHA256,
        "attempt":validation.get("source_feasibility_attempt_id")==ATTEMPT_ID,
        "one_attempt":validation.get("source_feasibility_attempt_limit")==1,
        "unconsumed":metrics.get("source_feasibility_attempts_consumed")==0,
        "source_run":validation.get("source_run_authorized") is True,
        "source_only":validation.get("source_feasibility_only") is True,
        "analyzer":validation.get("reviewed_analyzer_sha256")==base.sha256_file(Path(__file__).resolve()),
        "dependency":validation.get("ichimoku_formula_dependency_sha256")==BASE_SHA256,
        "no_outcomes":validation.get("outcome_prices_authorized") is False,
        "no_economics":validation.get("economics_authorized") is False,
        "no_validation":validation.get("research_validation_access_authorized") is False,
        "no_holdout":validation.get("research_holdout_access_authorized") is False,
        "no_mt5":validation.get("mt5_authorized") is False,
        "no_mql5":validation.get("mql5_authorized") is False,
        "no_live":validation.get("live_trading_authorized") is False,
    }
    failed=[name for name,ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {"registry_sha256":base.sha256_file(registry_path),"latest_row_sha256":hashlib.sha256(raw).hexdigest().upper()}


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    marker_path=output_dir/"attempt_started.json"
    started=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    marker={"schema_version":"ichimoku_h1_attempt_started.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,"started_at_utc":started,"process_id":os.getpid(),"registry_sha256":authority["registry_sha256"],"latest_hypothesis_row_sha256":authority["latest_row_sha256"],"analyzer_sha256":base.sha256_file(Path(__file__).resolve()),"ichimoku_formula_dependency_sha256":base.sha256_file(BASE_PATH),"status":"ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"}
    try:
        with marker_path.open("xb") as handle:
            handle.write(base.json_bytes(marker)); handle.flush(); os.fsync(handle.fileno())
    except FileExistsError as exc:
        raise ValueError("attempt already claimed") from exc
    return started,marker_path


def execute(root: Path) -> dict[str, Any]:
    prereg=root/"03. EA Developer/EA_IchimokuCloudAlignment/research/HYP-ICH-XAUUSD-H1-001_FROZEN_PREREG.md"
    manifest=root/"02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path=root/"02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"
    registry=root/"04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir=root/"03. EA Developer/EA_IchimokuCloudAlignment/research/evidence/HYP-ICH-XAUUSD-H1-001/ICHH1001-SOURCE-ATTEMPT-001"
    if base.sha256_file(prereg)!=PREREG_SHA256: raise ValueError("preregistration SHA mismatch")
    if base.sha256_file(BASE_PATH)!=BASE_SHA256: raise ValueError("Ichimoku formula dependency SHA mismatch")
    authority=validate_registry_authority(registry)
    started,start_path=claim_attempt(output_dir,authority)
    validate_manifest(manifest,data_path)
    if base.sha256_file(data_path)!=DATA_SHA256: raise ValueError("H1 data SHA mismatch")
    if not set(base.REQUIRED_COLUMNS)<=set(pq.ParquetFile(data_path).schema_arrow.names): raise ValueError("Parquet schema missing required columns")
    raw=pd.read_parquet(data_path,columns=list(base.REQUIRED_COLUMNS),filters=[("time_utc",">=",base.DESIGN_START.to_pydatetime()),("time_utc","<",base.DESIGN_END.to_pydatetime())],engine="pyarrow")
    selected=validate_selected_frame(raw)
    events,report=analyze_frame(selected); assert_outcome_blind(events,report)
    replay_events,replay_report=analyze_frame(selected)
    if base.jsonl_bytes(events)!=base.jsonl_bytes(replay_events) or base.json_bytes(report)!=base.json_bytes(replay_report): raise ValueError("deterministic replay failed")
    report_bytes=base.json_bytes(report); ledger_bytes=base.jsonl_bytes(events)
    report_path=output_dir/"ich_h1_001_source_report.json"; ledger_path=output_dir/"ich_h1_001_event_ledger.jsonl"
    base.atomic_write(report_path,report_bytes); base.atomic_write(ledger_path,ledger_bytes)
    receipt={"schema_version":"ichimoku_h1_source_receipt.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,"started_at_utc":started,"completed_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"bindings":{"preregistration":{"path":prereg.relative_to(root).as_posix(),"sha256":base.sha256_file(prereg)},"manifest":{"path":manifest.relative_to(root).as_posix(),"sha256":base.sha256_file(manifest)},"data":{"path":data_path.relative_to(root).as_posix(),"sha256":base.sha256_file(data_path)},"analyzer":{"path":Path(__file__).resolve().relative_to(root).as_posix(),"sha256":base.sha256_file(Path(__file__).resolve())},"ichimoku_formula_dependency":{"path":BASE_PATH.relative_to(root).as_posix(),"sha256":base.sha256_file(BASE_PATH)},"candidate_registry":{"path":registry.relative_to(root).as_posix(),**authority},"attempt_started":{"path":start_path.relative_to(root).as_posix(),"sha256":base.sha256_file(start_path)},"report":{"path":report_path.relative_to(root).as_posix(),"sha256":hashlib.sha256(report_bytes).hexdigest().upper()},"event_ledger":{"path":ledger_path.relative_to(root).as_posix(),"sha256":hashlib.sha256(ledger_bytes).hexdigest().upper()}},"outcome_blind_counters":{"post_event_ohlc_rows_read":0,"returns_computed":0,"trades_simulated":0,"pnl_computed":0,"profit_factor_computed":0,"validation_rows_read":0,"holdout_rows_read":0},"verdict":report["verdict"]}
    receipt_bytes=base.json_bytes(receipt); receipt_path=output_dir/"source_feasibility_receipt.json"; base.atomic_write(receipt_path,receipt_bytes)
    terminal={"schema_version":"ichimoku_h1_attempt_terminal.v1","hypothesis_id":HYPOTHESIS_ID,"attempt_id":ATTEMPT_ID,"completed_at_utc":receipt["completed_at_utc"],"status":"COMPLETE","verdict":report["verdict"],"source_feasibility_receipt_sha256":hashlib.sha256(receipt_bytes).hexdigest().upper(),"same_id_retry_authorized":False}
    base.atomic_write(output_dir/"attempt_terminal.json",base.json_bytes(terminal))
    return {"report":report,"receipt":receipt,"output_dir":str(output_dir)}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--execute",action="store_true"); args=parser.parse_args()
    if not args.execute: parser.error("--execute is required")
    result=execute(Path(__file__).resolve().parents[3]); print(base.json_bytes(result["report"]).decode("utf-8"),end=""); return 0


if __name__ == "__main__":
    raise SystemExit(main())
