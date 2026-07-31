#!/usr/bin/env python3
"""Deterministic synthetic math probe for HYP-PTR-T1-QAWAP-HVG-M5-001.

This runner intentionally uses no market data, no MT5 process and no trading
outcomes. Canonical mode follows the frozen population counts; use --smoke for
bounded tests and implementation checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import scipy
from scipy.optimize import minimize_scalar


HYPOTHESIS_ID = "HYP-PTR-T1-QAWAP-HVG-M5-001"
SCHEMA_VERSION = "alphafactory.synthetic_math_probe.v1"
EXPECTED_PLAN_SHA256 = "1127F4419EE098793E076C40017202CDFFFAB118482AE45A922A747A7E1B6ED4"
REPAIR_TASK_PACKET_PATH: Path | None = Path(__file__).resolve().with_name(
    f"{HYPOTHESIS_ID}_PROBE_REPAIR_01.json"
)
EXPECTED_REPAIR_TASK_PACKET_SHA256: str | None = "4C832510D2690D4020F732B11AC0EBDAE360C3A4678734C34CD9D2A7DEB4E7EB"
BASE_SEED = 20260731
OBS_N = 256
HVG_N = 64
BURN_IN = 4096
LW_M = 32
LW_BOUNDS = (-0.45, 0.45)
LW_FREQS = 2.0 * np.pi * np.arange(1, LW_M + 1, dtype=float) / OBS_N
LW_EXPO = np.exp(-1j * np.outer(LW_FREQS, np.arange(OBS_N, dtype=float)))
LW_MEAN_LOG_LAMBDA = float(np.mean(np.log(LW_FREQS)))
DFA_SCALES = (8, 16, 32, 64)
DFA_DESIGNS = {
    scale: np.column_stack([np.ones(scale, dtype=float), np.arange(scale, dtype=float)])
    for scale in DFA_SCALES
}
DFA_LOG_SCALES = np.log(np.asarray(DFA_SCALES, dtype=float))
LO_LAGS = (1, 3, 6, 12)
NULL_FAMILIES = (
    "IID_GAUSSIAN",
    "AR_NEG_03",
    "AR_POS_03",
    "AR_POS_06",
    "ARMA_11",
    "GARCH_0590",
    "VOLATILITY_BREAK",
    "MEAN_BREAK",
    "BLOCK_PERMUTED_AR06",
)
ALT_D_BY_FAMILY = {"FGN_H060": 0.10, "FGN_H065": 0.15, "FGN_H070": 0.20}
CANONICAL_NULL_CALIBRATION = 10_000
CANONICAL_NULL_VERIFICATION = 10_000
CANONICAL_ALT_VERIFICATION = 10_000
SMOKE_NULL_CALIBRATION = 18
SMOKE_NULL_VERIFICATION = 18
SMOKE_ALT_VERIFICATION = 18
INVALID_RATE_MAX = 0.001
Z_ONE_SIDED_95 = 1.6448536269514722
EXIT_PASS = 0
EXIT_FAIL_CAPABILITY = 2
EXIT_INVALID_REPAIR = 3
VERDICT_PASS = "PROBE_PASS_TO_P6"
VERDICT_FAIL = "PROBE_FAIL_CAPABILITY"
VERDICT_INVALID = "PROBE_INVALID_REPAIR"
PLAN_PATH = Path(__file__).resolve().with_name(f"{HYPOTHESIS_ID}_PROBE_PLAN.md")
INVALID_REASON_CODES = (
    "LOCAL_WHITTLE_BOUNDARY_OR_OPTIMIZER",
    "LOCAL_WHITTLE_PERIODOGRAM",
    "DFA",
    "LO_HAC",
    "DAVIES_HARTE_EIGEN",
    "INPUT_CONTRACT",
    "OTHER_NUMERIC",
)


class InvalidReplicate(ValueError):
    """Raised when a single synthetic path violates the frozen estimator contract."""

    def __init__(self, code: str, detail: str):
        if code not in INVALID_REASON_CODES:
            code = "OTHER_NUMERIC"
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class PopulationCounts:
    null_calibration: int
    null_verification: int
    alt_verification: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def json_ready(value):
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite value cannot be serialized to probe JSON")
        return value
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    return value


def stable_json_dumps(payload: dict) -> str:
    return json.dumps(json_ready(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"


def write_json(path: Path, payload: dict) -> str:
    text = stable_json_dumps(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return sha256_bytes(text.encode("utf-8"))


def assert_series_contract(x: np.ndarray, n: int = OBS_N) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.shape != (n,) or not np.all(np.isfinite(arr)):
        raise InvalidReplicate("INPUT_CONTRACT", "non-finite or inconsistent array length")
    if float(np.var(arr)) <= 0.0:
        raise InvalidReplicate("INPUT_CONTRACT", "zero variance input")
    return arr


def local_whittle_d(x: np.ndarray) -> float:
    arr = assert_series_contract(x)
    demeaned = arr - float(np.mean(arr))
    periodogram = np.abs(LW_EXPO @ demeaned) ** 2 / (2.0 * np.pi * OBS_N)
    if np.any(periodogram <= 0.0) or not np.all(np.isfinite(periodogram)):
        raise InvalidReplicate("LOCAL_WHITTLE_PERIODOGRAM", "non-positive local Whittle periodogram")

    def objective(d: float) -> float:
        weighted = periodogram * np.power(LW_FREQS, 2.0 * d)
        mean_weighted = float(np.mean(weighted))
        if mean_weighted <= 0.0 or not math.isfinite(mean_weighted):
            return math.inf
        return math.log(mean_weighted) - 2.0 * d * LW_MEAN_LOG_LAMBDA

    result = minimize_scalar(
        objective,
        bounds=LW_BOUNDS,
        method="bounded",
        options={"xatol": 1e-8, "maxiter": 500},
    )
    d_hat = float(result.x)
    if (
        not result.success
        or not math.isfinite(d_hat)
        or d_hat <= LW_BOUNDS[0] + 1e-7
        or d_hat >= LW_BOUNDS[1] - 1e-7
    ):
        raise InvalidReplicate("LOCAL_WHITTLE_BOUNDARY_OR_OPTIMIZER", "failed or boundary local Whittle optimization")
    return d_hat


def dfa1_h(x: np.ndarray) -> float:
    arr = assert_series_contract(x)
    profile = np.cumsum(arr - float(np.mean(arr)))
    flucts: list[float] = []
    for scale in DFA_SCALES:
        residual_squares: list[np.ndarray] = []
        design = DFA_DESIGNS[scale]
        for start in range(0, OBS_N - scale + 1, scale):
            segment = profile[start : start + scale]
            beta, *_ = np.linalg.lstsq(design, segment, rcond=None)
            residual_squares.append((segment - design @ beta) ** 2)
        for end in range(OBS_N, scale - 1, -scale):
            segment = profile[end - scale : end]
            beta, *_ = np.linalg.lstsq(design, segment, rcond=None)
            residual_squares.append((segment - design @ beta) ** 2)
        if not residual_squares:
            raise InvalidReplicate("DFA", "missing DFA boxes")
        f_s = math.sqrt(float(np.mean(np.concatenate(residual_squares))))
        if f_s <= 0.0 or not math.isfinite(f_s):
            raise InvalidReplicate("DFA", "non-positive DFA fluctuation")
        flucts.append(f_s)
    slope, _ = np.polyfit(DFA_LOG_SCALES, np.log(flucts), 1)
    h = float(slope)
    if not math.isfinite(h):
        raise InvalidReplicate("DFA", "non-finite DFA slope")
    return h


def lo_modified_rs(x: np.ndarray) -> dict[str, float]:
    arr = assert_series_contract(x)
    demeaned = arr - float(np.mean(arr))
    cumulative = np.cumsum(demeaned)
    series_range = float(np.max(cumulative) - np.min(cumulative))
    out: dict[str, float] = {}
    for q in LO_LAGS:
        gamma0 = float(np.dot(demeaned, demeaned) / OBS_N)
        hac = gamma0
        for lag in range(1, q + 1):
            cov = float(np.dot(demeaned[lag:], demeaned[:-lag]) / OBS_N)
            hac += 2.0 * (1.0 - lag / (q + 1.0)) * cov
        if hac <= 0.0 or not math.isfinite(hac):
            raise InvalidReplicate("LO_HAC", "non-positive Lo HAC variance")
        stat = series_range / math.sqrt(hac * OBS_N)
        if not math.isfinite(stat):
            raise InvalidReplicate("LO_HAC", "non-finite Lo statistic")
        out[f"lo_q{q}"] = stat
    return out


def memory_metrics(x: np.ndarray) -> dict[str, float]:
    d_hat = local_whittle_d(x)
    h_dfa = dfa1_h(x)
    return {"d_hat": d_hat, "h_dfa": h_dfa, **lo_modified_rs(x)}


def hvg_edges(values: Iterable[float]) -> list[tuple[int, int]]:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.ndim != 1 or not np.all(np.isfinite(arr)):
        raise InvalidReplicate("INPUT_CONTRACT", "invalid HVG input")
    edges: list[tuple[int, int]] = []
    n = len(arr)
    for i in range(n - 1):
        for j in range(i + 1, n):
            if j == i + 1:
                visible = True
            else:
                visible = bool(np.all(arr[i + 1 : j] < min(arr[i], arr[j])))
            if visible:
                edges.append((i, j))
    return edges


def _histogram_with_pseudocount(values: np.ndarray, bins: int) -> np.ndarray:
    counts = np.bincount(values.astype(int), minlength=bins).astype(float)[:bins]
    counts += 0.5
    return counts / float(np.sum(counts))


def _motif_mask4(values: np.ndarray) -> int:
    mask = 0
    bit = 0
    edge_set = set(hvg_edges(values))
    for i in range(3):
        for j in range(i + 1, 4):
            if (i, j) in edge_set:
                mask |= 1 << bit
            bit += 1
    return mask


def hvg_features(values: Iterable[float]) -> dict[str, float]:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.shape != (HVG_N,) or not np.all(np.isfinite(arr)):
        raise InvalidReplicate("INPUT_CONTRACT", "HVG requires exactly 64 finite observations")
    edges = hvg_edges(arr)
    out_degree = np.zeros(HVG_N, dtype=int)
    in_degree = np.zeros(HVG_N, dtype=int)
    total_degree = np.zeros(HVG_N, dtype=int)
    for i, j in edges:
        out_degree[i] += 1
        in_degree[j] += 1
        total_degree[i] += 1
        total_degree[j] += 1
    out_hist = _histogram_with_pseudocount(out_degree, HVG_N)
    in_hist = _histogram_with_pseudocount(in_degree, HVG_N)
    total_hist = _histogram_with_pseudocount(total_degree, HVG_N)
    degree_kl = float(np.sum(out_hist * np.log(out_hist / in_hist)))
    degree_entropy = float(-np.sum(total_hist * np.log(total_hist)) / math.log(HVG_N))
    fwd_counts = np.full(64, 0.5, dtype=float)
    rev_counts = np.full(64, 0.5, dtype=float)
    for start in range(0, HVG_N - 3):
        window = arr[start : start + 4]
        fwd_counts[_motif_mask4(window)] += 1.0
        rev_counts[_motif_mask4(window[::-1])] += 1.0
    fwd = fwd_counts / float(np.sum(fwd_counts))
    rev = rev_counts / float(np.sum(rev_counts))
    motif4_imbalance = float(0.5 * np.sum(np.abs(fwd - rev)))
    features = {
        "degree_kl": degree_kl,
        "degree_entropy": degree_entropy,
        "motif4_imbalance": motif4_imbalance,
    }
    if not all(math.isfinite(v) for v in features.values()):
        raise InvalidReplicate("OTHER_NUMERIC", "non-finite HVG feature")
    return features


def type7_quantile(values: np.ndarray, q: float) -> float:
    arr = np.asarray(values, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        raise ValueError("cannot compute quantile from empty finite array")
    return float(np.quantile(arr, q, method="linear"))


def wilson_upper(k: int, n: int, z: float = Z_ONE_SIDED_95) -> float:
    if n <= 0:
        raise ValueError("Wilson denominator must be positive")
    p = k / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) / n) + (z * z / (4.0 * n * n)))
    return float((center + margin) / denom)


def wilson_lower(k: int, n: int, z: float = Z_ONE_SIDED_95) -> float:
    if n <= 0:
        raise ValueError("Wilson denominator must be positive")
    p = k / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2.0 * n)
    margin = z * math.sqrt((p * (1.0 - p) / n) + (z * z / (4.0 * n * n)))
    return float((center - margin) / denom)


def persistence_support(row: dict[str, float], criticals: dict[str, float]) -> bool:
    lo_exceeds = sum(row[f"lo_q{q}"] > criticals[f"lo_q{q}"] for q in LO_LAGS)
    return bool(
        row["d_hat"] > criticals["d_hat"]
        and row["h_dfa"] > criticals["h_dfa"]
        and abs((0.5 + row["d_hat"]) - row["h_dfa"]) <= 0.10
        and lo_exceeds >= 3
    )


def irreversible(row: dict[str, float], criticals: dict[str, float]) -> bool:
    return bool(
        row["degree_kl"] > criticals["degree_kl"]
        or row["motif4_imbalance"] > criticals["motif4_imbalance"]
    )


def family_index(family: str) -> int:
    if family in NULL_FAMILIES:
        return list(NULL_FAMILIES).index(family)
    if family in ALT_D_BY_FAMILY:
        return len(NULL_FAMILIES) + list(ALT_D_BY_FAMILY).index(family)
    raise ValueError(f"unknown synthetic family: {family}")


def absolute_population_index(stream: str, replicate: int) -> int:
    if stream == "calibration":
        return int(replicate)
    if stream == "verification":
        return CANONICAL_NULL_CALIBRATION + int(replicate)
    if stream == "alternative":
        return int(replicate)
    raise ValueError(f"unknown stream: {stream}")


def seed_sequence_for(family: str, absolute_index: int) -> np.random.SeedSequence:
    return np.random.SeedSequence(BASE_SEED, spawn_key=(family_index(family), int(absolute_index)))


def rng_for(family: str, stream: str, replicate: int) -> np.random.Generator:
    seed_sequence = seed_sequence_for(family, absolute_population_index(stream, replicate))
    return np.random.default_rng(seed_sequence)


def seed_endpoint_state(family: str, absolute_index: int) -> list[int]:
    return [int(value) for value in seed_sequence_for(family, absolute_index).generate_state(4)]


def seed_range_payload(family: str, stream: str, count: int) -> dict:
    start = absolute_population_index(stream, 0)
    stop = start + int(count)
    payload = {
        "family_index": family_index(family),
        "absolute_start_inclusive": start,
        "absolute_stop_exclusive": stop,
        "count": int(count),
        "first_child_state_u32x4": seed_endpoint_state(family, start) if count else [],
        "last_child_state_u32x4": seed_endpoint_state(family, stop - 1) if count else [],
    }
    return payload


def build_seed_ledger(counts: PopulationCounts) -> dict:
    streams: dict[str, dict] = {"null": {}, "alternative": {}}
    for family in NULL_FAMILIES:
        streams["null"][family] = {
            "calibration": seed_range_payload(family, "calibration", counts.null_calibration),
            "verification": seed_range_payload(family, "verification", counts.null_verification),
        }
    for family in ALT_D_BY_FAMILY:
        streams["alternative"][family] = {
            "verification": seed_range_payload(family, "alternative", counts.alt_verification)
        }
    payload = {
        "base_entropy": BASE_SEED,
        "spawn_key_contract": ["family_index", "absolute_population_index"],
        "canonical_null_calibration_absolute_range": [0, CANONICAL_NULL_CALIBRATION],
        "canonical_null_verification_absolute_range": [
            CANONICAL_NULL_CALIBRATION,
            CANONICAL_NULL_CALIBRATION + CANONICAL_NULL_VERIFICATION,
        ],
        "canonical_alternative_verification_absolute_range": [0, CANONICAL_ALT_VERIFICATION],
        "actual_ranges": streams,
    }
    payload["seed_ledger_sha256"] = sha256_bytes(stable_json_dumps(payload).encode("utf-8"))
    return payload


def _ar1(rng: np.random.Generator, phi: float, total: int) -> np.ndarray:
    innovations = rng.standard_normal(total)
    x = np.empty(total, dtype=float)
    x[0] = innovations[0] / math.sqrt(max(1e-12, 1.0 - phi * phi))
    for i in range(1, total):
        x[i] = phi * x[i - 1] + innovations[i]
    return x


def _arma11(rng: np.random.Generator, total: int) -> np.ndarray:
    e = rng.standard_normal(total)
    x = np.empty(total, dtype=float)
    x[0] = e[0]
    for i in range(1, total):
        x[i] = 0.40 * x[i - 1] + e[i] - 0.30 * e[i - 1]
    return x


def _garch_0590(rng: np.random.Generator, total: int) -> np.ndarray:
    e = rng.standard_normal(total)
    h = np.empty(total, dtype=float)
    x = np.empty(total, dtype=float)
    h[0] = 1.0
    x[0] = math.sqrt(h[0]) * e[0]
    for i in range(1, total):
        h[i] = 0.05 + 0.05 * x[i - 1] ** 2 + 0.90 * h[i - 1]
        x[i] = math.sqrt(h[i]) * e[i]
    return x


def davies_harte_fgn(rng: np.random.Generator, h: float, n: int, burn_in: int = BURN_IN) -> np.ndarray:
    total = n + burn_in
    k = np.arange(0, total, dtype=float)
    gamma = np.empty(total, dtype=float)
    gamma[0] = 1.0
    gamma[1:] = 0.5 * ((k[1:] + 1.0) ** (2.0 * h) - 2.0 * k[1:] ** (2.0 * h) + (k[1:] - 1.0) ** (2.0 * h))
    circulant = np.concatenate([gamma, [0.0], gamma[:0:-1]])
    eigenvalues = np.fft.fft(circulant).real
    if float(np.min(eigenvalues)) < -1e-12:
        raise InvalidReplicate("DAVIES_HARTE_EIGEN", "negative Davies-Harte circulant eigenvalue")
    eigenvalues = np.where(eigenvalues < 0.0, 0.0, eigenvalues)
    m = len(eigenvalues)
    z = np.zeros(m, dtype=complex)
    z[0] = math.sqrt(eigenvalues[0]) * rng.standard_normal()
    z[total] = math.sqrt(eigenvalues[total]) * rng.standard_normal()
    for j in range(1, total):
        a = rng.standard_normal()
        b = rng.standard_normal()
        z[j] = math.sqrt(eigenvalues[j] / 2.0) * (a + 1j * b)
        z[m - j] = np.conjugate(z[j])
    fgn = np.fft.fft(z).real / math.sqrt(m)
    return fgn[-n:]


def generate_series(family: str, rng: np.random.Generator) -> np.ndarray:
    total = OBS_N + BURN_IN
    if family == "IID_GAUSSIAN":
        observed = rng.standard_normal(OBS_N)
    elif family == "AR_NEG_03":
        observed = _ar1(rng, -0.30, total)[-OBS_N:]
    elif family == "AR_POS_03":
        observed = _ar1(rng, 0.30, total)[-OBS_N:]
    elif family == "AR_POS_06":
        observed = _ar1(rng, 0.60, total)[-OBS_N:]
    elif family == "ARMA_11":
        observed = _arma11(rng, total)[-OBS_N:]
    elif family == "GARCH_0590":
        observed = _garch_0590(rng, total)[-OBS_N:]
    elif family == "VOLATILITY_BREAK":
        observed = np.concatenate([rng.normal(0.0, 0.5, 128), rng.normal(0.0, 2.0, 128)])
    elif family == "MEAN_BREAK":
        observed = np.concatenate([rng.normal(0.0, 1.0, 128), rng.normal(0.5, 1.0, 128)])
    elif family == "BLOCK_PERMUTED_AR06":
        base = _ar1(rng, 0.60, total)[-OBS_N:]
        blocks = base.reshape(32, 8)
        observed = blocks[rng.permutation(32)].reshape(OBS_N)
    elif family in ALT_D_BY_FAMILY:
        observed = davies_harte_fgn(rng, 0.5 + ALT_D_BY_FAMILY[family], OBS_N)
    else:
        raise ValueError(f"unknown synthetic family: {family}")
    observed = np.asarray(observed, dtype=np.float64)
    observed = observed - float(np.mean(observed))
    return assert_series_contract(observed)


def evaluate_path(series: np.ndarray) -> dict[str, dict[str, float]]:
    return {"memory": memory_metrics(series), "hvg": hvg_features(series[:HVG_N])}


def collect_family(
    family: str,
    stream: str,
    count: int,
    generator: Callable[[str, np.random.Generator], np.ndarray] = generate_series,
) -> dict:
    memory_rows: list[dict[str, float]] = []
    hvg_rows: list[dict[str, float]] = []
    invalid = 0
    invalid_examples: list[str] = []
    invalid_reason_counts = {code: 0 for code in INVALID_REASON_CODES}
    invalid_reason_examples: dict[str, list[dict[str, str | int]]] = {code: [] for code in INVALID_REASON_CODES}
    for replicate in range(count):
        try:
            series = generator(family, rng_for(family, stream, replicate))
            metrics = evaluate_path(series)
            memory_rows.append(metrics["memory"])
            hvg_rows.append(metrics["hvg"])
        except InvalidReplicate as exc:
            invalid += 1
            invalid_reason_counts[exc.code] += 1
            if len(invalid_reason_examples[exc.code]) < 5:
                invalid_reason_examples[exc.code].append(
                    {"replicate_index": replicate, "absolute_population_index": absolute_population_index(stream, replicate), "detail": exc.detail}
                )
            if len(invalid_examples) < 5:
                invalid_examples.append(f"{replicate}:{exc}")
        except (FloatingPointError, ValueError, np.linalg.LinAlgError) as exc:
            invalid += 1
            invalid_reason_counts["OTHER_NUMERIC"] += 1
            if len(invalid_reason_examples["OTHER_NUMERIC"]) < 5:
                invalid_reason_examples["OTHER_NUMERIC"].append(
                    {
                        "replicate_index": replicate,
                        "absolute_population_index": absolute_population_index(stream, replicate),
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                )
            if len(invalid_examples) < 5:
                invalid_examples.append(f"{replicate}:OTHER_NUMERIC: {type(exc).__name__}: {exc}")
    return {
        "family": family,
        "stream": stream,
        "requested": count,
        "valid": len(memory_rows),
        "invalid": invalid,
        "invalid_rate": invalid / count if count else 0.0,
        "invalid_examples": invalid_examples,
        "invalid_reason_counts": invalid_reason_counts,
        "invalid_reason_examples": invalid_reason_examples,
        "memory": memory_rows,
        "hvg": hvg_rows,
    }


def aggregate_invalid_observability(family_payloads: Iterable[dict]) -> dict:
    by_family_stream = {}
    totals = {code: 0 for code in INVALID_REASON_CODES}
    for payload in family_payloads:
        key = f"{payload['family']}:{payload['stream']}"
        counts = {code: int(payload["invalid_reason_counts"].get(code, 0)) for code in INVALID_REASON_CODES}
        for code, count in counts.items():
            totals[code] += count
        by_family_stream[key] = {
            "requested_denominator": int(payload["requested"]),
            "valid": int(payload["valid"]),
            "invalid": int(payload["invalid"]),
            "invalid_rate": float(payload["invalid_rate"]),
            "reason_counts": counts,
            "bounded_examples_by_reason": {
                code: payload["invalid_reason_examples"].get(code, []) for code in INVALID_REASON_CODES
            },
        }
    return {"reason_codes": list(INVALID_REASON_CODES), "total_reason_counts": totals, "by_family_stream": by_family_stream}


def repair_task_packet_binding() -> dict:
    if REPAIR_TASK_PACKET_PATH is None or EXPECTED_REPAIR_TASK_PACKET_SHA256 is None:
        return {
            "status": "NOT_BOUND_NO_PACKET_PROVIDED",
            "proposed_constants": {
                "REPAIR_TASK_PACKET_PATH": str(Path(__file__).resolve().with_name(f"{HYPOTHESIS_ID}_REPAIR_TASK_PACKET.md")),
                "EXPECTED_REPAIR_TASK_PACKET_SHA256": "<sha256 after parent creates packet>",
            },
        }
    actual = sha256_path(REPAIR_TASK_PACKET_PATH)
    if actual != EXPECTED_REPAIR_TASK_PACKET_SHA256:
        raise RuntimeError(f"repair task packet SHA256 binding failed: {actual}")
    return {
        "status": "BOUND",
        "path": str(REPAIR_TASK_PACKET_PATH),
        "sha256": actual,
        "expected_sha256": EXPECTED_REPAIR_TASK_PACKET_SHA256,
    }


def columns(rows: list[dict[str, float]], keys: Iterable[str]) -> dict[str, np.ndarray]:
    return {key: np.asarray([row[key] for row in rows], dtype=float) for key in keys}


def summarize_numeric(values: np.ndarray) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        raise ValueError("empty summary array")
    return {
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "std": float(np.std(arr)),
        "p05": type7_quantile(arr, 0.05),
        "p95": type7_quantile(arr, 0.95),
    }


def build_criticals(calibration: dict[str, dict]) -> tuple[dict[str, float], dict[str, float], dict]:
    memory_keys = ["d_hat", "h_dfa", *[f"lo_q{q}" for q in LO_LAGS]]
    hvg_keys = ["degree_kl", "motif4_imbalance"]
    per_family: dict[str, dict] = {}
    memory_common: dict[str, float] = {}
    hvg_common: dict[str, float] = {}
    for family, payload in calibration.items():
        mem_cols = columns(payload["memory"], memory_keys)
        hvg_cols = columns(payload["hvg"], hvg_keys)
        per_family[family] = {
            "memory_p95": {key: type7_quantile(mem_cols[key], 0.95) for key in memory_keys},
            "hvg_p975": {key: type7_quantile(hvg_cols[key], 0.975) for key in hvg_keys},
        }
    for key in memory_keys:
        memory_common[key] = max(per_family[family]["memory_p95"][key] for family in NULL_FAMILIES)
    for key in hvg_keys:
        hvg_common[key] = max(per_family[family]["hvg_p975"][key] for family in NULL_FAMILIES)
    return memory_common, hvg_common, per_family


def true_range_series(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> list[float]:
    out: list[float] = []
    for i in range(len(high)):
        if i == 0:
            out.append(float(high[i] - low[i]))
        else:
            out.append(float(max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))))
    return out


def session_qawap_fixture(
    timestamps_utc: list[str],
    typical_price: list[float],
    tick_volume: list[float],
    bar_present: list[bool],
) -> dict:
    values: list[float | None] = []
    actions: list[str] = []
    numerator = 0.0
    denominator = 0.0
    current_date: str | None = None
    for timestamp, typical, volume, present in zip(
        timestamps_utc, typical_price, tick_volume, bar_present, strict=True
    ):
        row_date = timestamp.split("T", 1)[0]
        if row_date != current_date:
            current_date = row_date
            numerator = 0.0
            denominator = 0.0
        if not present:
            values.append(None)
            actions.append("REJECT_MISSING_BAR_NO_STATE_UPDATE")
            continue
        if volume <= 0.0:
            values.append(None)
            actions.append("REJECT_ZERO_VOLUME_NO_STATE_UPDATE")
            continue
        numerator += typical * volume
        denominator += volume
        values.append(numerator / denominator)
        actions.append("ACCEPT_UPDATE")
    return {
        "values": values,
        "actions": actions,
        "session_reset_rule": "reset accumulator before processing first UTC-date/00:00 row",
        "rejected_bar_rule": "missing bars and zero-volume bars emit null and do not update accumulator",
    }


def reference_fixtures() -> dict:
    timestamps = [
        "2026-07-30T23:50:00Z",
        "2026-07-30T23:55:00Z",
        "2026-07-31T00:00:00Z",
        "2026-07-31T00:05:00Z",
        "2026-07-31T00:25:00Z",
        "2026-07-31T00:30:00Z",
        "2026-07-31T00:35:00Z",
        "2026-07-31T00:40:00Z",
        "2026-07-31T00:45:00Z",
        "2026-07-31T00:50:00Z",
        "2026-07-31T00:55:00Z",
        "2026-07-31T01:00:00Z",
        "2026-07-31T01:05:00Z",
        "2026-07-31T01:10:00Z",
        "2026-07-31T01:15:00Z",
    ]
    open_ = np.array([100.0, 100.4, 100.8, 100.6, 102.4, 102.2, 102.0, 102.1, 102.5, 102.4, 102.2, 102.1, 102.3, 102.4, 102.6])
    high = np.array([100.6, 100.9, 101.0, 100.8, 102.8, 102.5, 102.4, 102.6, 102.7, 102.8, 102.6, 102.5, 102.8, 102.9, 103.0])
    low = np.array([99.8, 100.2, 100.5, 100.1, 102.0, 101.9, 101.8, 101.9, 102.2, 102.0, 101.9, 101.8, 102.0, 102.2, 102.4])
    close = np.array([100.4, 100.7, 100.6, 100.2, 102.2, 102.0, 102.1, 102.5, 102.4, 102.2, 102.1, 102.3, 102.4, 102.6, 102.8])
    tick_volume = np.array([10.0, 12.0, 9.0, 0.0, 11.0, 13.0, 8.0, 15.0, 14.0, 10.0, 9.0, 7.0, 6.0, 5.0, 4.0])
    bar_present = [True, True, True, True, False, True, True, True, True, True, True, True, True, True, True]
    typical = (high + low + close) / 3.0
    qawap = session_qawap_fixture(timestamps, typical.tolist(), tick_volume.tolist(), bar_present)
    tr = true_range_series(high, low, close)
    atr14 = float(np.mean(tr[:14]))
    atr14_next = float((atr14 * 13.0 + tr[14]) / 14.0)
    equal = np.ones(HVG_N, dtype=float)
    prefix = np.sin(np.arange(HVG_N, dtype=float) / 7.0) + 0.01 * np.arange(HVG_N)
    future_tail = np.array([99.0, -99.0, 50.0], dtype=float)
    future = np.concatenate([prefix, future_tail])
    equal_edges = hvg_edges(equal)
    prefix_edges = hvg_edges(prefix)
    future_edges = hvg_edges(future)
    future_prefix_edges = [(i, j) for i, j in future_edges if i < HVG_N and j < HVG_N]
    payload = {
        "timestamps_utc": timestamps,
        "ohlc": {"open": open_.tolist(), "high": high.tolist(), "low": low.tolist(), "close": close.tolist()},
        "tick_volume": tick_volume.tolist(),
        "typical_price": typical.tolist(),
        "flags": {
            "utc_0000_reset_index": 2,
            "zero_tick_volume_indices": [3],
            "missing_bar_indices": [4],
            "bar_present": bar_present,
            "gap_minutes": [5, 5, 5, 20, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            "post_gap_return_excluded_index": 5,
            "post_gap_positive_volume_qawap_update_index": 5,
        },
        "post_gap_return_excluded": True,
        "qawap": qawap,
        "atr14": {"true_range": tr, "first_14_mean": atr14, "outputs": [None] * 13 + [atr14, atr14_next]},
        "hvg": {
            "equal_vector": equal.tolist(),
            "equal_edges": equal_edges,
            "equal_features": hvg_features(equal),
            "prefix_vector": prefix.tolist(),
            "prefix_edges": prefix_edges,
            "prefix_features": hvg_features(prefix),
            "future_tail": future_tail.tolist(),
            "future_vector": future.tolist(),
            "future_prefix_edges": future_prefix_edges,
            "future_prefix_features": hvg_features(future[:HVG_N]),
        },
        "directional_candidates": {
            "long": {"direction": 1, "decision_index": 12},
            "short": {"direction": -1, "decision_index": 13},
            "abstain": {"direction": 0, "decision_index": 14},
        },
    }
    payload["hashes"] = {
        "hvg_prefix_edges_sha256": sha256_bytes(stable_json_dumps({"edges": prefix_edges}).encode("utf-8")),
        "hvg_future_prefix_edges_sha256": sha256_bytes(stable_json_dumps({"edges": future_prefix_edges}).encode("utf-8")),
        "atr_sha256": sha256_bytes(stable_json_dumps(payload["atr14"]).encode("utf-8")),
        "qawap_sha256": sha256_bytes(stable_json_dumps(payload["qawap"]).encode("utf-8")),
    }
    payload["fixtures_sha256"] = sha256_bytes(stable_json_dumps({k: v for k, v in payload.items() if k != "fixtures_sha256"}).encode("utf-8"))
    return payload


def prefix_causality_check() -> dict:
    rng = rng_for("IID_GAUSSIAN", "verification", 999_999)
    prefix = rng.standard_normal(HVG_N)
    appended = np.concatenate([prefix, rng.standard_normal(16)])
    prefix_edges = hvg_edges(prefix)
    appended_prefix_edges = [(i, j) for i, j in hvg_edges(appended) if i < HVG_N and j < HVG_N]
    prefix_features = hvg_features(prefix)
    appended_features = hvg_features(appended[:HVG_N])
    return {
        "edge_sets_equal": prefix_edges == appended_prefix_edges,
        "features_equal": prefix_features == appended_features,
        "prefix_edge_count": len(prefix_edges),
    }


def evaluate_gates(
    calibration: dict[str, dict],
    null_verification: dict[str, dict],
    alternatives: dict[str, dict],
    memory_criticals: dict[str, float],
    hvg_criticals: dict[str, float],
) -> dict:
    invalid_by_family = {
        f"{payload['family']}:{payload['stream']}": payload["invalid_rate"]
        for payload in [*calibration.values(), *null_verification.values(), *alternatives.values()]
    }
    invalid_gate = all(rate <= INVALID_RATE_MAX for rate in invalid_by_family.values())
    null_rates = {}
    for family, payload in null_verification.items():
        n = payload["requested"]
        supports = sum(persistence_support(row, memory_criticals) for row in payload["memory"])
        irrevers = sum(irreversible(row, hvg_criticals) for row in payload["hvg"])
        null_rates[family] = {
            "memory_false_support": supports,
            "memory_false_support_rate_denominator_all_requested": supports / n,
            "memory_wilson95_upper": wilson_upper(supports, n),
            "hvg_irreversible": irrevers,
            "hvg_irreversible_rate_denominator_all_requested": irrevers / n,
            "hvg_wilson95_upper": wilson_upper(irrevers, n),
        }
    alt_rates = {}
    for family, payload in alternatives.items():
        n = payload["requested"]
        supports = sum(persistence_support(row, memory_criticals) for row in payload["memory"])
        mem_cols = columns(payload["memory"], ["d_hat", "h_dfa", *[f"lo_q{q}" for q in LO_LAGS]])
        target_d = ALT_D_BY_FAMILY[family]
        alt_rates[family] = {
            "target_d": target_d,
            "support": supports,
            "support_rate_denominator_all_requested": supports / n,
            "support_wilson95_lower": wilson_lower(supports, n),
            "median_bias_d_hat": float(np.median(mem_cols["d_hat"]) - target_d),
            "median_bias_dfa_implied_d": float(np.median(mem_cols["h_dfa"] - 0.5) - target_d),
            "abs_median_bias_d_hat": abs(float(np.median(mem_cols["d_hat"]) - target_d)),
            "abs_median_bias_dfa_implied_d": abs(float(np.median(mem_cols["h_dfa"] - 0.5) - target_d)),
            "lo_exceedance_rates": {
                f"lo_q{q}": float(np.mean(mem_cols[f"lo_q{q}"] > memory_criticals[f"lo_q{q}"]))
                for q in LO_LAGS
            },
        }
    hvg_variance = {}
    for family, payload in null_verification.items():
        hvg_cols = columns(payload["hvg"], ["degree_kl", "degree_entropy", "motif4_imbalance"])
        hvg_variance[family] = {key: float(np.var(values)) for key, values in hvg_cols.items()}
    causality = prefix_causality_check()
    gates = {
        "invalid_replicate_rate_lte_0_001_all_families": invalid_gate,
        "memory_null_wilson_upper_lte_0_05_all": all(row["memory_wilson95_upper"] <= 0.05 for row in null_rates.values()),
        "memory_fgn_d010_wilson_lower_gte_0_80": alt_rates["FGN_H060"]["support_wilson95_lower"] >= 0.80,
        "memory_alt_abs_median_bias_lte_0_05_all": all(
            row["abs_median_bias_d_hat"] <= 0.05 and row["abs_median_bias_dfa_implied_d"] <= 0.05
            for row in alt_rates.values()
        ),
        "hvg_null_wilson_upper_lte_0_05_all": all(row["hvg_wilson95_upper"] <= 0.05 for row in null_rates.values()),
        "hvg_feature_variance_nonzero_all": all(
            all(value > 0.0 and math.isfinite(value) for value in row.values()) for row in hvg_variance.values()
        ),
        "hvg_prefix_causality_pass": bool(causality["edge_sets_equal"] and causality["features_equal"]),
    }
    statistical_gate_names = [name for name in gates if not name.startswith("invalid_")]
    if not invalid_gate:
        verdict = VERDICT_INVALID
    elif all(gates[name] for name in statistical_gate_names):
        verdict = VERDICT_PASS
    else:
        verdict = VERDICT_FAIL
    return {
        "gates": gates,
        "verdict": verdict,
        "invalid_by_family": invalid_by_family,
        "null_rates": null_rates,
        "alt_rates": alt_rates,
        "hvg_variance": hvg_variance,
        "causality": causality,
    }


def run_probe(counts: PopulationCounts) -> dict:
    plan_sha256 = sha256_path(PLAN_PATH)
    if plan_sha256 != EXPECTED_PLAN_SHA256:
        raise RuntimeError(f"plan SHA256 binding failed: {plan_sha256}")
    repair_binding = repair_task_packet_binding()
    runner_sha256 = sha256_path(Path(__file__).resolve())
    calibration = {
        family: collect_family(family, "calibration", counts.null_calibration)
        for family in NULL_FAMILIES
    }
    null_verification = {
        family: collect_family(family, "verification", counts.null_verification)
        for family in NULL_FAMILIES
    }
    alternatives = {
        family: collect_family(family, "alternative", counts.alt_verification)
        for family in ALT_D_BY_FAMILY
    }
    all_family_payloads = [*calibration.values(), *null_verification.values(), *alternatives.values()]
    memory_criticals, hvg_criticals, per_family_criticals = build_criticals(calibration)
    gate_payload = evaluate_gates(calibration, null_verification, alternatives, memory_criticals, hvg_criticals)
    memory_keys = ["d_hat", "h_dfa", *[f"lo_q{q}" for q in LO_LAGS]]
    hvg_keys = ["degree_kl", "degree_entropy", "motif4_imbalance"]
    summaries = {}
    for family, payload in {**null_verification, **alternatives}.items():
        summaries[family] = {
            "memory": {key: summarize_numeric(columns(payload["memory"], [key])[key]) for key in memory_keys},
            "hvg": {key: summarize_numeric(columns(payload["hvg"], [key])[key]) for key in hvg_keys},
            "counts": {
                "requested": payload["requested"],
                "valid": payload["valid"],
                "invalid": payload["invalid"],
                "invalid_rate": payload["invalid_rate"],
            },
        }
    fixtures = reference_fixtures()
    return {
        "schema_version": SCHEMA_VERSION,
        "hypothesis_id": HYPOTHESIS_ID,
        "mode": "canonical"
        if counts == PopulationCounts(CANONICAL_NULL_CALIBRATION, CANONICAL_NULL_VERIFICATION, CANONICAL_ALT_VERIFICATION)
        else "smoke",
        "authorized_surface": "synthetic_estimator_and_causality_probe_only",
        "prohibited_surfaces": ["market_data", "MT5", "trading_backtest", "PnL", "economic_selection"],
        "population_counts": {
            "null_calibration_per_family": counts.null_calibration,
            "null_verification_per_family": counts.null_verification,
            "alt_verification_per_family": counts.alt_verification,
            "canonical_null_calibration_per_family": CANONICAL_NULL_CALIBRATION,
            "canonical_null_verification_per_family": CANONICAL_NULL_VERIFICATION,
            "canonical_alt_verification_per_family": CANONICAL_ALT_VERIFICATION,
        },
        "hash_bindings": {
            "plan_path": str(PLAN_PATH),
            "plan_sha256": plan_sha256,
            "expected_plan_sha256": EXPECTED_PLAN_SHA256,
            "runner_path": str(Path(__file__).resolve()),
            "runner_sha256": runner_sha256,
            "repair_task_packet": repair_binding,
        },
        "seed_contract": build_seed_ledger(counts),
        "estimator_contract": {
            "obs_n": OBS_N,
            "hvg_n": HVG_N,
            "burn_in": BURN_IN,
            "local_whittle_m": LW_M,
            "dfa_scales": list(DFA_SCALES),
            "lo_lags": list(LO_LAGS),
            "invalid_rate_max": INVALID_RATE_MAX,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "critical_values": {
            "memory_common_p95_max_over_nulls": memory_criticals,
            "hvg_common_p975_max_over_nulls": hvg_criticals,
            "per_null_family": per_family_criticals,
        },
        "family_summaries": summaries,
        "gate_results": gate_payload,
        "invalid_replicate_observability": aggregate_invalid_observability(all_family_payloads),
        "reference_fixtures": fixtures,
        "promotion_eligible": False,
        "source_build_authorized": gate_payload["verdict"] == VERDICT_PASS,
        "model0_authorized": False,
        "economic_trial_viewed": False,
        "verdict": gate_payload["verdict"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Explicit JSON artifact output path.")
    parser.add_argument("--smoke", action="store_true", help="Run bounded smoke population instead of canonical counts.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    counts = (
        PopulationCounts(SMOKE_NULL_CALIBRATION, SMOKE_NULL_VERIFICATION, SMOKE_ALT_VERIFICATION)
        if args.smoke
        else PopulationCounts(CANONICAL_NULL_CALIBRATION, CANONICAL_NULL_VERIFICATION, CANONICAL_ALT_VERIFICATION)
    )
    try:
        payload = run_probe(counts)
    except Exception as exc:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "hypothesis_id": HYPOTHESIS_ID,
            "mode": "smoke" if args.smoke else "canonical",
            "verdict": VERDICT_INVALID,
            "error": f"{type(exc).__name__}: {exc}",
            "promotion_eligible": False,
            "source_build_authorized": False,
            "model0_authorized": False,
            "economic_trial_viewed": False,
        }
    artifact_sha256 = write_json(args.output, payload)
    print(stable_json_dumps({"verdict": payload["verdict"], "artifact": str(args.output.resolve()), "sha256": artifact_sha256}), end="")
    if payload["verdict"] == VERDICT_PASS:
        return EXIT_PASS
    if payload["verdict"] == VERDICT_FAIL:
        return EXIT_FAIL_CAPABILITY
    return EXIT_INVALID_REPAIR


if __name__ == "__main__":
    raise SystemExit(main())
