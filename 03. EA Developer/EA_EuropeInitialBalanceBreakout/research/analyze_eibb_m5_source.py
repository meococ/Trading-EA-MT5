from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EIBB-XAUUSD-M15-001"
ATTEMPT_ID = "EIBB001-SOURCE-001"
DESIGN_START = pd.Timestamp("2018-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2023-01-01T00:00:00Z")
ELAPSED_WEEKS = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
PREREG_PATH = RESEARCH_DIR / "HYP-EIBB-XAUUSD-M15-001_FROZEN_SOURCE_PREREG.md"
REVIEW_PATH = RESEARCH_DIR / "HYP-EIBB-XAUUSD-M15-001_PRE_SOURCE_REVIEW.md"
TEST_PATH = RESEARCH_DIR / "tests/test_analyze_eibb_m5_source.py"
MANIFEST_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
DATA_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"

REQUIRED_COLUMNS = (
    "symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous",
    "open", "high", "low", "close", "tick_volume",
)
EVENT_KEYS = {
    "hypothesis_id", "source_bar_time_utc", "decision_time_utc", "direction",
    "initial_balance_high", "initial_balance_low", "source_close",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


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
        "schema_version": "eibb_source_attempt_started.v1",
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


def validate_frozen_inputs(hashes: dict[str, str]) -> None:
    if hashes["manifest"] != MANIFEST_SHA256 or hashes["source"] != DATA_SHA256:
        raise ValueError("frozen manifest/data identity mismatch")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    matches = [
        item for item in manifest.get("files", [])
        if str(item.get("path", "")).replace("\\", "/").endswith(
            "XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
        )
    ]
    if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
        raise ValueError("manifest does not bind the unique frozen M5 source")


def validate_m5(frame: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    for name in ("source_epoch", "open", "high", "low", "close", "tick_volume"):
        data[name] = pd.to_numeric(data[name], errors="coerce")
    if data.empty or (data["time_utc"] < DESIGN_START).any() or (data["time_utc"] >= DESIGN_END).any():
        raise ValueError("reader materialized rows outside the sealed design window")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("time_utc must be unique and increasing")
    if not data["source_epoch"].is_monotonic_increasing or data["source_epoch"].duplicated().any():
        raise ValueError("source_epoch must be unique and increasing")
    if not data["symbol"].eq("XAUUSD").all() or not data["timeframe"].eq("M5").all():
        raise ValueError("rows must be exclusively XAUUSD/M5")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous rows are forbidden")
    values = data.loc[:, ("open", "high", "low", "close", "tick_volume")].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("source geometry/volume must be finite")
    if not (
        data["high"].ge(data["low"]).all()
        and data["open"].ge(data["low"]).all()
        and data["open"].le(data["high"]).all()
        and data["close"].ge(data["low"]).all()
        and data["close"].le(data["high"]).all()
        and data["tick_volume"].gt(0.0).all()
    ):
        raise ValueError("source geometry/volume is invalid")
    return data


def aggregate_m15(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    data["bucket"] = data["time_utc"].dt.floor("15min")
    data["slot"] = ((data["time_utc"] - data["bucket"]).dt.total_seconds() / 300).astype(int)
    grouped = data.groupby("bucket", sort=True)
    valid = (
        grouped.size().eq(3)
        & grouped["slot"].agg(list).map(lambda values: values == [0, 1, 2])
        & grouped["source_epoch"].agg(list).map(
            lambda values: len(values) == 3
            and values[1] - values[0] == 300
            and values[2] - values[1] == 300
        )
    )
    keys = valid[valid].index
    return pd.DataFrame({
        "time_utc": keys,
        "source_epoch": grouped["source_epoch"].first().loc[keys].astype("int64").to_numpy(),
        "open": grouped["open"].first().loc[keys].to_numpy(dtype=float),
        "high": grouped["high"].max().loc[keys].to_numpy(dtype=float),
        "low": grouped["low"].min().loc[keys].to_numpy(dtype=float),
        "close": grouped["close"].last().loc[keys].to_numpy(dtype=float),
        "tick_volume": grouped["tick_volume"].sum().loc[keys].to_numpy(dtype=float),
    }).reset_index(drop=True)


def year_weeks(year: int) -> float:
    start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    end = pd.Timestamp(f"{year + 1}-01-01T00:00:00Z")
    return (end - start).total_seconds() / 604800.0


def analyze(frame: pd.DataFrame) -> tuple[dict, list[dict]]:
    m15 = aggregate_m15(frame)
    lookup = {time: index for index, time in enumerate(m15["time_utc"])}
    raw: list[dict] = []
    valid_ib_dates = 0
    conflicts = 0
    for _, day in m15.groupby(m15["time_utc"].dt.floor("D"), sort=True):
        by_time = {stamp: index for stamp, index in zip(day["time_utc"].dt.strftime("%H:%M"), day.index)}
        ib_times = ("07:00", "07:15", "07:30", "07:45")
        if any(stamp not in by_time for stamp in ib_times):
            continue
        initial = day.loc[[by_time[stamp] for stamp in ib_times]]
        valid_ib_dates += 1
        ib_high = float(initial["high"].max())
        ib_low = float(initial["low"].min())
        scan = day[
            day["time_utc"].dt.hour.ge(8) & day["time_utc"].dt.hour.lt(16)
        ].sort_values("time_utc")
        for index, row in scan.iterrows():
            long_break = bool(row["close"] > ib_high)
            short_break = bool(row["close"] < ib_low)
            if long_break and short_break:
                conflicts += 1
                break
            if not long_break and not short_break:
                continue
            raw.append({
                "index": int(index),
                "source_bar_time_utc": row["time_utc"],
                "source_epoch": int(row["source_epoch"]),
                "direction": "LONG" if long_break else "SHORT",
                "initial_balance_high": ib_high,
                "initial_balance_low": ib_low,
                "source_close": float(row["close"]),
            })
            break

    events: list[dict] = []
    for row in raw:
        decision_time = row["source_bar_time_utc"] + pd.Timedelta(minutes=15)
        next_index = lookup.get(decision_time)
        if next_index is None or int(m15.at[next_index, "source_epoch"]) != row["source_epoch"] + 900:
            continue
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": row["source_bar_time_utc"].isoformat().replace("+00:00", "Z"),
            "decision_time_utc": decision_time.isoformat().replace("+00:00", "Z"),
            "direction": row["direction"],
            "initial_balance_high": row["initial_balance_high"],
            "initial_balance_low": row["initial_balance_low"],
            "source_close": row["source_close"],
        })

    count = len(events)
    raw_count = len(raw)
    longs = sum(row["direction"] == "LONG" for row in events)
    shorts = count - longs
    years = {year: sum(pd.Timestamp(row["decision_time_utc"]).year == year for row in events) for year in range(2018, 2023)}
    yearly = {
        str(year): {
            "events": years[year],
            "elapsed_weeks": year_weeks(year),
            "cadence_per_week": years[year] / year_weeks(year),
            "share": years[year] / count if count else 0.0,
        }
        for year in years
    }
    exact_next = count / raw_count if raw_count else 0.0
    cadence = count / ELAPSED_WEEKS
    long_share = longs / count if count else 0.0
    short_share = shorts / count if count else 0.0
    max_year_share = max((item["share"] for item in yearly.values()), default=0.0)
    gates = {
        "design_m15_rows": len(m15) >= 100_000,
        "valid_initial_balance_dates": valid_ib_dates >= 1_200,
        "exact_next_coverage": exact_next >= 0.97,
        "minimum_events": count >= 500,
        "pooled_cadence": 2.0 <= cadence <= 5.0,
        "direction_balance": long_share >= 0.30 and short_share >= 0.30,
        "year_concentration": max_year_share <= 0.30,
        "each_year_cadence": all(1.25 <= item["cadence_per_week"] <= 6.50 for item in yearly.values()),
        "zero_conflicts": conflicts == 0,
    }
    passed = all(gates.values())
    report = {
        "schema_version": "eibb_m5_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "scope": "OUTCOME_BLIND_M5_TO_M15_INITIAL_BALANCE_SOURCE_FEASIBILITY_ONLY",
        "funnel": {
            "source_m5_rows": len(frame), "valid_m15_rows": len(m15),
            "valid_initial_balance_dates": valid_ib_dates, "raw_events": raw_count,
            "executable_events": count, "gap_rejected_events": raw_count - count,
            "long_events": longs, "short_events": shorts, "direction_conflicts": conflicts,
        },
        "metrics": {
            "elapsed_weeks": ELAPSED_WEEKS, "exact_next_coverage": exact_next,
            "cadence_per_week": cadence, "long_share": long_share,
            "short_share": short_share, "max_year_share": max_year_share,
        },
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": passed,
        "verdict": (
            "PASS_SOURCE_FEASIBILITY_DIRECT_M5_TO_M15_MQL5_BUILD_AUTHORIZED"
            if passed else "PARK_SOURCE_FEASIBILITY_EXACT_UTC_INITIAL_BALANCE_BREAKOUT"
        ),
        "outcome_blind_counters": {
            "post_event_ohlc_rows_read": 0, "returns_computed": 0,
            "trades_simulated": 0, "pnl_computed": 0,
            "profit_factor_computed": 0, "validation_rows_read": 0,
            "holdout_rows_read": 0,
        },
    }
    return report, events


def assert_outcome_blind(report: dict, events: list[dict]) -> None:
    if any(value != 0 for value in report["outcome_blind_counters"].values()):
        raise ValueError("outcome-blind counters violated")
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError("event allowlist violated")
        for key in ("initial_balance_high", "initial_balance_low", "source_close"):
            if not math.isfinite(float(row[key])):
                raise ValueError("event contains nonfinite source feature")


def execute() -> dict:
    context: dict[str, object] = {"stage": "claim"}
    claim_attempt()
    try:
        initial = frozen_hashes()
        context["stage"] = "frozen_input_validation"
        validate_frozen_inputs(initial)
        context["stage"] = "sealed_source_read"
        frame = pd.read_parquet(
            DATA_PATH, columns=list(REQUIRED_COLUMNS),
            filters=[
                ("time_utc", ">=", DESIGN_START.to_pydatetime()),
                ("time_utc", "<", DESIGN_END.to_pydatetime()),
            ], engine="pyarrow",
        )
        frame = validate_m5(frame.sort_values("time_utc").reset_index(drop=True))
        context["stage"] = "deterministic_analysis"
        report_a, events_a = analyze(frame)
        report_b, events_b = analyze(frame)
        assert_outcome_blind(report_a, events_a)
        if json_bytes(report_a) != json_bytes(report_b) or ledger_bytes(events_a) != ledger_bytes(events_b):
            raise ValueError("deterministic replay mismatch")
        final = frozen_hashes()
        if final != initial:
            raise ValueError("bound input drift during source attempt")
        report_payload = json_bytes(report_a)
        ledger_payload = ledger_bytes(events_a)
        write_exclusive(REPORT_PATH, report_payload)
        write_exclusive(LEDGER_PATH, ledger_payload)
        receipt = {
            "schema_version": "eibb_source_attempt_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
            "frozen_hashes": initial,
            "attempt_started_sha256": sha256_file(START_PATH),
            "source_report_sha256": hashlib.sha256(report_payload).hexdigest().upper(),
            "source_ledger_sha256": hashlib.sha256(ledger_payload).hexdigest().upper(),
            "deterministic_replay": True,
            "outcomes_opened": False, "economics_opened": False,
        }
        write_exclusive(RECEIPT_PATH, json_bytes(receipt))
        write_exclusive(TERMINAL_PATH, json_bytes({
            "schema_version": "eibb_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE", "verdict": report_a["verdict"],
            "receipt_sha256": sha256_file(RECEIPT_PATH),
            "same_id_retry_authorized": False,
        }))
        return report_a
    except Exception as exc:
        context["error"] = f"{type(exc).__name__}: {exc}"
        context["status"] = "FAILED"
        context["same_id_retry_authorized"] = False
        if not TERMINAL_PATH.exists():
            write_exclusive(TERMINAL_PATH, json_bytes(context))
        raise


if __name__ == "__main__":
    print(json.dumps(execute(), indent=2, sort_keys=True, allow_nan=False))

