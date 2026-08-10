from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


RESEARCH = Path(__file__).resolve().parents[1]
EA_ROOT = RESEARCH.parent
MQL = EA_ROOT / "EA_SupertrendStateFlip.mq5"
COLLECTOR_PATH = RESEARCH / "collect_st004_mt5_artifacts.py"
COMPARATOR_PATH = RESEARCH / "compare_st003_mql5_parity.py"
COMPILE_RUNNER_PATH = RESEARCH / "run_st004_static_compile.py"
MT5_RUNNER_PATH = RESEARCH / "run_st004_mt5_parity.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collector = load_module("st004_collector_test", COLLECTOR_PATH)
comparator = load_module("st004_comparator_test", COMPARATOR_PATH)
compile_runner = load_module("st004_compile_runner_test", COMPILE_RUNNER_PATH)
mt5_runner = load_module("st004_mt5_runner_test", MT5_RUNNER_PATH)


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_frozen_csv(path: Path, rows: int = 29460) -> None:
    with path.open("w", encoding="ascii", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=collector.MQL_COLUMNS)
        writer.writeheader()
        for index in range(rows):
            raw = index < 690
            executable = index < 683
            direction = "LONG" if index < 339 else "SHORT" if index < 683 else ""
            writer.writerow(
                {
                    "schema_version": "st003_mql5_parity.v1",
                    "hypothesis_id": "HYP-ST-XAUUSD-H1-003",
                    "audit_run_id": "ST003-MT5-PARITY-001",
                    "source_epoch": 1_514_764_800 + index * 3600,
                    "time_server": "2018.01.01 00:00:00",
                    "atr10": "1",
                    "final_upper": "2",
                    "final_lower": "0",
                    "supertrend": "2",
                    "prior_state": "DOWN",
                    "state": "UP" if direction == "LONG" else "DOWN",
                    "raw_event": int(raw),
                    "next_source_epoch": 1_514_768_400 + index * 3600,
                    "exact_next": int(index < 683 or index >= 690),
                    "executable_event": int(executable),
                    "direction": direction,
                }
            )


def test_hyp004_source_adds_only_read_only_data_quality_witness_contract() -> None:
    text = MQL.read_text(encoding="utf-8")
    assert "bool EmitDataQualitySeriesProof()" in text
    assert "DATA_EPOCH_D0_SERIES_PROOF symbol=%s" in text
    assert "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)" in text
    assert "if(!EmitDataQualitySeriesProof())" in text
    assert text.index("if(!EmitDataQualitySeriesProof())") < text.index("g_current_bar_open=CurrentH1Open()")
    assert "CTrade" not in text and "OrderSend(" not in text and "trade.Buy(" not in text


def test_scripts_bind_current_hyp008_mql_source() -> None:
    expected = file_sha(MQL)
    assert expected == "580E2F6713ABA77597528127249CF5BBE0F2826FFF20AE10B36B73402B4A03AF"
    assert collector.MQL_SOURCE_SHA256 == expected
    assert comparator.MQL_SOURCE_SHA256 == expected
    assert mt5_runner.SOURCE_SHA256 == expected


def test_hyp004_comparator_requires_collection_authorized_nonrepaint_audit() -> None:
    text = COMPARATOR_PATH.read_text(encoding="utf-8")
    assert "require_collection_authority=True" in text
    assert 'expected_hypothesis = AUTHORITY_HYPOTHESIS_ID if require_collection_authority' in text
    assert 'expected_run = "ST008-MQL5-STATIC-001" if require_collection_authority' in text


def test_frozen_dependency_hashes_match_live_tools() -> None:
    alpha = comparator.ROOT / "02. AlphaFactory/alpha.ps1"
    quant = comparator.ROOT / "02. AlphaFactory/analysis/quant_analyzer.py"
    audit = comparator.ROOT / "02. AlphaFactory/tools/audit_mql5_nonrepaint.py"
    assert file_sha(alpha) == collector.ALPHA_PS1_SHA256 == mt5_runner.ALPHA_PS1_SHA256
    assert file_sha(quant) == comparator.QUANT_ANALYZER_SHA256
    assert file_sha(audit) == comparator.NONREPAINT_TOOL_SHA256


def test_exact_comparator_attempt_and_correctness_only_verdict_are_frozen() -> None:
    text = COMPARATOR_PATH.read_text(encoding="utf-8")
    assert comparator.COMPARATOR_ATTEMPT_ID == "ST008-COMPARATOR-001"
    assert '"verdict": "ENGINEERING_VALID_DIRECT_MQL5_MT5_PARITY_PASS"' in text
    assert "ECONOMIC_CHILD_AUTHORIZED" not in text
    assert 'validation.get("comparator_execution_authorized") is True' in text
    assert 'metrics.get("comparator_attempts_consumed") == 0' in text
    assert 'validation.get("artifact_collection_attempt_limit") == 1' in text


def test_comparator_binds_only_canonical_run_local_compile_artifacts() -> None:
    text = COMPARATOR_PATH.read_text(encoding="utf-8")
    assert 'args.compiled_ex5.resolve() != run_ex5_snapshot.resolve()' in text
    assert 'args.compile_log.resolve() != run_compile_log.resolve()' in text
    assert 'validation.get("reviewed_compiled_ex5_sha256")' not in text
    assert 'compiled EX5 must be the canonical run-local snapshot' in text
    assert 'compile log must be the canonical run-local compile artifact' in text


def test_collection_authorized_audit_requires_exact_sole_copytime_allowance(tmp_path: Path) -> None:
    canonical = comparator.ROOT / "03. EA Developer/EA_SupertrendStateFlip/EA_SupertrendStateFlip.mq5"
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    source = snapshot_root / "EA_SupertrendStateFlip.mq5"
    source.write_bytes(canonical.read_bytes())
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({"snapshot_root": str(snapshot_root), "source_snapshot": str(source)}) + "\n",
        encoding="utf-8",
    )
    line = next(
        index for index, value in enumerate(source.read_text(encoding="utf-8").splitlines(), 1)
        if "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)" in value
    )
    allowed = {
        "path": str(source.resolve()), "line": line,
        "rule": "collection_first_date_copytime", "function": "CopyTime",
        "disposition": "allowed_collection_provenance_read",
    }
    audit = {
        "schema_version": "alphafactory_nonrepaint_audit.v1", "status": "PASS",
        "hypothesis_id": "HYP-ST-XAUUSD-H1-008", "run_id": "ST008-MQL5-STATIC-001",
        "manifest_sha256": file_sha(manifest), "collection_authority_verified": True,
        "findings": [], "audited_files": [{"path": str(source), "sha256": file_sha(source)}],
        "allowed_new_bar_gates": [allowed],
    }
    path = tmp_path / "audit.json"
    path.write_text(json.dumps(audit), encoding="utf-8")
    comparator.validate_nonrepaint_audit(path, manifest, require_collection_authority=True)
    audit["audited_files"][0]["path"] = str(canonical)
    path.write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(ValueError, match="source binding mismatch"):
        comparator.validate_nonrepaint_audit(path, manifest, require_collection_authority=True)
    audit["audited_files"][0]["path"] = str(source)
    audit["allowed_new_bar_gates"].append(dict(allowed))
    path.write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(ValueError, match="allowlist mismatch"):
        comparator.validate_nonrepaint_audit(path, manifest, require_collection_authority=True)


def test_static_compile_runner_claims_before_alphafactory_and_seals_failure() -> None:
    text = COMPILE_RUNNER_PATH.read_text(encoding="utf-8")
    assert text.index('marker = OUTPUT_DIR / "attempt_started.json"') < text.index("subprocess.run(")
    assert '"02. AlphaFactory/alpha.ps1"' in text
    assert '"compile", "EA_SupertrendStateFlip"' in text
    assert '"same_id_retry_authorized": False' in text
    assert "write_exclusive(destination, raw)" in text


def test_mt5_runner_claims_before_alpha_and_terminally_consumes_failures() -> None:
    text = MT5_RUNNER_PATH.read_text(encoding="utf-8")
    assert text.index('marker = OUTPUT_DIR / "attempt_started.json"') < text.index("subprocess.run(")
    assert 'ATTEMPT_ID = "ST008-MT5-001"' in text
    assert '"status": "FAILED"' in text
    assert '"same_id_retry_authorized": False' in text
    assert "if common.exists()" in text
    assert '"-Model", "0"' in text and '"-From", "2005.01.01"' in text
    assert '"-TimeoutSec", "1800"' in text


def test_mt5_runner_maps_semantic_current_spread_to_empty_alpha_cli_token(tmp_path: Path) -> None:
    receipt = tmp_path / "contract.json"
    receipt.write_text("{}\n", encoding="utf-8")
    command = mt5_runner.build_alpha_command(receipt)
    spread_index = command.index("-Spread")
    assert command[spread_index + 1] == ""
    assert "current" not in command[spread_index + 1 : spread_index + 2]


def test_profile_none_omits_redundant_telemetry_override_but_ea_fails_closed() -> None:
    assert "InpEnableTelemetry" not in mt5_runner.EXACT_OVERRIDES
    assert "InpEnableTelemetry" not in collector.EXACT_OVERRIDES
    assert "InpEnableTelemetry" not in comparator.EXACT_OVERRIDES
    source = MQL.read_text(encoding="utf-8")
    assert "input bool   InpEnableTelemetry = false;" in source
    assert "if(!InpAuditOnly || InpEnableTelemetry" in source


def test_inception_state_advances_before_exact_design_only_persistence() -> None:
    source = MQL.read_text(encoding="utf-8")
    assert "SOURCE_START_TIME = D'2004.06.11 07:00:00'" in source
    assert "DESIGN_START_TIME = D'2018.01.01 02:00:00'" in source
    assert "DESIGN_END_TIME   = D'2023.01.01 02:00:00'" in source
    advance = "if(!AdvanceState(bars[index],prior_state))"
    persist = "if(bars[index].time>=DESIGN_START_TIME && bars[index].time<DESIGN_END_TIME)"
    assert source.index(advance) < source.index(persist)
    assert "g_parity_rows!=29460" in source
    assert "g_runtime_failed=true;" in source


def test_mt5_runner_registry_rejects_consumed_or_existing_common_file(tmp_path: Path) -> None:
    receipt = tmp_path / "contract.json"
    receipt.write_text("{}\n", encoding="utf-8")
    common = tmp_path / "ST003_MQL5_PARITY_001.csv"
    row = {
        "hypothesis_id": "HYP-ST-XAUUSD-H1-008", "state": "screened",
        "verdict": "FROZEN_ST008_MT5_PARITY_RUN_AUTHORIZED",
        "metrics": {"mt5_parity_attempts_consumed": 0},
        "validation": {
            "mt5_parity_run_authorized": True, "mt5_parity_attempt_id": "ST008-MT5-001",
            "mt5_parity_attempt_limit": 1, "reviewed_mt5_launcher_sha256": file_sha(MT5_RUNNER_PATH),
            "reviewed_mql_source_sha256": file_sha(MQL),
            "reviewed_alpha_ps1_sha256": mt5_runner.ALPHA_PS1_SHA256,
            "contract_receipt_sha256": file_sha(receipt), "frozen_common_file_path": str(common),
            "economics_authorized": False, "performance_metrics_authorized": False,
            "live_trading_authorized": False,
        },
    }
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    mt5_runner.validate_registry(registry, receipt)
    common.write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing overwrite/retry"):
        mt5_runner.validate_registry(registry, receipt)
    common.unlink()
    row["metrics"]["mt5_parity_attempts_consumed"] = 1
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unconsumed"):
        mt5_runner.validate_registry(registry, receipt)


def test_frozen_csv_validator_accepts_exact_counts(tmp_path: Path) -> None:
    path = tmp_path / "audit.csv"
    write_frozen_csv(path)
    counters = collector.validate_common_csv(
        path,
        collector.datetime.fromtimestamp(path.stat().st_ctime, tz=collector.timezone.utc),
        collector.datetime.fromtimestamp(path.stat().st_mtime, tz=collector.timezone.utc),
    )
    assert counters["rows"] == 29460
    assert counters["raw_events"] == 690
    assert counters["executable_events"] == 683
    assert counters["gap_rejected_events"] == 7
    assert counters["long_events"] == 339
    assert counters["short_events"] == 344


def test_frozen_csv_validator_rejects_missing_row(tmp_path: Path) -> None:
    path = tmp_path / "audit.csv"
    write_frozen_csv(path, rows=29459)
    stamp = collector.datetime.fromtimestamp(path.stat().st_mtime, tz=collector.timezone.utc)
    with pytest.raises(ValueError, match="row count mismatch"):
        collector.validate_common_csv(path, stamp, stamp)


def test_data_quality_journal_must_be_run_local_and_hash_bound(tmp_path: Path) -> None:
    journal = tmp_path / "logs" / "tester_journal_delta.log"
    journal.parent.mkdir()
    proof = (
        "DATA_EPOCH_D0_SERIES_PROOF symbol=XAUUSD m5_synchronized=1 m5_first_epoch=1086938100 "
        "m5_terminal_first_epoch=1086938100 m1_server_first_epoch=1086938100 "
        "m1_terminal_first_epoch=1086938100 m5_bars=100 terminal_maxbars=10000000 "
        "copytime_from_epoch=1086938100 copytime_count=1 copytime_result=1 "
        "copytime_first_epoch=1086938100 copytime_last_error=0\n"
    )
    journal.write_text(proof, encoding="utf-8")
    parsed = collector.SERIES_PROOF.search(proof)
    assert parsed
    numeric = {key: int(value) for key, value in parsed.groupdict().items() if key != "symbol"}
    contract = {"symbol": "XAUUSD"}
    manifest = {
        "data_quality_contract": contract,
        "data_quality_gate": {
            "contract": contract,
            "history_quality": 99.0,
            "coverage_class": "FULL_2018_PLUS",
            "journal_path": "logs/tester_journal_delta.log",
            "journal_sha256": file_sha(journal),
            "journal_bytes_read": journal.stat().st_size,
            "journal_files_read": 1,
            "journal_truncated": False,
            "exact_match_count": 1,
            "distinct_range_count": 1,
            "series_proof": {"symbol": "XAUUSD", **numeric},
        },
        "data_quality_journal_delta": {
            "path": "logs/tester_journal_delta.log",
            "sha256": file_sha(journal),
            "bytes_read": journal.stat().st_size,
            "files_read": 1,
            "truncated": False,
        }
    }
    assert collector.validate_data_quality_journal(manifest, tmp_path) == journal
    manifest["data_quality_gate"]["series_proof"]["copytime_result"] = 0
    with pytest.raises(ValueError, match="do not reconcile"):
        collector.validate_data_quality_journal(manifest, tmp_path)
    manifest["data_quality_gate"]["series_proof"]["copytime_result"] = 1
    manifest["data_quality_journal_delta"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="journal hash mismatch"):
        collector.validate_data_quality_journal(manifest, tmp_path)


def test_tester_journal_requires_one_clean_summary(tmp_path: Path) -> None:
    journal = tmp_path / "agent" / "tester.log"
    journal.parent.mkdir()
    journal.write_text(
        "ST003_SUMMARY|run=ST003-MT5-PARITY-001|reason=0|rows=29460|raw=690|"
        "executable=683|gaps=7|long=339|short=344|failed=false\n",
        encoding="utf-8",
    )
    stamp = collector.datetime.fromtimestamp(journal.stat().st_mtime, tz=collector.timezone.utc)
    selected, raw = collector.locate_tester_journal(tmp_path, stamp, stamp)
    assert selected == journal and raw == journal.read_bytes()
    journal.write_text(journal.read_text(encoding="utf-8") + "ST003_FATAL|unexpected\n", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid ST003 evidence"):
        collector.locate_tester_journal(tmp_path, stamp, stamp)


def test_collection_contract_receipt_is_exact_and_manifest_bound(tmp_path: Path) -> None:
    quality = {
        "history_quality": {"operator": "gt", "value": 97.0},
        "coverage_mode": "fixed_window", "availability_asof_utc": "2026-08-09T00:00:00Z",
        "requested_from": "2005.01.01", "requested_to": "2023.01.01",
        "require_tester_journal_bounds": True,
    }
    binding = {
        "hypothesis_id": "HYP-ST-XAUUSD-H1-008", "run_role": "control",
        "ea_name": "EA_SupertrendStateFlip", "symbol": "XAUUSD", "period": "H1",
        "from": "2005.01.01", "to": "2023.01.01", "model": 0,
        "execution_mode": 0, "fixed_delay_ms": 0, "overrides": collector.EXACT_OVERRIDES,
        "telemetry_tier": "off", "telemetry_profile": "none", "deposit": 10000,
        "leverage": 100, "spread": "current", "required_sidecars": [],
        "indicator_dependencies": [], "data_quality_contract": quality,
    }
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "hypothesis_id": "HYP-ST-XAUUSD-H1-008", "binding": binding,
    }
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    manifest = {"contract_receipt_sha256": file_sha(path)}
    collector.validate_contract_receipt(path, manifest)
    receipt["authority"] = "UNAUTHORIZED"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    manifest["contract_receipt_sha256"] = file_sha(path)
    with pytest.raises(ValueError, match="receipt mismatch"):
        collector.validate_contract_receipt(path, manifest)


def test_collector_registry_is_fail_closed_on_economic_authority(tmp_path: Path) -> None:
    row = {
        "hypothesis_id": "HYP-ST-XAUUSD-H1-008",
        "state": "screened",
        "verdict": "FROZEN_ST008_MT5_PARITY_RUN_AUTHORIZED",
        "metrics": {"mt5_parity_attempts_consumed": 0, "artifact_collection_attempts_consumed": 0},
        "validation": {
            "parity_target_hypothesis_id": "HYP-ST-XAUUSD-H1-003",
            "mt5_parity_run_authorized": True,
            "mt5_parity_attempt_id": "ST008-MT5-001",
            "mt5_parity_attempt_limit": 1,
            "artifact_collection_authorized": True,
            "artifact_collection_attempt_id": "ST008-ARTIFACT-COLLECT-001",
            "artifact_collection_attempt_limit": 1,
            "reviewed_artifact_collector_sha256": file_sha(COLLECTOR_PATH),
            "reviewed_mql_source_sha256": file_sha(MQL),
            "run_compile_authorized": True,
            "static_compile_pass": False,
            "reviewed_alpha_ps1_sha256": collector.ALPHA_PS1_SHA256,
            "frozen_common_file_name": "ST003_MQL5_PARITY_001.csv",
            "performance_metrics_authorized": False,
            "economics_authorized": False,
            "live_trading_authorized": False,
        },
    }
    registry = tmp_path / "registry.jsonl"
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    collector.validate_registry(registry)
    row["validation"]["artifact_collection_attempt_limit"] = 2
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="collect_limit"):
        collector.validate_registry(registry)
    row["validation"]["artifact_collection_attempt_limit"] = 1
    row["validation"]["economics_authorized"] = True
    registry.write_text(json.dumps(row) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="no_economics"):
        collector.validate_registry(registry)


def test_exclusive_writer_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "sealed.bin"
    collector.write_exclusive(path, b"first")
    with pytest.raises(FileExistsError):
        collector.write_exclusive(path, b"second")
    assert path.read_bytes() == b"first"
