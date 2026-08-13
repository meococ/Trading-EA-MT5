from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


HYPOTHESIS_ID = "HYP-KST-XAUUSD-M15-001"
ATTEMPT_ID = "KST001-SOURCE-001"
TLB_SHA256 = "92174C77F64609F20A392C274E208097E0F4E3AF8DD45FFA5B71D8865CF6F8FA"
WARMUP_ROWS = 53
ELAPSED_WEEKS = 1826.0 / 7.0

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
TLB_PATH = REPO_ROOT / "03. EA Developer/EA_ThreeLineBreakReversal/research/analyze_tlb_source.py"
PREREG_PATH = RESEARCH_DIR / "HYP-KST-XAUUSD-M15-001_FROZEN_SOURCE_PREREG.md"
REVIEW_PATH = RESEARCH_DIR / "HYP-KST-XAUUSD-M15-001_PRE_SOURCE_REVIEW.md"
TEST_PATH = RESEARCH_DIR / "tests/test_analyze_kst_source.py"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"

SPEC = importlib.util.spec_from_file_location("tlb_frozen_dependency", TLB_PATH)
TLB = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(TLB)


def sha256_file(path: Path) -> str:
    return TLB.sha256_file(path)


def json_bytes(value: object) -> bytes:
    return TLB.json_bytes(value)


def ledger_bytes(rows: list[dict]) -> bytes:
    return TLB.ledger_bytes(rows)


def write_exclusive(path: Path, payload: bytes) -> None:
    TLB.write_exclusive(path, payload)


def claim_attempt() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    write_exclusive(START_PATH, json_bytes({
        "schema_version": "kst_source_attempt_started.v1",
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
        "m15_aggregation_dependency": sha256_file(TLB_PATH),
        "manifest": sha256_file(TLB.BASE.MANIFEST_PATH),
        "source": sha256_file(TLB.BASE.SOURCE_PATH),
    }


def validate_hashes(hashes: dict[str, str]) -> None:
    if hashes["m15_aggregation_dependency"] != TLB_SHA256:
        raise ValueError("M15 aggregation dependency hash mismatch")
    TLB.validate_hashes({
        "shared_validator": sha256_file(TLB.BASE_PATH),
        "manifest": hashes["manifest"],
        "source": hashes["source"],
    })


def calculate_kst(frame: pd.DataFrame) -> pd.DataFrame:
    close = frame["close"].astype(float)
    roc10 = 100.0 * (close / close.shift(10) - 1.0)
    roc15 = 100.0 * (close / close.shift(15) - 1.0)
    roc20 = 100.0 * (close / close.shift(20) - 1.0)
    roc30 = 100.0 * (close / close.shift(30) - 1.0)
    rcma1 = roc10.rolling(10, min_periods=10).mean()
    rcma2 = roc15.rolling(10, min_periods=10).mean()
    rcma3 = roc20.rolling(10, min_periods=10).mean()
    rcma4 = roc30.rolling(15, min_periods=15).mean()
    kst = rcma1 + 2.0 * rcma2 + 3.0 * rcma3 + 4.0 * rcma4
    signal = kst.rolling(9, min_periods=9).mean()
    return pd.DataFrame({"kst": kst, "signal": signal})


def extract_events(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    values = calculate_kst(frame)
    raw: list[dict] = []
    conflicts = 0
    usable = 0
    for i in range(1, len(frame)):
        prior_kst = values.at[i - 1, "kst"]
        prior_signal = values.at[i - 1, "signal"]
        current_kst = values.at[i, "kst"]
        current_signal = values.at[i, "signal"]
        if pd.isna(prior_kst) or pd.isna(prior_signal) or pd.isna(current_kst) or pd.isna(current_signal):
            continue
        usable += 1
        long_event = prior_kst <= prior_signal and current_kst > current_signal and current_kst < 0.0
        short_event = prior_kst >= prior_signal and current_kst < current_signal and current_kst > 0.0
        if long_event and short_event:
            conflicts += 1
            continue
        if not long_event and not short_event:
            continue
        decision_epoch = int(frame.at[i, "source_epoch"])
        exact_next = bool(
            i + 1 < len(frame)
            and int(frame.at[i + 1, "source_epoch"]) == decision_epoch + 900
            and frame.at[i + 1, "time_utc"] == frame.at[i, "time_utc"] + pd.Timedelta(minutes=15)
        )
        availability = frame.at[i + 1, "time_utc"] if exact_next else None
        raw.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "decision_source_epoch": decision_epoch,
            "decision_time_utc": frame.at[i, "time_utc"].isoformat(),
            "availability_source_epoch": int(frame.at[i + 1, "source_epoch"]) if exact_next else None,
            "availability_time_utc": availability.isoformat() if exact_next else None,
            "decision_year": int(availability.year) if exact_next else None,
            "direction": "LONG" if long_event else "SHORT",
            "prior_kst": float(prior_kst),
            "prior_signal": float(prior_signal),
            "kst": float(current_kst),
            "signal": float(current_signal),
            "exact_next": exact_next,
        })
    return raw, {"feature_usable_rows": usable, "direction_conflicts": conflicts}


def analyze_m15(frame: pd.DataFrame, aggregation: dict, validation: dict) -> tuple[dict, list[dict]]:
    raw, diagnostics = extract_events(frame)
    executable = [row for row in raw if row["exact_next"]]
    n = len(executable)
    exact_next = sum(row["exact_next"] for row in raw) / len(raw) if raw else 0.0
    denominator = max(len(frame) - WARMUP_ROWS, 1)
    feature_coverage = diagnostics["feature_usable_rows"] / denominator
    sides = {side: sum(row["direction"] == side for row in executable) for side in ("LONG", "SHORT")}
    shares = {side: sides[side] / n if n else 0.0 for side in sides}
    years = {year: sum(row["decision_year"] == year for row in executable) for year in range(2018, 2023)}
    year_weeks = {year: (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days / 7.0 for year in years}
    yearly = {str(year): years[year] / year_weeks[year] for year in years}
    cadence = n / ELAPSED_WEEKS
    max_year_share = max(years.values()) / n if n else 1.0
    gates = {
        "m15_rows_gte_115000": len(frame) >= 115_000,
        "aggregation_coverage_gte_0_98": aggregation["aggregation_coverage"] >= 0.98,
        "feature_coverage_gte_0_99": feature_coverage >= 0.99,
        "exact_next_gte_0_97": exact_next >= 0.97,
        "events_gte_500": n >= 500,
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "long_share_gte_0_30": shares["LONG"] >= 0.30,
        "short_share_gte_0_30": shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
        "every_year_1_25_to_6_5": all(1.25 <= value <= 6.5 for value in yearly.values()),
        "zero_conflicts": diagnostics["direction_conflicts"] == 0,
    }
    return {
        "schema_version": "kst_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "parameters": {"roc_lengths": [10, 15, 20, 30], "sma_lengths": [10, 10, 10, 15],
                       "signal_length": 9, "event": "negative_bull_cross_positive_bear_cross"},
        "validation": validation,
        **aggregation,
        **diagnostics,
        "feature_coverage": feature_coverage,
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
        context["stage"] = "bind_inputs"
        initial = frozen_hashes()
        context["input_hashes"] = initial
        validate_hashes(initial)
        context["stage"] = "read_design"
        source = TLB.BASE.read_design()
        valid, validation = TLB.BASE.validate_frame(source)
        context["stage"] = "aggregate_m15"
        m15, aggregation = TLB.aggregate_m15(valid)
        context["stage"] = "analyze"
        report_a, ledger_a = analyze_m15(m15, aggregation, validation)
        report_b, ledger_b = analyze_m15(m15, aggregation, validation)
        replay = json_bytes(report_a) == json_bytes(report_b) and ledger_bytes(ledger_a) == ledger_bytes(ledger_b)
        report_a["gates"]["deterministic_replay"] = replay
        report_a["deterministic_replay"] = replay
        report_a["all_gates_pass"] = bool(all(report_a["gates"].values()))
        context["gate_results"] = report_a["gates"]
        context["observed"] = {"m15_rows": len(m15), "raw_events": report_a["raw_events"],
                               "executable_events": report_a["executable_events"]}
        if not replay:
            raise ValueError("deterministic replay mismatch")
        context["stage"] = "rehash_inputs"
        final = frozen_hashes()
        if final != initial:
            raise ValueError("frozen input drift")
        report_payload = json_bytes(report_a)
        ledger_payload = ledger_bytes(ledger_a)
        write_exclusive(REPORT_PATH, report_payload)
        write_exclusive(LEDGER_PATH, ledger_payload)
        receipt = {
            "schema_version": "kst_source_attempt_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "attempt_started_sha256": sha256_file(START_PATH),
            "input_hashes": final,
            "source_report_sha256": hashlib.sha256(report_payload).hexdigest().upper(),
            "source_ledger_sha256": hashlib.sha256(ledger_payload).hexdigest().upper(),
            "outcomes_opened": False, "economics_evaluated": False,
            "same_id_retry_authorized": False,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_exclusive(RECEIPT_PATH, json_bytes(receipt))
        write_exclusive(TERMINAL_PATH, json_bytes({
            "schema_version": "kst_source_attempt_terminal.v1",
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
                "schema_version": "kst_source_attempt_terminal.v1",
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
