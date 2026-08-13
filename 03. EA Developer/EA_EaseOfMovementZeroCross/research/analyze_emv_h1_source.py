from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EMV-XAUUSD-H1-001"
ATTEMPT_ID = "EMV001-SOURCE-001"
PERIOD = 14
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
SOURCE_START = pd.Timestamp("2004-06-11T04:00:00Z")
ELAPSED_WEEKS = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "B85006E201DA7B359E9F25290C81C72A6092CFA08AEDFFE05E693E17A005ACC3"

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
PREREG_PATH = RESEARCH_DIR / "HYP-EMV-XAUUSD-H1-001_FROZEN_SOURCE_PREREG.md"
REVIEW_PATH = RESEARCH_DIR / "HYP-EMV-XAUUSD-H1-001_PRE_SOURCE_REVIEW.md"
TEST_PATH = RESEARCH_DIR / "tests/test_analyze_emv_h1_source.py"
MANIFEST_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
DATA_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"
REQUIRED_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous", "high", "low", "close", "tick_volume")
EVENT_KEYS = {"hypothesis_id", "source_bar_time_utc", "decision_time_utc", "direction", "prior_eom14", "eom14"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def ledger_bytes(rows: list[dict]) -> bytes:
    return b"".join(json_bytes(row) for row in rows)


def write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def claim_attempt() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    write_exclusive(START_PATH, json_bytes({
        "schema_version": "emv_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CLAIMED_BEFORE_SOURCE_READ",
        "same_id_retry_authorized": False,
    }))


def frozen_hashes() -> dict[str, str]:
    return {
        "analyzer": sha256_file(SCRIPT_PATH),
        "test": sha256_file(TEST_PATH),
        "prereg": sha256_file(PREREG_PATH),
        "pre_source_review": sha256_file(REVIEW_PATH),
        "manifest": sha256_file(MANIFEST_PATH),
        "source": sha256_file(DATA_PATH),
    }


def validate_frozen_hashes(hashes: dict[str, str]) -> None:
    if hashes["manifest"] != MANIFEST_SHA256 or hashes["source"] != DATA_SHA256:
        raise ValueError("frozen manifest/data identity mismatch")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("XAUUSD/XAUUSD_H1_ALL_AVAILABLE_20260801.parquet")]
    if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
        raise ValueError("manifest does not bind unique frozen H1 source")


def validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    data["source_epoch"] = pd.to_numeric(data["source_epoch"], errors="raise")
    for name in ("high", "low", "close", "tick_volume"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    if data.empty or data.at[0, "time_utc"] != SOURCE_START:
        raise ValueError("source frame does not begin at frozen H1 inception")
    if (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("sealed reader materialized rows outside source window")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and increasing")
    if not data["symbol"].eq("XAUUSD").all() or not data["timeframe"].eq("H1").all():
        raise ValueError("rows must be exclusively XAUUSD/H1")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    high = data["high"].to_numpy(dtype=float)
    low = data["low"].to_numpy(dtype=float)
    close = data["close"].to_numpy(dtype=float)
    volume = data["tick_volume"].to_numpy(dtype=float)
    if not (np.isfinite(high).all() and np.isfinite(low).all() and np.isfinite(close).all() and np.isfinite(volume).all()):
        raise ValueError("source geometry/volume must be finite")
    if not (np.all(high >= low) and np.all(close >= low) and np.all(close <= high) and np.all(volume > 0.0)):
        raise ValueError("source geometry/volume is invalid")
    return data


def calculate_eom14(high: np.ndarray, low: np.ndarray, volume: np.ndarray) -> np.ndarray:
    high_values = np.asarray(high, dtype=float)
    low_values = np.asarray(low, dtype=float)
    volume_values = np.asarray(volume, dtype=float)
    midpoint = (high_values + low_values) / 2.0
    raw = np.full(len(midpoint), np.nan, dtype=float)
    valid = (
        np.isfinite(midpoint[1:])
        & np.isfinite(midpoint[:-1])
        & np.isfinite(high_values[1:])
        & np.isfinite(low_values[1:])
        & np.isfinite(volume_values[1:])
        & (high_values[1:] >= low_values[1:])
        & (volume_values[1:] > 0.0)
    )
    raw[1:][valid] = (midpoint[1:][valid] - midpoint[:-1][valid]) * (high_values[1:][valid] - low_values[1:][valid]) / volume_values[1:][valid]
    return pd.Series(raw).rolling(PERIOD, min_periods=PERIOD).mean().to_numpy(dtype=float)


def year_weeks(year: int) -> float:
    start = max(DESIGN_START, pd.Timestamp(f"{year}-01-01T00:00:00Z"))
    end = min(DESIGN_END, pd.Timestamp(f"{year + 1}-01-01T00:00:00Z"))
    return (end - start).total_seconds() / 604800.0


def analyze(frame: pd.DataFrame) -> tuple[dict, list[dict]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    eom = pd.Series(calculate_eom14(data["high"], data["low"], data["tick_volume"]), index=data.index)
    prior = eom.shift(1)
    design = data["time_utc"].ge(DESIGN_START) & data["time_utc"].lt(DESIGN_END)
    usable = design & np.isfinite(eom) & np.isfinite(prior)
    raw_long = usable & prior.le(0.0) & eom.gt(0.0)
    raw_short = usable & prior.ge(0.0) & eom.lt(0.0)
    conflicts = raw_long & raw_short
    raw = (raw_long | raw_short) & ~conflicts
    exact_next = data["source_epoch"].shift(-1).eq(data["source_epoch"] + 3600) & ((data["time_utc"].shift(-1) - data["time_utc"]) == pd.Timedelta(hours=1))
    executable = raw & exact_next
    events: list[dict] = []
    for index in data.index[executable]:
        source_time = data.at[index, "time_utc"]
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": source_time.isoformat().replace("+00:00", "Z"),
            "decision_time_utc": (source_time + pd.Timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            "direction": "LONG" if bool(raw_long.loc[index]) else "SHORT",
            "prior_eom14": float(prior.loc[index]),
            "eom14": float(eom.loc[index]),
        })
    count = len(events)
    raw_count = int(raw.sum())
    design_rows = int(design.sum())
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    event_years = pd.Series([pd.Timestamp(row["decision_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, dict[str, float | int]] = {}
    for year in range(2018, 2023):
        year_count = int((event_years == year).sum()) if count else 0
        weeks = year_weeks(year)
        yearly[str(year)] = {"events": year_count, "elapsed_weeks": weeks, "cadence_per_week": year_count / weeks, "share": year_count / count if count else 0.0}
    feature_coverage = int(usable.sum()) / max(design_rows, 1)
    next_coverage = count / max(raw_count, 1)
    cadence = count / ELAPSED_WEEKS
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    max_year_share = max((item["share"] for item in yearly.values()), default=0.0)
    gates = {
        "minimum_design_rows": design_rows >= 25_000,
        "feature_coverage": feature_coverage >= 0.99,
        "exact_next_coverage": next_coverage >= 0.97,
        "minimum_events": count >= 500,
        "pooled_cadence": 2.0 <= cadence <= 5.0,
        "direction_balance": long_share >= 0.30 and short_share >= 0.30,
        "year_concentration": max_year_share <= 0.30,
        "each_year_cadence": all(1.25 <= item["cadence_per_week"] <= 6.50 for item in yearly.values()),
        "zero_conflicts": int(conflicts.sum()) == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "emv14_h1_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "scope": "OUTCOME_BLIND_EOM14_ZERO_CROSS_SOURCE_FEASIBILITY_ONLY",
        "parameters": {"timeframe": "H1", "period": PERIOD, "first_eom14_index": 14, "first_event_index": 15},
        "funnel": {"source_rows": len(data), "design_rows": design_rows, "feature_usable_rows": int(usable.sum()), "raw_events": raw_count, "executable_events": count, "gap_rejected_events": raw_count - count, "long_events": longs, "short_events": shorts, "direction_conflicts": int(conflicts.sum())},
        "metrics": {"elapsed_weeks": ELAPSED_WEEKS, "feature_coverage": feature_coverage, "exact_next_coverage": next_coverage, "cadence_per_week": cadence, "long_share": long_share, "short_share": short_share, "max_year_share": max_year_share},
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": passed,
        "verdict": "PASS_SOURCE_FEASIBILITY_DIRECT_MQL5_BUILD_AUTHORIZED" if passed else "PARK_SOURCE_FEASIBILITY_EXACT_EMV14_ZERO_CROSS",
        "outcome_blind_counters": {"post_event_ohlc_rows_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0},
    }
    return report, events


def assert_outcome_blind(report: dict, events: list[dict]) -> None:
    if any(value != 0 for value in report["outcome_blind_counters"].values()):
        raise ValueError("outcome-blind counters violated")
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError("event allowlist violated")
        if not all(math.isfinite(float(row[key])) for key in ("prior_eom14", "eom14")):
            raise ValueError("event contains nonfinite feature")


def execute() -> dict:
    context: dict[str, object] = {"stage": "claim"}
    claim_attempt()
    try:
        initial = frozen_hashes()
        validate_frozen_hashes(initial)
        context = {"stage": "source_read", "initial_hashes": initial}
        frame = pd.read_parquet(DATA_PATH, columns=list(REQUIRED_COLUMNS), filters=[("time_utc", "<", DESIGN_END.to_pydatetime())], engine="pyarrow")
        validated = validate_frame(frame)
        report, events = analyze(validated)
        replay_report, replay_events = analyze(validated)
        if json_bytes(report) != json_bytes(replay_report) or ledger_bytes(events) != ledger_bytes(replay_events):
            raise ValueError("deterministic replay failed")
        assert_outcome_blind(report, events)
        final = frozen_hashes()
        if final != initial:
            raise ValueError("frozen input drift detected")
        write_exclusive(REPORT_PATH, json_bytes(report))
        write_exclusive(LEDGER_PATH, ledger_bytes(events))
        receipt = {
            "schema_version": "emv_source_attempt_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "bindings": initial,
            "attempt_started_sha256": sha256_file(START_PATH),
            "report_sha256": sha256_file(REPORT_PATH),
            "ledger_sha256": sha256_file(LEDGER_PATH),
            "deterministic_replay": True,
            "outcome_blind_counters": report["outcome_blind_counters"],
            "verdict": report["verdict"],
        }
        write_exclusive(RECEIPT_PATH, json_bytes(receipt))
        write_exclusive(TERMINAL_PATH, json_bytes({
            "schema_version": "emv_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": report["verdict"],
            "receipt_sha256": sha256_file(RECEIPT_PATH),
            "same_id_retry_authorized": False,
        }))
        return report
    except Exception as exc:
        context["error"] = str(exc)
        if not TERMINAL_PATH.exists():
            write_exclusive(TERMINAL_PATH, json_bytes({
                "schema_version": "emv_source_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "status": "FAILED",
                "context": context,
                "same_id_retry_authorized": False,
            }))
        raise


if __name__ == "__main__":
    print(json.dumps(execute(), indent=2, sort_keys=True))
