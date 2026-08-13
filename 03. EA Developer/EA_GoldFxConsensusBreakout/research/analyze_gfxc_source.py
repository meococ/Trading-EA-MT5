from __future__ import annotations

import calendar
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-GFXC-XAUUSD-M5-001"
ATTEMPT_ID = "GFXC-SOURCE-001"
START_EPOCH = 1514764800
END_EPOCH = 1672531200
SCALE_WINDOW = 288
RETURN_WINDOW = 12
BREAKOUT_WINDOW = 24
WARMUP_ROWS = 290
LOCKOUT_BARS = 12
Z_THRESHOLD = 0.50
ELAPSED_WEEKS = 1826.0 / 7.0
COLS = ["symbol", "timeframe", "source_epoch", "time_server", "open", "high", "low", "close", "tick_volume"]
SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY")
EXPECTED_SHA = {
    "XAUUSD": "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380",
    "EURUSD": "6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8",
    "GBPUSD": "8EE2720261FC05A13A2E919C3EAA4FF50EEF75F9CB068519C61C48BB3D6B4F4B",
    "USDJPY": "FECD42A01AFD14D4149121A122468DA5597939A20DD1533A36DA711E6FA2DAFD",
}

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
PREREG_PATH = RESEARCH_DIR / "HYP-GFXC-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md"
TEST_PATH = RESEARCH_DIR / "test_gfxc_source.py"
FOUNDATION = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004"
SOURCE_PATHS = {s: FOUNDATION / s / f"{s}_M5_ALL_AVAILABLE_20260801.parquet" for s in SYMBOLS}
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


def validate(frame: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if list(frame.columns) != COLS:
        raise ValueError(f"{symbol} schema mismatch")
    if not frame["symbol"].eq(symbol).all() or not frame["timeframe"].eq("M5").all():
        raise ValueError(f"{symbol} identity mismatch")
    epoch = frame["source_epoch"].to_numpy(dtype=np.int64)
    if len(frame) < 300_000 or not (np.diff(epoch) > 0).all():
        raise ValueError(f"{symbol} row/order gate failed")
    if epoch[0] < START_EPOCH or epoch[-1] >= END_EPOCH:
        raise ValueError(f"{symbol} window sealing failed")
    server = pd.to_datetime(frame["time_server"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    if server.isna().any() or not server.is_monotonic_increasing or server.duplicated().any():
        raise ValueError(f"{symbol} time_server order gate failed")
    expected_server = pd.to_datetime(epoch, unit="s")
    if not np.array_equal(server.to_numpy(), expected_server.to_numpy()):
        raise ValueError(f"{symbol} source_epoch/time_server mismatch")
    prices = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    volume = frame["tick_volume"].to_numpy(dtype=float)
    valid = (
        np.isfinite(prices).all(axis=1)
        & np.isfinite(volume)
        & (volume > 0)
        & (prices[:, 1] >= prices[:, 2])
        & (prices[:, 2] <= prices[:, 0])
        & (prices[:, 0] <= prices[:, 1])
        & (prices[:, 2] <= prices[:, 3])
        & (prices[:, 3] <= prices[:, 1])
        & (prices > 0).all(axis=1)
    )
    if not valid.all():
        raise ValueError(f"{symbol} geometry gate failed")
    return frame


def join_sources(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    xau = frames["XAUUSD"][["source_epoch", "time_server", "high", "low", "close"]].rename(
        columns={"time_server": "XAUUSD_time_server", "high": "xau_high", "low": "xau_low", "close": "XAUUSD_close"}
    )
    joined = xau
    for symbol in SYMBOLS[1:]:
        leg = frames[symbol][["source_epoch", "time_server", "close"]].rename(
            columns={"time_server": f"{symbol}_time_server", "close": f"{symbol}_close"}
        )
        joined = joined.merge(leg, on="source_epoch", how="inner", validate="one_to_one")
    clock_cols = [f"{symbol}_time_server" for symbol in SYMBOLS]
    for col in clock_cols[1:]:
        if not joined[clock_cols[0]].eq(joined[col]).all():
            raise ValueError(f"cross-symbol clock mismatch: {col}")
    joined = joined.rename(columns={clock_cols[0]: "time_server"}).drop(columns=clock_cols[1:])
    if len(joined) < 300_000 or not joined["source_epoch"].is_monotonic_increasing:
        raise ValueError("joined row/order gate failed")
    return joined.reset_index(drop=True)


def last_sunday(year: int, month: int) -> int:
    last = calendar.monthrange(year, month)[1]
    return last - ((datetime(year, month, last).weekday() + 1) % 7)


def server_to_utc(server_time: datetime) -> datetime:
    dst_start = datetime(server_time.year, 3, last_sunday(server_time.year, 3), 3)
    dst_end = datetime(server_time.year, 10, last_sunday(server_time.year, 10), 4)
    return server_time - timedelta(hours=3 if dst_start <= server_time < dst_end else 2)


def compute_features(joined: pd.DataFrame) -> pd.DataFrame:
    data = joined.copy()
    root12 = np.sqrt(float(RETURN_WINDOW))
    for symbol in SYMBOLS:
        close = data[f"{symbol}_close"].astype(float)
        one_bar = np.log(close / close.shift(1))
        sigma = one_bar.shift(1).rolling(SCALE_WINDOW, min_periods=SCALE_WINDOW).std(ddof=1)
        z12 = np.log(close / close.shift(RETURN_WINDOW)) / (sigma * root12)
        data[f"{symbol}_sigma"] = sigma.where(sigma > 0.0)
        data[f"{symbol}_z12"] = z12
    data["prior_upper"] = data["xau_high"].shift(1).rolling(BREAKOUT_WINDOW, min_periods=BREAKOUT_WINDOW).max()
    data["prior_lower"] = data["xau_low"].shift(1).rolling(BREAKOUT_WINDOW, min_periods=BREAKOUT_WINDOW).min()
    usable_cols = [f"{s}_sigma" for s in SYMBOLS] + [f"{s}_z12" for s in SYMBOLS] + ["prior_upper", "prior_lower"]
    data["feature_usable"] = np.isfinite(data[usable_cols]).all(axis=1)
    data["long_state"] = (
        data["feature_usable"]
        & (data["XAUUSD_close"] > data["prior_upper"])
        & (data["XAUUSD_z12"] >= Z_THRESHOLD)
        & (data["EURUSD_z12"] >= Z_THRESHOLD)
        & (data["GBPUSD_z12"] >= Z_THRESHOLD)
        & (data["USDJPY_z12"] <= -Z_THRESHOLD)
    )
    data["short_state"] = (
        data["feature_usable"]
        & (data["XAUUSD_close"] < data["prior_lower"])
        & (data["XAUUSD_z12"] <= -Z_THRESHOLD)
        & (data["EURUSD_z12"] <= -Z_THRESHOLD)
        & (data["GBPUSD_z12"] <= -Z_THRESHOLD)
        & (data["USDJPY_z12"] >= Z_THRESHOLD)
    )
    return data


def extract_events(data: pd.DataFrame) -> tuple[list[dict], int]:
    raw: list[dict] = []
    conflicts = 0
    lockout_until = -1
    for i in range(WARMUP_ROWS, len(data)):
        if not bool(data.at[i, "feature_usable"]):
            continue
        long_event = bool(data.at[i, "long_state"]) and not bool(data.at[i - 1, "long_state"])
        short_event = bool(data.at[i, "short_state"]) and not bool(data.at[i - 1, "short_state"])
        if long_event and short_event:
            conflicts += 1
            continue
        if not (long_event or short_event) or i <= lockout_until:
            continue
        lockout_until = i + LOCKOUT_BARS
        decision_epoch = int(data.at[i, "source_epoch"])
        exact_next = i + 1 < len(data) and int(data.at[i + 1, "source_epoch"]) == decision_epoch + 300
        server_time = pd.Timestamp(data.at[i, "time_server"]).to_pydatetime()
        availability_utc = server_to_utc(server_time + timedelta(seconds=300))
        friday_blocked = availability_utc.weekday() == 4 and availability_utc.hour >= 20
        direction = "LONG" if long_event else "SHORT"
        raw.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "decision_source_epoch": decision_epoch,
            "decision_time_server": server_time.isoformat(),
            "availability_time_utc": availability_utc.isoformat(),
            "decision_year": availability_utc.year,
            "direction": direction,
            "XAUUSD_z12": float(data.at[i, "XAUUSD_z12"]),
            "EURUSD_z12": float(data.at[i, "EURUSD_z12"]),
            "GBPUSD_z12": float(data.at[i, "GBPUSD_z12"]),
            "USDJPY_z12": float(data.at[i, "USDJPY_z12"]),
            "breakout_boundary": float(data.at[i, "prior_upper"] if long_event else data.at[i, "prior_lower"]),
            "exact_next": exact_next,
            "friday_20utc_blocked": friday_blocked,
        })
    return raw, conflicts


def analyze(joined: pd.DataFrame) -> tuple[dict, list[dict]]:
    data = compute_features(joined)
    raw, conflicts = extract_events(data)
    executable = [row for row in raw if row["exact_next"] and not row["friday_20utc_blocked"]]
    n = len(executable)
    usable_after_warmup = int(data.loc[WARMUP_ROWS:, "feature_usable"].sum())
    feature_denominator = max(len(data) - WARMUP_ROWS, 1)
    feature_coverage = usable_after_warmup / feature_denominator
    exact_next_coverage = sum(row["exact_next"] for row in raw) / len(raw) if raw else 0.0
    sides = {side: sum(row["direction"] == side for row in executable) for side in ("LONG", "SHORT")}
    shares = {side: sides[side] / n if n else 0.0 for side in sides}
    years = {year: sum(row["decision_year"] == year for row in executable) for year in range(2018, 2023)}
    year_weeks = {year: (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days / 7.0 for year in years}
    yearly_cadence = {str(year): years[year] / year_weeks[year] for year in years}
    cadence = n / ELAPSED_WEEKS
    max_year_share = max(years.values()) / n if n else 1.0
    gates = {
        "joined_rows_gte_300000": len(data) >= 300_000,
        "feature_coverage_gte_0_99": feature_coverage >= 0.99,
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
        "schema_version": "gfxc_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "year_axis": "availability_time_utc",
        "joined_rows": len(data),
        "warmup_rows": WARMUP_ROWS,
        "feature_coverage": feature_coverage,
        "raw_consumed_events": len(raw),
        "friday_blocked": sum(row["friday_20utc_blocked"] for row in raw),
        "executable_events": n,
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


def serialize_analysis(joined: pd.DataFrame) -> tuple[bytes, bytes]:
    report, ledger = analyze(joined)
    report_bytes = json_bytes(report)
    ledger_bytes = b"".join(json.dumps(row, sort_keys=True).encode("utf-8") + b"\n" for row in ledger)
    return report_bytes, ledger_bytes


def captured_hashes() -> dict[str, dict[str, str]]:
    paths = {f"{symbol}_source": path for symbol, path in SOURCE_PATHS.items()}
    paths.update({"prereg": PREREG_PATH, "analyzer": SCRIPT_PATH, "test": TEST_PATH})
    return {label: {"path": str(path), "sha256": sha256_file(path)} for label, path in paths.items()}


def execute() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    started = {
        "schema_version": "gfxc_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(START_PATH, json_bytes(started))
    start_sha = sha256_file(START_PATH)
    try:
        initial = captured_hashes()
        for symbol in SYMBOLS:
            if initial[f"{symbol}_source"]["sha256"] != EXPECTED_SHA[symbol]:
                raise ValueError(f"{symbol} source hash mismatch")
        filters = [("source_epoch", ">=", START_EPOCH), ("source_epoch", "<", END_EPOCH)]
        frames = {
            symbol: validate(pd.read_parquet(path, columns=COLS, filters=filters, engine="pyarrow"), symbol)
            for symbol, path in SOURCE_PATHS.items()
        }
        joined = join_sources(frames)
        report_bytes, ledger_bytes = serialize_analysis(joined)
        replay_report, replay_ledger = serialize_analysis(joined)
        if report_bytes != replay_report or ledger_bytes != replay_ledger:
            raise ValueError("deterministic replay mismatch")
        if captured_hashes() != initial:
            raise ValueError("bound input changed during analysis")
        write_exclusive(REPORT_PATH, report_bytes)
        write_exclusive(LEDGER_PATH, ledger_bytes)
        receipt = {
            "schema_version": "gfxc_source_attempt_receipt.v1",
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
            "schema_version": "gfxc_source_attempt_terminal.v1",
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
                "schema_version": "gfxc_source_attempt_terminal.v1",
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
