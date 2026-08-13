from __future__ import annotations

import calendar
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-XJRR-XAUUSD-M5-001"
ATTEMPT_ID = "XJRR-SOURCE-002"
XAU_SHA = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"
JPY_SHA = "FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD"
START_EPOCH = 1514764800
END_EPOCH = 1672531200
WINDOW = 288
ELAPSED_WEEKS = 1826.0 / 7.0
COLS = ["symbol", "timeframe", "source_epoch", "time_server", "open", "high", "low", "close", "tick_volume"]

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
PREREG_PATH = RESEARCH_DIR / "HYP-XJRR-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md"
ADDENDUM_PATH = RESEARCH_DIR / "HYP-XJRR-XAUUSD-M5-001_SOURCE_EVIDENCE_ADDENDUM.md"
TEST_PATH = RESEARCH_DIR / "test_xjrr_source.py"
XAU_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
JPY_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/USDJPY/USDJPY_M5_ALL_AVAILABLE_20260801.parquet"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_exclusive(path: Path, payload: bytes) -> None:
    with path.open("xb") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())


def validate(frame: pd.DataFrame, symbol: str, minimum_rows: int = 300_000) -> pd.DataFrame:
    if list(frame.columns) != COLS:
        raise ValueError("schema mismatch")
    if not frame["symbol"].eq(symbol).all() or not frame["timeframe"].eq("M5").all():
        raise ValueError("identity mismatch")
    epoch = frame["source_epoch"].to_numpy(dtype=np.int64)
    if len(frame) < minimum_rows or not (np.diff(epoch) > 0).all():
        raise ValueError("row/order gate failed")
    if len(epoch) and (epoch[0] < START_EPOCH or epoch[-1] >= END_EPOCH):
        raise ValueError("window sealing failed")
    parsed_server = pd.to_datetime(frame["time_server"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    if parsed_server.isna().any() or not parsed_server.is_monotonic_increasing or parsed_server.duplicated().any():
        raise ValueError("time_server order gate failed")
    expected_server = pd.to_datetime(epoch, unit="s")
    if not np.array_equal(parsed_server.to_numpy(), expected_server.to_numpy()):
        raise ValueError("source_epoch/time_server mapping failed")
    values = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    volume = frame["tick_volume"].to_numpy(dtype=float)
    valid = (
        np.isfinite(values).all(axis=1) & np.isfinite(volume) & (volume > 0)
        & (values[:, 1] >= values[:, 2])
        & (values[:, 2] <= values[:, 0]) & (values[:, 0] <= values[:, 1])
        & (values[:, 2] <= values[:, 3]) & (values[:, 3] <= values[:, 1])
    )
    if not valid.all():
        raise ValueError("geometry gate failed")
    return frame


def join_sources(xau: pd.DataFrame, jpy: pd.DataFrame) -> pd.DataFrame:
    joined = xau[["source_epoch", "time_server", "close"]].rename(
        columns={"time_server": "xau_time_server", "close": "xau_close"}
    ).merge(
        jpy[["source_epoch", "time_server", "close"]].rename(
            columns={"time_server": "jpy_time_server", "close": "jpy_close"}
        ),
        on="source_epoch",
        how="inner",
        validate="one_to_one",
    )
    if joined.empty or not joined["xau_time_server"].eq(joined["jpy_time_server"]).all():
        raise ValueError("joined server-clock mismatch")
    joined = joined.rename(columns={"xau_time_server": "time_server"}).drop(columns=["jpy_time_server"])
    joined["both_symbols"] = True
    return joined


def last_sunday(year: int, month: int) -> int:
    last = calendar.monthrange(year, month)[1]
    return last - ((datetime(year, month, last).weekday() + 1) % 7)


def server_to_utc(server_time: datetime) -> datetime:
    start = datetime(server_time.year, 3, last_sunday(server_time.year, 3), 3)
    finish = datetime(server_time.year, 10, last_sunday(server_time.year, 10), 4)
    return server_time - timedelta(hours=3 if start <= server_time < finish else 2)


def compute_features(joined: pd.DataFrame) -> pd.DataFrame:
    result = joined.copy()
    rx = np.log(result["xau_close"] / result["xau_close"].shift(1))
    rj = np.log(result["jpy_close"] / result["jpy_close"].shift(1))
    sx = rx.shift(1).rolling(WINDOW, min_periods=WINDOW).sum()
    sy = rj.shift(1).rolling(WINDOW, min_periods=WINDOW).sum()
    sxx = (rx * rx).shift(1).rolling(WINDOW, min_periods=WINDOW).sum()
    syy = (rj * rj).shift(1).rolling(WINDOW, min_periods=WINDOW).sum()
    sxy = (rx * rj).shift(1).rolling(WINDOW, min_periods=WINDOW).sum()
    beta = sxy / syy
    mean = (sx - beta * sy) / WINDOW
    ss = sxx - 2.0 * beta * sxy + beta * beta * syy - WINDOW * mean * mean
    variance = (ss / (WINDOW - 1)).where(lambda value: value > 0.0)
    sigma = np.sqrt(variance)
    result["beta"] = beta
    result["sigma"] = sigma
    result["z"] = (rx - beta * rj) / sigma
    result["z_prior"] = result["z"].shift(1)
    return result


def extract_events(data: pd.DataFrame) -> tuple[list[dict], int]:
    usable = np.isfinite(data["beta"]) & np.isfinite(data["sigma"]) & np.isfinite(data["z"]) & np.isfinite(data["z_prior"])
    raw: list[dict] = []
    consumed_date = None
    lockout_until = -1
    conflicts = 0
    for i in range(1, len(data) - 1):
        if not usable.iloc[i]:
            continue
        zp = float(data.at[i, "z_prior"])
        z = float(data.at[i, "z"])
        long_event = zp <= -2.0 and z > -2.0
        short_event = zp >= 2.0 and z < 2.0
        if long_event and short_event:
            conflicts += 1
            continue
        if not (long_event or short_event):
            continue
        server_dt = pd.Timestamp(data.at[i, "time_server"]).to_pydatetime()
        server_date = server_dt.date()
        if consumed_date == server_date or i <= lockout_until:
            continue
        consumed_date = server_date
        lockout_until = i + 12
        current_epoch = int(data.at[i, "source_epoch"])
        next_exact = int(data.at[i + 1, "source_epoch"]) == current_epoch + 300 and bool(data.at[i + 1, "both_symbols"])
        availability_utc = server_to_utc(server_dt) + timedelta(seconds=300)
        friday_blocked = availability_utc.weekday() == 4 and availability_utc.hour >= 20
        raw.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "decision_source_epoch": current_epoch,
            "decision_time_server": server_dt.isoformat(),
            "availability_time_utc": availability_utc.isoformat(),
            "decision_year": server_dt.year,
            "direction": "LONG" if long_event else "SHORT",
            "beta": float(data.at[i, "beta"]),
            "sigma": float(data.at[i, "sigma"]),
            "z_prior": zp,
            "z": z,
            "exact_next": next_exact,
            "friday_20utc_blocked": friday_blocked,
        })
    return raw, conflicts


def analyze(joined: pd.DataFrame) -> tuple[dict, list[dict]]:
    data = compute_features(joined).reset_index(drop=True)
    usable = np.isfinite(data["beta"]) & np.isfinite(data["sigma"]) & np.isfinite(data["z"]) & np.isfinite(data["z_prior"])
    raw, conflicts = extract_events(data)
    executable = [row for row in raw if row["exact_next"] and not row["friday_20utc_blocked"]]
    n = len(executable)
    sides = {side: sum(row["direction"] == side for row in executable) for side in ("LONG", "SHORT")}
    years = {year: sum(row["decision_year"] == year for row in executable) for year in range(2018, 2023)}
    year_weeks = {year: (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days / 7 for year in years}
    feature_coverage = int(usable.sum()) / max(len(data) - (WINDOW + 2), 1)
    next_coverage = sum(row["exact_next"] for row in raw) / len(raw) if raw else 0.0
    cadence = n / ELAPSED_WEEKS
    shares = {side: sides[side] / n if n else 0.0 for side in sides}
    yearly = {str(year): years[year] / year_weeks[year] for year in years}
    max_year_share = max(years.values()) / n if n else 1.0
    gates = {
        "joined_rows_gte_300000": len(data) >= 300_000,
        "feature_coverage_gte_0_99": feature_coverage >= 0.99,
        "exact_next_gte_0_97": next_coverage >= 0.97,
        "events_gte_500": n >= 500,
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "long_share_gte_0_30": shares["LONG"] >= 0.30,
        "short_share_gte_0_30": shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
        "every_year_1_25_to_6_5": all(1.25 <= value <= 6.5 for value in yearly.values()),
        "zero_conflicts": conflicts == 0,
    }
    report = {
        "schema_version": "xjrr_source_report.v2",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "cadence_interpretation": "upper_bound_opportunity_population_before_trade_overlap_or_geometry",
        "year_axis": "decision_time_server",
        "joined_rows": len(data),
        "feature_coverage": feature_coverage,
        "raw_consumed_events": len(raw),
        "friday_blocked": sum(row["friday_20utc_blocked"] for row in raw),
        "executable_events": n,
        "exact_next_coverage": next_coverage,
        "cadence_per_week": cadence,
        "direction_counts": sides,
        "direction_shares": shares,
        "year_counts": years,
        "year_cadence": yearly,
        "max_year_share": max_year_share,
        "conflicts": conflicts,
        "gates": gates,
        "verdict": "PASS_SOURCE_FEASIBILITY" if all(gates.values()) else "PARK_SOURCE_FEASIBILITY_GATE_FAIL",
    }
    return report, executable


def serialize_analysis(joined: pd.DataFrame) -> tuple[bytes, bytes]:
    report, ledger = analyze(joined)
    return json_bytes(report), b"".join(json.dumps(row, sort_keys=True).encode("utf-8") + b"\n" for row in ledger)


def captured_hashes() -> dict[str, dict[str, str]]:
    paths = {
        "xau_source": XAU_PATH,
        "jpy_source": JPY_PATH,
        "prereg": PREREG_PATH,
        "evidence_addendum": ADDENDUM_PATH,
        "analyzer": SCRIPT_PATH,
        "test": TEST_PATH,
    }
    return {label: {"path": str(path), "sha256": sha256_file(path)} for label, path in paths.items()}


def execute() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    started = {
        "schema_version": "xjrr_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(START_PATH, json_bytes(started))
    start_sha = sha256_file(START_PATH)
    try:
        initial = captured_hashes()
        if initial["xau_source"]["sha256"] != XAU_SHA or initial["jpy_source"]["sha256"] != JPY_SHA:
            raise ValueError("source hash mismatch")
        filters = [("source_epoch", ">=", START_EPOCH), ("source_epoch", "<", END_EPOCH)]
        xau = validate(pd.read_parquet(XAU_PATH, columns=COLS, filters=filters, engine="pyarrow"), "XAUUSD")
        jpy = validate(pd.read_parquet(JPY_PATH, columns=COLS, filters=filters, engine="pyarrow"), "USDJPY")
        joined = join_sources(xau, jpy)
        report_bytes, ledger_bytes = serialize_analysis(joined)
        replay_report, replay_ledger = serialize_analysis(joined)
        if report_bytes != replay_report or ledger_bytes != replay_ledger:
            raise ValueError("deterministic replay mismatch")
        if captured_hashes() != initial:
            raise ValueError("bound input changed during analysis")
        write_exclusive(REPORT_PATH, report_bytes)
        write_exclusive(LEDGER_PATH, ledger_bytes)
        receipt = {
            "schema_version": "xjrr_source_attempt_receipt.v1",
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
            "schema_version": "xjrr_source_attempt_terminal.v1",
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
                "schema_version": "xjrr_source_attempt_terminal.v1",
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
