#!/usr/bin/env python3
"""One-shot TRAIN proxy evaluator for HYP-LOJM-USDJPY-M1-001.

The evaluator is fail-closed and can run only when armed to the latest
hash-bound registry authority row. It reads the frozen 2016-2020 USDJPY
close-only parquet and never opens validation or holdout data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-LOJM-USDJPY-M1-001"
ATTEMPT_ID = "LOJM001-TRAIN-ECON-001"
PLAN_REL = (
    "03. EA Developer/EA_LondonOpenJPYMomentum/research/"
    "HYP-LOJM-USDJPY-M1-001_TRAIN_ECONOMIC_PROBE_PLAN.md"
)
PLAN_SHA256 = "83C1D47893170789C936F1539889A46A596BEEDC19B45BED465C5CDB7EB9B66C"
EVALUATOR_REL = (
    "03. EA Developer/EA_LondonOpenJPYMomentum/research/"
    "evaluate_lojm_001_train.py"
)
TEST_REL = (
    "03. EA Developer/EA_LondonOpenJPYMomentum/research/tests/"
    "test_evaluate_lojm_001_train.py"
)
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
PARQUET_REL = (
    "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
    "HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet"
)
MANIFEST_REL = (
    "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
    "HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json"
)
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)

PARQUET_SHA256 = "C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6"
MANIFEST_SHA256 = "4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8"
DESIGN_START = pd.Timestamp("2016-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2020-12-31T23:59:59Z")
LOCAL_TZ = "Europe/London"
PIP_SIZE = 0.01
COSTS = {"x1": 1.50, "x1_5": 2.25, "x2": 3.00}
PERMUTATIONS = 10_000
PERMUTATION_SEED = 20_260_729
HEX = frozenset("0123456789ABCDEF")
CHUNK_SIZE = 1024 * 1024

VERDICT_PASS = "PASS_TRAIN_PROXY_AUTHORIZE_FRESH_MQL5_MODEL0_PACKET_ONLY"
VERDICT_KILL = "KILL_TRAIN_PROXY_HOLDOUT_REMAINS_SEALED"
VERDICT_STRUCTURAL = "KILL_STRUCTURAL_NO_ECONOMICS_SURVIVOR"
VERDICT_INVALID = "ENGINEERING_INVALID_NO_MARKET_VERDICT"

# Independent pre-run QC replaces this exact sentinel with the latest
# authorized registry row SHA. The normalized evaluator hash ignores it.
REVIEWED_REGISTRY_ROW_SHA256: str | None = "AD8DEBD530DDA0E340CA2609D9655FC248434E6D095CD1189100BAE7C360CB1C"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    """A fail-closed engineering or authority violation."""


@dataclass(frozen=True)
class Authority:
    row: dict[str, object]
    row_sha256: str
    evaluator_base_sha256: str
    evaluator_file_sha256: str
    test_sha256: str


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
        raise ContractError("non-canonical or non-finite JSON") from exc


def sha256_bytes(payload: bytes) -> str:
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
    lines = payload.splitlines(keepends=True)
    matches = [
        index
        for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(matches) != 1:
        raise ContractError("evaluator must contain exactly one valid sentinel")
    index = matches[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d_side(path: Path, *, label: str) -> Path:
    resolved = Path(path).resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D: storage")
    return resolved


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def write_json_new(path: Path, value: object) -> None:
    write_new(path, canonical_json(value) + b"\n")


def parse_registry(payload: bytes) -> list[tuple[dict[str, object], bytes]]:
    rows: list[tuple[dict[str, object], bytes]] = []
    for raw in payload.splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError("registry contains invalid JSONL") from exc
        if type(row) is not dict:
            raise ContractError("registry row must be an object")
        rows.append((row, raw + b"\n"))
    return rows


def validate_authority(workspace: Path) -> Authority:
    if not _valid_sha(REVIEWED_REGISTRY_ROW_SHA256):
        raise ContractError("evaluator registry sentinel is not armed")

    plan_path = workspace / PLAN_REL
    evaluator_path = workspace / EVALUATOR_REL
    test_path = workspace / TEST_REL
    registry_path = workspace / REGISTRY_REL
    for label, path in (
        ("plan", plan_path),
        ("evaluator", evaluator_path),
        ("test", test_path),
        ("registry", registry_path),
    ):
        if not path.is_file():
            raise ContractError(f"{label} file is missing")

    if sha256_file(plan_path) != PLAN_SHA256:
        raise ContractError("plan hash drift")
    evaluator_payload = evaluator_path.read_bytes()
    evaluator_base_sha = normalized_evaluator_base_sha256(evaluator_payload)
    evaluator_file_sha = sha256_bytes(evaluator_payload)
    test_sha = sha256_file(test_path)

    candidates = [
        (row, line)
        for row, line in parse_registry(registry_path.read_bytes())
        if row.get("hypothesis_id") == HYPOTHESIS_ID
    ]
    if not candidates:
        raise ContractError("hypothesis is absent from registry")
    row, line = candidates[-1]
    row_sha = sha256_bytes(line)
    if row_sha != REVIEWED_REGISTRY_ROW_SHA256:
        raise ContractError("armed row is not the latest hypothesis row")
    validation = row.get("validation")
    metrics = row.get("metrics")
    if type(validation) is not dict or type(metrics) is not dict:
        raise ContractError("registry authority fields are missing")
    if row.get("state") != "probe":
        raise ContractError("economic probe requires state=probe")
    if row.get("prereg_sha256") != PLAN_SHA256:
        raise ContractError("registry prereg hash mismatch")
    if validation.get("train_economic_evaluation_authorized") is not True:
        raise ContractError("train economic run is not authorized")
    if validation.get("one_use") is not True:
        raise ContractError("one-use authority is missing")
    if int(metrics.get("train_economic_attempts_consumed", -1)) != 0:
        raise ContractError("economic attempt already consumed")
    if ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("attempt id is already registered")
    expected = {
        "reviewed_evaluator_base_sha256": evaluator_base_sha,
        "reviewed_test_sha256": test_sha,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "dataset_parquet_sha256": PARQUET_SHA256,
    }
    for key, value in expected.items():
        if validation.get(key) != value:
            raise ContractError(f"registry binding mismatch: {key}")
    for key in (
        "mql5_authorized",
        "model0_authorized",
        "optimization_authorized",
        "research_validation_access_authorized",
        "research_holdout_access_authorized",
        "paper_trading_authorized",
        "live_trading_authorized",
    ):
        if validation.get(key) is not False:
            raise ContractError(f"forbidden registry authority is not false: {key}")
    return Authority(row, row_sha, evaluator_base_sha, evaluator_file_sha, test_sha)


def validate_manifest(workspace: Path) -> dict[str, object]:
    manifest_path = require_d_side(workspace / MANIFEST_REL, label="manifest")
    parquet_path = require_d_side(workspace / PARQUET_REL, label="parquet")
    if sha256_file(manifest_path) != MANIFEST_SHA256:
        raise ContractError("dataset manifest hash mismatch")
    if sha256_file(parquet_path) != PARQUET_SHA256:
        raise ContractError("dataset parquet hash mismatch")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("dataset manifest is not valid JSON") from exc
    if type(manifest) is not dict:
        raise ContractError("dataset manifest must be an object")
    expected = {
        "parquet_sha256": PARQUET_SHA256,
        "row_count": 5_580_755,
        "schema": ["symbol", "time_utc", "close"],
        "design_years": [2016, 2017, 2018, 2019, 2020],
        "symbols": ["EURUSD", "USDJPY", "EURJPY"],
        "split": "DESIGN",
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ContractError(f"manifest contract mismatch: {key}")
    per_symbol = manifest.get("per_symbol")
    if type(per_symbol) is not dict or type(per_symbol.get("USDJPY")) is not dict:
        raise ContractError("USDJPY manifest entry is missing")
    if int(per_symbol["USDJPY"].get("rows", -1)) != 1_860_286:
        raise ContractError("USDJPY manifest row count mismatch")
    counters = manifest.get("outcome_blind_counters")
    if type(counters) is not dict:
        raise ContractError("source outcome counters are missing")
    if counters.get("validation_opened") is not False:
        raise ContractError("source manifest says validation was opened")
    if counters.get("research_holdout_opened") is not False:
        raise ContractError("source manifest says holdout was opened")
    return manifest


def load_usdjpy(workspace: Path) -> pd.DataFrame:
    parquet_path = require_d_side(workspace / PARQUET_REL, label="parquet")
    try:
        frame = pd.read_parquet(
            parquet_path,
            columns=["symbol", "time_utc", "close"],
            filters=[("symbol", "==", "USDJPY")],
        )
    except Exception as exc:  # pragma: no cover - backend-specific detail
        raise ContractError("failed to read frozen parquet") from exc
    if list(frame.columns) != ["symbol", "time_utc", "close"]:
        raise ContractError("parquet projection schema mismatch")
    if len(frame) != 1_860_286 or set(frame["symbol"].unique()) != {"USDJPY"}:
        raise ContractError("USDJPY parquet population mismatch")
    timestamps = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if timestamps.isna().any() or closes.isna().any():
        raise ContractError("timestamp or close contains null/non-numeric values")
    if not np.isfinite(closes.to_numpy(dtype=float)).all() or (closes <= 0).any():
        raise ContractError("close values must be finite and positive")
    if timestamps.duplicated().any() or not timestamps.is_monotonic_increasing:
        raise ContractError("USDJPY timestamps must be unique and increasing")
    if timestamps.min() < DESIGN_START or timestamps.max() > DESIGN_END:
        raise ContractError("USDJPY rows leave the frozen DESIGN window")
    return pd.DataFrame({"time_utc": timestamps, "close": closes.astype(float)})


def build_trades_from_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Construct one locked trade per complete London-local weekday."""
    required = {"time_utc", "close"}
    if set(frame.columns) != required:
        raise ContractError("frame must contain exactly time_utc and close")
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if times.isna().any() or closes.isna().any():
        raise ContractError("frame contains invalid time or close")
    if times.duplicated().any() or not times.is_monotonic_increasing:
        raise ContractError("frame times must be unique and increasing")
    if not np.isfinite(closes.to_numpy(dtype=float)).all() or (closes <= 0).any():
        raise ContractError("frame closes must be finite and positive")

    local = times.dt.tz_convert(LOCAL_TZ)
    hour = local.dt.hour.to_numpy()
    minute = local.dt.minute.to_numpy()
    weekday = local.dt.weekday.to_numpy()
    slots = np.select(
        [
            (hour == 7) & (minute == 59),
            (hour == 8) & (minute == 29),
            (hour == 16) & (minute == 29),
        ],
        ["pre", "entry", "exit"],
        default="",
    )
    mask = (weekday < 5) & (slots != "")
    selected = pd.DataFrame(
        {
            "local_date": local[mask].dt.date.to_numpy(),
            "slot": slots[mask],
            "close": closes[mask].to_numpy(dtype=float),
        }
    )
    if selected.duplicated(["local_date", "slot"]).any():
        raise ContractError("duplicate local date/slot observation")
    pivot = selected.pivot(index="local_date", columns="slot", values="close")
    for column in ("pre", "entry", "exit"):
        if column not in pivot:
            pivot[column] = np.nan
    pivot = pivot[["pre", "entry", "exit"]].dropna().sort_index()
    formation = np.log(pivot["entry"] / pivot["pre"])
    pivot = pivot.loc[formation != 0.0].copy()
    formation = formation.loc[pivot.index]
    direction = np.where(formation.to_numpy() > 0.0, 1, -1)
    raw_move_pips = (pivot["exit"].to_numpy() - pivot["entry"].to_numpy()) / PIP_SIZE
    gross_pips = direction * raw_move_pips
    trades = pd.DataFrame(
        {
            "local_date": list(pivot.index),
            "year": [d.year for d in pivot.index],
            "direction": direction.astype(int),
            "pre_close": pivot["pre"].to_numpy(dtype=float),
            "entry_close": pivot["entry"].to_numpy(dtype=float),
            "exit_close": pivot["exit"].to_numpy(dtype=float),
            "formation_log_return": formation.to_numpy(dtype=float),
            "raw_move_pips": raw_move_pips.astype(float),
            "gross_pips": gross_pips.astype(float),
        }
    )
    for label, cost in COSTS.items():
        trades[f"primary_net_{label}_pips"] = trades["gross_pips"] - cost
        trades[f"reverse_net_{label}_pips"] = -trades["gross_pips"] - cost
    return trades


def profit_factor(values: Iterable[float]) -> float | None:
    array = np.asarray(list(values), dtype=float)
    wins = float(array[array > 0.0].sum())
    losses = float(-array[array < 0.0].sum())
    if wins <= 0.0 or losses <= 0.0:
        return None
    return wins / losses


def permutation_p_value(
    directions: Sequence[int],
    raw_moves: Sequence[float],
    *,
    permutations: int = PERMUTATIONS,
    seed: int = PERMUTATION_SEED,
) -> float:
    d = np.asarray(directions, dtype=int)
    r = np.asarray(raw_moves, dtype=float)
    if d.size == 0 or d.size != r.size:
        raise ContractError("permutation inputs are empty or misaligned")
    if set(np.unique(d)) - {-1, 1}:
        raise ContractError("permutation directions must be +/-1")
    observed = float(np.mean(d * r))
    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in range(permutations):
        null_mean = float(np.mean(rng.permutation(d) * r))
        if null_mean >= observed:
            exceed += 1
    return (1.0 + exceed) / (permutations + 1.0)


def _finite_float(value: float) -> float:
    if not math.isfinite(float(value)):
        raise ContractError("metric is non-finite")
    return float(value)


def summarize_trades(
    trades: pd.DataFrame,
    *,
    permutations: int = PERMUTATIONS,
    seed: int = PERMUTATION_SEED,
) -> dict[str, object]:
    if trades.empty:
        return {
            "trade_count": 0,
            "structural_gates": {},
            "economic_gates": {},
            "source_gate_pass_count": 0,
            "source_gate_total": 5,
            "economic_gate_pass_count": 0,
            "economic_gate_total": 7,
        }
    first_date = min(trades["local_date"])
    last_date = max(trades["local_date"])
    expected_weekdays = len(pd.date_range(first_date, last_date, freq="B"))
    elapsed_weeks = float((DESIGN_END - DESIGN_START).total_seconds() / 604800.0)
    count = int(len(trades))
    cadence = count / elapsed_weeks
    direction_counts = {
        "LONG": int((trades["direction"] == 1).sum()),
        "SHORT": int((trades["direction"] == -1).sum()),
    }
    direction_shares = {key: value / count for key, value in direction_counts.items()}
    year_counts = {str(int(k)): int(v) for k, v in trades.groupby("year").size().items()}
    max_year_share = max(year_counts.values()) / count
    coverage = count / expected_weekdays

    pf: dict[str, dict[str, float | None]] = {"primary": {}, "reverse": {}}
    expectancy: dict[str, dict[str, float]] = {"primary": {}, "reverse": {}}
    for arm in ("primary", "reverse"):
        for label in COSTS:
            column = f"{arm}_net_{label}_pips"
            pf[arm][label] = profit_factor(trades[column])
            expectancy[arm][label] = _finite_float(float(trades[column].mean()))

    annual_x1 = {
        str(int(year)): _finite_float(float(group["primary_net_x1_pips"].sum()))
        for year, group in trades.groupby("year")
    }
    positive_years = sum(value > 0.0 for value in annual_x1.values())
    p_value = permutation_p_value(
        trades["direction"].to_numpy(),
        trades["raw_move_pips"].to_numpy(),
        permutations=permutations,
        seed=seed,
    )

    structural_gates = {
        "trade_count_ge_1000": count >= 1000,
        "weekday_coverage_ge_0_95": coverage >= 0.95,
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "direction_balance": all(
            direction_counts[key] >= 300 and direction_shares[key] >= 0.25
            for key in ("LONG", "SHORT")
        ),
        "max_year_share_le_0_25": max_year_share <= 0.25,
    }
    primary_pf_x1 = pf["primary"]["x1"]
    primary_pf_x15 = pf["primary"]["x1_5"]
    primary_pf_x2 = pf["primary"]["x2"]
    reverse_pf_x1 = pf["reverse"]["x1"]
    economic_gates = {
        "pf_x1_gt_1_30": primary_pf_x1 is not None and primary_pf_x1 > 1.30,
        "pf_x1_5_ge_1_25": primary_pf_x15 is not None and primary_pf_x15 >= 1.25,
        "pf_x2_ge_1_00": primary_pf_x2 is not None and primary_pf_x2 >= 1.00,
        "expectancy_x1_gt_0": expectancy["primary"]["x1"] > 0.0,
        "positive_years_ge_4_of_5": len(annual_x1) == 5 and positive_years >= 4,
        "permutation_p_le_0_05": p_value <= 0.05,
        "beats_reverse_x1": (
            primary_pf_x1 is not None
            and reverse_pf_x1 is not None
            and primary_pf_x1 > reverse_pf_x1
            and expectancy["primary"]["x1"] > expectancy["reverse"]["x1"]
        ),
    }
    return {
        "trade_count": count,
        "first_local_date": first_date.isoformat(),
        "last_local_date": last_date.isoformat(),
        "expected_weekdays_between_first_last": expected_weekdays,
        "eligible_weekday_coverage": coverage,
        "elapsed_calendar_weeks": elapsed_weeks,
        "trades_per_elapsed_week": cadence,
        "direction_count": direction_counts,
        "direction_share": direction_shares,
        "year_count": year_counts,
        "max_year_share": max_year_share,
        "profit_factor": pf,
        "expectancy_pips": expectancy,
        "annual_primary_x1_net_pips": annual_x1,
        "positive_years": positive_years,
        "permutation_count": permutations,
        "permutation_seed": seed,
        "permutation_one_sided_p_value": p_value,
        "structural_gates": structural_gates,
        "economic_gates": economic_gates,
        "source_gate_pass_count": sum(structural_gates.values()),
        "source_gate_total": len(structural_gates),
        "economic_gate_pass_count": sum(economic_gates.values()),
        "economic_gate_total": len(economic_gates),
    }


def trade_records(trades: pd.DataFrame) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    float_columns = [column for column in trades.columns if column not in {"local_date", "year", "direction"}]
    for index, row in trades.iterrows():
        record: dict[str, object] = {
            "trade_id": f"LOJM001-{row['local_date'].isoformat()}",
            "local_date": row["local_date"].isoformat(),
            "year": int(row["year"]),
            "direction": "LONG" if int(row["direction"]) == 1 else "SHORT",
        }
        for column in float_columns:
            record[column] = round(_finite_float(float(row[column])), 12)
        records.append(record)
    return records


def run(workspace: Path) -> dict[str, object]:
    workspace = require_d_side(workspace, label="workspace")
    authority = validate_authority(workspace)
    evidence_root = require_d_side(workspace / EVIDENCE_ROOT_REL, label="evidence root")
    evidence_root.mkdir(parents=True, exist_ok=True)
    started_path = evidence_root / "attempt_started.json"
    trades_path = evidence_root / "trades.jsonl"
    terminal_path = evidence_root / "train_economic_terminal.json"
    if any(path.exists() for path in (started_path, trades_path, terminal_path)):
        raise ContractError("one-shot evidence path already contains output")

    started = {
        "schema_version": "lojm_001_attempt_started.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "registry_row_sha256": authority.row_sha256,
        "evaluator_base_sha256": authority.evaluator_base_sha256,
        "evaluator_file_sha256": authority.evaluator_file_sha256,
        "test_sha256": authority.test_sha256,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "dataset_parquet_sha256": PARQUET_SHA256,
    }
    write_json_new(started_path, started)

    manifest = validate_manifest(workspace)
    frame = load_usdjpy(workspace)
    trades = build_trades_from_frame(frame)
    summary = summarize_trades(trades)
    structural = summary["structural_gates"]
    economic = summary["economic_gates"]
    if not structural or not all(structural.values()):
        verdict = VERDICT_STRUCTURAL
    elif economic and all(economic.values()):
        verdict = VERDICT_PASS
    else:
        verdict = VERDICT_KILL

    records = trade_records(trades)
    ledger_payload = b"".join(canonical_json(record) + b"\n" for record in records)
    write_new(trades_path, ledger_payload)
    completed = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    terminal = {
        "schema_version": "lojm_001_train_economic_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": completed,
        "verdict": verdict,
        "engineering_valid": True,
        "economic_edge_evaluated": True,
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "registry_row_sha256": authority.row_sha256,
        "evaluator_path": EVALUATOR_REL,
        "evaluator_base_sha256": authority.evaluator_base_sha256,
        "evaluator_file_sha256": authority.evaluator_file_sha256,
        "test_path": TEST_REL,
        "test_sha256": authority.test_sha256,
        "attempt_started_sha256": sha256_file(started_path),
        "dataset_manifest_path": MANIFEST_REL,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "dataset_parquet_path": PARQUET_REL,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "source_manifest_row_count": manifest["row_count"],
        "trades_path": str(Path(EVIDENCE_ROOT_REL) / trades_path.name).replace("\\", "/"),
        "trades_sha256": sha256_bytes(ledger_payload),
        "metrics": summary,
        "forbidden_counters": {
            "mt5_launches": 0,
            "hcc_payloads_decoded": 0,
            "mql5_files_created": 0,
            "model0_runs": 0,
            "model4_runs": 0,
            "optimization_trials": 0,
            "research_validation_opened": False,
            "research_holdout_opened": False,
            "bars_read_2021plus": 0,
            "network_calls": 0,
            "paid_requests_made": 0,
            "orders_submitted": 0,
            "paper_trading": False,
            "live_trading": False,
        },
        "authority_after_verdict": {
            "mql5_model0_packet_may_be_preregistered": verdict == VERDICT_PASS,
            "validation_authorized": False,
            "holdout_authorized": False,
            "optimization_authorized": False,
            "promotion_eligible": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
        },
    }
    write_json_new(terminal_path, terminal)
    return terminal


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args(argv)
    try:
        terminal = run(args.workspace)
    except ContractError as exc:
        print(f"ENGINEERING_INVALID: {exc}")
        return 2
    metrics = terminal["metrics"]
    print(
        f"{terminal['verdict']} trades={metrics['trade_count']} "
        f"cadence={metrics['trades_per_elapsed_week']:.6f} "
        f"pf_x1={metrics['profit_factor']['primary']['x1']} "
        f"gates={metrics['economic_gate_pass_count']}/{metrics['economic_gate_total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
