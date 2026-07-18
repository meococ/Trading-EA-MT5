#!/usr/bin/env python3
"""Build a report-bound execution-cost artifact from raw, bound evidence.

Promotion-grade evidence remains the default.  A separately labelled
``RESEARCH_PROXY`` tier is accepted only as non-promotable falsification input;
it cannot silently impersonate observed fills.  Both tiers independently
recompute cost-source statistics, join lifecycle telemetry to MT5 report deals,
reconcile account P&L, and reprice each completed position in R.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


TOOLS_DIR = Path(__file__).resolve().parent
ALPHA_ROOT = TOOLS_DIR.parent
ANALYSIS_DIR = ALPHA_ROOT / "analysis"
if str(ANALYSIS_DIR) not in sys.path:
    sys.path.insert(0, str(ANALYSIS_DIR))

from quant_analyzer import Deal, parse_deals  # noqa: E402
from unified_validation import _run_identity_sha256  # noqa: E402


SCHEMA_VERSION = "verified_execution_cost.v1"
RESEARCH_PROXY_SCHEMA_VERSION = "research_execution_cost_proxy.v1"
COST_SOURCE_SCHEMA = "alphafactory_cost_source_manifest.v1"
RESEARCH_PROXY_TIER = "RESEARCH_PROXY"
TELEMETRY_SCHEMA = "alphafactory_lifecycle_telemetry.v1"
REQUIRED_LIFECYCLE_COLUMNS = {
    "event_time",
    "action",
    "order_type",
    "volume",
    "price",
    "symbol",
    "position_id",
    "risk_pts",
    "initial_risk_account",
    "deal",
    "deal_profit",
    "deal_commission",
    "deal_swap",
    "deal_fee",
    "deal_net",
    "is_final_close",
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def finite(value: Any, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def positive(value: Any, label: str) -> float:
    number = finite(value, label)
    if number <= 0:
        raise ValueError(f"{label} must be > 0")
    return number


def integer(value: Any, label: str) -> int:
    number = finite(value, label)
    if not number.is_integer():
        raise ValueError(f"{label} must be an integer")
    return int(number)


def close_enough(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def resolve_evidence_path(raw: Any, anchor: Path) -> Path:
    path = Path(str(raw or ""))
    if not path.is_absolute():
        anchored = (anchor / path).resolve()
        if anchored.exists():
            return anchored
        path = ALPHA_ROOT.parent / path
    return path.resolve()


def same_path(left: Any, right: Path) -> bool:
    try:
        return Path(str(left)).resolve() == right.resolve()
    except (OSError, RuntimeError, ValueError):
        return False


def verified_reference(node: dict[str, Any], anchor: Path, label: str) -> dict[str, Any]:
    path = resolve_evidence_path(node.get("source"), anchor)
    if not path.is_file():
        raise ValueError(f"{label}.source does not exist: {path}")
    declared = str(node.get("source_sha256") or node.get("sha256") or "").upper()
    actual = sha256_file(path)
    if declared != actual:
        raise ValueError(f"{label}.source_sha256 mismatch")
    result = dict(node)
    result["source"] = str(path)
    result["sha256"] = actual
    result.pop("source_sha256", None)
    return result


def read_csv(path: Path, required: set[str], label: str) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"{label} is missing columns: {missing}")
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError(f"{label} contains no rows")
    return rows


def parse_timestamp(value: Any, label: str) -> datetime:
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text.removesuffix("Z"))
        if parsed.tzinfo is not None:
            parsed = parsed.replace(tzinfo=None)
        return parsed
    except ValueError:
        pass
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"{label} has invalid timestamp: {text}")


def manifest_date(value: Any, label: str) -> datetime:
    text = str(value or "").strip()
    for fmt in ("%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"{label} has invalid date: {text}")


def p90(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("P90 requires at least one value")
    return ordered[max(0, math.ceil(0.90 * len(ordered)) - 1)]


def validate_spread_evidence(
    node: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    rows = read_csv(
        Path(node["source"]),
        {"timestamp", "symbol", "bid", "ask"},
        "historical spread evidence",
    )
    symbol = str(manifest.get("symbol") or "")
    start = manifest_date(manifest.get("from"), "run_manifest.from").date()
    end = manifest_date(manifest.get("to"), "run_manifest.to").date()
    valid = 0
    for index, row in enumerate(rows, start=2):
        if str(row.get("symbol") or "") != symbol:
            raise ValueError(f"spread row {index} symbol does not match run")
        timestamp = parse_timestamp(row.get("timestamp"), f"spread row {index}")
        if not start <= timestamp.date() <= end:
            raise ValueError(f"spread row {index} is outside the run window")
        try:
            bid = finite(row.get("bid"), f"spread row {index} bid")
            ask = finite(row.get("ask"), f"spread row {index} ask")
        except ValueError:
            continue
        if bid > 0 and ask >= bid:
            valid += 1
    total = len(rows)
    ratio = valid / total
    coverage = node.get("coverage") if isinstance(node.get("coverage"), dict) else {}
    if integer(coverage.get("sample_count"), "spread coverage sample_count") != valid:
        raise ValueError("spread coverage sample_count does not match raw evidence")
    if integer(coverage.get("total_count"), "spread coverage total_count") != total:
        raise ValueError("spread coverage total_count does not match raw evidence")
    if not close_enough(finite(coverage.get("coverage_ratio"), "spread coverage ratio"), ratio, 1e-9):
        raise ValueError("spread coverage ratio does not match raw evidence")
    if ratio < 0.99:
        raise ValueError("historical spread coverage does not meet the 99% contract")
    if str(coverage.get("from") or "") != str(manifest.get("from") or "") or str(
        coverage.get("to") or ""
    ) != str(manifest.get("to") or ""):
        raise ValueError("historical spread coverage window does not match run")
    result = dict(node)
    result["coverage"] = {
        "from": manifest["from"],
        "to": manifest["to"],
        "sample_count": valid,
        "total_count": total,
        "coverage_ratio": ratio,
    }
    return result


def validate_commission_evidence(
    node: dict[str, Any], manifest: dict[str, Any], account_currency: str
) -> tuple[dict[str, Any], float]:
    rows = read_csv(
        Path(node["source"]),
        {
            "position_id",
            "symbol",
            "account_currency",
            "round_turn_account_per_lot",
            "conversion_method",
        },
        "commission evidence",
    )
    ids: set[str] = set()
    values: list[float] = []
    for index, row in enumerate(rows, start=2):
        position_id = str(row.get("position_id") or "").strip()
        if not position_id or position_id in ids:
            raise ValueError(f"commission row {index} has duplicate/empty position_id")
        ids.add(position_id)
        if str(row.get("symbol") or "") != str(manifest.get("symbol") or ""):
            raise ValueError(f"commission row {index} symbol does not match run")
        if str(row.get("account_currency") or "") != account_currency:
            raise ValueError(f"commission row {index} account currency does not match run")
        if str(row.get("conversion_method") or "") != "per_trade_contemporaneous":
            raise ValueError(f"commission row {index} lacks contemporaneous conversion")
        values.append(
            positive(
                row.get("round_turn_account_per_lot"),
                f"commission row {index} round_turn_account_per_lot",
            )
        )
    statistic = str(node.get("statistic") or "")
    if statistic != "p90":
        raise ValueError("commission_provenance.statistic must equal p90")
    computed = p90(values)
    declared = positive(node.get("value"), "commission_provenance.value")
    if not close_enough(declared, computed, 1e-9):
        raise ValueError("commission_provenance.value does not match raw-evidence P90")
    if integer(node.get("sample_count"), "commission sample_count") != len(values):
        raise ValueError("commission sample_count does not match raw evidence")
    if len(values) < 30 or node.get("same_symbol_lifecycles") is not True:
        raise ValueError("commission evidence needs at least 30 same-symbol lifecycles")
    result = dict(node)
    result["sample_count"] = len(values)
    result["value"] = computed
    return result, computed


def validate_proxy_commission_evidence(
    node: dict[str, Any], manifest: dict[str, Any], account_currency: str
) -> tuple[dict[str, Any], float]:
    """Validate a deliberately conservative tester-only commission clue."""
    rows = read_csv(
        Path(node["source"]),
        {
            "position_id",
            "symbol",
            "account_currency",
            "round_turn_account_per_lot",
            "source_kind",
        },
        "research proxy commission evidence",
    )
    ids: set[str] = set()
    values: list[float] = []
    for index, row in enumerate(rows, start=2):
        position_id = str(row.get("position_id") or "").strip()
        if not position_id or position_id in ids:
            raise ValueError(f"proxy commission row {index} has duplicate/empty position_id")
        ids.add(position_id)
        if str(row.get("symbol") or "") != str(manifest.get("symbol") or ""):
            raise ValueError(f"proxy commission row {index} symbol does not match run")
        if str(row.get("account_currency") or "") != account_currency:
            raise ValueError(f"proxy commission row {index} account currency does not match run")
        if str(row.get("source_kind") or "") != "strategy_tester_simulation":
            raise ValueError(f"proxy commission row {index} must remain tester-labelled")
        values.append(
            positive(
                row.get("round_turn_account_per_lot"),
                f"proxy commission row {index} round_turn_account_per_lot",
            )
        )
    if str(node.get("statistic") or "") != "maximum":
        raise ValueError("research proxy commission statistic must equal maximum")
    computed = max(values)
    declared = positive(node.get("value"), "commission_provenance.value")
    if not close_enough(declared, computed, 1e-9):
        raise ValueError("research proxy commission value does not match raw-evidence maximum")
    if integer(node.get("sample_count"), "proxy commission sample_count") != len(values):
        raise ValueError("research proxy commission sample_count does not match raw evidence")
    if (
        len(values) < 30
        or node.get("same_symbol_lifecycles") is not True
        or node.get("source_kind") != "strategy_tester_simulation"
    ):
        raise ValueError("research proxy commission needs 30 tester-labelled same-symbol lifecycles")
    result = dict(node)
    result["sample_count"] = len(values)
    result["value"] = computed
    return result, computed


def validate_contract_evidence(
    node: dict[str, Any], manifest: dict[str, Any], account_currency: str
) -> tuple[dict[str, Any], float]:
    contract = load_json(Path(node["source"]))
    required_equal = {
        "broker_fingerprint": manifest.get("broker_fingerprint"),
        "server_fingerprint": manifest.get("server_fingerprint"),
        "account_fingerprint": manifest.get("account_fingerprint"),
        "symbol": manifest.get("symbol"),
        "account_currency": account_currency,
        "from": manifest.get("from"),
        "to": manifest.get("to"),
        "conversion_method": "per_trade_contemporaneous",
    }
    for field, expected in required_equal.items():
        if contract.get(field) != expected or node.get(field) != expected:
            raise ValueError(f"commission broker contract {field} does not match run")
    if contract.get("per_lot_basis") is not True or node.get("per_lot_basis") is not True:
        raise ValueError("commission broker contract per_lot_basis must be true")
    value = positive(
        contract.get("round_turn_account_per_lot"),
        "broker contract round_turn_account_per_lot",
    )
    if not close_enough(
        value,
        positive(node.get("round_turn_account_per_lot"), "manifest broker contract value"),
        1e-9,
    ):
        raise ValueError("broker contract value does not match its raw JSON evidence")
    if not str(contract.get("description") or "").strip() or node.get("description") != contract.get(
        "description"
    ):
        raise ValueError("broker contract description is missing or mismatched")
    result = dict(node)
    result.update(contract)
    return result, value


def validate_slippage_evidence(
    node: dict[str, Any], manifest: dict[str, Any], pip_size: float
) -> tuple[dict[str, Any], float]:
    rows = read_csv(
        Path(node["source"]),
        {
            "fill_id",
            "timestamp",
            "symbol",
            "side",
            "reference_side",
            "reference_price",
            "fill_price",
            "pip_size",
        },
        "slippage evidence",
    )
    start = manifest_date(manifest.get("from"), "run_manifest.from").date()
    end = manifest_date(manifest.get("to"), "run_manifest.to").date()
    ids: set[str] = set()
    by_side: dict[str, list[float]] = {"BUY": [], "SELL": []}
    for index, row in enumerate(rows, start=2):
        fill_id = str(row.get("fill_id") or "").strip()
        if not fill_id or fill_id in ids:
            raise ValueError(f"slippage row {index} has duplicate/empty fill_id")
        ids.add(fill_id)
        if str(row.get("symbol") or "") != str(manifest.get("symbol") or ""):
            raise ValueError(f"slippage row {index} symbol does not match run")
        timestamp = parse_timestamp(row.get("timestamp"), f"slippage row {index}")
        if not start <= timestamp.date() <= end:
            raise ValueError(f"slippage row {index} is outside the run window")
        side = str(row.get("side") or "").upper()
        expected_reference = "ask" if side == "BUY" else "bid" if side == "SELL" else ""
        if not expected_reference or str(row.get("reference_side") or "").lower() != expected_reference:
            raise ValueError(f"slippage row {index} has invalid side/reference-side pairing")
        row_pip = positive(row.get("pip_size"), f"slippage row {index} pip_size")
        if not close_enough(row_pip, pip_size, 1e-12):
            raise ValueError(f"slippage row {index} pip_size does not match run geometry")
        reference = positive(row.get("reference_price"), f"slippage row {index} reference_price")
        fill = positive(row.get("fill_price"), f"slippage row {index} fill_price")
        adverse = max(0.0, (fill - reference) / pip_size) if side == "BUY" else max(
            0.0, (reference - fill) / pip_size
        )
        by_side[side].append(adverse)
    buy_p90 = p90(by_side["BUY"])
    sell_p90 = p90(by_side["SELL"])
    roundturn = buy_p90 + sell_p90
    expected = {
        "sample_count": len(rows),
        "buy_count": len(by_side["BUY"]),
        "sell_count": len(by_side["SELL"]),
    }
    for field, value in expected.items():
        if integer(node.get(field), f"slippage {field}") != value:
            raise ValueError(f"slippage {field} does not match raw evidence")
    if expected["sample_count"] < 100 or expected["buy_count"] < 30 or expected["sell_count"] < 30:
        raise ValueError("slippage evidence does not meet the 100/30/30 contract")
    for field, value in (("p90_buy", buy_p90), ("p90_sell", sell_p90), ("p90_roundturn", roundturn)):
        if not close_enough(finite(node.get(field), f"slippage {field}"), value, 1e-9):
            raise ValueError(f"slippage {field} does not match raw evidence")
    if (
        node.get("independent_reference") is not True
        or node.get("buy_reference_side") != "ask"
        or node.get("sell_reference_side") != "bid"
        or node.get("slippage_unit") != "pips"
        or not str(node.get("method") or "").strip()
    ):
        raise ValueError("slippage provenance lacks the independent side-referenced pips contract")
    result = dict(node)
    result.update(expected)
    result.update({"p90_buy": buy_p90, "p90_sell": sell_p90, "p90_roundturn": roundturn})
    return result, roundturn


def validate_quote_latency_proxy(
    node: dict[str, Any], manifest: dict[str, Any], pip_size: float
) -> tuple[dict[str, Any], float]:
    """Validate adverse movement to a future executable quote, never a claimed fill."""
    rows = read_csv(
        Path(node["source"]),
        {
            "sample_id",
            "reference_timestamp",
            "future_timestamp",
            "symbol",
            "side",
            "reference_side",
            "reference_price",
            "future_quote_price",
            "pip_size",
            "latency_ms",
            "actual_delay_ms",
        },
        "research quote-latency proxy evidence",
    )
    fixed_latency_ms = integer(node.get("fixed_latency_ms"), "proxy fixed_latency_ms")
    max_quote_wait_ms = integer(node.get("max_quote_wait_ms"), "proxy max_quote_wait_ms")
    if fixed_latency_ms <= 0 or max_quote_wait_ms < 0:
        raise ValueError("research quote proxy latency contract is invalid")
    ids: set[str] = set()
    by_side: dict[str, list[float]] = {"BUY": [], "SELL": []}
    last_future_by_side: dict[str, datetime] = {}
    for index, row in enumerate(rows, start=2):
        sample_id = str(row.get("sample_id") or "").strip()
        if not sample_id or sample_id in ids:
            raise ValueError(f"quote proxy row {index} has duplicate/empty sample_id")
        ids.add(sample_id)
        if str(row.get("symbol") or "") != str(manifest.get("symbol") or ""):
            raise ValueError(f"quote proxy row {index} symbol does not match run")
        side = str(row.get("side") or "").upper()
        expected_reference = "ask" if side == "BUY" else "bid" if side == "SELL" else ""
        if not expected_reference or str(row.get("reference_side") or "").lower() != expected_reference:
            raise ValueError(f"quote proxy row {index} has invalid side/reference-side pairing")
        reference_time = parse_timestamp(
            row.get("reference_timestamp"), f"quote proxy row {index} reference_timestamp"
        )
        future_time = parse_timestamp(
            row.get("future_timestamp"), f"quote proxy row {index} future_timestamp"
        )
        actual_delay_ms = integer(row.get("actual_delay_ms"), f"quote proxy row {index} delay")
        measured_delay_ms = int(round((future_time - reference_time).total_seconds() * 1000.0))
        if actual_delay_ms != measured_delay_ms:
            raise ValueError(f"quote proxy row {index} timestamp delay does not match actual_delay_ms")
        if not fixed_latency_ms <= actual_delay_ms <= fixed_latency_ms + max_quote_wait_ms:
            raise ValueError(f"quote proxy row {index} violates the fixed-latency wait contract")
        if integer(row.get("latency_ms"), f"quote proxy row {index} latency_ms") != fixed_latency_ms:
            raise ValueError(f"quote proxy row {index} latency_ms does not match provenance")
        previous_future = last_future_by_side.get(side)
        if previous_future is not None and reference_time < previous_future:
            raise ValueError(f"quote proxy row {index} overlaps the prior {side} sample")
        last_future_by_side[side] = future_time
        row_pip = positive(row.get("pip_size"), f"quote proxy row {index} pip_size")
        if not close_enough(row_pip, pip_size, 1e-12):
            raise ValueError(f"quote proxy row {index} pip_size does not match run geometry")
        reference = positive(row.get("reference_price"), f"quote proxy row {index} reference_price")
        future_quote = positive(
            row.get("future_quote_price"), f"quote proxy row {index} future_quote_price"
        )
        adverse = (
            max(0.0, (future_quote - reference) / pip_size)
            if side == "BUY"
            else max(0.0, (reference - future_quote) / pip_size)
        )
        by_side[side].append(adverse)
    buy_p90 = p90(by_side["BUY"])
    sell_p90 = p90(by_side["SELL"])
    roundturn = buy_p90 + sell_p90
    expected = {
        "sample_count": len(rows),
        "buy_count": len(by_side["BUY"]),
        "sell_count": len(by_side["SELL"]),
    }
    for field, value in expected.items():
        if integer(node.get(field), f"quote proxy {field}") != value:
            raise ValueError(f"quote proxy {field} does not match raw evidence")
    if expected["sample_count"] < 100 or expected["buy_count"] < 30 or expected["sell_count"] < 30:
        raise ValueError("research quote proxy does not meet the 100/30/30 contract")
    for field, value in (("p90_buy", buy_p90), ("p90_sell", sell_p90), ("p90_roundturn", roundturn)):
        if not close_enough(finite(node.get(field), f"quote proxy {field}"), value, 1e-9):
            raise ValueError(f"quote proxy {field} does not match raw evidence")
    if (
        node.get("independent_reference") is not False
        or node.get("independent_quote_reference") is not True
        or node.get("fill_observed") is not False
        or node.get("buy_reference_side") != "ask"
        or node.get("sell_reference_side") != "bid"
        or node.get("slippage_unit") != "pips"
        or not str(node.get("method") or "").strip()
    ):
        raise ValueError("research quote proxy must remain explicitly non-fill and side-referenced")
    result = dict(node)
    result.update(expected)
    result.update({"p90_buy": buy_p90, "p90_sell": sell_p90, "p90_roundturn": roundturn})
    return result, roundturn


def validate_cost_source(
    payload: dict[str, Any], source_path: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    if payload.get("schema_version") != COST_SOURCE_SCHEMA:
        raise ValueError(f"cost source schema must be {COST_SOURCE_SCHEMA}")
    research_proxy = payload.get("evidence_tier") == RESEARCH_PROXY_TIER
    if research_proxy:
        if payload.get("promotion_eligible") is not False:
            raise ValueError("RESEARCH_PROXY cost source promotion_eligible must be false")
        if (
            payload.get("provenance_status") != "VERIFIED_RESEARCH_PROXY"
            or payload.get("audit_status") != "PASS_RESEARCH_ONLY"
            or payload.get("verdict") != "PASS_RESEARCH_ONLY"
        ):
            raise ValueError("RESEARCH_PROXY cost source root is not explicitly research-only")
    elif (
        payload.get("provenance_status") != "VERIFIED"
        or payload.get("audit_status") != "PASS"
        or payload.get("verdict") != "PASS"
    ):
        raise ValueError("cost source root is not VERIFIED/PASS")
    basis = manifest.get("fingerprint_basis") if isinstance(manifest.get("fingerprint_basis"), dict) else {}
    digits = integer(basis.get("digits"), "run digits")
    point = positive(basis.get("point"), "run point")
    pip_size = positive(basis.get("pip_size"), "run pip_size")
    account_currency = str(basis.get("currency") or "").strip()
    if not account_currency:
        raise ValueError("run account currency is missing")
    required_equal = {
        "broker": basis.get("broker"),
        "server": basis.get("server"),
        "account_currency": account_currency,
        "broker_fingerprint": manifest.get("broker_fingerprint"),
        "server_fingerprint": manifest.get("server_fingerprint"),
        "account_fingerprint": manifest.get("account_fingerprint"),
        "data_fingerprint": manifest.get("data_fingerprint"),
        "symbol": manifest.get("symbol"),
        "from": manifest.get("from"),
        "to": manifest.get("to"),
    }
    for field, expected in required_equal.items():
        if not expected or payload.get(field) != expected:
            raise ValueError(f"cost source {field} does not match run manifest")
    geometry = payload.get("symbol_geometry") if isinstance(payload.get("symbol_geometry"), dict) else {}
    for field, expected in (("digits", digits), ("point", point), ("pip_size", pip_size)):
        actual = integer(geometry.get(field), field) if field == "digits" else positive(geometry.get(field), field)
        if not close_enough(float(actual), float(expected), 1e-12):
            raise ValueError(f"cost source symbol_geometry.{field} does not match run")

    spread_raw = payload.get("historical_spread_provenance")
    commission_raw = payload.get("commission_provenance")
    slippage_raw = payload.get("slippage_provenance")
    methodology = payload.get("direction_aware_methodology")
    if not all(isinstance(node, dict) for node in (spread_raw, commission_raw, slippage_raw, methodology)):
        raise ValueError("cost source provenance nodes must be objects")
    spread_ref = verified_reference(spread_raw, source_path.parent, "historical_spread_provenance")
    slippage_ref = verified_reference(slippage_raw, source_path.parent, "slippage_provenance")
    if spread_ref.get("verification_status") != "VERIFIED" or spread_ref.get("symbol") != manifest.get("symbol"):
        raise ValueError("historical spread provenance is not VERIFIED for the run symbol")
    spread = validate_spread_evidence(spread_ref, manifest)

    commission = dict(commission_raw)
    commission_value_declared = positive(commission.get("value"), "commission_provenance.value")
    if research_proxy:
        commission = verified_reference(commission, source_path.parent, "commission_provenance")
        if (
            commission.get("verification_status") != "VERIFIED_RESEARCH_PROXY"
            or commission.get("symbol") != manifest.get("symbol")
        ):
            raise ValueError("research proxy commission provenance is not valid for the run symbol")
        commission, commission_value = validate_proxy_commission_evidence(
            commission, manifest, account_currency
        )
    elif commission.get("source"):
        commission = verified_reference(commission, source_path.parent, "commission_provenance")
        if commission.get("verification_status") != "VERIFIED" or commission.get("symbol") != manifest.get("symbol"):
            raise ValueError("commission provenance is not VERIFIED for the run symbol")
        commission, commission_value = validate_commission_evidence(
            commission, manifest, account_currency
        )
    else:
        contract_raw = commission.get("broker_contract")
        if not isinstance(contract_raw, dict):
            raise ValueError("commission provenance requires empirical evidence or a broker contract")
        contract_ref = verified_reference(
            contract_raw, source_path.parent, "commission_provenance.broker_contract"
        )
        contract, commission_value = validate_contract_evidence(
            contract_ref, manifest, account_currency
        )
        commission["broker_contract"] = contract
    if not close_enough(commission_value_declared, commission_value, 1e-9):
        raise ValueError("commission_provenance.value does not match verified evidence")

    expected_slippage_status = "VERIFIED_RESEARCH_PROXY" if research_proxy else "VERIFIED"
    if slippage_ref.get("verification_status") != expected_slippage_status or slippage_ref.get(
        "symbol"
    ) != manifest.get("symbol"):
        raise ValueError("slippage provenance is not valid for the run symbol/tier")
    if research_proxy:
        slippage, slippage_roundturn = validate_quote_latency_proxy(
            slippage_ref, manifest, pip_size
        )
    else:
        slippage, slippage_roundturn = validate_slippage_evidence(
            slippage_ref, manifest, pip_size
        )
    expected_methodology_status = "VERIFIED_RESEARCH_PROXY" if research_proxy else "VERIFIED"
    if (
        methodology.get("verification_status") != expected_methodology_status
        or methodology.get("direction_aware") is not True
    ):
        raise ValueError("direction-aware cost methodology is not valid for the evidence tier")
    long_treatment = str(methodology.get("long_cost_treatment") or "").strip()
    short_treatment = str(methodology.get("short_cost_treatment") or "").strip()
    if not long_treatment or not short_treatment or long_treatment == short_treatment:
        raise ValueError("direction-aware long/short cost treatments must be distinct and nonempty")

    return {
        "evidence_tier": RESEARCH_PROXY_TIER if research_proxy else "PROMOTION_GRADE",
        "promotion_eligible": not research_proxy,
        "broker": str(basis.get("broker")),
        "server": str(basis.get("server")),
        "account_currency": account_currency,
        "broker_fingerprint": manifest["broker_fingerprint"],
        "server_fingerprint": manifest["server_fingerprint"],
        "account_fingerprint": manifest["account_fingerprint"],
        "data_fingerprint": manifest["data_fingerprint"],
        "symbol": manifest["symbol"],
        "from": manifest["from"],
        "to": manifest["to"],
        "symbol_geometry": {"digits": digits, "point": point, "pip_size": pip_size},
        "historical_spread": spread,
        "commission": commission,
        "slippage": slippage,
        "cost_methodology": {
            **methodology,
            "description": (
                f"Long: {long_treatment}. Short: {short_treatment}. Model-0 prices retain "
                "historical spread; "
                + (
                    "tester-maximum commission and fixed-latency adverse quote movement are "
                    "repriced for research falsification only; no fill is claimed."
                    if research_proxy
                    else "verified commission and side-referenced adverse slippage are repriced "
                    "from report-deal/account-risk lifecycles."
                )
            ),
        },
        "commission_value": commission_value,
        "slippage_p90_roundturn": slippage_roundturn,
    }


def lifecycle_sidecar(manifest: dict[str, Any], run_dir: Path) -> tuple[Path, str]:
    candidates: list[tuple[Path, str]] = []
    sidecars = manifest.get("sidecars")
    if not isinstance(sidecars, list):
        raise ValueError("run_manifest.sidecars must be a list")
    run_root = run_dir.resolve()
    for row in sidecars:
        if not isinstance(row, dict):
            continue
        relative = str(row.get("path") or "")
        name = Path(relative).name
        if not name.lower().endswith(".csv") or not any(
            marker in name for marker in ("_LifecycleTrades_", "_PX6_Trades_")
        ):
            continue
        path = Path(relative)
        if not path.is_absolute():
            path = run_dir / path
        path = path.resolve()
        if not path.is_relative_to(run_root) or not path.is_file():
            raise ValueError(f"lifecycle sidecar is absent or escapes run directory: {path}")
        declared = str(row.get("sha256") or "").upper()
        actual = sha256_file(path)
        if declared != actual:
            raise ValueError(f"lifecycle sidecar SHA256 mismatch: {path}")
        candidates.append((path, actual))
    if len(candidates) != 1:
        raise ValueError(
            "expected exactly one manifest-bound AlphaFactory lifecycle trade sidecar "
            f"(generic LifecycleTrades or legacy PX6); found {len(candidates)}"
        )
    return candidates[0]


def _deal_economics(row: dict[str, str], row_number: int) -> tuple[float, float, float, float, float]:
    profit = finite(row.get("deal_profit"), f"lifecycle row {row_number} deal_profit")
    commission = finite(row.get("deal_commission"), f"lifecycle row {row_number} deal_commission")
    swap = finite(row.get("deal_swap"), f"lifecycle row {row_number} deal_swap")
    fee = finite(row.get("deal_fee"), f"lifecycle row {row_number} deal_fee")
    net = finite(row.get("deal_net"), f"lifecycle row {row_number} deal_net")
    if not close_enough(net, profit + commission + swap + fee, 0.011):
        raise ValueError(f"lifecycle row {row_number} deal_net does not reconcile")
    return profit, commission, swap, fee, net


def parse_lifecycle(
    path: Path,
    symbol: str,
    point: float,
    pip_size: float,
    report_deals: list[Deal],
) -> list[dict[str, Any]]:
    rows = read_csv(path, REQUIRED_LIFECYCLE_COLUMNS, "lifecycle telemetry")
    report_trade_deals = {
        deal.deal_id: deal
        for deal in report_deals
        if deal.deal_id > 0
        and deal.symbol == symbol
        and str(deal.direction or "").strip().lower().startswith(("in", "out"))
    }
    if not report_trade_deals:
        raise ValueError("report contains no symbol trade deals")
    if len(report_trade_deals) != len(
        [
            deal
            for deal in report_deals
            if deal.deal_id > 0
            and deal.symbol == symbol
            and str(deal.direction or "").strip().lower().startswith(("in", "out"))
        ]
    ):
        raise ValueError("report contains duplicate deal IDs")

    groups: dict[str, list[tuple[dict[str, str], Deal, int]]] = defaultdict(list)
    seen_deals: set[int] = set()
    for row_number, row in enumerate(rows, start=2):
        if str(row.get("symbol") or "") != symbol:
            raise ValueError(f"lifecycle row {row_number} symbol does not match run")
        position_id = str(row.get("position_id") or "").strip()
        if not position_id or position_id == "0":
            raise ValueError(f"lifecycle row {row_number} has invalid position_id")
        deal_id = integer(row.get("deal"), f"lifecycle row {row_number} deal")
        if deal_id <= 0 or deal_id in seen_deals:
            raise ValueError(f"lifecycle row {row_number} has duplicate/invalid deal")
        seen_deals.add(deal_id)
        report_deal = report_trade_deals.get(deal_id)
        if report_deal is None:
            raise ValueError(f"lifecycle row {row_number} deal is absent from report")
        action = str(row.get("action") or "")
        report_direction = str(report_deal.direction or "").strip().lower()
        if action == "OPEN":
            if not report_direction.startswith("in"):
                raise ValueError(f"lifecycle row {row_number} OPEN does not bind an entry deal")
            expected_side = str(row.get("order_type") or "").strip().lower()
        elif action in {"CLOSE", "CLOSE_PARTIAL"}:
            if not report_direction.startswith("out"):
                raise ValueError(f"lifecycle row {row_number} close does not bind an exit deal")
            entry_side = str(row.get("order_type") or "").strip().upper()
            expected_side = "sell" if entry_side == "BUY" else "buy" if entry_side == "SELL" else ""
        else:
            raise ValueError(f"lifecycle row {row_number} has unsupported action")
        if expected_side != str(report_deal.side or "").strip().lower():
            raise ValueError(f"lifecycle row {row_number} order side does not match report deal")
        volume = positive(row.get("volume"), f"lifecycle row {row_number} volume")
        price = positive(row.get("price"), f"lifecycle row {row_number} price")
        if not close_enough(volume, abs(report_deal.volume), max(1e-8, abs(report_deal.volume) * 1e-6)):
            raise ValueError(f"lifecycle row {row_number} volume does not match report deal")
        if not close_enough(price, report_deal.price, max(point, 1e-9)):
            raise ValueError(f"lifecycle row {row_number} price does not match report deal")
        profit, commission, swap, fee, _ = _deal_economics(row, row_number)
        if not close_enough(profit, report_deal.profit, 0.011):
            raise ValueError(f"lifecycle row {row_number} profit does not match report deal")
        if not close_enough(swap, report_deal.swap, 0.011):
            raise ValueError(f"lifecycle row {row_number} swap does not match report deal")
        if not close_enough(commission + fee, report_deal.commission, 0.011):
            raise ValueError(f"lifecycle row {row_number} commission+fee does not match report deal")
        groups[position_id].append((row, report_deal, row_number))

    if seen_deals != set(report_trade_deals):
        missing = sorted(set(report_trade_deals) - seen_deals)
        extra = sorted(seen_deals - set(report_trade_deals))
        raise ValueError(f"report/lifecycle deal-set mismatch; missing={missing} extra={extra}")

    repricing: list[dict[str, Any]] = []
    for position_id, items in sorted(groups.items()):
        opens = [item for item in items if item[0].get("action") == "OPEN"]
        closes = [item for item in items if item[0].get("action") in {"CLOSE", "CLOSE_PARTIAL"}]
        finals = [item for item in closes if str(item[0].get("is_final_close") or "") == "1"]
        if not opens or not closes or len(finals) != 1:
            raise ValueError(
                f"position {position_id} requires one-or-more opens/closes and exactly one final close"
            )
        if finals[0][1].deal_id != max(item[1].deal_id for item in closes):
            raise ValueError(f"position {position_id} final-close marker is not the last exit deal")
        open_volume = sum(positive(item[0].get("volume"), "open volume") for item in opens)
        close_volume = sum(positive(item[0].get("volume"), "close volume") for item in closes)
        if not close_enough(close_volume, open_volume, max(1e-8, open_volume * 1e-6)):
            raise ValueError(f"position {position_id} close volume does not reconcile to open volume")
        directions = {str(item[0].get("order_type") or "").upper() for item in opens}
        if len(directions) != 1 or next(iter(directions)) not in {"BUY", "SELL"}:
            raise ValueError(f"position {position_id} has inconsistent entry directions")
        total_risk = 0.0
        slippage_weight = 0.0
        for row, _, _ in opens:
            risk_points = positive(row.get("risk_pts"), f"position {position_id} risk_pts")
            risk_account = positive(
                row.get("initial_risk_account"),
                f"position {position_id} initial_risk_account",
            )
            risk_pips = risk_points * point / pip_size
            if risk_pips <= 0:
                raise ValueError(f"position {position_id} has nonpositive risk_pips")
            total_risk += risk_account
            slippage_weight += risk_account / risk_pips
        gross_account = sum(item[1].profit for item in items)
        swap_account = sum(item[1].swap for item in items)
        fee_account = sum(item[1].commission for item in items)
        report_net = gross_account + swap_account + fee_account
        repricing.append(
            {
                "trade_id": position_id,
                "deal_ids": sorted(item[1].deal_id for item in items),
                "exit_time": finals[0][1].time.strftime("%Y.%m.%d %H:%M:%S"),
                "direction": next(iter(directions)),
                "entry_volume": open_volume,
                "initial_risk_account": total_risk,
                "slippage_r_weight": slippage_weight / total_risk,
                "gross_r": gross_account / total_risk,
                "swap_r": swap_account / total_risk,
                "reported_fee_r": fee_account / total_risk,
                "reported_net_r": report_net / total_risk,
            }
        )
    return repricing


def scenario_rows(
    repricing: list[dict[str, Any]],
    commission_per_lot: float,
    slippage_roundturn_pips: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    enriched: list[dict[str, Any]] = []
    for row in repricing:
        item = dict(row)
        item["commission_r"] = (
            commission_per_lot * item["entry_volume"] / item["initial_risk_account"]
        )
        item["slippage_r"] = slippage_roundturn_pips * item.pop("slippage_r_weight")
        enriched.append(item)

    scenarios: list[dict[str, Any]] = []
    for label, multiplier in (
        ("cost_x1_00", 1.0),
        ("cost_x1_50", 1.5),
        ("cost_x2_00", 2.0),
    ):
        values = [
            row["gross_r"]
            + row["swap_r"]
            - multiplier * (row["commission_r"] + row["slippage_r"])
            for row in enriched
        ]
        positive_sum = sum(value for value in values if value > 0)
        negative_sum = sum(value for value in values if value < 0)
        loss_count = sum(1 for value in values if value < 0)
        if loss_count <= 0 or negative_sum >= 0:
            raise ValueError(f"{label} has no realized loss denominator; PF is undefined")
        scenarios.append(
            {
                "scenario": label,
                "cost_multiplier": multiplier,
                "trade_count": len(values),
                "loss_count": loss_count,
                "sum_positive_net_r": round(positive_sum, 9),
                "sum_negative_net_r": round(negative_sum, 9),
                "net_r": round(sum(values), 9),
                "profit_factor": round(positive_sum / abs(negative_sum), 9),
            }
        )
    return scenarios, enriched


def build(report: Path, cost_source_path: Path) -> dict[str, Any]:
    report = report.resolve()
    cost_source_path = cost_source_path.resolve()
    if not report.is_file() or not cost_source_path.is_file():
        raise ValueError("report and cost-source manifest must exist")
    run_dir = report.parent
    manifest_path = run_dir / "run_manifest.json"
    manifest = load_json(manifest_path)
    if not same_path(manifest.get("report_path"), report):
        raise ValueError("run_manifest.report_path does not match report")
    report_sha = sha256_file(report)
    if str(manifest.get("report_sha256") or "").upper() != report_sha:
        raise ValueError("run_manifest.report_sha256 does not match report")
    provenance = validate_cost_source(load_json(cost_source_path), cost_source_path, manifest)
    lifecycle_path, lifecycle_sha = lifecycle_sidecar(manifest, run_dir)
    geometry = provenance["symbol_geometry"]
    repricing = parse_lifecycle(
        lifecycle_path,
        str(manifest.get("symbol") or ""),
        geometry["point"],
        geometry["pip_size"],
        parse_deals(report),
    )
    scenarios, enriched = scenario_rows(
        repricing,
        provenance.pop("commission_value"),
        provenance.pop("slippage_p90_roundturn"),
    )
    x1_5 = next(row for row in scenarios if row["scenario"] == "cost_x1_50")
    research_proxy = provenance.get("evidence_tier") == RESEARCH_PROXY_TIER
    return {
        "schema_version": RESEARCH_PROXY_SCHEMA_VERSION if research_proxy else SCHEMA_VERSION,
        "provenance_status": "VERIFIED_RESEARCH_PROXY" if research_proxy else "VERIFIED",
        "stress_mode": (
            "run_bound_research_cost_proxy_repricing"
            if research_proxy
            else "verified_report_deal_lifecycle_r_repricing"
        ),
        "promotion_eligible": not research_proxy,
        "report": str(report),
        "report_sha256": report_sha,
        "run_id": manifest.get("run_id"),
        "hypothesis_id": manifest.get("hypothesis_id"),
        "run_identity_sha256": _run_identity_sha256(manifest, report_sha),
        "cost_source_manifest": str(cost_source_path),
        "cost_source_manifest_sha256": sha256_file(cost_source_path),
        "lifecycle_evidence": {
            "source": str(lifecycle_path),
            "sha256": lifecycle_sha,
            "schema_version": TELEMETRY_SCHEMA,
            "completed_positions": len(enriched),
            "deal_count": sum(len(item["deal_ids"]) for item in enriched),
        },
        "execution_provenance": provenance,
        "trade_repricing": enriched,
        "scenarios": scenarios,
        "net_r_x1_5": x1_5["net_r"],
        "producer": {
            "script": str(Path(__file__).resolve()),
            "script_sha256": sha256_file(Path(__file__).resolve()),
        },
    }


def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--cost-source-manifest", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        output = Path(args.out).resolve()
        payload = build(Path(args.report), Path(args.cost_source_manifest))
        write_atomic(output, payload)
        print(json.dumps(payload, indent=2))
        return 0
    except Exception as exc:
        print(f"VERIFIED_COST_BUILD_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
