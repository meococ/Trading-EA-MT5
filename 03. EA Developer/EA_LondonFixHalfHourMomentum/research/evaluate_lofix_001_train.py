#!/usr/bin/env python3
"""One-shot TRAIN proxy evaluator for HYP-LOFIX-USDJPY-M1-001."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-LOFIX-USDJPY-M1-001"
ATTEMPT_ID = "LOFIX001-TRAIN-ECON-001"
PLAN_REL = (
    "03. EA Developer/EA_LondonFixHalfHourMomentum/research/"
    "HYP-LOFIX-USDJPY-M1-001_TRAIN_ECONOMIC_PROBE_PLAN.md"
)
PLAN_SHA256 = "2A4AEC85B10E524C03F72B1B9E11B7F2422DE41D137979478B63D6CC1BBCDC9A"
EVALUATOR_REL = (
    "03. EA Developer/EA_LondonFixHalfHourMomentum/research/"
    "evaluate_lofix_001_train.py"
)
TEST_REL = (
    "03. EA Developer/EA_LondonFixHalfHourMomentum/research/tests/"
    "test_evaluate_lofix_001_train.py"
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
PRIOR_LEDGER_REL = (
    "03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/"
    "HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001/trades.jsonl"
)
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_LondonFixHalfHourMomentum/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)

PARQUET_SHA256 = "C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6"
MANIFEST_SHA256 = "4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8"
PRIOR_LEDGER_SHA256 = "6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
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

# Independent pre-run QC replaces this exact sentinel with the latest
# authorized registry row SHA. The normalized evaluator hash ignores it.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    """Fail-closed engineering or authority violation."""


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
        "prior_trial_ledger_sha256": PRIOR_LEDGER_SHA256,
        "canonical_dsr_sha256": DSR_SHA256,
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
    except Exception as exc:  # pragma: no cover
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
    """Build one closed-bar 15:30-16:00 London trade per complete weekday."""
    if set(frame.columns) != {"time_utc", "close"}:
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
            (hour == 15) & (minute == 29),
            (hour == 15) & (minute == 59),
        ],
        ["pre", "signal", "entry", "exit"],
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
    for column in ("pre", "signal", "entry", "exit"):
        if column not in pivot:
            pivot[column] = np.nan
    pivot = pivot[["pre", "signal", "entry", "exit"]].dropna().sort_index()
    formation = np.log(pivot["signal"] / pivot["pre"])
    pivot = pivot.loc[formation != 0.0].copy()
    formation = formation.loc[pivot.index]
    direction = np.where(formation.to_numpy() > 0.0, 1, -1)
    raw_move_pips = (pivot["exit"].to_numpy() - pivot["entry"].to_numpy()) / PIP_SIZE
    gross_pips = direction * raw_move_pips
    trades = pd.DataFrame(
        {
            "local_date": list(pivot.index),
            "year": [day.year for day in pivot.index],
            "direction": direction.astype(int),
            "pre_close": pivot["pre"].to_numpy(dtype=float),
            "signal_close": pivot["signal"].to_numpy(dtype=float),
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
        if float(np.mean(rng.permutation(d) * r)) >= observed:
            exceed += 1
    return (1.0 + exceed) / (permutations + 1.0)


def load_dsr_module(workspace: Path) -> ModuleType:
    path = require_d_side(workspace / DSR_REL, label="DSR module")
    if sha256_file(path) != DSR_SHA256:
        raise ContractError("canonical DSR module hash mismatch")
    spec = importlib.util.spec_from_file_location("lofix_canonical_dsr", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load canonical DSR module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "dsr", None)):
        raise ContractError("canonical DSR function is missing")
    return module


def load_prior_arms(workspace: Path) -> tuple[np.ndarray, np.ndarray]:
    path = require_d_side(workspace / PRIOR_LEDGER_REL, label="prior trial ledger")
    if sha256_file(path) != PRIOR_LEDGER_SHA256:
        raise ContractError("prior trial ledger hash mismatch")
    primary: list[float] = []
    reverse: list[float] = []
    for raw in path.read_bytes().splitlines():
        try:
            row = json.loads(raw)
            primary.append(float(row["primary_net_x1_pips"]))
            reverse.append(float(row["reverse_net_x1_pips"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ContractError("prior trial ledger row is invalid") from exc
    if len(primary) != 1283 or len(reverse) != 1283:
        raise ContractError("prior trial ledger population mismatch")
    return np.asarray(primary, dtype=float), np.asarray(reverse, dtype=float)


def _arm_moments(values: Sequence[float]) -> dict[str, float | int]:
    series = pd.Series(np.asarray(values, dtype=float))
    if len(series) < 3 or not np.isfinite(series.to_numpy()).all():
        raise ContractError("DSR arm is too short or non-finite")
    std = float(series.std(ddof=1))
    if std <= 0.0:
        raise ContractError("DSR arm has zero sample variance")
    return {
        "n": int(len(series)),
        "sr": float(series.mean()) / std,
        "skew": float(series.skew()),
        "kurtosis_non_excess": float(series.kurt()) + 3.0,
    }


def compute_dsr(
    current_primary: Sequence[float],
    current_reverse: Sequence[float],
    prior_primary: Sequence[float],
    prior_reverse: Sequence[float],
    module: ModuleType,
) -> dict[str, object]:
    arms = {
        "lojm001_primary": _arm_moments(prior_primary),
        "lojm001_reverse": _arm_moments(prior_reverse),
        "lofix001_primary": _arm_moments(current_primary),
        "lofix001_reverse": _arm_moments(current_reverse),
    }
    sharpe_values = [float(item["sr"]) for item in arms.values()]
    variance = float(np.var(sharpe_values, ddof=1))
    primary = arms["lofix001_primary"]
    value = float(
        module.dsr(
            float(primary["sr"]),
            int(primary["n"]),
            float(primary["skew"]),
            float(primary["kurtosis_non_excess"]),
            variance,
            len(arms),
        )
    )
    if not math.isfinite(value):
        raise ContractError("DSR result is non-finite")
    return {
        "n_trials": len(arms),
        "variance_sr_trials": variance,
        "expected_max_sr": float(module.expected_max_sharpe(variance, len(arms))),
        "primary_dsr": value,
        "arms": arms,
    }


def summarize_trades(
    trades: pd.DataFrame,
    *,
    prior_primary: Sequence[float],
    prior_reverse: Sequence[float],
    dsr_module: ModuleType,
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
            "economic_gate_total": 8,
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
    year_counts = {str(int(key)): int(value) for key, value in trades.groupby("year").size().items()}
    max_year_share = max(year_counts.values()) / count
    coverage = count / expected_weekdays

    pf: dict[str, dict[str, float | None]] = {"primary": {}, "reverse": {}}
    expectancy: dict[str, dict[str, float]] = {"primary": {}, "reverse": {}}
    for arm in ("primary", "reverse"):
        for label in COSTS:
            column = f"{arm}_net_{label}_pips"
            pf[arm][label] = profit_factor(trades[column])
            expectancy[arm][label] = float(trades[column].mean())

    annual_x1 = {
        str(int(year)): float(group["primary_net_x1_pips"].sum())
        for year, group in trades.groupby("year")
    }
    positive_years = sum(value > 0.0 for value in annual_x1.values())
    p_value = permutation_p_value(
        trades["direction"].to_numpy(),
        trades["raw_move_pips"].to_numpy(),
        permutations=permutations,
        seed=seed,
    )
    dsr_result = compute_dsr(
        trades["primary_net_x1_pips"].to_numpy(),
        trades["reverse_net_x1_pips"].to_numpy(),
        prior_primary,
        prior_reverse,
        dsr_module,
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
    reverse_pf_x1 = pf["reverse"]["x1"]
    economic_gates = {
        "pf_x1_gt_1_30": primary_pf_x1 is not None and primary_pf_x1 > 1.30,
        "pf_x1_5_ge_1_25": pf["primary"]["x1_5"] is not None and pf["primary"]["x1_5"] >= 1.25,
        "pf_x2_ge_1_00": pf["primary"]["x2"] is not None and pf["primary"]["x2"] >= 1.00,
        "expectancy_x1_gt_0": expectancy["primary"]["x1"] > 0.0,
        "positive_years_ge_4_of_5": len(annual_x1) == 5 and positive_years >= 4,
        "permutation_p_le_0_05": p_value <= 0.05,
        "dsr_ge_0_95": float(dsr_result["primary_dsr"]) >= 0.95,
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
        "deflated_sharpe": dsr_result,
        "structural_gates": structural_gates,
        "economic_gates": economic_gates,
        "source_gate_pass_count": sum(structural_gates.values()),
        "source_gate_total": len(structural_gates),
        "economic_gate_pass_count": sum(economic_gates.values()),
        "economic_gate_total": len(economic_gates),
    }


def trade_rows(trades: pd.DataFrame) -> bytes:
    lines: list[bytes] = []
    for row in trades.itertuples(index=False):
        local_date = row.local_date.isoformat()
        payload = {
            "trade_id": f"LOFIX001-{local_date}",
            "local_date": local_date,
            "year": int(row.year),
            "direction": "LONG" if int(row.direction) == 1 else "SHORT",
            "pre_close": float(row.pre_close),
            "signal_close": float(row.signal_close),
            "entry_close": float(row.entry_close),
            "exit_close": float(row.exit_close),
            "formation_log_return": round(float(row.formation_log_return), 12),
            "raw_move_pips": round(float(row.raw_move_pips), 10),
            "gross_pips": round(float(row.gross_pips), 10),
            "primary_net_x1_pips": round(float(row.primary_net_x1_pips), 10),
            "primary_net_x1_5_pips": round(float(row.primary_net_x1_5_pips), 10),
            "primary_net_x2_pips": round(float(row.primary_net_x2_pips), 10),
            "reverse_net_x1_pips": round(float(row.reverse_net_x1_pips), 10),
            "reverse_net_x1_5_pips": round(float(row.reverse_net_x1_5_pips), 10),
            "reverse_net_x2_pips": round(float(row.reverse_net_x2_pips), 10),
        }
        lines.append(canonical_json(payload) + b"\n")
    return b"".join(lines)


def execute(workspace: Path) -> Path:
    workspace = require_d_side(workspace, label="workspace")
    authority = validate_authority(workspace)
    manifest = validate_manifest(workspace)
    prior_primary, prior_reverse = load_prior_arms(workspace)
    dsr_module = load_dsr_module(workspace)
    evidence_root = require_d_side(workspace / EVIDENCE_ROOT_REL, label="evidence root")
    if evidence_root.exists():
        raise ContractError("one-shot evidence root already exists")

    started_path = evidence_root / "attempt_started.json"
    started = {
        "schema_version": "lofix_001_attempt_started.v1",
        "attempt_id": ATTEMPT_ID,
        "hypothesis_id": HYPOTHESIS_ID,
        "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "plan_sha256": PLAN_SHA256,
        "registry_row_sha256": authority.row_sha256,
        "evaluator_base_sha256": authority.evaluator_base_sha256,
        "evaluator_file_sha256": authority.evaluator_file_sha256,
        "test_sha256": authority.test_sha256,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "prior_trial_ledger_sha256": PRIOR_LEDGER_SHA256,
        "canonical_dsr_sha256": DSR_SHA256,
        "validation_opened": False,
        "research_holdout_opened": False,
    }
    write_json_new(started_path, started)

    frame = load_usdjpy(workspace)
    trades = build_trades_from_frame(frame)
    metrics = summarize_trades(
        trades,
        prior_primary=prior_primary,
        prior_reverse=prior_reverse,
        dsr_module=dsr_module,
    )
    if int(metrics["source_gate_pass_count"]) < int(metrics["source_gate_total"]):
        verdict = VERDICT_STRUCTURAL
    elif int(metrics["economic_gate_pass_count"]) == int(metrics["economic_gate_total"]):
        verdict = VERDICT_PASS
    else:
        verdict = VERDICT_KILL

    trades_path = evidence_root / "trades.jsonl"
    write_new(trades_path, trade_rows(trades))
    terminal_path = evidence_root / "train_economic_terminal.json"
    terminal = {
        "schema_version": "lofix_001_train_economic_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verdict": verdict,
        "engineering_valid": True,
        "economic_edge_evaluated": verdict != VERDICT_STRUCTURAL,
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "registry_row_sha256": authority.row_sha256,
        "evaluator_path": EVALUATOR_REL,
        "evaluator_base_sha256": authority.evaluator_base_sha256,
        "evaluator_file_sha256": authority.evaluator_file_sha256,
        "test_path": TEST_REL,
        "test_sha256": authority.test_sha256,
        "dataset_manifest_path": MANIFEST_REL,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "dataset_parquet_path": PARQUET_REL,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "source_manifest_row_count": int(manifest["row_count"]),
        "prior_trial_ledger_path": PRIOR_LEDGER_REL,
        "prior_trial_ledger_sha256": PRIOR_LEDGER_SHA256,
        "canonical_dsr_path": DSR_REL,
        "canonical_dsr_sha256": DSR_SHA256,
        "attempt_started_sha256": sha256_file(started_path),
        "trades_path": str(trades_path.relative_to(workspace)).replace("\\", "/"),
        "trades_sha256": sha256_file(trades_path),
        "metrics": metrics,
        "forbidden_counters": {
            "bars_read_2021plus": 0,
            "research_validation_opened": False,
            "research_holdout_opened": False,
            "hcc_payloads_decoded": 0,
            "mt5_launches": 0,
            "mql5_files_created": 0,
            "model0_runs": 0,
            "model4_runs": 0,
            "optimization_trials": 0,
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
    return terminal_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    terminal_path = execute(args.workspace.resolve())
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    metrics = terminal["metrics"]
    print(
        f"LOFIX001_RESULT verdict={terminal['verdict']} "
        f"trades={metrics['trade_count']} "
        f"pf_x1={metrics['profit_factor']['primary']['x1']:.6f} "
        f"dsr={metrics['deflated_sharpe']['primary_dsr']:.6f}"
    )
    print(f"TERMINAL {terminal_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
