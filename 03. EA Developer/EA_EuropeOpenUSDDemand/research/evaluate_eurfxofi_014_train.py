#!/usr/bin/env python3
"""One-shot TRAIN evaluator for final-15-second CME 6E flow reversal."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd


HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-014"
SOURCE_HYPOTHESIS_ID = "HYP-EURFXOFI-EURUSD-M1-013"
ATTEMPT_ID = "EURFXOFI014-TRAIN-ECON-001"
DISPLAY_TAG = "HYP014"
ARTIFACT_PREFIX = "EURFXOFI014"
SCHEMA_PREFIX = "eurfxofi014"
RUN_ELIGIBLE_STATE = "screened"
ALLOWED_MISSING_TARGET_DATES: tuple[str, ...] = ()
BASE_REL = "03. EA Developer/EA_EuropeOpenUSDDemand/research/"
PLAN_REL = BASE_REL + "HYP-EURFXOFI-EURUSD-M1-014_TRAIN_ECONOMIC_PROBE_PLAN.md"
EVALUATOR_REL = BASE_REL + "evaluate_eurfxofi_014_train.py"
TEST_REL = BASE_REL + "tests/test_evaluate_eurfxofi_014_train.py"
REGISTRY_REL = "04. Memory/research/CANDIDATE_REGISTRY.jsonl"
FEATURE_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-013/EURFXOFI013-SOURCE-CLASSIFIER-001/source_features.parquet"
)
SOURCE_SUMMARY_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-013/EURFXOFI013-SOURCE-CLASSIFIER-001/source_quality_summary.json"
)
SOURCE_ARTIFACT_MANIFEST_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-013/EURFXOFI013-SOURCE-CLASSIFIER-001/artifact_manifest.json"
)
SIGNAL_LEDGER_REL = (
    "02. AlphaFactory/data/databento/cme_6e_ecbfix_ofi/"
    "HYP-EURFXOFI-EURUSD-M1-002/EURFXOFI002-SIGNAL-DATE-SELECTION-001/signal_dates.jsonl"
)
PARQUET_REL = (
    "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
    "HYP-TRILAG-EURJPY-M1-002/design_m1_close.parquet"
)
MANIFEST_REL = (
    "02. AlphaFactory/data/fivepercent/TriangularConsensusLag/"
    "HYP-TRILAG-EURJPY-M1-002/design_m1_manifest.json"
)
DSR_REL = "02. AlphaFactory/tools/research/dsr.py"
EVIDENCE_ROOT_REL = BASE_REL + f"evidence/{HYPOTHESIS_ID}/{ATTEMPT_ID}"

PRIOR_LEDGERS = {
    "lojm001": (
        "03. EA Developer/EA_LondonOpenJPYMomentum/research/evidence/"
        "HYP-LOJM-USDJPY-M1-001/LOJM001-TRAIN-ECON-001/trades.jsonl",
        "6985108DEEDF59A503F5A96285F7D5CC8D8CE303FC03A599B5C3E414E0ECDC98",
    ),
    "lofix002": (
        "03. EA Developer/EA_LondonFixHalfHourMomentum/research/evidence/"
        "HYP-LOFIX-USDJPY-M1-002/LOFIX002-TRAIN-ECON-001/trades.jsonl",
        "04270A2E9772A884322753701D55B6101109B1BA1E49ABFF59F89B882815A6DB",
    ),
    "euusd_usdjpy001": (
        BASE_REL + "evidence/HYP-EUUSD-USDJPY-M1-001/EUUSD001-TRAIN-ECON-001/trades.jsonl",
        "18D8C2333FE421DFA279325D30A29D759AAD4333A304BA1FC68E7B485009E10C",
    ),
    "euusd_eurusd001": (
        BASE_REL + "evidence/HYP-EUUSD-EURUSD-M1-001/EUEUR001-TRAIN-ECON-001/trades.jsonl",
        "204050AAA213DB1BC468FD022733425DC3E2E70EF33A742A0A7D620EF8B166E8",
    ),
    "euvix002": (
        BASE_REL + "evidence/HYP-EUVIX-EURUSD-M1-002/EUVIX002-TRAIN-ECON-001/trades.jsonl",
        "B2C9CA21F80F307BDBCB9B8DFE34D4477D3B7CFF78B164823D6810563EA66F1E",
    ),
    "eurfxrev001": (
        BASE_REL + "evidence/HYP-EURFXREV-EURUSD-M1-001/EURFXREV001-TRAIN-ECON-001/trades.jsonl",
        "952E193FFC65D91B43E7F55EE970A65E904B2E9DD50A5E6469B9659EDFC28E45",
    ),
}

PLAN_SHA256 = "55FD3EFC6EF1737D6418D2AAC86B5BA65A1792E86211008530F4C1CCF3E1A8D7"
SIGNAL_LEDGER_SHA256 = "EA0083B28AEF366ABDDCD36C82505100B2B9E10D54AC700E384879D83EF0E1DF"
PARQUET_SHA256 = "C1065F84F7FB79F7C4E83A2A52B9BD8C137E7CF788F75BC46D53C3FBDCD6EAE6"
MANIFEST_SHA256 = "4A8A51693B7D268BA2E8A179316774463D1C5631769C6B28E06DC113026228A8"
DSR_SHA256 = "A0659CDCDB2EAB4F29F69A1FBF4222FE3EC12467FE4CC664E194173126A4CEEA"
LOCAL_TZ = "Europe/Berlin"
PIP_SIZE = 0.0001
COSTS = {"x1": 1.50, "x1_5": 2.25, "x2": 3.00}
ARMS = (
    "flow_reversal_primary",
    "flow_continuation_control",
    "pressure_reversal_control",
    "pressure_continuation_control",
)
PERMUTATIONS = 10_000
PERMUTATION_SEED = 20_260_730
DESIGN_START = pd.Timestamp("2016-01-01T00:00:00Z")
DESIGN_END = pd.Timestamp("2020-12-31T23:59:59Z")
EXPECTED_TRAIN_DATES = 630
VERDICT_PASS = "PASS_TRAIN_AUTHORIZE_FRESH_SEQUENTIAL_VALIDATION_SUCCESSOR_ONLY"
VERDICT_KILL = "KILL_TRAIN_FLOW_REVERSAL_HOLDOUT_REMAINS_SEALED"
VERDICT_STRUCTURAL = "INVALID_TRAIN_SOURCE_OR_ENGINEERING"
CHART_NAMES = (
    "01_equity_and_drawdown.png",
    "02_yearly_performance.png",
    "03_four_arm_comparison.png",
    "04_flow_decile_diagnostic.png",
    "05_distributions_and_funnel.png",
)

# Independent pre-run QC replaces only this sentinel. Its normalized value is
# used for the registry binding, so arming cannot change reviewed logic.
REVIEWED_REGISTRY_ROW_SHA256: str | None = None
_SENTINEL_RE = re.compile(
    rb'^REVIEWED_REGISTRY_ROW_SHA256: str \| None = (?:None|"[A-F0-9]{64}")\r?$'
)


class ContractError(RuntimeError):
    """Fail-closed authority, data or engineering violation."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def workspace_from_source() -> Path:
    return Path(__file__).resolve().parents[3]


def require_d(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if resolved.drive.upper() != "D:":
        raise ContractError(f"{label} must stay on D:, got {resolved}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def normalized_evaluator_base_sha256(payload: bytes) -> str:
    lines = payload.splitlines(keepends=True)
    indices = [
        index
        for index, line in enumerate(lines)
        if _SENTINEL_RE.match(line.rstrip(b"\n"))
    ]
    if len(indices) != 1:
        raise ContractError("evaluator must contain exactly one valid sentinel")
    index = indices[0]
    newline = b"\n" if lines[index].endswith(b"\n") else b""
    lines[index] = b"REVIEWED_REGISTRY_ROW_SHA256: str | None = None" + newline
    return sha256_bytes(b"".join(lines))


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def latest_registry_row(path: Path, hypothesis_id: str) -> tuple[dict[str, Any], bytes]:
    latest: tuple[dict[str, Any], bytes] | None = None
    for raw in path.read_bytes().splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row.get("hypothesis_id") == hypothesis_id:
            latest = (row, raw + b"\n")
    if latest is None:
        raise ContractError(f"registry missing {hypothesis_id}")
    return latest


def validate_authority(root: Path) -> dict[str, str]:
    if type(REVIEWED_REGISTRY_ROW_SHA256) is not str or len(REVIEWED_REGISTRY_ROW_SHA256) != 64:
        raise ContractError("registry sentinel is not armed")
    plan = root / PLAN_REL
    evaluator = root / EVALUATOR_REL
    test = root / TEST_REL
    registry = root / REGISTRY_REL
    for label, path in (("plan", plan), ("evaluator", evaluator), ("test", test), ("registry", registry)):
        if not path.is_file():
            raise ContractError(f"missing {label}: {path}")
    if sha256_file(plan) != PLAN_SHA256:
        raise ContractError("plan hash drift")
    evaluator_payload = evaluator.read_bytes()
    evaluator_base_hash = normalized_evaluator_base_sha256(evaluator_payload)
    test_hash = sha256_file(test)

    row, raw = latest_registry_row(registry, HYPOTHESIS_ID)
    row_hash = sha256_bytes(raw)
    if row_hash != REVIEWED_REGISTRY_ROW_SHA256:
        raise ContractError("sentinel does not bind latest HYP014 row")
    validation = row.get("validation", {})
    metrics = row.get("metrics", {})
    if row.get("state") != RUN_ELIGIBLE_STATE or row.get("prereg_sha256") != PLAN_SHA256:
        raise ContractError("HYP014 state/plan is not run-eligible")
    if validation.get("train_economic_evaluation_authorized") is not True:
        raise ContractError("TRAIN economics is not authorized")
    for key in (
        "performance_metrics_authorized",
        "economics_authorized",
        "outcome_prices_authorized",
        "post_entry_price_projection_authorized",
    ):
        if validation.get(key) is not True:
            raise ContractError(f"required TRAIN authority closed: {key}")
    if validation.get("one_use") is not True:
        raise ContractError("HYP014 one-use flag absent")
    if int(metrics.get("train_economic_attempts_consumed", -1)) != 0:
        raise ContractError("HYP014 attempt already consumed")
    if ATTEMPT_ID in row.get("run_ids", []):
        raise ContractError("HYP014 attempt ID already present")
    expected = {
        "train_economic_plan_sha256": PLAN_SHA256,
        "reviewed_evaluator_base_sha256": evaluator_base_hash,
        "reviewed_test_sha256": test_hash,
        "signal_date_ledger_sha256": SIGNAL_LEDGER_SHA256,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "canonical_dsr_sha256": DSR_SHA256,
    }
    for key, value in expected.items():
        if validation.get(key) != value:
            raise ContractError(f"registry binding mismatch: {key}")
    source_hashes = {
        "feature": str(validation.get("source_quality_feature_sha256", "")),
        "summary": str(validation.get("source_quality_summary_sha256", "")),
        "artifact_manifest": str(validation.get("source_quality_artifact_manifest_sha256", "")),
    }
    if any(len(value) != 64 for value in source_hashes.values()):
        raise ContractError("HYP014 source-quality hash binding missing")

    source_row, _ = latest_registry_row(registry, SOURCE_HYPOTHESIS_ID)
    source_validation = source_row.get("validation", {})
    if source_row.get("state") != "parked" or source_row.get("verdict") != "PASS_SOURCE_QUALITY_HANDOFF_TO_TRAIN_ECONOMICS":
        raise ContractError("HYP013 is not a terminal source-quality PASS")
    if source_validation.get("source_features_sha256") != source_hashes["feature"]:
        raise ContractError("HYP013/HYP014 feature binding mismatch")
    if source_validation.get("source_quality_summary_sha256") != source_hashes["summary"]:
        raise ContractError("HYP013/HYP014 summary binding mismatch")
    if source_validation.get("artifact_manifest_sha256") != source_hashes["artifact_manifest"]:
        raise ContractError("HYP013/HYP014 artifact-manifest binding mismatch")
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
            raise ContractError(f"forbidden authority open: {key}")
    return {
        "registry_row_sha256": row_hash,
        "evaluator_base_sha256": evaluator_base_hash,
        "evaluator_file_sha256": sha256_bytes(evaluator_payload),
        "test_sha256": test_hash,
        **source_hashes,
    }


def load_module(path: Path, expected_hash: str, name: str) -> ModuleType:
    if sha256_file(path) != expected_hash:
        raise ContractError(f"{name} hash mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_eurusd(root: Path) -> pd.DataFrame:
    parquet = require_d(root / PARQUET_REL, "target parquet")
    manifest = require_d(root / MANIFEST_REL, "target manifest")
    if sha256_file(parquet) != PARQUET_SHA256 or sha256_file(manifest) != MANIFEST_SHA256:
        raise ContractError("target dataset hash mismatch")
    frame = pd.read_parquet(
        parquet,
        columns=["symbol", "time_utc", "close"],
        filters=[("symbol", "==", "EURUSD")],
    )
    if list(frame.columns) != ["symbol", "time_utc", "close"]:
        raise ContractError("target projection schema mismatch")
    if len(frame) != 1_859_939 or set(frame["symbol"].unique()) != {"EURUSD"}:
        raise ContractError("target population mismatch")
    times = pd.to_datetime(frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(frame["close"], errors="coerce")
    if times.isna().any() or closes.isna().any() or times.duplicated().any():
        raise ContractError("target time/price integrity failed")
    if not times.is_monotonic_increasing:
        raise ContractError("target timestamps are not increasing")
    values = closes.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ContractError("target closes are invalid")
    if times.min() < DESIGN_START or times.max() > DESIGN_END:
        raise ContractError("target dataset leaves TRAIN boundary")
    return pd.DataFrame({"time_utc": times, "close": values})


def load_signal_ledger(path: Path) -> pd.DataFrame:
    if sha256_file(path) != SIGNAL_LEDGER_SHA256:
        raise ContractError("signal ledger hash mismatch")
    rows: list[dict[str, Any]] = []
    for raw in path.read_bytes().splitlines():
        item = json.loads(raw)
        if item.get("split") != "TRAIN":
            continue
        rows.append(
            {
                "local_date": str(item["local_date"]),
                "pre_fix_pressure_pips": float(item["pre_fix_pressure_pips"]),
                "pressure_threshold_pips": float(item["pressure_threshold_pips"]),
                "pressure_direction": int(item["direction_from_pressure"]),
            }
        )
    frame = pd.DataFrame(rows).sort_values("local_date").reset_index(drop=True)
    if len(frame) != EXPECTED_TRAIN_DATES or frame["local_date"].duplicated().any():
        raise ContractError("TRAIN signal-ledger population mismatch")
    if not (
        frame["pre_fix_pressure_pips"].abs() >= frame["pressure_threshold_pips"]
    ).all():
        raise ContractError("signal ledger violates frozen threshold")
    if not (
        frame["pressure_direction"].to_numpy()
        == -np.sign(frame["pre_fix_pressure_pips"].to_numpy()).astype(int)
    ).all():
        raise ContractError("signal ledger pressure direction mismatch")
    return frame


def load_source_features(
    path: Path, expected_hash: str, summary_path: Path, summary_hash: str
) -> pd.DataFrame:
    if sha256_file(path) != expected_hash or sha256_file(summary_path) != summary_hash:
        raise ContractError("source-quality artifact hash mismatch")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("verdict") != "PASS_SOURCE_QUALITY":
        raise ContractError("source-quality summary is not PASS")
    if summary.get("outcome_fields_used") is not False:
        raise ContractError("source-quality summary opened outcomes")
    columns = [
        "local_date",
        "split",
        "source_empty",
        "records",
        "flow_signed",
        "flow_imbalance",
        "classified_volume",
        "total_volume",
        "flow_acceleration",
        "late_flow_share",
    ]
    frame = pd.read_parquet(path, columns=columns)
    if len(frame) != 1359 or frame["local_date"].duplicated().any():
        raise ContractError("source feature population mismatch")
    train = frame.loc[frame["split"].eq("TRAIN")].copy()
    if len(train) != EXPECTED_TRAIN_DATES:
        raise ContractError("source TRAIN split mismatch")
    train["local_date"] = train["local_date"].astype(str)
    numeric = [
        "records",
        "flow_signed",
        "flow_imbalance",
        "classified_volume",
        "total_volume",
        "flow_acceleration",
        "late_flow_share",
    ]
    for name in numeric:
        train[name] = pd.to_numeric(train[name], errors="coerce")
    populated = ~train["source_empty"].astype(bool)
    if train.loc[populated, ["records", "flow_signed", "classified_volume"]].isna().any().any():
        raise ContractError("populated source rows have null core flow fields")
    return train.sort_values("local_date").reset_index(drop=True)


def project_train_targets(price_frame: pd.DataFrame) -> pd.DataFrame:
    if set(price_frame.columns) != {"time_utc", "close"}:
        raise ContractError("price frame projection mismatch")
    times = pd.to_datetime(price_frame["time_utc"], utc=True, errors="coerce")
    closes = pd.to_numeric(price_frame["close"], errors="coerce")
    local = times.dt.tz_convert(LOCAL_TZ)
    hhmm = local.dt.strftime("%H:%M")
    slot = hhmm.map({"14:14": "entry", "15:59": "exit"}).fillna("")
    mask = (local.dt.weekday < 5) & slot.ne("")
    selected = pd.DataFrame(
        {
            "local_date": local[mask].dt.strftime("%Y-%m-%d").to_numpy(),
            "slot": slot[mask].to_numpy(),
            "close": closes[mask].to_numpy(dtype=float),
        }
    )
    if selected.duplicated(["local_date", "slot"]).any():
        raise ContractError("duplicate target date/slot")
    pivot = selected.pivot(index="local_date", columns="slot", values="close")
    if not {"entry", "exit"}.issubset(pivot.columns):
        raise ContractError("target boundary columns absent")
    pivot = pivot[["entry", "exit"]].dropna().reset_index()
    pivot["post_fix_move_pips"] = (pivot["exit"] - pivot["entry"]) / PIP_SIZE
    return pivot


def build_trades(
    features: pd.DataFrame, signal_ledger: pd.DataFrame, targets: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    if len(features) != EXPECTED_TRAIN_DATES or len(signal_ledger) != EXPECTED_TRAIN_DATES:
        raise ContractError("build input TRAIN population mismatch")
    merged = signal_ledger.merge(features, on="local_date", how="inner", validate="one_to_one")
    if len(merged) != EXPECTED_TRAIN_DATES:
        raise ContractError("signal/source date join mismatch")
    merged = merged.merge(targets, on="local_date", how="left", validate="one_to_one")
    missing_target = int(merged[["entry", "exit", "post_fix_move_pips"]].isna().any(axis=1).sum())
    source_empty = merged["source_empty"].astype(bool)
    zero_flow = merged["flow_signed"].fillna(0).eq(0)
    target_available = merged[["entry", "exit", "post_fix_move_pips"]].notna().all(axis=1)
    eligible = ~source_empty & ~zero_flow & target_available
    funnel = {
        "selected_train_dates": int(len(merged)),
        "source_empty_dates": int(source_empty.sum()),
        "zero_signed_flow_dates": int((~source_empty & zero_flow).sum()),
        "missing_target_dates": missing_target,
        "trades": int((eligible & merged["post_fix_move_pips"].notna()).sum()),
    }
    missing_dates = tuple(sorted(merged.loc[~target_available, "local_date"].astype(str)))
    if missing_dates != tuple(sorted(ALLOWED_MISSING_TARGET_DATES)):
        raise ContractError(
            f"selected TRAIN dates missing exact target boundaries; frozen set mismatch: expected {ALLOWED_MISSING_TARGET_DATES}, got {missing_dates}"
        )
    trades = merged.loc[eligible].copy()
    if trades.empty:
        raise ContractError("no nonzero-flow TRAIN trades")
    flow_sign = np.sign(trades["flow_signed"].to_numpy(dtype=float)).astype(int)
    pressure_sign = np.sign(trades["pre_fix_pressure_pips"].to_numpy(dtype=float)).astype(int)
    if not np.isin(flow_sign, (-1, 1)).all() or not np.isin(pressure_sign, (-1, 1)).all():
        raise ContractError("non-binary flow/pressure sign after eligibility")
    directions = {
        "flow_reversal_primary": -flow_sign,
        "flow_continuation_control": flow_sign,
        "pressure_reversal_control": -pressure_sign,
        "pressure_continuation_control": pressure_sign,
    }
    move = trades["post_fix_move_pips"].to_numpy(dtype=float)
    for arm, direction in directions.items():
        trades[f"{arm}_direction"] = direction
        trades[f"{arm}_gross_pips"] = direction * move
        for label, cost in COSTS.items():
            trades[f"{arm}_net_{label}_pips"] = trades[f"{arm}_gross_pips"] - cost
    trades["direction"] = trades["flow_reversal_primary_direction"]
    trades["gross_pips"] = trades["flow_reversal_primary_gross_pips"]
    for label in COSTS:
        trades[f"primary_net_{label}_pips"] = trades[f"flow_reversal_primary_net_{label}_pips"]
        trades[f"reverse_net_{label}_pips"] = trades[f"flow_continuation_control_net_{label}_pips"]
    trades["year"] = trades["local_date"].str[:4].astype(int)
    trades["weekday"] = pd.to_datetime(trades["local_date"]).dt.weekday
    trades["flow_pressure_agree"] = flow_sign.eq(pressure_sign) if isinstance(flow_sign, pd.Series) else flow_sign == pressure_sign
    trades["entry_local_hhmm"] = "14:14"
    trades["exit_local_hhmm"] = "15:59"
    return trades.sort_values("local_date").reset_index(drop=True), funnel


def profit_factor(values: Iterable[float]) -> float | None:
    array = np.asarray(list(values), dtype=float)
    wins = float(array[array > 0].sum())
    losses = float(-array[array < 0].sum())
    return wins / losses if wins > 0 and losses > 0 else None


def sign_flip_p_value(values: Sequence[float], permutations: int = PERMUTATIONS, seed: int = PERMUTATION_SEED) -> float:
    array = np.asarray(values, dtype=float)
    if array.size == 0 or not np.isfinite(array).all():
        raise ContractError("invalid sign-flip input")
    observed = float(array.mean())
    rng = np.random.default_rng(seed)
    exceed = 0
    for _ in range(permutations):
        permuted = float(np.mean(array * rng.choice(np.array([-1.0, 1.0]), size=array.size)))
        exceed += permuted >= observed
    return (1 + exceed) / (permutations + 1)


def read_pair(path: Path, expected_hash: str) -> tuple[np.ndarray, np.ndarray]:
    if sha256_file(path) != expected_hash:
        raise ContractError(f"prior ledger hash mismatch: {path}")
    primary: list[float] = []
    reverse: list[float] = []
    for raw in path.read_bytes().splitlines():
        row = json.loads(raw)
        primary.append(float(row["primary_net_x1_pips"]))
        reverse.append(float(row["reverse_net_x1_pips"]))
    if len(primary) < 500 or len(primary) != len(reverse):
        raise ContractError(f"prior ledger population mismatch: {path}")
    return np.asarray(primary), np.asarray(reverse)


def load_prior_arms(root: Path) -> dict[str, np.ndarray]:
    arms: dict[str, np.ndarray] = {}
    for name, (relative, expected_hash) in PRIOR_LEDGERS.items():
        primary, reverse = read_pair(require_d(root / relative, f"{name} ledger"), expected_hash)
        arms[f"{name}_primary"] = primary
        arms[f"{name}_reverse"] = reverse
    if len(arms) != 12:
        raise ContractError("prior DSR universe is not 12 arms")
    return arms


def arm_moments(values: Sequence[float]) -> dict[str, float | int]:
    series = pd.Series(np.asarray(values, dtype=float))
    std = float(series.std(ddof=1))
    if len(series) < 3 or not math.isfinite(std) or std <= 0:
        raise ContractError("invalid DSR arm")
    return {"n": len(series), "sr": float(series.mean()) / std, "skew": float(series.skew()), "kurtosis_non_excess": float(series.kurt()) + 3.0}


def compute_dsr(trades: pd.DataFrame, prior: dict[str, np.ndarray], dsr_module: ModuleType) -> dict[str, Any]:
    arms = {name: arm_moments(values) for name, values in prior.items()}
    for arm in ARMS:
        arms[f"{SCHEMA_PREFIX}_{arm}"] = arm_moments(trades[f"{arm}_net_x1_pips"])
    if len(arms) != 16:
        raise ContractError("DSR universe is not 16 arms")
    variance = float(np.var([float(item["sr"]) for item in arms.values()], ddof=1))
    primary = arms[f"{SCHEMA_PREFIX}_flow_reversal_primary"]
    value = float(dsr_module.dsr(float(primary["sr"]), int(primary["n"]), float(primary["skew"]), float(primary["kurtosis_non_excess"]), variance, len(arms)))
    if not math.isfinite(value):
        raise ContractError("non-finite DSR")
    return {"n_trials": len(arms), "variance_sr_trials": variance, "primary_dsr": value, "arms": arms}


def summarize_trades(
    trades: pd.DataFrame,
    funnel: dict[str, int],
    prior: dict[str, np.ndarray],
    dsr_module: ModuleType,
    permutations: int = PERMUTATIONS,
) -> dict[str, Any]:
    if trades.empty:
        raise ContractError("cannot summarize empty trades")
    elapsed_weeks = float((DESIGN_END - DESIGN_START).total_seconds() / 604800.0)
    cadence = len(trades) / elapsed_weeks
    arm_metrics: dict[str, Any] = {}
    for arm in ARMS:
        pf = {
            label: profit_factor(trades[f"{arm}_net_{label}_pips"])
            for label in COSTS
        }
        expectancy = {
            label: float(trades[f"{arm}_net_{label}_pips"].mean())
            for label in COSTS
        }
        arm_metrics[arm] = {
            "gross_profit_factor": profit_factor(trades[f"{arm}_gross_pips"]),
            "gross_expectancy_pips": float(trades[f"{arm}_gross_pips"].mean()),
            "profit_factor": pf,
            "expectancy_pips": expectancy,
        }
    primary = "flow_reversal_primary"
    annual: dict[str, Any] = {}
    for year, group in trades.groupby("year"):
        values = group[f"{primary}_net_x1_pips"]
        annual[str(int(year))] = {
            "trades": int(len(group)),
            "net_pips": float(values.sum()),
            "profit_factor": profit_factor(values),
            "expectancy_pips": float(values.mean()),
        }
    positive_years = sum(item["net_pips"] > 0 for item in annual.values())
    leave_one_year_out: dict[str, Any] = {}
    for year in sorted(trades["year"].unique()):
        values = trades.loc[trades["year"].ne(year), f"{primary}_net_x1_pips"]
        leave_one_year_out[str(int(year))] = {
            "trades": int(len(values)),
            "profit_factor": profit_factor(values),
            "expectancy_pips": float(values.mean()),
        }
    positive_contributions = [max(0.0, float(item["net_pips"])) for item in annual.values()]
    positive_total = sum(positive_contributions)
    max_positive_year_share = (
        max(positive_contributions) / positive_total if positive_total > 0 else 1.0
    )
    p_value = sign_flip_p_value(trades[f"{primary}_gross_pips"], permutations=permutations)
    dsr = compute_dsr(trades, prior, dsr_module)
    x1_values = trades[f"{primary}_net_x1_pips"].to_numpy(dtype=float)
    equity = np.cumsum(x1_values)
    drawdown = equity - np.maximum.accumulate(np.r_[0.0, equity])[-len(equity):]
    primary_pf = arm_metrics[primary]["profit_factor"]
    primary_exp = arm_metrics[primary]["expectancy_pips"]
    exact = bool(
        (trades["entry_local_hhmm"] == "14:14").all()
        and (trades["exit_local_hhmm"] == "15:59").all()
        and (
            trades[f"{primary}_direction"].to_numpy()
            == -np.sign(trades["flow_signed"].to_numpy()).astype(int)
        ).all()
        and (trades["flow_signed"] != 0).all()
    )
    structural = {
        "source_population_reconciled": funnel["selected_train_dates"] == EXPECTED_TRAIN_DATES,
        "target_missingness_matches_frozen_allowlist": funnel["missing_target_dates"]
        == len(ALLOWED_MISSING_TARGET_DATES),
        "cadence_2_to_5": 2.0 <= cadence <= 5.0,
        "both_directions_ge_0_25": float((trades["direction"] == 1).mean()) >= 0.25
        and float((trades["direction"] == -1).mean()) >= 0.25,
        "exact_frozen_rule": exact,
    }
    economic = {
        "pf_x1_ge_1_30": primary_pf["x1"] is not None and primary_pf["x1"] >= 1.30,
        "pf_x1_5_ge_1_25": primary_pf["x1_5"] is not None and primary_pf["x1_5"] >= 1.25,
        "pf_x2_ge_1_00": primary_pf["x2"] is not None and primary_pf["x2"] >= 1.00,
        "expectancy_x1_gt_0": primary_exp["x1"] > 0,
        "positive_years_ge_4_of_5": len(annual) == 5 and positive_years >= 4,
        "leave_one_year_out_pf_gt_1": all(
            item["profit_factor"] is not None and item["profit_factor"] > 1.0
            for item in leave_one_year_out.values()
        ),
        "sign_flip_p_le_0_05": p_value <= 0.05,
        "dsr_ge_0_95": float(dsr["primary_dsr"]) >= 0.95,
        "max_positive_year_share_le_0_35": max_positive_year_share <= 0.35,
    }
    return {
        "trade_count": int(len(trades)),
        "first_local_date": str(trades["local_date"].min()),
        "last_local_date": str(trades["local_date"].max()),
        "elapsed_calendar_weeks": elapsed_weeks,
        "trades_per_elapsed_week": cadence,
        "long_share": float((trades["direction"] == 1).mean()),
        "short_share": float((trades["direction"] == -1).mean()),
        "flow_pressure_agreement_share": float(trades["flow_pressure_agree"].mean()),
        "funnel": funnel,
        "arms": arm_metrics,
        "annual_primary_x1": annual,
        "positive_years": positive_years,
        "leave_one_year_out_primary_x1": leave_one_year_out,
        "max_positive_year_share": max_positive_year_share,
        "sign_flip_one_sided_p_value": p_value,
        "permutation_count": permutations,
        "permutation_seed": PERMUTATION_SEED,
        "deflated_sharpe": dsr,
        "max_drawdown_pips_x1": float(drawdown.min()),
        "structural_gates": structural,
        "economic_gates": economic,
        "structural_gate_pass_count": sum(structural.values()),
        "structural_gate_total": len(structural),
        "economic_gate_pass_count": sum(economic.values()),
        "economic_gate_total": len(economic),
    }


def write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(payload)


def trade_rows(trades: pd.DataFrame) -> bytes:
    rows: list[bytes] = []
    for raw in trades.to_dict(orient="records"):
        local_date = str(raw["local_date"])
        payload: dict[str, Any] = {
            "trade_id": f"{ARTIFACT_PREFIX}-{local_date}",
            "local_date": local_date,
        }
        for key, value in raw.items():
            if key == "local_date":
                continue
            if pd.isna(value):
                payload[key] = None
            elif isinstance(value, (np.bool_, bool)):
                payload[key] = bool(value)
            elif isinstance(value, (np.integer, int)):
                payload[key] = int(value)
            elif isinstance(value, (np.floating, float)):
                payload[key] = round(float(value), 10)
            else:
                payload[key] = value
        rows.append(canonical_json(payload) + b"\n")
    return b"".join(rows)


def render_charts(trades: pd.DataFrame, metrics: dict[str, Any], root: Path) -> list[Path]:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    dates = pd.to_datetime(trades["local_date"])
    primary = "flow_reversal_primary"
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=("Cumulative PnL", "x1 drawdown"), row_heights=[0.68, 0.32])
    for label, column in (
        ("gross", f"{primary}_gross_pips"),
        ("x1 1.50 pips", f"{primary}_net_x1_pips"),
        ("x1.5 2.25 pips", f"{primary}_net_x1_5_pips"),
        ("x2 3.00 pips", f"{primary}_net_x2_pips"),
    ):
        fig.add_trace(go.Scatter(x=dates, y=trades[column].cumsum(), mode="lines", name=label), row=1, col=1)
    equity = trades[f"{primary}_net_x1_pips"].cumsum()
    drawdown = equity - equity.cummax().clip(lower=0)
    fig.add_trace(go.Scatter(x=dates, y=drawdown, mode="lines", fill="tozeroy", name="x1 drawdown"), row=2, col=1)
    fig.update_layout(title=f"{DISPLAY_TAG} TRAIN equity and drawdown | n={len(trades):,}")
    chart1 = root / CHART_NAMES[0]
    _write_plot(fig, chart1)

    annual = pd.DataFrame(metrics["annual_primary_x1"]).T.reset_index(names="year")
    fig = make_subplots(rows=1, cols=3, subplot_titles=("x1 net pips", "x1 profit factor", "x1 expectancy"))
    fig.add_trace(go.Bar(x=annual["year"], y=annual["net_pips"], name="net pips"), row=1, col=1)
    fig.add_trace(go.Bar(x=annual["year"], y=annual["profit_factor"], name="PF"), row=1, col=2)
    fig.add_hline(y=1.0, line_dash="dash", line_color="black", row=1, col=2)
    fig.add_trace(go.Bar(x=annual["year"], y=annual["expectancy_pips"], name="expectancy"), row=1, col=3)
    fig.add_hline(y=0.0, line_dash="dash", line_color="black", row=1, col=3)
    fig.update_layout(title=f"{DISPLAY_TAG} TRAIN annual stability after 1.50-pip cost")
    chart2 = root / CHART_NAMES[1]
    _write_plot(fig, chart2)

    arm_labels = list(ARMS)
    arm_pf = [metrics["arms"][arm]["profit_factor"]["x1"] for arm in arm_labels]
    arm_exp = [metrics["arms"][arm]["expectancy_pips"]["x1"] for arm in arm_labels]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Profit factor x1", "Expectancy x1 (pips)"))
    fig.add_trace(go.Bar(x=arm_labels, y=arm_pf, name="PF"), row=1, col=1)
    fig.add_hline(y=1.0, line_dash="dash", line_color="black", row=1, col=1)
    fig.add_trace(go.Bar(x=arm_labels, y=arm_exp, name="expectancy"), row=1, col=2)
    fig.add_hline(y=0.0, line_dash="dash", line_color="black", row=1, col=2)
    fig.update_layout(title=f"Four frozen arms | n={len(trades):,} each", showlegend=False)
    chart3 = root / CHART_NAMES[2]
    _write_plot(fig, chart3)

    decile_frame = trades[["flow_imbalance", "post_fix_move_pips"]].dropna().copy()
    decile_frame["decile"] = pd.qcut(decile_frame["flow_imbalance"], 10, labels=False, duplicates="drop")
    decile = decile_frame.groupby("decile").agg(
        mean_flow=("flow_imbalance", "mean"),
        mean_return=("post_fix_move_pips", "mean"),
        std_return=("post_fix_move_pips", "std"),
        n=("post_fix_move_pips", "size"),
    )
    decile["ci95"] = 1.96 * decile["std_return"] / np.sqrt(decile["n"])
    fig = go.Figure(go.Scatter(x=decile["mean_flow"], y=decile["mean_return"], error_y={"type": "data", "array": decile["ci95"]}, mode="lines+markers"))
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    fig.update_layout(title="Diagnostic only: flow-imbalance deciles vs raw post-fix return (no threshold authority)", xaxis_title="Mean signed-flow imbalance", yaxis_title="Mean raw post-fix EURUSD move (pips)")
    chart4 = root / CHART_NAMES[3]
    _write_plot(fig, chart4)

    funnel = metrics["funnel"]
    funnel_labels = ["Selected", "Non-empty", "Nonzero flow", "Exact target", "Trades"]
    funnel_values = [
        funnel["selected_train_dates"],
        funnel["selected_train_dates"] - funnel["source_empty_dates"],
        funnel["selected_train_dates"] - funnel["source_empty_dates"] - funnel["zero_signed_flow_dates"],
        funnel["selected_train_dates"] - funnel["missing_target_dates"],
        funnel["trades"],
    ]
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("Signal funnel", "Signed flow", "Holding return", "Primary x1 PnL"),
    )
    fig.add_trace(go.Funnel(y=funnel_labels, x=funnel_values, name="count"), row=1, col=1)
    fig.add_trace(go.Histogram(x=trades["flow_signed"], nbinsx=45, name="flow"), row=1, col=2)
    fig.add_trace(go.Histogram(x=trades["post_fix_move_pips"], nbinsx=45, name="raw return"), row=2, col=1)
    fig.add_trace(go.Histogram(x=trades[f"{primary}_net_x1_pips"], nbinsx=45, name="x1 pnl"), row=2, col=2)
    fig.update_layout(title=f"{DISPLAY_TAG} TRAIN signal and distribution controls | trades={len(trades):,}", showlegend=False)
    chart5 = root / CHART_NAMES[4]
    _write_plot(fig, chart5)
    return [chart1, chart2, chart3, chart4, chart5]


def _write_plot(fig: Any, path: Path) -> None:
    fig.update_layout(
        template="plotly_white",
        font={"family": "Arial", "size": 12},
        margin={"l": 60, "r": 30, "t": 90, "b": 65},
        legend={"orientation": "h", "y": 1.08, "x": 0},
    )
    fig.write_image(str(path), width=1500, height=850, scale=1.25)


def execute(root: Path) -> Path:
    root = require_d(root, "workspace")
    authority = validate_authority(root)
    feature_path = require_d(root / FEATURE_REL, "source features")
    summary_path = require_d(root / SOURCE_SUMMARY_REL, "source summary")
    artifact_manifest_path = require_d(root / SOURCE_ARTIFACT_MANIFEST_REL, "source artifact manifest")
    if sha256_file(artifact_manifest_path) != authority["artifact_manifest"]:
        raise ContractError("source artifact manifest hash mismatch")
    evidence = require_d(root / EVIDENCE_ROOT_REL, "evidence root")
    if evidence.exists():
        raise ContractError("one-shot evidence root already exists")
    evidence.mkdir(parents=True)
    started = evidence / "attempt_started.json"
    write_new(
        started,
        canonical_json(
            {
                "schema_version": f"{SCHEMA_PREFIX}_attempt_started.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "started_at_utc": utc_now(),
                "plan_sha256": PLAN_SHA256,
                "registry_row_sha256": authority["registry_row_sha256"],
                "evaluator_base_sha256": authority["evaluator_base_sha256"],
                "evaluator_file_sha256": authority["evaluator_file_sha256"],
                "test_sha256": authority["test_sha256"],
                "source_feature_sha256": authority["feature"],
                "source_artifact_manifest_sha256": authority["artifact_manifest"],
                "validation_outcomes_opened": False,
                "holdout_outcomes_opened": False,
            }
        )
        + b"\n",
    )
    run_log = evidence / "run_log.jsonl"
    write_new(run_log, canonical_json({"event": "attempt_started", "at_utc": utc_now()}) + b"\n")

    features = load_source_features(
        feature_path,
        authority["feature"],
        summary_path,
        authority["summary"],
    )
    signal = load_signal_ledger(root / SIGNAL_LEDGER_REL)
    targets = project_train_targets(load_eurusd(root))
    trades, funnel = build_trades(features, signal, targets)
    dsr_module = load_module(require_d(root / DSR_REL, "DSR"), DSR_SHA256, f"{SCHEMA_PREFIX}_dsr")
    prior = load_prior_arms(root)
    metrics = summarize_trades(trades, funnel, prior, dsr_module)
    if metrics["structural_gate_pass_count"] < metrics["structural_gate_total"]:
        verdict = VERDICT_STRUCTURAL
    elif metrics["economic_gate_pass_count"] == metrics["economic_gate_total"]:
        verdict = VERDICT_PASS
    else:
        verdict = VERDICT_KILL

    ledger = evidence / "trades.jsonl"
    write_new(ledger, trade_rows(trades))
    charts = render_charts(trades, metrics, evidence)
    log_triage = evidence / "log_triage.json"
    write_new(
        log_triage,
        canonical_json(
            {
                "schema_version": f"{SCHEMA_PREFIX}_log_triage.v1",
                "fatal_errors": 0,
                "warnings": 0,
                "attempt_completed": True,
                "validation_outcomes_opened": False,
                "holdout_outcomes_opened": False,
            }
        )
        + b"\n",
    )
    with run_log.open("ab") as handle:
        handle.write(
            canonical_json(
                {
                    "event": "attempt_completed",
                    "at_utc": utc_now(),
                    "verdict": verdict,
                    "trades": len(trades),
                }
            )
            + b"\n"
        )
    terminal = evidence / "train_economic_terminal.json"
    terminal_payload = {
        "schema_version": f"{SCHEMA_PREFIX}_train_economic_terminal.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "attempt_id": ATTEMPT_ID,
        "completed_at_utc": utc_now(),
        "verdict": verdict,
        "engineering_valid": verdict != VERDICT_STRUCTURAL,
        "economic_edge_evaluated": verdict != VERDICT_STRUCTURAL,
        "plan_path": PLAN_REL,
        "plan_sha256": PLAN_SHA256,
        "registry_row_sha256": authority["registry_row_sha256"],
        "evaluator_path": EVALUATOR_REL,
        "evaluator_base_sha256": authority["evaluator_base_sha256"],
        "evaluator_file_sha256": authority["evaluator_file_sha256"],
        "test_path": TEST_REL,
        "test_sha256": authority["test_sha256"],
        "source_feature_path": FEATURE_REL,
        "source_feature_sha256": authority["feature"],
        "source_summary_path": SOURCE_SUMMARY_REL,
        "source_summary_sha256": authority["summary"],
        "source_artifact_manifest_path": SOURCE_ARTIFACT_MANIFEST_REL,
        "source_artifact_manifest_sha256": authority["artifact_manifest"],
        "signal_ledger_path": SIGNAL_LEDGER_REL,
        "signal_ledger_sha256": SIGNAL_LEDGER_SHA256,
        "dataset_parquet_path": PARQUET_REL,
        "dataset_parquet_sha256": PARQUET_SHA256,
        "dataset_manifest_path": MANIFEST_REL,
        "dataset_manifest_sha256": MANIFEST_SHA256,
        "canonical_dsr_path": DSR_REL,
        "canonical_dsr_sha256": DSR_SHA256,
        "prior_ledgers": {
            name: {"path": relative, "sha256": expected}
            for name, (relative, expected) in PRIOR_LEDGERS.items()
        },
        "attempt_started_sha256": sha256_file(started),
        "trades_path": str(ledger.relative_to(root)).replace("\\", "/"),
        "trades_sha256": sha256_file(ledger),
        "run_log_sha256": sha256_file(run_log),
        "log_triage_sha256": sha256_file(log_triage),
        "charts": [
            {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in charts
        ],
        "metrics": metrics,
        "forbidden_counters": {
            "validation_outcomes_opened": False,
            "holdout_outcomes_opened": False,
            "mt5_launches": 0,
            "mql5_files_created": 0,
            "model0_runs": 0,
            "optimization_trials": 0,
            "orders_submitted": 0,
            "paper_trading": False,
            "live_trading": False,
        },
        "authority_after_verdict": {
            "fresh_validation_successor_may_be_preregistered": verdict == VERDICT_PASS,
            "validation_authorized": False,
            "holdout_authorized": False,
            "mql5_authorized": False,
            "model0_authorized": False,
            "optimization_authorized": False,
            "promotion_eligible": False,
            "paper_trading_authorized": False,
            "live_trading_authorized": False,
        },
    }
    write_new(terminal, canonical_json(terminal_payload) + b"\n")
    artifact_manifest = evidence / "artifact_manifest.json"
    artifact_paths = [started, ledger, run_log, log_triage, terminal, *charts]
    write_new(
        artifact_manifest,
        canonical_json(
            {
                "schema_version": f"{SCHEMA_PREFIX}_artifact_manifest.v1",
                "hypothesis_id": HYPOTHESIS_ID,
                "attempt_id": ATTEMPT_ID,
                "generated_at_utc": utc_now(),
                "artifacts": [
                    {
                        "path": str(path.relative_to(root)).replace("\\", "/"),
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                    for path in artifact_paths
                ],
            }
        )
        + b"\n",
    )
    return terminal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=workspace_from_source())
    args = parser.parse_args()
    try:
        terminal = execute(args.workspace.resolve())
    except ContractError as exc:
        print(f"{ARTIFACT_PREFIX}_ERROR {exc}", file=sys.stderr)
        return 2
    payload = json.loads(terminal.read_text(encoding="utf-8"))
    metrics = payload["metrics"]
    pf_x1 = metrics["arms"]["flow_reversal_primary"]["profit_factor"]["x1"]
    print(
        f"{ARTIFACT_PREFIX}_RESULT verdict={payload['verdict']} "
        f"trades={metrics['trade_count']} pf_x1={pf_x1} "
        f"economic_gates={metrics['economic_gate_pass_count']}/{metrics['economic_gate_total']}"
    )
    print(f"TERMINAL {terminal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
