from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-CUSX-XAUUSD-M5-001"
ATTEMPT_ID = "CUSX-SOURCE-001"
SOURCE_SHA256 = "12679E647739D8DB616F78578D924912A1AC580CED535D763DBEA1B04480D380"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
START_EPOCH = 1514764800
END_EPOCH = 1672531200
ATR_WINDOW = 48
WARMUP_ROWS = 49
REFERENCE_ALLOWANCE = 0.05
THRESHOLD = 3.00
ELAPSED_WEEKS = 1826.0 / 7.0
COLS = [
    "symbol", "timeframe", "source_epoch", "time_server", "time_utc",
    "utc_ambiguous", "open", "high", "low", "close", "tick_volume",
]

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
PREREG_PATH = RESEARCH_DIR / "HYP-CUSX-XAUUSD-M5-001_FROZEN_SOURCE_PREREG.md"
REVIEW_PATH = RESEARCH_DIR / "HYP-CUSX-XAUUSD-M5-001_PRE_SOURCE_REVIEW.md"
TEST_PATH = RESEARCH_DIR / "test_cusx_source.py"
MANIFEST_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
SOURCE_PATH = REPO_ROOT / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/XAUUSD/XAUUSD_M5_ALL_AVAILABLE_20260801.parquet"
ATTEMPT_ROOT = RESEARCH_DIR / "evidence" / HYPOTHESIS_ID / ATTEMPT_ID
START_PATH = ATTEMPT_ROOT / "attempt_started.json"
REPORT_PATH = ATTEMPT_ROOT / "source_report.json"
LEDGER_PATH = ATTEMPT_ROOT / "source_ledger.jsonl"
RECEIPT_PATH = ATTEMPT_ROOT / "attempt_receipt.json"
TERMINAL_PATH = ATTEMPT_ROOT / "attempt_terminal.json"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def ledger_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
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
        "schema_version": "cusx_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(START_PATH, json_bytes(started))
    return started


def frozen_input_hashes() -> dict[str, str]:
    return {
        "analyzer": sha256_file(SCRIPT_PATH),
        "test": sha256_file(TEST_PATH),
        "prereg": sha256_file(PREREG_PATH),
        "pre_source_review": sha256_file(REVIEW_PATH),
        "manifest": sha256_file(MANIFEST_PATH),
        "source": sha256_file(SOURCE_PATH),
    }


def validate_frozen_hashes(hashes: dict[str, str]) -> None:
    if hashes["manifest"] != MANIFEST_SHA256:
        raise ValueError("manifest hash mismatch")
    if hashes["source"] != SOURCE_SHA256:
        raise ValueError("source hash mismatch")


def read_design() -> pd.DataFrame:
    return pd.read_parquet(
        SOURCE_PATH,
        columns=COLS,
        filters=[
            ("source_epoch", ">=", START_EPOCH),
            ("source_epoch", "<", END_EPOCH),
        ],
        engine="pyarrow",
    )


def validate_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    observed: dict[str, object] = {
        "design_rows": int(len(frame)),
        "schema_exact": list(frame.columns) == COLS,
    }
    if not observed["schema_exact"]:
        raise ValueError("schema mismatch")
    identity_ok = bool(frame["symbol"].eq("XAUUSD").all() and frame["timeframe"].eq("M5").all())
    observed["identity_ok"] = identity_ok
    if not identity_ok:
        raise ValueError("identity mismatch")

    epoch = frame["source_epoch"].to_numpy(dtype=np.int64)
    chronology_ok = bool(len(epoch) > 0 and (np.diff(epoch) > 0).all())
    window_sealed = bool(len(epoch) > 0 and epoch[0] >= START_EPOCH and epoch[-1] < END_EPOCH)
    observed["chronology_strict"] = chronology_ok
    observed["window_sealed"] = window_sealed
    observed["first_source_epoch"] = int(epoch[0]) if len(epoch) else None
    observed["last_source_epoch"] = int(epoch[-1]) if len(epoch) else None
    if not chronology_ok:
        raise ValueError("source chronology gate failed")
    if not window_sealed:
        raise ValueError("window sealing failed")

    server = pd.to_datetime(frame["time_server"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    utc = pd.to_datetime(frame["time_utc"], errors="coerce", utc=True)
    ambiguous = frame["utc_ambiguous"].astype(bool)
    server_ok = bool(not server.isna().any() and server.is_monotonic_increasing and not server.duplicated().any())
    epoch_server_ok = bool(np.array_equal(server.to_numpy(), pd.to_datetime(epoch, unit="s").to_numpy()))
    utc_ok = bool(not ambiguous.any() and utc.notna().all())
    observed.update({
        "time_server_ok": server_ok,
        "source_epoch_time_server_equal": epoch_server_ok,
        "utc_complete_unambiguous": utc_ok,
    })
    if not server_ok or not epoch_server_ok or not utc_ok:
        raise ValueError("clock contract failed")

    prices = frame[["open", "high", "low", "close"]].to_numpy(dtype=float)
    volume = frame["tick_volume"].to_numpy(dtype=float)
    geometry = (
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
    observed["geometry_valid_rows"] = int(geometry.sum())
    observed["geometry_all_valid"] = bool(geometry.all())
    if not bool(geometry.all()):
        raise ValueError("geometry gate failed")

    result = frame.copy().reset_index(drop=True)
    result["time_server"] = server.reset_index(drop=True)
    result["time_utc"] = utc.reset_index(drop=True)
    result["utc_ambiguous"] = ambiguous.reset_index(drop=True)
    return result, observed


def compute_atr48_prev(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    tr = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1, skipna=False)
    return tr.shift(1).rolling(ATR_WINDOW, min_periods=ATR_WINDOW).mean()


def extract_events(frame: pd.DataFrame) -> tuple[list[dict], dict]:
    data = frame.copy()
    data["atr48_prev"] = compute_atr48_prev(data)
    epoch = data["source_epoch"].to_numpy(dtype=np.int64)
    close = data["close"].to_numpy(dtype=float)
    atr = data["atr48_prev"].to_numpy(dtype=float)
    exact_previous = np.zeros(len(data), dtype=bool)
    exact_previous[1:] = np.diff(epoch) == 300
    feature_usable = exact_previous & np.isfinite(atr) & (atr > 0.0)

    polarity = 0
    splus = 0.0
    sminus = 0.0
    raw: list[dict] = []
    conflicts = 0
    gap_resets = 0

    for i in range(1, len(data)):
        if not exact_previous[i]:
            polarity = 0
            splus = 0.0
            sminus = 0.0
            gap_resets += 1
            continue
        if not feature_usable[i]:
            continue

        innovation = (close[i] - close[i - 1]) / atr[i]
        splus = max(0.0, splus + innovation - REFERENCE_ALLOWANCE)
        sminus = min(0.0, sminus + innovation + REFERENCE_ALLOWANCE)
        long_event = splus >= THRESHOLD and polarity != 1
        short_event = sminus <= -THRESHOLD and polarity != -1
        if long_event and short_event:
            conflicts += 1
            splus = 0.0
            sminus = 0.0
            polarity = 0
            continue
        if not long_event and not short_event:
            continue

        prior_polarity = polarity
        direction = "LONG" if long_event else "SHORT"
        hit_splus = splus
        hit_sminus = sminus
        polarity = 1 if long_event else -1
        decision_epoch = int(epoch[i])
        has_next = i + 1 < len(data)
        exact_next = bool(has_next and int(epoch[i + 1]) == decision_epoch + 300)
        availability = data.at[i + 1, "time_utc"] if exact_next else None
        weekday_allowed = bool(exact_next and availability.weekday() < 5)
        friday_blocked = bool(exact_next and availability.weekday() == 4 and availability.hour >= 20)
        raw.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "decision_source_epoch": decision_epoch,
            "availability_source_epoch": int(epoch[i + 1]) if exact_next else None,
            "availability_time_utc": availability.isoformat() if exact_next else None,
            "decision_year": int(availability.year) if exact_next else None,
            "direction": direction,
            "prior_polarity": int(prior_polarity),
            "normalized_innovation": float(innovation),
            "atr48_prev": float(atr[i]),
            "splus_at_hit": float(hit_splus),
            "sminus_at_hit": float(hit_sminus),
            "exact_next": exact_next,
            "weekday_allowed": weekday_allowed,
            "friday_20utc_blocked": friday_blocked,
        })
        splus = 0.0
        sminus = 0.0

    diagnostics = {
        "feature_usable_rows": int(feature_usable[WARMUP_ROWS:].sum()),
        "feature_denominator": int(max(len(data) - WARMUP_ROWS, 1)),
        "gap_resets": int(gap_resets),
        "direction_conflicts": int(conflicts),
    }
    return raw, diagnostics


def analyze(frame: pd.DataFrame, validation: dict) -> tuple[dict, list[dict]]:
    raw, diagnostics = extract_events(frame)
    executable = [
        row for row in raw
        if row["exact_next"] and row["weekday_allowed"] and not row["friday_20utc_blocked"]
    ]
    n = len(executable)
    feature_coverage = diagnostics["feature_usable_rows"] / diagnostics["feature_denominator"]
    exact_next_coverage = sum(row["exact_next"] for row in raw) / len(raw) if raw else 0.0
    sides = {side: sum(row["direction"] == side for row in executable) for side in ("LONG", "SHORT")}
    shares = {side: sides[side] / n if n else 0.0 for side in sides}
    years = {year: sum(row["decision_year"] == year for row in executable) for year in range(2018, 2023)}
    year_weeks = {year: (datetime(year + 1, 1, 1) - datetime(year, 1, 1)).days / 7.0 for year in years}
    yearly_cadence = {str(year): years[year] / year_weeks[year] for year in years}
    cadence = n / ELAPSED_WEEKS
    max_year_share = max(years.values()) / n if n else 1.0
    gates = {
        "design_rows_gte_300000": len(frame) >= 300_000,
        "feature_coverage_gte_0_98": feature_coverage >= 0.98,
        "exact_next_gte_0_97": exact_next_coverage >= 0.97,
        "events_gte_500": n >= 500,
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "long_share_gte_0_30": shares["LONG"] >= 0.30,
        "short_share_gte_0_30": shares["SHORT"] >= 0.30,
        "max_year_share_lte_0_30": max_year_share <= 0.30,
        "every_year_1_25_to_6_5": all(1.25 <= value <= 6.5 for value in yearly_cadence.values()),
        "zero_conflicts": diagnostics["direction_conflicts"] == 0,
    }
    report = {
        "schema_version": "cusx_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "outcomes_opened": False,
        "economics_evaluated": False,
        "parameters": {
            "atr_window": ATR_WINDOW,
            "reference_allowance": REFERENCE_ALLOWANCE,
            "threshold": THRESHOLD,
            "gap_reset_seconds": 300,
        },
        "validation": validation,
        "design_rows": int(len(frame)),
        "feature_usable_rows": diagnostics["feature_usable_rows"],
        "feature_coverage": feature_coverage,
        "gap_resets": diagnostics["gap_resets"],
        "raw_events": len(raw),
        "executable_events": n,
        "weekend_blocked": sum(row["exact_next"] and not row["weekday_allowed"] for row in raw),
        "friday_blocked": sum(row["friday_20utc_blocked"] for row in raw),
        "exact_next_coverage": exact_next_coverage,
        "cadence_per_week": cadence,
        "directions": sides,
        "direction_shares": shares,
        "decision_year_counts": {str(key): value for key, value in years.items()},
        "decision_year_cadence": yearly_cadence,
        "max_year_share": max_year_share,
        "direction_conflicts": diagnostics["direction_conflicts"],
        "gates": gates,
    }
    return report, executable


def execute() -> dict:
    context: dict[str, object] = {
        "stage": "claim",
        "observed": {},
        "gate_results": {},
        "outcomes_opened": False,
        "economics_evaluated": False,
    }
    started = claim_attempt()
    try:
        context["stage"] = "bind_inputs"
        initial_hashes = frozen_input_hashes()
        context["input_hashes"] = initial_hashes
        validate_frozen_hashes(initial_hashes)

        context["stage"] = "read_design"
        frame = read_design()
        context["observed"] = {"design_rows": int(len(frame))}

        context["stage"] = "validate_design"
        valid, validation = validate_frame(frame)
        context["observed"] = validation

        context["stage"] = "analyze"
        report_a, ledger_a = analyze(valid, validation)
        report_b, ledger_b = analyze(valid, validation)
        replay_equal = json_bytes(report_a) == json_bytes(report_b) and ledger_bytes(ledger_a) == ledger_bytes(ledger_b)
        report_a["gates"]["deterministic_replay"] = replay_equal
        report_a["deterministic_replay"] = replay_equal
        report_a["all_gates_pass"] = bool(all(report_a["gates"].values()))
        context["gate_results"] = report_a["gates"]
        context["observed"] = {
            **validation,
            "raw_events": report_a["raw_events"],
            "executable_events": report_a["executable_events"],
            "cadence_per_week": report_a["cadence_per_week"],
        }
        if not replay_equal:
            raise ValueError("deterministic replay mismatch")

        context["stage"] = "rehash_inputs"
        final_hashes = frozen_input_hashes()
        if final_hashes != initial_hashes:
            raise ValueError("frozen input drift")

        report_payload = json_bytes(report_a)
        ledger_payload = ledger_bytes(ledger_a)
        write_exclusive(REPORT_PATH, report_payload)
        write_exclusive(LEDGER_PATH, ledger_payload)
        receipt = {
            "schema_version": "cusx_source_attempt_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "attempt_started_sha256": sha256_file(START_PATH),
            "input_hashes": final_hashes,
            "source_report_sha256": sha256_bytes(report_payload),
            "source_ledger_sha256": sha256_bytes(ledger_payload),
            "outcomes_opened": False,
            "economics_evaluated": False,
            "same_id_retry_authorized": False,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_exclusive(RECEIPT_PATH, json_bytes(receipt))
        verdict = "PASS_SOURCE_FEASIBILITY" if report_a["all_gates_pass"] else "PARK_SOURCE_GATE_FAILURE"
        terminal = {
            "schema_version": "cusx_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "COMPLETE",
            "verdict": verdict,
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
        terminal = {
            "schema_version": "cusx_source_attempt_terminal.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "FAILED",
            "verdict": "FAILED_ENGINEERING_STRUCTURED_EVIDENCE",
            "attempt_started_sha256": sha256_file(START_PATH),
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "same_id_retry_authorized": False,
            "failure_context": context,
        }
        if not TERMINAL_PATH.exists():
            write_exclusive(TERMINAL_PATH, json_bytes(terminal))
        raise


if __name__ == "__main__":
    print(json.dumps(execute(), indent=2, sort_keys=True))
