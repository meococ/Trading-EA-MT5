#!/usr/bin/env python3
"""Frozen contracts and low-level helpers for the FVG comparison casebook.

This module intentionally contains study-specific defaults.  Nothing here is
part of the strategy-neutral AlphaFactory research SDK.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

STUDY_ID = "STUDY-FVG-COMPARE-EURUSD-M5-001"
HYPOTHESIS_ID = "HYP-FVG-HUMAN-CONTEXT-EURUSD-M5-001"
HOLDOUT = pd.Timestamp("2023-01-01T00:00:00")
SEED = 26071801
ALLOWED_LABELS = frozenset({"ACCEPT", "REJECT", "UNCERTAIN"})
STRATA = (
    "ea_source_signal_core",
    "high_recall_fvg_reject",
    "near_miss_control",
)

ROOT = Path(__file__).resolve().parents[5]
CASEBOOK_DIR = Path(__file__).resolve().parent
COMPARISON_DIR = CASEBOOK_DIR.parent
PROTOCOL_PATH = COMPARISON_DIR / "BENCHMARK_PROTOCOL_V1.json"
SOURCE_PATH = ROOT / "03. EA Developer/EA_FVGConfluence/EA_FVGConfluence.mq5"
INCLUDE_DIR = SOURCE_PATH.parent / "Include"
DATA_MANIFEST_PATH = ROOT / "02. AlphaFactory/data/fivepercent/EURUSD/manifest.json"
M1_PATH = DATA_MANIFEST_PATH.parent / "EURUSD_M1_2015_now.parquet"
REGISTRY_PATH = ROOT / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
RESEARCH_TOOLS_DIR = ROOT / "02. AlphaFactory/tools/research"
if str(RESEARCH_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_TOOLS_DIR))

from indicators import atr_mt5 as _alpha_atr_mt5  # noqa: E402


class ContractError(RuntimeError):
    """A fail-closed contract violation."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def canonical_json_bytes(value: Any) -> bytes:
    def encode_extra(obj: Any) -> Any:
        if isinstance(obj, np.generic):
            return obj.item()
        if isinstance(obj, (pd.Timestamp, np.datetime64)):
            return pd.Timestamp(obj).isoformat()
        raise TypeError(f"unsupported JSON type: {type(obj).__name__}")
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       default=encode_extra) + "\n").encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_frozen_inputs() -> dict[str, Any]:
    protocol = load_json(PROTOCOL_PATH)
    if protocol.get("schema_version") != "fvg_comparison_protocol.v1":
        raise ContractError("protocol schema is not fvg_comparison_protocol.v1")
    if protocol.get("study_id") != STUDY_ID:
        raise ContractError("study id mismatch")
    if protocol["data"].get("holdout_start_utc") != "2023-01-01T00:00:00Z":
        raise ContractError("holdout boundary drift")
    expected = {
        SOURCE_PATH: protocol["specimen"]["source_sha256"],
        DATA_MANIFEST_PATH: protocol["data"]["manifest_sha256"],
        M1_PATH: protocol["data"]["m1_sha256"],
    }
    for path, wanted in expected.items():
        got = sha256_file(path)
        if got != wanted:
            raise ContractError(f"SHA256 mismatch: {path}; expected={wanted} got={got}")
    return protocol


def source_binding() -> dict[str, Any]:
    protocol = assert_frozen_inputs()
    files = [SOURCE_PATH, *sorted(INCLUDE_DIR.glob("*.mqh"))]
    return {
        "schema_version": "fvg_source_binding.v1",
        "study_id": STUDY_ID,
        "protocol_sha256": sha256_file(PROTOCOL_PATH),
        "protocol_declared_main_source_sha256": protocol["specimen"]["source_sha256"],
        "files": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in files
        ],
    }


def casebook_code_binding() -> dict[str, Any]:
    """Bind the exact pre-outcome builder, gate, and analysis surfaces."""
    paths = [
        CASEBOOK_DIR / "casebook_contract.py",
        CASEBOOK_DIR / "build_casebook.py",
        CASEBOOK_DIR / "validate_casebook.py",
        CASEBOOK_DIR / "run_label_gate.py",
        CASEBOOK_DIR / "analyze_locked_economics.py",
        CASEBOOK_DIR / "SEALED_ANALYSIS_PLAN.json",
        CASEBOOK_DIR / "PREREG_TEMPLATE.json",
        RESEARCH_TOOLS_DIR / "indicators.py",
    ]
    return {
        "schema_version": "fvg_casebook_code_binding.v1",
        "files": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in paths
        ],
    }


def load_m1_pre_holdout(start: str = "2018-09-01") -> pd.DataFrame:
    """Load only pre-holdout rows using parquet predicate pushdown.

    The strict upper filter is repeated after load so a backend that ignores
    filters cannot silently expose the holdout to the builder.
    """
    assert_frozen_inputs()
    cols = ["time_server", "time_utc", "open", "high", "low", "close", "tick_volume"]
    frame = pd.read_parquet(
        M1_PATH,
        columns=cols,
        filters=[("time_utc", ">=", pd.Timestamp(start)), ("time_utc", "<", HOLDOUT)],
    )
    frame = frame[(frame["time_utc"] >= pd.Timestamp(start)) & (frame["time_utc"] < HOLDOUT)].copy()
    if frame.empty or frame["time_utc"].max() >= HOLDOUT:
        raise ContractError("M1 loader empty or crossed the 2023 holdout boundary")
    if frame["time_utc"].duplicated().any():
        raise ContractError("duplicate M1 UTC timestamps")
    return frame.sort_values("time_utc").reset_index(drop=True)


def resample_ohlc(m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if minutes not in (5, 15, 60):
        raise ValueError("only M5/M15/H1 are supported")
    x = m1.set_index("time_utc")
    rule = f"{minutes}min"
    out = x.resample(rule, label="left", closed="left").agg(
        time_server=("time_server", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        source_rows=("close", "count"),
    )
    out = out[out["source_rows"] > 0].reset_index()
    out["bar_close_utc"] = out["time_utc"] + pd.Timedelta(minutes=minutes)
    if out["time_utc"].max() >= HOLDOUT:
        raise ContractError(f"M{minutes} resample crossed holdout")
    return out


def mt5_atr(frame: pd.DataFrame, period: int = 14) -> np.ndarray:
    """Use AlphaFactory's parity-proven MT5 iATR implementation."""
    return _alpha_atr_mt5(frame, period).to_numpy(float)


def signal_identity(row: dict[str, Any]) -> tuple[str, int, str, str]:
    """Identity of the underlying FVG, independent of later decision cutoffs."""
    return (
        str(row["formed_time_utc"]),
        int(row["direction"]),
        f"{float(row['bottom']):.10f}",
        f"{float(row['top']):.10f}",
    )


def stable_rank(rows: Iterable[dict[str, Any]], seed: int, salt: str) -> list[dict[str, Any]]:
    def key(row: dict[str, Any]) -> str:
        raw = f"{seed}|{salt}|{row['decision_time_utc']}|{row['direction']}".encode()
        return hashlib.sha256(raw).hexdigest()
    return sorted(rows, key=key)


def packet_file_hashes(packet: Path, exclude: set[str] | None = None) -> list[dict[str, Any]]:
    excluded = exclude or set()
    return [
        {"path": p.relative_to(packet).as_posix(), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        for p in sorted(packet.rglob("*"))
        if p.is_file() and p.relative_to(packet).as_posix() not in excluded
    ]
