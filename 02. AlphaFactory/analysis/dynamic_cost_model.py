#!/usr/bin/env python3
"""Deterministic volume/liquidity/volatility market-impact stress model.

Schema v1 is diagnostic-only.  It estimates one-way fill cost as half-spread
plus square-root impact, converts every component to one account currency, and
never promotes a manifest hash check into an economic-evidence claim.  It does
not replace broker fill/TCA provenance or the verified execution-cost builder.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "alphafactory_dynamic_cost.v1"
CALIBRATION_SCHEMA = "alphafactory_impact_calibration.v1"
REQUIRED_FILL_FIELDS = {
    "fill_id",
    "trade_id",
    "timestamp",
    "symbol",
    "side",
    "quantity",
    "quantity_unit",
    "reference_price",
    "spread_price",
    "volatility_bps",
    "liquidity_quantity",
    "quote_currency",
    "quote_to_account_rate",
    "commission_account",
    "account_currency",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _positive(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"{label} must be finite and > 0")
    return parsed


def _nonnegative(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"{label} must be finite and >= 0")
    return parsed


def _finite_derived(value: float, label: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{label} overflowed or is not finite")
    return value


def _currency(value: Any, label: str) -> str:
    parsed = str(value or "").strip().upper()
    if not parsed or len(parsed) > 12:
        raise ValueError(f"{label} must be a non-empty currency/unit code")
    return parsed


def _timestamp(value: Any) -> str:
    raw = str(value or "").strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include an explicit timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def estimate_fill_cost(fill: Mapping[str, Any], *, eta: float) -> dict[str, Any]:
    missing = REQUIRED_FILL_FIELDS - set(fill)
    if missing:
        raise ValueError(f"fill is missing fields: {sorted(missing)}")
    eta_value = _positive(eta, "eta")
    quantity = _positive(fill.get("quantity"), "quantity")
    if fill.get("quantity_unit") != "base_units":
        raise ValueError("quantity_unit must be base_units")
    reference_price = _positive(fill.get("reference_price"), "reference_price")
    spread_price = _nonnegative(fill.get("spread_price"), "spread_price")
    volatility_bps = _nonnegative(fill.get("volatility_bps"), "volatility_bps")
    liquidity_quantity = _positive(fill.get("liquidity_quantity"), "liquidity_quantity")
    quote_currency = _currency(fill.get("quote_currency"), "quote_currency")
    account_currency = _currency(fill.get("account_currency"), "account_currency")
    quote_to_account_rate = _positive(
        fill.get("quote_to_account_rate"), "quote_to_account_rate"
    )
    if quote_currency == account_currency and not math.isclose(
        quote_to_account_rate, 1.0, rel_tol=0.0, abs_tol=1e-12
    ):
        raise ValueError("quote_to_account_rate must equal 1 when currencies match")
    commission_account = _nonnegative(
        fill.get("commission_account"), "commission_account"
    )
    side = str(fill.get("side") or "").upper()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    fill_id = str(fill.get("fill_id") or "").strip()
    trade_id = str(fill.get("trade_id") or "").strip()
    symbol = str(fill.get("symbol") or "").strip()
    if not fill_id or not trade_id or not symbol:
        raise ValueError("fill_id, trade_id, and symbol are required")

    participation = _finite_derived(quantity / liquidity_quantity, "participation_rate")
    normalized_timestamp = _timestamp(fill.get("timestamp"))
    spread_bps = _finite_derived(
        spread_price / reference_price * 10_000.0, "spread_bps"
    )
    impact_bps = _finite_derived(
        eta_value * volatility_bps * math.sqrt(participation), "impact_bps"
    )
    notional_quote = _finite_derived(quantity * reference_price, "notional_quote")
    half_spread_cost_quote = _finite_derived(
        notional_quote * (spread_bps * 0.5) / 10_000.0,
        "half_spread_cost_quote",
    )
    impact_cost_quote = _finite_derived(
        notional_quote * impact_bps / 10_000.0, "impact_cost_quote"
    )
    half_spread_cost_account = _finite_derived(
        half_spread_cost_quote * quote_to_account_rate,
        "half_spread_cost_account",
    )
    impact_cost_account = _finite_derived(
        impact_cost_quote * quote_to_account_rate, "impact_cost_account"
    )
    total_cost_account = _finite_derived(
        half_spread_cost_account + impact_cost_account + commission_account,
        "estimated_total_cost_account",
    )
    return {
        "fill_id": fill_id,
        "trade_id": trade_id,
        "timestamp": normalized_timestamp,
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "quantity_unit": "base_units",
        "reference_price": reference_price,
        "quote_currency": quote_currency,
        "account_currency": account_currency,
        "quote_to_account_rate": quote_to_account_rate,
        "notional_quote": notional_quote,
        "spread_price": spread_price,
        "spread_bps": spread_bps,
        "volatility_bps": volatility_bps,
        "liquidity_quantity": liquidity_quantity,
        "participation_rate": participation,
        "eta": eta_value,
        "impact_bps": impact_bps,
        "half_spread_cost_quote": half_spread_cost_quote,
        "impact_cost_quote": impact_cost_quote,
        "half_spread_cost_account": half_spread_cost_account,
        "impact_cost_account": impact_cost_account,
        "commission_account": commission_account,
        "estimated_total_cost_account": total_cost_account,
    }


def load_calibration(path: Path | str) -> dict[str, Any]:
    calibration_path = Path(path)
    if not calibration_path.is_file():
        raise ValueError(f"calibration JSON not found: {calibration_path}")
    try:
        payload = json.loads(calibration_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid calibration JSON: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != CALIBRATION_SCHEMA:
        raise ValueError(f"calibration schema_version must be {CALIBRATION_SCHEMA}")
    if payload.get("source_kind") != "observed_depth":
        raise ValueError("schema v1 calibration requires source_kind=observed_depth")
    if payload.get("quantity_unit") != "base_units":
        raise ValueError("calibration quantity_unit must be base_units")
    eta = _positive(payload.get("eta"), "calibration eta")
    try:
        sample_count = int(payload.get("sample_count"))
    except (TypeError, ValueError) as exc:
        raise ValueError("calibration sample_count must be an integer") from exc
    if sample_count < 1:
        raise ValueError("calibration sample_count must be at least 1")
    if payload.get("frozen_pre_outcome") is not True:
        raise ValueError("calibration must be frozen_pre_outcome=true")
    if payload.get("verification_status") != "UNVERIFIED_DIAGNOSTIC_ONLY":
        raise ValueError(
            "schema v1 calibration verification_status must be "
            "UNVERIFIED_DIAGNOSTIC_ONLY"
        )
    symbol = str(payload.get("symbol") or "").strip()
    if not symbol:
        raise ValueError("calibration symbol is required")

    evidence_raw = str(payload.get("evidence_path") or "").strip()
    if not evidence_raw:
        raise ValueError("calibration evidence_path is required")
    evidence_path = Path(evidence_raw)
    if not evidence_path.is_absolute():
        evidence_path = calibration_path.parent / evidence_path
    evidence_path = evidence_path.resolve()
    if not evidence_path.is_file():
        raise ValueError(f"calibration evidence is missing: {evidence_path}")
    expected_hash = str(payload.get("evidence_sha256") or "").lower()
    actual_hash = _sha256(evidence_path)
    if expected_hash != actual_hash:
        raise ValueError(
            f"calibration evidence SHA256 mismatch: expected {expected_hash}, actual {actual_hash}"
        )
    if evidence_path.suffix.lower() != ".csv":
        raise ValueError("calibration evidence must be a CSV in schema v1")
    with evidence_path.open("r", encoding="utf-8-sig", newline="") as handle:
        evidence_reader = csv.reader(handle)
        try:
            next(evidence_reader)
        except StopIteration as exc:
            raise ValueError("calibration evidence CSV is empty") from exc
        observed_sample_count = sum(1 for row in evidence_reader if any(cell.strip() for cell in row))
    if observed_sample_count != sample_count:
        raise ValueError(
            "calibration sample_count does not match evidence rows: "
            f"declared {sample_count}, observed {observed_sample_count}"
        )
    return {
        **payload,
        "eta": eta,
        "sample_count": sample_count,
        "symbol": symbol,
        "calibration_path": str(calibration_path.resolve()),
        "calibration_sha256": _sha256(calibration_path),
        "evidence_path": str(evidence_path),
        "evidence_sha256": actual_hash,
        "manifest_verified": True,
        "hash_integrity_verified": True,
        "calibration_recomputed": False,
        "verification_status": "MANIFEST_HASH_ONLY",
    }


def _profit_factor(values: Sequence[float]) -> float | None:
    gross_profit = _finite_derived(
        sum(value for value in values if value > 0.0), "gross_profit"
    )
    gross_loss = _finite_derived(
        -sum(value for value in values if value < 0.0), "gross_loss"
    )
    if gross_loss == 0.0:
        return None
    return _finite_derived(gross_profit / gross_loss, "profit_factor")


def build_cost_audit(
    fills: Sequence[Mapping[str, Any]],
    trade_pnl_by_id: Mapping[str, float],
    *,
    source_kind: str,
    eta: float,
    calibration: Mapping[str, Any] | None,
    account_currency: str,
    pnl_basis: str,
) -> dict[str, Any]:
    if source_kind not in {"adv_proxy", "observed_depth"}:
        raise ValueError("source_kind must be adv_proxy or observed_depth")
    if not fills:
        raise ValueError("at least one fill is required")
    if not trade_pnl_by_id:
        raise ValueError("trade PnL mapping is required")
    normalized_account_currency = _currency(account_currency, "account_currency")
    if pnl_basis != "mid_reference_before_modeled_costs":
        raise ValueError(
            "pnl_basis must be mid_reference_before_modeled_costs in schema v1"
        )
    if source_kind == "observed_depth" and calibration is None:
        raise ValueError("observed_depth requires a hash-bound calibration manifest")
    if source_kind == "adv_proxy" and calibration is not None:
        raise ValueError("adv_proxy must not use an observed-depth calibration")

    eta_value = _positive(eta, "eta")
    if calibration is not None:
        if calibration.get("manifest_verified") is not True:
            raise ValueError("calibration manifest must be verified by load_calibration")
        calibrated_eta = _positive(calibration.get("eta"), "calibration eta")
        if abs(calibrated_eta - eta_value) > 1e-12:
            raise ValueError("eta does not match the hash-bound calibration")

    estimated = [estimate_fill_cost(fill, eta=eta_value) for fill in fills]
    fill_ids = [row["fill_id"] for row in estimated]
    if len(set(fill_ids)) != len(fill_ids):
        raise ValueError("fill_id values must be unique")
    symbols = sorted({row["symbol"] for row in estimated})
    currencies = sorted({row["account_currency"] for row in estimated})
    if currencies != [normalized_account_currency]:
        raise ValueError(
            "all fills must use the declared account_currency; "
            f"declared {normalized_account_currency}, fills {currencies}"
        )
    if calibration is not None and symbols != [calibration.get("symbol")]:
        raise ValueError("observed-depth calibration requires an exact single-symbol corpus")

    costs_by_trade: dict[str, float] = {}
    for row in estimated:
        costs_by_trade[row["trade_id"]] = costs_by_trade.get(row["trade_id"], 0.0) + row[
            "estimated_total_cost_account"
        ]
    missing_fill_coverage = sorted(set(trade_pnl_by_id) - set(costs_by_trade))
    unknown_trade_fills = sorted(set(costs_by_trade) - set(trade_pnl_by_id))
    if unknown_trade_fills:
        raise ValueError(f"fills reference unknown trade ids: {unknown_trade_fills}")

    trade_rows: list[dict[str, Any]] = []
    for trade_id, gross_raw in sorted(trade_pnl_by_id.items()):
        try:
            gross_pnl = float(gross_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"trade {trade_id} gross_pnl must be numeric") from exc
        if not math.isfinite(gross_pnl):
            raise ValueError(f"trade {trade_id} gross_pnl must be finite")
        cost = _finite_derived(
            costs_by_trade.get(trade_id, 0.0), f"trade {trade_id} dynamic cost"
        )
        adjusted_pnl = _finite_derived(
            gross_pnl - cost, f"trade {trade_id} adjusted_pnl"
        )
        trade_rows.append(
            {
                "trade_id": trade_id,
                "account_currency": normalized_account_currency,
                "pnl_basis": pnl_basis,
                "gross_pnl_account": gross_pnl,
                "estimated_dynamic_cost_account": cost,
                "adjusted_pnl_account": adjusted_pnl,
                "fill_count": sum(1 for row in estimated if row["trade_id"] == trade_id),
            }
        )

    basic_trade_id_coverage = not missing_fill_coverage
    gross_values = [row["gross_pnl_account"] for row in trade_rows]
    adjusted_values = [row["adjusted_pnl_account"] for row in trade_rows]
    gross_pf = _profit_factor(gross_values)
    adjusted_pf = _profit_factor(adjusted_values)
    return {
        "schema_version": SCHEMA_VERSION,
        "analysis_kind": "conditional_square_root_market_impact_stress",
        "methodology": {
            "formula": "half_spread_bps + eta * volatility_bps * sqrt(quantity/liquidity_quantity)",
            "eta": eta_value,
            "source_kind": source_kind,
            "quantity_unit": "base_units",
            "account_currency": normalized_account_currency,
            "pnl_basis": pnl_basis,
            "spread_counting": "half spread per fill; entry and exit fills sum to round turn",
            "conversion": "quote-currency spread/impact converted per fill before aggregation",
            "impact_granularity": (
                "per fill; partial-fill partition invariance is not established in schema v1"
            ),
        },
        "calibration": dict(calibration) if calibration is not None else None,
        "coverage": {
            "fill_count": len(estimated),
            "trade_count": len(trade_rows),
            "symbols": symbols,
            "missing_trade_fill_coverage": missing_fill_coverage,
            "basic_trade_id_coverage": basic_trade_id_coverage,
            "lifecycle_reconciled": False,
        },
        "summary": {
            "account_currency": normalized_account_currency,
            "gross_pnl_account": _finite_derived(
                sum(gross_values), "summary gross_pnl_account"
            ),
            "estimated_dynamic_cost_account": _finite_derived(
                sum(row["estimated_total_cost_account"] for row in estimated),
                "summary estimated_dynamic_cost_account",
            ),
            "adjusted_pnl_account": _finite_derived(
                sum(adjusted_values), "summary adjusted_pnl_account"
            ),
            "gross_profit_factor": gross_pf,
            "gross_profit_factor_defined": gross_pf is not None,
            "adjusted_profit_factor": adjusted_pf,
            "adjusted_profit_factor_defined": adjusted_pf is not None,
            "max_participation_rate": max(row["participation_rate"] for row in estimated),
            "max_impact_bps": max(row["impact_bps"] for row in estimated),
        },
        "fills": estimated,
        "trades": trade_rows,
        "impact_gate_eligible": False,
        "economic_claim_allowed": False,
        "promotion_eligible": False,
        "limitation": (
            "DIAGNOSTIC_ONLY: schema v1 verifies manifest/file integrity but does not "
            "recompute eta, reconcile the full order lifecycle, or bind causal depth "
            "snapshots. Per-fill impact is not yet invariant to partial-fill partitioning. "
            "It cannot support an economic or promotion claim."
        ),
    }


def _load_csv_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing columns: {sorted(missing)}")
        return [dict(row) for row in reader]


def main() -> int:
    parser = argparse.ArgumentParser(description="Dynamic volume/liquidity/volatility cost audit")
    parser.add_argument("--fills-csv", required=True)
    parser.add_argument(
        "--trades-csv",
        required=True,
        help="CSV with trade_id,gross_pnl,account_currency,pnl_basis",
    )
    parser.add_argument("--source-kind", choices=["adv_proxy", "observed_depth"], required=True)
    parser.add_argument("--eta", type=float, default=0.5)
    parser.add_argument("--calibration", default="")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    try:
        fills_path = Path(args.fills_csv)
        trades_path = Path(args.trades_csv)
        fills = _load_csv_rows(fills_path, REQUIRED_FILL_FIELDS)
        trade_rows = _load_csv_rows(
            trades_path,
            {"trade_id", "gross_pnl", "account_currency", "pnl_basis"},
        )
        trade_pnl: dict[str, float] = {}
        trade_currencies: set[str] = set()
        trade_bases: set[str] = set()
        for row in trade_rows:
            trade_id = str(row.get("trade_id") or "").strip()
            if not trade_id:
                raise ValueError("trade_id must not be empty")
            if trade_id in trade_pnl:
                raise ValueError(f"duplicate trade_id in trades CSV: {trade_id}")
            trade_pnl[trade_id] = float(row["gross_pnl"])
            trade_currencies.add(_currency(row.get("account_currency"), "account_currency"))
            trade_bases.add(str(row.get("pnl_basis") or "").strip())
        if len(trade_currencies) != 1:
            raise ValueError("trades CSV must contain exactly one account_currency")
        if len(trade_bases) != 1:
            raise ValueError("trades CSV must contain exactly one pnl_basis")
        account_currency = next(iter(trade_currencies))
        pnl_basis = next(iter(trade_bases))
        calibration = load_calibration(Path(args.calibration)) if args.calibration else None
        eta = float(calibration["eta"]) if calibration is not None else args.eta
        result = build_cost_audit(
            fills,
            trade_pnl,
            source_kind=args.source_kind,
            eta=eta,
            calibration=calibration,
            account_currency=account_currency,
            pnl_basis=pnl_basis,
        )
        result["inputs"] = {
            "fills_csv": str(fills_path.resolve()),
            "fills_sha256": _sha256(fills_path),
            "trades_csv": str(trades_path.resolve()),
            "trades_sha256": _sha256(trades_path),
        }
        out_dir = Path(args.out) if args.out else fills_path.resolve().parent / "dynamic_cost_analysis"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "dynamic_cost_analysis.json"
        out_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False),
            encoding="utf-8",
        )
        rows_path = out_dir / "dynamic_cost_rows.csv"
        with rows_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result["fills"][0].keys()))
            writer.writeheader()
            writer.writerows(result["fills"])
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"[DYNAMIC COST] {out_path}")
    print(
        f"fills={result['coverage']['fill_count']} "
        f"adjusted_pnl={result['summary']['adjusted_pnl_account']:.6f} "
        "status=DIAGNOSTIC_ONLY claim_allowed=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
