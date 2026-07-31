"""Hash-bound offline DESIGN probe for HYP-CME6E-RAWBREAK-BOOKSTATE-001.

This tool performs the first and only authorized outcome join for the frozen
2019-2020 DESIGN population. It never opens a CME OOS source, changes the
source-only feature surface, or simulates different trade management.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


MODULE_PATH = Path(__file__).resolve()
PACKAGE = MODULE_PATH.parents[1]
WORKSPACE = MODULE_PATH.parents[3]
HYPOTHESIS_ID = "HYP-CME6E-RAWBREAK-BOOKSTATE-001"
PREREG_SHA256 = "A1862A7173DA5AC063E0C2E23A872B69EB2966DB76EFE462D141C3177ED5E578"
FEATURE_SHA256 = "7BE51A64CB282DD5F11719B97206173F3A0D9D37A212A043B1AC5D45ACFC8BAD"
FEATURE_RECEIPT_SHA256 = "801BA6B1D6627367280C614E9B64D3F2D4CAAC4F096858632487CB1F85DEE9BB"
EXTRACTOR_SHA256 = "34A668CF89FEB9ED5A0D74E41E35B6C6B19E810E5BF6CC02AA6F36EE4FDBC4BB"
CONTROL_SHA256 = "07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9"
SOURCE_PLAN_SHA256 = "B780B7A4AD0F0C8B7CDF6A109DE41754C5F9CD88856D464085EE69513A1E24D5"
DOWNLOAD_MANIFEST_SHA256 = "7C83A964551B7A1F82E483173879A4468A076DA1D2D823E8C8F99A8A3034D38F"
VALIDATION_RECEIPT_SHA256 = "DC383862412E22652FBAA48365CB64D2453200C2727EF1B23AEFFEDD3D57FFFC"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"

THRESHOLD = -0.005025602742083225
ELAPSED_WEEKS = 730.0 / 7.0
EXPECTED_TOTAL = 547
EXPECTED_ELIGIBLE = 459
EXPECTED_CHALLENGER = 230
EXPECTED_BOTTOM = 229
COST_STRESSES = (0.5, 1.5, 2.25, 3.0)

PREREG_PATH = PACKAGE / "research" / f"{HYPOTHESIS_ID}_PROBE_PLAN.md"
FEATURE_PATH = WORKSPACE / "02. AlphaFactory" / "data" / "databento" / "cme_6e_raw_break_design" / "book_features_source_only.csv"
FEATURE_RECEIPT_PATH = FEATURE_PATH.with_name("book_features_source_only_receipt.json")
EXTRACTOR_PATH = PACKAGE / "research" / "extract_cme6e_raw_break_features.py"
SOURCE_PLAN_PATH = FEATURE_PATH.with_name("source_plan.json")
DOWNLOAD_MANIFEST_PATH = FEATURE_PATH.with_name("download_manifest.json")
VALIDATION_RECEIPT_PATH = FEATURE_PATH.with_name("validation_receipt.json")
CONTROL_PATH = WORKSPACE / "03. EA Developer" / "EA_SweepCascadeContinuation" / "research" / "evidence" / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS" / "control_trades.csv"
CLOCK_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
DSR_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "dsr.py"
REGISTRY_PATH = WORKSPACE / "04. Memory" / "research" / "CANDIDATE_REGISTRY.jsonl"
EVIDENCE_DIR = PACKAGE / "research" / "evidence" / f"{HYPOTHESIS_ID}_DESIGN"
TRIAL_LOG_PATH = PACKAGE / "research" / "trials" / "trial_log.jsonl"


class ProbeError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def workspace_rel(path: Path) -> str:
    return str(path.resolve().relative_to(WORKSPACE)).replace("\\", "/")


def require_sha(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ProbeError(f"SHA mismatch: {workspace_rel(path)} expected={expected} actual={actual}")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProbeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ProbeError(f"invalid boolean value: {value!r}")


def parse_server_time(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y.%m.%d %H:%M:%S")
    except ValueError as exc:
        raise ProbeError(f"invalid FivePercent decision time: {value}") from exc


def utc_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_feature_rows(path: Path = FEATURE_PATH) -> list[dict[str, Any]]:
    forbidden = {"net", "realized_r", "profit", "pnl", "exit", "close_time"}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        overlap = sorted(forbidden & {field.lower() for field in fields})
        if overlap:
            raise ProbeError(f"source-only feature file contains outcome columns: {overlap}")
        raw_rows = list(reader)
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        row = dict(raw)
        row["position_id"] = str(row["position_id"])
        row["direction"] = str(row["direction"]).upper()
        row["quality_eligible"] = parse_bool(row["quality_eligible"])
        score = str(row.get("book_alignment_score", "")).strip()
        row["book_alignment_score"] = float(score) if score else None
        rows.append(row)
    return rows


def load_frozen_design_outcomes(path: Path, allowed_ids: set[str]) -> list[dict[str, str]]:
    """Materialize only the 547 frozen DESIGN identities; never retain OOS rows."""
    materialized: list[dict[str, str]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"position_id", "decision_time", "direction", "volume", "net", "realized_r", "initial_risk_account"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ProbeError("control outcome ledger schema mismatch")
        for row in reader:
            position_id = str(row["position_id"])
            if position_id in allowed_ids:
                if position_id in seen:
                    raise ProbeError(f"duplicate control outcome identity: {position_id}")
                materialized.append({field: row[field] for field in required})
                seen.add(position_id)
                if seen == allowed_ids:
                    break
            elif parse_server_time(row["decision_time"]).year > 2020 and seen != allowed_ids:
                raise ProbeError("DESIGN outcome identity missing before sealed OOS boundary")
    if seen != allowed_ids:
        missing = sorted(allowed_ids - seen, key=int)
        raise ProbeError(f"missing DESIGN outcome identities: {missing[:10]}")
    return materialized


def join_design_rows(
    features: list[dict[str, Any]],
    outcomes: list[dict[str, Any]],
    server_to_utc: Callable[[datetime], datetime],
) -> list[dict[str, Any]]:
    feature_ids = [str(row["position_id"]) for row in features]
    if len(set(feature_ids)) != len(feature_ids):
        raise ProbeError("duplicate source feature identity")
    outcome_by_id: dict[str, dict[str, Any]] = {}
    for outcome in outcomes:
        position_id = str(outcome["position_id"])
        if position_id in outcome_by_id:
            raise ProbeError(f"duplicate outcome identity: {position_id}")
        outcome_by_id[position_id] = outcome
    if set(outcome_by_id) != set(feature_ids):
        raise ProbeError("feature/outcome identity set mismatch")

    joined: list[dict[str, Any]] = []
    for source in features:
        position_id = str(source["position_id"])
        outcome = outcome_by_id[position_id]
        source_direction = str(source["direction"]).upper()
        outcome_direction = str(outcome["direction"]).upper()
        if source_direction != outcome_direction:
            raise ProbeError(f"direction mismatch for position {position_id}")
        server_time = parse_server_time(str(outcome["decision_time"]))
        decision_utc = utc_iso(server_to_utc(server_time))
        if decision_utc != str(source["end"]):
            raise ProbeError(
                f"decision clock mismatch for position {position_id}: source={source['end']} outcome={decision_utc}"
            )
        row = dict(source)
        row.update(
            {
                "decision_time_server": str(outcome["decision_time"]),
                "decision_time_utc": decision_utc,
                "decision_year": int(decision_utc[:4]),
                "volume": float(outcome["volume"]),
                "initial_risk_account": float(outcome["initial_risk_account"]),
                "net": float(outcome["net"]),
                "realized_r": float(outcome["realized_r"]),
            }
        )
        joined.append(row)
    joined.sort(key=lambda row: (row["decision_time_utc"], int(row["position_id"])))
    return joined


def select_frozen_populations(rows: list[dict[str, Any]], threshold: float = THRESHOLD) -> dict[str, list[dict[str, Any]]]:
    eligible = [row for row in rows if parse_bool(row["quality_eligible"])]
    challenger = [row for row in eligible if float(row["book_alignment_score"]) >= threshold]
    bottom = [row for row in eligible if float(row["book_alignment_score"]) < threshold]
    return {
        "CONTROL_QUALITY_ELIGIBLE": eligible,
        "CHALLENGER_TOP50_SCORE": challenger,
        "NEGATIVE_CONTROL_BOTTOM50_SCORE": bottom,
    }


def profit_factor(values: Iterable[float]) -> float | None:
    values = list(values)
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    if gross_loss == 0:
        return None
    return gross_profit / gross_loss


def moment_shape(values: list[float]) -> tuple[float, float, float]:
    if len(values) < 2:
        return 0.0, 0.0, 3.0
    mean = statistics.fmean(values)
    std = statistics.stdev(values)
    if std == 0:
        return 0.0, 0.0, 3.0
    sr = mean / std
    m2 = statistics.fmean((value - mean) ** 2 for value in values)
    m3 = statistics.fmean((value - mean) ** 3 for value in values)
    m4 = statistics.fmean((value - mean) ** 4 for value in values)
    skew = m3 / (m2 ** 1.5) if m2 > 0 else 0.0
    kurt = m4 / (m2 * m2) if m2 > 0 else 3.0
    return sr, skew, kurt


def native_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    nets = [float(row["net"]) for row in rows]
    realized = [float(row["realized_r"]) for row in rows]
    sr, skew, kurt = moment_shape(realized)
    return {
        "count": len(rows),
        "gross_profit": sum(value for value in nets if value > 0),
        "gross_loss": sum(value for value in nets if value < 0),
        "net": sum(nets),
        "profit_factor": profit_factor(nets),
        "mean_realized_r": statistics.fmean(realized) if realized else None,
        "median_realized_r": statistics.median(realized) if realized else None,
        "win_rate": sum(value > 0 for value in nets) / len(nets) if nets else None,
        "per_trade_sharpe": sr,
        "skew": skew,
        "non_excess_kurtosis": kurt,
    }


def bucket_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    native = native_metrics(rows)
    return {
        "count": native["count"],
        "profit_factor": native["profit_factor"],
        "net": native["net"],
        "mean_realized_r": native["mean_realized_r"],
    }


def arm_metrics(rows: list[dict[str, Any]], elapsed_weeks: float = ELAPSED_WEEKS) -> dict[str, Any]:
    native = native_metrics(rows)
    cost_stress: dict[str, Any] = {}
    for pips in COST_STRESSES:
        stressed = [float(row["net"]) - pips * float(row["volume"]) * 10.0 for row in rows]
        cost_stress[str(pips)] = {
            "round_trip_pips": pips,
            "net": sum(stressed),
            "profit_factor": profit_factor(stressed),
            "epistemic_class": "UNVERIFIED_PROXY",
        }
    by_year = {
        str(year): bucket_metrics([row for row in rows if int(row["decision_year"]) == year])
        for year in (2019, 2020)
    }
    by_direction = {
        direction: bucket_metrics([row for row in rows if str(row["direction"]).upper() == direction])
        for direction in ("BUY", "SELL")
    }
    return {
        "count": len(rows),
        "cadence_per_elapsed_week": len(rows) / elapsed_weeks,
        "elapsed_weeks": elapsed_weeks,
        "native": native,
        "cost_stress": cost_stress,
        "by_year": by_year,
        "by_direction": by_direction,
    }


def metric_gte(value: Any, floor: float) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) >= floor


def metric_gt(value: Any, floor: float) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) > floor


def evaluate_gates(
    control: dict[str, Any],
    challenger: dict[str, Any],
    bottom: dict[str, Any],
    *,
    dsr_value: float,
    integrity_pass: bool,
) -> dict[str, Any]:
    if not integrity_pass:
        return {
            "verdict": "PARK_INVALID_BOOK_FEATURE_OR_JOIN",
            "gates": {"integrity": False},
            "passed": 0,
            "total": 11,
        }
    c_native = challenger["native"]
    control_native = control["native"]
    bottom_native = bottom["native"]
    years_pass = all(
        metric_gt(challenger["by_year"][str(year)]["profit_factor"], 1.0)
        and metric_gt(challenger["by_year"][str(year)]["mean_realized_r"], 0.0)
        for year in (2019, 2020)
    )
    directions_pass = all(
        metric_gt(challenger["by_direction"][direction]["profit_factor"], 1.0)
        and metric_gt(challenger["by_direction"][direction]["mean_realized_r"], 0.0)
        for direction in ("BUY", "SELL")
    )
    gates = {
        "integrity": True,
        "challenger_n230_cadence_2_to_5": challenger["count"] == EXPECTED_CHALLENGER
        and 2.0 <= challenger["cadence_per_elapsed_week"] <= 5.0,
        "native_pf_gte_1_30": metric_gte(c_native["profit_factor"], 1.30),
        "native_mean_r_gte_0_08": metric_gte(c_native["mean_realized_r"], 0.08),
        "stress_1_5_pf_gte_1_25": metric_gte(challenger["cost_stress"]["1.5"]["profit_factor"], 1.25),
        "stress_2_25_pf_gte_1_00": metric_gte(challenger["cost_stress"]["2.25"]["profit_factor"], 1.00),
        "both_years_pf_gt_1_mean_r_gt_0": years_pass,
        "both_directions_pf_gt_1_mean_r_gt_0": directions_pass,
        "vs_quality_control_pf_lift_0_15_mean_r_lift_0_10": (
            c_native["profit_factor"] is not None
            and control_native["profit_factor"] is not None
            and c_native["profit_factor"] - control_native["profit_factor"] >= 0.15
            and c_native["mean_realized_r"] - control_native["mean_realized_r"] >= 0.10
        ),
        "vs_bottom_pf_lift_0_20_mean_r_lift_0_15": (
            c_native["profit_factor"] is not None
            and bottom_native["profit_factor"] is not None
            and c_native["profit_factor"] - bottom_native["profit_factor"] >= 0.20
            and c_native["mean_realized_r"] - bottom_native["mean_realized_r"] >= 0.15
        ),
        "dsr_gte_0_95": metric_gte(dsr_value, 0.95),
    }
    passed = sum(gates.values())
    verdict = (
        "FLAG_DESIGN_SURVIVOR_OOS_STILL_SEALED"
        if passed == len(gates)
        else "KILL_DESIGN_BOOK_ALIGNMENT_NO_POSITIVE_EXPECTANCY"
    )
    return {"verdict": verdict, "gates": gates, "passed": passed, "total": len(gates)}


def compute_dsr(arms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sharpe_values = [arms[name]["native"]["per_trade_sharpe"] for name in (
        "CONTROL_QUALITY_ELIGIBLE", "CHALLENGER_TOP50_SCORE", "NEGATIVE_CONTROL_BOTTOM50_SCORE"
    )]
    var_sr = statistics.variance(sharpe_values)
    candidate = arms["CHALLENGER_TOP50_SCORE"]["native"]
    dsr_module = load_module(DSR_PATH, "canonical_dsr")
    value = dsr_module.dsr(
        candidate["per_trade_sharpe"],
        candidate["count"],
        candidate["skew"],
        candidate["non_excess_kurtosis"],
        var_sr,
        3,
    )
    return {
        "value": value,
        "n_trials": 3,
        "var_sr_trials": var_sr,
        "arm_per_trade_sharpes": sharpe_values,
        "kurtosis_convention": "non-excess",
    }


def validate_registry_binding() -> None:
    matching: list[dict[str, Any]] = []
    with REGISTRY_PATH.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matching.append(row)
    if len(matching) != 1:
        raise ProbeError(f"expected exactly one preregistered row, got {len(matching)}")
    row = matching[0]
    if row.get("state") != "probe" or row.get("prereg_sha256") != PREREG_SHA256:
        raise ProbeError("registry row does not authorize the frozen DESIGN probe")
    validation = row.get("validation", {})
    if validation.get("performance_metrics_authorized") is not True:
        raise ProbeError("registry does not authorize DESIGN performance metrics")
    if validation.get("model0_authorized") is not False:
        raise ProbeError("registry unexpectedly authorizes Model 0")


def validate_frozen_inputs() -> None:
    bindings = (
        (PREREG_PATH, PREREG_SHA256),
        (FEATURE_PATH, FEATURE_SHA256),
        (FEATURE_RECEIPT_PATH, FEATURE_RECEIPT_SHA256),
        (EXTRACTOR_PATH, EXTRACTOR_SHA256),
        (CONTROL_PATH, CONTROL_SHA256),
        (SOURCE_PLAN_PATH, SOURCE_PLAN_SHA256),
        (DOWNLOAD_MANIFEST_PATH, DOWNLOAD_MANIFEST_SHA256),
        (VALIDATION_RECEIPT_PATH, VALIDATION_RECEIPT_SHA256),
        (CLOCK_PATH, CLOCK_SHA256),
        (DSR_PATH, DSR_SHA256),
    )
    for path, expected in bindings:
        require_sha(path, expected)
    feature_receipt = json.loads(FEATURE_RECEIPT_PATH.read_text(encoding="utf-8"))
    if feature_receipt.get("outcome_fields_used") is not False:
        raise ProbeError("feature receipt reports outcome access")
    if feature_receipt.get("sealed_oos_opened") is not False:
        raise ProbeError("feature receipt reports sealed OOS access")
    validation_receipt = json.loads(VALIDATION_RECEIPT_PATH.read_text(encoding="utf-8"))
    if validation_receipt.get("sealed_oos_opened") is not False:
        raise ProbeError("raw validation receipt reports sealed OOS access")
    validate_registry_binding()


def csv_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value)
    return value


def write_joined_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    source_fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=source_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_scalar(row.get(field)) for field in source_fields})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def append_trial_log(rows: list[dict[str, Any]]) -> None:
    TRIAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = TRIAL_LOG_PATH.read_text(encoding="utf-8") if TRIAL_LOG_PATH.exists() else ""
    for line in existing.splitlines():
        if line.strip() and json.loads(line).get("hypothesis_id") == HYPOTHESIS_ID:
            raise ProbeError("trial log already contains this hypothesis; refusing duplicate execution")
    with TRIAL_LOG_PATH.open("a", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def main() -> int:
    validate_frozen_inputs()
    features = load_feature_rows()
    if len(features) != EXPECTED_TOTAL or len({row["position_id"] for row in features}) != EXPECTED_TOTAL:
        raise ProbeError("source-only DESIGN population must contain exactly 547 unique rows")
    populations_source = select_frozen_populations(features)
    expected_counts = {
        "CONTROL_QUALITY_ELIGIBLE": EXPECTED_ELIGIBLE,
        "CHALLENGER_TOP50_SCORE": EXPECTED_CHALLENGER,
        "NEGATIVE_CONTROL_BOTTOM50_SCORE": EXPECTED_BOTTOM,
    }
    actual_counts = {name: len(rows) for name, rows in populations_source.items()}
    if actual_counts != expected_counts:
        raise ProbeError(f"frozen source population mismatch: {actual_counts}")

    clock_module = load_module(CLOCK_PATH, "fivepercent_server_clock")
    allowed_ids = {row["position_id"] for row in features}
    outcomes = load_frozen_design_outcomes(CONTROL_PATH, allowed_ids)
    joined = join_design_rows(features, outcomes, clock_module.server_to_utc)
    if {row["decision_year"] for row in joined} != {2019, 2020}:
        raise ProbeError("joined ledger crossed the frozen DESIGN year boundary")
    populations = select_frozen_populations(joined)
    if {name: len(rows) for name, rows in populations.items()} != expected_counts:
        raise ProbeError("joined population counts changed after outcome access")

    arms = {name: arm_metrics(rows) for name, rows in populations.items()}
    dsr_result = compute_dsr(arms)
    gate_result = evaluate_gates(
        arms["CONTROL_QUALITY_ELIGIBLE"],
        arms["CHALLENGER_TOP50_SCORE"],
        arms["NEGATIVE_CONTROL_BOTTOM50_SCORE"],
        dsr_value=dsr_result["value"],
        integrity_pass=True,
    )

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    joined_path = EVIDENCE_DIR / "joined_design_trades.csv"
    result_path = EVIDENCE_DIR / "probe_result.json"
    receipt_path = EVIDENCE_DIR / "reconciliation_receipt.json"
    if any(path.exists() for path in (joined_path, result_path, receipt_path)):
        raise ProbeError("probe evidence already exists; refusing an implicit rerun")
    write_joined_csv(joined_path, joined)

    result = {
        "schema_version": "cme6e_raw_break_book_state_design_probe.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": generated_at,
        "verdict": gate_result["verdict"],
        "epistemic_class": "VALID_OFFLINE_DESIGN_ECONOMIC_PROBE_UNVERIFIED_PROXY_COSTS_OOS_SEALED",
        "frozen_threshold": THRESHOLD,
        "elapsed_weeks": ELAPSED_WEEKS,
        "arms": arms,
        "dsr": dsr_result,
        "gate_result": gate_result,
        "prohibitions": [
            "no alternate threshold or subgroup rescue under this hypothesis",
            "no OOS quote, source acquisition, feature extraction or outcome join",
            "no MQL5, Model 0, promotion, paper or live authority",
            "cost stresses are UNVERIFIED_PROXY and not broker cost truth",
        ],
    }
    write_json(result_path, result)

    trial_rows = [
        {
            "schema_version": "alphafactory_trial_log.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "prereg_sha256": PREREG_SHA256,
            "generated_at_utc": generated_at,
            "trial_number": index,
            "arm": name,
            "metrics": arms[name],
            "joined_ledger_sha256": sha256_file(joined_path),
            "sealed_oos_opened": False,
        }
        for index, name in enumerate(
            ("CONTROL_QUALITY_ELIGIBLE", "CHALLENGER_TOP50_SCORE", "NEGATIVE_CONTROL_BOTTOM50_SCORE"),
            start=1,
        )
    ]
    append_trial_log(trial_rows)
    receipt = {
        "schema_version": "cme6e_raw_break_book_state_reconciliation.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "generated_at_utc": generated_at,
        "status": "PASS",
        "prereg_sha256": PREREG_SHA256,
        "probe_script_sha256": sha256_file(MODULE_PATH),
        "inputs": {
            workspace_rel(FEATURE_PATH): FEATURE_SHA256,
            workspace_rel(FEATURE_RECEIPT_PATH): FEATURE_RECEIPT_SHA256,
            workspace_rel(CONTROL_PATH): CONTROL_SHA256,
            workspace_rel(CLOCK_PATH): CLOCK_SHA256,
            workspace_rel(DSR_PATH): DSR_SHA256,
        },
        "outputs": {
            workspace_rel(joined_path): sha256_file(joined_path),
            workspace_rel(result_path): sha256_file(result_path),
            workspace_rel(TRIAL_LOG_PATH): sha256_file(TRIAL_LOG_PATH),
        },
        "source_rows": EXPECTED_TOTAL,
        "control_rows_materialized": EXPECTED_TOTAL,
        "oos_rows_materialized": 0,
        "population_counts": actual_counts,
        "trials_executed": 3,
        "sealed_oos_opened": False,
        "cme_oos_quoted": False,
        "cme_oos_downloaded": False,
        "source_feature_threshold_changed": False,
    }
    write_json(receipt_path, receipt)
    print(
        "CME6E_RAW_BREAK_DESIGN_PROBE "
        f"verdict={gate_result['verdict']} gates={gate_result['passed']}/{gate_result['total']} "
        f"challenger_n={arms['CHALLENGER_TOP50_SCORE']['count']} "
        f"pf={arms['CHALLENGER_TOP50_SCORE']['native']['profit_factor']:.9f} "
        f"mean_r={arms['CHALLENGER_TOP50_SCORE']['native']['mean_realized_r']:.9f} "
        f"dsr={dsr_result['value']:.9f} oos_opened=false"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeError as exc:
        print(f"CME6E_RAW_BREAK_DESIGN_PROBE status=FAIL_CLOSED error={exc}")
        raise SystemExit(2)
