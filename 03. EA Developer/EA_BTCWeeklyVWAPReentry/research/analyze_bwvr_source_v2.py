from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-BWVR-BTCUSD-M5-002"
ATTEMPT_ID = "BWVR002-SOURCE-001"
MIN_DESIGN_ROWS = 220_000
SOURCE_SHA = "5B4DA734215BA56DE0DEA7C33E06ECC74C44EDE1CED9986AEB5B98F4B2053AE0"
MANIFEST_SHA = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
BASE_ANALYZER_SHA = "39B2AF7B9EFE21964DD65646FFB7678A17DA6310C61B6434E9379B3F43D81A0E"
START_EPOCH = 1514764800
END_EPOCH = 1672531200
COLS = [
    "symbol", "timeframe", "source_epoch", "time_server", "time_utc",
    "utc_ambiguous", "open", "high", "low", "close", "tick_volume",
]

SCRIPT_PATH = Path(__file__).resolve()
RESEARCH_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPT_PATH.parents[3]
BASE_ANALYZER_PATH = RESEARCH_DIR / "analyze_bwvr_source.py"
PREREG_PATH = RESEARCH_DIR / "HYP-BWVR-BTCUSD-M5-002_FROZEN_SOURCE_PREREG.md"
TEST_PATH = RESEARCH_DIR / "test_bwvr_source_v2.py"
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


def load_base():
    if sha256_file(BASE_ANALYZER_PATH) != BASE_ANALYZER_SHA:
        raise ValueError("formula dependency hash mismatch")
    spec = importlib.util.spec_from_file_location("bwvr_parent_formula", BASE_ANALYZER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.HYPOTHESIS_ID = HYPOTHESIS_ID
    module.ATTEMPT_ID = ATTEMPT_ID
    return module


def observed_contract(frame: pd.DataFrame) -> dict[str, object]:
    epoch = frame["source_epoch"].to_numpy(dtype=np.int64) if "source_epoch" in frame else np.array([], dtype=np.int64)
    return {
        "design_rows": int(len(frame)),
        "minimum_design_rows": MIN_DESIGN_ROWS,
        "row_floor_pass": bool(len(frame) >= MIN_DESIGN_ROWS),
        "first_source_epoch": int(epoch[0]) if len(epoch) else None,
        "last_source_epoch": int(epoch[-1]) if len(epoch) else None,
        "strict_source_epoch_order": bool(len(epoch) > 0 and (np.diff(epoch) > 0).all()),
        "schema_exact": bool(list(frame.columns) == COLS),
    }


def validate_v2(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    observed = observed_contract(frame)
    if not observed["schema_exact"]:
        raise ValueError("schema gate failed")
    if not frame["symbol"].eq("BTCUSD").all() or not frame["timeframe"].eq("M5").all():
        raise ValueError("identity gate failed")
    if not observed["row_floor_pass"]:
        raise ValueError("design row floor failed")
    if not observed["strict_source_epoch_order"]:
        raise ValueError("source epoch order gate failed")

    epoch = frame["source_epoch"].to_numpy(dtype=np.int64)
    if epoch[0] < START_EPOCH or epoch[-1] >= END_EPOCH:
        raise ValueError("window sealing gate failed")
    server = pd.to_datetime(frame["time_server"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    if server.isna().any() or not server.is_monotonic_increasing or server.duplicated().any():
        raise ValueError("time_server chronology gate failed")
    expected_server = pd.to_datetime(epoch, unit="s")
    if not np.array_equal(server.to_numpy(), expected_server.to_numpy()):
        raise ValueError("source_epoch/time_server gate failed")
    utc = pd.to_datetime(frame["time_utc"], errors="coerce", utc=True)
    ambiguous = frame["utc_ambiguous"].astype(bool)
    if utc.notna().ne(~ambiguous).any():
        raise ValueError("UTC ambiguity gate failed")

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
    observed.update({
        "window_sealed": True,
        "time_server_chronology_pass": True,
        "source_epoch_time_server_match": True,
        "utc_ambiguity_contract_pass": True,
        "geometry_pass": True,
    })
    return result, observed


def analyze_v2(frame: pd.DataFrame, base) -> tuple[dict, list[dict]]:
    report, ledger = base.analyze(frame)
    old_gate = report["gates"].pop("design_rows_gte_400000")
    if old_gate and len(frame) < MIN_DESIGN_ROWS:
        raise AssertionError("inconsistent parent row gate")
    report["schema_version"] = "bwvr002_source_report.v1"
    report["hypothesis_id"] = HYPOTHESIS_ID
    report["attempt_id"] = ATTEMPT_ID
    report["parent_formula_analyzer_sha256"] = BASE_ANALYZER_SHA
    report["minimum_design_rows"] = MIN_DESIGN_ROWS
    report["gates"] = {"design_rows_gte_220000": len(frame) >= MIN_DESIGN_ROWS, **report["gates"]}
    report["verdict"] = "PASS_SOURCE_FEASIBILITY" if all(report["gates"].values()) else "PARK_SOURCE_FEASIBILITY_GATE_FAIL"
    return report, ledger


def serialize_analysis(frame: pd.DataFrame, base) -> tuple[bytes, bytes]:
    report, ledger = analyze_v2(frame, base)
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
        "formula_dependency": BASE_ANALYZER_PATH,
    }
    return {label: {"path": str(path), "sha256": sha256_file(path)} for label, path in paths.items()}


def execute() -> None:
    ATTEMPT_ROOT.parent.mkdir(parents=True, exist_ok=True)
    ATTEMPT_ROOT.mkdir()
    started = {
        "schema_version": "bwvr002_source_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "same_id_retry_authorized": False,
    }
    write_exclusive(START_PATH, json_bytes(started))
    start_sha = sha256_file(START_PATH)
    initial = None
    observed: dict[str, object] = {}
    try:
        initial = captured_hashes()
        if initial["source"]["sha256"] != SOURCE_SHA or initial["manifest"]["sha256"] != MANIFEST_SHA:
            raise ValueError("source/manifest hash mismatch")
        if initial["formula_dependency"]["sha256"] != BASE_ANALYZER_SHA:
            raise ValueError("formula dependency hash mismatch")
        base = load_base()
        filters = [("source_epoch", ">=", START_EPOCH), ("source_epoch", "<", END_EPOCH)]
        raw_frame = pd.read_parquet(SOURCE_PATH, columns=COLS, filters=filters, engine="pyarrow")
        observed = observed_contract(raw_frame)
        frame, observed = validate_v2(raw_frame)
        report_bytes, ledger_bytes = serialize_analysis(frame, base)
        replay_report, replay_ledger = serialize_analysis(frame, base)
        if report_bytes != replay_report or ledger_bytes != replay_ledger:
            raise ValueError("deterministic replay mismatch")
        if captured_hashes() != initial:
            raise ValueError("bound input changed during analysis")
        write_exclusive(REPORT_PATH, report_bytes)
        write_exclusive(LEDGER_PATH, ledger_bytes)
        receipt = {
            "schema_version": "bwvr002_source_attempt_receipt.v1",
            "hypothesis_id": HYPOTHESIS_ID,
            "attempt_id": ATTEMPT_ID,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "attempt_started_sha256": start_sha,
            "inputs": initial,
            "observed_source_contract": observed,
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
            "schema_version": "bwvr002_source_attempt_terminal.v1",
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
                "schema_version": "bwvr002_source_attempt_terminal.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "status": "FAILED",
                "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "attempt_started_sha256": start_sha,
                "input_hashes": initial,
                "observed_source_contract": observed,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "same_id_retry_authorized": False,
            }
            write_exclusive(TERMINAL_PATH, json_bytes(failure))
        raise


if __name__ == "__main__":
    execute()
