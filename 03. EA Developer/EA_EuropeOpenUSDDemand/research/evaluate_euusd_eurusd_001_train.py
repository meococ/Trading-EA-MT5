#!/usr/bin/env python3
"""One-shot TRAIN proxy evaluator for HYP-EUUSD-EURUSD-M1-001."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Iterable, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EUUSD-EURUSD-M1-001"
ATTEMPT_ID = "EUEUR001-TRAIN-ECON-001"
PLAN_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
    "HYP-EUUSD-EURUSD-M1-001_TRAIN_ECONOMIC_PROBE_PLAN.md"
)
PLAN_SHA256 = "D8585C793F0F742D96471BC25330F0368714CCCD1E1E66DEAF4AA79C2A242B4C"
EVALUATOR_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
    "evaluate_euusd_eurusd_001_train.py"
)
TEST_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/tests/"
    "test_evaluate_euusd_eurusd_001_train.py"
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
LOJM_LEDGER_REL = (
    "03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/"
    "HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001/trades.jsonl"
)
LOFIX_LEDGER_REL = (
    "03. EA Developer/EA_LondonFixHalfHourMomentum/research/evidence/"
    "HYP-LOFIX-USDJPY-M1-002/LOFIX002-TRAIN-ECON-001/trades.jsonl"
)
EUJPY_LEDGER_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/"
    "HYP-EUUSD-USDJPY-M1-001/EUUSD001-TRAIN-ECON-001/trades.jsonl"
)
COMMON_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
    "evaluate_euusd_001_train.py"
)
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
EVIDENCE_ROOT_REL = (
    "03. EA Developer/EA_EuropeOpenUSDDemand/research/evidence/"
    f"{HYPOTHESIS_ID}/{ATTEMPT_ID}"
)

PARQUET_SHA256 = "C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6"
MANIFEST_SHA256 = "4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8"
LOJM_LEDGER_SHA256 = "6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98"
LOFIX_LEDGER_SHA256 = "04270A2E9772A884322753701D55B6101109B1BA1E49ABFF59F89B882815A6DB"
EUJPY_LEDGER_SHA256 = "18D8C2333FE421DFA279325D30A29D759AAD4333A304BA1FC68E7B485009E10C"
COMMON_SHA256 = "A8E8E61A8D75E9D95808A637E3E876A627DDBC8906EDF94743A79F1DCF691A63"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
DESIGN_START = pd.Timestamp("2016-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2020-12-31T23:59:59Z")
LOCAL_TZ = "Europe/Berlin"
PIP_SIZE = 0.0001
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
REVIEWED_REGISTRY_ROW_SHA256: str | None = "A9F887EBEC45DA4CC760C9E79473CE84EDC95BFDF0DA4AD650F8690D693F2B5C"
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    """Fail-closed engineering or authority violation."""


@dataclass(frozen=True)
class Authority:
    row_sha256: str
    evaluator_base_sha256: str
    evaluator_file_sha256: str
    test_sha256: str


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if _SENTINEL_RE.match(line.rstrip(b"\n"))]
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


def load_common(workspace: Path) -> ModuleType:
    path = require_d_side(workspace / COMMON_REL, label="common evaluator")
    if sha256_file(path) != COMMON_SHA256:
        raise ContractError("common evaluator hash mismatch")
    spec = importlib.util.spec_from_file_location("eueur_bound_euusd_common", path)
    if spec is None or spec.loader is None:
        raise ContractError("cannot load common evaluator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_authority(workspace: Path) -> Authority:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise ContractError("evaluator registry sentinel is not armed")
    plan = workspace / PLAN_REL
    evaluator = workspace / EVALUATOR_REL
    test = workspace / TEST_REL
    registry = workspace / REGISTRY_REL
    for label, path in (("plan", plan), ("evaluator", evaluator), ("test", test), ("registry", registry)):
        if not path.is_file():
            raise ContractError(f"{label} file is missing")
    if sha256_file(plan) != PLAN_SHA256:
        raise ContractError("plan hash drift")
    payload = evaluator.read_bytes()
    base_sha = normalized_evaluator_base_sha256(payload)
    file_sha = sha256_bytes(payload)
    test_sha = sha256_file(test)
    candidates: list[tuple[dict[str, object], bytes]] = []
    for raw in registry.read_bytes().splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ContractError("registry contains invalid JSONL") from exc
        if type(row) is not dict:
            raise ContractError("registry row must be an object")
        if row.get("hypothesis_id") == HYPOTHESIS_ID:
            candidates.append((row, raw + b"\n"))
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
    if row.get("state") != "probe" or row.get("prereg_sha256") != PLAN_SHA256:
        raise ContractError("registry state or plan binding is invalid")
    if validation.get("train_economic_evaluation_authorized") is not True:
        raise ContractError("train economic evaluation is not authorized")
    if validation.get("one_use") is not True or int(metrics.get("train_economic_attempts_consumed", -1)) != 0:
        raise ContractError("one-use attempt authority is invalid")
    if ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("attempt id is already registered")
    expected = {
        "reviewed_evaluator_base_sha256": base_sha,
        "reviewed_test_sha256": test_sha,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "prior_lojm_ledger_sha256": LOJM_LEDGER_SHA256,
        "prior_lofix_ledger_sha256": LOFIX_LEDGER_SHA256,
        "prior_euusd_usdjpy_ledger_sha256": EUJPY_LEDGER_SHA256,
        "common_evaluator_sha256": COMMON_SHA256,
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
    return Authority(row_sha, base_sha, file_sha, test_sha)


def load_eurusd(workspace: Path) -> pd.DataFrame:
    parquet = require_d_side(workspace / PARQUET_REL, label="parquet")
    if sha256_file(parquet) != PARQUET_SHA256:
        raise ContractError("dataset parquet hash mismatch")
    try:
        frame = pd.read_parquet(
            parquet,
            columns=["symbol", "time_utc", "close"],
            filters=[("symbol", "==", "EURUSD")],
        )
    except Exception as exc:  # pragma: no cover
        raise ContractError("failed to read frozen parquet") from exc
    if list(frame.columns) != ["symbol", "time_utc", "close"]:
        raise ContractError("parquet projection schema mismatch")
    if len(frame) != 1_859_939 or set(frame["symbol"].unique()) != {"EURUSD"}:
        raise ContractError("EURUSD parquet population mismatch")
    timestamps = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if timestamps.isna().any() or closes.isna().any():
        raise ContractError("timestamp or close contains invalid values")
    values = closes.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0.0).any():
        raise ContractError("close values must be finite and positive")
    if timestamps.duplicated().any() or not timestamps.is_monotonic_increasing:
        raise ContractError("EURUSD timestamps must be unique and increasing")
    if timestamps.min() < DESIGN_START or timestamps.max() > DESIGN_END:
        raise ContractError("EURUSD rows leave the frozen DESIGN window")
    return pd.DataFrame({"time_utc": timestamps, "close": closes.astype(float)})


def build_trades_from_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Build one short EURUSD 08:00-14:15 Berlin trade per complete weekday."""
    if set(frame.columns) != {"time_utc", "close"}:
        raise ContractError("frame must contain exactly time_utc and close")
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if times.isna().any() or closes.isna().any():
        raise ContractError("frame contains invalid time or close")
    if times.duplicated().any() or not times.is_monotonic_increasing:
        raise ContractError("frame times must be unique and increasing")
    if not np.isfinite(closes.to_numpy(dtype=float)).all() or (closes <= 0.0).any():
        raise ContractError("frame closes must be finite and positive")
    local = times.dt.tz_convert(LOCAL_TZ)
    hour = local.dt.hour.to_numpy()
    minute = local.dt.minute.to_numpy()
    weekday = local.dt.weekday.to_numpy()
    slots = np.select(
        [(hour == 7) & (minute == 59), (hour == 14) & (minute == 14)],
        ["entry", "exit"],
        default="",
    )
    mask = (weekday < 5) & (slots != "")
    selected = pd.DataFrame(
        {"local_date": local[mask].dt.date.to_numpy(), "slot": slots[mask], "close": closes[mask].to_numpy(dtype=float)}
    )
    if selected.duplicated(["local_date", "slot"]).any():
        raise ContractError("duplicate local date/slot observation")
    pivot = selected.pivot(index="local_date", columns="slot", values="close")
    for column in ("entry", "exit"):
        if column not in pivot:
            pivot[column] = np.nan
    pivot = pivot[["entry", "exit"]].dropna().sort_index()
    raw = (pivot["exit"].to_numpy() - pivot["entry"].to_numpy()) / PIP_SIZE
    gross = -raw
    trades = pd.DataFrame(
        {
            "local_date": list(pivot.index),
            "year": [day.year for day in pivot.index],
            "weekday": [day.weekday() for day in pivot.index],
            "direction": -np.ones(len(pivot), dtype=int),
            "entry_local_hhmm": ["07:59"] * len(pivot),
            "exit_local_hhmm": ["14:14"] * len(pivot),
            "entry_close": pivot["entry"].to_numpy(dtype=float),
            "exit_close": pivot["exit"].to_numpy(dtype=float),
            "raw_move_pips": raw.astype(float),
            "gross_pips": gross.astype(float),
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


def sign_flip_p_value(values: Sequence[float], *, permutations: int, seed: int) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        raise ContractError("sign-flip input is empty or non-finite")
    observed = float(array.mean())
    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in range(permutations):
        signs = rng.choice(np.array([-1.0, 1.0]), size=array.size)
        if float(np.mean(array * signs)) >= observed:
            exceed += 1
    return (1.0 + exceed) / (permutations + 1.0)


def _read_pair(path: Path, expected_sha: str) -> tuple[np.ndarray, np.ndarray]:
    if sha256_file(path) != expected_sha:
        raise ContractError("prior ledger hash mismatch")
    primary: list[float] = []
    reverse: list[float] = []
    for raw in path.read_bytes().splitlines():
        try:
            row = json.loads(raw)
            primary.append(float(row["primary_net_x1_pips"]))
            reverse.append(float(row["reverse_net_x1_pips"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ContractError("prior ledger row is invalid") from exc
    if len(primary) < 1000 or len(primary) != len(reverse):
        raise ContractError("prior ledger population mismatch")
    return np.asarray(primary, dtype=float), np.asarray(reverse, dtype=float)


def load_prior_arms(workspace: Path) -> dict[str, np.ndarray]:
    lojm = _read_pair(require_d_side(workspace / LOJM_LEDGER_REL, label="LOJM ledger"), LOJM_LEDGER_SHA256)
    lofix = _read_pair(require_d_side(workspace / LOFIX_LEDGER_REL, label="LOFIX ledger"), LOFIX_LEDGER_SHA256)
    eujpy = _read_pair(require_d_side(workspace / EUJPY_LEDGER_REL, label="EUUSD-JPY ledger"), EUJPY_LEDGER_SHA256)
    return {
        "lojm001_primary": lojm[0], "lojm001_reverse": lojm[1],
        "lofix002_primary": lofix[0], "lofix002_reverse": lofix[1],
        "euusd_usdjpy_001_primary": eujpy[0], "euusd_usdjpy_001_reverse": eujpy[1],
    }


def _arm_moments(values: Sequence[float]) -> dict[str, float | int]:
    series = pd.Series(np.asarray(values, dtype=float))
    if len(series) < 3 or not np.isfinite(series.to_numpy()).all():
        raise ContractError("DSR arm is too short or non-finite")
    std = float(series.std(ddof=1))
    if std <= 0.0:
        raise ContractError("DSR arm has zero variance")
    return {"n": len(series), "sr": float(series.mean()) / std, "skew": float(series.skew()), "kurtosis_non_excess": float(series.kurt()) + 3.0}


def compute_dsr(current_primary: Sequence[float], current_reverse: Sequence[float], prior: dict[str, np.ndarray], module: ModuleType) -> dict[str, object]:
    if len(prior) != 6:
        raise ContractError("prior DSR arm universe mismatch")
    arms = {name: _arm_moments(values) for name, values in prior.items()}
    arms["euusd_eurusd_001_primary"] = _arm_moments(current_primary)
    arms["euusd_eurusd_001_reverse"] = _arm_moments(current_reverse)
    srs = [float(item["sr"]) for item in arms.values()]
    variance = float(np.var(srs, ddof=1))
    primary = arms["euusd_eurusd_001_primary"]
    value = float(module.dsr(float(primary["sr"]), int(primary["n"]), float(primary["skew"]), float(primary["kurtosis_non_excess"]), variance, len(arms)))
    if not math.isfinite(value):
        raise ContractError("DSR result is non-finite")
    return {"n_trials": len(arms), "variance_sr_trials": variance, "expected_max_sr": float(module.expected_max_sharpe(variance, len(arms))), "primary_dsr": value, "arms": arms}


def summarize_trades(trades: pd.DataFrame, *, prior: dict[str, np.ndarray], dsr_module: ModuleType, permutations: int = PERMUTATIONS, seed: int = PERMUTATION_SEED) -> dict[str, object]:
    if trades.empty:
        return {"trade_count": 0, "source_gate_pass_count": 0, "source_gate_total": 5, "economic_gate_pass_count": 0, "economic_gate_total": 8, "structural_gates": {}, "economic_gates": {}}
    first_date, last_date = min(trades["local_date"]), max(trades["local_date"])
    expected_weekdays = len(pd.date_range(first_date, last_date, freq="B"))
    elapsed_weeks = float((DESIGN_END - DESIGN_START).total_seconds() / 604800.0)
    count = len(trades)
    cadence = count / elapsed_weeks
    year_count = {str(int(k)): int(v) for k, v in trades.groupby("year").size().items()}
    coverage = count / expected_weekdays
    max_year_share = max(year_count.values()) / count
    pf: dict[str, dict[str, float | None]] = {"primary": {}, "reverse": {}}
    expectancy: dict[str, dict[str, float]] = {"primary": {}, "reverse": {}}
    for arm in ("primary", "reverse"):
        for label in COSTS:
            values = trades[f"{arm}_net_{label}_pips"]
            pf[arm][label] = profit_factor(values)
            expectancy[arm][label] = float(values.mean())
    gross_pf = {"primary": profit_factor(trades["gross_pips"]), "reverse": profit_factor(-trades["gross_pips"])}
    annual = {str(int(y)): float(g["primary_net_x1_pips"].sum()) for y, g in trades.groupby("year")}
    positive_years = sum(v > 0 for v in annual.values())
    p_value = sign_flip_p_value(trades["gross_pips"], permutations=permutations, seed=seed)
    dsr = compute_dsr(trades["primary_net_x1_pips"], trades["reverse_net_x1_pips"], prior, dsr_module)
    exact = bool((trades["direction"] == -1).all() and (trades["entry_local_hhmm"] == "07:59").all() and (trades["exit_local_hhmm"] == "14:14").all())
    structural = {"trade_count_ge_1000": count >= 1000, "weekday_coverage_ge_0_95": coverage >= 0.95, "cadence_2_to_5": 2 <= cadence <= 5, "max_year_share_le_0_25": max_year_share <= 0.25, "fixed_short_exact_boundaries": exact}
    primary_x1, reverse_x1 = pf["primary"]["x1"], pf["reverse"]["x1"]
    economic = {
        "pf_x1_gt_1_30": primary_x1 is not None and primary_x1 > 1.30,
        "pf_x1_5_ge_1_25": pf["primary"]["x1_5"] is not None and pf["primary"]["x1_5"] >= 1.25,
        "pf_x2_ge_1_00": pf["primary"]["x2"] is not None and pf["primary"]["x2"] >= 1.0,
        "expectancy_x1_gt_0": expectancy["primary"]["x1"] > 0,
        "positive_years_ge_4_of_5": len(annual) == 5 and positive_years >= 4,
        "sign_flip_p_le_0_05": p_value <= 0.05,
        "dsr_ge_0_95": float(dsr["primary_dsr"]) >= 0.95,
        "beats_reverse_x1": primary_x1 is not None and reverse_x1 is not None and primary_x1 > reverse_x1 and expectancy["primary"]["x1"] > expectancy["reverse"]["x1"],
    }
    weekday = {str(int(d)): {"count": len(g), "net_pips": float(g["primary_net_x1_pips"].sum()), "profit_factor": profit_factor(g["primary_net_x1_pips"])} for d, g in trades.groupby("weekday")}
    return {"trade_count": count, "first_local_date": first_date.isoformat(), "last_local_date": last_date.isoformat(), "expected_weekdays_between_first_last": expected_weekdays, "eligible_weekday_coverage": coverage, "elapsed_calendar_weeks": elapsed_weeks, "trades_per_elapsed_week": cadence, "year_count": year_count, "max_year_share": max_year_share, "gross_profit_factor": gross_pf, "gross_expectancy_pips": float(trades["gross_pips"].mean()), "profit_factor": pf, "expectancy_pips": expectancy, "annual_primary_x1_net_pips": annual, "positive_years": positive_years, "weekday_primary_x1": weekday, "permutation_count": permutations, "permutation_seed": seed, "sign_flip_one_sided_p_value": p_value, "deflated_sharpe": dsr, "structural_gates": structural, "economic_gates": economic, "source_gate_pass_count": sum(structural.values()), "source_gate_total": len(structural), "economic_gate_pass_count": sum(economic.values()), "economic_gate_total": len(economic)}


def canonical_json(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ContractError("non-canonical or non-finite JSON") from exc


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def write_json_new(path: Path, value: object) -> None:
    write_new(path, canonical_json(value) + b"\n")


def trade_rows(trades: pd.DataFrame) -> bytes:
    rows: list[bytes] = []
    for row in trades.itertuples(index=False):
        date = row.local_date.isoformat()
        payload = {"trade_id": f"EUEUR001-{date}", "local_date": date, "year": int(row.year), "weekday": int(row.weekday), "direction": "SHORT", "entry_local_hhmm": row.entry_local_hhmm, "exit_local_hhmm": row.exit_local_hhmm, "entry_close": float(row.entry_close), "exit_close": float(row.exit_close), "raw_move_pips": round(float(row.raw_move_pips), 10), "gross_pips": round(float(row.gross_pips), 10), "primary_net_x1_pips": round(float(row.primary_net_x1_pips), 10), "primary_net_x1_5_pips": round(float(row.primary_net_x1_5_pips), 10), "primary_net_x2_pips": round(float(row.primary_net_x2_pips), 10), "reverse_net_x1_pips": round(float(row.reverse_net_x1_pips), 10), "reverse_net_x1_5_pips": round(float(row.reverse_net_x1_5_pips), 10), "reverse_net_x2_pips": round(float(row.reverse_net_x2_pips), 10)}
        rows.append(canonical_json(payload) + b"\n")
    return b"".join(rows)


def execute(workspace: Path) -> Path:
    workspace = require_d_side(workspace, label="workspace")
    authority = validate_authority(workspace)
    common = load_common(workspace)
    helper = common.load_helper(workspace)
    manifest = helper.validate_manifest(workspace)
    prior = load_prior_arms(workspace)
    dsr_module = helper.load_dsr_module(workspace)
    evidence = require_d_side(workspace / EVIDENCE_ROOT_REL, label="evidence root")
    if evidence.exists():
        raise ContractError("one-shot evidence root already exists")
    started_path = evidence / "attempt_started.json"
    started = {"schema_version": "euusd_eurusd_001_attempt_started.v1", "attempt_id": ATTEMPT_ID, "hypothesis_id": HYPOTHESIS_ID, "started_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority.row_sha256, "evaluator_base_sha256": authority.evaluator_base_sha256, "evaluator_file_sha256": authority.evaluator_file_sha256, "test_sha256": authority.test_sha256, "dataset_manifest_sha256": MANIFEST_SHA256, "dataset_parquet_sha256": PARQUET_SHA256, "prior_lojm_ledger_sha256": LOJM_LEDGER_SHA256, "prior_lofix_ledger_sha256": LOFIX_LEDGER_SHA256, "prior_euusd_usdjpy_ledger_sha256": EUJPY_LEDGER_SHA256, "common_evaluator_sha256": COMMON_SHA256, "canonical_dsr_sha256": DSR_SHA256, "validation_opened": False, "research_holdout_opened": False}
    write_json_new(started_path, started)
    trades = build_trades_from_frame(load_eurusd(workspace))
    metrics = summarize_trades(trades, prior=prior, dsr_module=dsr_module)
    if metrics["source_gate_pass_count"] < metrics["source_gate_total"]:
        verdict = VERDICT_STRUCTURAL
    elif metrics["economic_gate_pass_count"] == metrics["economic_gate_total"]:
        verdict = VERDICT_PASS
    else:
        verdict = VERDICT_KILL
    trades_path = evidence / "trades.jsonl"
    write_new(trades_path, trade_rows(trades))
    terminal_path = evidence / "train_economic_terminal.json"
    terminal = {"schema_version": "euusd_eurusd_001_train_economic_terminal.v1", "hypothesis_id": HYPOTHESIS_ID, "attempt_id": ATTEMPT_ID, "completed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "verdict": verdict, "engineering_valid": True, "economic_edge_evaluated": verdict != VERDICT_STRUCTURAL, "plan_path": PLAN_REL, "plan_sha256": PLAN_SHA256, "registry_row_sha256": authority.row_sha256, "evaluator_path": EVALUATOR_REL, "evaluator_base_sha256": authority.evaluator_base_sha256, "evaluator_file_sha256": authority.evaluator_file_sha256, "test_path": TEST_REL, "test_sha256": authority.test_sha256, "dataset_manifest_path": MANIFEST_REL, "dataset_manifest_sha256": MANIFEST_SHA256, "dataset_parquet_path": PARQUET_REL, "dataset_parquet_sha256": PARQUET_SHA256, "source_manifest_row_count": int(manifest["row_count"]), "prior_lojm_ledger_path": LOJM_LEDGER_REL, "prior_lojm_ledger_sha256": LOJM_LEDGER_SHA256, "prior_lofix_ledger_path": LOFIX_LEDGER_REL, "prior_lofix_ledger_sha256": LOFIX_LEDGER_SHA256, "prior_euusd_usdjpy_ledger_path": EUJPY_LEDGER_REL, "prior_euusd_usdjpy_ledger_sha256": EUJPY_LEDGER_SHA256, "common_evaluator_path": COMMON_REL, "common_evaluator_sha256": COMMON_SHA256, "canonical_dsr_path": DSR_REL, "canonical_dsr_sha256": DSR_SHA256, "attempt_started_sha256": sha256_file(started_path), "trades_path": str(trades_path.relative_to(workspace)).replace("\\", "/"), "trades_sha256": sha256_file(trades_path), "metrics": metrics, "forbidden_counters": {"bars_read_2021plus": 0, "research_validation_opened": False, "research_holdout_opened": False, "hcc_payloads_decoded": 0, "mt5_launches": 0, "mql5_files_created": 0, "model0_runs": 0, "model4_runs": 0, "optimization_trials": 0, "network_calls_during_evaluation": 0, "paid_requests_made": 0, "orders_submitted": 0, "paper_trading": False, "live_trading": False}, "authority_after_verdict": {"mql5_model0_packet_may_be_preregistered": verdict == VERDICT_PASS, "validation_authorized": False, "holdout_authorized": False, "optimization_authorized": False, "promotion_eligible": False, "paper_trading_authorized": False, "live_trading_authorized": False}}
    write_json_new(terminal_path, terminal)
    return terminal_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    terminal_path = execute(args.workspace.resolve())
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    metrics = terminal["metrics"]
    print(f"EUEUR001_RESULT verdict={terminal['verdict']} trades={metrics['trade_count']} pf_x1={metrics['profit_factor']['primary']['x1']:.6f} dsr={metrics['deflated_sharpe']['primary_dsr']:.6f}")
    print(f"TERMINAL {terminal_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
