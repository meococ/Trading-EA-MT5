from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


HYPOTHESIS_ID = "HYP-TLB-XAUUSD-M15-001"
ATTEMPT_ID = "TLB001-SOURCE-001"
BASE_SHA256 = "AE06830575C27776926B3129F97FDD85EC586F830CC86977D4C63A16E888E583"
SOURCE_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
LINE_COUNT = 3
ELAPSED_WEEKS = 1826.0 / 7.0

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
BASE_PATH = REPO_ROOT / "03. EA Developer/EA_IntradaySemivarianceAbsorption/research/analyze_isva_source.py"
PREREG_PATH = RESEARCH_DIR / "HYP-TLB-XAUUSD-M15-001_FROZEN_SOURCE_PREREG.md"
REVIEW_PATH = RESEARCH_DIR / "HYP-TLB-XAUUSD-M15-001_PRE_SOURCE_REVIEW.md"
TEST_PATH = RESEARCH_DIR / "tests/test_analyze_tlb_source.py"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"

SPEC = importlib.util.spec_from_file_location("isva_frozen_dependency", BASE_PATH)
BASE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(BASE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def ledger_bytes(rows: list[dict]) -> bytes:
    return b"".join(
        (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )


def write_exclusive(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def claim_attempt() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    write_exclusive(START_PATH, json_bytes({
        "schema_version": "tlb_source_attempt_started.v1",
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
        "shared_validator": sha256_file(BASE_PATH),
        "manifest": sha256_file(BASE.MANIFEST_PATH),
        "source": sha256_file(BASE.SOURCE_PATH),
    }


def validate_hashes(hashes: dict[str, str]) -> None:
    if hashes["shared_validator"] != BASE_SHA256:
        raise ValueError("shared validator hash mismatch")
    if hashes["manifest"] != MANIFEST_SHA256 or hashes["source"] != SOURCE_SHA256:
        raise ValueError("manifest/source hash mismatch")


def aggregate_m15(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    work = frame.copy()
    work["bucket"] = work["time_utc"].dt.floor("15min")
    rows: list[dict] = []
    rejected = 0
    for bucket, group in work.groupby("bucket", sort=True):
        ordered = group.sort_values("time_utc")
        if len(ordered) != 3:
            rejected += 1
            continue
        epochs = ordered["source_epoch"].astype("int64").tolist()
        times = ordered["time_utc"].tolist()
        expected_times = [bucket + pd.Timedelta(minutes=value) for value in (0, 5, 10)]
        if times != expected_times or epochs[1] != epochs[0] + 300 or epochs[2] != epochs[1] + 300:
            rejected += 1
            continue
        values = [float(ordered.iloc[0]["open"]), float(ordered["high"].max()),
                  float(ordered["low"].min()), float(ordered.iloc[-1]["close"])]
        if not all(math.isfinite(value) for value in values) or values[1] < values[2]:
            rejected += 1
            continue
        rows.append({
            "time_utc": bucket,
            "source_epoch": epochs[0],
            "open": values[0],
            "high": values[1],
            "low": values[2],
            "close": values[3],
        })
    result = pd.DataFrame(rows)
    coverage = (len(result) * 3 / len(frame)) if len(frame) else 0.0
    return result, {
        "m5_rows": int(len(frame)),
        "m15_rows": int(len(result)),
        "rejected_m15_buckets": rejected,
        "aggregation_coverage": coverage,
    }


def extract_events(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    lines: list[dict] = []
    seed_close: float | None = None
    raw: list[dict] = []
    conflicts = 0
    created_lines = 0
    for i, row in frame.iterrows():
        close = float(row["close"])
        if seed_close is None:
            seed_close = close
            continue
        if not lines:
            if close == seed_close:
                continue
            direction = "LONG" if close > seed_close else "SHORT"
            lines.append({"open": seed_close, "close": close, "high": max(seed_close, close),
                          "low": min(seed_close, close), "direction": direction})
            created_lines += 1
            continue
        recent = lines[-min(LINE_COUNT, len(lines)):]
        upper = max(line["high"] for line in recent)
        lower = min(line["low"] for line in recent)
        direction: str | None = None
        if close > upper:
            direction = "LONG"
        elif close < lower:
            direction = "SHORT"
        if direction is None:
            continue
        previous = lines[-1]
        reversal = len(lines) >= LINE_COUNT and direction != previous["direction"]
        new_line = {
            "open": previous["close"],
            "close": close,
            "high": max(float(previous["close"]), close),
            "low": min(float(previous["close"]), close),
            "direction": direction,
        }
        if reversal:
            decision_epoch = int(row["source_epoch"])
            exact_next = bool(
                i + 1 < len(frame)
                and int(frame.at[i + 1, "source_epoch"]) == decision_epoch + 900
                and frame.at[i + 1, "time_utc"] == row["time_utc"] + pd.Timedelta(minutes=15)
            )
            availability = frame.at[i + 1, "time_utc"] if exact_next else None
            raw.append({
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "decision_source_epoch": decision_epoch,
                "decision_time_utc": row["time_utc"].isoformat(),
                "availability_source_epoch": int(frame.at[i + 1, "source_epoch"]) if exact_next else None,
                "availability_time_utc": availability.isoformat() if exact_next else None,
                "decision_year": int(availability.year) if exact_next else None,
                "direction": direction,
                "prior_direction": previous["direction"],
                "close": close,
                "three_line_upper": upper,
                "three_line_lower": lower,
                "prior_line_count": len(lines),
                "exact_next": exact_next,
            })
        lines.append(new_line)
        created_lines += 1
    return raw, {"confirmed_lines": created_lines, "direction_conflicts": conflicts}


def analyze(frame: pd.DataFrame, validation: dict) -> tuple[dict, list[dict]]:
    m15, aggregation = aggregate_m15(frame)
    raw, diagnostics = extract_events(m15)
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
        "m15_rows_gte_115000": len(m15) >= 115_000,
        "aggregation_coverage_gte_0_98": aggregation["aggregation_coverage"] >= 0.98,
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
        "schema_version": "tlb_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "parameters": {"line_count": LINE_COUNT, "input": "completed_native_m15_close"},
        "validation": validation,
        **aggregation,
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
        context["stage"] = "bind_inputs"
        initial = frozen_hashes()
        context["input_hashes"] = initial
        validate_hashes(initial)
        context["stage"] = "read_design"
        frame = BASE.read_design()
        context["observed"] = {"design_rows": int(len(frame))}
        context["stage"] = "validate_design"
        valid, validation = BASE.validate_frame(frame)
        context["stage"] = "analyze"
        report_a, ledger_a = analyze(valid, validation)
        report_b, ledger_b = analyze(valid, validation)
        replay = json_bytes(report_a) == json_bytes(report_b) and ledger_bytes(ledger_a) == ledger_bytes(ledger_b)
        report_a["gates"]["deterministic_replay"] = replay
        report_a["deterministic_replay"] = replay
        report_a["all_gates_pass"] = bool(all(report_a["gates"].values()))
        context["gate_results"] = report_a["gates"]
        context["observed"] = {"design_rows": int(len(valid)), "m15_rows": report_a["m15_rows"],
                               "raw_events": report_a["raw_events"], "executable_events": report_a["executable_events"]}
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
            "schema_version": "tlb_source_attempt_receipt.v1",
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
            "schema_version": "tlb_source_attempt_terminal.v1",
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
                "schema_version": "tlb_source_attempt_terminal.v1",
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
