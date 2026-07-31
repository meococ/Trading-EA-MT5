"""Hash-bound offline DESIGN probe for HYP-CME6E-RAWBREAK-BOOKTRANSITION-002.

The source-only score and population were frozen before this tool was allowed
to read the parent trade outcomes. This tool performs one exact 2021-2022
DESIGN join; it does not authorize a threshold search, EA build, or deployment.
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

HYPOTHESIS_ID = "HYP-CME6E-RAWBREAK-BOOKTRANSITION-002"
PREREG_SHA256 = "E0E7040E29EB2A37D11532293C298167D7C429618B38D722C9D1599AF799A894"
FEATURE_SHA256 = "E8CEA705489AEB3BF684CE0949924BB5FB1D9EAA030779B5E58911F6A7EE2B49"
FEATURE_RECEIPT_SHA256 = "6C4E48E1DEE15DE22DD92989DFCB871CF70B110C87C6545C616FE2202C3C389C"
EXTRACTOR_SHA256 = "E1DA8963A05FFFCDF3745E02EB1051B5E54DADCCD998145B3B6DEE6A3DA1402B"
CONTROL_SHA256 = "07CDBD82D9BE6B9745484E5312F534B72C883AF8B61D8FB240D28EEE72FDC0D9"
SOURCE_PLAN_SHA256 = "BF478C4FF9B181E0BC7C38E55C9613D69B44DBF348CBC351EC0909583E25D7F6"
DOWNLOAD_MANIFEST_SHA256 = "5E2DFCB42E451104C9C9A941610BE514839C85129BB3E457EAA9BA4B7FC1BC52"
VALIDATION_RECEIPT_SHA256 = "4771964FFA829A152C8F45D91C8F058FC48CCAF63536428B4E52C78B8D4382FB"
CLOCK_SHA256 = "A7F179935102B57BA3B629345209F6B0D668D1F7FD828A5ED6003207F41A2F52"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
TRIAL_HELPER_SHA256 = "DECFBE0A9613A3145075D6EBF247813C0E72679D6314636535D341A0C1934AD3"

THRESHOLD = -0.012342488801680875
ELAPSED_WEEKS = 729.0 / 7.0
EXPECTED_TOTAL = 565
EXPECTED_ELIGIBLE = 516
EXPECTED_CHALLENGER = 258
EXPECTED_BOTTOM = 258
COST_STRESSES = (0.5, 1.5, 2.25, 3.0)

PREREG_PATH = PACKAGE / "research" / f"{HYPOTHESIS_ID}_PROBE_PLAN.md"
SOURCE_ROOT = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "databento"
    / "cme_6e_breakbar_transition_design"
)
FEATURE_PATH = SOURCE_ROOT / "book_transition_features_source_only.csv"
FEATURE_RECEIPT_PATH = SOURCE_ROOT / "book_transition_feature_receipt.json"
EXTRACTOR_PATH = PACKAGE / "research" / "extract_cme6e_breakbar_transition_features.py"
SOURCE_PLAN_PATH = SOURCE_ROOT / "source_plan.json"
DOWNLOAD_MANIFEST_PATH = SOURCE_ROOT / "download_manifest.json"
VALIDATION_RECEIPT_PATH = SOURCE_ROOT / "validation_receipt.json"
CONTROL_PATH = (
    WORKSPACE
    / "03. EA Developer"
    / "EA_SweepCascadeContinuation"
    / "research"
    / "evidence"
    / "HYP-SCC-MT5-REPLICATION-EURUSD-M5-004_PAIR_ANALYSIS"
    / "control_trades.csv"
)
CLOCK_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "fivepercent_server_clock.py"
DSR_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "dsr.py"
TRIAL_HELPER_PATH = WORKSPACE / "02. AlphaFactory" / "tools" / "research" / "trial_log.py"
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
        raise ProbeError(
            f"SHA mismatch: {workspace_rel(path)} expected={expected} actual={actual}"
        )


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
        raise ProbeError(f"invalid FivePercent time: {value}") from exc


def utc_iso(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_feature_rows(path: Path = FEATURE_PATH) -> list[dict[str, Any]]:
    forbidden = {
        "net",
        "realized_r",
        "profit",
        "pnl",
        "exit",
        "close_time",
        "open_time",
        "decision_time",
    }
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = {field.lower() for field in (reader.fieldnames or [])}
        overlap = sorted(forbidden & fields)
        if overlap:
            raise ProbeError(
                f"source-only feature file contains outcome columns: {overlap}"
            )
        raw_rows = list(reader)
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        row = dict(raw)
        row["position_id"] = str(row["position_id"])
        row["direction"] = str(row["direction"]).upper()
        row["quality_eligible"] = parse_bool(row["quality_eligible"])
        score = str(row.get("book_transition_score", "")).strip()
        row["book_transition_score"] = float(score) if score else None
        rows.append(row)
    return rows


def load_frozen_design_outcomes(
    path: Path, allowed_ids: set[str]
) -> list[dict[str, str]]:
    """Materialize exactly the frozen HYP-002 DESIGN identities."""
    required = {
        "position_id",
        "decision_time",
        "open_time",
        "direction",
        "volume",
        "net",
        "realized_r",
        "initial_risk_account",
    }
    materialized: list[dict[str, str]] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not required.issubset(set(reader.fieldnames or [])):
            raise ProbeError("control outcome ledger schema mismatch")
        for row in reader:
            position_id = str(row["position_id"])
            if position_id not in allowed_ids:
                continue
            if position_id in seen:
                raise ProbeError(f"duplicate control outcome identity: {position_id}")
            materialized.append({field: row[field] for field in required})
            seen.add(position_id)
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

        decision_utc = utc_iso(
            server_to_utc(parse_server_time(str(outcome["decision_time"])))
        )
        entry_utc = utc_iso(
            server_to_utc(parse_server_time(str(outcome["open_time"])))
        )
        if decision_utc != str(source["break_bar_open"]):
            raise ProbeError(
                "break-bar clock mismatch for position "
                f"{position_id}: source={source['break_bar_open']} outcome={decision_utc}"
            )
        if entry_utc != str(source["actual_decision"]):
            raise ProbeError(
                "entry clock mismatch for position "
                f"{position_id}: source={source['actual_decision']} outcome={entry_utc}"
            )

        row = dict(source)
        row.update(
            {
                "decision_time_server": str(outcome["decision_time"]),
                "open_time_server": str(outcome["open_time"]),
                "break_bar_open_utc": decision_utc,
                "actual_decision_utc": entry_utc,
                "decision_year": int(entry_utc[:4]),
                "volume": float(outcome["volume"]),
                "initial_risk_account": float(outcome["initial_risk_account"]),
                "net": float(outcome["net"]),
                "realized_r": float(outcome["realized_r"]),
            }
        )
        joined.append(row)
    joined.sort(key=lambda row: (row["actual_decision_utc"], int(row["position_id"])))
    return joined


def select_frozen_populations(
    rows: list[dict[str, Any]], threshold: float = THRESHOLD
) -> dict[str, list[dict[str, Any]]]:
    eligible = [row for row in rows if parse_bool(row["quality_eligible"])]
    challenger = [
        row
        for row in eligible
        if float(row["book_transition_score"]) >= threshold
    ]
    bottom = [
        row
        for row in eligible
        if float(row["book_transition_score"]) < threshold
    ]
    return {
        "CONTROL_QUALITY_ELIGIBLE": eligible,
        "CHALLENGER_TOP50_TRANSITION_SCORE": challenger,
        "NEGATIVE_CONTROL_BOTTOM50_TRANSITION_SCORE": bottom,
    }


def profit_factor(values: Iterable[float]) -> float | None:
    materialized = list(values)
    gross_profit = sum(value for value in materialized if value > 0)
    gross_loss = -sum(value for value in materialized if value < 0)
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
    skew = m3 / (m2**1.5) if m2 > 0 else 0.0
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


def arm_metrics(
    rows: list[dict[str, Any]], elapsed_weeks: float = ELAPSED_WEEKS
) -> dict[str, Any]:
    native = native_metrics(rows)
    cost_stress: dict[str, Any] = {}
    for pips in COST_STRESSES:
        stressed = [
            float(row["net"]) - pips * float(row["volume"]) * 10.0
            for row in rows
        ]
        cost_stress[str(pips)] = {
            "round_trip_pips": pips,
            "net": sum(stressed),
            "profit_factor": profit_factor(stressed),
            "epistemic_class": "UNVERIFIED_PROXY",
        }
    by_year = {
        str(year): bucket_metrics(
            [row for row in rows if int(row["decision_year"]) == year]
        )
        for year in (2021, 2022)
    }
    by_direction = {
        direction: bucket_metrics(
            [row for row in rows if str(row["direction"]).upper() == direction]
        )
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
            "verdict": "PARK_INVALID_BREAKBAR_BOOK_FEATURE_OR_JOIN",
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
        for year in (2021, 2022)
    )
    directions_pass = all(
        metric_gt(challenger["by_direction"][direction]["profit_factor"], 1.0)
        and metric_gt(
            challenger["by_direction"][direction]["mean_realized_r"], 0.0
        )
        for direction in ("BUY", "SELL")
    )
    gates = {
        "integrity": True,
        "challenger_n258_cadence_2_to_5": challenger["count"]
        == EXPECTED_CHALLENGER
        and 2.0 <= challenger["cadence_per_elapsed_week"] <= 5.0,
        "native_pf_gte_1_30": metric_gte(c_native["profit_factor"], 1.30),
        "native_mean_r_gte_0_08": metric_gte(c_native["mean_realized_r"], 0.08),
        "stress_1_5_pf_gte_1_25": metric_gte(
            challenger["cost_stress"]["1.5"]["profit_factor"], 1.25
        ),
        "stress_2_25_pf_gte_1_00": metric_gte(
            challenger["cost_stress"]["2.25"]["profit_factor"], 1.00
        ),
        "both_years_pf_gt_1_mean_r_gt_0": years_pass,
        "both_directions_pf_gt_1_mean_r_gt_0": directions_pass,
        "vs_quality_control_pf_lift_0_15_mean_r_lift_0_10": (
            c_native["profit_factor"] is not None
            and control_native["profit_factor"] is not None
            and c_native["profit_factor"] - control_native["profit_factor"]
            >= 0.15
            and c_native["mean_realized_r"] - control_native["mean_realized_r"]
            >= 0.10
        ),
        "vs_bottom_pf_lift_0_20_mean_r_lift_0_15": (
            c_native["profit_factor"] is not None
            and bottom_native["profit_factor"] is not None
            and c_native["profit_factor"] - bottom_native["profit_factor"] >= 0.20
            and c_native["mean_realized_r"] - bottom_native["mean_realized_r"]
            >= 0.15
        ),
        "dsr_gte_0_95": metric_gte(dsr_value, 0.95),
    }
    passed = sum(gates.values())
    verdict = (
        "FLAG_DESIGN_BREAKBAR_TRANSITION_SURVIVOR_NEEDS_FRESH_VALIDATION"
        if passed == len(gates)
        else "KILL_DESIGN_BREAKBAR_BOOK_TRANSITION_NO_POSITIVE_EXPECTANCY"
    )
    return {"verdict": verdict, "gates": gates, "passed": passed, "total": len(gates)}


def compute_dsr(arms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    names = (
        "CONTROL_QUALITY_ELIGIBLE",
        "CHALLENGER_TOP50_TRANSITION_SCORE",
        "NEGATIVE_CONTROL_BOTTOM50_TRANSITION_SCORE",
    )
    sharpe_values = [arms[name]["native"]["per_trade_sharpe"] for name in names]
    var_sr = statistics.variance(sharpe_values)
    candidate = arms["CHALLENGER_TOP50_TRANSITION_SCORE"]["native"]
    dsr_module = load_module(DSR_PATH, "canonical_dsr_hyp002")
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
        (TRIAL_HELPER_PATH, TRIAL_HELPER_SHA256),
    )
    for path, expected in bindings:
        require_sha(path, expected)
    feature_receipt = json.loads(FEATURE_RECEIPT_PATH.read_text(encoding="utf-8"))
    if feature_receipt.get("outcome_fields_used") is not False:
        raise ProbeError("feature receipt reports outcome access")
    if feature_receipt.get("outcomes_opened") is not False:
        raise ProbeError("source-only feature receipt reports opened outcomes")
    if feature_receipt.get("prior_hypothesis_oos_opened") is not False:
        raise ProbeError("source-only receipt reports HYP-001 OOS access")
    validation_receipt = json.loads(
        VALIDATION_RECEIPT_PATH.read_text(encoding="utf-8")
    )
    if validation_receipt.get("outcome_fields_used") is not False:
        raise ProbeError("raw validation receipt reports outcome access")
    validate_registry_binding()


def write_joined_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def append_trial_rows(rows: list[dict[str, Any]]) -> None:
    if TRIAL_LOG_PATH.exists():
        for line in TRIAL_LOG_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("hypothesis_id") == HYPOTHESIS_ID:
                raise ProbeError(
                    "trial log already contains this hypothesis; refusing duplicate execution"
                )
    trial_helper = load_module(TRIAL_HELPER_PATH, "canonical_trial_log_hyp002")
    for row in rows:
        trial_helper.append_trial(TRIAL_LOG_PATH, row)


def main() -> int:
    validate_frozen_inputs()
    features = load_feature_rows()
    if len(features) != EXPECTED_TOTAL or len(
        {row["position_id"] for row in features}
    ) != EXPECTED_TOTAL:
        raise ProbeError("source-only DESIGN population must contain 565 unique rows")

    populations_source = select_frozen_populations(features)
    expected_counts = {
        "CONTROL_QUALITY_ELIGIBLE": EXPECTED_ELIGIBLE,
        "CHALLENGER_TOP50_TRANSITION_SCORE": EXPECTED_CHALLENGER,
        "NEGATIVE_CONTROL_BOTTOM50_TRANSITION_SCORE": EXPECTED_BOTTOM,
    }
    actual_counts = {
        name: len(rows) for name, rows in populations_source.items()
    }
    if actual_counts != expected_counts:
        raise ProbeError(f"frozen source population mismatch: {actual_counts}")

    clock_module = load_module(CLOCK_PATH, "fivepercent_server_clock_hyp002")
    allowed_ids = {row["position_id"] for row in features}
    outcomes = load_frozen_design_outcomes(CONTROL_PATH, allowed_ids)
    joined = join_design_rows(features, outcomes, clock_module.server_to_utc)
    if {row["decision_year"] for row in joined} != {2021, 2022}:
        raise ProbeError("joined ledger crossed the frozen HYP-002 DESIGN boundary")
    populations = select_frozen_populations(joined)
    if {name: len(rows) for name, rows in populations.items()} != expected_counts:
        raise ProbeError("joined population counts changed after outcome access")

    arms = {name: arm_metrics(rows) for name, rows in populations.items()}
    dsr_result = compute_dsr(arms)
    gate_result = evaluate_gates(
        arms["CONTROL_QUALITY_ELIGIBLE"],
        arms["CHALLENGER_TOP50_TRANSITION_SCORE"],
        arms["NEGATIVE_CONTROL_BOTTOM50_TRANSITION_SCORE"],
        dsr_value=dsr_result["value"],
        integrity_pass=True,
    )

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    run_id = datetime.now(timezone.utc).strftime("CME6E_BREAKBAR_DESIGN_%Y%m%d_%H%M%SZ")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    joined_path = EVIDENCE_DIR / "joined_design_trades.csv"
    result_path = EVIDENCE_DIR / "probe_result.json"
    receipt_path = EVIDENCE_DIR / "reconciliation_receipt.json"
    if any(path.exists() for path in (joined_path, result_path, receipt_path)):
        raise ProbeError("probe evidence already exists; refusing an implicit rerun")
    write_joined_csv(joined_path, joined)

    result = {
        "schema_version": "cme6e_breakbar_transition_design_probe.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": run_id,
        "generated_at_utc": generated_at,
        "verdict": gate_result["verdict"],
        "epistemic_class": (
            "VALID_OFFLINE_DESIGN_ECONOMIC_PROBE_UNVERIFIED_PROXY_COSTS_"
            "NO_HOLDOUT"
        ),
        "frozen_threshold": THRESHOLD,
        "elapsed_weeks": ELAPSED_WEEKS,
        "arms": arms,
        "dsr": dsr_result,
        "gate_result": gate_result,
        "prohibitions": [
            "no alternate threshold or subgroup rescue under this hypothesis",
            "no claim that HYP-001 was reopened or amended",
            "no MQL5, Model 0, promotion, paper or live authority",
            "cost stresses are UNVERIFIED_PROXY and not broker cost truth",
            "a survivor needs separately preregistered fresh validation data",
        ],
    }
    write_json(result_path, result)

    joined_sha = sha256_file(joined_path)
    trial_rows = [
        {
            "schema_version": "alphafactory_trial_log.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "prereg_sha256": PREREG_SHA256,
            "generated_at_utc": generated_at,
            "run_id": run_id,
            "trial_number": index,
            "arm": name,
            "metrics": arms[name],
            "joined_ledger_sha256": joined_sha,
            "holdout_opened": False,
            "prior_hypothesis_oos_opened": False,
        }
        for index, name in enumerate(
            (
                "CONTROL_QUALITY_ELIGIBLE",
                "CHALLENGER_TOP50_TRANSITION_SCORE",
                "NEGATIVE_CONTROL_BOTTOM50_TRANSITION_SCORE",
            ),
            start=1,
        )
    ]
    append_trial_rows(trial_rows)

    receipt = {
        "schema_version": "cme6e_breakbar_transition_reconciliation.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "run_id": run_id,
        "generated_at_utc": generated_at,
        "status": "PASS",
        "prereg_sha256": PREREG_SHA256,
        "probe_script_sha256": sha256_file(MODULE_PATH),
        "inputs": {
            workspace_rel(PREREG_PATH): PREREG_SHA256,
            workspace_rel(FEATURE_PATH): FEATURE_SHA256,
            workspace_rel(FEATURE_RECEIPT_PATH): FEATURE_RECEIPT_SHA256,
            workspace_rel(EXTRACTOR_PATH): EXTRACTOR_SHA256,
            workspace_rel(CONTROL_PATH): CONTROL_SHA256,
            workspace_rel(SOURCE_PLAN_PATH): SOURCE_PLAN_SHA256,
            workspace_rel(DOWNLOAD_MANIFEST_PATH): DOWNLOAD_MANIFEST_SHA256,
            workspace_rel(VALIDATION_RECEIPT_PATH): VALIDATION_RECEIPT_SHA256,
            workspace_rel(CLOCK_PATH): CLOCK_SHA256,
            workspace_rel(DSR_PATH): DSR_SHA256,
            workspace_rel(TRIAL_HELPER_PATH): TRIAL_HELPER_SHA256,
        },
        "outputs": {
            workspace_rel(joined_path): joined_sha,
            workspace_rel(result_path): sha256_file(result_path),
            workspace_rel(TRIAL_LOG_PATH): sha256_file(TRIAL_LOG_PATH),
        },
        "source_rows": EXPECTED_TOTAL,
        "design_outcome_rows_materialized": EXPECTED_TOTAL,
        "holdout_rows_materialized": 0,
        "population_counts": actual_counts,
        "trials_executed": 3,
        "prior_hypothesis_oos_opened": False,
        "source_feature_threshold_changed": False,
        "entry_and_break_bar_clock_reconciled": True,
    }
    write_json(receipt_path, receipt)

    candidate = arms["CHALLENGER_TOP50_TRANSITION_SCORE"]
    print(
        "CME6E_BREAKBAR_TRANSITION_DESIGN_PROBE "
        f"verdict={gate_result['verdict']} "
        f"gates={gate_result['passed']}/{gate_result['total']} "
        f"challenger_n={candidate['count']} "
        f"pf={candidate['native']['profit_factor']:.9f} "
        f"mean_r={candidate['native']['mean_realized_r']:.9f} "
        f"dsr={dsr_result['value']:.9f} holdout_opened=false"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeError as exc:
        print(f"CME6E_BREAKBAR_TRANSITION_DESIGN_PROBE status=FAIL_CLOSED error={exc}")
        raise SystemExit(2)
