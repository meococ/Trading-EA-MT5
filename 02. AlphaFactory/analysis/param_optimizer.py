#!/usr/bin/env python3
"""Fail-closed MT5 optimization importer, DSR audit, and real parameter surface.

This module deliberately does not perturb a single backtest's P/L. Every
surface cell must come from an exported optimization pass. The resulting
artifact is one anti-overfit gate input; it never grants promotion by itself.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "alphafactory_optimization_audit.v1"
RECEIPT_SCHEMA_VERSION = "alphafactory_optimization_receipt.v1"
KNOWN_METRICS = {
    "pass",
    "result",
    "profit",
    "expected payoff",
    "profit factor",
    "recovery factor",
    "sharpe ratio",
    "custom",
    "equity dd %",
    "equity dd",
    "balance dd %",
    "balance dd",
    "trades",
}


class OptimizationPass:
    def __init__(self, pass_id: str, values: dict[str, Any]) -> None:
        self.pass_id = pass_id
        self.values = values


class OptimizationReport:
    def __init__(
        self,
        *,
        path: Path,
        sha256: str,
        report_format: str,
        headers: Sequence[str],
        rows: Sequence[OptimizationPass],
    ) -> None:
        self.path = path
        self.sha256 = sha256
        self.format = report_format
        self.headers = tuple(headers)
        self.rows = tuple(rows)

    @property
    def total_passes(self) -> int:
        return len(self.rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decode_text(raw: bytes) -> str:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    if raw and raw.count(b"\x00") / len(raw) > 0.20:
        even_nuls = raw[0::2].count(b"\x00")
        odd_nuls = raw[1::2].count(b"\x00")
        encoding = "utf-16-be" if even_nuls > odd_nuls else "utf-16-le"
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError as exc:
            raise ValueError("BOM-less UTF-16 optimization report is malformed") from exc
    for encoding in ("utf-8", "utf-16-le", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("optimization report encoding is unsupported")


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _cell_text(cell: ET.Element) -> str:
    for node in cell.iter():
        if _local_name(node.tag) == "Data":
            return (node.text or "").strip()
    return ""


def _spreadsheet_rows(raw: bytes) -> list[list[str]]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ValueError(f"invalid optimization XML: {exc}") from exc

    def read_table(table: ET.Element) -> list[list[str]]:
        rows: list[list[str]] = []
        for row in (node for node in table if _local_name(node.tag) == "Row"):
            values: list[str] = []
            for cell in (node for node in row if _local_name(node.tag) == "Cell"):
                index_raw = next(
                    (value for key, value in cell.attrib.items() if _local_name(key) == "Index"),
                    "",
                )
                if index_raw:
                    try:
                        target_index = int(index_raw) - 1
                    except ValueError as exc:
                        raise ValueError(f"invalid SpreadsheetML cell index: {index_raw}") from exc
                    while len(values) < target_index:
                        values.append("")
                values.append(_cell_text(cell))
            if any(value.strip() for value in values):
                rows.append(values)
        return rows

    candidates: list[tuple[str, list[list[str]]]] = []
    for worksheet in (node for node in root.iter() if _local_name(node.tag) == "Worksheet"):
        name = next(
            (value for key, value in worksheet.attrib.items() if _local_name(key) == "Name"),
            "",
        ).strip()
        for table in (node for node in worksheet if _local_name(node.tag) == "Table"):
            rows = read_table(table)
            if rows and any("pass" in {value.strip().lower() for value in row} for row in rows):
                candidates.append((name, rows))

    preferred = [item for item in candidates if item[0].strip().lower() == "optimization results"]
    if len(preferred) == 1:
        return preferred[0][1]
    if len(preferred) > 1:
        raise ValueError("SpreadsheetML contains multiple Optimization Results worksheets")
    non_forward = [item for item in candidates if "forward" not in item[0].strip().lower()]
    if len(non_forward) == 1:
        return non_forward[0][1]
    if not candidates:
        raise ValueError("SpreadsheetML optimization table with a Pass column was not found")
    names = [name or "<unnamed>" for name, _ in candidates]
    raise ValueError(f"SpreadsheetML optimization worksheet is ambiguous: {names}")


def _delimited_rows(raw: bytes) -> list[list[str]]:
    text = _decode_text(raw)
    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = "\t" if "\t" in sample else (";" if ";" in sample else ",")
    return [row for row in csv.reader(text.splitlines(), delimiter=delimiter) if any(cell.strip() for cell in row)]


def _coerce(value: str) -> Any:
    stripped = value.strip()
    if stripped == "":
        return None
    numeric = stripped.replace("\u00a0", "").replace(" ", "")
    if numeric.endswith("%"):
        numeric = numeric[:-1]
    if "," in numeric and "." not in numeric and numeric.count(",") == 1:
        numeric = numeric.replace(",", ".")
    elif "," in numeric and "." in numeric:
        if numeric.rfind(",") > numeric.rfind("."):
            numeric = numeric.replace(".", "").replace(",", ".")
        else:
            numeric = numeric.replace(",", "")
    try:
        parsed = float(numeric)
    except ValueError:
        return stripped
    return parsed if math.isfinite(parsed) else None


def _parse_rows(path: Path, raw: bytes, report_format: str, rows: list[list[str]]) -> OptimizationReport:
    header_index = -1
    for index, row in enumerate(rows):
        if "pass" in {cell.strip().lower() for cell in row}:
            header_index = index
            break
    if header_index < 0:
        raise ValueError("optimization report has no Pass header")

    headers = [cell.strip() for cell in rows[header_index]]
    if any(not header for header in headers):
        raise ValueError("optimization report contains an empty header")
    if len(set(headers)) != len(headers):
        raise ValueError("optimization report contains duplicate headers")
    pass_header = next(header for header in headers if header.lower() == "pass")

    parsed_rows: list[OptimizationPass] = []
    seen_pass_ids: set[str] = set()
    for raw_row in rows[header_index + 1 :]:
        padded = raw_row + [""] * max(0, len(headers) - len(raw_row))
        values = {header: _coerce(padded[index]) for index, header in enumerate(headers)}
        raw_pass_id = values.get(pass_header)
        if raw_pass_id is None:
            raise ValueError("optimization report contains a non-empty row without Pass identity")
        if isinstance(raw_pass_id, float) and raw_pass_id.is_integer():
            pass_id = str(int(raw_pass_id))
        else:
            pass_id = str(raw_pass_id).strip()
        if not pass_id or not pass_id.isdigit():
            raise ValueError(f"optimization pass id must be a non-negative integer: {pass_id!r}")
        if pass_id in seen_pass_ids:
            raise ValueError(f"duplicate optimization pass id: {pass_id}")
        seen_pass_ids.add(pass_id)
        parsed_rows.append(OptimizationPass(pass_id, values))

    if not parsed_rows:
        raise ValueError("optimization report contains no pass rows")
    return OptimizationReport(
        path=path.resolve(),
        sha256=_sha256(path),
        report_format=report_format,
        headers=headers,
        rows=parsed_rows,
    )


def parse_optimization_report(path: Path | str) -> OptimizationReport:
    report_path = Path(path)
    if not report_path.is_file():
        raise ValueError(f"optimization report not found: {report_path}")
    raw = report_path.read_bytes()
    stripped = raw.lstrip()
    if report_path.suffix.lower() in {".xml", ".htm", ".html"} or stripped.startswith(b"<"):
        rows = _spreadsheet_rows(raw)
        report_format = "spreadsheetml"
    else:
        rows = _delimited_rows(raw)
        report_format = "delimited"
    return _parse_rows(report_path, raw, report_format, rows)


def _as_finite_float(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{label} must be finite")
    return parsed


def _connected_components(cells: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    remaining = set(cells)
    components: list[list[tuple[int, int]]] = []
    while remaining:
        seed = remaining.pop()
        stack = [seed]
        component = [seed]
        while stack:
            row, col = stack.pop()
            for neighbor in ((row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=lambda item: (-len(item), item))


def build_parameter_surface(
    rows: Sequence[OptimizationPass],
    *,
    param1: str,
    param2: str,
    metric: str,
    plateau_fraction: float = 0.90,
    lower_is_better: bool = False,
) -> dict[str, Any]:
    if not 0.0 < plateau_fraction <= 1.0:
        raise ValueError("plateau_fraction must be in (0, 1]")
    observations: dict[tuple[float, float], list[float]] = {}
    for row in rows:
        if param1 not in row.values or param2 not in row.values or metric not in row.values:
            raise ValueError(f"optimization report is missing one of: {param1}, {param2}, {metric}")
        p1 = _as_finite_float(row.values[param1], f"pass {row.pass_id} {param1}")
        p2 = _as_finite_float(row.values[param2], f"pass {row.pass_id} {param2}")
        value = _as_finite_float(row.values[metric], f"pass {row.pass_id} {metric}")
        observations.setdefault((p1, p2), []).append(value)
    if not observations:
        raise ValueError("no complete numeric parameter cells were found")
    duplicate_cells = {
        f"{p1}|{p2}": len(values)
        for (p1, p2), values in observations.items()
        if len(values) > 1
    }
    if duplicate_cells:
        raise ValueError(
            "2D surface is ambiguous because other optimizer axes vary within cells; "
            f"export a frozen slice first: {duplicate_cells}"
        )

    p1_values = sorted({key[0] for key in observations})
    p2_values = sorted({key[1] for key in observations})
    matrix: list[list[float | None]] = []
    for p1 in p1_values:
        matrix.append(
            [
                statistics.median(observations[(p1, p2)]) if (p1, p2) in observations else None
                for p2 in p2_values
            ]
        )

    populated = [value for row in matrix for value in row if value is not None]
    best_value = min(populated) if lower_is_better else max(populated)
    tolerance = max(abs(best_value), 1e-12) * (1.0 - plateau_fraction)
    threshold = best_value + tolerance if lower_is_better else best_value - tolerance
    plateau_cells: set[tuple[int, int]] = set()
    for row_index, matrix_row in enumerate(matrix):
        for col_index, value in enumerate(matrix_row):
            if value is None:
                continue
            if (lower_is_better and value <= threshold) or (not lower_is_better and value >= threshold):
                plateau_cells.add((row_index, col_index))
    components = _connected_components(plateau_cells)

    best_indices = [
        (row_index, col_index)
        for row_index, matrix_row in enumerate(matrix)
        for col_index, value in enumerate(matrix_row)
        if value == best_value
    ]
    best_row, best_col = best_indices[0]
    return {
        "surface_kind": "actual_mt5_optimization_passes",
        "param1": param1,
        "param2": param2,
        "metric": metric,
        "lower_is_better": lower_is_better,
        "grid_shape": [len(p1_values), len(p2_values)],
        "parameter_values": {param1: p1_values, param2: p2_values},
        "matrix": matrix,
        "populated_cells": len(observations),
        "missing_cells": len(p1_values) * len(p2_values) - len(observations),
        "duplicate_cells": duplicate_cells,
        "best": {
            param1: p1_values[best_row],
            param2: p2_values[best_col],
            "value": best_value,
            "is_grid_edge": best_row in {0, len(p1_values) - 1}
            or best_col in {0, len(p2_values) - 1},
        },
        "plateau": {
            "fraction_of_best": plateau_fraction,
            "threshold": threshold,
            "total_cells": len(plateau_cells),
            "component_count": len(components),
            "largest_component_cells": len(components[0]) if components else 0,
            "largest_component_fraction": (
                len(components[0]) / len(observations) if components else 0.0
            ),
            "components": [
                [
                    {param1: p1_values[row], param2: p2_values[col], "value": matrix[row][col]}
                    for row, col in component
                ]
                for component in components
            ],
        },
        "stability_claim": "DIAGNOSTIC_UNTIL_REPORT_RECEIPT_AND_TRIAL_CLOSURE_ARE_BOUND",
    }


def _load_returns(path: Path, column: str) -> list[float]:
    if not path.is_file():
        raise ValueError(f"selected returns CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"selected returns CSV is missing column: {column}")
        values = [_as_finite_float(row.get(column), column) for row in reader]
    if len(values) < 3:
        raise ValueError("selected returns need at least three observations")
    return values


def _verified_file_reference(
    payload: Mapping[str, Any],
    *,
    path_field: str,
    hash_field: str,
    receipt_path: Path,
) -> dict[str, str]:
    raw_path = str(payload.get(path_field) or "").strip()
    expected_hash = str(payload.get(hash_field) or "").strip().lower()
    if not raw_path or len(expected_hash) != 64:
        raise ValueError(f"optimization receipt requires {path_field} and {hash_field}")
    target = Path(raw_path)
    if not target.is_absolute():
        target = receipt_path.parent / target
    target = target.resolve()
    if not target.is_file():
        raise ValueError(f"optimization receipt file is missing: {target}")
    actual_hash = _sha256(target)
    if actual_hash != expected_hash:
        raise ValueError(
            f"optimization receipt {hash_field} mismatch: expected {expected_hash}, actual {actual_hash}"
        )
    return {"path": str(target), "sha256": actual_hash}


def load_optimization_receipt(path: Path | str) -> dict[str, Any]:
    receipt_path = Path(path)
    if not receipt_path.is_file():
        raise ValueError(f"optimization receipt not found: {receipt_path}")
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid optimization receipt JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ValueError(f"optimization receipt schema_version must be {RECEIPT_SCHEMA_VERSION}")
    if payload.get("frozen_pre_outcome") is not True:
        raise ValueError("optimization receipt must be frozen_pre_outcome=true")
    if payload.get("selection_rule_frozen") is not True:
        raise ValueError("optimization receipt must freeze the selection rule before outcomes")
    try:
        expected_total_trials = int(payload.get("expected_total_trials"))
    except (TypeError, ValueError) as exc:
        raise ValueError("optimization receipt expected_total_trials must be an integer") from exc
    if expected_total_trials <= 0:
        raise ValueError("optimization receipt expected_total_trials must be positive")
    report_format = str(payload.get("report_format") or "").strip()
    if report_format not in {"delimited", "spreadsheetml"}:
        raise ValueError("optimization receipt report_format must be delimited or spreadsheetml")
    sharpe_column = str(payload.get("sharpe_column") or "").strip()
    if not sharpe_column:
        raise ValueError("optimization receipt sharpe_column is required")
    if payload.get("sr_semantics") != "per_trade_net_r":
        raise ValueError("optimization receipt sr_semantics must be per_trade_net_r for DSR")
    required_strings = (
        "hypothesis_id",
        "run_id",
        "selection_metric",
        "selected_pass_id",
        "selected_returns_column",
    )
    normalized_strings: dict[str, str] = {}
    for field in required_strings:
        value = str(payload.get(field) or "").strip()
        if not value or value.startswith("<"):
            raise ValueError(f"optimization receipt {field} is required and must be resolved")
        normalized_strings[field] = value
    selection_direction = str(payload.get("selection_direction") or "").strip().lower()
    if selection_direction not in {"max", "min"}:
        raise ValueError("optimization receipt selection_direction must be max or min")
    if payload.get("selection_tie_breaker") != "lowest_pass_id":
        raise ValueError("optimization receipt selection_tie_breaker must be lowest_pass_id")
    parameter_axes = payload.get("parameter_axes")
    if (
        not isinstance(parameter_axes, list)
        or not parameter_axes
        or any(not isinstance(item, str) or not item.strip() for item in parameter_axes)
        or len(set(parameter_axes)) != len(parameter_axes)
    ):
        raise ValueError("optimization receipt parameter_axes must be a non-empty unique string list")
    try:
        cumulative_trials_before = int(payload.get("cumulative_trials_before"))
        selected_returns_row_count = int(payload.get("selected_returns_row_count"))
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "optimization receipt cumulative_trials_before and selected_returns_row_count "
            "must be integers"
        ) from exc
    if cumulative_trials_before < 0:
        raise ValueError("optimization receipt cumulative_trials_before must be non-negative")
    if selected_returns_row_count < 3:
        raise ValueError("optimization receipt selected_returns_row_count must be at least 3")
    source = _verified_file_reference(
        payload,
        path_field="source_path",
        hash_field="source_sha256",
        receipt_path=receipt_path,
    )
    config = _verified_file_reference(
        payload,
        path_field="config_path",
        hash_field="config_sha256",
        receipt_path=receipt_path,
    )
    report = _verified_file_reference(
        payload,
        path_field="report_path",
        hash_field="report_sha256",
        receipt_path=receipt_path,
    )
    selected_returns = _verified_file_reference(
        payload,
        path_field="selected_returns_path",
        hash_field="selected_returns_sha256",
        receipt_path=receipt_path,
    )
    bound_returns = _load_returns(
        Path(selected_returns["path"]), normalized_strings["selected_returns_column"]
    )
    if len(bound_returns) != selected_returns_row_count:
        raise ValueError(
            "optimization receipt selected_returns_row_count mismatch: "
            f"declared {selected_returns_row_count}, observed {len(bound_returns)}"
        )
    return {
        **payload,
        **normalized_strings,
        "expected_total_trials": expected_total_trials,
        "cumulative_trials_before": cumulative_trials_before,
        "selected_returns_row_count": selected_returns_row_count,
        "selection_direction": selection_direction,
        "parameter_axes": [str(item).strip() for item in parameter_axes],
        "report_format": report_format,
        "sharpe_column": sharpe_column,
        "source": source,
        "config": config,
        "report": report,
        "selected_returns": selected_returns,
        "receipt_path": str(receipt_path.resolve()),
        "receipt_sha256": _sha256(receipt_path),
        "receipt_integrity_verified": True,
    }


def sample_sharpe(values: Sequence[float]) -> float:
    if len(values) < 2:
        raise ValueError("Sharpe requires at least two observations")
    std = statistics.stdev(values)
    if std <= 0.0:
        raise ValueError("Sharpe is undefined for zero-variance returns")
    return statistics.mean(values) / std


def _distribution_shape(values: Sequence[float]) -> tuple[float, float]:
    mean_value = statistics.mean(values)
    centered = [value - mean_value for value in values]
    m2 = sum(value * value for value in centered) / len(centered)
    if m2 <= 0.0:
        raise ValueError("return distribution has zero variance")
    m3 = sum(value**3 for value in centered) / len(centered)
    m4 = sum(value**4 for value in centered) / len(centered)
    skew = m3 / (m2**1.5)
    non_excess_kurtosis = m4 / (m2 * m2)
    return skew, non_excess_kurtosis


def _canonical_dsr(
    sr: float,
    n_obs: int,
    skew: float,
    kurt: float,
    var_sr_trials: float,
    n_trials: int,
) -> float:
    dsr_path = Path(__file__).resolve().parents[1] / "tools" / "research" / "dsr.py"
    spec = importlib.util.spec_from_file_location("alphafactory_canonical_dsr", dsr_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"canonical DSR module cannot be loaded: {dsr_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return float(module.dsr(sr, n_obs, skew, kurt, var_sr_trials, n_trials))


def build_optimization_audit(
    report: OptimizationReport,
    *,
    expected_total_trials: int | None = None,
    selected_pass_id: str | None = None,
    selected_returns_path: Path | str | None = None,
    returns_column: str = "net_r",
    sharpe_column: str = "Custom",
    sr_semantics: str = "unspecified",
    selection_frozen: bool = False,
    sr_match_tolerance: float = 1e-6,
    optimization_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if optimization_receipt is not None:
        if optimization_receipt.get("receipt_integrity_verified") is not True:
            raise ValueError("optimization_receipt must be verified by load_optimization_receipt")
        receipt_trials = int(optimization_receipt["expected_total_trials"])
        if expected_total_trials is None:
            expected_total_trials = receipt_trials
        elif expected_total_trials != receipt_trials:
            raise ValueError("expected_total_trials conflicts with the optimization receipt")
        if optimization_receipt.get("report_format") != report.format:
            raise ValueError("optimization report format conflicts with the frozen receipt")
        if optimization_receipt.get("sharpe_column") != sharpe_column:
            raise ValueError("sharpe_column conflicts with the frozen optimization receipt")
        if optimization_receipt.get("sr_semantics") != sr_semantics:
            raise ValueError("sr_semantics conflicts with the frozen optimization receipt")
        if optimization_receipt["report"]["sha256"] != report.sha256:
            raise ValueError("optimization report SHA256 conflicts with the frozen receipt")
        receipt_selected_pass = str(optimization_receipt["selected_pass_id"])
        if selected_pass_id is None:
            selected_pass_id = receipt_selected_pass
        elif str(selected_pass_id) != receipt_selected_pass:
            raise ValueError("selected_pass_id conflicts with the optimization receipt")
        receipt_returns_path = Path(optimization_receipt["selected_returns"]["path"])
        if selected_returns_path is None:
            selected_returns_path = receipt_returns_path
        elif Path(selected_returns_path).resolve() != receipt_returns_path.resolve():
            raise ValueError("selected_returns_path conflicts with the optimization receipt")
        if returns_column != optimization_receipt["selected_returns_column"]:
            raise ValueError("returns_column conflicts with the optimization receipt")
    if expected_total_trials is not None:
        if expected_total_trials <= 0:
            raise ValueError("expected_total_trials must be positive")
        if report.total_passes != expected_total_trials:
            raise ValueError(
                "expected_total_trials mismatch: "
                f"expected {expected_total_trials}, parsed {report.total_passes}"
            )
        numeric_pass_ids = sorted(int(row.pass_id) for row in report.rows)
        contiguous_from_zero = numeric_pass_ids == list(range(report.total_passes))
        contiguous_from_one = numeric_pass_ids == list(range(1, report.total_passes + 1))
        if not (contiguous_from_zero or contiguous_from_one):
            raise ValueError(
                "full-pass closure requires contiguous Pass identities starting at 0 or 1"
            )

    trial_srs: list[float] = []
    missing_sr_passes: list[str] = []
    for row in report.rows:
        try:
            trial_srs.append(_as_finite_float(row.values.get(sharpe_column), sharpe_column))
        except ValueError:
            missing_sr_passes.append(row.pass_id)

    dsr_payload: dict[str, Any]
    evidence_complete = False
    selected = next((row for row in report.rows if row.pass_id == str(selected_pass_id)), None)
    if optimization_receipt is not None and selected is not None:
        selection_metric = str(optimization_receipt["selection_metric"])
        direction = str(optimization_receipt["selection_direction"])
        scored = [
            (
                _as_finite_float(row.values.get(selection_metric), selection_metric),
                int(row.pass_id),
                row.pass_id,
            )
            for row in report.rows
        ]
        best_value = (
            max(value for value, _, _ in scored)
            if direction == "max"
            else min(value for value, _, _ in scored)
        )
        tied = [item for item in scored if math.isclose(item[0], best_value, rel_tol=1e-12, abs_tol=1e-12)]
        rule_selected_pass = min(tied, key=lambda item: item[1])[2]
        if selected.pass_id != rule_selected_pass:
            raise ValueError(
                "selected pass violates the frozen selection rule: "
                f"expected {rule_selected_pass}, got {selected.pass_id}"
            )
    if selected_pass_id is None or selected_returns_path is None:
        dsr_payload = {
            "status": "BLOCKED_MISSING_SELECTED_SERIES",
            "reason": "selected pass id and hashable per-trade net_R series are required",
        }
    elif selected is None:
        dsr_payload = {
            "status": "BLOCKED_SELECTED_PASS_NOT_FOUND",
            "reason": f"selected pass {selected_pass_id} is not present in the full report",
        }
    elif sr_semantics != "per_trade_net_r":
        dsr_payload = {
            "status": "BLOCKED_SR_SEMANTICS",
            "reason": (
                "DSR requires the same per-trade net_R Sharpe semantics for every trial "
                "and the selected return series; MT5 tester Sharpe is not silently mixed"
            ),
            "declared_sr_semantics": sr_semantics,
        }
    elif missing_sr_passes:
        dsr_payload = {
            "status": "BLOCKED_INCOMPLETE_TRIAL_SHARPE",
            "missing_pass_ids": missing_sr_passes,
        }
    elif len(trial_srs) < 2:
        dsr_payload = {"status": "BLOCKED_INSUFFICIENT_TRIALS"}
    else:
        returns_path = Path(selected_returns_path)
        if optimization_receipt is not None:
            expected_returns_hash = optimization_receipt["selected_returns"]["sha256"]
            actual_returns_hash = _sha256(returns_path)
            if actual_returns_hash != expected_returns_hash:
                raise ValueError(
                    "selected returns SHA256 changed after receipt verification: "
                    f"expected {expected_returns_hash}, actual {actual_returns_hash}"
                )
        returns = _load_returns(returns_path, returns_column)
        selected_sr = sample_sharpe(returns)
        reported_selected_sr = _as_finite_float(selected.values.get(sharpe_column), sharpe_column)
        sr_delta = abs(selected_sr - reported_selected_sr)
        if sr_delta > sr_match_tolerance:
            dsr_payload = {
                "status": "BLOCKED_SELECTED_SR_MISMATCH",
                "computed_selected_sr": selected_sr,
                "reported_selected_sr": reported_selected_sr,
                "absolute_delta": sr_delta,
                "tolerance": sr_match_tolerance,
            }
        else:
            skew, kurt = _distribution_shape(returns)
            variance = statistics.variance(trial_srs)
            probability = _canonical_dsr(
                selected_sr,
                len(returns),
                skew,
                kurt,
                variance,
                report.total_passes
                + int(optimization_receipt.get("cumulative_trials_before", 0) if optimization_receipt else 0),
            )
            dsr_payload = {
                "status": "COMPUTED",
                "probability": probability,
                "threshold": 0.95,
                "passes_threshold": probability >= 0.95,
                "selected_pass_id": selected.pass_id,
                "selected_sr": selected_sr,
                "n_observations": len(returns),
                "skew": skew,
                "non_excess_kurtosis": kurt,
                "variance_of_trial_sr": variance,
                "selected_returns_path": str(returns_path.resolve()),
                "selected_returns_sha256": _sha256(returns_path),
            }
            evidence_complete = True

    cumulative_trials = report.total_passes + int(
        optimization_receipt.get("cumulative_trials_before", 0) if optimization_receipt else 0
    )
    diagnostic_evidence_complete = bool(
        expected_total_trials is not None
        and selection_frozen
        and evidence_complete
        and sr_semantics == "per_trade_net_r"
        and not missing_sr_passes
        and optimization_receipt is not None
        and optimization_receipt.get("receipt_integrity_verified") is True
        and optimization_receipt.get("selection_rule_frozen") is True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_kind": "full_mt5_optimization_trial_inventory_and_dsr",
        "report": {
            "path": str(report.path),
            "sha256": report.sha256,
            "format": report.format,
            "headers": list(report.headers),
        },
        "trial_inventory": {
            "n_trials": report.total_passes,
            "cumulative_trials_considered": cumulative_trials,
            "expected_total_trials": expected_total_trials,
            "expected_count_bound": expected_total_trials is not None,
            "sharpe_column": sharpe_column,
            "sr_semantics": sr_semantics,
            "usable_sharpe_passes": len(trial_srs),
            "missing_sharpe_pass_ids": missing_sr_passes,
            "pass_ids": [row.pass_id for row in report.rows],
        },
        "selection_frozen_pre_outcome": selection_frozen,
        "optimization_receipt": dict(optimization_receipt) if optimization_receipt else None,
        "dsr": dsr_payload,
        "diagnostic_evidence_complete": diagnostic_evidence_complete,
        "anti_overfit_gate_eligible": False,
        "anti_overfit_gate_pass": False,
        "diagnostic_dsr_pass": diagnostic_evidence_complete
        and dsr_payload.get("passes_threshold") is True,
        "promotion_eligible": False,
        "limitation": (
            "DIAGNOSTIC_ONLY: the receipt binds this exported family and selected series, "
            "but schema v1 does not independently prove a preregistration timestamp or "
            "complete cumulative campaign exposure. It cannot pass a promotion gate."
        ),
    }


def _autodetect_parameter_axes(report: OptimizationReport) -> tuple[str, str]:
    candidates: list[str] = []
    for header in report.headers:
        if header.strip().lower() in KNOWN_METRICS:
            continue
        numeric_values: set[float] = set()
        for row in report.rows:
            try:
                numeric_values.add(_as_finite_float(row.values.get(header), header))
            except ValueError:
                pass
        if len(numeric_values) >= 2:
            candidates.append(header)
    if len(candidates) < 2:
        raise ValueError("specify --param1 and --param2; two numeric parameter axes were not found")
    return candidates[0], candidates[1]


def _plot_surface(surface: dict[str, Any], out_dir: Path) -> list[str]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        raise ValueError("matplotlib and numpy are required for plot output") from exc

    matrix = np.array(
        [[np.nan if value is None else value for value in row] for row in surface["matrix"]],
        dtype=float,
    )
    p1 = surface["parameter_values"][surface["param1"]]
    p2 = surface["parameter_values"][surface["param2"]]

    heatmap_path = out_dir / "parameter_heatmap.png"
    fig, ax = plt.subplots(figsize=(10, 7))
    image = ax.imshow(matrix, origin="lower", aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(p2)), [str(value) for value in p2], rotation=45, ha="right")
    ax.set_yticks(range(len(p1)), [str(value) for value in p1])
    ax.set_xlabel(surface["param2"])
    ax.set_ylabel(surface["param1"])
    ax.set_title(f"Actual MT5 optimization surface: {surface['metric']}")
    fig.colorbar(image, ax=ax, label=surface["metric"])
    fig.tight_layout()
    fig.savefig(heatmap_path, dpi=160)
    plt.close(fig)

    surface_path = out_dir / "parameter_surface_3d.png"
    x_grid, y_grid = np.meshgrid(range(len(p2)), range(len(p1)))
    fig = plt.figure(figsize=(11, 8))
    ax3d = fig.add_subplot(111, projection="3d")
    ax3d.plot_surface(x_grid, y_grid, matrix, cmap="viridis", edgecolor="none")
    ax3d.set_xticks(range(len(p2)), [str(value) for value in p2])
    ax3d.set_yticks(range(len(p1)), [str(value) for value in p1])
    ax3d.set_xlabel(surface["param2"])
    ax3d.set_ylabel(surface["param1"])
    ax3d.set_zlabel(surface["metric"])
    ax3d.set_title("Parameter stability surface (actual passes)")
    fig.tight_layout()
    fig.savefig(surface_path, dpi=160)
    plt.close(fig)
    return [str(heatmap_path), str(surface_path)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import every MT5 optimization pass, compute DSR, and render a real surface"
    )
    parser.add_argument("--report", required=True, help="Full MT5 optimization XML/CSV export")
    parser.add_argument("--out", default="", help="Output directory")
    parser.add_argument("--param1", default="", help="First actual optimizer input column")
    parser.add_argument("--param2", default="", help="Second actual optimizer input column")
    parser.add_argument("--metric", default="Custom", help="Pass metric for the surface")
    parser.add_argument("--plateau-fraction", type=float, default=0.90)
    parser.add_argument("--lower-is-better", action="store_true")
    parser.add_argument("--expected-total-trials", type=int, default=0)
    parser.add_argument("--selected-pass", default="")
    parser.add_argument("--selected-returns", default="")
    parser.add_argument("--returns-column", default="net_r")
    parser.add_argument("--sharpe-column", default="Custom")
    parser.add_argument(
        "--sr-semantics",
        default="unspecified",
        choices=["unspecified", "per_trade_net_r", "mt5_tester_sharpe"],
    )
    parser.add_argument("--selection-frozen", action="store_true")
    parser.add_argument("--optimization-receipt", default="")
    parser.add_argument("--no-plot", action="store_true")
    args = parser.parse_args()

    try:
        report = parse_optimization_report(Path(args.report))
        param1, param2 = args.param1, args.param2
        if bool(param1) != bool(param2):
            raise ValueError("provide both --param1 and --param2, or neither")
        surface: dict[str, Any]
        if not param1 and not param2:
            try:
                param1, param2 = _autodetect_parameter_axes(report)
            except ValueError as exc:
                surface = {
                    "status": "BLOCKED_FEWER_THAN_TWO_PARAMETER_AXES",
                    "reason": str(exc),
                    "stability_claim": "UNAVAILABLE",
                }
            else:
                surface = build_parameter_surface(
                    report.rows,
                    param1=param1,
                    param2=param2,
                    metric=args.metric,
                    plateau_fraction=args.plateau_fraction,
                    lower_is_better=args.lower_is_better,
                )
        else:
            surface = build_parameter_surface(
                report.rows,
                param1=param1,
                param2=param2,
                metric=args.metric,
                plateau_fraction=args.plateau_fraction,
                lower_is_better=args.lower_is_better,
            )
        optimization_receipt = (
            load_optimization_receipt(Path(args.optimization_receipt))
            if args.optimization_receipt
            else None
        )
        audit = build_optimization_audit(
            report,
            expected_total_trials=args.expected_total_trials or None,
            selected_pass_id=args.selected_pass or None,
            selected_returns_path=Path(args.selected_returns) if args.selected_returns else None,
            returns_column=args.returns_column,
            sharpe_column=args.sharpe_column,
            sr_semantics=args.sr_semantics,
            selection_frozen=args.selection_frozen,
            optimization_receipt=optimization_receipt,
        )
        audit["parameter_surface"] = surface
        out_dir = Path(args.out) if args.out else Path(args.report).resolve().parent / "optimization_analysis"
        out_dir.mkdir(parents=True, exist_ok=True)
        if not args.no_plot and surface.get("status") is None:
            audit["parameter_surface"]["plots"] = _plot_surface(surface, out_dir)
        out_path = out_dir / "optimization_audit.json"
        out_path.write_text(
            json.dumps(audit, indent=2, ensure_ascii=False, allow_nan=False),
            encoding="utf-8",
        )
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"[OPTIMIZATION AUDIT] {out_path}")
    print(
        f"passes={report.total_passes} dsr={audit['dsr']['status']} "
        f"gate_eligible={audit['anti_overfit_gate_eligible']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
