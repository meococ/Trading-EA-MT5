from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "append_t2_data_epoch_evidence.py"
spec = importlib.util.spec_from_file_location("append_t2_data_epoch_evidence", MODULE_PATH)
assert spec and spec.loader
sut = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sut)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":")), encoding="utf-8")


def make_workspace(
    tmp_path: Path,
    symbol: str = "EURUSD",
    hq: float = 98.5,
    trades: int = 0,
    coverage_class: str = "FULL_2018_PLUS",
    copytime_result: int = 1,
) -> tuple[Path, Path, Path, Path]:
    workspace = tmp_path
    epoch = workspace / sut.EPOCH_CONTRACT_PATH
    ledger = workspace / sut.EVIDENCE_LEDGER_PATH
    epoch.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        epoch,
        {
            "schema_version": "alphafactory_data_epoch_contract.v1",
            "record_type": "data_epoch_contract",
            "campaign_id": "CAMPAIGN-PTR-E01",
            "generation": 2,
            "generation_id": "T2",
            "charter": {"path": "x", "sha256": "D63F782926DEC4F12EA8EBB17B3511BC08C249A0AE4ECD9C1F25F5C611386E9E"},
            "server": sut.SERVER,
            "timeframe": sut.PERIOD,
            "tester_model": sut.MODEL,
            "requested_from": sut.FROM_DATE,
            "availability_cutoff_utc": sut.AVAILABILITY_CUTOFF_UTC,
            "history_quality": {"operator": "gt", "threshold_pct": sut.HQ_THRESHOLD},
            "no_skip": True,
            "mandatory_symbols": sut.MANDATORY_SYMBOLS,
            "evidence_ledger_path": sut.EVIDENCE_LEDGER_PATH,
        },
    )
    sut.EPOCH_SHA256 = sha(epoch)
    header = {
        "schema_version": "alphafactory_data_epoch_evidence.v1",
        "record_type": "data_epoch_header",
        "epoch_manifest_sha256": sut.EPOCH_SHA256,
        "campaign_id": "CAMPAIGN-PTR-E01",
        "generation": 2,
        "generation_id": "T2",
        "charter_sha256": "D63F782926DEC4F12EA8EBB17B3511BC08C249A0AE4ECD9C1F25F5C611386E9E",
        "server": sut.SERVER,
        "timeframe": sut.PERIOD,
        "tester_model": sut.MODEL,
        "requested_from": sut.FROM_DATE,
        "availability_cutoff_utc": sut.AVAILABILITY_CUTOFF_UTC,
        "history_quality": {"operator": "gt", "threshold_pct": sut.HQ_THRESHOLD},
        "no_skip": True,
        "mandatory_symbols": sut.MANDATORY_SYMBOLS,
        "prior_epoch_row_sha256": None,
    }
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(header, separators=(",", ":")) + "\n", encoding="utf-8")

    run_dir = workspace / "02. AlphaFactory/runs/EA_PTR_T2_DataEpochD0V2/TEST"
    (run_dir / "config").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    report = run_dir / "report.html"
    report.write_text(f"<b>{sut.SERVER} (Build 9999)</b><table><tr><td>History Quality</td><td>{hq}%</td></tr></table>", encoding="utf-8")
    journal = run_dir / "logs/tester_journal_delta.log"
    journal.write_text(f"{symbol}: history synchronized from 2010.01.01 to {sut.TO_DATE}\n", encoding="utf-8")
    first_epoch = 1262304000
    receipt = run_dir / "config/contract_receipt.json"
    write_json(
        receipt,
        {
            "schema_version": "alphafactory_execution_receipt.v1",
            "authority": sut.AUTHORITY,
            "binding": {
                "hypothesis_id": sut.HYPOTHESIS_ID,
                "run_role": "control",
                "ea_name": sut.EA_NAME,
                "symbol": symbol,
                "period": sut.PERIOD,
                "from": sut.FROM_DATE,
                "to": sut.TO_DATE,
                "model": sut.MODEL,
                "telemetry_profile": "none",
                "data_quality_contract": {
                    "availability_asof_utc": sut.AVAILABILITY_CUTOFF_UTC,
                    "coverage_mode": "all_available_asof",
                    "history_quality": {"operator": "gt", "value": sut.HQ_THRESHOLD},
                    "requested_from": sut.FROM_DATE,
                    "requested_to": sut.TO_DATE,
                    "require_tester_journal_bounds": True,
                },
            },
        },
    )
    dq_contract = {
        "schema_version": "alphafactory_data_quality_contract.v1",
        "symbol": symbol,
        "requested_from": sut.FROM_DATE,
        "requested_to": sut.TO_DATE,
        "history_quality_threshold": sut.HQ_THRESHOLD,
        "coverage_mode": "all_available_asof",
        "availability_asof_utc": sut.AVAILABILITY_CUTOFF_UTC,
        "require_tester_journal_bounds": True,
        "max_journal_delta_bytes": 1048576,
    }
    dq_gate = {
        "contract": dq_contract,
        "coverage_class": coverage_class,
        "series_proof": {
            "symbol": symbol,
            "m5_synchronized": 1,
            "m5_first_epoch": first_epoch,
            "m5_terminal_first_epoch": first_epoch,
            "m1_server_first_epoch": first_epoch,
            "m1_terminal_first_epoch": first_epoch,
            "m5_bars": 1000,
            "terminal_maxbars": 100000,
            "copytime_from_epoch": 0,
            "copytime_count": 1,
            "copytime_result": copytime_result,
            "copytime_first_epoch": first_epoch if copytime_result == 1 else 0,
            "copytime_last_error": 0,
        },
        "history_quality": hq,
        "actual_from": "2010.01.01",
        "actual_to": sut.TO_DATE,
        "journal_path": "logs/tester_journal_delta.log",
        "journal_sha256": sha(journal),
        "journal_bytes_read": journal.stat().st_size,
        "journal_files_read": 1,
        "journal_truncated": False,
        "exact_match_count": 1,
        "distinct_range_count": 1,
    }
    data_fingerprint = "A" * 64
    basis = {
        "schema_version": "alphafactory_data_quality_fingerprint.v1",
        "base_data_fingerprint": data_fingerprint,
        "contract": dq_contract,
        "history_quality": hq,
        "actual_from": "2010.01.01",
        "actual_to": sut.TO_DATE,
        "coverage_class": coverage_class,
        "series_proof": dq_gate["series_proof"],
        "journal_sha256": sha(journal),
        "journal_bytes_read": journal.stat().st_size,
        "journal_files_read": 1,
        "journal_truncated": False,
        "exact_match_count": 1,
        "distinct_range_count": 1,
    }
    data_quality_fingerprint = sut.text_sha256(sut.ps_compact_json(basis))
    manifest = run_dir / "run_manifest.json"
    write_json(
        manifest,
        {
            "schema_version": "alphafactory_run_manifest.v2",
            "hypothesis_id": sut.HYPOTHESIS_ID,
            "ea_name": sut.EA_NAME,
            "run_role": "control",
            "symbol": symbol,
            "period": sut.PERIOD,
            "model": sut.MODEL,
            "from": sut.FROM_DATE,
            "to": sut.TO_DATE,
            "telemetry_profile": "none",
            "local_run_dir": str(run_dir.resolve()),
            "report_path": str(report.resolve()),
            "contract_receipt_sha256": sha(receipt),
            "report_sha256": sha(report),
            "data_quality_contract": dq_contract,
            "data_quality_gate": dq_gate,
            "data_fingerprint": data_fingerprint,
            "data_quality_journal_delta": {
                "path": "logs/tester_journal_delta.log",
                "sha256": sha(journal),
                "bytes_read": journal.stat().st_size,
                "files_read": 1,
                "truncated": False,
            },
            "data_quality_fingerprint_basis": basis,
            "data_quality_fingerprint": data_quality_fingerprint,
        },
    )
    summary = run_dir / "analysis/enhanced_summary.json"
    write_json(
        summary,
        {
            "schema_version": "alphafactory_zero_trade_collection_summary.v1",
            "analysis_mode": "data_acquisition_only",
            "authority": sut.AUTHORITY,
            "n_trades": trades,
            "performance_metrics_authorized": False,
            "generated_at_utc": "2026-07-30T23:10:00Z",
        },
    )
    return workspace, manifest, summary, ledger


def test_build_row_accepts_exact_zero_trade_data_epoch(tmp_path: Path) -> None:
    workspace, manifest, summary, _ = make_workspace(tmp_path)
    row = sut.build_row(workspace, "EURUSD", manifest, summary)
    assert row["record_type"] == "data_epoch_symbol"
    assert row["status"] == "PASS"
    assert row["selected"] is True
    assert row["symbol"] == "EURUSD"
    assert row["data_quality_fingerprint"] == sut.text_sha256(sut.ps_compact_json(manifest_data_quality_basis(manifest)))
    assert set(row) == {
        "schema_version",
        "record_type",
        "symbol",
        "status",
        "selected",
        "prior_epoch_row_sha256",
        "receipt",
        "run_manifest",
        "data_quality_fingerprint",
        "report",
}


def manifest_data_quality_basis(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["data_quality_fingerprint_basis"]


def test_append_rejects_nonzero_trade_summary(tmp_path: Path) -> None:
    workspace, manifest, summary, _ = make_workspace(tmp_path, trades=1)
    with pytest.raises(sut.EvidenceError, match="n_trades"):
        sut.build_row(workspace, "EURUSD", manifest, summary)


def test_append_rejects_history_quality_at_threshold(tmp_path: Path) -> None:
    workspace, manifest, summary, _ = make_workspace(tmp_path, hq=97.0)
    with pytest.raises(sut.EvidenceError, match="History Quality"):
        sut.build_row(workspace, "EURUSD", manifest, summary)


def test_append_rejects_invalid_truncated_terminal_cache(tmp_path: Path) -> None:
    workspace, manifest, summary, _ = make_workspace(tmp_path, coverage_class="INVALID_TRUNCATED_TERMINAL_CACHE")
    with pytest.raises(sut.EvidenceError, match="INVALID_TRUNCATED_TERMINAL_CACHE"):
        sut.build_row(workspace, "EURUSD", manifest, summary)


def test_append_rejects_failed_series_copytime_probe(tmp_path: Path) -> None:
    workspace, manifest, summary, _ = make_workspace(tmp_path, copytime_result=0)
    with pytest.raises(sut.EvidenceError, match="CopyTime"):
        sut.build_row(workspace, "EURUSD", manifest, summary)


def test_append_rejects_duplicate_selected_pass_symbol(tmp_path: Path) -> None:
    workspace, manifest, summary, ledger = make_workspace(tmp_path)
    row = sut.build_row(workspace, "EURUSD", manifest, summary)
    sut.append_row(ledger, row)
    with pytest.raises(sut.EvidenceError, match="already exists"):
        sut.build_row(workspace, "EURUSD", manifest, summary)
