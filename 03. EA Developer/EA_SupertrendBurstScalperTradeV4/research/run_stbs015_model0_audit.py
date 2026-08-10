#!/usr/bin/env python3
"""Fresh outer-only current-spread correctness audit for HYP-STBS-XAUUSD-M15-015."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-015"
INNER_HYPOTHESIS_ID = "HYP-STBS-XAUUSD-M15-014"
ATTEMPT_ID = "STBS015-MODEL0-AUDIT-001"
EA_NAME = "EA_SupertrendBurstScalperTradeV4"
MAGIC = 5604114
OVERRIDES = (
    "InpAuditOnly=true;"
    f"InpHypothesisId={INNER_HYPOTHESIS_ID};InpMagic={MAGIC};"
    "InpMaxNewPositionMarginPct=5.0;"
    "InpMinProjectedMarginLevelPct=2000.0;"
    "InpStopoutHeadroomFactor=1.25;"
    "InpVariantTag=STBS_H1_FLIP_M15_BURST_TRADE_FSM_V4_MARGIN_SAFE"
)
SOURCE = ROOT / "03. EA Developer" / EA_NAME / f"{EA_NAME}.mq5"
PREREG = ROOT / "03. EA Developer" / EA_NAME / "research" / f"{HYPOTHESIS_ID}_ENGINEERING_PREREG.md"
EA_CONTRACT = ROOT / "03. EA Developer" / EA_NAME / "ALPHAFACTORY_EA_CONTRACT.json"
COST_MANIFEST = ROOT / "03. EA Developer" / EA_NAME / "research" / "HYP-STBS-XAUUSD-M15-014_COLLECTION_ONLY_COST_MANIFEST.json"
REGISTRY = ROOT / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
TASK_PACKET = ROOT / "03. EA Developer" / EA_NAME / "research" / "preflight" / HYPOTHESIS_ID / "V1" / "task_packet.control.json"
RECEIPT = TASK_PACKET.with_name("contract_receipt.control.json")
ALPHA = ROOT / "02. AlphaFactory" / "alpha.ps1"
QUANT_ANALYZER = ROOT / "02. AlphaFactory" / "analysis" / "quant_analyzer.py"
RUNS_ROOT = ROOT / "02. AlphaFactory" / "runs" / EA_NAME
ATTEMPT_ROOT = ROOT / "02. AlphaFactory" / "runtime" / "model0_audit_attempts" / HYPOTHESIS_ID / ATTEMPT_ID
CANONICAL_EX5 = ROOT / "03. EA Developer" / EA_NAME / f"{EA_NAME}.ex5"
CANONICAL_COMPILE_LOG = ROOT / "03. EA Developer" / EA_NAME / f"{EA_NAME}.log"
STATIC_ARCHIVE_ROOT = ATTEMPT_ROOT / "static_review"
RUN_ARCHIVE_ROOT = ATTEMPT_ROOT / "run_evidence"
EXPECTED_SOURCE_SHA = "028D0AADB49856F58B167390E93300CD12AD90993F13FE7D5012DE6FFB8FC726"
EXPECTED_PREREG_SHA = "46F44F893909E70E0859FEC0A9CB10B1592B6BD757F9532B1E8D6A3AAFB296E0"
EXPECTED_COST_SHA = "F3C1C71F92C823D965CCE9780954A20ADA09B9F826416594C1D77F2117C15595"
EXPECTED_CONTRACT_SHA = "E15F88FB996D995D34A912714BBDAA4452893C705CE2B1096E6FCC38D96C3980"
EXPECTED_DATA_SHA = "077437E0038B40FEDB8AC611CAFE410B2FF8D0A90A742F0C52336F728D8C0BF4"
EXPECTED_BROKER_SHA = "E464F31D4B323A66DBC18D9409052E70F3711DB8F23597441648B19296B61D54"
EXPECTED_SERVER_SHA = "30B251638403D085CAB177A77A1B0EB69BD371793B501BE696F08033BE1E8DB0"
EXPECTED_ACCOUNT_SHA = "0635F9333630C605B51F8208861007B4267011E5F4D7C3C841309F04FE39BF02"
EMPTY_SHA = hashlib.sha256(b"").hexdigest().upper()
EXPECTED_ORDER_COLSPANS = [1, 1, 1, 1, 2, 1, 1, 1, 2, 1, 1]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temp.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def exclusive_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def capture_once(source: Path, destination: Path) -> tuple[bytes, str]:
    raw = source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest().upper()
    exclusive_write(destination, raw)
    if sha256_file(destination) != digest:
        raise RuntimeError(f"captured artifact hash mismatch: {destination}")
    return raw, digest


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def claim_attempt() -> tuple[Path, str]:
    ATTEMPT_ROOT.mkdir(parents=True, exist_ok=False)
    path = ATTEMPT_ROOT / "attempt_started.json"
    payload = {
        "schema_version": "alphafactory_model0_audit_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": utc_now(),
        "same_id_retry_authorized": False,
    }
    raw = canonical_json_bytes(payload)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    return path, hashlib.sha256(raw).hexdigest().upper()


def read_registry_authority() -> tuple[dict, str, str]:
    raw_registry = REGISTRY.read_bytes()
    rows = [line for line in raw_registry.splitlines() if line.strip()]
    latest_raw = None
    latest = None
    for raw in rows:
        candidate = json.loads(raw)
        if candidate.get("hypothesis_id") == HYPOTHESIS_ID:
            latest_raw, latest = raw, candidate
    if latest is None or latest_raw is None:
        raise RuntimeError("HYP015 authority row is missing")
    parent_rows = [raw for raw in rows if json.loads(raw).get("hypothesis_id") == INNER_HYPOTHESIS_ID]
    if not parent_rows:
        raise RuntimeError("terminal HYP014 parent row is missing")
    parent = json.loads(parent_rows[-1])
    parent_sha = hashlib.sha256(parent_rows[-1]).hexdigest().upper()
    if not (
        parent.get("state") == "killed"
        and parent.get("verdict") == "KILL_HARNESS_LITERAL_CURRENT_SPREAD_PRECOMPILE_NO_MT5_NO_ECONOMIC_VERDICT"
        and parent_sha == "72B25C6BEC0E562D255020F3E11B8B86BDE8B8995BFBC639A3988BE395CAA862"
    ):
        raise RuntimeError("terminal HYP014 parent state/hash/verdict mismatch")
    v = latest.get("validation", {})
    m = latest.get("metrics", {})
    exact = {
        "state": "screened",
        "ea_name": EA_NAME,
        "model": 0,
        "exact_overrides": OVERRIDES,
        "source_hash": EXPECTED_SOURCE_SHA,
        "prereg_sha256": EXPECTED_PREREG_SHA,
    }
    for key, value in exact.items():
        if latest.get(key) != value:
            raise RuntimeError(f"authority {key} mismatch")
    if v.get("authority") != "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE":
        raise RuntimeError("authority scope mismatch")
    required_true = {
        "mt5_audit_run_authorized",
        "mt5_authorized",
        "model0_authorized",
        "model0_data_acquisition_authorized",
        "run_compile_authorized",
        "mql5_compile_authorized",
        "artifact_collection_authorized",
    }
    for field in required_true:
        if v.get(field) is not True:
            raise RuntimeError(f"authority must enable {field}")
    required_false = {
        "packet_build_authorized", "source_run_authorized", "compile_authorized",
        "standalone_compile_authorized", "model0_performance_authorized",
        "model4_authorized", "model4_data_acquisition_authorized",
        "model4_performance_authorized", "trade_api_authorized",
        "performance_metrics_authorized", "outcome_prices_authorized",
        "post_event_ohlc_authorized", "economics_authorized",
        "comparator_execution_authorized",
        "optimization_authorized", "validation_authorized", "holdout_authorized",
        "research_validation_access_authorized", "research_holdout_access_authorized",
        "validation_access_authorized", "holdout_access_authorized",
        "research_falsification_authorized", "economic_validity_authorized",
        "promotion_eligible", "paper_trading_authorized", "live_trading_authorized",
        "market_edge_claim_authorized", "same_id_retry_authorized",
        "registry_mutation_allowed",
        "visual_mode_authorized", "network_authorized", "paid_requests_authorized",
    }
    for field in required_false:
        if v.get(field) is not False:
            raise RuntimeError(f"authority must disable {field}")
    if v.get("mt5_audit_attempt_id") != ATTEMPT_ID or v.get("mt5_audit_attempt_limit") != 1:
        raise RuntimeError("attempt authority mismatch")
    if m.get("mt5_audit_attempts_consumed") != 0 or m.get("mt5_audit_attempt_limit") != 1:
        raise RuntimeError("attempt counters are not unconsumed 0/1")
    if m.get("run_compile_attempts_consumed") != 0 or m.get("run_compile_attempt_limit") != 1:
        raise RuntimeError("run-compile counters are not unconsumed 0/1")
    for field in (
        "model0_runs", "mt5_launches", "orders_executed", "trades_simulated",
        "returns_computed", "performance_trials_executed",
    ):
        if m.get(field) != 0:
            raise RuntimeError(f"pre-run counter must be zero: {field}")
    if m.get("economics_executed") is not False:
        raise RuntimeError("pre-run economics_executed must be false")
    if m.get("research_validation_opened") is not False or m.get("research_holdout_opened") is not False:
        raise RuntimeError("research validation/holdout must remain unopened")
    if v.get("reviewed_runner_sha256") != sha256_file(Path(__file__).resolve()):
        raise RuntimeError("reviewed runner hash mismatch")
    if v.get("parent_hyp014_terminal_row_sha256") != "72B25C6BEC0E562D255020F3E11B8B86BDE8B8995BFBC639A3988BE395CAA862":
        raise RuntimeError("terminal HYP014 parent binding mismatch")
    return latest, hashlib.sha256(latest_raw).hexdigest().upper(), hashlib.sha256(raw_registry).hexdigest().upper()


def assert_bound_inputs(latest: dict) -> None:
    expected = {
        SOURCE: EXPECTED_SOURCE_SHA,
        PREREG: EXPECTED_PREREG_SHA,
        COST_MANIFEST: EXPECTED_COST_SHA,
        EA_CONTRACT: EXPECTED_CONTRACT_SHA,
    }
    for path, expected_sha in expected.items():
        if sha256_file(path) != expected_sha:
            raise RuntimeError(f"bound input changed: {path}")
    v = latest["validation"]
    for path_field, sha_field in (
        ("source_contract_test_path", "source_contract_test_sha256"),
        ("audit_runner_test_path", "audit_runner_test_sha256"),
        ("nonrepaint_manifest_path", "nonrepaint_manifest_sha256"),
        ("nonrepaint_audit_path", "nonrepaint_audit_sha256"),
        ("independent_pre_run_review_path", "independent_pre_run_review_sha256"),
        ("reviewed_ex5_path", "reviewed_ex5_sha256"),
        ("reviewed_compile_log_path", "reviewed_compile_log_sha256"),
        ("reviewed_alpha_ps1_path", "reviewed_alpha_ps1_sha256"),
        ("reviewed_registry_validator_path", "reviewed_registry_validator_sha256"),
        ("reviewed_quant_analyzer_path", "reviewed_quant_analyzer_sha256"),
        ("parent_hyp014_failure_path", "parent_hyp014_failure_sha256"),
        ("parent_hyp014_post_failure_review_path", "parent_hyp014_post_failure_review_sha256"),
        ("parent_hyp014_attempt_terminal_path", "parent_hyp014_attempt_terminal_sha256"),
    ):
        path = ROOT / v[path_field]
        if sha256_file(path) != v[sha_field]:
            raise RuntimeError(f"reviewed evidence changed: {path}")


def snapshot_static_review(latest: dict) -> dict[str, dict[str, str]]:
    validation = latest["validation"]
    specs = {
        "reviewed_static_ex5": (
            ROOT / validation["reviewed_ex5_path"],
            validation["reviewed_ex5_sha256"],
            STATIC_ARCHIVE_ROOT / f"{EA_NAME}.ex5",
        ),
        "reviewed_static_compile_log": (
            ROOT / validation["reviewed_compile_log_path"],
            validation["reviewed_compile_log_sha256"],
            STATIC_ARCHIVE_ROOT / f"{EA_NAME}.log",
        ),
        "reviewed_quant_analyzer": (
            ROOT / validation["reviewed_quant_analyzer_path"],
            validation["reviewed_quant_analyzer_sha256"],
            STATIC_ARCHIVE_ROOT / "quant_analyzer.py",
        ),
    }
    captured: dict[str, dict[str, str]] = {}
    for label, (source, expected_sha, archive) in specs.items():
        _, digest = capture_once(source, archive)
        if digest != expected_sha:
            raise RuntimeError(f"static reviewed artifact hash mismatch: {source}")
        captured[label] = {
            "source_path": str(source),
            "archive_path": str(archive),
            "sha256": digest,
        }
    return captured


def assert_reserved_placeholders(latest: dict) -> None:
    validation = latest["validation"]
    pairs = (
        (TASK_PACKET, "reserved_task_packet_path", "reserved_task_packet_placeholder_sha256"),
        (RECEIPT, "reserved_receipt_path", "reserved_receipt_placeholder_sha256"),
    )
    for path, path_field, hash_field in pairs:
        expected_path = str(path.relative_to(ROOT)).replace("\\", "/")
        if validation.get(path_field) != expected_path or validation.get(hash_field) != sha256_file(path):
            raise RuntimeError(f"reserved placeholder binding mismatch: {path}")
        if path.read_text(encoding="utf-8-sig").strip() != "{}":
            raise RuntimeError(f"reserved placeholder already used: {path}")


def ensure_clean_stable_sidecars() -> None:
    stable_hypothesis = INNER_HYPOTHESIS_ID
    names = {
        f"XAUUSD_LifecycleTrades_{stable_hypothesis}_{MAGIC}.csv",
        f"XAUUSD_RunMeta_{stable_hypothesis}_{MAGIC}.json",
    }
    scan_roots = [ROOT / "02. AlphaFactory" / "runtime"]
    roaming = os.environ.get("APPDATA")
    if roaming:
        scan_roots.append(Path(roaming) / "MetaQuotes" / "Terminal")
    found: list[str] = []
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for name in names:
            found.extend(str(p) for p in scan_root.rglob(name))
    if found:
        raise RuntimeError("pre-existing stable HYP014 sidecar(s): " + "; ".join(sorted(found)))


def git_snapshot() -> tuple[str, list[str], str]:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(
        ["git", "status", "--short", "--untracked-files=all"], cwd=ROOT, text=True, encoding="utf-8"
    )
    lines = raw.splitlines()
    status_sha = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest().upper()
    return commit, lines, status_sha


def build_receipt(latest_row_sha: str, registry_sha: str, static_review: dict[str, dict[str, str]]) -> str:
    packet = {
        "schema_version": "alphafactory_research_task_packet.v1",
        "authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "hypothesis_id": HYPOTHESIS_ID,
        "inner_mql_hypothesis_id": INNER_HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "registry_row_sha256": latest_row_sha,
        "registry_sha256": registry_sha,
        "indicator_dependencies": [],
        "visual_mode": False,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "promotion_eligible": False,
    }
    atomic_write(TASK_PACKET, canonical_json_bytes(packet))
    commit, status, status_sha = git_snapshot()
    data_quality = {
        "history_quality": {"operator": "gt", "value": 97.0},
        "coverage_mode": "fixed_window",
        "availability_asof_utc": utc_now(),
        "requested_from": "2005.01.01",
        "requested_to": "2023.01.01",
        "require_tester_journal_bounds": True,
    }
    binding = {
        "hypothesis_id": HYPOTHESIS_ID,
        "inner_mql_hypothesis_id": INNER_HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": "XAUUSD",
        "period": "M15",
        "from": "2005.01.01",
        "to": "2023.01.01",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "timeout_sec": 900,
        "overrides": OVERRIDES,
        "telemetry_tier": "off",
        "telemetry_profile": "none",
        "deposit": 10000,
        "leverage": 100,
        "spread": "current",
        "required_sidecars": [],
        "visual_mode": False,
        "indicator_dependencies": [],
        "include_closure_sha256": EMPTY_SHA,
        "symbol_geometry": {"digits": 2, "point": 0.01, "pip_size": 0.01},
        "data_quality_contract": data_quality,
    }
    evidence = []
    for label, path in (
        ("task_packet", TASK_PACKET),
        ("source", SOURCE),
        ("prereg", PREREG),
        ("cost_source_manifest", COST_MANIFEST),
        ("candidate_registry", REGISTRY),
        ("ea_capability_contract", EA_CONTRACT),
    ):
        evidence.append({"label": label, "kind": "file", "path": str(path), "sha256": sha256_file(path)})
    for label, item in static_review.items():
        evidence.append({
            "label": label,
            "kind": "file",
            "path": item["archive_path"],
            "sha256": item["sha256"],
        })
    receipt = {
        "schema_version": "alphafactory_execution_receipt.v1",
        "authority": "DATA_ACQUISITION_ONLY_NO_MODEL0_PERFORMANCE",
        "generated_at_utc": utc_now(),
        "binding": binding,
        "evidence": evidence,
        "git_commit": commit,
        "git_status": status,
        "git_status_sha256": status_sha,
    }
    atomic_write(RECEIPT, canonical_json_bytes(receipt))
    return sha256_file(RECEIPT)


def assert_prelaunch_integrity(
    latest: dict,
    latest_row_sha: str,
    registry_sha: str,
    receipt_sha: str,
    static_review: dict[str, dict[str, str]],
) -> None:
    expected = {
        SOURCE: EXPECTED_SOURCE_SHA,
        PREREG: EXPECTED_PREREG_SHA,
        COST_MANIFEST: EXPECTED_COST_SHA,
        EA_CONTRACT: EXPECTED_CONTRACT_SHA,
        REGISTRY: registry_sha,
        RECEIPT: receipt_sha,
    }
    for path, expected_sha in expected.items():
        if sha256_file(path) != expected_sha:
            raise RuntimeError(f"prelaunch binding changed: {path}")
    validation = latest["validation"]
    canonical = {
        CANONICAL_EX5: validation["reviewed_ex5_sha256"],
        CANONICAL_COMPILE_LOG: validation["reviewed_compile_log_sha256"],
        QUANT_ANALYZER: validation["reviewed_quant_analyzer_sha256"],
    }
    for path, expected_sha in canonical.items():
        if sha256_file(path) != expected_sha:
            raise RuntimeError(f"canonical reviewed artifact changed before launch: {path}")
    for item in static_review.values():
        if sha256_file(Path(item["archive_path"])) != item["sha256"]:
            raise RuntimeError(f"static archive changed before launch: {item['archive_path']}")
    raw_rows = [line for line in REGISTRY.read_bytes().splitlines() if line.strip()]
    hyp_rows = [line for line in raw_rows if json.loads(line).get("hypothesis_id") == HYPOTHESIS_ID]
    if not hyp_rows or hashlib.sha256(hyp_rows[-1]).hexdigest().upper() != latest_row_sha:
        raise RuntimeError("latest HYP014 authority row changed before launch")


def parse_colspans(cells: list[tuple[str, str]]) -> list[int] | None:
    values: list[int] = []
    for attrs, _ in cells:
        occurrences = len(re.findall(r"\bcolspan\b", attrs, re.I))
        matches = re.findall(r"\bcolspan\s*=\s*(?:\"([0-9]+)\"|'([0-9]+)'|([0-9]+))(?=\s|$)", attrs, re.I)
        if occurrences > 1 or (occurrences == 1 and len(matches) != 1):
            return None
        digits = next((part for part in matches[0] if part), "") if matches else ""
        value = int(digits) if digits else 1
        if value <= 0:
            return None
        values.append(value)
    return values


def orders_section_is_empty(html: str) -> bool:
    start = re.search(r"<b>\s*(?:Orders|C\u00e1c\s+l\u1ec7nh\s+\u0111\u1eb7t)\s*</b>", html, re.I)
    if not start:
        return False
    end = re.search(r"<b>\s*Deals\s*</b>", html[start.end():], re.I)
    if not end:
        return False
    section = html[start.end(): start.end() + end.start()]
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", section, re.I | re.S)
    if len(rows) != 2:
        return False
    td_re = re.compile(r"<td([^>]*)>(.*?)</td>", re.I | re.S)
    header, spacer = td_re.findall(rows[0]), td_re.findall(rows[1])
    if len(header) != 11 or parse_colspans(header) != EXPECTED_ORDER_COLSPANS:
        return False
    if not all(re.fullmatch(r"\s*<b>.*?</b>\s*", inner, re.I | re.S) for _, inner in header):
        return False
    if len(spacer) != 1 or parse_colspans(spacer) != [1]:
        return False
    return re.sub(r"<[^>]+>", "", spacer[0][1]).strip() == ""


def parse_kv_payload(line: str, marker: str) -> dict[str, str]:
    payload = line.split(marker, 1)[1].strip()
    result: dict[str, str] = {}
    for part in payload.split("|"):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        result[key] = value
    return result


def validate_journal_text(text: str) -> dict:
    forbidden = ("STBS_FATAL|", "STBS_ENTRY_REQUEST|", "STBS_CLOSE_REQUEST|", "STBS_CANCEL_REQUEST|", "STBS_DEAL|")
    for marker in forbidden:
        if marker in text:
            raise RuntimeError(f"forbidden audit journal marker: {marker}")
    summaries = [parse_kv_payload(line, "STBS_SUMMARY|") for line in text.splitlines() if "STBS_SUMMARY|" in line]
    if not summaries or any(item != summaries[0] for item in summaries[1:]):
        raise RuntimeError("missing or non-identical STBS summaries")
    expected_summary = {
        "hypothesis": INNER_HYPOTHESIS_ID, "raw": "690", "executable": "683", "gaps": "7",
        "long": "339", "short": "344", "atr_ready": "683", "geometry_ready": "683",
        "margin_ready": "683", "margin_rejects": "0", "margin_emergencies": "0",
        "forced_stopouts": "0", "entries": "0", "entry_rejects": "0", "closes": "0",
        "lifecycle_open_rows": "0", "lifecycle_final_close_rows": "0",
        "lifecycle_positions_opened": "0", "lifecycle_positions_final_closed": "0",
        "exec_state": "0", "exit_intent": "0", "failed": "false",
    }
    for key, value in expected_summary.items():
        if summaries[0].get(key) != value:
            raise RuntimeError(f"summary {key}: expected {value}, got {summaries[0].get(key)}")
    signals: dict[str, dict[str, str]] = {}
    multiplicities: dict[str, int] = {}
    for line in text.splitlines():
        if "STBS_SIGNAL|" not in line:
            continue
        item = parse_kv_payload(line, "STBS_SIGNAL|")
        epoch = item.get("source_epoch", "")
        if not epoch:
            raise RuntimeError("signal without source_epoch")
        if epoch in signals and signals[epoch] != item:
            raise RuntimeError(f"non-identical duplicate signal {epoch}")
        signals[epoch] = item
        multiplicities[epoch] = multiplicities.get(epoch, 0) + 1
    if len(signals) != 690 or set(multiplicities.values()) != {2} or len(summaries) != 2:
        raise RuntimeError("signal count/multiplicity mismatch")
    if next(iter(multiplicities.values())) != len(summaries):
        raise RuntimeError("signal and summary multiplicities differ")
    exact = [item for item in signals.values() if item.get("exact_next") == "true"]
    gaps = [item for item in signals.values() if item.get("exact_next") == "false"]
    if len(exact) != 683 or len(gaps) != 7:
        raise RuntimeError("exact/gap signal count mismatch")
    for item in exact:
        for key in ("atr_ready", "geometry_ready", "margin_ready", "audit"):
            if item.get(key) != "true":
                raise RuntimeError(f"executable signal {key} is not true")
    if sum(i.get("direction") == "LONG" for i in exact) != 339 or sum(i.get("direction") == "SHORT" for i in exact) != 344:
        raise RuntimeError("direction counts mismatch")
    counts = {key: int(summaries[0][key]) for key in (
        "raw", "executable", "gaps", "long", "short", "atr_ready", "geometry_ready",
        "margin_ready", "margin_rejects", "margin_emergencies", "forced_stopouts",
        "entries", "entry_rejects", "closes", "lifecycle_open_rows",
        "lifecycle_final_close_rows", "lifecycle_positions_opened",
        "lifecycle_positions_final_closed",
    )}
    return {"summary_multiplicity": len(summaries), "signal_multiplicity": next(iter(multiplicities.values())), "verified_counts": counts}


def validate_journal(journal: Path) -> dict:
    return validate_journal_text(journal.read_text(encoding="utf-8", errors="replace"))


def decode_compile_log(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig", errors="strict")


def capture_post_alpha_compile() -> dict[str, object]:
    result: dict[str, object] = {}
    for label, source, destination in (
        ("ex5", CANONICAL_EX5, RUN_ARCHIVE_ROOT / "compile" / f"{EA_NAME}.ex5"),
        ("compile_log", CANONICAL_COMPILE_LOG, RUN_ARCHIVE_ROOT / "compile" / f"{EA_NAME}.log"),
    ):
        if not source.is_file():
            result[label] = {"status": "ABSENT", "source_path": str(source)}
            continue
        try:
            raw, digest = capture_once(source, destination)
            item: dict[str, object] = {
                "status": "CAPTURED",
                "source_path": str(source),
                "archive_path": str(destination),
                "sha256": digest,
                "length": len(raw),
            }
            if label == "compile_log":
                matches = re.findall(
                    r"(?m)^Result:\s*0 errors,\s*0 warnings(?:,.*)?\s*$",
                    decode_compile_log(raw),
                )
                item["zero_error_warning_result_count"] = len(matches)
            result[label] = item
        except Exception as exc:
            result[label] = {
                "status": "CAPTURE_FAILED",
                "source_path": str(source),
                "error": str(exc),
            }
    return result


def capture_created_run_inventory(created: list[str]) -> list[dict[str, object]]:
    inventories: list[dict[str, object]] = []
    for run_name in created:
        source_root = RUNS_ROOT / run_name
        item: dict[str, object] = {
            "run_name": run_name,
            "source_path": str(source_root),
            "files": [],
        }
        if not source_root.is_dir():
            item["status"] = "MISSING"
            inventories.append(item)
            continue
        item["status"] = "CAPTURED"
        for source in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative = source.relative_to(source_root)
            destination = ATTEMPT_ROOT / "failed_run_inventory" / run_name / relative
            record: dict[str, object] = {"source_path": str(source), "relative_path": str(relative)}
            try:
                raw, digest = capture_once(source, destination)
                record.update({
                    "status": "CAPTURED",
                    "archive_path": str(destination),
                    "sha256": digest,
                    "length": len(raw),
                })
            except Exception as exc:
                record.update({"status": "CAPTURE_FAILED", "error": str(exc)})
                item["status"] = "PARTIAL"
            item["files"].append(record)
        inventories.append(item)
    return inventories


def validate_run(
    run_dir: Path,
    receipt_sha: str,
    static_review: dict[str, dict[str, str]],
    post_alpha_compile: dict[str, object],
) -> dict:
    run_ex5 = post_alpha_compile.get("ex5", {})
    run_log = post_alpha_compile.get("compile_log", {})
    if run_ex5.get("status") != "CAPTURED" or run_log.get("status") != "CAPTURED":
        raise RuntimeError("post-Alpha compile artifacts were not captured")
    run_ex5_sha = str(run_ex5["sha256"])
    run_log_sha = str(run_log["sha256"])
    if run_log.get("zero_error_warning_result_count") != 1:
        raise RuntimeError("fresh run compile log does not contain one 0 errors / 0 warnings result")
    manifest_path = run_dir / "run_manifest.json"
    manifest_raw, manifest_sha = capture_once(
        manifest_path, RUN_ARCHIVE_ROOT / "run_manifest.json"
    )
    manifest = json.loads(manifest_raw.decode("utf-8-sig"))
    expected = {
        "schema_version": "alphafactory_run_manifest.v2", "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control", "ea_name": EA_NAME, "symbol": "XAUUSD", "period": "M15",
        "from": "2005.01.01", "to": "2023.01.01", "model": 0, "execution_mode": 0,
        "fixed_delay_ms": 0, "timeout_sec": 900, "overrides": OVERRIDES,
        "deposit": 10000, "leverage": 100, "spread": "current",
        "telemetry_tier": "off", "telemetry_profile": "none", "visual_mode": False,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"manifest {key} mismatch")
    if manifest.get("source_sha256") != EXPECTED_SOURCE_SHA:
        raise RuntimeError("run source hash mismatch")
    if manifest.get("contract_receipt_sha256") != receipt_sha:
        raise RuntimeError("run manifest receipt binding mismatch")
    identity = {
        "data_fingerprint": EXPECTED_DATA_SHA,
        "broker_fingerprint": EXPECTED_BROKER_SHA,
        "server_fingerprint": EXPECTED_SERVER_SHA,
        "account_fingerprint": EXPECTED_ACCOUNT_SHA,
    }
    for key, value in identity.items():
        if manifest.get(key) != value:
            raise RuntimeError(f"run manifest {key} mismatch")
    if manifest.get("ex5_sha256") != manifest.get("tester_ex5_sha256"):
        raise RuntimeError("compiled/tester EX5 mismatch")
    if run_ex5_sha != manifest.get("ex5_sha256"):
        raise RuntimeError("captured fresh run EX5 does not match manifest")
    canonical_report = (run_dir / "report.html").resolve()
    if Path(manifest.get("report_path", "")).resolve() != canonical_report:
        raise RuntimeError("run manifest report path is not canonical")
    snapshot_specs = (
        ("source_snapshot", run_dir / "snapshot" / "source" / f"{EA_NAME}.mq5"),
        ("ex5_snapshot", run_dir / "snapshot" / "build" / f"{EA_NAME}.ex5"),
        ("config_snapshot", run_dir / "snapshot" / "config" / "config.ini"),
    )
    for field, path in snapshot_specs:
        if Path(manifest.get(field, "")).resolve() != path.resolve() or not path.is_file():
            raise RuntimeError(f"run manifest {field} is not canonical")
    snapshot_capture: dict[str, tuple[Path, str]] = {}
    for field, path in snapshot_specs:
        destination = RUN_ARCHIVE_ROOT / "snapshot" / path.parent.name / path.name
        _, digest = capture_once(path, destination)
        snapshot_capture[field] = (destination, digest)
    if snapshot_capture["ex5_snapshot"][1] != manifest.get("ex5_sha256"):
        raise RuntimeError("run snapshot EX5 hash mismatch")
    if snapshot_capture["source_snapshot"][1] != manifest.get("source_sha256"):
        raise RuntimeError("run snapshot source hash mismatch")
    if snapshot_capture["config_snapshot"][1] != manifest.get("config_sha256"):
        raise RuntimeError("run snapshot config hash mismatch")
    dq = manifest.get("data_quality_fingerprint_basis", {})
    contract = dq.get("contract", {})
    proof = dq.get("series_proof", {})
    if not (
        dq.get("base_data_fingerprint") == EXPECTED_DATA_SHA
        and float(dq.get("history_quality", 0)) > 97.0
        and contract.get("requested_from") == "2005.01.01"
        and contract.get("requested_to") == "2023.01.01"
        and contract.get("coverage_mode") == "fixed_window"
        and contract.get("require_tester_journal_bounds") is True
        and proof.get("symbol") == "XAUUSD"
        and proof.get("m5_synchronized") == 1
        and proof.get("copytime_result") == 1
        and proof.get("copytime_count") == 1
        and proof.get("m5_first_epoch") == proof.get("m5_terminal_first_epoch")
        and proof.get("m1_server_first_epoch") == proof.get("m1_terminal_first_epoch")
    ):
        raise RuntimeError("run data-quality/series proof mismatch")
    journal_path = run_dir / "logs" / "tester_journal_delta.log"
    journal_raw, journal_sha = capture_once(
        journal_path, RUN_ARCHIVE_ROOT / "logs" / "tester_journal_delta.log"
    )
    if journal_sha != dq.get("journal_sha256"):
        raise RuntimeError("journal hash does not match data-quality evidence")
    journal_result = validate_journal_text(journal_raw.decode("utf-8", errors="replace"))
    runmeta_files = list((run_dir / "logs").glob("*_RunMeta_*.json"))
    lifecycle_files = list((run_dir / "logs").glob("*_LifecycleTrades_*.csv"))
    if runmeta_files or lifecycle_files:
        raise RuntimeError("telemetry-none audit must create no RunMeta/lifecycle sidecar")
    quant_snapshot = Path(static_review["reviewed_quant_analyzer"]["archive_path"])
    if sha256_file(quant_snapshot) != static_review["reviewed_quant_analyzer"]["sha256"]:
        raise RuntimeError("captured quant analyzer changed")
    spec = importlib.util.spec_from_file_location("quant_analyzer", quant_snapshot)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    report_path = Path(manifest["report_path"])
    report_raw, report_sha = capture_once(
        report_path, RUN_ARCHIVE_ROOT / "report.html"
    )
    if report_sha != manifest.get("report_sha256"):
        raise RuntimeError("report hash does not match run manifest")
    report_html = module._decode_report_bytes(report_raw)
    if not orders_section_is_empty(report_html):
        raise RuntimeError("audit report Orders section is not exact-empty")
    captured_report = RUN_ARCHIVE_ROOT / "report.html"
    deals = module.parse_deals(captured_report)
    if sha256_file(captured_report) != report_sha:
        raise RuntimeError("captured report changed during parsing")
    if len(deals) != 1:
        raise RuntimeError(f"audit report must contain one funding deal, got {len(deals)}")
    funding = deals[0]
    if not (
        funding.time == dt.datetime(2005, 1, 1) and funding.deal_id == 1 and funding.side == "balance"
        and funding.symbol == "" and funding.direction == "" and funding.comment == ""
        and funding.volume == 0.0 and funding.price == 0.0 and funding.commission == 0.0
        and funding.swap == 0.0 and funding.order_id is None and funding.profit == 10000.0
        and funding.balance == 10000.0
    ):
        raise RuntimeError("audit report funding row mismatch")
    if module.deals_to_trades(deals):
        raise RuntimeError("audit report unexpectedly contains completed trades")
    return {
        "run_id": manifest["run_id"], "run_directory": str(run_dir),
        "manifest_path": str(manifest_path), "manifest_sha256": manifest_sha,
        "captured_manifest_path": str(RUN_ARCHIVE_ROOT / "run_manifest.json"),
        "captured_report_path": str(captured_report),
        "report_path": str(report_path), "report_sha256": report_sha,
        "captured_journal_path": str(RUN_ARCHIVE_ROOT / "logs" / "tester_journal_delta.log"),
        "journal_path": str(journal_path), "journal_sha256": journal_sha,
        "run_compile_ex5_path": str(RUN_ARCHIVE_ROOT / "compile" / f"{EA_NAME}.ex5"),
        "run_compile_ex5_sha256": run_ex5_sha,
        "run_compile_log_path": str(RUN_ARCHIVE_ROOT / "compile" / f"{EA_NAME}.log"),
        "run_compile_log_sha256": run_log_sha,
        "run_snapshot_source_path": str(snapshot_capture["source_snapshot"][0]),
        "run_snapshot_source_sha256": snapshot_capture["source_snapshot"][1],
        "run_snapshot_ex5_path": str(snapshot_capture["ex5_snapshot"][0]),
        "run_snapshot_ex5_sha256": snapshot_capture["ex5_snapshot"][1],
        "run_snapshot_config_path": str(snapshot_capture["config_snapshot"][0]),
        "run_snapshot_config_sha256": snapshot_capture["config_snapshot"][1],
        **journal_result,
    }


def write_terminal(start_path: Path, start_sha: str, status: str, detail: dict) -> None:
    payload = {
        "schema_version": "alphafactory_model0_audit_attempt_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "status": status,
        "completed_at_utc": utc_now(),
        "attempt_started_path": str(start_path),
        "attempt_started_sha256": start_sha,
        "same_id_retry_authorized": False,
        **detail,
    }
    path = ATTEMPT_ROOT / "attempt_terminal.json"
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "wb") as handle:
        handle.write(canonical_json_bytes(payload))
        handle.flush()
        os.fsync(handle.fileno())


def execute() -> dict:
    start_path, start_sha = claim_attempt()
    static_review: dict[str, dict[str, str]] = {}
    post_alpha_compile: dict[str, object] = {}
    run_set_delta: dict[str, object] = {}
    failed_run_inventory: list[dict[str, object]] = []
    try:
        latest, latest_row_sha, registry_sha = read_registry_authority()
        assert_reserved_placeholders(latest)
        assert_bound_inputs(latest)
        ensure_clean_stable_sidecars()
        static_review = snapshot_static_review(latest)
        receipt_sha = build_receipt(latest_row_sha, registry_sha, static_review)
        assert_prelaunch_integrity(latest, latest_row_sha, registry_sha, receipt_sha, static_review)
        assert_bound_inputs(latest)
        before = {p.name for p in RUNS_ROOT.iterdir()} if RUNS_ROOT.exists() else set()
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ALPHA),
            "backtest", EA_NAME, "-Symbol", "XAUUSD", "-Period", "M15",
            "-From", "2005.01.01", "-To", "2023.01.01", "-Model", "0",
            "-ExecutionMode", "0", "-FixedDelayMs", "0", "-TimeoutSec", "900",
            "-Overrides", OVERRIDES, "-HypothesisId", HYPOTHESIS_ID, "-RunRole", "control",
            "-TelemetryTier", "off", "-Deposit", "10000", "-Leverage", "100",
            "-ContractReceipt", str(RECEIPT),
            "-ContractReceiptSha256", receipt_sha,
        ]
        completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        atomic_write(ATTEMPT_ROOT / "alpha_stdout.log", completed.stdout.encode("utf-8"))
        atomic_write(ATTEMPT_ROOT / "alpha_stderr.log", completed.stderr.encode("utf-8"))
        post_alpha_compile = capture_post_alpha_compile()
        after = {p.name for p in RUNS_ROOT.iterdir()} if RUNS_ROOT.exists() else set()
        created = sorted(after - before)
        deleted = sorted(before - after)
        run_set_delta = {
            "before_count": len(before),
            "after_count": len(after),
            "created": created,
            "deleted": deleted,
        }
        if completed.returncode != 0:
            failed_run_inventory = capture_created_run_inventory(created)
            raise RuntimeError(f"AlphaFactory returned {completed.returncode}; run delta={run_set_delta}")
        if len(created) != 1 or not before.issubset(after) or after != before | set(created):
            failed_run_inventory = capture_created_run_inventory(created)
            raise RuntimeError(f"expected exactly one run directory, got {created}")
        try:
            result = validate_run(RUNS_ROOT / created[0], receipt_sha, static_review, post_alpha_compile)
        except Exception:
            failed_run_inventory = capture_created_run_inventory(created)
            raise
        evidence = {
            "verdict": "PASS_ZERO_TRADE_MODEL0_AUDIT",
            "authority_row_sha256": latest_row_sha,
            "registry_sha256": registry_sha,
            "task_packet_path": str(TASK_PACKET),
            "task_packet_sha256": sha256_file(TASK_PACKET),
            "contract_receipt_path": str(RECEIPT),
            "contract_receipt_sha256": receipt_sha,
            "alpha_stdout_sha256": sha256_file(ATTEMPT_ROOT / "alpha_stdout.log"),
            "alpha_stderr_sha256": sha256_file(ATTEMPT_ROOT / "alpha_stderr.log"),
            "static_review_archives": static_review,
            "post_alpha_canonical_compile": post_alpha_compile,
            "run_set_delta": run_set_delta,
            **result,
        }
        write_terminal(start_path, start_sha, "COMPLETE", evidence)
        return result
    except Exception as exc:
        failure = {"error": str(exc)}
        for label, path in (
            ("task_packet", TASK_PACKET), ("contract_receipt", RECEIPT),
            ("alpha_stdout", ATTEMPT_ROOT / "alpha_stdout.log"),
            ("alpha_stderr", ATTEMPT_ROOT / "alpha_stderr.log"),
        ):
            if path.is_file():
                failure[f"{label}_path"] = str(path)
                failure[f"{label}_sha256"] = sha256_file(path)
        failure["static_review_archives"] = static_review
        failure["post_alpha_canonical_compile"] = post_alpha_compile
        failure["run_set_delta"] = run_set_delta
        failure["created_run_inventory"] = failed_run_inventory
        failure["attempt_artifacts"] = [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in sorted(ATTEMPT_ROOT.rglob("*"))
            if path.is_file() and path.name != "attempt_terminal.json"
        ]
        write_terminal(start_path, start_sha, "FAILED", failure)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("--execute is required; dry-run is intentionally unsupported")
    print(json.dumps(execute(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
