from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path

import pytest


TOOL = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "research"
    / "finalize_fivepercent_market_data_receipt.py"
)


def load_tool():
    spec = importlib.util.spec_from_file_location("finalize_five_asset_data", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_manifest(mod, workspace: Path):
    files = []
    total_bytes = 0
    for symbol in mod.SYMBOLS:
        for timeframe in mod.TIMEFRAMES:
            relative = (
                f"{mod.DATA_ROOT_REL}/{symbol}/"
                f"{symbol}_{timeframe}_ALL_AVAILABLE_20260801.parquet"
            )
            path = workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"{symbol}-{timeframe}".encode("ascii"))
            total_bytes += path.stat().st_size
            files.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": mod.sha256_file(path),
                    "rows": 1,
                    "utc_ambiguous_rows": 0,
                    "source_exact_duplicate_rows_removed": 0,
                }
            )
    manifest = {
        "schema_version": "five_asset_market_data_manifest.v1",
        "dataset_id": mod.DATASET_ID,
        "symbols": list(mod.SYMBOLS),
        "timeframes": list(mod.TIMEFRAMES),
        "terminal": {
            "server": "FivePercentOnline-Real",
            "company": "Five Percent Online Ltd",
            "terminal_trade_allowed": False,
            "data_path": r"D:\MT5",
        },
        "outcome_blind_counters": {
            "orders_submitted": 0,
            "trades_simulated": 0,
            "positions_queried": 0,
            "deals_queried": 0,
            "pnl_computed": 0,
            "profit_factor_computed": 0,
            "mfe_mae_computed": 0,
            "economics_executed": False,
            "validation_selected": False,
            "holdout_selected": False,
        },
        "files": files,
    }
    path = workspace / mod.MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, manifest, total_bytes


def test_manifest_rehashes_all_expected_files_and_rejects_tamper(tmp_path: Path):
    mod = load_tool()
    path, manifest, total_bytes = build_manifest(mod, tmp_path)

    summary = mod.validate_manifest(
        path,
        workspace=tmp_path,
        expected_total_rows=20,
        expected_total_bytes=total_bytes,
        expected_utc_ambiguous_rows=0,
        expected_exact_duplicates_removed=0,
    )
    assert summary["file_count"] == 20

    first = tmp_path / manifest["files"][0]["path"]
    first.write_bytes(b"tampered")
    with pytest.raises(mod.FinalizeError, match="mismatch"):
        mod.validate_manifest(
            path,
            workspace=tmp_path,
            expected_total_rows=20,
            expected_total_bytes=total_bytes,
            expected_utc_ambiguous_rows=0,
            expected_exact_duplicates_removed=0,
        )


def test_manifest_rejects_any_outcome_counter(tmp_path: Path):
    mod = load_tool()
    path, manifest, total_bytes = build_manifest(mod, tmp_path)
    manifest["outcome_blind_counters"]["orders_submitted"] = 1
    path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(mod.FinalizeError, match="outcome-blind"):
        mod.validate_manifest(
            path,
            workspace=tmp_path,
            expected_total_rows=20,
            expected_total_bytes=total_bytes,
            expected_utc_ambiguous_rows=0,
            expected_exact_duplicates_removed=0,
        )


def test_authority_rehashes_every_bound_artifact(tmp_path: Path):
    mod = load_tool()
    authority = {
        "schema_version": "five_asset_data_finalize_authority.v1",
        "dataset_id": mod.DATASET_ID,
        "authorized": True,
        "one_use": True,
    }
    for label in (
        "manifest",
        "export_tool",
        "finalizer",
        "test",
        "plan",
        "storage_reconciliation",
        "consumed_export_authority",
        "blocker",
    ):
        path = tmp_path / f"{label}.txt"
        path.write_text(label, encoding="utf-8")
        authority[f"{label}_path"] = str(path)
        authority[f"{label}_sha256"] = mod.sha256_file(path)

    mod.validate_authority(authority)
    Path(authority["blocker_path"]).write_text("drift", encoding="utf-8")
    with pytest.raises(mod.FinalizeError, match="blocker"):
        mod.validate_authority(authority)


def test_finalizer_ast_has_no_mt5_or_trading_api_surface():
    source = TOOL.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "MetaTrader5" not in source
    forbidden = {
        "initialize",
        "order_send",
        "order_check",
        "positions_get",
        "orders_get",
        "history_orders_get",
        "history_deals_get",
    }
    observed = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in forbidden
    }
    assert observed == set()
