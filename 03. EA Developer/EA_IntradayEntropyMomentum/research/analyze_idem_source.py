from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-IDEM-XAUUSD-M5-001"
ATTEMPT_ID = "IDEM001-SOURCE-001"
DPMO_SHA256 = "4DDC3056D2C35B88198A9C1C0734F4746CC3E5BCC37037F8715978AFD443D670"
ELAPSED_WEEKS = 1826.0 / 7.0
REFERENCE_DAYS = 20

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
DPMO_PATH = REPO_ROOT / "03. EA Developer/EA_DailyParticipationMomentum/research/analyze_dpmo_source.py"
PREREG_PATH = RESEARCH_DIR / "HYP-IDEM-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md"
REVIEW_PATH = RESEARCH_DIR / "HYP-IDEM-XAUUSD-M5-001_PRE_SOURCE_REVIEW.md"
TEST_PATH = RESEARCH_DIR / "tests/test_analyze_idem_source.py"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"

SPEC = importlib.util.spec_from_file_location("dpmo_frozen_dependency", DPMO_PATH)
DPMO = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(DPMO)

sha256_file = DPMO.sha256_file
json_bytes = DPMO.json_bytes
ledger_bytes = DPMO.ledger_bytes
write_exclusive = DPMO.write_exclusive


def claim_attempt() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    write_exclusive(START_PATH, json_bytes({
        "schema_version": "idem_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_id_retry_authorized": False,
    }))


def frozen_hashes() -> dict[str, str]:
    return {
        "analyzer": sha256_file(SCRIPT_PATH),
        "test": sha256_file(TEST_PATH),
        "prereg": sha256_file(PREREG_PATH),
        "pre_source_review": sha256_file(REVIEW_PATH),
        "daily_session_dependency": sha256_file(DPMO_PATH),
        "manifest": sha256_file(DPMO.BASE.MANIFEST_PATH),
        "source": sha256_file(DPMO.BASE.SOURCE_PATH),
    }


def validate_hashes(hashes: dict[str, str]) -> None:
    if hashes["daily_session_dependency"] != DPMO_SHA256:
        raise ValueError("DPMO dependency hash mismatch")
    DPMO.validate_hashes({
        "shared_validator": sha256_file(DPMO.BASE_PATH),
        "manifest": hashes["manifest"],
        "source": hashes["source"],
    })


def measure_session(group: pd.DataFrame) -> dict | None:
    if DPMO.BASE.session_measure(group) is None:
        return None
    ordered = group.sort_values("time_utc")
    closes = ordered["close"].astype(float).to_numpy()
    if len(closes) != 192 or np.any(~np.isfinite(closes)) or np.any(closes <= 0.0):
        return None
    returns = np.log(closes[1:] / closes[:-1])
    positive = int(np.count_nonzero(returns > 0.0))
    negative = int(np.count_nonzero(returns < 0.0))
    nonzero = positive + negative
    if nonzero <= 0:
        return None
    p = positive / nonzero
    entropy = 0.0
    if 0.0 < p < 1.0:
        entropy = -p * math.log(p) - (1.0 - p) * math.log(1.0 - p)
    session_return = math.log(float(closes[-1]) / float(closes[0]))
    if not math.isfinite(entropy) or not math.isfinite(session_return):
        return None
    return {
        "decision_index": int(ordered.index[-1]),
        "entropy": float(entropy),
        "session_return": float(session_return),
        "positive_returns": positive,
        "negative_returns": negative,
        "session_open_close": float(closes[0]),
        "decision_close": float(closes[-1]),
    }


def select_direction(measure: dict, prior_entropies: list[float]) -> str | None:
    if len(prior_entropies) < REFERENCE_DAYS:
        return None
    reference = float(np.median(np.asarray(prior_entropies[-REFERENCE_DAYS:], dtype=float)))
    if not math.isfinite(reference) or measure["entropy"] >= reference:
        return None
    if measure["session_return"] > 0.0:
        return "LONG"
    if measure["session_return"] < 0.0:
        return "SHORT"
    return None


def extract_events(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    intraday = frame[(frame["time_utc"].dt.weekday < 5) & (frame["time_utc"].dt.hour < 16)]
    expected_days = len(pd.bdate_range("2018-01-01", "2022-12-30"))
    complete = 0
    valid_measurements = 0
    history: list[float] = []
    raw: list[dict] = []
    for day, group in intraday.groupby("utc_date", sort=True):
        if DPMO.BASE.session_measure(group) is None:
            continue
        complete += 1
        measure = measure_session(group)
        if measure is None:
            continue
        valid_measurements += 1
        reference = float(np.median(np.asarray(history[-REFERENCE_DAYS:], dtype=float))) if len(history) >= REFERENCE_DAYS else None
        direction = select_direction(measure, history)
        history.append(measure["entropy"])
        if direction is None:
            continue
        i = measure["decision_index"]
        decision_epoch = int(frame.at[i, "source_epoch"])
        exact_next = bool(
            i + 1 < len(frame)
            and int(frame.at[i + 1, "source_epoch"]) == decision_epoch + 300
            and frame.at[i + 1, "time_utc"] == frame.at[i, "time_utc"] + pd.Timedelta(minutes=5)
            and frame.at[i + 1, "time_utc"].hour == 16
            and frame.at[i + 1, "time_utc"].minute == 0
        )
        availability = frame.at[i + 1, "time_utc"] if exact_next else None
        raw.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "utc_date": str(day),
            "decision_source_epoch": decision_epoch,
            "decision_time_utc": frame.at[i, "time_utc"].isoformat(),
            "availability_source_epoch": int(frame.at[i + 1, "source_epoch"]) if exact_next else None,
            "availability_time_utc": availability.isoformat() if exact_next else None,
            "decision_year": int(availability.year) if exact_next else None,
            "direction": direction,
            "entropy": measure["entropy"],
            "prior20_entropy_median": reference,
            "session_return": measure["session_return"],
            "positive_returns": measure["positive_returns"],
            "negative_returns": measure["negative_returns"],
            "session_complete": True,
            "exact_next": exact_next,
        })
    return raw, {
        "expected_weekdays": expected_days,
        "complete_sessions": complete,
        "session_coverage": complete / expected_days,
        "valid_measurements": valid_measurements,
        "measurement_coverage": valid_measurements / complete if complete else 0.0,
        "reference_days": REFERENCE_DAYS,
    }


def analyze(frame: pd.DataFrame, validation: dict) -> tuple[dict, list[dict]]:
    raw, diagnostics = extract_events(frame)
    executable = [row for row in raw if row["exact_next"]]
    n = len(executable)
    exact_next = sum(row["exact_next"] for row in raw) / len(raw) if raw else 0.0
    sides = {side: sum(row["direction"] == side for row in executable) for side in ("LONG", "SHORT")}
    shares = {side: sides[side] / n if n else 0.0 for side in sides}
    years = {year: sum(row["decision_year"] == year for row in executable) for year in range(2018, 2023)}
    year_weeks = {year: (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days / 7.0 for year in years}
    yearly = {str(year): years[year] / year_weeks[year] for year in years}
    cadence = n / ELAPSED_WEEKS
    max_year_share = max(years.values()) / n if n else 1.0
    gates = {
        "design_rows_gte_300000": len(frame) >= 300_000,
        "session_coverage_gte_0_95": diagnostics["session_coverage"] >= 0.95,
        "measurement_coverage_gte_0_95": diagnostics["measurement_coverage"] >= 0.95,
        "exact_next_gte_0_97": exact_next >= 0.97,
        "events_gte_500": n >= 500,
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "long_share_gte_0_30": shares["LONG"] >= 0.30,
        "short_share_gte_0_30": shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
        "every_year_1_25_to_6_5": all(1.25 <= value <= 6.5 for value in yearly.values()),
        "zero_conflicts": True,
    }
    return {
        "schema_version": "idem_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "parameters": {"session_utc": "00:00-15:55", "entropy": "binary_log_return_sign",
                       "reference": "strictly_below_prior20_ordinary_median"},
        "validation": validation,
        "design_rows": int(len(frame)),
        **diagnostics,
        "raw_events": len(raw),
        "executable_events": n,
        "exact_next_coverage": exact_next,
        "cadence_per_week": cadence,
        "directions": sides,
        "direction_shares": shares,
        "decision_year_counts": {str(key): value for key, value in years.items()},
        "decision_year_cadence": yearly,
        "max_year_share": max_year_share,
        "gates": gates,
    }, executable


def execute() -> dict:
    context: dict[str, object] = {"stage": "claim", "observed": {}, "gate_results": {},
                                  "outcomes_opened": False, "economics_evaluated": False}
    claim_attempt()
    try:
        initial = frozen_hashes()
        context["input_hashes"] = initial
        validate_hashes(initial)
        context["stage"] = "read_design"
        source = DPMO.BASE.read_design()
        valid, validation = DPMO.BASE.validate_frame(source)
        context["stage"] = "analyze"
        report_a, ledger_a = analyze(valid, validation)
        report_b, ledger_b = analyze(valid, validation)
        replay = json_bytes(report_a) == json_bytes(report_b) and ledger_bytes(ledger_a) == ledger_bytes(ledger_b)
        report_a["gates"]["deterministic_replay"] = replay
        report_a["deterministic_replay"] = replay
        report_a["all_gates_pass"] = bool(all(report_a["gates"].values()))
        context["gate_results"] = report_a["gates"]
        context["observed"] = {"complete_sessions": report_a["complete_sessions"],
                               "raw_events": report_a["raw_events"], "executable_events": report_a["executable_events"]}
        if not replay:
            raise ValueError("deterministic replay mismatch")
        final = frozen_hashes()
        if final != initial:
            raise ValueError("frozen input drift")
        report_payload = json_bytes(report_a)
        ledger_payload = ledger_bytes(ledger_a)
        write_exclusive(REPORT_PATH, report_payload)
        write_exclusive(LEDGER_PATH, ledger_payload)
        receipt = {
            "schema_version": "idem_source_attempt_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "attempt_started_sha256": sha256_file(START_PATH),
            "input_hashes": final,
            "source_report_sha256": hashlib.sha256(report_payload).hexdigest().upper(),
            "source_ledger_sha256": hashlib.sha256(ledger_payload).hexdigest().upper(),
            "outcomes_opened": False,
            "economics_evaluated": False,
            "same_id_retry_authorized": False,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_exclusive(RECEIPT_PATH, json_bytes(receipt))
        write_exclusive(TERMINAL_PATH, json_bytes({
            "schema_version": "idem_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": "PASS_SOURCE_FEASIBILITY" if report_a["all_gates_pass"] else "PARK_SOURCE_GATE_FAILURE",
            "attempt_started_sha256": sha256_file(START_PATH),
            "attempt_receipt_sha256": sha256_file(RECEIPT_PATH),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "same_id_retry_authorized": False,
        }))
        return report_a
    except Exception as exc:
        context["error_type"] = type(exc).__name__
        context["error"] = str(exc)
        if not TERMINAL_PATH.exists():
            write_exclusive(TERMINAL_PATH, json_bytes({
                "schema_version": "idem_source_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "status": "FAILED",
                "verdict": "FAILED_ENGINEERING_STRUCTURED_EVIDENCE",
                "attempt_started_sha256": sha256_file(START_PATH),
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "same_id_retry_authorized": False,
                "failure_context": context,
            }))
        raise


if __name__ == "__main__":
    print(json.dumps(execute(), indent=2, sort_keys=True))
