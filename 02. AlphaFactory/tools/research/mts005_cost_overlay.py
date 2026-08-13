"""Apply the frozen MTS005 commission, slippage and financing contract.

This tool is deliberately downstream of an MT5 run.  It verifies every input
hash, reconciles EA telemetry with the report summary, and never authorizes an
economic or performance verdict by itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


HYPOTHESIS_ID = "HYP-MULTI-TSMOM-D1-005"
EXPOSURE_RE = re.compile(
    r"MTS005_FINANCE_EXPOSURE\s+epoch=(?P<epoch>\d+)\s+"
    r"day=(?P<day>\d{8})\s+reason=(?P<reason>[A-Za-z0-9_.-]+)\s+"
    r"fx_usd=(?P<fx>-?\d+(?:\.\d+)?)\s+"
    r"xau_usd=(?P<xau>-?\d+(?:\.\d+)?)\s+"
    r"btc_usd=(?P<btc>-?\d+(?:\.\d+)?)"
)
ECON_RE = re.compile(
    r"MTS005_ECON_TELEMETRY\s+ticks=(?P<ticks>\d+)\s+"
    r"deal_profit=(?P<profit>-?\d+(?:\.\d+)?)\s+"
    r"deal_swap=(?P<swap>-?\d+(?:\.\d+)?)\s+"
    r"deal_commission=(?P<commission>-?\d+(?:\.\d+)?)\s+"
    r"native_net=(?P<net>-?\d+(?:\.\d+)?)"
)
DEAL_RE = re.compile(
    r"MTS005_DEAL_COST\s+epoch=(?P<epoch>\d+)\s+deal=(?P<deal>\d+)\s+"
    r"symbol=(?P<symbol>\S+)\s+class=(?P<class>FX|XAU|BTC|UNKNOWN)\s+"
    r"entry=(?P<entry>-?\d+)\s+type=(?P<type>-?\d+)\s+"
    r"volume=(?P<volume>-?\d+(?:\.\d+)?)\s+"
    r"price=(?P<price>-?\d+(?:\.\d+)?)\s+"
    r"spread_points=(?P<spread>-?\d+)\s+"
    r"one_spread_cost_usd=(?P<spread_cost>-?\d+(?:\.\d+)?)\s+"
    r"native_profit=(?P<profit>-?\d+(?:\.\d+)?)\s+"
    r"native_swap=(?P<swap>-?\d+(?:\.\d+)?)\s+"
    r"native_commission=(?P<commission>-?\d+(?:\.\d+)?)"
)


class CostOverlayError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExposureEvent:
    epoch: int
    day: date
    reason: str
    fx_usd: float
    xau_usd: float
    btc_usd: float


@dataclass(frozen=True)
class DealCost:
    epoch: int
    deal: int
    symbol: str
    asset_class: str
    entry: int
    deal_type: int
    volume: float
    price: float
    spread_points: int
    one_spread_cost_usd: float
    native_profit: float
    native_swap: float
    native_commission: float


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha256(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", expected) or actual != expected.upper():
        raise CostOverlayError(f"{label} SHA256 mismatch: expected {expected}, got {actual}")
    return actual


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise CostOverlayError(f"expected JSON object: {path}")
    return payload


def parse_date(value: str) -> date:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise CostOverlayError(f"invalid date: {value}")


def _finite_nonnegative(value: object, label: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise CostOverlayError(f"{label} must be finite and nonnegative")
    return result


def parse_exposures(text: str) -> list[ExposureEvent]:
    rows: list[ExposureEvent] = []
    seen: set[tuple[object, ...]] = set()
    for match in EXPOSURE_RE.finditer(text):
        row = ExposureEvent(
            epoch=int(match.group("epoch")),
            day=datetime.strptime(match.group("day"), "%Y%m%d").date(),
            reason=match.group("reason"),
            fx_usd=_finite_nonnegative(match.group("fx"), "fx exposure"),
            xau_usd=_finite_nonnegative(match.group("xau"), "xau exposure"),
            btc_usd=_finite_nonnegative(match.group("btc"), "btc exposure"),
        )
        key = tuple(row.__dict__.values())
        if key not in seen:
            seen.add(key)
            rows.append(row)
    if not rows:
        raise CostOverlayError("no MTS005_FINANCE_EXPOSURE rows")
    if any(rows[i].epoch > rows[i + 1].epoch for i in range(len(rows) - 1)):
        raise CostOverlayError("exposure rows are not epoch-monotonic")
    return rows


def parse_economic_telemetry(text: str) -> dict[str, float | int]:
    rows = {
        (
            int(m.group("ticks")),
            float(m.group("profit")),
            float(m.group("swap")),
            float(m.group("commission")),
            float(m.group("net")),
        )
        for m in ECON_RE.finditer(text)
    }
    if len(rows) != 1:
        raise CostOverlayError(f"expected one distinct MTS005_ECON_TELEMETRY row, got {len(rows)}")
    ticks, profit, swap, commission, net = rows.pop()
    if not math.isclose(profit + swap + commission, net, abs_tol=0.02):
        raise CostOverlayError("native telemetry components do not reconcile")
    return {
        "ticks": ticks,
        "deal_profit": profit,
        "deal_swap": swap,
        "deal_commission": commission,
        "native_net": net,
    }


def parse_deals(text: str) -> list[DealCost]:
    by_id: dict[int, DealCost] = {}
    for match in DEAL_RE.finditer(text):
        row = DealCost(
            epoch=int(match.group("epoch")),
            deal=int(match.group("deal")),
            symbol=match.group("symbol"),
            asset_class=match.group("class").lower(),
            entry=int(match.group("entry")),
            deal_type=int(match.group("type")),
            volume=float(match.group("volume")),
            price=float(match.group("price")),
            spread_points=int(match.group("spread")),
            one_spread_cost_usd=float(match.group("spread_cost")),
            native_profit=float(match.group("profit")),
            native_swap=float(match.group("swap")),
            native_commission=float(match.group("commission")),
        )
        if (
            row.asset_class not in {"fx", "xau", "btc"}
            or not math.isfinite(row.volume)
            or not math.isfinite(row.price)
            or not math.isfinite(row.one_spread_cost_usd)
            or row.volume <= 0.0
            or row.price <= 0.0
            or row.spread_points < 1
            or row.one_spread_cost_usd < 0.0
            or row.native_commission > 1e-8
        ):
            raise CostOverlayError(f"invalid deal cost row: {row}")
        previous = by_id.get(row.deal)
        if previous is not None and previous != row:
            raise CostOverlayError(f"conflicting duplicate deal telemetry: {row.deal}")
        by_id[row.deal] = row
    rows = sorted(by_id.values(), key=lambda row: (row.epoch, row.deal))
    if not rows:
        raise CostOverlayError("no MTS005_DEAL_COST rows")
    return rows


def find_repo_root(path: Path) -> Path:
    for candidate in path.resolve().parents:
        if (candidate / "02. AlphaFactory").is_dir() and (candidate / "03. EA Developer").is_dir():
            return candidate
    raise CostOverlayError(f"cannot find repository root from {path}")


def verify_source_receipts(contract: dict[str, object], path: Path) -> list[dict[str, str]]:
    receipts = contract.get("source_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise CostOverlayError("cost contract source receipts are missing")
    root = find_repo_root(path)
    verified: list[dict[str, str]] = []
    for index, row in enumerate(receipts):
        if not isinstance(row, dict) or not isinstance(row.get("path"), str) or not isinstance(row.get("sha256"), str):
            raise CostOverlayError(f"invalid source receipt {index}")
        relative = Path(str(row["path"]))
        if relative.is_absolute():
            raise CostOverlayError("source receipt path must be relative")
        resolved = (root / relative).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise CostOverlayError(f"source receipt escapes repository: {relative}") from exc
        if not resolved.is_file():
            raise CostOverlayError(f"source receipt missing: {relative}")
        verified.append({"path": relative.as_posix(), "sha256": require_sha256(resolved, str(row["sha256"]), f"source receipt {index}")})
    return verified


def validate_contract(contract: dict[str, object]) -> None:
    if contract.get("schema_version") != "mts005_cost_contract.v1" or contract.get("hypothesis_id") != HYPOTHESIS_ID:
        raise CostOverlayError("cost contract identity mismatch")
    if contract.get("status") != "FROZEN_BEFORE_ECONOMICS":
        raise CostOverlayError("cost contract was not frozen before economics")
    if contract.get("historical_pit_financing_proven") is not False:
        raise CostOverlayError("cost contract must not claim historical PIT financing")
    commissions = contract.get("commission_per_side")
    financing = contract.get("financing")
    scenarios = contract.get("scenarios")
    if not isinstance(commissions, dict) or set(commissions) != {"fx", "xau", "btc"}:
        raise CostOverlayError("commission contract is incomplete")
    expected_commission = {
        "fx": ("usd_per_standard_lot", 2.0),
        "xau": ("deal_notional_fraction", 0.00001),
        "btc": ("deal_notional_fraction", 0.0003),
    }
    for name, (basis, value) in expected_commission.items():
        row = commissions[name]
        if not isinstance(row, dict) or row.get("basis") != basis or float(row.get("value", -1)) != value:
            raise CostOverlayError(f"unexpected {name} commission contract")
    if not isinstance(financing, dict) or int(financing.get("day_count_denominator", 0)) != 365:
        raise CostOverlayError("invalid financing contract")
    classes = financing.get("class_contracts")
    if not isinstance(classes, dict) or set(classes) != {"fx", "xau", "btc"}:
        raise CostOverlayError("financing classes are incomplete")
    if not isinstance(scenarios, dict) or list(scenarios) != ["base", "adverse", "severe"]:
        raise CostOverlayError("scenario contract is incomplete or reordered")
    expected = {"base": (1.0, 0.25, 1.0), "adverse": (1.25, 0.5, 1.5), "severe": (1.5, 1.0, 2.0)}
    for name, values in expected.items():
        row = scenarios[name]
        observed = (float(row["commission_multiplier"]), float(row["slippage_multiplier"]), float(row["financing_multiplier"]))
        if observed != values:
            raise CostOverlayError(f"unexpected scenario contract: {name}")


def expected_commission(deal: DealCost, contract: dict[str, object]) -> float:
    rows = contract["commission_per_side"]
    assert isinstance(rows, dict)
    row = rows[deal.asset_class]
    assert isinstance(row, dict)
    value = float(row["value"])
    if deal.asset_class == "fx":
        return deal.volume * value
    contract_size = float(row["contract_size"])
    return deal.volume * deal.price * contract_size * value


def financing_base_cost(events: list[ExposureEvent], start: date, end: date, contract: dict[str, object]) -> dict[str, object]:
    if end <= start:
        raise CostOverlayError("end must be after start")
    financing = contract["financing"]
    assert isinstance(financing, dict)
    classes = financing["class_contracts"]
    assert isinstance(classes, dict)
    by_day: dict[date, list[ExposureEvent]] = {}
    for event in events:
        if start <= event.day < end:
            by_day.setdefault(event.day, []).append(event)
    state: ExposureEvent | None = None
    weighted = {"fx": 0.0, "xau": 0.0, "btc": 0.0}
    observed = carried = leading_zero = 0
    current = start
    while current < end:
        if current in by_day:
            state = by_day[current][-1]
            observed += 1
        else:
            carried += 1
        if state is None:
            leading_zero += 1
            current += timedelta(days=1)
            continue
        for name in weighted:
            row = classes[name]
            assert isinstance(row, dict)
            coefficients = row["weekday_coefficients_monday_first"]
            value = getattr(state, f"{name}_usd")
            weighted[name] += value * float(coefficients[current.weekday()])
        current += timedelta(days=1)
    by_class = {}
    for name, value in weighted.items():
        row = classes[name]
        assert isinstance(row, dict)
        by_class[name] = value * float(row["base_annual_rate"]) / 365.0
    return {
        "calendar_days": (end - start).days,
        "observed_event_days": observed,
        "carried_days": carried,
        "leading_zero_days": leading_zero,
        "weighted_notional_days": weighted,
        "base_cost_by_class_usd": by_class,
        "base_cost_usd": sum(by_class.values()),
    }


def calculate(text: str, summary: dict[str, object], contract: dict[str, object], start: date, end: date) -> dict[str, object]:
    validate_contract(contract)
    telemetry = parse_economic_telemetry(text)
    deals = parse_deals(text)
    exposure = parse_exposures(text)
    native_net = float(summary.get("net_profit", math.nan))
    if not math.isfinite(native_net) or not math.isclose(native_net, float(telemetry["native_net"]), abs_tol=0.02):
        raise CostOverlayError("report net_profit disagrees with EA telemetry")
    deal_profit = sum(row.native_profit for row in deals)
    deal_swap = sum(row.native_swap for row in deals)
    deal_commission = sum(row.native_commission for row in deals)
    if not math.isclose(deal_profit, float(telemetry["deal_profit"]), abs_tol=0.05) or not math.isclose(deal_swap, float(telemetry["deal_swap"]), abs_tol=0.05) or not math.isclose(deal_commission, float(telemetry["deal_commission"]), abs_tol=0.05):
        raise CostOverlayError("deal telemetry does not reconcile with terminal aggregate")
    expected_by_class = {"fx": 0.0, "xau": 0.0, "btc": 0.0}
    native_by_class = {"fx": 0.0, "xau": 0.0, "btc": 0.0}
    spread_by_class = {"fx": 0.0, "xau": 0.0, "btc": 0.0}
    count_by_class = {"fx": 0, "xau": 0, "btc": 0}
    for deal in deals:
        expected_by_class[deal.asset_class] += expected_commission(deal, contract)
        native_by_class[deal.asset_class] += abs(deal.native_commission)
        spread_by_class[deal.asset_class] += deal.one_spread_cost_usd
        count_by_class[deal.asset_class] += 1
    expected_total = sum(expected_by_class.values())
    native_total = sum(native_by_class.values())
    one_spread_total = sum(spread_by_class.values())
    financing = financing_base_cost(exposure, start, end, contract)
    pre_controlled_financing = native_net - float(telemetry["deal_swap"])
    scenarios = contract["scenarios"]
    assert isinstance(scenarios, dict)
    scenario_results: dict[str, object] = {}
    for name, row in scenarios.items():
        assert isinstance(row, dict)
        commission_target = expected_total * float(row["commission_multiplier"])
        commission_shortfall = max(0.0, commission_target - native_total)
        slippage_cost = one_spread_total * float(row["slippage_multiplier"])
        financing_cost = float(financing["base_cost_usd"]) * float(row["financing_multiplier"])
        scenario_results[name] = {
            "commission_target_usd": commission_target,
            "native_commission_abs_usd": native_total,
            "commission_shortfall_usd": commission_shortfall,
            "extra_slippage_usd": slippage_cost,
            "financing_usd": financing_cost,
            "adjusted_net_usd": pre_controlled_financing - commission_shortfall - slippage_cost - financing_cost,
        }
    return {
        "native": telemetry,
        "pre_controlled_financing_net_usd": pre_controlled_financing,
        "deal_costs": {
            "deal_count": len(deals),
            "deal_count_by_class": count_by_class,
            "expected_base_commission_by_class_usd": expected_by_class,
            "native_commission_abs_by_class_usd": native_by_class,
            "one_spread_cost_by_class_usd": spread_by_class,
        },
        "financing": financing,
        "scenarios": scenario_results,
    }


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply frozen MTS005 cost overlay")
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--journal-sha256", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--summary-sha256", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    journal_sha = require_sha256(args.journal, args.journal_sha256, "journal")
    summary_sha = require_sha256(args.summary, args.summary_sha256, "summary")
    contract_sha = require_sha256(args.contract, args.contract_sha256, "contract")
    contract = load_json(args.contract)
    verified = verify_source_receipts(contract, args.contract)
    result = calculate(
        args.journal.read_text(encoding="utf-8-sig", errors="strict"),
        load_json(args.summary),
        contract,
        parse_date(args.from_date),
        parse_date(args.to_date),
    )
    payload: dict[str, object] = {
        "schema_version": "mts005_cost_overlay_result.v1",
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "PASS_CALCULATION",
        "inputs": {
            "journal_path": args.journal.resolve().as_posix(),
            "journal_sha256": journal_sha,
            "summary_path": args.summary.resolve().as_posix(),
            "summary_sha256": summary_sha,
            "contract_path": args.contract.resolve().as_posix(),
            "contract_sha256": contract_sha,
            "source_receipt_bindings": verified,
            "from": parse_date(args.from_date).isoformat(),
            "to_exclusive": parse_date(args.to_date).isoformat(),
        },
        **result,
        "calculation_valid": True,
        "historical_pit_financing_proven": False,
        "economic_verdict_authorized": False,
        "performance_verdict_authorized": False,
    }
    write_json_atomic(args.output, payload)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CostOverlayError as exc:
        print(f"FATAL {exc}")
        raise SystemExit(2)
