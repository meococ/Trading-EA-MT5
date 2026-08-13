#!/usr/bin/env python3
"""Outcome-blind EHPR Hilbert-phase source and event-population analyzer."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq


HYPOTHESIS_ID = "HYP-EHPR-EURUSD-M15-001"
ATTEMPT_ID = "EHPR001-SOURCE-ATTEMPT-001"
PREREG_SHA256 = "948EEA1A653A956E37336C280AC4B4BD980F87B7E009575C9924F583006E7304"
MANIFEST_SHA256 = "D2F48E9CB3809AB447B89DC22E658D4988AD71AE26F864B96EA1D7D9FF83AD23"
DATA_SHA256 = "6B18C8BE6F772893428199A44708208EEB844F95BC02FD1317528E163EC72ED8"
SOURCE_START = pd.Timestamp("2015-01-01T00:00:00Z")
DESIGN_START = pd.Timestamp("2016-01-04T00:00:00Z")
DESIGN_END = pd.Timestamp("2021-01-01T00:00:00Z")
WARMUP_BARS = 40
MAX_PERIOD = 50.0
VALID_PERIOD_MAX = 42.5
AMPLITUDE_EPSILON = 1.0e-12
MIN_DERIVED_COVERAGE = 0.99
MIN_USABLE_COVERAGE = 0.80
MIN_NEXT_COVERAGE = 0.97
MIN_EVENTS = 1000
MIN_YEAR_EVENTS = 100
MIN_DIRECTION_SHARE = 0.45
MAX_YEAR_SHARE = 0.25
REQUIRED_COLUMNS = ("symbol", "timeframe", "source_epoch", "time_utc", "utc_ambiguous", "open", "high", "low", "close")
EVENT_KEYS = {"hypothesis_id", "source_bar_time_utc", "decision_time_utc", "direction", "dominant_period", "phase_radians", "phase_amplitude", "segment_bars"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def json_bytes(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return b"".join(json_bytes(row) for row in rows)


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def utc_text(value: pd.Timestamp) -> str:
    return value.isoformat().replace("+00:00", "Z")


def is_scheduled_weekend_gap(previous: pd.Timestamp, current: pd.Timestamp) -> bool:
    delta = current - previous
    return pd.Timedelta(hours=24) <= delta <= pd.Timedelta(days=4) and previous.dayofweek == 4 and current.dayofweek in (6, 0)


def derived_m15_from_m5(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"missing source columns: {missing}")
    data = frame.loc[:, REQUIRED_COLUMNS].copy()
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    if data.empty or not data["symbol"].eq("EURUSD").all() or not data["timeframe"].eq("M5").all():
        raise ValueError("source must contain only EURUSD M5")
    if data["utc_ambiguous"].fillna(True).astype(bool).any():
        raise ValueError("UTC-ambiguous EURUSD rows are forbidden")
    if not data["time_utc"].is_monotonic_increasing or data["time_utc"].duplicated().any():
        raise ValueError("M5 time_utc must be unique and increasing")
    values = data[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="raise").to_numpy(dtype=float)
    valid = np.isfinite(values).all(axis=1) & (values[:, 1] >= np.maximum(values[:, 0], values[:, 3])) & (values[:, 2] <= np.minimum(values[:, 0], values[:, 3])) & (values[:, 1] >= values[:, 2])
    if not valid.all():
        raise ValueError("M5 geometry is invalid")
    epoch = (data["time_utc"].astype("int64") // 1_000_000_000).to_numpy(dtype=np.int64)
    bucket = epoch - np.mod(epoch, 900)
    data["bucket_epoch"] = bucket
    rows: list[dict[str, Any]] = []
    complete = 0
    for bucket_epoch, group in data.groupby("bucket_epoch", sort=True):
        offsets = (group["time_utc"].astype("int64") // 1_000_000_000 - int(bucket_epoch)).to_numpy(dtype=np.int64)
        if len(group) != 3 or not np.array_equal(offsets, np.array([0, 300, 600], dtype=np.int64)):
            continue
        complete += 1
        rows.append({
            "time_utc": pd.Timestamp(int(bucket_epoch), unit="s", tz="UTC"),
            "open": float(group.iloc[0]["open"]),
            "high": float(group["high"].max()),
            "low": float(group["low"].min()),
            "close": float(group.iloc[-1]["close"]),
        })
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("no complete derived M15 bars")
    unique_buckets = int(data["bucket_epoch"].nunique())
    diagnostics = {"m5_rows": int(len(data)), "unique_m15_buckets": unique_buckets, "complete_m15_bars": complete, "alignable_m15_slots": unique_buckets}
    return result, diagnostics


@dataclass
class HilbertState:
    hl2: list[float] = field(default_factory=list)
    smooth: list[float] = field(default_factory=list)
    detrender: list[float] = field(default_factory=list)
    i1: list[float] = field(default_factory=list)
    q1: list[float] = field(default_factory=list)
    i2: list[float] = field(default_factory=list)
    q2: list[float] = field(default_factory=list)
    re: list[float] = field(default_factory=list)
    im: list[float] = field(default_factory=list)
    period: list[float] = field(default_factory=list)
    dc: list[float] = field(default_factory=list)

    def reset(self) -> None:
        for values in (self.hl2, self.smooth, self.detrender, self.i1, self.q1, self.i2, self.q2, self.re, self.im, self.period, self.dc):
            values.clear()

    @staticmethod
    def at(values: list[float], index: int) -> float:
        return values[index] if 0 <= index < len(values) else 0.0

    def update(self, price: float) -> dict[str, Any]:
        if not math.isfinite(price):
            raise ValueError("nonfinite HL2")
        index = len(self.hl2)
        self.hl2.append(price)
        for values in (self.smooth, self.detrender, self.i1, self.q1, self.i2, self.q2, self.re, self.im, self.period, self.dc):
            values.append(0.0)
        if index >= 6:
            self.smooth[index] = (4.0 * self.hl2[index] + 3.0 * self.hl2[index - 1] + 2.0 * self.hl2[index - 2] + self.hl2[index - 3]) / 10.0
            previous_period = self.period[index - 1]
            multiplier = 0.075 * previous_period + 0.54
            self.detrender[index] = (0.0962 * self.smooth[index] + 0.5769 * self.at(self.smooth, index - 2) - 0.5769 * self.at(self.smooth, index - 4) - 0.0962 * self.at(self.smooth, index - 6)) * multiplier
            self.q1[index] = (0.0962 * self.detrender[index] + 0.5769 * self.at(self.detrender, index - 2) - 0.5769 * self.at(self.detrender, index - 4) - 0.0962 * self.at(self.detrender, index - 6)) * multiplier
            self.i1[index] = self.at(self.detrender, index - 3)
            ji = (0.0962 * self.i1[index] + 0.5769 * self.at(self.i1, index - 2) - 0.5769 * self.at(self.i1, index - 4) - 0.0962 * self.at(self.i1, index - 6)) * multiplier
            jq = (0.0962 * self.q1[index] + 0.5769 * self.at(self.q1, index - 2) - 0.5769 * self.at(self.q1, index - 4) - 0.0962 * self.at(self.q1, index - 6)) * multiplier
            self.i2[index] = 0.2 * (self.i1[index] - jq) + 0.8 * self.at(self.i2, index - 1)
            self.q2[index] = 0.2 * (self.q1[index] + ji) + 0.8 * self.at(self.q2, index - 1)
            self.re[index] = 0.2 * (self.i2[index] * self.at(self.i2, index - 1) + self.q2[index] * self.at(self.q2, index - 1)) + 0.8 * self.at(self.re, index - 1)
            self.im[index] = 0.2 * (self.i2[index] * self.at(self.q2, index - 1) - self.q2[index] * self.at(self.i2, index - 1)) + 0.8 * self.at(self.im, index - 1)
            raw_period = previous_period
            if self.im[index] != 0.0 and self.re[index] != 0.0:
                angle = math.atan(self.im[index] / self.re[index])
                if angle != 0.0:
                    raw_period = 2.0 * math.pi / angle
            if raw_period > 1.5 * previous_period:
                raw_period = 1.5 * previous_period
            if raw_period < 0.67 * previous_period:
                raw_period = 0.67 * previous_period
            raw_period = min(MAX_PERIOD, max(6.0, raw_period))
            self.period[index] = 0.2 * raw_period + 0.8 * previous_period
            self.dc[index] = 0.33 * self.period[index] + 0.67 * self.at(self.dc, index - 1)
        amplitude = math.hypot(self.i1[index], self.q1[index])
        phase = math.atan2(self.q1[index], self.i1[index]) if amplitude > AMPLITUDE_EPSILON else 0.0
        usable = index >= WARMUP_BARS and amplitude > AMPLITUDE_EPSILON and self.dc[index] > 0.0 and self.dc[index] < VALID_PERIOD_MAX and all(math.isfinite(value) for value in (phase, amplitude, self.dc[index]))
        diff = math.sin(phase) - math.sin(phase + math.pi / 4.0) if usable else 0.0
        return {"usable": usable, "phase": phase, "amplitude": amplitude, "dominant_period": self.dc[index], "diff": diff, "segment_bars": index + 1}


def analyze_m15(frame: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = frame.copy().reset_index(drop=True)
    data["time_utc"] = pd.to_datetime(data["time_utc"], utc=True, errors="raise")
    state = HilbertState()
    features: list[dict[str, Any]] = []
    unexpected_resets = 0
    previous_time: pd.Timestamp | None = None
    for row in data.itertuples(index=False):
        stamp = pd.Timestamp(row.time_utc)
        if previous_time is not None and stamp - previous_time != pd.Timedelta(minutes=15) and not is_scheduled_weekend_gap(previous_time, stamp):
            state.reset()
            unexpected_resets += 1
        feature = state.update((float(row.high) + float(row.low)) * 0.5)
        feature["time_utc"] = stamp
        features.append(feature)
        previous_time = stamp
    design = np.array([(item["time_utc"] >= DESIGN_START and item["time_utc"] < DESIGN_END) for item in features], dtype=bool)
    usable = np.array([bool(item["usable"]) for item in features], dtype=bool)
    diff = np.array([float(item["diff"]) for item in features], dtype=float)
    prior_usable = np.roll(usable, 1); prior_usable[0] = False
    prior_diff = np.roll(diff, 1); prior_diff[0] = 0.0
    raw_long = design & usable & prior_usable & (prior_diff <= 0.0) & (diff > 0.0)
    raw_short = design & usable & prior_usable & (prior_diff >= 0.0) & (diff < 0.0)
    conflicts = raw_long & raw_short
    raw_mask = (raw_long | raw_short) & ~conflicts
    times = data["time_utc"]
    exact_next = ((times.shift(-1) - times) == pd.Timedelta(minutes=15)).to_numpy()
    executable = raw_mask & exact_next
    events: list[dict[str, Any]] = []
    for index in np.flatnonzero(executable):
        feature = features[index]
        source_time = times.iloc[index]
        events.append({
            "hypothesis_id": HYPOTHESIS_ID,
            "source_bar_time_utc": utc_text(source_time),
            "decision_time_utc": utc_text(source_time + pd.Timedelta(minutes=15)),
            "direction": "LONG" if raw_long[index] else "SHORT",
            "dominant_period": float(feature["dominant_period"]),
            "phase_radians": float(feature["phase"]),
            "phase_amplitude": float(feature["amplitude"]),
            "segment_bars": int(feature["segment_bars"]),
        })
    design_rows = int(design.sum())
    usable_design = int((design & usable).sum())
    raw_count = int(raw_mask.sum())
    event_count = len(events)
    long_count = sum(row["direction"] == "LONG" for row in events)
    short_count = event_count - long_count
    elapsed_weeks = (DESIGN_END - DESIGN_START).total_seconds() / 604800.0
    event_years = pd.Series([pd.Timestamp(row["source_bar_time_utc"]).year for row in events], dtype="int64")
    yearly: dict[str, Any] = {}
    for year in range(2016, 2021):
        count = int((event_years == year).sum()) if event_count else 0
        yearly[str(year)] = {"events": count, "share": count / event_count if event_count else 0.0}
    max_year_share = max((item["share"] for item in yearly.values()), default=0.0)
    usable_coverage = usable_design / max(design_rows, 1)
    next_coverage = event_count / max(raw_count, 1)
    gates = {
        "estimator_usable_design_coverage": usable_coverage >= MIN_USABLE_COVERAGE,
        "raw_event_exact_next_coverage": next_coverage >= MIN_NEXT_COVERAGE,
        "minimum_executable_events": event_count >= MIN_EVENTS,
        "minimum_each_year_events": all(item["events"] >= MIN_YEAR_EVENTS for item in yearly.values()),
        "direction_balance": event_count > 0 and long_count / event_count >= MIN_DIRECTION_SHARE and short_count / event_count >= MIN_DIRECTION_SHARE,
        "year_concentration": max_year_share <= MAX_YEAR_SHARE,
        "zero_direction_conflicts": int(conflicts.sum()) == 0,
        "finite_event_features": all(all(math.isfinite(float(row[key])) for key in ("dominant_period", "phase_radians", "phase_amplitude")) for row in events),
    }
    report = {
        "schema_version": "ehpr_source_report.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "epistemic_scope": "OUTCOME_BLIND_HILBERT_PHASE_EVENT_POPULATION_ONLY",
        "source_window": {"from": utc_text(SOURCE_START), "to_exclusive": utc_text(DESIGN_END)},
        "design_window": {"from": utc_text(DESIGN_START), "to_exclusive": utc_text(DESIGN_END)},
        "parameters": {"timeframe": "M15_DERIVED_FROM_EXACT_M5_TRIPLETS", "warmup_bars": WARMUP_BARS, "period_clamp": [6.0, 50.0], "valid_period_max_exclusive": VALID_PERIOD_MAX, "amplitude_epsilon": AMPLITUDE_EPSILON, "phase_lead_radians": math.pi / 4.0},
        "funnel": {"derived_m15_bars": int(len(data)), "design_bars": design_rows, "usable_design_bars": usable_design, "raw_events": raw_count, "executable_events": event_count, "gap_rejected_events": raw_count - event_count, "unexpected_gap_resets": unexpected_resets, "direction_conflicts": int(conflicts.sum()), "long_events": long_count, "short_events": short_count},
        "metrics": {"elapsed_weeks": elapsed_weeks, "event_cadence_per_week": event_count / elapsed_weeks, "estimator_usable_design_coverage": usable_coverage, "raw_event_exact_next_coverage": next_coverage, "long_share": long_count / event_count if event_count else 0.0, "short_share": short_count / event_count if event_count else 0.0, "max_year_event_share": max_year_share},
        "yearly": yearly,
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "prohibitions": {"post_event_ohlc_rows_read": 0, "returns_computed": 0, "trades_simulated": 0, "pnl_computed": 0, "profit_factor_computed": 0, "validation_rows_read": 0, "holdout_rows_read": 0, "mql5_built": False, "mt5_runs": 0},
    }
    report["verdict"] = "PASS_SOURCE_FEASIBILITY_MAY_DRAFT_MQL5_BASELINE" if report["all_gates_pass"] else "PARK_SOURCE_FEASIBILITY_EXACT_HILBERT_PHASE"
    return events, report


def assert_outcome_blind(events: list[dict[str, Any]], report: dict[str, Any]) -> None:
    for row in events:
        if set(row) != EVENT_KEYS:
            raise ValueError(f"event keys differ from allowlist: {sorted(row)}")
    if any(int(value) != 0 for value in report["prohibitions"].values() if not isinstance(value, bool)):
        raise ValueError("outcome-blind counters are nonzero")


def validate_manifest(manifest_path: Path, data_path: Path) -> None:
    if sha256_file(manifest_path) != MANIFEST_SHA256 or sha256_file(data_path) != DATA_SHA256:
        raise ValueError("source hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [item for item in manifest.get("files", []) if str(item.get("path", "")).replace("\\", "/").endswith("EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet")]
    if len(matches) != 1 or matches[0].get("sha256") != DATA_SHA256:
        raise ValueError("manifest does not bind frozen EURUSD M5 file")


def validate_registry_authority(registry_path: Path) -> dict[str, str]:
    matches: list[tuple[bytes, dict[str, Any]]] = []
    for raw in registry_path.read_bytes().splitlines():
        if raw.strip():
            row = json.loads(raw.decode("utf-8"))
            if row.get("hypothesis_id") == HYPOTHESIS_ID:
                matches.append((raw, row))
    if not matches:
        raise ValueError("missing registry authority")
    raw, row = matches[-1]
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    checks = {
        "state": row.get("state") == "probe",
        "verdict": row.get("verdict") == "FROZEN_SOURCE_FEASIBILITY_AUTHORIZED_PRE_RUN",
        "prereg": row.get("prereg_sha256") == PREREG_SHA256,
        "attempt": validation.get("source_feasibility_attempt_id") == ATTEMPT_ID,
        "attempt_limit": validation.get("source_feasibility_attempt_limit") == 1,
        "unconsumed": metrics.get("source_feasibility_attempts_consumed") == 0,
        "source_run": validation.get("source_run_authorized") is True,
        "source_only": validation.get("source_feasibility_only") is True,
        "analyzer": validation.get("reviewed_analyzer_sha256") == sha256_file(Path(__file__).resolve()),
        "no_outcomes": validation.get("outcome_prices_authorized") is False,
        "no_economics": validation.get("economics_authorized") is False,
        "no_mt5": validation.get("mt5_authorized") is False,
        "no_mql5": validation.get("mql5_authorized") is False,
        "no_validation": validation.get("research_validation_access_authorized") is False,
        "no_holdout": validation.get("research_holdout_access_authorized") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"registry authority failed: {failed}")
    return {"registry_sha256": sha256_file(registry_path), "latest_row_sha256": hashlib.sha256(raw).hexdigest().upper()}


def claim_attempt(output_dir: Path, authority: dict[str, str]) -> tuple[str, Path]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("attempt evidence already exists")
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    marker_path = output_dir / "attempt_started.json"
    marker = {"schema_version": "ehpr_attempt_started.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "process_id": os.getpid(), "registry_sha256": authority["registry_sha256"], "latest_hypothesis_row_sha256": authority["latest_row_sha256"], "analyzer_sha256": sha256_file(Path(__file__).resolve()), "status": "ATTEMPT_CLAIMED_SOURCE_NOT_YET_OPENED"}
    with marker_path.open("xb") as handle:
        handle.write(json_bytes(marker)); handle.flush(); os.fsync(handle.fileno())
    return started, marker_path


def execute(root: Path) -> dict[str, Any]:
    base = root / "03. EA Developer/EA_EhlersHilbertPhaseRotation/research"
    prereg = base / "HYP-EHPR-EURUSD-M15-001_FROZEN_PREREG.md"
    manifest = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/manifest.json"
    data_path = root / "02. AlphaFactory/data/fivepercent/FiveAssetFoundation/DATA-FIVEPERCENT-5ASSET-MULTITF-004/EURUSD/EURUSD_M5_ALL_AVAILABLE_20260801.parquet"
    registry = root / "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
    output_dir = base / "evidence/HYP-EHPR-EURUSD-M15-001/EHPR001-SOURCE-ATTEMPT-001"
    if sha256_file(prereg) != PREREG_SHA256:
        raise ValueError("preregistration hash mismatch")
    validate_manifest(manifest, data_path)
    authority = validate_registry_authority(registry)
    started, marker_path = claim_attempt(output_dir, authority)
    if not set(REQUIRED_COLUMNS) <= set(pq.ParquetFile(data_path).schema_arrow.names):
        raise ValueError("Parquet schema missing required columns")
    source_start_epoch = int(SOURCE_START.timestamp())
    design_end_epoch = int(DESIGN_END.timestamp())
    raw = pd.read_parquet(data_path, columns=list(REQUIRED_COLUMNS), filters=[("source_epoch", ">=", source_start_epoch), ("source_epoch", "<", design_end_epoch)], engine="pyarrow")
    m15, resample = derived_m15_from_m5(raw)
    derived_coverage = resample["complete_m15_bars"] / max(resample["alignable_m15_slots"], 1)
    events, report = analyze_m15(m15)
    report["resample"] = {**resample, "derived_slot_coverage": derived_coverage}
    report["gates"]["complete_derived_m15_coverage"] = derived_coverage >= MIN_DERIVED_COVERAGE
    report["all_gates_pass"] = all(report["gates"].values())
    report["verdict"] = "PASS_SOURCE_FEASIBILITY_MAY_DRAFT_MQL5_BASELINE" if report["all_gates_pass"] else "PARK_SOURCE_FEASIBILITY_EXACT_HILBERT_PHASE"
    assert_outcome_blind(events, report)
    replay_events, replay_report = analyze_m15(m15)
    replay_report["resample"] = report["resample"]
    replay_report["gates"]["complete_derived_m15_coverage"] = report["gates"]["complete_derived_m15_coverage"]
    replay_report["all_gates_pass"] = all(replay_report["gates"].values())
    replay_report["verdict"] = "PASS_SOURCE_FEASIBILITY_MAY_DRAFT_MQL5_BASELINE" if replay_report["all_gates_pass"] else "PARK_SOURCE_FEASIBILITY_EXACT_HILBERT_PHASE"
    if jsonl_bytes(events) != jsonl_bytes(replay_events) or json_bytes(report) != json_bytes(replay_report):
        raise ValueError("deterministic replay failed")
    report_bytes = json_bytes(report); ledger_bytes = jsonl_bytes(events)
    report_path = output_dir / "ehpr_001_source_report.json"; ledger_path = output_dir / "ehpr_001_event_ledger.jsonl"
    atomic_write(report_path, report_bytes); atomic_write(ledger_path, ledger_bytes)
    receipt = {"schema_version": "ehpr_source_receipt.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "started_at_utc": started, "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "bindings": {"preregistration": {"path": prereg.relative_to(root).as_posix(), "sha256": sha256_file(prereg)}, "manifest": {"path": manifest.relative_to(root).as_posix(), "sha256": sha256_file(manifest)}, "data": {"path": data_path.relative_to(root).as_posix(), "sha256": sha256_file(data_path)}, "analyzer": {"path": Path(__file__).resolve().relative_to(root).as_posix(), "sha256": sha256_file(Path(__file__).resolve())}, "candidate_registry": {"path": registry.relative_to(root).as_posix(), **authority}, "attempt_started": {"path": marker_path.relative_to(root).as_posix(), "sha256": sha256_file(marker_path)}, "report": {"path": report_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(report_bytes).hexdigest().upper()}, "event_ledger": {"path": ledger_path.relative_to(root).as_posix(), "sha256": hashlib.sha256(ledger_bytes).hexdigest().upper()}}, "outcome_blind_counters": report["prohibitions"], "verdict": report["verdict"]}
    receipt_bytes = json_bytes(receipt); receipt_path = output_dir / "source_feasibility_receipt.json"; atomic_write(receipt_path, receipt_bytes)
    terminal = {"schema_version": "ehpr_attempt_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": receipt["completed_at_utc"], "status": "COMPLETE", "verdict": report["verdict"], "source_feasibility_receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest().upper(), "same_id_retry_authorized": False}
    atomic_write(output_dir / "attempt_terminal.json", json_bytes(terminal))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        parser.error("--execute is required")
    root = Path(__file__).resolve().parents[3]
    print(json_bytes(execute(root)).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
