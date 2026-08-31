from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


RESEARCH = Path(__file__).resolve().parents[1]
MODULE_PATH = RESEARCH / "validate_data_epoch.py"
SPEC = importlib.util.spec_from_file_location("data_epoch_validator", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
SUT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUT)


def body(row: dict[str, object]) -> bytes:
    return json.dumps(row, separators=(",", ":")).encode("utf-8")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write_json(path: Path, value: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
    return path


def write_blob(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_ledger(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(body(row) + b"\n" for row in rows))
    return path


def chain(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    chained: list[dict[str, object]] = []
    prior: str | None = None
    for row in rows:
        current = copy.deepcopy(row)
        current["prior_epoch_row_sha256"] = prior
        chained.append(current)
        prior = sha_bytes(body(current))
    return chained


def contract_fixture(tmp_path: Path, ledger: Path | None = None) -> tuple[Path, dict[str, object], Path]:
    workspace = tmp_path / "workspace"
    SUT.WORKSPACE_ROOT = workspace
    charter = write_blob(workspace / "04. Memory/research/charter.json", b'{"charter":"frozen"}\n')
    ledger_path = ledger or workspace / "04. Memory/research/data_epoch_evidence.jsonl"
    contract = {
        "schema_version": "alphafactory_data_epoch_contract.v1",
        "record_type": "data_epoch_contract",
        "campaign_id": "CAMPAIGN-PTR-E01",
        "generation": 1,
        "generation_id": "T1",
        "charter": {
            "path": "04. Memory/research/charter.json",
            "sha256": sha_file(charter),
        },
        "server": "FivePercentOnline-Real",
        "timeframe": "M5",
        "tester_model": 0,
        "requested_from": "1970.01.01",
        "availability_cutoff_utc": "2026-07-30T23:59:59Z",
        "history_quality": {"operator": "gt", "threshold_pct": 97.0},
        "no_skip": True,
        "mandatory_symbols": SUT.MANDATORY_SYMBOLS,
        "evidence_ledger_path": str(ledger_path.relative_to(workspace)),
    }
    contract_path = write_json(workspace / "04. Memory/research/data_epoch_contract.json", contract)
    return contract_path, contract, ledger_path


def header_row(contract_path: Path, contract: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "alphafactory_data_epoch_evidence.v1",
        "record_type": "data_epoch_header",
        "epoch_manifest_sha256": sha_file(contract_path),
        "campaign_id": contract["campaign_id"],
        "generation": contract["generation"],
        "generation_id": contract["generation_id"],
        "charter_sha256": contract["charter"]["sha256"],  # type: ignore[index]
        "server": contract["server"],
        "timeframe": contract["timeframe"],
        "tester_model": contract["tester_model"],
        "requested_from": contract["requested_from"],
        "availability_cutoff_utc": contract["availability_cutoff_utc"],
        "history_quality": contract["history_quality"],
        "no_skip": True,
        "mandatory_symbols": SUT.MANDATORY_SYMBOLS,
        "prior_epoch_row_sha256": None,
    }


def symbol_row(
    workspace: Path,
    contract: dict[str, object],
    symbol: str,
    *,
    duplicate_identical_journal_line: bool = False,
    actual_to: str = "2026.07.30",
) -> dict[str, object]:
    root = workspace / "02. AlphaFactory/runs/T1_EPOCH" / symbol
    report = write_blob(
        root / "report.html",
        b"<html><b>FivePercentOnline-Real (Build 6006)</b><table><tr><td>History Quality:</td><td><b>99%</b></td></tr></table></html>\n",
    )
    journal_line = f"{symbol}: history synchronized from 2018.01.01 to {actual_to}\n"
    series_proof_line = (
        f"DATA_EPOCH_D0_SERIES_PROOF symbol={symbol} m5_synchronized=1 "
        "m5_first_epoch=1514764800 m5_terminal_first_epoch=1514764800 "
        "m1_server_first_epoch=1514764800 m1_terminal_first_epoch=1514764800 "
        "m5_bars=100001 terminal_maxbars=100000 copytime_from_epoch=1514764800 "
        "copytime_count=1 copytime_result=1 copytime_first_epoch=1514764800 "
        "copytime_last_error=0\n"
    )
    real_tick_line = (
        f"CS\t0\t07:55:31.561\tTester\t{symbol},M5 "
        "(FivePercentOnline-Real): generating based on real ticks\n"
        if contract["tester_model"] == 4
        else ""
    )
    journal = write_blob(
        root / "logs/tester_journal_delta.log",
        (real_tick_line + journal_line * (2 if duplicate_identical_journal_line else 1) + series_proof_line).encode("utf-8"),
    )
    exact_match_count = 2 if duplicate_identical_journal_line else 1
    receipt_contract = {
        "availability_asof_utc": contract["availability_cutoff_utc"],
        "coverage_mode": "all_available_asof",
        "history_quality": {"operator": "gt", "value": 97.0},
        "requested_from": "1970.01.01",
        "requested_to": "2026.07.30",
        "require_tester_journal_bounds": True,
    }
    receipt_value = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": (
            "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE"
            if contract["tester_model"] == 0
            else "DATA_ACQUISITION_ONLY_NO_PERFORMANCE"
        ),
        "binding": {
            "symbol": symbol,
            "period": "M5",
            "from": "1970.01.01",
            "to": "2026.07.30",
            "model": contract["tester_model"],
            "data_quality_contract": receipt_contract,
        },
        "evidence": [],
    }
    receipt = write_json(root / "receipt.json", receipt_value)
    dq_contract = {
        "schema_version": "alphafactory_data_quality_contract.v1",
        "symbol": symbol,
        "requested_from": "1970.01.01",
        "requested_to": "2026.07.30",
        "history_quality_threshold": 97.0,
        "coverage_mode": "all_available_asof",
        "availability_asof_utc": contract["availability_cutoff_utc"],
        "require_tester_journal_bounds": True,
        "max_journal_delta_bytes": 1048576,
    }
    dq_gate = {
        "contract": dq_contract,
        "history_quality": 99.0,
        "actual_from": "2018.01.01",
        "actual_to": actual_to,
        "coverage_class": "FULL_2018_PLUS",
        "series_proof": {
            "symbol": symbol,
            "m5_synchronized": 1,
            "m5_first_epoch": 1514764800,
            "m5_terminal_first_epoch": 1514764800,
            "m1_server_first_epoch": 1514764800,
            "m1_terminal_first_epoch": 1514764800,
            "m5_bars": 100001,
            "terminal_maxbars": 100000,
            "copytime_from_epoch": 1514764800,
            "copytime_count": 1,
            "copytime_result": 1,
            "copytime_first_epoch": 1514764800,
            "copytime_last_error": 0,
        },
        "journal_path": "logs/tester_journal_delta.log",
        "journal_sha256": sha_file(journal),
        "journal_bytes_read": len(journal.read_bytes()),
        "journal_files_read": 1,
        "journal_truncated": False,
        "exact_match_count": exact_match_count,
        "distinct_range_count": 1,
    }
    base_data_fingerprint = "B" * 64
    fingerprint_basis = {
        "schema_version": "alphafactory_data_quality_fingerprint.v1",
        "base_data_fingerprint": base_data_fingerprint,
        "contract": dq_contract,
        "history_quality": dq_gate["history_quality"],
        "actual_from": dq_gate["actual_from"],
        "actual_to": dq_gate["actual_to"],
        "coverage_class": dq_gate["coverage_class"],
        "series_proof": dq_gate["series_proof"],
        "journal_sha256": dq_gate["journal_sha256"],
        "journal_bytes_read": dq_gate["journal_bytes_read"],
        "journal_files_read": dq_gate["journal_files_read"],
        "journal_truncated": dq_gate["journal_truncated"],
        "exact_match_count": dq_gate["exact_match_count"],
        "distinct_range_count": dq_gate["distinct_range_count"],
    }
    fingerprint = sha_bytes(SUT._ps_compact_json(fingerprint_basis).encode("utf-8"))
    manifest_value = {
        "schema_version": "alphafactory_run_manifest.v2",
        "run_id": f"T1_EPOCH_{symbol}",
        "symbol": symbol,
        "period": "M5",
        "model": contract["tester_model"],
        "from": "1970.01.01",
        "to": "2026.07.30",
        "local_run_dir": str(root),
        "report_path": str(report),
        "report_sha256": sha_file(report),
        "contract_receipt_sha256": sha_file(receipt),
        "data_fingerprint": base_data_fingerprint,
        "data_quality_contract": dq_contract,
        "data_quality_journal_delta": {
            "path": "logs/tester_journal_delta.log",
            "sha256": sha_file(journal),
            "bytes_read": len(journal.read_bytes()),
            "files_read": 1,
            "truncated": False,
        },
        "data_quality_gate": dq_gate,
        "data_quality_fingerprint_basis": fingerprint_basis,
        "data_quality_fingerprint": fingerprint,
    }
    manifest = write_json(root / "run_manifest.json", manifest_value)
    return {
        "schema_version": "alphafactory_data_epoch_evidence.v1",
        "record_type": "data_epoch_symbol",
        "symbol": symbol,
        "status": "PASS",
        "selected": True,
        "prior_epoch_row_sha256": None,
        "receipt": {"path": str(receipt.relative_to(workspace)), "sha256": sha_file(receipt)},
        "run_manifest": {"path": str(manifest.relative_to(workspace)), "sha256": sha_file(manifest)},
        "data_quality_fingerprint": fingerprint,
        "report": {"path": str(report.relative_to(workspace)), "sha256": sha_file(report)},
    }


def refresh_manifest_and_row(workspace: Path, row: dict[str, object]) -> None:
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    basis = manifest["data_quality_fingerprint_basis"]
    fingerprint = sha_bytes(SUT._ps_compact_json(basis).encode("utf-8"))
    manifest["data_quality_fingerprint"] = fingerprint
    write_json(manifest_path, manifest)
    row["data_quality_fingerprint"] = fingerprint
    row["run_manifest"]["sha256"] = sha_file(manifest_path)  # type: ignore[index]
    report_path = workspace / row["report"]["path"]  # type: ignore[index,operator]
    row["report"]["sha256"] = sha_file(report_path)  # type: ignore[index]
    receipt_path = workspace / row["receipt"]["path"]  # type: ignore[index,operator]
    row["receipt"]["sha256"] = sha_file(receipt_path)  # type: ignore[index]


def validate_contract(contract_path: Path, require_complete: bool = False) -> dict[str, object]:
    return SUT.validate_epoch(contract_path, require_complete=require_complete)


def test_empty_header_valid_incomplete(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    write_ledger(ledger, chain([header_row(contract_path, contract)]))

    result = validate_contract(contract_path)

    assert result["ok"] is True
    assert result["aggregate_ready"] is False
    assert result["missing"] == SUT.MANDATORY_SYMBOLS


def test_model4_real_tick_epoch_row_is_valid(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["tester_model"] = 4
    write_json(contract_path, contract)
    workspace = SUT.WORKSPACE_ROOT
    rows = chain([header_row(contract_path, contract), symbol_row(workspace, contract, "XAUUSD")])
    write_ledger(ledger, rows)

    result = validate_contract(contract_path)

    assert result["ok"] is True
    assert result["aggregate_ready"] is False


def test_model4_requires_explicit_real_tick_journal_readback(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["tester_model"] = 4
    write_json(contract_path, contract)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    journal_path = workspace / "02. AlphaFactory/runs/T1_EPOCH/XAUUSD/logs/tester_journal_delta.log"
    journal_path.write_text(
        re.sub(
            r"(?m)^CS\t0\t07:55:31\.561\tTester\t.*generating based on real ticks\n",
            "",
            journal_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    journal_sha = sha_file(journal_path)
    journal_bytes = journal_path.stat().st_size
    manifest["data_quality_journal_delta"]["sha256"] = journal_sha
    manifest["data_quality_journal_delta"]["bytes_read"] = journal_bytes
    manifest["data_quality_gate"]["journal_sha256"] = journal_sha
    manifest["data_quality_gate"]["journal_bytes_read"] = journal_bytes
    manifest["data_quality_fingerprint_basis"]["journal_sha256"] = journal_sha
    manifest["data_quality_fingerprint_basis"]["journal_bytes_read"] = journal_bytes
    write_json(manifest_path, manifest)
    refresh_manifest_and_row(workspace, row)
    rows = chain([header_row(contract_path, contract), row])
    write_ledger(ledger, rows)

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("lacks exact Tester execution mode" in error for error in result["errors"])


def test_model4_rejects_execution_mode_from_another_symbol(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["tester_model"] = 4
    write_json(contract_path, contract)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    journal_path = workspace / "02. AlphaFactory/runs/T1_EPOCH/XAUUSD/logs/tester_journal_delta.log"
    journal_path.write_text(
        journal_path.read_text(encoding="utf-8").replace(
            "Tester\tXAUUSD,M5 (FivePercentOnline-Real): generating based on real ticks",
            "Tester\tEURUSD,M5 (FivePercentOnline-Real): generating based on real ticks",
        ),
        encoding="utf-8",
    )
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    journal_sha = sha_file(journal_path)
    journal_bytes = journal_path.stat().st_size
    manifest["data_quality_journal_delta"]["sha256"] = journal_sha
    manifest["data_quality_journal_delta"]["bytes_read"] = journal_bytes
    manifest["data_quality_gate"]["journal_sha256"] = journal_sha
    manifest["data_quality_gate"]["journal_bytes_read"] = journal_bytes
    manifest["data_quality_fingerprint_basis"]["journal_sha256"] = journal_sha
    manifest["data_quality_fingerprint_basis"]["journal_bytes_read"] = journal_bytes
    write_json(manifest_path, manifest)
    refresh_manifest_and_row(workspace, row)
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("lacks exact Tester execution mode" in error for error in result["errors"])


def test_model4_shared_parser_rejects_bare_wrong_period_and_wrong_server() -> None:
    wrong_lines = (
        "Tester: XAUUSD,M5 (FivePercentOnline-Real): generating based on real ticks\n",
        "CS\t0\t07:55:31.561\tTester\tXAUUSD,M15 "
        "(FivePercentOnline-Real): generating based on real ticks\n",
        "CS\t0\t07:55:31.561\tTester\tXAUUSD,M5 "
        "(WrongServer): generating based on real ticks\n",
    )
    for journal_text in wrong_lines:
        errors = SUT._model4_real_tick_mode_errors(
            journal_text,
            "test journal",
            symbol="XAUUSD",
            period="M5",
            server="FivePercentOnline-Real",
        )
        assert any("lacks exact Tester execution mode" in error for error in errors)


def test_model4_rejects_contradictory_generated_tick_readback(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["tester_model"] = 4
    write_json(contract_path, contract)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    journal_path = workspace / "02. AlphaFactory/runs/T1_EPOCH/XAUUSD/logs/tester_journal_delta.log"
    journal_path.write_text(
        journal_path.read_text(encoding="utf-8")
        + "CS\t0\t07:55:31.562\tTester\tXAUUSD,M5 "
        "(FivePercentOnline-Real): every tick generated from M1 bars\n",
        encoding="utf-8",
    )
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    journal_sha = sha_file(journal_path)
    journal_bytes = journal_path.stat().st_size
    manifest["data_quality_journal_delta"]["sha256"] = journal_sha
    manifest["data_quality_journal_delta"]["bytes_read"] = journal_bytes
    manifest["data_quality_gate"]["journal_sha256"] = journal_sha
    manifest["data_quality_gate"]["journal_bytes_read"] = journal_bytes
    manifest["data_quality_fingerprint_basis"]["journal_sha256"] = journal_sha
    manifest["data_quality_fingerprint_basis"]["journal_bytes_read"] = journal_bytes
    write_json(manifest_path, manifest)
    refresh_manifest_and_row(workspace, row)
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("contradictory generated-tick" in error for error in result["errors"])


def test_model4_identity_chain_rejects_cross_hypothesis_substitution(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    SUT.WORKSPACE_ROOT = workspace
    research = workspace / "04. Memory/research"
    source = write_blob(
        workspace / "03. EA Developer/EA_PTR_T2_DataEpochD0V3/EA_PTR_T2_DataEpochD0V3.mq5",
        b"// frozen source\n",
    )
    prereg = write_blob(
        workspace
        / "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/HYP-PTR-T2-DATA-EPOCH-D0-M5-004_PREREG.md",
        b"# frozen prereg\n",
    )
    cost = write_blob(
        workspace
        / "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/COLLECTION_ONLY_COST_SOURCE_MANIFEST_MODEL4.json",
        b'{"authority":"DATA_ACQUISITION_ONLY_NO_PERFORMANCE"}\n',
    )
    contract_sha = "A" * 64
    registry_row = {
        "record_type": "hypothesis_state",
        "hypothesis_id": "HYP-PTR-T2-DATA-EPOCH-D0-M5-004",
        "ea_name": "EA_PTR_T2_DataEpochD0V3",
        "model": 4,
        "source_path": str(source.relative_to(workspace)).replace("\\", "/"),
        "source_hash": sha_file(source),
        "prereg_path": str(prereg.relative_to(workspace)).replace("\\", "/"),
        "prereg_sha256": sha_file(prereg),
        "validation": {
            "data_epoch_contract_sha256": contract_sha,
            "cost_source_manifest_path": str(cost.relative_to(workspace)).replace("\\", "/"),
            "cost_source_manifest_sha256": sha_file(cost),
        },
    }
    registry_body = body(registry_row)
    registry = research / "CANDIDATE_REGISTRY.jsonl"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_bytes(registry_body + b"\n")
    row_sha = sha_bytes(registry_body)
    registry_prefix_sha = sha_file(registry)
    task = {
        "hypothesis_id": "HYP-CROSS-SUBSTITUTION-M5-999",
        "ea_name": "EA_PTR_T2_DataEpochD0V3",
        "run_role": "control",
        "authority": "DATA_ACQUISITION_ONLY_NO_PERFORMANCE",
        "model": 4,
        "symbol": "XAUUSD",
        "period": "M5",
        "source_path": registry_row["source_path"],
        "source_sha256": registry_row["source_hash"],
        "prereg_path": registry_row["prereg_path"],
        "prereg_sha256": registry_row["prereg_sha256"],
        "cost_source_manifest_path": registry_row["validation"]["cost_source_manifest_path"],
        "cost_source_manifest_sha256": registry_row["validation"]["cost_source_manifest_sha256"],
        "registry_row_sha256": row_sha,
        "registry_sha256": registry_prefix_sha,
    }
    task_path = write_json(
        workspace / "03. EA Developer/EA_PTR_T2_DataEpochD0V3/research/task.json",
        task,
    )
    receipt_path = workspace / "02. AlphaFactory/runtime/receipt.json"
    receipt = {
        "hypothesis_id": "HYP-CROSS-SUBSTITUTION-M5-999",
        "registry_row_sha256": row_sha,
        "task_packet_sha256": sha_file(task_path),
        "binding": {
            "hypothesis_id": "HYP-CROSS-SUBSTITUTION-M5-999",
            "ea_name": "EA_PTR_T2_DataEpochD0V3",
            "run_role": "control",
            "telemetry_profile": "none",
        },
        "evidence": [
            {"label": "task_packet", "path": str(task_path), "sha256": sha_file(task_path)},
            {"label": "candidate_registry", "path": str(registry), "sha256": registry_prefix_sha},
            {"label": "source", "path": str(source), "sha256": sha_file(source)},
            {"label": "prereg", "path": str(prereg), "sha256": sha_file(prereg)},
            {"label": "cost_source_manifest", "path": str(cost), "sha256": sha_file(cost)},
        ],
    }
    write_json(receipt_path, receipt)
    identity_errors: list[str] = []
    identity = SUT._registry_identity_for_model4(contract_sha, identity_errors)
    assert identity_errors == []
    assert identity is not None
    manifest = {
        "hypothesis_id": "HYP-CROSS-SUBSTITUTION-M5-999",
        "ea_name": "EA_PTR_T2_DataEpochD0V3",
        "run_role": "control",
        "source_sha256": sha_file(source),
        "research_loop": {
            "hypothesis_id": "HYP-CROSS-SUBSTITUTION-M5-999",
            "run_role": "control",
            "prereg_sha256": sha_file(prereg),
            "task_packet_path": str(task_path),
            "task_packet_sha256": sha_file(task_path),
            "evidence": {
                "execution_receipt_path": str(receipt_path),
                "execution_receipt_sha256": sha_file(receipt_path),
            },
        },
    }
    evidence_row = {"symbol": "XAUUSD", "receipt": {"sha256": sha_file(receipt_path)}}
    errors: list[str] = []
    SUT._validate_model4_identity_chain(
        receipt,
        receipt_path,
        manifest,
        evidence_row,
        identity,
        "cross-hyp",
        errors,
    )
    assert any("receipt hypothesis_id must equal HYP-PTR-T2-DATA-EPOCH-D0-M5-004" in error for error in errors)
    assert any("task packet hypothesis_id must equal registry identity" in error for error in errors)


def test_data_epoch_rejects_other_tester_models(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["tester_model"] = 2
    write_json(contract_path, contract)
    write_ledger(ledger, chain([header_row(contract_path, contract)]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("tester_model must be integer 0 or 4" in error for error in result["errors"])


def test_native_mt5_utf16_report_is_decoded(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text(
        "<html><b>FivePercentOnline-Real (Build 6061)</b><table>"
        "<tr><td>History Quality:</td><td><b>98%</b></td></tr></table></html>",
        encoding="utf-16",
    )

    report_text = SUT._read_report_text(report)
    assert SUT._report_history_quality(report_text) == 98.0
    assert SUT._report_server_identity(report_text) == "FivePercentOnline-Real (Build 6061)"


def test_series_proof_classifies_broker_limit_and_rejects_truncated_cache() -> None:
    first = 1612137600  # 2021-02-01 UTC
    valid = (
        "EURUSD: history synchronized from 2021.02.01 to 2026.07.30\n"
        "DATA_EPOCH_D0_SERIES_PROOF symbol=EURUSD m5_synchronized=1 "
        f"m5_first_epoch={first} m5_terminal_first_epoch={first} "
        f"m1_server_first_epoch={first} m1_terminal_first_epoch={first} "
        f"m5_bars=100001 terminal_maxbars=100000 copytime_from_epoch={first} "
        f"copytime_count=1 copytime_result=1 copytime_first_epoch={first} copytime_last_error=0\n"
    )
    proof = SUT._journal_series_proof(valid, "EURUSD", "2021.02.01")
    assert proof is not None
    assert proof["coverage_class"] == "BROKER_LIMITED_START"

    server_2017 = 1483315200
    truncated = valid.replace(
        f"m1_server_first_epoch={first} m1_terminal_first_epoch={first}",
        f"m1_server_first_epoch={server_2017} m1_terminal_first_epoch={server_2017}",
    )
    assert SUT._journal_series_proof(truncated, "EURUSD", "2021.02.01") is None


def test_contract_rejects_bool_generation_and_tester_model(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["generation"] = True
    contract["tester_model"] = False
    write_json(contract_path, contract)
    write_ledger(ledger, chain([header_row(contract_path, contract)]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("generation must be an integer from 1 through 100" in error for error in result["errors"])
    assert any("tester_model must be integer 0" in error for error in result["errors"])


def test_contract_accepts_t2_generation_identity(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["generation"] = 2
    contract["generation_id"] = "T2"
    write_json(contract_path, contract)
    write_ledger(ledger, chain([header_row(contract_path, contract)]))

    result = validate_contract(contract_path)

    assert result["ok"] is True
    assert result["aggregate_ready"] is False
    assert result["missing"] == SUT.MANDATORY_SYMBOLS


def test_contract_rejects_generation_id_mismatch(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    contract["generation"] = 2
    contract["generation_id"] = "T1"
    write_json(contract_path, contract)
    write_ledger(ledger, chain([header_row(contract_path, contract)]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("generation_id must equal T{generation}" in error for error in result["errors"])


def test_missing_mandatory_and_duplicate_symbol_are_rejected(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    first = symbol_row(workspace, contract, "XAUUSD")
    duplicate = symbol_row(workspace, contract, "XAUUSD")
    write_ledger(ledger, chain([header_row(contract_path, contract), first, duplicate]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert "BTCUSD" in result["missing"]
    assert any("duplicate selected row for symbol" in error for error in result["errors"])


def test_forged_hashes_are_rejected(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    row["receipt"]["sha256"] = "A" * 64  # type: ignore[index]
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("receipt: sha256 mismatch" in error for error in result["errors"])


def test_receipt_blob_is_rejected(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    receipt_path = workspace / row["receipt"]["path"]  # type: ignore[index,operator]
    receipt_path.write_text("not-json\n", encoding="utf-8")
    row["receipt"]["sha256"] = sha_file(receipt_path)  # type: ignore[index]
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("receipt invalid strict JSON" in error for error in result["errors"])


def test_receipt_binding_model_rejects_json_bool(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    receipt_path = workspace / row["receipt"]["path"]  # type: ignore[index,operator]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["binding"]["model"] = False
    write_json(receipt_path, receipt)
    row["receipt"]["sha256"] = sha_file(receipt_path)  # type: ignore[index]
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["contract_receipt_sha256"] = row["receipt"]["sha256"]  # type: ignore[index]
    write_json(manifest_path, manifest)
    row["run_manifest"]["sha256"] = sha_file(manifest_path)  # type: ignore[index]
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("receipt binding model must be integer 0" in error for error in result["errors"])


def test_run_manifest_model_rejects_json_bool(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["model"] = False
    write_json(manifest_path, manifest)
    row["run_manifest"]["sha256"] = sha_file(manifest_path)  # type: ignore[index]
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("run manifest model must be integer 0" in error for error in result["errors"])


def test_report_history_quality_and_server_identity_are_rejected(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    report_path = workspace / row["report"]["path"]  # type: ignore[index,operator]
    report_path.write_text(
        "<html><b>OtherServer (Build 6006)</b><table><tr><td>History Quality:</td><td><b>98%</b></td></tr></table></html>\n",
        encoding="utf-8",
    )
    row["report"]["sha256"] = sha_file(report_path)  # type: ignore[index]
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["report_sha256"] = row["report"]["sha256"]  # type: ignore[index]
    write_json(manifest_path, manifest)
    row["run_manifest"]["sha256"] = sha_file(manifest_path)  # type: ignore[index]
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("report History Quality must equal" in error for error in result["errors"])
    assert any("report server/build identity must contain exact contract server" in error for error in result["errors"])


def test_copied_manifest_external_local_run_dir_is_rejected(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD")
    manifest_path = workspace / row["run_manifest"]["path"]  # type: ignore[index,operator]
    copied_manifest_path = manifest_path.parent.parent / "copied_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["local_run_dir"] = str(manifest_path.parent)
    write_json(copied_manifest_path, manifest)
    row["run_manifest"] = {
        "path": str(copied_manifest_path.relative_to(workspace)),
        "sha256": sha_file(copied_manifest_path),
    }
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("run manifest parent must equal manifest local_run_dir" in error for error in result["errors"])


def test_partial_require_complete_fails(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    write_ledger(ledger, chain([header_row(contract_path, contract), symbol_row(workspace, contract, "XAUUSD")]))

    result = validate_contract(contract_path, require_complete=True)

    assert result["ok"] is False
    assert result["aggregate_ready"] is False
    assert any("aggregate incomplete" in error for error in result["errors"])


def test_nine_valid_synthetic_rows_complete_pass(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    rows = [header_row(contract_path, contract)] + [
        symbol_row(workspace, contract, symbol) for symbol in SUT.MANDATORY_SYMBOLS
    ]
    write_ledger(ledger, chain(rows))

    result = validate_contract(contract_path, require_complete=True)

    assert result["ok"] is True
    assert result["aggregate_ready"] is True
    assert result["missing"] == []


def test_duplicate_identical_journal_sync_lines_pass(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD", duplicate_identical_journal_line=True)
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is True
    assert result["missing"] == SUT.MANDATORY_SYMBOLS[1:]


def test_actual_to_after_frozen_cutoff_is_rejected(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    row = symbol_row(workspace, contract, "XAUUSD", actual_to="2026.08.01")
    write_ledger(ledger, chain([header_row(contract_path, contract), row]))

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any(
        "actual_to must equal the frozen requested_to cutoff" in error
        for error in result["errors"]
    )


def test_chain_tamper_is_rejected(tmp_path: Path) -> None:
    contract_path, contract, ledger = contract_fixture(tmp_path)
    workspace = SUT.WORKSPACE_ROOT
    rows = chain(
        [
            header_row(contract_path, contract),
            symbol_row(workspace, contract, "XAUUSD"),
            symbol_row(workspace, contract, "BTCUSD"),
        ]
    )
    rows[2]["prior_epoch_row_sha256"] = "F" * 64
    write_ledger(ledger, rows)

    result = validate_contract(contract_path)

    assert result["ok"] is False
    assert any("prior_epoch_row_sha256 must equal raw SHA256" in error for error in result["errors"])


def test_cli_reports_incomplete_success(tmp_path: Path) -> None:
    real_workspace = RESEARCH.parents[1]
    sandbox = real_workspace / "04. Memory/research/.data_epoch_cli_test"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True)
    try:
        charter = write_blob(sandbox / "charter.json", b'{"charter":"frozen"}\n')
        ledger = sandbox / "data_epoch_evidence.jsonl"
        contract = {
            "schema_version": "alphafactory_data_epoch_contract.v1",
            "record_type": "data_epoch_contract",
            "campaign_id": "CAMPAIGN-PTR-E01",
            "generation": 1,
            "generation_id": "T1",
            "charter": {
                "path": str(charter.relative_to(real_workspace)),
                "sha256": sha_file(charter),
            },
            "server": "FivePercentOnline-Real",
            "timeframe": "M5",
            "tester_model": 0,
            "requested_from": "1970.01.01",
            "availability_cutoff_utc": "2026-07-30T23:59:59Z",
            "history_quality": {"operator": "gt", "threshold_pct": 97.0},
            "no_skip": True,
            "mandatory_symbols": SUT.MANDATORY_SYMBOLS,
            "evidence_ledger_path": str(ledger.relative_to(real_workspace)),
        }
        contract_path = write_json(sandbox / "data_epoch_contract.json", contract)
        write_ledger(ledger, chain([header_row(contract_path, contract)]))

        result = subprocess.run(
            [sys.executable, "-X", "utf8", str(MODULE_PATH), str(contract_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    finally:
        shutil.rmtree(sandbox)

    assert result.returncode == 0, result.stderr
    assert "aggregate_ready=false" in result.stdout
