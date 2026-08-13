from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-BWVR-BTCUSD-M5-001"
ATTEMPT_ID = "BWVR-SOURCE-001"
SOURCE_SHA = "5B4DA734215BA56DE0DEA7C33E06ECC74C44EDE1CED9986AEB5B98F4B2053AE0"
MANIFEST_SHA = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
START_EPOCH = 1514764800
END_EPOCH = 1672531200
ATR_WINDOW = 14
WARMUP_ROWS = 15
LOCKOUT_BARS = 24
BAND_ATR = 1.50
ELAPSED_WEEKS = 1826.0 / 7.0
COLS = [
    "symbol", "timeframe", "source_epoch", "time_server", "time_utc",
    "utc_ambiguous", "open", "high", "low", "close", "tick_volume",
]

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
PREREG_PATH = RESEARCH_DIR / "HYP-BWVR-BTCUSD-M5-001_FROZEN_SOURCE_PREREG.md"
TEST_PATH = RESEARCH_DIR / "test_bwvr_source.py"
SOURCE_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/BTCUSD/BTCUSD_M5_ALL_AVAILABLE_20260801.parquet"
MANIFEST_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_exclusive(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def validate(frame: pd.DataFrame) -> pd.DataFrame:
    if list(frame.columns) != COLS:
        raise ValueError("schema mismatch")
    if not frame["symbol"].eq("BTCUSD").all() or not frame["timeframe"].eq("M5").all():
        raise ValueError("identity mismatch")
    epoch = frame["source_epoch"].to_numpy(dtype=np.int64)
    if len(frame) < 400_000 or not (np.diff(epoch) > 0).all():
        raise ValueError("row/order gate failed")
    if epoch[0] < START_EPOCH or epoch[-1] >= END_EPOCH:
        raise ValueError("window sealing failed")
    server = pd.to_datetime(frame["time_server"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    if server.isna().any() or not server.is_monotonic_increasing or server.duplicated().any():
        raise ValueError("time_server gate failed")
    expected_server = pd.to_datetime(epoch, unit="s")
    if not np.array_equal(server.to_numpy(), expected_server.to_numpy()):
        raise ValueError("source_epoch/time_server mismatch")
    utc = pd.to_datetime(frame["time_utc"], errors="coerce", utc=True)
    ambiguous = frame["utc_ambiguous"].astype(bool)
    if utc.notna().ne(~ambiguous).any():
        raise ValueError("UTC ambiguity contract failed")
    prices = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    volume = frame["tick_volume"].to_numpy(dtype=float)
    valid = (
        np.isfinite(prices).all(axis=1)
        & (prices > 0).all(axis=1)
        & np.isfinite(volume)
        & (volume > 0)
        & (prices[:, 1] >= prices[:, 2])
        & (prices[:, 2] <= prices[:, 0])
        & (prices[:, 0] <= prices[:, 1])
        & (prices[:, 2] <= prices[:, 3])
        & (prices[:, 3] <= prices[:, 1])
    )
    if not valid.all():
        raise ValueError("geometry gate failed")
    result = frame.copy()
    result["time_server"] = server
    result["time_utc"] = utc
    result["utc_ambiguous"] = ambiguous
    return result


def compute_features(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy().reset_index(drop=True)
    server = pd.to_datetime(data["time_server"])
    iso = server.dt.isocalendar()
    data["week_key"] = iso["year"].astype(str) + "-" + iso["week"].astype(str).str.zfill(2)
    typical = (data["high"].astype(float) + data["low"].astype(float) + data["close"].astype(float)) / 3.0
    weight = data["tick_volume"].astype(float)
    numerator = (typical * weight).groupby(data["week_key"], sort=False).cumsum()
    denominator = weight.groupby(data["week_key"], sort=False).cumsum()
    data["avwap"] = numerator / denominator
    prev_close = data["close"].shift(1)
    tr = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - prev_close).abs(),
            (data["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1, skipna=False)
    data["atr14_prev"] = tr.shift(1).rolling(ATR_WINDOW, min_periods=ATR_WINDOW).mean()
    data["lower"] = data["avwap"] - BAND_ATR * data["atr14_prev"]
    data["upper"] = data["avwap"] + BAND_ATR * data["atr14_prev"]
    same_week = data["week_key"].eq(data["week_key"].shift(1))
    base_valid = (
        np.isfinite(data[["avwap", "atr14_prev", "lower", "upper"]]).all(axis=1)
        & (data["atr14_prev"] > 0.0)
    )
    data["feature_usable"] = base_valid & base_valid.shift(1, fill_value=False) & same_week
    data["long_event"] = (
        data["feature_usable"]
        & (data["close"].shift(1) <= data["lower"].shift(1))
        & (data["close"] > data["lower"])
        & (data["close"] < data["avwap"])
    )
    data["short_event"] = (
        data["feature_usable"]
        & (data["close"].shift(1) >= data["upper"].shift(1))
        & (data["close"] < data["upper"])
        & (data["close"] > data["avwap"])
    )
    return data


def extract_events(data: pd.DataFrame) -> tuple[list[dict], int]:
    raw: list[dict] = []
    conflicts = 0
    lockout_until = -1
    for i in range(WARMUP_ROWS, len(data)):
        long_event = bool(data.at[i, "long_event"])
        short_event = bool(data.at[i, "short_event"])
        if long_event and short_event:
            conflicts += 1
            continue
        if not (long_event or short_event) or i <= lockout_until:
            continue
        lockout_until = i + LOCKOUT_BARS
        decision_epoch = int(data.at[i, "source_epoch"])
        has_next = i + 1 < len(data)
        exact_next = has_next and int(data.at[i + 1, "source_epoch"]) == decision_epoch + 300
        decision_utc_ok = not bool(data.at[i, "utc_ambiguous"]) and pd.notna(data.at[i, "time_utc"])
        next_utc_ok = exact_next and not bool(data.at[i + 1, "utc_ambiguous"]) and pd.notna(data.at[i + 1, "time_utc"])
        utc_available = bool(decision_utc_ok and next_utc_ok and data.at[i + 1, "time_utc"] == data.at[i, "time_utc"] + pd.Timedelta(minutes=5))
        availability_utc = data.at[i + 1, "time_utc"] if utc_available else None
        weekday_allowed = bool(utc_available and availability_utc.weekday() < 5)
        friday_blocked = bool(utc_available and availability_utc.weekday() == 4 and availability_utc.hour >= 20)
        direction = "LONG" if long_event else "SHORT"
        raw.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "decision_source_epoch": decision_epoch,
            "decision_time_server": pd.Timestamp(data.at[i, "time_server"]).isoformat(),
            "availability_time_utc": availability_utc.isoformat() if utc_available else None,
            "decision_year": int(availability_utc.year) if utc_available else None,
            "direction": direction,
            "avwap": float(data.at[i, "avwap"]),
            "atr14_prev": float(data.at[i, "atr14_prev"]),
            "active_band": float(data.at[i, "lower"] if long_event else data.at[i, "upper"]),
            "prior_close": float(data.at[i - 1, "close"]),
            "current_close": float(data.at[i, "close"]),
            "exact_next": bool(exact_next),
            "utc_available": utc_available,
            "weekday_allowed": weekday_allowed,
            "friday_20utc_blocked": friday_blocked,
        })
    return raw, conflicts


def analyze(frame: pd.DataFrame) -> tuple[dict, list[dict]]:
    data = compute_features(frame)
    raw, conflicts = extract_events(data)
    executable = [
        row for row in raw
        if row["exact_next"] and row["utc_available"] and row["weekday_allowed"] and not row["friday_20utc_blocked"]
    ]
    n = len(executable)
    feature_denominator = max(len(data) - WARMUP_ROWS, 1)
    feature_coverage = int(data.loc[WARMUP_ROWS:, "feature_usable"].sum()) / feature_denominator
    exact_next_coverage = sum(row["exact_next"] for row in raw) / len(raw) if raw else 0.0
    utc_coverage = sum(row["utc_available"] for row in raw) / len(raw) if raw else 0.0
    sides = {side: sum(row["direction"] == side for row in executable) for side in ("LONG", "SHORT")}
    shares = {side: sides[side] / n if n else 0.0 for side in sides}
    years = {year: sum(row["decision_year"] == year for row in executable) for year in range(2018, 2023)}
    year_weeks = {year: (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days / 7.0 for year in years}
    yearly_cadence = {str(year): years[year] / year_weeks[year] for year in years}
    cadence = n / ELAPSED_WEEKS
    max_year_share = max(years.values()) / n if n else 1.0
    gates = {
        "design_rows_gte_400000": len(data) >= 400_000,
        "feature_coverage_gte_0_99": feature_coverage >= 0.99,
        "utc_coverage_gte_0_99": utc_coverage >= 0.99,
        "exact_next_gte_0_97": exact_next_coverage >= 0.97,
        "events_gte_500": n >= 500,
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "long_share_gte_0_30": shares["LONG"] >= 0.30,
        "short_share_gte_0_30": shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
        "every_year_1_25_to_6_5": all(1.25 <= value <= 6.5 for value in yearly_cadence.values()),
        "zero_conflicts": conflicts == 0,
    }
    report = {
        "schema_version": "bwvr_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "year_axis": "availability_time_utc",
        "design_rows": len(data),
        "warmup_rows": WARMUP_ROWS,
        "feature_coverage": feature_coverage,
        "raw_consumed_events": len(raw),
        "weekend_blocked": sum(not row["weekday_allowed"] and row["utc_available"] for row in raw),
        "friday_blocked": sum(row["friday_20utc_blocked"] for row in raw),
        "executable_events": n,
        "utc_coverage": utc_coverage,
        "exact_next_coverage": exact_next_coverage,
        "cadence_per_week": cadence,
        "direction_counts": sides,
        "direction_shares": shares,
        "year_counts": years,
        "year_cadence": yearly_cadence,
        "max_year_share": max_year_share,
        "conflicts": conflicts,
        "gates": gates,
        "verdict": "PASS_SOURCE_FEASIBILITY" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY_GATE_FAIL",
    }
    return report, executable


def serialize_analysis(frame: pd.DataFrame) -> tuple[bytes, bytes]:
    report, ledger = analyze(frame)
    report_bytes = json_bytes(report)
    ledger_bytes = b"".join(json.dumps(row, sort_keys=True).encode("utf-8") + b"\n" for row in ledger)
    return report_bytes, ledger_bytes


def captured_hashes() -> dict[str, dict[str, str]]:
    paths = {
        "source": SOURCE_PATH,
        "manifest": MANIFEST_PATH,
        "prereg": PREREG_PATH,
        "analyzer": SCRIPT_PATH,
        "test": TEST_PATH,
    }
    return {label: {"path": str(path), "sha256": sha256_file(path)} for label, path in paths.items()}


def execute() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    started = {
        "schema_version": "bwvr_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(START_PATH, json_bytes(started))
    start_sha = sha256_file(START_PATH)
    try:
        initial = captured_hashes()
        if initial["source"]["sha256"] != SOURCE_SHA or initial["manifest"]["sha256"] != MANIFEST_SHA:
            raise ValueError("source/manifest hash mismatch")
        filters = [("source_epoch", ">=", START_EPOCH), ("source_epoch", "<", END_EPOCH)]
        frame = validate(pd.read_parquet(SOURCE_PATH, columns=COLS, filters=filters, engine="pyarrow"))
        report_bytes, ledger_bytes = serialize_analysis(frame)
        replay_report, replay_ledger = serialize_analysis(frame)
        if report_bytes != replay_report or ledger_bytes != replay_ledger:
            raise ValueError("deterministic replay mismatch")
        if captured_hashes() != initial:
            raise ValueError("bound input changed during analysis")
        write_exclusive(REPORT_PATH, report_bytes)
        write_exclusive(LEDGER_PATH, ledger_bytes)
        receipt = {
            "schema_version": "bwvr_source_attempt_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "attempt_started_sha256": start_sha,
            "inputs": initial,
            "outputs": {
                "report": {"path": str(REPORT_PATH), "sha256": sha256_file(REPORT_PATH)},
                "ledger": {"path": str(LEDGER_PATH), "sha256": sha256_file(LEDGER_PATH)},
            },
            "deterministic_replay": True,
            "outcomes_opened": False,
            "economics_evaluated": False,
        }
        if captured_hashes() != initial:
            raise ValueError("bound input changed before receipt")
        write_exclusive(RECEIPT_PATH, json_bytes(receipt))
        terminal = {
            "schema_version": "bwvr_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "attempt_started_sha256": start_sha,
            "attempt_receipt_sha256": sha256_file(RECEIPT_PATH),
            "same_id_retry_authorized": False,
        }
        write_exclusive(TERMINAL_PATH, json_bytes(terminal))
    except Exception as exc:
        if not TERMINAL_PATH.exists():
            failure = {
                "schema_version": "bwvr_source_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "status": "FAILED",
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "attempt_started_sha256": start_sha,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "same_id_retry_authorized": False,
            }
            write_exclusive(TERMINAL_PATH, json_bytes(failure))
        raise


if __name__ == "__main__":
    execute()
