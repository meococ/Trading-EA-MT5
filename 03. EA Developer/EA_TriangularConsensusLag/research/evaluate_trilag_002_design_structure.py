#!/usr/bin/env python3
"""Outcome-blind DESIGN structural evaluator for HYP-TRILAG-EURJPY-M1-002.

The evaluator uses only each completed bar and strictly prior completed bars.
It emits event geometry and structural gates, never a future return, trade,
cost, PF, PnL, expectancy or drawdown.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


HYPOTHESIS_ID = "HYP-TRILAG-EURJPY-M1-002"
PARENT_HYPOTHESIS_ID = "HYP-TRILAG-EURJPY-M1-001"
ATTEMPT_ID = "TRILAG002-DESIGN-STRUCTURE-001"
EXPORT_ATTEMPT_ID = "TRILAG002-DESIGN-EXPORT-001"

PLAN_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "HYP-TRILAG-EURJPY-M1-002_DESIGN_STRUCTURE_PLAN.md"
)
PLAN_SHA256 = "33715BD2CB337C3A700BA08421EE1BD3E92434555E92C85B044FB115412F9200"
EVALUATOR_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "evaluate_trilag_002_design_structure.py"
)
EXPORTER_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "export_trilag_002_design_m1.py"
)
TEST_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/tests/"
    "test_trilag_002_design_structure.py"
)
REVIEW_RECEIPT_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/"
    "HYP-TRILAG-EURJPY-M1-002_DESIGN_IMPLEMENTATION_REVIEW_RECEIPT.json"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
DATASET_ROOT_REL = (
    "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
    "HYP-TRILAG-EURJPY-M1-002"
)
PARQUET_NAME = "design_m1_close.parquet"
MANIFEST_NAME = "design_m1_manifest.json"
EXPORT_RECEIPT_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
    "HYP-TRILAG-EURJPY-M1-002/TRILAG002-DESIGN-EXPORT-001/"
    "design_export_receipt.json"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_TriangularConsensusLag/research/evidence/"
    f"HYP-TRILAG-EURJPY-M1-002/{ATTEMPT_ID}"
)
EVENT_LEDGER_NAME = "design_events.jsonl"
TERMINAL_NAME = "design_structure_terminal.json"

SYMBOLS: tuple[str, ...] = ("EURUSD", "USDJPY", "EURJPY")
SCHEMA_COLUMNS: tuple[str, ...] = ("symbol", "time_utc", "close")
DESIGN_START_TEXT = "2016-01-01T00:00:00Z"
DESIGN_END_TEXT = "2020-12-31T23:59:59Z"
DESIGN_YEARS: tuple[int, ...] = (2016, 2017, 2018, 2019, 2020)
ROLLING_WINDOW = 1440
ROLLING_MIN = 1400
Z_MIN = 3.0
LEAD_SHARE_MIN = 0.25
LAG_SHARE_MAX = 0.25
COOLDOWN_SECONDS = 60 * 60
INNER_JOIN_RATIO_MIN = 0.990
CADENCE_MIN = 2.0
CADENCE_MAX = 5.0
MIN_DIRECTION_EVENTS = 100
MIN_DIRECTION_SHARE = 0.25
MAX_YEAR_SHARE = 0.30
MEDIAN_GAP_PIPS_MIN = 5.0
P25_GAP_PIPS_MIN = 2.5
CHUNK_SIZE = 1024 * 1024
HEX = frozenset("0123456789ABCDEF")

VERDICT_PASS = "PASS_DESIGN_STRUCTURE_FUTURE_ECONOMICS_PREREG_ONLY"
VERDICT_KILL = "KILL_DESIGN_STRUCTURE_NO_ECONOMICS_AUTHORITY"
VERDICT_INVALID = "ENGINEERING_INVALID_NO_MARKET_VERDICT"

# Independent review must replace this exact sentinel before the one real eval.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    """Fail-closed engineering contract violation; never a market verdict."""


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("non-canonical or non-finite JSON value") from exc


def sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractError("hash input must be bytes")
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _valid_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in HEX for c in value)


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise ContractError("evaluator payload must be bytes")
    lines = payload.splitlines(keepends=True)
    matches = [
        index for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("evaluator must contain exactly one valid sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


normalized_base_sha256 = normalized_evaluator_base_sha256


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d_side(path: Path, *, label: str) -> Path:
    resolved = Path(path).resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D: storage")
    return resolved


def _read(path: Path) -> bytes:
    return Path(path).read_bytes()


def parse_registry(payload: bytes) -> tuple[list[dict[str, object]], list[bytes]]:
    rows: list[dict[str, object]] = []
    lines: list[bytes] = []
    for raw in payload.splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError("registry contains invalid JSONL") from exc
        if type(row) is not dict:
            raise ContractError("registry row must be an object")
        rows.append(row)
        lines.append(raw + b"\n")
    return rows, lines


def validate_registry_authority(payload: bytes, expected_row_sha: str) -> dict[str, object]:
    rows, lines = parse_registry(payload)
    candidates = [
        (row, line) for row, line in zip(rows, lines)
        if row.get("hypothesis_id") == HYPOTHESIS_ID
    ]
    if not candidates:
        raise ContractError("registry hypothesis missing")
    row, line = candidates[-1]
    if sha256_bytes(line) != expected_row_sha:
        raise ContractError("armed row SHA is not latest hypothesis row")
    validation = row.get("validation")
    metrics = row.get("metrics")
    if type(validation) is not dict or type(metrics) is not dict:
        raise ContractError("registry authority missing validation/metrics")
    if row.get("state") != "probe":
        raise ContractError("structural evaluation requires probe state")
    if validation.get("design_structure_evaluation_authorized") is not True:
        raise ContractError("structural evaluation is not authorized")
    if validation.get("design_export_run_authorized") is not False:
        raise ContractError("evaluation row must close export authority")
    if validation.get("one_use") is not True:
        raise ContractError("one-use authority missing")
    if int(metrics.get("design_structure_attempts_consumed", -1)) != 0:
        raise ContractError("structural attempt already consumed")
    if ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("structural attempt id already present")
    for key in (
        "reviewed_exporter_base_sha256",
        "reviewed_evaluator_base_sha256",
        "reviewed_test_sha256",
        "independent_review_receipt_sha256",
        "dataset_manifest_sha256",
        "dataset_parquet_sha256",
        "design_export_receipt_sha256",
    ):
        if not _valid_sha(validation.get(key)):
            raise ContractError(f"invalid authority binding:{key}")
    return row


def validate_manifest_and_load(
    *,
    dataset_root: Path,
    expected_manifest_sha256: str | None = None,
    expected_parquet_sha256: str | None = None,
) -> tuple[Any, dict[str, object], dict[str, str]]:
    root = require_d_side(dataset_root, label="dataset root")
    manifest_path = root / MANIFEST_NAME
    parquet_path = root / PARQUET_NAME
    if not manifest_path.is_file() or not parquet_path.is_file():
        raise ContractError("DESIGN dataset files missing")
    manifest_payload = _read(manifest_path)
    parquet_payload = _read(parquet_path)
    manifest_sha = sha256_bytes(manifest_payload)
    parquet_sha = sha256_bytes(parquet_payload)
    if expected_manifest_sha256 is not None and manifest_sha != expected_manifest_sha256:
        raise ContractError("manifest SHA mismatch")
    if expected_parquet_sha256 is not None and parquet_sha != expected_parquet_sha256:
        raise ContractError("parquet SHA mismatch")
    try:
        manifest = json.loads(manifest_payload)
    except json.JSONDecodeError as exc:
        raise ContractError("manifest JSON invalid") from exc
    if manifest_payload != canonical_json(manifest) + b"\n":
        raise ContractError("manifest is not canonical JSON")
    required = {
        "schema_version": "trilag_002_design_m1_manifest.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": EXPORT_ATTEMPT_ID,
        "split": "DESIGN",
        "requested_start_utc": DESIGN_START_TEXT,
        "requested_end_utc": DESIGN_END_TEXT,
        "plan_sha256": PLAN_SHA256,
        "parquet_sha256": parquet_sha,
    }
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise ContractError(f"manifest binding mismatch:{key}")
    if tuple(manifest.get("symbols", [])) != SYMBOLS:
        raise ContractError("manifest symbol set/order mismatch")
    if tuple(manifest.get("schema", [])) != SCHEMA_COLUMNS:
        raise ContractError("manifest schema mismatch")
    if tuple(manifest.get("design_years", [])) != DESIGN_YEARS:
        raise ContractError("manifest DESIGN years mismatch")
    counters = manifest.get("outcome_blind_counters")
    if type(counters) is not dict:
        raise ContractError("manifest outcome-blind counters missing")
    numeric_zero = (
        "bars_requested_2021plus",
        "bars_exported_2021plus",
        "post_decision_bars_read",
        "future_path_labels",
        "trades_simulated",
        "costs_computed",
        "pf_computed",
        "pnl_computed",
        "orders_submitted",
        "network_calls",
        "paid_requests_made",
    )
    if any(int(counters.get(key, -1)) != 0 for key in numeric_zero):
        raise ContractError("manifest contains forbidden nonzero counter")
    if counters.get("economics_executed") is not False:
        raise ContractError("manifest economics flag must be false")
    if counters.get("validation_opened") is not False:
        raise ContractError("manifest validation flag must be false")
    if counters.get("research_holdout_opened") is not False:
        raise ContractError("manifest holdout flag must be false")
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover - host dependency
        raise ContractError(f"pandas import failed:{exc}") from exc
    frame = pd.read_parquet(io.BytesIO(parquet_payload))
    if tuple(frame.columns) != SCHEMA_COLUMNS:
        raise ContractError("parquet schema mismatch")
    if int(manifest.get("row_count", -1)) != int(len(frame)):
        raise ContractError("manifest row count mismatch")
    return frame, manifest, {
        "manifest_sha256": manifest_sha,
        "parquet_sha256": parquet_sha,
    }


def validate_panel(frame: Any) -> dict[str, object]:
    try:
        import pandas as pd
    except Exception as exc:  # pragma: no cover
        raise ContractError(f"pandas import failed:{exc}") from exc
    if tuple(frame.columns) != SCHEMA_COLUMNS:
        raise ContractError("panel schema mismatch")
    if frame.empty:
        raise ContractError("empty DESIGN panel")
    if set(frame["symbol"].astype(str).unique()) != set(SYMBOLS):
        raise ContractError("panel symbol set mismatch")
    times = pd.to_datetime(frame["time_utc"], format="%Y-%m-%dT%H:%M:%SZ", utc=True)
    if bool(times.isna().any()):
        raise ContractError("invalid UTC timestamp")
    if times.min().year < 2016 or times.max().year > 2020:
        raise ContractError("panel escaped DESIGN years")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if bool(closes.isna().any()) or bool((closes <= 0.0).any()):
        raise ContractError("panel close must be finite and positive")
    checked = frame.copy()
    checked["time_utc"] = times
    checked["close"] = closes.astype("float64")
    if bool(checked.duplicated(["symbol", "time_utc"]).any()):
        raise ContractError("duplicate symbol/timestamp")
    counts: dict[str, int] = {}
    for symbol in SYMBOLS:
        subset = checked[checked["symbol"].astype(str) == symbol]
        if not bool(subset["time_utc"].is_monotonic_increasing):
            raise ContractError(f"timestamp order failure:{symbol}")
        counts[symbol] = int(len(subset))
    pivot = checked.pivot(index="time_utc", columns="symbol", values="close")
    common = pivot.dropna(subset=list(SYMBOLS)).sort_index()
    if common.empty:
        raise ContractError("no exact common timestamp")
    ratios = {symbol: float(len(common) / counts[symbol]) for symbol in SYMBOLS}
    elapsed_seconds = float((common.index[-1] - common.index[0]).total_seconds())
    if elapsed_seconds <= 0.0:
        raise ContractError("non-positive elapsed DESIGN span")
    return {
        "checked": checked,
        "common": common,
        "per_symbol_rows": counts,
        "common_rows": int(len(common)),
        "inner_join_ratio": ratios,
        "first_common_time_utc": common.index[0].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_common_time_utc": common.index[-1].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "elapsed_weeks": elapsed_seconds / (7.0 * 24.0 * 60.0 * 60.0),
    }


def build_raw_events(common: Any) -> list[dict[str, object]]:
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover - host dependency
        raise ContractError(f"numpy import failed:{exc}") from exc
    log_close = np.log(common.loc[:, list(SYMBOLS)].astype("float64"))
    returns = log_close.diff()
    r_eu = returns["EURUSD"]
    r_uj = returns["USDJPY"]
    r_ej = returns["EURJPY"]
    implied = r_eu + r_uj
    sigma = implied.rolling(window=ROLLING_WINDOW, min_periods=ROLLING_MIN).std(ddof=1).shift(1)
    abs_implied = implied.abs()
    gap = implied - r_ej
    z = abs_implied / sigma
    contribution_eu = r_eu.abs() / abs_implied
    contribution_uj = r_uj.abs() / abs_implied
    eligible = (
        (sigma > 0.0)
        & np.isfinite(sigma)
        & (z >= Z_MIN)
        & (r_eu != 0.0)
        & (r_uj != 0.0)
        & (np.sign(r_eu) == np.sign(r_uj))
        & (contribution_eu >= LEAD_SHARE_MIN)
        & (contribution_uj >= LEAD_SHARE_MIN)
        & (r_ej.abs() <= LAG_SHARE_MAX * abs_implied)
        & (np.sign(gap) == np.sign(implied))
    )
    events: list[dict[str, object]] = []
    for stamp in common.index[eligible.fillna(False)]:
        gap_value = float(gap.loc[stamp])
        close_ej = float(common.loc[stamp, "EURJPY"])
        direction = "LONG" if float(implied.loc[stamp]) > 0.0 else "SHORT"
        events.append(
            {
                "bar_time_utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "decision_time_utc": (stamp + __import__("pandas").Timedelta(seconds=60)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                ),
                "direction": direction,
                "r_eu": float(r_eu.loc[stamp]),
                "r_uj": float(r_uj.loc[stamp]),
                "r_ej": float(r_ej.loc[stamp]),
                "u": float(implied.loc[stamp]),
                "sigma_u": float(sigma.loc[stamp]),
                "z": float(z.loc[stamp]),
                "gap": gap_value,
                "gap_pips": abs(math.expm1(gap_value)) * close_ej / 0.01,
            }
        )
    return events


def decluster_events(
    raw_events: Sequence[Mapping[str, object]],
    *,
    cooldown_seconds: int = COOLDOWN_SECONDS,
) -> list[dict[str, object]]:
    if cooldown_seconds != COOLDOWN_SECONDS:
        raise ContractError("cooldown drift")
    accepted: list[dict[str, object]] = []
    last: datetime | None = None
    ordered = sorted(raw_events, key=lambda row: str(row["decision_time_utc"]))
    for row in ordered:
        decision = datetime.strptime(
            str(row["decision_time_utc"]), "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        if last is None or (decision - last).total_seconds() >= cooldown_seconds:
            record = dict(row)
            record["event_id"] = f"TRILAG002-E{len(accepted) + 1:06d}"
            accepted.append(record)
            last = decision
    return accepted


def percentile_linear(values: Sequence[float], q: float) -> float:
    if not values:
        raise ContractError("percentile requires observations")
    ordered = sorted(float(value) for value in values)
    if not 0.0 <= q <= 1.0:
        raise ContractError("invalid percentile")
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_structure(
    *,
    panel: Mapping[str, object],
    raw_events: Sequence[Mapping[str, object]],
    accepted: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    count = len(accepted)
    elapsed_weeks = float(panel["elapsed_weeks"])
    directions = {
        side: sum(1 for event in accepted if event["direction"] == side)
        for side in ("LONG", "SHORT")
    }
    direction_share = {
        side: (directions[side] / count if count else 0.0)
        for side in directions
    }
    by_year: dict[str, int] = {str(year): 0 for year in DESIGN_YEARS}
    for event in accepted:
        year = str(event["bar_time_utc"])[:4]
        if year not in by_year:
            raise ContractError(f"accepted event outside DESIGN:{year}")
        by_year[year] += 1
    year_share = {
        year: (value / count if count else 0.0) for year, value in by_year.items()
    }
    gaps = [float(event["gap_pips"]) for event in accepted]
    return {
        "per_symbol_rows": dict(panel["per_symbol_rows"]),
        "common_rows": int(panel["common_rows"]),
        "inner_join_ratio": dict(panel["inner_join_ratio"]),
        "first_common_time_utc": panel["first_common_time_utc"],
        "last_common_time_utc": panel["last_common_time_utc"],
        "elapsed_weeks": elapsed_weeks,
        "raw_event_count": len(raw_events),
        "accepted_event_count": count,
        "events_per_elapsed_week": count / elapsed_weeks,
        "direction_count": directions,
        "direction_share": direction_share,
        "year_count": by_year,
        "year_share": year_share,
        "max_year_share": max(year_share.values()) if year_share else 0.0,
        "median_gap_pips": percentile_linear(gaps, 0.50) if gaps else None,
        "p25_gap_pips": percentile_linear(gaps, 0.25) if gaps else None,
    }


def build_gates(summary: Mapping[str, object]) -> list[dict[str, object]]:
    ratios = summary["inner_join_ratio"]
    directions = summary["direction_count"]
    shares = summary["direction_share"]
    cadence = float(summary["events_per_elapsed_week"])
    accepted = int(summary["accepted_event_count"])
    gates = [
        {
            "gate": "exact_inner_join_ratio",
            "pass": all(float(ratios[symbol]) >= INNER_JOIN_RATIO_MIN for symbol in SYMBOLS),
            "observed": dict(ratios),
            "threshold": INNER_JOIN_RATIO_MIN,
        },
        {
            "gate": "elapsed_week_cadence",
            "pass": CADENCE_MIN <= cadence <= CADENCE_MAX,
            "observed": cadence,
            "threshold": [CADENCE_MIN, CADENCE_MAX],
        },
        {
            "gate": "direction_balance",
            "pass": accepted > 0 and all(
                int(directions[side]) >= MIN_DIRECTION_EVENTS
                and float(shares[side]) >= MIN_DIRECTION_SHARE
                for side in ("LONG", "SHORT")
            ),
            "observed": {"count": dict(directions), "share": dict(shares)},
            "threshold": {"min_count_each": MIN_DIRECTION_EVENTS, "min_share_each": MIN_DIRECTION_SHARE},
        },
        {
            "gate": "calendar_year_concentration",
            "pass": accepted > 0 and float(summary["max_year_share"]) <= MAX_YEAR_SHARE,
            "observed": summary["max_year_share"],
            "threshold": MAX_YEAR_SHARE,
        },
        {
            "gate": "decision_time_gap_geometry",
            "pass": accepted > 0
            and summary["median_gap_pips"] is not None
            and summary["p25_gap_pips"] is not None
            and float(summary["median_gap_pips"]) >= MEDIAN_GAP_PIPS_MIN
            and float(summary["p25_gap_pips"]) >= P25_GAP_PIPS_MIN,
            "observed": {
                "median_gap_pips": summary["median_gap_pips"],
                "p25_gap_pips": summary["p25_gap_pips"],
            },
            "threshold": {
                "median_gap_pips_min": MEDIAN_GAP_PIPS_MIN,
                "p25_gap_pips_min": P25_GAP_PIPS_MIN,
            },
        },
        {
            "gate": "both_residual_signs",
            "pass": int(directions["LONG"]) > 0 and int(directions["SHORT"]) > 0,
            "observed": dict(directions),
            "threshold": "BOTH_NONZERO",
        },
        {
            "gate": "post_decision_and_economics_hard_zero",
            "pass": True,
            "observed": {
                "post_decision_bars_read": 0,
                "future_path_labels": 0,
                "trades_simulated": 0,
                "costs_computed": 0,
                "pf_computed": 0,
                "pnl_computed": 0,
                "economics_executed": False,
            },
            "threshold": "ZERO_FALSE",
        },
        {
            "gate": "sealed_surfaces_hard_zero",
            "pass": True,
            "observed": {
                "validation_opened": False,
                "research_holdout_opened": False,
                "mql5_files_created": 0,
                "model0_runs": 0,
                "network_calls": 0,
                "paid_requests_made": 0,
            },
            "threshold": "ZERO_FALSE",
        },
    ]
    return gates


def canonical_event_ledger(events: Sequence[Mapping[str, object]]) -> bytes:
    return b"".join(canonical_json(dict(event)) + b"\n" for event in events)


def evaluate_frame(frame: Any) -> dict[str, object]:
    panel = validate_panel(frame)
    raw = build_raw_events(panel["common"])
    accepted = decluster_events(raw)
    summary = summarize_structure(panel=panel, raw_events=raw, accepted=accepted)
    gates = build_gates(summary)
    verdict = VERDICT_PASS if all(bool(gate["pass"]) for gate in gates) else VERDICT_KILL
    ledger = canonical_event_ledger(accepted)
    return {
        "summary": summary,
        "gates": gates,
        "verdict": verdict,
        "events": accepted,
        "event_ledger_sha256": sha256_bytes(ledger),
        "event_ledger_payload": ledger,
    }


def atomic_write(path: Path, payload: bytes) -> None:
    if path.exists():
        raise ContractError(f"create-new target already exists:{path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp-{os.getpid()}-{os.urandom(6).hex()}")
    try:
        with temp.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def reserve_dir(path: Path) -> Path:
    target = require_d_side(path, label="evidence root")
    try:
        target.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise ContractError("exclusive evidence root already exists") from exc
    return target


def normalized_exporter_sha(payload: bytes) -> str:
    pattern = re.compile(
        rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$',
        flags=re.MULTILINE,
    )
    matches = list(pattern.finditer(payload))
    if len(matches) != 1:
        raise ContractError("exporter must contain exactly one valid sentinel")
    return sha256_bytes(pattern.sub(b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None", payload, count=1))


def run_production(*, workspace_root: Path, production: bool) -> dict[str, object]:
    if production is not True:
        raise ContractError("explicit --production is required")
    if REVIEWED_REGISTRY_ROW_SHA256 is None or not _valid_sha(
        REVIEWED_REGISTRY_ROW_SHA256
    ):
        raise ContractError("reviewed registry-row sentinel is absent or invalid")
    workspace = require_d_side(Path(workspace_root), label="workspace")
    canonical = require_d_side(workspace_from_source(), label="source workspace")
    if os.path.normcase(str(workspace)) != os.path.normcase(str(canonical)):
        raise ContractError("workspace is not the source-bound canonical root")
    row = validate_registry_authority(
        _read(workspace / REGISTRY_REL), REVIEWED_REGISTRY_ROW_SHA256
    )
    validation = row["validation"]
    bindings = {
        "reviewed_exporter_base_sha256": normalized_exporter_sha(
            _read(workspace / EXPORTER_REL)
        ),
        "reviewed_evaluator_base_sha256": normalized_evaluator_base_sha256(
            _read(workspace / EVALUATOR_REL)
        ),
        "reviewed_test_sha256": sha256_file(workspace / TEST_REL),
        "independent_review_receipt_sha256": sha256_file(
            workspace / REVIEW_RECEIPT_REL
        ),
    }
    for key, actual in bindings.items():
        if validation.get(key) != actual:
            raise ContractError(f"review binding mismatch:{key}")
    if sha256_file(workspace / PLAN_REL) != PLAN_SHA256:
        raise ContractError("frozen plan SHA mismatch")
    if sha256_file(workspace / EXPORT_RECEIPT_REL) != validation.get(
        "design_export_receipt_sha256"
    ):
        raise ContractError("design export receipt SHA mismatch")

    evidence_root = reserve_dir(workspace / EVIDENCE_ROOT_REL)
    atomic_write(
        evidence_root / "attempt_started.json",
        canonical_json(
            {
                "schema_version": "trilag_002_design_structure_attempt.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
                "status": "STARTED_AUTHORITY_CONSUMED",
                **bindings,
            }
        ) + b"\n",
    )
    frame, manifest, hashes = validate_manifest_and_load(
        dataset_root=workspace / DATASET_ROOT_REL,
        expected_manifest_sha256=str(validation["dataset_manifest_sha256"]),
        expected_parquet_sha256=str(validation["dataset_parquet_sha256"]),
    )
    result = evaluate_frame(frame)
    ledger_payload = result.pop("event_ledger_payload")
    ledger_path = evidence_root / EVENT_LEDGER_NAME
    atomic_write(ledger_path, ledger_payload)
    ledger_sha = sha256_file(ledger_path)
    if ledger_sha != result["event_ledger_sha256"]:
        raise ContractError("event ledger SHA replay mismatch")
    terminal = {
        "schema_version": "trilag_002_design_structure_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "export_attempt_id": EXPORT_ATTEMPT_ID,
        "reviewed_registry_row_sha256": REVIEWED_REGISTRY_ROW_SHA256,
        "plan_sha256": PLAN_SHA256,
        **bindings,
        "dataset_manifest_sha256": hashes["manifest_sha256"],
        "dataset_parquet_sha256": hashes["parquet_sha256"],
        "dataset_row_count": int(manifest["row_count"]),
        "event_ledger_path": f"{EVIDENCE_ROOT_REL}/{EVENT_LEDGER_NAME}",
        "event_ledger_sha256": ledger_sha,
        "verdict": result["verdict"],
        "summary": result["summary"],
        "gates": result["gates"],
        "counters": {
            "design_structure_attempts_consumed": 1,
            "bars_read": int(manifest["row_count"]),
            "timestamps_read": int(manifest["row_count"]),
            "prices_read": int(manifest["row_count"]),
            "returns_computed": int(result["summary"]["common_rows"] * 3),
            "residuals_computed": int(result["summary"]["common_rows"]),
            "raw_events_generated": int(result["summary"]["raw_event_count"]),
            "accepted_events_generated": int(result["summary"]["accepted_event_count"]),
            "post_decision_bars_read": 0,
            "future_path_labels": 0,
            "trades_simulated": 0,
            "costs_computed": 0,
            "outcomes_opened": 0,
            "pf_computed": 0,
            "pnl_computed": 0,
            "economics_executed": False,
            "validation_opened": False,
            "research_holdout_opened": False,
            "mql5_files_created": 0,
            "model0_runs": 0,
            "mt5_launches": 0,
            "network_calls": 0,
            "paid_requests_made": 0,
        },
    }
    atomic_write(evidence_root / TERMINAL_NAME, canonical_json(terminal) + b"\n")
    return terminal


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, default=Path.cwd())
    parser.add_argument("--production", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(
        canonical_json(
            run_production(
                workspace_root=args.workspace_root,
                production=bool(args.production),
            )
        ).decode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
