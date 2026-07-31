from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import validate_execution_audit as v1


WORKSPACE = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
PREFLIGHT = PACKAGE / "research" / "preflight" / "HYP-LOMX-EXEC-AUDIT-M1-003"
REGISTRY = WORKSPACE / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"

HYPOTHESIS_ID = "HYP-LOMX-EXEC-AUDIT-M1-003"
EA_NAME = "EA_LondonOpenExecutionAudit"
SOURCE_SHA256 = "C99D18C7912384D529CF651214EBF636211536957D7F4241831CB2418D28EEC1"
PREREG_SHA256 = "FA5745BAFFD8FBBE8238D82B143E5F6DFC4E9CD7DD1D9A5557F3B3E01310CABA"
CAPABILITY_SHA256 = "CF1357EF72B9B4575A34FDFBD5234828C036B59344A6D46903B44DC7D5F42B5E"
ENGINEERING_GATE_SHA256 = "0005B40B4589986F45ED762CA0A5F59B416E30BF1D824C483267FF6420205007"
SCREENED_ROW_SHA256 = "4CC856EECFBD5CA6C7E20875221EB96087298F70DFF0D30D04D602DE3B958F6C"
HISTORICAL_REGISTRY_SHA256 = "2EEB75B389B396267C888EB4CF3FD9DCB9D9E8C234115B831CBEF12DB854AF1A"
EMPTY_INCLUDE_SHA256 = "E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
REQUIRED_SIDECARS = sorted(
    ["*_DecisionTelemetry_*.csv", "*_LifecycleTrades_*.csv", "*_RunMeta_*.json"]
)

AUTHORIZED_RUN_IDS = {
    "EURUSD_MIDDAY_CONT": "20260730_190022",
    "GBPUSD_MIDDAY_REV": "20260730_190128",
    "GBPUSD_LATE_FIX_REV": "20260730_190227",
    "GBPUSD_FULL_SESSION_REV": "20260730_190328",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        errors.append(f"{label} malformed: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{label} is not a JSON object")
        return {}
    return value


def check_equal(errors: list[str], label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        errors.append(f"{label} mismatch actual={actual!r} expected={expected!r}")


def check_hash(errors: list[str], label: str, path: Path, expected: str) -> None:
    if not path.is_file():
        errors.append(f"{label} missing: {path}")
        return
    actual = sha256(path)
    if actual != expected.upper():
        errors.append(f"{label} hash mismatch actual={actual} expected={expected}")


def expected_overrides(scenario: str) -> str:
    return (
        "InpAuditAutoMode=true;InpBrokerFollowsEuropeDST=true;"
        "InpBrokerGMTOffsetWinter=2;InpDeviationPips=2.00;"
        "InpEnableTelemetry=true;InpHypothesisId=HYP-LOMX-EXEC-AUDIT-M1-003;"
        f"InpMagic=5601303;InpScenario={scenario};InpVolumeLots=0.01"
    )


def last_sunday(year: int, month: int) -> datetime:
    if month == 12:
        last = datetime(year, 12, 31)
    else:
        last = datetime(year, month + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def europe_dst_utc(value: datetime) -> bool:
    start = last_sunday(value.year, 3).replace(hour=1)
    end = last_sunday(value.year, 10).replace(hour=1)
    return start <= value < end


def london_local_to_server(day: str, minute_of_day: int) -> datetime:
    local = datetime.strptime(day, "%Y.%m.%d").replace(
        hour=minute_of_day // 60, minute=minute_of_day % 60
    )
    trial_utc = local
    if europe_dst_utc(trial_utc - timedelta(hours=1)):
        trial_utc = local - timedelta(hours=1)
    broker_offset = 3 if europe_dst_utc(trial_utc) else 2
    return trial_utc + timedelta(hours=broker_offset)


def clock_errors(decisions: list[dict[str, str]], scenario: str) -> list[str]:
    errors: list[str] = []
    contract = v1.SCENARIOS[scenario]
    for index, row in enumerate(decisions, start=2):
        try:
            server = v1.parse_time(row["server_time"])
            utc = v1.parse_time(row["utc_time"])
            london = v1.parse_time(row["london_time"])
        except Exception as exc:
            errors.append(f"decision row {index} time parse failed: {exc}")
            continue
        dst = europe_dst_utc(utc)
        if server != utc + timedelta(hours=3 if dst else 2):
            errors.append(f"decision row {index} server/UTC conversion mismatch")
        if london != utc + timedelta(hours=1 if dst else 0):
            errors.append(f"decision row {index} London/UTC conversion mismatch")
        if london.strftime("%Y.%m.%d") != row.get("london_date"):
            errors.append(f"decision row {index} london_date mismatch")

    signals = [
        row
        for row in decisions
        if row.get("event") == "SIGNAL_READY" and row.get("status") == "PASS"
    ]
    for row in signals:
        day = row["london_date"]
        expected = {
            "source_0800_server": london_local_to_server(day, 8 * 60),
            "source_0830_server": london_local_to_server(day, 8 * 60 + 30),
            "signal_observed_server": london_local_to_server(day, 8 * 60 + 31),
            "entry_eligible_server": london_local_to_server(day, contract["entry"]),
        }
        for key, value in expected.items():
            try:
                observed = v1.parse_time(row[key])
            except Exception as exc:
                errors.append(f"{key} parse failed on {day}: {exc}")
                continue
            if observed != value:
                errors.append(f"{key} clock mismatch on {day}")
    return errors


def raw_registry_row_sha256(errors: list[str]) -> str:
    matches: list[tuple[str, dict[str, Any]]] = []
    for raw in REGISTRY.read_text(encoding="utf-8-sig").splitlines():
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if row.get("hypothesis_id") == HYPOTHESIS_ID and row.get("state") == "screened":
            matches.append((raw, row))
    if len(matches) != 1:
        errors.append(f"expected one screened registry row, found {len(matches)}")
        return ""
    return sha256_bytes(matches[0][0].encode("utf-8"))


def validate_provenance(scenario: str, run_dir: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    contract = v1.SCENARIOS[scenario]
    run_dir = run_dir.resolve()
    manifest_path = run_dir / "run_manifest.json"
    report_path = run_dir / "report.html"
    manifest = load_json(manifest_path, errors, "run manifest") if manifest_path.is_file() else {}
    if not manifest_path.is_file():
        errors.append("run manifest missing")

    expected_manifest = {
        "schema_version": "alphafactory_run_manifest.v2",
        "run_id": AUTHORIZED_RUN_IDS[scenario],
        "hypothesis_id": HYPOTHESIS_ID,
        "run_role": "control",
        "ea_name": EA_NAME,
        "symbol": contract["symbol"],
        "period": "M1",
        "from": "2016.01.01",
        "to": "2020.12.31",
        "model": 0,
        "execution_mode": 0,
        "fixed_delay_ms": 0,
        "overrides": expected_overrides(scenario),
        "deposit": 500000,
        "leverage": 100,
        "spread": "current",
        "telemetry_tier": "trade-only",
        "telemetry_profile": "lifecycle-v3",
        "source_sha256": SOURCE_SHA256,
        "includes_sha256": EMPTY_INCLUDE_SHA256,
    }
    for key, expected in expected_manifest.items():
        check_equal(errors, f"manifest.{key}", manifest.get(key), expected)
    check_equal(errors, "run directory identity", run_dir.name, AUTHORIZED_RUN_IDS[scenario])
    if manifest.get("local_run_dir"):
        check_equal(
            errors,
            "manifest.local_run_dir",
            Path(str(manifest["local_run_dir"])).resolve(),
            run_dir,
        )
    if manifest.get("report_path"):
        check_equal(
            errors,
            "manifest.report_path",
            Path(str(manifest["report_path"])).resolve(),
            report_path.resolve(),
        )

    if report_path.is_file() and manifest.get("report_sha256"):
        check_hash(errors, "report", report_path, str(manifest["report_sha256"]))
    else:
        errors.append("report or manifest report hash missing")

    snapshot_checks = [
        ("source_snapshot", "source_sha256"),
        ("ex5_snapshot", "ex5_sha256"),
        ("config_snapshot", "config_sha256"),
    ]
    for path_key, hash_key in snapshot_checks:
        value = manifest.get(path_key)
        expected = manifest.get(hash_key)
        if not value or not expected:
            errors.append(f"manifest {path_key}/{hash_key} missing")
            continue
        check_hash(errors, path_key, Path(str(value)), str(expected))
    check_equal(errors, "manifest tester EX5 hash", manifest.get("tester_ex5_sha256"), manifest.get("ex5_sha256"))

    fingerprint = manifest.get("fingerprint_basis", {})
    check_equal(errors, "history quality", fingerprint.get("history_quality"), "100%")
    try:
        if int(fingerprint.get("bars", 0)) <= 0 or int(fingerprint.get("ticks", 0)) <= 0:
            errors.append("manifest bars/ticks must be positive")
    except Exception:
        errors.append("manifest bars/ticks malformed")
    check_equal(errors, "symbol digits", fingerprint.get("digits"), 5)
    check_equal(errors, "symbol point", float(fingerprint.get("point", 0.0)), 0.00001)
    check_equal(errors, "symbol pip_size", float(fingerprint.get("pip_size", 0.0)), 0.0001)
    check_equal(errors, "required sidecars", sorted(manifest.get("required_sidecars", [])), REQUIRED_SIDECARS)

    manifest_sidecars = manifest.get("sidecars", [])
    if not isinstance(manifest_sidecars, list) or len(manifest_sidecars) != 3:
        errors.append(f"manifest must bind exactly three sidecars, found {len(manifest_sidecars) if isinstance(manifest_sidecars, list) else 'non-list'}")
        manifest_sidecars = []
    for item in manifest_sidecars:
        sidecar = (run_dir / str(item.get("path", ""))).resolve()
        if run_dir not in sidecar.parents:
            errors.append(f"sidecar escapes run directory: {sidecar}")
            continue
        expected_hash = str(item.get("sha256", ""))
        check_hash(errors, f"sidecar {sidecar.name}", sidecar, expected_hash)
        if sidecar.is_file():
            check_equal(errors, f"sidecar {sidecar.name} length", sidecar.stat().st_size, item.get("length"))
            if sidecar.suffix.lower() == ".csv":
                with sidecar.open("r", encoding="utf-8-sig", newline="") as handle:
                    data_rows = max(sum(1 for _ in handle) - 1, 0)
                check_equal(errors, f"sidecar {sidecar.name} row_count", data_rows, item.get("row_count"))

    receipt_path = PREFLIGHT / f"execution_receipt.{scenario}_V2.json"
    task_path = PREFLIGHT / f"task_packet.{scenario}_V2.json"
    receipt = load_json(receipt_path, errors, "execution receipt")
    task = load_json(task_path, errors, "task packet")
    if receipt_path.is_file():
        receipt_hash = sha256(receipt_path)
        check_equal(errors, "manifest receipt hash", manifest.get("contract_receipt_sha256"), receipt_hash)
    else:
        receipt_hash = ""
        errors.append("execution receipt missing")
    task_hash = sha256(task_path) if task_path.is_file() else ""

    check_equal(errors, "receipt schema", receipt.get("schema_version"), "alphafactory_execution_receipt.v1")
    check_equal(errors, "receipt hypothesis", receipt.get("hypothesis_id"), HYPOTHESIS_ID)
    check_equal(errors, "receipt task hash", receipt.get("task_packet_sha256"), task_hash)
    check_equal(errors, "receipt registry row hash", receipt.get("registry_row_sha256"), SCREENED_ROW_SHA256)
    check_equal(errors, "screened registry row live hash", raw_registry_row_sha256(errors), SCREENED_ROW_SHA256)

    binding = receipt.get("binding", {})
    required_binding = {
        key: expected_manifest[key]
        for key in (
            "hypothesis_id", "run_role", "ea_name", "symbol", "period", "from", "to",
            "model", "execution_mode", "fixed_delay_ms", "overrides", "telemetry_tier",
            "telemetry_profile", "deposit", "leverage", "spread",
        )
    }
    for key, expected in required_binding.items():
        check_equal(errors, f"receipt.binding.{key}", binding.get(key), expected)
    check_equal(errors, "receipt binding hypothesis", binding.get("hypothesis_id"), HYPOTHESIS_ID)
    check_equal(errors, "receipt binding required sidecars", sorted(binding.get("required_sidecars", [])), REQUIRED_SIDECARS)
    check_equal(errors, "receipt include closure", binding.get("include_closure_sha256"), EMPTY_INCLUDE_SHA256)
    check_equal(
        errors,
        "receipt symbol geometry",
        binding.get("symbol_geometry"),
        {"digits": 5, "point": 0.00001, "pip_size": 0.0001},
    )

    check_equal(errors, "task schema", task.get("schema_version"), "alphafactory_audit_task_packet.v1")
    check_equal(errors, "task amendment", task.get("amendment"), "V2_PRE_VALID_OUTCOME_ENGINEERING_CORRECTION")
    check_equal(errors, "task hypothesis", task.get("hypothesis_id"), HYPOTHESIS_ID)
    check_equal(errors, "task scenario", task.get("scenario"), scenario)
    check_equal(errors, "task symbol", task.get("symbol"), contract["symbol"])
    check_equal(errors, "task model", task.get("model"), 0)
    check_equal(errors, "task period", task.get("period"), "M1")
    check_equal(errors, "task from", task.get("from"), "2016.01.01")
    check_equal(errors, "task to", task.get("to"), "2020.12.31")
    check_equal(errors, "task deposit", task.get("deposit"), 500000)
    check_equal(errors, "task source hash", task.get("source_sha256"), SOURCE_SHA256)
    check_equal(errors, "task prereg hash", task.get("prereg_v2_sha256"), PREREG_SHA256)
    check_equal(errors, "task historical registry hash", task.get("candidate_registry_sha256"), HISTORICAL_REGISTRY_SHA256)
    check_equal(errors, "task screened row hash", task.get("registry_row_sha256"), SCREENED_ROW_SHA256)
    check_equal(errors, "task capability hash", task.get("ea_capability_contract_sha256"), CAPABILITY_SHA256)
    check_equal(errors, "task required sidecars", sorted(task.get("required_sidecars", [])), REQUIRED_SIDECARS)
    check_equal(errors, "task minimum population", task.get("minimum_completed_lifecycles"), v1.MIN_COMPLETED_LIFECYCLES)
    check_equal(errors, "task audit_only", task.get("audit_only"), True)
    check_equal(errors, "task performance authority", task.get("performance_metrics_authorized"), False)
    check_equal(errors, "task economics authority", task.get("economics_authorized"), False)
    check_equal(errors, "task optimization authority", task.get("optimization_authorized"), False)
    check_equal(errors, "task promotion authority", task.get("promotion_authorized"), False)
    check_equal(errors, "task sealed later years", task.get("later_years_sealed"), True)

    evidence = receipt.get("evidence", [])
    evidence_by_label: dict[str, dict[str, Any]] = {}
    if not isinstance(evidence, list):
        errors.append("receipt evidence is not a list")
        evidence = []
    for item in evidence:
        label = str(item.get("label", ""))
        if not label or label in evidence_by_label:
            errors.append(f"receipt missing/duplicate evidence label {label!r}")
            continue
        evidence_by_label[label] = item
    expected_evidence_hashes = {
        "task_packet": task_hash,
        "source": SOURCE_SHA256,
        "prereg": PREREG_SHA256,
        "ea_capability_contract": CAPABILITY_SHA256,
        "engineering_gate": ENGINEERING_GATE_SHA256,
    }
    for label, expected_hash in expected_evidence_hashes.items():
        item = evidence_by_label.get(label)
        if item is None:
            errors.append(f"receipt evidence missing {label}")
            continue
        check_equal(errors, f"receipt evidence {label} hash", str(item.get("sha256", "")).upper(), expected_hash)
        check_hash(errors, f"receipt evidence {label}", Path(str(item.get("path", ""))), expected_hash)
    registry_item = evidence_by_label.get("candidate_registry", {})
    check_equal(
        errors,
        "receipt historical whole-registry hash",
        str(registry_item.get("sha256", "")).upper(),
        HISTORICAL_REGISTRY_SHA256,
    )

    details = {
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256(manifest_path) if manifest_path.is_file() else None,
        "alpha_run_id": manifest.get("run_id"),
        "receipt_path": str(receipt_path),
        "receipt_sha256": receipt_hash or None,
        "task_packet_path": str(task_path),
        "task_packet_sha256": task_hash or None,
        "source_snapshot_sha256": manifest.get("source_sha256"),
        "ex5_snapshot_sha256": manifest.get("ex5_sha256"),
        "config_snapshot_sha256": manifest.get("config_sha256"),
        "report_sha256": manifest.get("report_sha256"),
        "history_quality": fingerprint.get("history_quality"),
        "bars": fingerprint.get("bars"),
        "ticks": fingerprint.get("ticks"),
        "historical_whole_registry_hash_status": "RUN_TIME_ASSERTED; CURRENT APPEND_ONLY FILE HAS ADVANCED",
    }
    return errors, details


def keyed(rows: list[dict[str, str]], key: str, label: str, errors: list[str]) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    for row in rows:
        try:
            value = int(row[key])
        except Exception:
            errors.append(f"{label} has invalid {key}")
            continue
        if value in result:
            errors.append(f"{label} duplicate {key}={value}")
        result[value] = row
    return result


def validate_identity(scenario: str, run_dir: Path) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    contract = v1.SCENARIOS[scenario]
    logs = run_dir / "logs"
    decision_path = next(iter(sorted(logs.glob("*_DecisionTelemetry_*.csv"))), None)
    lifecycle_path = next(iter(sorted(logs.glob("*_LifecycleTrades_*.csv"))), None)
    meta_path = next(iter(sorted(logs.glob("*_RunMeta_*.json"))), None)
    if decision_path is None or lifecycle_path is None or meta_path is None:
        return ["identity validation sidecars are missing"], {}
    decisions = v1.read_csv(decision_path)
    lifecycle = v1.read_csv(lifecycle_path)
    meta = load_json(meta_path, errors, "RunMeta")

    successful_specs = {
        "SIGNAL_READY": "PASS",
        "ENTRY_REQUEST": "REQUESTED",
        "ENTRY_SUBMIT": "ACCEPTED",
        "ENTRY_DEAL": "EXECUTED",
        "EXIT_REQUEST": "REQUESTED",
        "EXIT_SUBMIT": "ACCEPTED",
        "EXIT_DEAL": "EXECUTED",
    }
    events: dict[str, list[dict[str, str]]] = {}
    for event, status in successful_specs.items():
        rows = [row for row in decisions if row.get("event") == event]
        events[event] = rows
        bad = [row for row in rows if row.get("status") != status]
        if bad:
            errors.append(f"{event} contains {len(bad)} rows with non-{status} status")
    funnel_counts = {event: len(rows) for event, rows in events.items()}
    if len(set(funnel_counts.values())) != 1:
        errors.append(f"successful funnel counts differ: {funnel_counts}")
    expected_population = funnel_counts.get("SIGNAL_READY", 0)
    if expected_population < v1.MIN_COMPLETED_LIFECYCLES:
        errors.append(f"successful funnel population {expected_population} below frozen floor")

    for event, rows in events.items():
        dates = Counter(row.get("london_date", "") for row in rows)
        if any(not day or count != 1 for day, count in dates.items()):
            errors.append(f"{event} is not unique by london_date")
    date_sets = {event: {row["london_date"] for row in rows} for event, rows in events.items()}
    if len({frozenset(days) for days in date_sets.values()}) != 1:
        errors.append("successful funnel london_date sets differ")

    rejected_execution = [
        row
        for row in decisions
        if (row.get("event", "").startswith("ENTRY_") or row.get("event", "").startswith("EXIT_"))
        and row.get("status") not in {"REQUESTED", "ACCEPTED", "EXECUTED"}
    ]
    if rejected_execution:
        errors.append(f"execution telemetry contains {len(rejected_execution)} rejected/nonterminal rows")

    entry_deals = events["ENTRY_DEAL"]
    exit_deals = events["EXIT_DEAL"]
    entry_by_deal = keyed(entry_deals, "deal_id", "entry decisions", errors)
    exit_by_deal = keyed(exit_deals, "deal_id", "exit decisions", errors)
    if set(entry_by_deal) & set(exit_by_deal):
        errors.append("entry and exit deal ID sets overlap")
    lifecycle_by_deal = keyed(lifecycle, "deal", "lifecycle", errors)
    if set(lifecycle_by_deal) != set(entry_by_deal) | set(exit_by_deal):
        errors.append("lifecycle deal ID set differs from decision deal ID set")

    report_path = run_dir / "report.html"
    try:
        report_rows = [deal for deal in v1.parse_mt5_deals(report_path) if deal.symbol == contract["symbol"]]
    except Exception as exc:
        report_rows = []
        errors.append(f"real report parse failed: {exc}")
    report_by_deal: dict[int, Any] = {}
    for deal in report_rows:
        if deal.deal_id in report_by_deal:
            errors.append(f"report duplicate deal ID {deal.deal_id}")
        report_by_deal[deal.deal_id] = deal
    if set(report_by_deal) != set(entry_by_deal) | set(exit_by_deal):
        errors.append("report deal ID set differs from decision deal ID set")

    entry_by_date = {row["london_date"]: row for row in entry_deals}
    exit_by_date = {row["london_date"]: row for row in exit_deals}
    if set(entry_by_date) != set(exit_by_date):
        errors.append("entry/exit decision date sets differ")

    rows_by_event_date = {
        event: {row["london_date"]: row for row in rows}
        for event, rows in events.items()
    }
    unchanged_context = (
        "server_time", "utc_time", "london_time", "london_date", "scenario",
        "set_name", "hypothesis_id", "formation_sign", "polarity", "direction",
        "source_0800_server", "source_0830_server", "source_0800_open_bid",
        "source_0830_open_bid", "source_0800_shift", "source_0830_shift",
        "signal_observed_server", "entry_eligible_server", "bid", "ask",
        "spread_points",
    )
    for stage in ("ENTRY", "EXIT"):
        request_by_date = rows_by_event_date[f"{stage}_REQUEST"]
        submit_by_date = rows_by_event_date[f"{stage}_SUBMIT"]
        deal_by_date = rows_by_event_date[f"{stage}_DEAL"]
        for day in sorted(deal_by_date):
            request = request_by_date[day]
            submit = submit_by_date[day]
            deal = deal_by_date[day]
            for key in unchanged_context:
                if not (request.get(key) == submit.get(key) == deal.get(key)):
                    errors.append(f"{stage} request/submit/deal {key} mismatch on {day}")
            numeric_equal = (
                ("request/submit request_price", request["request_price"], submit["request_price"]),
                ("request/submit/deal volume", request["volume"], submit["volume"]),
                ("request/submit/deal volume", request["volume"], deal["volume"]),
                ("submit/deal actual price", submit["actual_deal_price"], deal["actual_deal_price"]),
            )
            for label, actual, expected in numeric_equal:
                try:
                    matches = abs(float(actual) - float(expected)) <= 1e-9
                except Exception:
                    matches = False
                if not matches:
                    errors.append(f"{stage} {label} mismatch on {day}")
            for key in ("order_id", "deal_id"):
                if submit.get(key) != deal.get(key):
                    errors.append(f"{stage} submit/deal {key} mismatch on {day}")
            if submit.get("retcode") != "10009":
                errors.append(f"{stage} submit retcode is not TRADE_RETCODE_DONE on {day}")
            if any(request.get(key) != "0" for key in ("order_id", "deal_id")):
                errors.append(f"{stage} request has non-sentinel order/deal identity on {day}")
            if float(deal.get("request_price", "nan")) != 0.0:
                errors.append(f"{stage} deal request_price sentinel mismatch on {day}")

            deal_position = deal.get("position_id")
            if stage == "ENTRY":
                if request.get("position_id") != "0" or submit.get("position_id") != "0":
                    errors.append(f"ENTRY request/submit position sentinel mismatch on {day}")
            elif not (request.get("position_id") == submit.get("position_id") == deal_position):
                errors.append(f"EXIT request/submit/deal position identity mismatch on {day}")

    positions: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in lifecycle:
        try:
            positions[int(row["position_id"])].append(row)
        except Exception:
            errors.append("lifecycle position_id malformed")
    if len(positions) != expected_population:
        errors.append(f"unique positions {len(positions)} != successful population {expected_population}")
    for position_id, rows in positions.items():
        actions = Counter(row.get("action") for row in rows)
        final_closes = sum(row.get("action") == "CLOSE" and row.get("is_final_close") == "1" for row in rows)
        if actions != Counter({"OPEN": 1, "CLOSE": 1}) or final_closes != 1:
            errors.append(f"position {position_id} is not exactly one OPEN plus one final CLOSE")

    for day, entry in entry_by_date.items():
        exit_row = exit_by_date.get(day)
        if exit_row is None:
            continue
        entry_deal = int(entry["deal_id"])
        exit_deal = int(exit_row["deal_id"])
        entry_position = int(entry["position_id"])
        exit_position = int(exit_row["position_id"])
        if entry_position != exit_position:
            errors.append(f"position identity mismatch on {day}")
        direction = int(entry["direction"])
        expected_entry_side = "buy" if direction > 0 else "sell"
        expected_exit_side = "sell" if direction > 0 else "buy"
        expected_position_side = expected_entry_side.upper()

        for label, decision, deal_id, direction_label, side in [
            ("entry", entry, entry_deal, "in", expected_entry_side),
            ("exit", exit_row, exit_deal, "out", expected_exit_side),
        ]:
            life = lifecycle_by_deal.get(deal_id)
            report = report_by_deal.get(deal_id)
            if life is None or report is None:
                continue
            if int(life["position_id"]) != entry_position:
                errors.append(f"{label} lifecycle position mismatch on {day}")
            if life["order_type"].upper() != expected_position_side:
                errors.append(f"{label} lifecycle position side mismatch on {day}")
            if report.direction.lower() != direction_label or report.side.lower() != side:
                errors.append(f"{label} report direction/side mismatch on {day}")
            if report.time != v1.parse_time(decision["server_time"]):
                errors.append(f"{label} report time mismatch on {day}")
            if report.order_id != int(decision["order_id"]):
                errors.append(f"{label} report order ID mismatch on {day}")
            values = [
                ("report/decision price", report.price, float(decision["actual_deal_price"])),
                ("lifecycle/decision price", float(life["price"]), float(decision["actual_deal_price"])),
                ("report/decision volume", report.volume, float(decision["volume"])),
                ("lifecycle/decision volume", float(life["volume"]), float(decision["volume"])),
            ]
            for value_label, actual, expected in values:
                if abs(actual - expected) > 1e-9:
                    errors.append(f"{label} {value_label} mismatch on {day}")
            if v1.parse_time(life["event_time"]) != v1.parse_time(decision["server_time"]):
                errors.append(f"{label} lifecycle time mismatch on {day}")

    errors.extend(clock_errors(decisions, scenario))

    decision_token = decision_path.stem.split("_DecisionTelemetry_", 1)[-1]
    lifecycle_token = lifecycle_path.stem.split("_LifecycleTrades_", 1)[-1]
    meta_token = meta_path.stem.split("_RunMeta_", 1)[-1]
    if len({decision_token, lifecycle_token, meta_token, str(meta.get("run_id", ""))}) != 1:
        errors.append("telemetry run token differs across sidecars/RunMeta")
    if str(meta.get("run_id", "")) == run_dir.name:
        errors.append("telemetry run token must remain distinct from AlphaFactory run directory ID")

    diag = meta.get("diagnostic", {})
    expected_diag = {
        "signals_ready": expected_population,
        "entries_attempted": expected_population,
        "entries_opened": expected_population,
        "entry_rejections": 0,
        "exposure_rejections": 0,
        "exit_requests": expected_population,
        "exit_rejections": 0,
        "entries_closed": expected_population,
        "overnight_violations": 0,
    }
    for key, expected in expected_diag.items():
        check_equal(errors, f"RunMeta diagnostic {key}", diag.get(key), expected)

    details = {
        "telemetry_run_token": meta.get("run_id"),
        "alpha_run_id": run_dir.name,
        "run_id_semantics": {
            "alpha_run_id": "directory/manifest identity",
            "telemetry_run_token": "unique sidecar token generated by the EA",
        },
        "successful_funnel_counts": funnel_counts,
        "unique_entry_deal_ids": len(entry_by_deal),
        "unique_exit_deal_ids": len(exit_by_deal),
        "unique_positions": len(positions),
        "report_deal_ids": len(report_by_deal),
        "clock_rows_checked": len(decisions),
        "first_eligible_tick_proof": "NOT_PROVEN_BEYOND_EVENT_TIMESTAMP_AND_ON_TICK_SOURCE_GATE",
    }
    return errors, details


@dataclass
class ScenarioResultV2:
    scenario: str
    run_dir: str
    passed: bool
    errors: list[str]
    base_v1_passed: bool
    provenance: dict[str, Any]
    identity: dict[str, Any]
    base_counts: dict[str, int]


def validate_scenario_v2(scenario: str, run_dir: Path) -> ScenarioResultV2:
    base = v1.validate_scenario(scenario, run_dir)
    provenance_errors, provenance = validate_provenance(scenario, run_dir)
    identity_errors, identity = validate_identity(scenario, run_dir)
    errors = [f"V1: {item}" for item in base.errors]
    errors.extend(f"PROVENANCE: {item}" for item in provenance_errors)
    errors.extend(f"IDENTITY: {item}" for item in identity_errors)
    return ScenarioResultV2(
        scenario=scenario,
        run_dir=str(run_dir.resolve()),
        passed=not errors,
        errors=errors,
        base_v1_passed=base.passed,
        provenance=provenance,
        identity=identity,
        base_counts=base.counts,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    for scenario in v1.SCENARIOS:
        parser.add_argument(f"--{scenario.lower().replace('_', '-')}", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    results = [
        validate_scenario_v2(scenario, getattr(args, scenario.lower()))
        for scenario in v1.SCENARIOS
    ]
    payload = {
        "schema_version": "lomx_execution_audit.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "audit_only": True,
        "performance_metrics_authorized": False,
        "economics_authorized": False,
        "parent_economic_verdict_unchanged": "KILLED",
        "canonical_alpha_analyzer_status": "UNSUPPORTED_NA_FOR_DECISIONTELEMETRY_LIFECYCLEV3",
        "first_eligible_tick_claim_authorized": False,
        "passed": all(item.passed for item in results),
        "scenario_results": [asdict(item) for item in results],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "passed": payload["passed"],
                "scenarios": {item.scenario: item.passed for item in results},
            }
        )
    )
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
