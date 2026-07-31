#!/usr/bin/env python3
"""Outcome-blind source exporter for the HYP-LOMX-002 data-contract successor."""

from __future__ import annotations

import importlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


BASE_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "export_lomx_001_train_source.py"
)
HYPOTHESIS_ID = "HYP-LOMX-MULTI-M1-002"
ATTEMPT_ID = "LOMX002-TRAIN-SOURCE-001"
PLAN_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "HYP-LOMX-MULTI-M1-002_TRAIN_PROBE_PLAN.md"
)
SCRIPT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/"
    "export_lomx_002_train_source.py"
)
DATA_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/LondonOpenMultiAssetMomentum/"
    "HYP-LOMX-MULTI-M1-002"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_LondonOpenMultiAssetMomentum/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)
MIN_RAW_POSITIVE_SPREAD_COVERAGE = 0.80
IMPUTATION_QUANTILE = 0.95


def _load_base():
    path = Path(__file__).with_name("export_lomx_001_train_source.py")
    spec = importlib.util.spec_from_file_location("lomx_001_export_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load HYP001 source base")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


base = _load_base()
ContractError = base.ContractError


def configure_base() -> None:
    base.HYPOTHESIS_ID = HYPOTHESIS_ID
    base.ATTEMPT_ID = ATTEMPT_ID
    base.PLAN_REL = PLAN_REL
    base.SCRIPT_REL = SCRIPT_REL
    base.DATA_ROOT_REL = DATA_ROOT_REL
    base.EVIDENCE_ROOT_REL = EVIDENCE_ROOT_REL


def impute_missing_spreads(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    """Replace absent historical spreads with a predeclared conservative q95."""

    result = frame.copy()
    spread_cols = [column for column in result.columns if column.startswith("spread_")]
    if len(spread_cols) != 5:
        raise ContractError("unexpected spread schema")
    quality: dict[str, object] = {}
    for symbol in base.SYMBOLS:
        mask = result["symbol"] == symbol
        values = result.loc[mask, spread_cols].to_numpy(dtype=float)
        if values.size == 0:
            raise ContractError(f"no source rows for {symbol}")
        positive = values[values > 0]
        coverage = float(len(positive) / values.size)
        if coverage < MIN_RAW_POSITIVE_SPREAD_COVERAGE:
            raise ContractError(
                f"raw positive spread coverage below successor gate for {symbol}: {coverage:.6f}"
            )
        if len(positive) == 0:
            raise ContractError(f"no positive spread observations for {symbol}")
        fallback = max(1, int(math.ceil(float(np.quantile(positive, IMPUTATION_QUANTILE, method="higher")))))
        missing = int(np.count_nonzero(values <= 0))
        for column in spread_cols:
            target = mask & (result[column] <= 0)
            result.loc[target, column] = fallback
        quality[symbol] = {
            "raw_positive_spread_coverage": coverage,
            "raw_nonpositive_endpoint_count": missing,
            "imputed_endpoint_count": missing,
            "imputation_quantile": IMPUTATION_QUANTILE,
            "imputation_spread_points": fallback,
            "imputation_scope": "NONPOSITIVE_ENDPOINT_FIELDS_ONLY",
        }
    if (result[spread_cols] <= 0).any().any():
        raise ContractError("nonpositive spread survived imputation")
    return result, quality


def verify_base_binding(workspace: Path) -> None:
    row, _ = base.latest_registry_row(workspace / base.REGISTRY_REL)
    validation = row.get("validation") or {}
    if validation.get("reviewed_source_exporter_base_path") != BASE_REL:
        raise ContractError("source exporter base path mismatch")
    expected = str(validation.get("reviewed_source_exporter_base_sha256", "")).upper()
    if base.sha256_file(workspace / BASE_REL) != expected:
        raise ContractError("source exporter base SHA mismatch")


def export_train_source(workspace: Path, *, reviewed_registry_sha: str) -> dict[str, object]:
    configure_base()
    workspace = base.require_d_path(workspace, label="workspace")
    verify_base_binding(workspace)
    authority = base.verify_authority(workspace, reviewed_registry_sha)
    data_root = base.reserve_directory(workspace / DATA_ROOT_REL)
    evidence_root = base.reserve_directory(workspace / EVIDENCE_ROOT_REL)
    terminal_path = base.require_d_path(workspace / base.TERMINAL_REL, label="terminal")
    mt5 = importlib.import_module("MetaTrader5")
    rows: list[dict[str, object]] = []
    try:
        terminal_meta, geometry = base.initialize_terminal(mt5, terminal_path)
        for symbol in base.SYMBOLS:
            point, digits = geometry[symbol]
            for year in base.TRAIN_YEARS:
                start = datetime(year, 1, 1, tzinfo=timezone.utc)
                end = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
                if rates is None:
                    raise ContractError(
                        f"copy_rates_range failed: {symbol}:{year}:{mt5.last_error()}"
                    )
                rows.extend(
                    base.extract_daily_windows(
                        rates,
                        symbol=symbol,
                        point=point,
                        digits=digits,
                        broker_server=base.EXPECTED_SERVER,
                    )
                )
    finally:
        mt5.shutdown()
    raw_frame = pd.DataFrame(rows, columns=base.SCHEMA_COLUMNS)
    raw_frame = raw_frame.sort_values(["symbol", "local_date"], kind="mergesort").reset_index(drop=True)
    frame, spread_quality = impute_missing_spreads(raw_frame)
    source_summary = base.summarize_source(frame)
    parquet_path = data_root / "train_daily_windows.parquet"
    frame.to_parquet(parquet_path, index=False, compression="zstd")
    manifest = {
        "schema_version": "lomx_002_train_source_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "split": "TRAIN",
        "train_years": list(base.TRAIN_YEARS),
        "validation_years_sealed": [2021, 2022, 2023, 2024],
        "holdout_rule": "EVERY_YEAR_2025PLUS_FORBIDDEN",
        "symbols": list(base.SYMBOLS),
        "timezone": base.LOCAL_TZ,
        "required_hhmm": list(base.REQUIRED_HHMM),
        "bar_contract": "BROKER_BID_M1_EXACT_LOCAL_TIMESTAMP_OPEN",
        "spread_contract": (
            "RAW_POSITIVE_COVERAGE_GTE_0.80; NONPOSITIVE_ENDPOINTS_IMPUTED_"
            "WITH_SAME_SYMBOL_TRAIN_POSITIVE_SPREAD_Q95"
        ),
        "raw_spread_quality": spread_quality,
        "row_count": int(len(frame)),
        "schema": list(frame.columns),
        "per_symbol": source_summary,
        "parquet_path": str(parquet_path.relative_to(workspace)).replace("\\", "/"),
        "parquet_sha256": base.sha256_file(parquet_path),
        "authority": authority,
        "terminal_metadata": terminal_meta,
        "outcome_blind_counters": {
            "returns_computed": 0,
            "signals_generated": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "pf_computed": 0,
            "expectancy_computed": 0,
            "economics_executed": False,
            "validation_rows_requested": 0,
            "holdout_rows_requested": 0,
            "orders_submitted": 0,
            "paid_requests_made": 0,
            "model0_runs": 0,
            "source_attempts_consumed": 1,
        },
    }
    manifest_path = data_root / "train_source_manifest.json"
    base.atomic_write(manifest_path, base.canonical_json(manifest) + b"\n")
    receipt = {
        "schema_version": "lomx_002_train_source_receipt.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": "TRAIN_SOURCE_COMPLETE_ECONOMICS_DISABLED",
        "manifest_path": str(manifest_path.relative_to(workspace)).replace("\\", "/"),
        "manifest_sha256": base.sha256_file(manifest_path),
        "parquet_sha256": manifest["parquet_sha256"],
        "row_count": int(len(frame)),
        "authority": authority,
        "created_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    receipt_path = evidence_root / "train_source_receipt.json"
    base.atomic_write(receipt_path, base.canonical_json(receipt) + b"\n")
    return receipt


def main(argv: Iterable[str] | None = None) -> int:
    configure_base()
    args = base.build_parser().parse_args(list(argv) if argv is not None else None)
    if not args.production:
        raise ContractError("production is disarmed; pass --production")
    if not args.reviewed_registry_row_sha256:
        raise ContractError("reviewed registry row SHA is required")
    receipt = export_train_source(
        Path(args.workspace),
        reviewed_registry_sha=str(args.reviewed_registry_row_sha256),
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ContractError as exc:
        print(f"LOMX002_SOURCE_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
