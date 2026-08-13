from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-ISVA-XAUUSD-M5-001"
ATTEMPT_ID = "ISVA-SOURCE-001"
SOURCE_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
START_EPOCH = 1514764800
END_EPOCH = 1672531200
ELAPSED_WEEKS = 1826.0 / 7.0
SESSION_ROWS = 192
LOW_CLV = 1.0 / 3.0
HIGH_CLV = 2.0 / 3.0
COLS = [
    "symbol", "timeframe", "source_epoch", "time_server", "time_utc",
    "utc_ambiguous", "open", "high", "low", "close", "tick_volume",
]

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
PREREG_PATH = RESEARCH_DIR / "HYP-ISVA-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md"
REVIEW_PATH = RESEARCH_DIR / "HYP-ISVA-XAUUSD-M5-001_PRE_SOURCE_REVIEW.md"
TEST_PATH = RESEARCH_DIR / "test_isva_source.py"
MANIFEST_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
SOURCE_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
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


def claim_attempt() -> dict:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    started = {
        "schema_version": "isva_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(START_PATH, json_bytes(started))
    return started


def frozen_hashes() -> dict[str, str]:
    return {
        "analyzer": sha256_file(SCRIPT_PATH),
        "test": sha256_file(TEST_PATH),
        "prereg": sha256_file(PREREG_PATH),
        "pre_source_review": sha256_file(REVIEW_PATH),
        "manifest": sha256_file(MANIFEST_PATH),
        "source": sha256_file(SOURCE_PATH),
    }


def validate_hashes(hashes: dict[str, str]) -> None:
    if hashes["manifest"] != MANIFEST_SHA256 or hashes["source"] != SOURCE_SHA256:
        raise ValueError("manifest/source hash mismatch")


def read_design() -> pd.DataFrame:
    return pd.read_parquet(
        SOURCE_PATH,
        columns=COLS,
        filters=[("source_epoch", ">=", START_EPOCH), ("source_epoch", "<", END_EPOCH)],
        engine="pyarrow",
    )


def validate_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    observed: dict[str, object] = {"design_rows": int(len(frame)), "schema_exact": list(frame.columns) == COLS}
    if not observed["schema_exact"]:
        raise ValueError("schema mismatch")
    identity = bool(frame["symbol"].eq("XAUUSD").all() and frame["timeframe"].eq("M5").all())
    observed["identity_ok"] = identity
    if not identity:
        raise ValueError("identity mismatch")
    epoch = frame["source_epoch"].to_numpy(dtype=np.int64)
    strict = bool(len(epoch) > 0 and (np.diff(epoch) > 0).all())
    sealed = bool(len(epoch) > 0 and epoch[0] >= START_EPOCH and epoch[-1] < END_EPOCH)
    observed.update({
        "chronology_strict": strict,
        "window_sealed": sealed,
        "first_source_epoch": int(epoch[0]) if len(epoch) else None,
        "last_source_epoch": int(epoch[-1]) if len(epoch) else None,
    })
    if not strict or not sealed:
        raise ValueError("chronology/window gate failed")
    server = pd.to_datetime(frame["time_server"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    utc = pd.to_datetime(frame["time_utc"], errors="coerce", utc=True)
    clock_ok = bool(
        not server.isna().any()
        and server.is_monotonic_increasing
        and not server.duplicated().any()
        and np.array_equal(server.to_numpy(), pd.to_datetime(epoch, unit="s").to_numpy())
        and utc.notna().all()
        and not frame["utc_ambiguous"].astype(bool).any()
    )
    observed["clock_ok"] = clock_ok
    if not clock_ok:
        raise ValueError("clock contract failed")
    prices = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    volume = frame["tick_volume"].to_numpy(dtype=float)
    geometry = (
        np.isfinite(prices).all(axis=1)
        & (prices > 0).all(axis=1)
        & np.isfinite(volume)
        & (volume > 0)
        & (prices[:, 1] >= prices[:, 2])
        & (prices[:, 2] <= prices[:, 0]) & (prices[:, 0] <= prices[:, 1])
        & (prices[:, 2] <= prices[:, 3]) & (prices[:, 3] <= prices[:, 1])
    )
    observed["geometry_valid_rows"] = int(geometry.sum())
    observed["geometry_all_valid"] = bool(geometry.all())
    if not bool(geometry.all()):
        raise ValueError("geometry gate failed")
    result = frame.copy().reset_index(drop=True)
    result["time_server"] = server.reset_index(drop=True)
    result["time_utc"] = utc.reset_index(drop=True)
    result["utc_date"] = result["time_utc"].dt.date
    return result, observed


def session_measure(group: pd.DataFrame) -> dict | None:
    group = group.sort_values("time_utc")
    if len(group) != SESSION_ROWS:
        return None
    utc = group["time_utc"].reset_index(drop=True)
    epoch = group["source_epoch"].to_numpy(dtype=np.int64)
    expected = pd.date_range(utc.iloc[0].normalize(), periods=SESSION_ROWS, freq="5min", tz="UTC")
    if utc.iloc[0].hour != 0 or utc.iloc[0].minute != 0 or not np.array_equal(utc.to_numpy(), expected.to_numpy()):
        return None
    if not (np.diff(epoch) == 300).all():
        return None
    closes = group["close"].to_numpy(dtype=float)
    returns = np.diff(np.log(closes))
    rvplus = float(np.square(returns[returns > 0.0]).sum())
    rvminus = float(np.square(returns[returns < 0.0]).sum())
    session_high = float(group["high"].max())
    session_low = float(group["low"].min())
    session_close = float(closes[-1])
    span = session_high - session_low
    if not all(math.isfinite(value) for value in (rvplus, rvminus, session_high, session_low, session_close)) or span <= 0.0:
        return None
    clv = (session_close - session_low) / span
    return {
        "decision_index": int(group.index[-1]),
        "rvplus": rvplus,
        "rvminus": rvminus,
        "clv": float(clv),
        "session_high": session_high,
        "session_low": session_low,
        "session_close": session_close,
    }


def extract_events(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    intraday = frame[(frame["time_utc"].dt.weekday < 5) & (frame["time_utc"].dt.hour < 16)]
    expected_days = len(pd.bdate_range("2018-01-01", "2022-12-30"))
    raw: list[dict] = []
    complete_sessions = 0
    conflicts = 0
    for day, group in intraday.groupby("utc_date", sort=True):
        measure = session_measure(group)
        if measure is None:
            continue
        complete_sessions += 1
        long_event = measure["rvminus"] > measure["rvplus"] and measure["clv"] >= HIGH_CLV
        short_event = measure["rvplus"] > measure["rvminus"] and measure["clv"] <= LOW_CLV
        if long_event and short_event:
            conflicts += 1
            continue
        if not (long_event or short_event):
            continue
        i = measure["decision_index"]
        decision_epoch = int(frame.at[i, "source_epoch"])
        has_next = i + 1 < len(frame)
        exact_next = bool(
            has_next
            and int(frame.at[i + 1, "source_epoch"]) == decision_epoch + 300
            and frame.at[i + 1, "time_utc"] == frame.at[i, "time_utc"] + pd.Timedelta(minutes=5)
            and frame.at[i + 1, "time_utc"].date() == day
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
            "direction": "LONG" if long_event else "SHORT",
            "rvplus": measure["rvplus"],
            "rvminus": measure["rvminus"],
            "clv": measure["clv"],
            "session_high": measure["session_high"],
            "session_low": measure["session_low"],
            "session_close": measure["session_close"],
            "session_complete": True,
            "exact_next": exact_next,
        })
    return raw, {
        "expected_weekdays": expected_days,
        "complete_sessions": complete_sessions,
        "session_coverage": complete_sessions / expected_days,
        "direction_conflicts": conflicts,
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
    yearly_cadence = {str(year): years[year] / year_weeks[year] for year in years}
    cadence = n / ELAPSED_WEEKS
    max_year_share = max(years.values()) / n if n else 1.0
    gates = {
        "design_rows_gte_300000": len(frame) >= 300_000,
        "session_coverage_gte_0_95": diagnostics["session_coverage"] >= 0.95,
        "exact_next_gte_0_97": exact_next >= 0.97,
        "events_gte_500": n >= 500,
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "long_share_gte_0_30": shares["LONG"] >= 0.30,
        "short_share_gte_0_30": shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
        "every_year_1_25_to_6_5": all(1.25 <= value <= 6.5 for value in yearly_cadence.values()),
        "zero_conflicts": diagnostics["direction_conflicts"] == 0,
    }
    return {
        "schema_version": "isva_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "parameters": {"session_utc": "00:00-15:55", "low_clv": LOW_CLV, "high_clv": HIGH_CLV},
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
        "decision_year_cadence": yearly_cadence,
        "max_year_share": max_year_share,
        "gates": gates,
    }, executable


def execute() -> dict:
    context: dict[str, object] = {"stage": "claim", "observed": {}, "gate_results": {}, "outcomes_opened": False, "economics_evaluated": False}
    claim_attempt()
    try:
        context["stage"] = "bind_inputs"
        initial = frozen_hashes()
        context["input_hashes"] = initial
        validate_hashes(initial)
        context["stage"] = "read_design"
        frame = read_design()
        context["observed"] = {"design_rows": int(len(frame))}
        context["stage"] = "validate_design"
        valid, validation = validate_frame(frame)
        context["observed"] = validation
        context["stage"] = "analyze"
        report_a, ledger_a = analyze(valid, validation)
        report_b, ledger_b = analyze(valid, validation)
        replay = json_bytes(report_a) == json_bytes(report_b) and ledger_bytes(ledger_a) == ledger_bytes(ledger_b)
        report_a["gates"]["deterministic_replay"] = replay
        report_a["deterministic_replay"] = replay
        report_a["all_gates_pass"] = bool(all(report_a["gates"].values()))
        context["gate_results"] = report_a["gates"]
        context["observed"] = {**validation, "complete_sessions": report_a["complete_sessions"], "raw_events": report_a["raw_events"], "executable_events": report_a["executable_events"]}
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
            "schema_version": "isva_source_attempt_receipt.v1",
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
        terminal = {
            "schema_version": "isva_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": "PASS_SOURCE_FEASIBILITY" if report_a["all_gates_pass"] else "PARK_SOURCE_GATE_FAILURE",
            "attempt_started_sha256": sha256_file(START_PATH),
            "attempt_receipt_sha256": sha256_file(RECEIPT_PATH),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "same_id_retry_authorized": False,
        }
        write_exclusive(TERMINAL_PATH, json_bytes(terminal))
        return report_a
    except Exception as exc:
        context["error_type"] = type(exc).__name__
        context["error"] = str(exc)
        if not TERMINAL_PATH.exists():
            write_exclusive(TERMINAL_PATH, json_bytes({
                "schema_version": "isva_source_attempt_terminal.v1",
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
