from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-018"
PARENT_ID = "HYP-STBS-XAUUSD-M15-017"
INNER_ID = "HYP-STBS-XAUUSD-M15-016"
ATTEMPT_ID = "STBS018-COMPARATOR-001"
EA_NAME = "EA_SupertrendBurstScalperTradeV5"
REGISTRY = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
ATTEMPT_ROOT = ROOT / "02. AlphaFactory/runtime/comparator_attempts" / HYPOTHESIS_ID / ATTEMPT_ID
INVENTORY_ROOT = ROOT / "02. AlphaFactory/runtime/model0_audit_attempts/HYP-STBS-XAUUSD-M15-017/STBS017-MODEL0-AUDIT-001/failed_run_inventory/20260810_002304"
HYP017_START = ROOT / "02. AlphaFactory/runtime/model0_audit_attempts/HYP-STBS-XAUUSD-M15-017/STBS017-MODEL0-AUDIT-001/attempt_started.json"
HYP017_TERMINAL = ROOT / "02. AlphaFactory/runtime/model0_audit_attempts/HYP-STBS-XAUUSD-M15-017/STBS017-MODEL0-AUDIT-001/attempt_terminal.json"
HYP017_TASK = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV5/research/preflight/HYP-STBS-XAUUSD-M15-017/V1/task_packet.control.json"
HYP017_RECEIPT = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV5/research/preflight/HYP-STBS-XAUUSD-M15-017/V1/contract_receipt.control.json"
HYP013_TASK = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV3/research/preflight/HYP-STBS-XAUUSD-M15-013/V1/task_packet.control.json"
HYP013_PREREG = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV3/research/HYP-STBS-XAUUSD-M15-013_MODEL0_TRAIN_PREREG.md"
HYP013_COST = ROOT / "03. EA Developer/EA_SupertrendBurstScalperTradeV3/research/HYP-STBS-XAUUSD-M15-013_RESEARCH_COST_SOURCE_MANIFEST.json"
QUANT = ROOT / "02. AlphaFactory/runtime/model0_audit_attempts/HYP-STBS-XAUUSD-M15-017/STBS017-MODEL0-AUDIT-001/static_review/quant_analyzer.py"
RUN_COMPILE_LOG = ROOT / "02. AlphaFactory/runtime/model0_audit_attempts/HYP-STBS-XAUUSD-M15-017/STBS017-MODEL0-AUDIT-001/run_evidence/compile/EA_SupertrendBurstScalperTradeV5.log"
ORIGINAL_RUN_ROOT = ROOT / "02. AlphaFactory/runs/EA_SupertrendBurstScalperTradeV5/20260810_002304"
PREREG = Path(__file__).with_name("HYP-STBS-XAUUSD-M15-018_SEALED_ZERO_TRADE_COMPARATOR_PREREG.md")
TEST = Path(__file__).with_name("tests") / "test_stbs018_sealed_zero_trade_comparator.py"

HYP017_TERMINAL_ROW_SHA = "23F36E10EDB42BD1A2F4134194EEBDAB35239788B3A25BD9C56AE704699E3726"
DATA_SHA = "B326D511C805C7998DF1C2FC540770B6EC3054D0D4BCBB41A5A4E3C2E4239D25"
BROKER_SHA = "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54"
SERVER_SHA = "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0"
ACCOUNT_SHA = "0A603E7B316F58B39FEA0A1710FE6F250E544909DA2B91967C93AD984317A073"
SOURCE_SHA = "3822EED82C8D484CE8010A496767271DED20528158D68509B46EF934B043D918"
EX5_SHA = "832712C5A392400B46BB2B44F1273B05DDEDD25793DA7CB020B844EDD003E30B"
CONFIG_SHA = "E2F2C56684CF726C5A100D779AE0AFDA074E8D0954A888336A3381AE57461053"
REPORT_SHA = "8AC7C0005D02BFF4E963049107ED1AA950BFFA3205E906EB1781D386866286DB"
JOURNAL_SHA = "3284EA885A965123FB0BDA1B51F126524F014C1ABD95D43BDCF66E222A9361CE"
MANIFEST_SHA = "8829191F4957ACF162F46B90EA1886AF26BB26B6271CC93638CE62E89319CFE7"
RECEIPT_SHA = "96914D0FFD672876ED09D67A012CBA11E6FC02C46CA9CAB8130238CFE9456E8D"
START_SHA = "1A065A5E168095755300CF5D25D9526E9DB10B65525F542C6671A55C3B05D643"
TERMINAL_SHA = "97228B36FA2E7A1511AC113DD43212C2382BB3B72724B2D1CDDE2D58D60416DD"
QUANT_SHA = "A7F93E8DC35A2FC7A273419500E7B41DF742F828613C48EDA3D5C766C042616B"
HYP013_TASK_SHA = "DE25AE28B29087901514B1ABA067A00B8DF05F7F4288CF93D79188A730255DE9"
HYP013_PREREG_SHA = "EF3DB79293438056A1634723E5F2DAE7183E093EF33A6F84CC6E061AC4AFE1CA"
HYP013_COST_SHA = "77A7D738AD945AB869CC1682110FF64C1DC3D8827039F68F937392A793C7CAF8"
HYP013_AUTHORITY_ROW_SHA = "5A957E169AEF9DF420534FE4A242E0ABC81F58FB2F80070AED4A4148047FD837"
RUN_COMPILE_LOG_SHA = "886A9883DEDC54D2FC8236B8075A72FD1CDF61F8C407DE32E8402E95110300E6"
OVERRIDES = "InpAuditOnly=true;InpHypothesisId=HYP-STBS-XAUUSD-M15-016;InpMagic=5604116;InpMaxNewPositionMarginPct=5.0;InpMinProjectedMarginLevelPct=2000.0;InpMoneyFreeEquityFloorPct=1.0;InpMoneyHeadroomReserveFactor=0.20;InpPercentStopoutHeadroomFactor=1.25;InpVariantTag=STBS_H1_FLIP_M15_BURST_AUDIT_V5_ACCOUNT_SAFE"
ORDER_COLSPANS = [1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]
REQUIRED_TRUE_PERMISSIONS = {"artifact_collection_authorized", "comparator_execution_authorized"}
REQUIRED_FALSE_PERMISSIONS = {
    "packet_build_authorized", "mt5_audit_run_authorized", "mt5_authorized",
    "model0_authorized", "model0_data_acquisition_authorized", "model0_performance_authorized",
    "model4_authorized", "model4_data_acquisition_authorized", "model4_performance_authorized",
    "source_run_authorized", "compile_authorized", "run_compile_authorized",
    "mql5_compile_authorized", "standalone_compile_authorized", "trade_api_authorized",
    "performance_metrics_authorized", "outcome_prices_authorized", "post_event_ohlc_authorized",
    "visual_mode_authorized", "network_authorized", "paid_requests_authorized",
    "economics_authorized", "optimization_authorized", "validation_authorized",
    "holdout_authorized", "research_validation_access_authorized",
    "research_holdout_access_authorized", "validation_access_authorized",
    "holdout_access_authorized", "research_falsification_authorized",
    "economic_validity_authorized", "promotion_eligible", "paper_trading_authorized",
    "live_trading_authorized", "market_edge_claim_authorized", "same_id_retry_authorized",
    "registry_mutation_allowed",
}
ZERO_METRICS = {
    "mt5_audit_attempts_consumed": 0, "run_compile_attempts_consumed": 0,
    "model0_runs": 0, "mt5_launches": 0, "orders_executed": 0,
    "trades_simulated": 0, "returns_computed": 0, "performance_trials_executed": 0,
    "economics_executed": False, "research_validation_opened": False,
    "research_holdout_opened": False,
}
EXPECTED_INVENTORY_FILES = {
    "analysis/enhanced_summary.json", "build/report.html", "config/config.ini",
    "config/overrides.txt", "config/run_manifest.json", "config.ini",
    "logs/tester_journal_delta.log", "overrides.txt", "report.html", "run_manifest.json",
    "snapshot/build/EA_SupertrendBurstScalperTradeV5.ex5",
    "snapshot/config/config.ini", "snapshot/source/EA_SupertrendBurstScalperTradeV5.mq5",
}


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def strict_json(raw: bytes, label: str) -> object:
    def reject(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RuntimeError(f"{label} duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=reject, parse_constant=lambda value: (_ for _ in ()).throw(RuntimeError(f"{label} nonfinite JSON value: {value}")))
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"{label} invalid JSON") from exc


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def exclusive(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def claim() -> tuple[Path, str]:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    path = ATTEMPT_ROOT / "attempt_started.json"
    raw = canonical({"schema_version": "stbs018_comparator_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": now(), "same_id_retry_authorized": False})
    exclusive(path, raw)
    return path, sha256_bytes(raw)


def registry_rows(raw_registry: bytes) -> list[tuple[dict, str, bytes]]:
    result = []
    for raw in raw_registry.splitlines():
        row = strict_json(raw, "registry row")
        if not isinstance(row, dict):
            raise RuntimeError("registry row is not an object")
        result.append((row, sha256_bytes(raw), raw))
    return result


def validate_authority_row(row: dict) -> None:
    v, m = row.get("validation", {}), row.get("metrics", {})
    required = {
        "authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "comparator_execution_authorized": True,
        "comparator_attempt_id": ATTEMPT_ID,
        "comparator_attempt_limit": 1,
        "parent_hyp017_terminal_row_sha256": HYP017_TERMINAL_ROW_SHA,
        "expected_data_fingerprint": DATA_SHA,
        "run_manifest_path": str(INVENTORY_ROOT.relative_to(ROOT) / "run_manifest.json").replace("\\", "/"),
        "run_manifest_sha256": MANIFEST_SHA,
        "tester_report_path": str(INVENTORY_ROOT.relative_to(ROOT) / "report.html").replace("\\", "/"),
        "tester_report_sha256": REPORT_SHA,
        "tester_journal_path": str(INVENTORY_ROOT.relative_to(ROOT) / "logs/tester_journal_delta.log").replace("\\", "/"),
        "tester_journal_sha256": JOURNAL_SHA,
        "source_snapshot_sha256": SOURCE_SHA,
        "ex5_snapshot_sha256": EX5_SHA,
        "config_snapshot_sha256": CONFIG_SHA,
        "hyp017_attempt_started_sha256": START_SHA,
        "hyp017_attempt_terminal_sha256": TERMINAL_SHA,
        "hyp017_contract_receipt_sha256": RECEIPT_SHA,
        "hyp013_task_packet_sha256": HYP013_TASK_SHA,
        "hyp013_prereg_sha256": HYP013_PREREG_SHA,
        "hyp013_cost_manifest_sha256": HYP013_COST_SHA,
        "reviewed_quant_analyzer_sha256": QUANT_SHA,
        "hyp013_preoutcome_authority_row_sha256": HYP013_AUTHORITY_ROW_SHA,
        "run_compile_log_sha256": RUN_COMPILE_LOG_SHA,
    }
    for key, value in required.items():
        if v.get(key) != value:
            raise RuntimeError(f"authority {key} mismatch")
    if m.get("comparator_attempt_limit") != 1 or m.get("comparator_attempts_consumed") != 0:
        raise RuntimeError("comparator attempt counters mismatch")
    for key, value in ZERO_METRICS.items():
        if m.get(key) != value:
            raise RuntimeError(f"authority metric mismatch: {key}")
    if row.get("state") != "screened" or row.get("evidence_contract_kind") != "data_acquisition":
        raise RuntimeError("HYP018 authority state/contract mismatch")
    for key in REQUIRED_TRUE_PERMISSIONS:
        if v.get(key) is not True:
            raise RuntimeError(f"authority required-true permission mismatch: {key}")
    for key in REQUIRED_FALSE_PERMISSIONS:
        if v.get(key) is not False:
            raise RuntimeError(f"authority required-false permission mismatch: {key}")


def authority() -> tuple[dict, str, str, bytes, bytes, bytes]:
    raw_registry = REGISTRY.read_bytes()
    rows = registry_rows(raw_registry)
    parent = [(row, digest, raw) for row, digest, raw in rows if row.get("hypothesis_id") == PARENT_ID]
    mine = [(row, digest, raw) for row, digest, raw in rows if row.get("hypothesis_id") == HYPOTHESIS_ID]
    hyp013 = [(row, digest, raw) for row, digest, raw in rows if row.get("hypothesis_id") == "HYP-STBS-XAUUSD-M15-013" and digest == HYP013_AUTHORITY_ROW_SHA]
    if not parent or parent[-1][0].get("state") != "killed" or parent[-1][1] != HYP017_TERMINAL_ROW_SHA:
        raise RuntimeError("terminal HYP017 row mismatch")
    if not mine:
        raise RuntimeError("HYP018 authority absent")
    if len(hyp013) != 1:
        raise RuntimeError("HYP013 pre-outcome authority row mismatch")
    row, row_sha, row_raw = mine[-1]
    validate_authority_row(row)
    return row, row_sha, sha256_bytes(raw_registry), raw_registry, row_raw, hyp013[0][2]


def capture(label: str, path: Path, expected: str) -> tuple[bytes, dict]:
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    if digest != expected:
        raise RuntimeError(f"{label} hash mismatch")
    target = ATTEMPT_ROOT / "captured" / label
    exclusive(target, raw)
    if sha256_file(target) != digest:
        raise RuntimeError(f"{label} capture mismatch")
    return raw, {"source_path": str(path), "captured_path": str(target), "sha256": digest, "length": len(raw)}


def capture_raw(label: str, raw: bytes, source_label: str, expected: str) -> tuple[bytes, dict]:
    digest = sha256_bytes(raw)
    if digest != expected:
        raise RuntimeError(f"{label} raw hash mismatch")
    target = ATTEMPT_ROOT / "captured" / label
    exclusive(target, raw)
    if sha256_file(target) != digest:
        raise RuntimeError(f"{label} raw capture mismatch")
    return raw, {"source_path": source_label, "captured_path": str(target), "sha256": digest, "length": len(raw)}


def parse_kv(line: str, marker: str) -> dict[str, str]:
    payload = line.split(marker, 1)[1].strip()
    if not payload:
        raise RuntimeError(f"empty {marker} payload")
    result: dict[str, str] = {}
    for part in payload.split("|"):
        if not part or "=" not in part:
            raise RuntimeError(f"bare {marker} fragment")
        key, value = part.split("=", 1)
        if not key or not value or key in result:
            raise RuntimeError(f"empty/duplicate {marker} field")
        result[key] = value
    return result


def analyze_journal(text: str) -> dict:
    for marker in ("STBS_FATAL|", "STBS_ENTRY_REQUEST|", "STBS_CLOSE_REQUEST|", "STBS_CANCEL_REQUEST|", "STBS_DEAL|"):
        if marker in text:
            raise RuntimeError(f"forbidden marker {marker}")
    summaries = [parse_kv(line, "STBS_SUMMARY|") for line in text.splitlines() if "STBS_SUMMARY|" in line]
    if len(summaries) != 2 or summaries[0] != summaries[1]:
        raise RuntimeError("summary multiplicity/identity mismatch")
    expected = {"hypothesis": INNER_ID, "reason": "1", "raw": "690", "executable": "683", "gaps": "7", "long": "339", "short": "344", "atr_ready": "683", "geometry_ready": "683", "margin_ready": "683", "margin_rejects": "0", "margin_emergencies": "0", "forced_stopouts": "0", "entries": "0", "entry_rejects": "0", "closes": "0", "lifecycle_open_rows": "0", "lifecycle_final_close_rows": "0", "lifecycle_positions_opened": "0", "lifecycle_positions_final_closed": "0", "exec_state": "0", "exit_intent": "0", "failed": "false"}
    if summaries[0] != expected:
        raise RuntimeError("summary allowlist/value mismatch")
    signals: dict[str, dict[str, str]] = {}
    multiplicity: dict[str, int] = {}
    for line in text.splitlines():
        if "STBS_SIGNAL|" not in line:
            continue
        item = parse_kv(line, "STBS_SIGNAL|")
        epoch = item.get("source_epoch", "")
        if not epoch or (epoch in signals and signals[epoch] != item):
            raise RuntimeError("signal identity mismatch")
        signals[epoch] = item
        multiplicity[epoch] = multiplicity.get(epoch, 0) + 1
    if len(signals) != 690 or set(multiplicity.values()) != {2}:
        raise RuntimeError("signal count/multiplicity mismatch")
    exact = [x for x in signals.values() if x.get("exact_next") == "true"]
    gaps = [x for x in signals.values() if x.get("exact_next") == "false"]
    if len(exact) != 683 or len(gaps) != 7:
        raise RuntimeError("exact/gap count mismatch")
    for item in exact:
        if set(item) != {"source_epoch", "decision_epoch", "direction", "exact_next", "atr_ready", "geometry_ready", "margin_ready", "volume", "projected_free", "required_free", "audit"}:
            raise RuntimeError("exact signal allowlist mismatch")
        if any(item[k] != "true" for k in ("atr_ready", "geometry_ready", "margin_ready", "audit")):
            raise RuntimeError("readiness mismatch")
        source, decision = int(item["source_epoch"]), int(item["decision_epoch"])
        values = [float(item[k]) for k in ("volume", "projected_free", "required_free")]
        if decision != source + 3600 or not all(math.isfinite(x) for x in values):
            raise RuntimeError("clock/numeric mismatch")
        if values[0] <= 0 or abs(values[2] - 93600.0) > 1e-6 or values[1] < values[2]:
            raise RuntimeError("margin evidence mismatch")
    for item in gaps:
        if set(item) != {"source_epoch", "decision_epoch", "direction", "exact_next", "consumed", "audit"} or item.get("consumed") != "true" or item.get("audit") != "true":
            raise RuntimeError("gap evidence mismatch")
    if sum(x.get("direction") == "LONG" for x in exact) != 339 or sum(x.get("direction") == "SHORT" for x in exact) != 344:
        raise RuntimeError("direction mismatch")
    return {"summary_multiplicity": 2, "signal_rows": 1380, "unique_signals": 690, "executable": 683, "gaps": 7, "long": 339, "short": 344, "atr_ready": 683, "geometry_ready": 683, "margin_ready": 683, "orders": 0, "trades": 0, "runtime_failed": False, "reason": 1}


def parse_colspans(cells: list[tuple[str, str]]) -> list[int] | None:
    result = []
    for attrs, _ in cells:
        names = re.findall(r"\bcolspan\b", attrs, re.I)
        if not names:
            result.append(1); continue
        if len(names) != 1:
            return None
        match = re.search(r"\bcolspan\s*=\s*(?:\"([0-9]+)\"|'([0-9]+)'|([0-9]+))(?=\s|$)", attrs, re.I)
        if not match:
            return None
        value = int(next(x for x in match.groups() if x is not None))
        if value <= 0:
            return None
        result.append(value)
    return result


def orders_empty(html: str) -> bool:
    start = re.search(r"<b>\s*(?:Orders|C\u00e1c\s+l\u1ec7nh\s+\u0111\u1eb7t)\s*</b>", html, re.I)
    end = re.search(r"<b>\s*Deals\s*</b>", html[start.end():], re.I) if start else None
    if not start or not end:
        return False
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html[start.end():start.end()+end.start()], re.I | re.S)
    if len(rows) != 2:
        return False
    td_re = re.compile(r"<td([^>]*)>(.*?)</td>", re.I | re.S)
    header, spacer = td_re.findall(rows[0]), td_re.findall(rows[1])
    return len(header) == 11 and parse_colspans(header) == ORDER_COLSPANS and all(re.fullmatch(r"\s*<b>.*?</b>\s*", x, re.I | re.S) for _, x in header) and len(spacer) == 1 and parse_colspans(spacer) == [1] and re.sub(r"<[^>]+>", "", spacer[0][1]).strip() == ""


def analyze(captured: dict[str, bytes]) -> dict:
    manifest = strict_json(captured["run_manifest.json"], "run manifest")
    if not isinstance(manifest, dict):
        raise RuntimeError("run manifest root mismatch")
    expected = {"schema_version": "alphafactory_run_manifest.v2", "hypothesis_id": PARENT_ID, "run_id": "20260810_002304", "run_role": "control", "ea_name": EA_NAME, "symbol": "XAUUSD", "period": "M15", "from": "2005.01.01", "to": "2023.01.01", "model": 0, "execution_mode": 0, "fixed_delay_ms": 0, "timeout_sec": 900, "overrides": OVERRIDES, "deposit": 100000, "leverage": 100, "spread": "current", "telemetry_tier": "off", "telemetry_profile": "none", "visual_mode": False, "source_sha256": SOURCE_SHA, "ex5_sha256": EX5_SHA, "tester_ex5_sha256": EX5_SHA, "config_sha256": CONFIG_SHA, "report_sha256": REPORT_SHA, "contract_receipt_sha256": RECEIPT_SHA, "data_fingerprint": DATA_SHA, "broker_fingerprint": BROKER_SHA, "server_fingerprint": SERVER_SHA, "account_fingerprint": ACCOUNT_SHA}
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"manifest {key} mismatch")
    exact_paths = {
        "report_path": ORIGINAL_RUN_ROOT / "report.html",
        "source_snapshot": ORIGINAL_RUN_ROOT / "snapshot/source/EA_SupertrendBurstScalperTradeV5.mq5",
        "ex5_snapshot": ORIGINAL_RUN_ROOT / "snapshot/build/EA_SupertrendBurstScalperTradeV5.ex5",
        "config_snapshot": ORIGINAL_RUN_ROOT / "snapshot/config/config.ini",
    }
    for key, path in exact_paths.items():
        if manifest.get(key) != str(path):
            raise RuntimeError(f"manifest canonical {key} mismatch")
    if manifest.get("sidecars") != [{"path": "logs/tester_journal_delta.log", "sha256": JOURNAL_SHA, "length": 428908, "row_count": None}]:
        raise RuntimeError("manifest sidecar allowlist mismatch")
    dqj = manifest.get("data_quality_journal_delta", {})
    basis = manifest.get("data_quality_fingerprint_basis", {})
    contract, proof = basis.get("contract", {}), basis.get("series_proof", {})
    exact_proof = {"symbol": "XAUUSD", "m5_synchronized": 1, "m5_first_epoch": 1086938100, "m5_terminal_first_epoch": 1086938100, "m1_server_first_epoch": 1086938100, "m1_terminal_first_epoch": 1086938100, "m5_bars": 28408, "terminal_maxbars": 10000000, "copytime_from_epoch": 1086938100, "copytime_count": 1, "copytime_result": 1, "copytime_first_epoch": 1086938100, "copytime_last_error": 0}
    if not (dqj.get("path") == "logs/tester_journal_delta.log" and dqj.get("sha256") == JOURNAL_SHA and dqj.get("bytes_read") == 857818 and dqj.get("files_read") == 3 and dqj.get("truncated") is False and basis.get("base_data_fingerprint") == DATA_SHA and basis.get("history_quality") == 98 and basis.get("actual_from") == "2004.06.11" and basis.get("actual_to") == "2026.07.30" and basis.get("coverage_class") == "FULL_2018_PLUS" and basis.get("journal_sha256") == JOURNAL_SHA and basis.get("journal_bytes_read") == 857818 and basis.get("journal_files_read") == 3 and basis.get("journal_truncated") is False and basis.get("exact_match_count") == 2 and basis.get("distinct_range_count") == 1 and contract.get("requested_from") == "2005.01.01" and contract.get("requested_to") == "2023.01.01" and contract.get("coverage_mode") == "fixed_window" and contract.get("require_tester_journal_bounds") is True and proof == exact_proof):
        raise RuntimeError("data-quality provenance mismatch")
    task = strict_json(captured["hyp013_task.json"], "HYP013 task")
    h13 = strict_json(captured["hyp013_authority_row.json"], "HYP013 authority row")
    h17_start = strict_json(captured["hyp017_start.json"], "HYP017 start")
    h17_terminal = strict_json(captured["hyp017_terminal.json"], "HYP017 terminal")
    if not all(isinstance(x, dict) for x in (task, h13, h17_start, h17_terminal)):
        raise RuntimeError("provenance root mismatch")
    if task.get("data_fingerprint") != DATA_SHA:
        raise RuntimeError("HYP013 pre-outcome data provenance mismatch")
    h13v = h13.get("validation", {})
    if not (h13.get("hypothesis_id") == "HYP-STBS-XAUUSD-M15-013" and h13.get("state") == "screened" and h13.get("verdict") == "SCREENED_STBS013_ONE_SHOT_PACKET_BOUND_MODEL0_BASELINE_AUTHORIZED" and h13v.get("task_packet_sha256") == HYP013_TASK_SHA and h13v.get("data_fingerprint") == DATA_SHA and h13v.get("cost_source_manifest_sha256") == HYP013_COST_SHA):
        raise RuntimeError("HYP013 authority provenance mismatch")
    if dt.datetime.fromisoformat(h13["updated_at_utc"].replace("Z", "+00:00")) >= dt.datetime.fromisoformat(h17_start["started_at_utc"].replace("Z", "+00:00")):
        raise RuntimeError("HYP013 fingerprint provenance is not pre-HYP017")
    if not (h17_terminal.get("status") == "FAILED" and h17_terminal.get("error") == "run manifest data_fingerprint mismatch" and h17_terminal.get("attempt_started_sha256") == START_SHA and h17_terminal.get("contract_receipt_sha256") == RECEIPT_SHA):
        raise RuntimeError("HYP017 terminal chain mismatch")
    journal = analyze_journal(captured["journal.log"].decode("utf-8", errors="replace"))
    spec = importlib.util.spec_from_file_location("stbs018_quant", ATTEMPT_ROOT / "captured" / "quant_analyzer.py")
    if not spec or not spec.loader:
        raise RuntimeError("quant parser import failed")
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
    report_path = ATTEMPT_ROOT / "captured" / "report.html"
    html = module._decode_report_bytes(captured["report.html"])
    if not orders_empty(html):
        raise RuntimeError("Orders section is not exact-empty")
    deals = module.parse_deals(report_path)
    if len(deals) != 1:
        raise RuntimeError("funding-row count mismatch")
    d = deals[0]
    if not (d.time == dt.datetime(2005,1,1) and d.deal_id == 1 and d.side == "balance" and d.symbol == "" and d.direction == "" and d.comment == "" and d.volume == d.price == d.commission == d.swap == 0.0 and d.order_id is None and d.profit == d.balance == 100000.0 and not module.deals_to_trades(deals)):
        raise RuntimeError("funding/zero-trade report mismatch")
    return {"verdict": "PASS_ENGINEERING_ZERO_TRADE_MODEL0_AUDIT", "manifest_sha256": MANIFEST_SHA, "report_sha256": REPORT_SHA, "journal_sha256": JOURNAL_SHA, "data_fingerprint": DATA_SHA, **journal}


def execute() -> dict:
    start_path, start_sha = claim()
    context: dict[str, object] = {}
    try:
        row, row_sha, registry_sha, registry_raw, authority_raw, hyp013_raw = authority()
        context.update({"authority_row_sha256": row_sha, "registry_sha256_at_claim": registry_sha})
        actual_inventory = {path.relative_to(INVENTORY_ROOT).as_posix() for path in INVENTORY_ROOT.rglob("*") if path.is_file()}
        if actual_inventory != EXPECTED_INVENTORY_FILES:
            raise RuntimeError("failed-run inventory file-set mismatch")
        bindings = {
            "run_manifest.json": (INVENTORY_ROOT / "run_manifest.json", MANIFEST_SHA),
            "report.html": (INVENTORY_ROOT / "report.html", REPORT_SHA),
            "journal.log": (INVENTORY_ROOT / "logs/tester_journal_delta.log", JOURNAL_SHA),
            "source.mq5": (INVENTORY_ROOT / "snapshot/source/EA_SupertrendBurstScalperTradeV5.mq5", SOURCE_SHA),
            "ea.ex5": (INVENTORY_ROOT / "snapshot/build/EA_SupertrendBurstScalperTradeV5.ex5", EX5_SHA),
            "config.ini": (INVENTORY_ROOT / "snapshot/config/config.ini", CONFIG_SHA),
            "hyp017_start.json": (HYP017_START, START_SHA), "hyp017_terminal.json": (HYP017_TERMINAL, TERMINAL_SHA),
            "hyp017_task.json": (HYP017_TASK, "52F75B8CA1A909DEFB6CDD3C339AF6023A1FE70D43EED33B170AFA44DEECBD1F"),
            "hyp017_receipt.json": (HYP017_RECEIPT, RECEIPT_SHA), "quant_analyzer.py": (QUANT, QUANT_SHA),
            "hyp013_task.json": (HYP013_TASK, HYP013_TASK_SHA), "hyp013_prereg.md": (HYP013_PREREG, HYP013_PREREG_SHA), "hyp013_cost.json": (HYP013_COST, HYP013_COST_SHA),
            "run_compile.log": (RUN_COMPILE_LOG, RUN_COMPILE_LOG_SHA),
            "comparator.py": (Path(__file__), row["validation"].get("reviewed_comparator_sha256", "")),
            "prereg.md": (PREREG, row["validation"].get("reviewed_prereg_sha256", "")),
            "test.py": (TEST, row["validation"].get("reviewed_test_sha256", "")),
        }
        captures, evidence = {}, {}
        for label, (path, digest) in bindings.items():
            captures[label], evidence[label] = capture(label, path, digest)
        captures["registry_snapshot.jsonl"], evidence["registry_snapshot.jsonl"] = capture_raw("registry_snapshot.jsonl", registry_raw, str(REGISTRY), registry_sha)
        captures["authority_row.json"], evidence["authority_row.json"] = capture_raw("authority_row.json", authority_raw, f"{REGISTRY}#latest-{HYPOTHESIS_ID}", row_sha)
        captures["hyp013_authority_row.json"], evidence["hyp013_authority_row.json"] = capture_raw("hyp013_authority_row.json", hyp013_raw, f"{REGISTRY}#sha256-{HYP013_AUTHORITY_ROW_SHA}", HYP013_AUTHORITY_ROW_SHA)
        if evidence["journal.log"]["length"] != 428908:
            raise RuntimeError("journal captured-size mismatch")
        compile_text = captures["run_compile.log"].decode("utf-16" if captures["run_compile.log"].startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig", errors="strict")
        if len(re.findall(r"(?m)^Result:\s*0 errors,\s*0 warnings(?:,.*)?\s*$", compile_text)) != 1:
            raise RuntimeError("run compile log is not exact 0E/0W")
        first = analyze(captures); second = analyze(captures)
        if canonical(first) != canonical(second):
            raise RuntimeError("deterministic replay mismatch")
        for label, meta in evidence.items():
            if sha256_file(Path(meta["captured_path"])) != meta["sha256"]:
                raise RuntimeError(f"captured {label} drift")
        report_path = ATTEMPT_ROOT / "comparison_report.json"
        exclusive(report_path, canonical(first)); report_sha = sha256_file(report_path)
        receipt = {"schema_version": "stbs018_comparator_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "created_at_utc": now(), "authority_row_sha256": row_sha, "registry_sha256_at_claim": registry_sha, "attempt_started_path": str(start_path), "attempt_started_sha256": start_sha, "comparison_report_path": str(report_path), "comparison_report_sha256": report_sha, "evidence": evidence, "result": first, "deterministic_replay": True, "mt5_launched": False, "compile_executed": False, "source_data_opened": False, "orders": 0, "trades": 0, "outcomes_read": 0, "returns": 0, "pf_computed": False, "economics_evaluated": False, "optimization_executed": False, "validation_opened": False, "holdout_opened": False, "promotion_authorized": False, "paper_authorized": False, "live_authorized": False}
        receipt_path = ATTEMPT_ROOT / "comparison_receipt.json"; exclusive(receipt_path, canonical(receipt)); receipt_sha = sha256_file(receipt_path)
        terminal = {"schema_version": "stbs018_comparator_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "status": "COMPLETE", "completed_at_utc": now(), "attempt_started_path": str(start_path), "attempt_started_sha256": start_sha, "receipt_path": str(receipt_path), "receipt_sha256": receipt_sha, "verdict": first["verdict"], "same_id_retry_authorized": False}
        exclusive(ATTEMPT_ROOT / "attempt_terminal.json", canonical(terminal))
        return terminal
    except Exception as exc:
        artifacts = []
        for path in sorted(p for p in ATTEMPT_ROOT.rglob("*") if p.is_file() and p.name != "attempt_terminal.json"):
            artifacts.append({"path": str(path), "sha256": sha256_file(path), "length": path.stat().st_size})
        terminal = {"schema_version": "stbs018_comparator_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "status": "FAILED", "completed_at_utc": now(), "attempt_started_path": str(start_path), "attempt_started_sha256": start_sha, **context, "error": str(exc), "attempt_artifacts": artifacts, "mt5_launched": False, "compile_executed": False, "source_data_opened": False, "orders": 0, "trades": 0, "outcomes_read": 0, "returns": 0, "pf_computed": False, "economics_evaluated": False, "same_id_retry_authorized": False}
        exclusive(ATTEMPT_ROOT / "attempt_terminal.json", canonical(terminal))
        raise


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--execute", action="store_true"); args = parser.parse_args()
    if not args.execute:
        print("STBS018 comparator package loaded; use --execute for the sole authorized attempt")
        return 0
    print(json.dumps(execute(), indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
