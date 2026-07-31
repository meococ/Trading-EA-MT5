#!/usr/bin/env python3
"""Fail-closed loader for preregistered, aligned EA-variant return evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA = "alphafactory_aligned_variant_manifest.v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789ABCDEF" for c in value)


def _resolve(raw: Any, manifest_path: Path) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("evidence path must be a non-empty string")
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (manifest_path.parent / path).resolve()


def _verified_file(node: dict[str, Any], manifest_path: Path, label: str) -> Path:
    path = _resolve(node.get("path"), manifest_path)
    expected = node.get("sha256")
    if not path.is_file():
        raise ValueError(f"{label} file is missing: {path}")
    if not _is_sha256(expected):
        raise ValueError(f"{label} sha256 must be uppercase SHA256")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{label} SHA256 mismatch")
    return path


def _verified_run_file(
    run_payload: dict[str, Any], run_path: Path, path_key: str, hash_key: str, label: str
) -> Path:
    raw_path = run_payload.get(path_key)
    expected = run_payload.get(hash_key)
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError(f"{label} missing {path_key}")
    path = Path(raw_path)
    path = path.resolve() if path.is_absolute() else (run_path.parent / path).resolve()
    if not path.is_file():
        raise ValueError(f"{label} {path_key} is missing: {path}")
    if not _is_sha256(expected):
        raise ValueError(f"{label} {hash_key} must be uppercase SHA256")
    if sha256_file(path) != expected:
        raise ValueError(f"{label} {path_key} SHA256 mismatch")
    return path


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


@dataclass(frozen=True)
class AlignedVariantEvidence:
    manifest_path: Path
    manifest_sha256: str
    hypothesis_id: str
    source_sha256: str
    expected_variant_ids: list[str]
    baseline_variant_id: str
    robustness_variant_ids: list[str]
    dates: list[str]
    series: dict[str, list[float]]
    matrix_sha256: str
    minimum_variant_mean_net_r: float
    minimum_robustness_pass_ratio: float
    wfa_windows: int
    cscv_slices: int
    cscv_max_combinations: int
    white_reality_bootstrap: int
    white_reality_block_length: int
    random_seed: int

    def promotion_metadata(self) -> dict[str, Any]:
        return {
            "variant_manifest": str(self.manifest_path),
            "variant_manifest_sha256": self.manifest_sha256,
            "aligned_matrix_sha256": self.matrix_sha256,
            "aligned_rows": len(self.dates),
            "aligned_start": self.dates[0] if self.dates else None,
            "aligned_end": self.dates[-1] if self.dates else None,
            "expected_variant_ids": self.expected_variant_ids,
            "robustness_variant_ids": self.robustness_variant_ids,
            "hypothesis_id": self.hypothesis_id,
            "source_sha256": self.source_sha256,
            "alignment_missing_values": 0,
            "value_semantics": "net_r",
            "analysis_settings": {
                "wfa_windows": self.wfa_windows,
                "cscv_slices": self.cscv_slices,
                "cscv_max_combinations": self.cscv_max_combinations,
                "white_reality_bootstrap": self.white_reality_bootstrap,
                "white_reality_block_length": self.white_reality_block_length,
                "random_seed": self.random_seed,
            },
        }


def load_aligned_variant_evidence(manifest_path: Path) -> AlignedVariantEvidence:
    manifest_path = manifest_path.resolve()
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"variant manifest cannot be parsed: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA:
        raise ValueError(f"variant manifest schema_version must be {SCHEMA}")
    for key in ("frozen_pre_outcome", "full_tried_family", "selection_rule_frozen"):
        if payload.get(key) is not True:
            raise ValueError(f"variant manifest {key} must be true")
    if payload.get("value_semantics") != "net_r":
        raise ValueError("variant manifest value_semantics must be net_r")
    if payload.get("time_column") != "exit_time" or payload.get("value_column") != "net_r":
        raise ValueError("promotion matrix requires exit_time and net_r columns")

    hypothesis_id = str(payload.get("hypothesis_id") or "").strip()
    source_sha256 = payload.get("source_sha256")
    if not hypothesis_id:
        raise ValueError("variant manifest hypothesis_id is required")
    if not _is_sha256(source_sha256):
        raise ValueError("variant manifest source_sha256 must be uppercase SHA256")
    prereg = payload.get("preregistration")
    if not isinstance(prereg, dict):
        raise ValueError("variant manifest preregistration must be an object")
    _verified_file(prereg, manifest_path, "preregistration")

    expected = payload.get("expected_variant_ids")
    if not isinstance(expected, list) or len(expected) < 2 or not all(
        isinstance(item, str) and item.strip() for item in expected
    ):
        raise ValueError("expected_variant_ids must contain at least two non-empty IDs")
    expected_ids = [str(item) for item in expected]
    if len(set(expected_ids)) != len(expected_ids):
        raise ValueError("expected_variant_ids must be unique")
    baseline = str(payload.get("baseline_variant_id") or "").strip()
    if baseline not in expected_ids:
        raise ValueError("baseline_variant_id must be in expected_variant_ids")
    robustness_ids = payload.get("robustness_variant_ids")
    if not isinstance(robustness_ids, list) or len(robustness_ids) < 2 or not all(
        isinstance(item, str) and item.strip() for item in robustness_ids
    ):
        raise ValueError("robustness_variant_ids must contain at least two IDs")
    robustness_ids = [str(item) for item in robustness_ids]
    if len(set(robustness_ids)) != len(robustness_ids) or not set(robustness_ids) <= set(expected_ids):
        raise ValueError("robustness_variant_ids must be a unique subset of expected_variant_ids")

    variants = payload.get("variants")
    if not isinstance(variants, list):
        raise ValueError("variants must be an array")
    by_id: dict[str, dict[str, Any]] = {}
    for row in variants:
        if not isinstance(row, dict):
            raise ValueError("variant row must be an object")
        variant_id = str(row.get("variant_id") or "").strip()
        if not variant_id or variant_id in by_id:
            raise ValueError("variant_id must be non-empty and unique")
        by_id[variant_id] = row
    if set(by_id) != set(expected_ids):
        raise ValueError("variant rows must exactly match expected_variant_ids")

    min_trades = payload.get("minimum_trades_per_variant", 20)
    if not isinstance(min_trades, int) or min_trades < 1:
        raise ValueError("minimum_trades_per_variant must be a positive integer")

    daily_by_variant: dict[str, dict[str, float]] = {}
    declared_csvs: set[Path] = set()
    for variant_id in expected_ids:
        row = by_id[variant_id]
        trades_node = row.get("trades_csv")
        run_node = row.get("run_manifest")
        if not isinstance(trades_node, dict) or not isinstance(run_node, dict):
            raise ValueError(f"{variant_id} requires trades_csv and run_manifest bindings")
        trades_path = _verified_file(trades_node, manifest_path, f"{variant_id}.trades_csv")
        run_path = _verified_file(run_node, manifest_path, f"{variant_id}.run_manifest")
        declared_csvs.add(trades_path)
        try:
            run_payload = json.loads(run_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"{variant_id} run_manifest cannot be parsed: {exc}") from exc
        if not isinstance(run_payload, dict):
            raise ValueError(f"{variant_id} run_manifest must be an object")
        if str(run_payload.get("hypothesis_id") or "") != hypothesis_id:
            raise ValueError(f"{variant_id} run_manifest hypothesis_id mismatch")
        run_variant = str(run_payload.get("variant_id") or run_payload.get("variant_tag") or "")
        if run_variant != variant_id:
            raise ValueError(f"{variant_id} run_manifest variant identity mismatch")
        if run_payload.get("model") != 0:
            raise ValueError(f"{variant_id} run_manifest model must be 0")
        if str(run_payload.get("source_sha256") or "").upper() != source_sha256:
            raise ValueError(f"{variant_id} run_manifest source_sha256 mismatch")
        if run_payload.get("schema_version") != "alphafactory_run_manifest.v2":
            raise ValueError(f"{variant_id} run_manifest must use alphafactory_run_manifest.v2")
        _verified_run_file(
            run_payload, run_path, "source_snapshot", "source_sha256", variant_id
        )
        _verified_run_file(
            run_payload, run_path, "ex5_snapshot", "ex5_sha256", variant_id
        )
        _verified_run_file(
            run_payload, run_path, "report_path", "report_sha256", variant_id
        )

        daily: dict[str, float] = {}
        rows_seen = 0
        with trades_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "exit_time" not in reader.fieldnames or "net_r" not in reader.fieldnames:
                raise ValueError(f"{variant_id} trades_csv requires exit_time and net_r")
            for trade in reader:
                try:
                    timestamp = _parse_time(str(trade["exit_time"]))
                    value = float(trade["net_r"])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"{variant_id} has invalid exit_time/net_r row") from exc
                if not math.isfinite(value):
                    raise ValueError(f"{variant_id} net_r must be finite")
                day = timestamp.date().isoformat()
                daily[day] = daily.get(day, 0.0) + value
                rows_seen += 1
        if rows_seen < min_trades:
            raise ValueError(f"{variant_id} has {rows_seen} trades; minimum is {min_trades}")
        daily_by_variant[variant_id] = daily

    discovered_csvs = {path.resolve() for path in manifest_path.parent.rglob("*.csv")}
    if discovered_csvs != declared_csvs:
        extra = sorted(str(path) for path in discovered_csvs - declared_csvs)
        missing = sorted(str(path) for path in declared_csvs - discovered_csvs)
        raise ValueError(f"variant CSV closure mismatch extra={extra} missing={missing}")

    dates = sorted({day for daily in daily_by_variant.values() for day in daily})
    if len(dates) < 20:
        raise ValueError("aligned variant matrix requires at least 20 distinct dates")
    series = {
        variant_id: [daily_by_variant[variant_id].get(day, 0.0) for day in dates]
        for variant_id in expected_ids
    }
    matrix_payload = {"dates": dates, "series": series}
    matrix_sha = hashlib.sha256(
        json.dumps(matrix_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()

    min_mean = payload.get("minimum_variant_mean_net_r", 0.0)
    min_pass_ratio = payload.get("minimum_robustness_pass_ratio", 0.60)
    if not isinstance(min_mean, (int, float)) or not math.isfinite(float(min_mean)):
        raise ValueError("minimum_variant_mean_net_r must be finite")
    if not isinstance(min_pass_ratio, (int, float)) or not 0.0 <= float(min_pass_ratio) <= 1.0:
        raise ValueError("minimum_robustness_pass_ratio must be within [0,1]")

    settings = payload.get("analysis_settings")
    if not isinstance(settings, dict):
        raise ValueError("analysis_settings must be an object frozen before outcomes")

    def positive_int(name: str, minimum: int) -> int:
        value = settings.get(name)
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f"analysis_settings.{name} must be an integer >= {minimum}")
        return value

    wfa_windows = positive_int("wfa_windows", 2)
    cscv_slices = positive_int("cscv_slices", 4)
    if cscv_slices % 2:
        raise ValueError("analysis_settings.cscv_slices must be even")
    cscv_max_combinations = positive_int("cscv_max_combinations", 1)
    white_reality_bootstrap = positive_int("white_reality_bootstrap", 200)
    white_reality_block_length = positive_int("white_reality_block_length", 2)
    random_seed = settings.get("random_seed")
    if not isinstance(random_seed, int) or isinstance(random_seed, bool):
        raise ValueError("analysis_settings.random_seed must be an integer")
    if white_reality_block_length > len(dates):
        raise ValueError("white_reality_block_length cannot exceed aligned date count")

    return AlignedVariantEvidence(
        manifest_path=manifest_path,
        manifest_sha256=sha256_file(manifest_path),
        hypothesis_id=hypothesis_id,
        source_sha256=source_sha256,
        expected_variant_ids=expected_ids,
        baseline_variant_id=baseline,
        robustness_variant_ids=robustness_ids,
        dates=dates,
        series=series,
        matrix_sha256=matrix_sha,
        minimum_variant_mean_net_r=float(min_mean),
        minimum_robustness_pass_ratio=float(min_pass_ratio),
        wfa_windows=wfa_windows,
        cscv_slices=cscv_slices,
        cscv_max_combinations=cscv_max_combinations,
        white_reality_bootstrap=white_reality_bootstrap,
        white_reality_block_length=white_reality_block_length,
        random_seed=random_seed,
    )
