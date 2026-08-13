from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


EXPOSURE_RE = re.compile(
    r"MTS004_FINANCE_EXPOSURE\s+epoch=(?P<epoch>\d+)\s+"
    r"day=(?P<day>\d{8})\s+reason=(?P<reason>[A-Za-z0-9_.-]+)\s+"
    r"fx_usd=(?P<fx>-?\d+(?:\.\d+)?)\s+"
    r"xau_usd=(?P<xau>-?\d+(?:\.\d+)?)\s+"
    r"btc_usd=(?P<btc>-?\d+(?:\.\d+)?)"
)
ECON_RE = re.compile(
    r"MTS004_ECON_TELEMETRY\s+ticks=(?P<ticks>\d+)\s+"
    r"deal_profit=(?P<profit>-?\d+(?:\.\d+)?)\s+"
    r"deal_swap=(?P<swap>-?\d+(?:\.\d+)?)\s+"
    r"deal_commission=(?P<commission>-?\d+(?:\.\d+)?)\s+"
    r"native_net=(?P<net>-?\d+(?:\.\d+)?)"
)


class FinancingOverlayError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExposureEvent:
    epoch: int
    day: date
    reason: str
    fx_usd: float
    xau_usd: float
    btc_usd: float

    def key(self) -> tuple[object, ...]:
        return (
            self.epoch,
            self.day,
            self.reason,
            self.fx_usd,
            self.xau_usd,
            self.btc_usd,
        )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha256(path: Path, expected: str, label: str) -> str:
    actual = sha256_file(path)
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", expected) or actual != expected.upper():
        raise FinancingOverlayError(
            f"{label} SHA256 mismatch: expected {expected}, got {actual}"
        )
    return actual


def parse_date(value: str) -> date:
    for fmt in ("%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise FinancingOverlayError(f"invalid date: {value}")


def parse_exposure_events(text: str) -> list[ExposureEvent]:
    unique: list[ExposureEvent] = []
    seen: set[tuple[object, ...]] = set()
    for match in EXPOSURE_RE.finditer(text):
        event = ExposureEvent(
            epoch=int(match.group("epoch")),
            day=datetime.strptime(match.group("day"), "%Y%m%d").date(),
            reason=match.group("reason"),
            fx_usd=float(match.group("fx")),
            xau_usd=float(match.group("xau")),
            btc_usd=float(match.group("btc")),
        )
        if any(
            not math.isfinite(value) or value < 0.0
            for value in (event.fx_usd, event.xau_usd, event.btc_usd)
        ):
            raise FinancingOverlayError(f"invalid exposure event: {event}")
        if event.key() not in seen:
            seen.add(event.key())
            unique.append(event)
    if not unique:
        raise FinancingOverlayError("no MTS004_FINANCE_EXPOSURE events found")
    if any(unique[index].epoch > unique[index + 1].epoch for index in range(len(unique) - 1)):
        raise FinancingOverlayError("unique exposure events are not epoch-monotonic")
    return unique


def parse_unique_economic_telemetry(text: str) -> dict[str, float | int]:
    rows = {
        (
            int(match.group("ticks")),
            float(match.group("profit")),
            float(match.group("swap")),
            float(match.group("commission")),
            float(match.group("net")),
        )
        for match in ECON_RE.finditer(text)
    }
    if len(rows) != 1:
        raise FinancingOverlayError(
            f"expected one distinct MTS004_ECON_TELEMETRY row, found {len(rows)}"
        )
    ticks, profit, swap, commission, net = rows.pop()
    if not math.isclose(profit + swap + commission, net, abs_tol=0.02):
        raise FinancingOverlayError("MTS004 native_net does not equal its deal components")
    return {
        "ticks": ticks,
        "deal_profit": profit,
        "deal_swap": swap,
        "deal_commission": commission,
        "native_net": net,
    }


def _validate_contract(contract: dict[str, object]) -> dict[str, dict[str, object]]:
    if contract.get("schema_version") != "mts004_financing_contract.v1":
        raise FinancingOverlayError("unsupported financing contract schema")
    if contract.get("hypothesis_id") != "HYP-MULTI-TSMOM-D1-004":
        raise FinancingOverlayError("financing contract hypothesis mismatch")
    if contract.get("historical_pit_financing_proven") is not False:
        raise FinancingOverlayError("financing contract must not claim historical PIT proof")
    classes = contract.get("class_contracts")
    if not isinstance(classes, dict) or set(classes) != {"fx", "xau", "btc"}:
        raise FinancingOverlayError("financing class contract is incomplete")
    validated: dict[str, dict[str, object]] = {}
    for name in ("fx", "xau", "btc"):
        row = classes[name]
        if not isinstance(row, dict):
            raise FinancingOverlayError(f"invalid {name} class contract")
        rate = float(row.get("base_annual_rate", -1.0))
        floor = float(row.get("floor_annual_rate", -1.0))
        current = float(row.get("current_class_max_calendar_annual_rate", -1.0))
        coefficients = row.get("weekday_coefficients_monday_first")
        if (
            not math.isfinite(rate)
            or rate <= 0.0
            or rate < floor
            or rate < current
            or not isinstance(coefficients, list)
            or len(coefficients) != 7
            or any(float(value) < 0.0 for value in coefficients)
        ):
            raise FinancingOverlayError(f"invalid {name} rate/schedule contract")
        validated[name] = {
            "rate": rate,
            "coefficients": [float(value) for value in coefficients],
        }
    return validated


def _find_repo_root(contract_path: Path) -> Path:
    resolved = contract_path.resolve()
    for candidate in resolved.parents:
        if (
            (candidate / "02. AlphaFactory").is_dir()
            and (candidate / "03. EA Developer").is_dir()
        ):
            return candidate
    raise FinancingOverlayError(
        f"cannot locate repository root from financing contract: {resolved}"
    )


def verify_source_receipts(
    contract: dict[str, object], contract_path: Path
) -> list[dict[str, str]]:
    rows = contract.get("source_receipts")
    if not isinstance(rows, list) or not rows:
        raise FinancingOverlayError("financing contract has no source receipts")
    repo_root = _find_repo_root(contract_path)
    bindings: list[dict[str, str]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise FinancingOverlayError(f"invalid source receipt row {index}")
        relative = row.get("path")
        expected = row.get("sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise FinancingOverlayError(f"invalid source receipt binding {index}")
        relative_path = Path(relative)
        if relative_path.is_absolute():
            raise FinancingOverlayError(f"source receipt path must be relative: {relative}")
        resolved = (repo_root / relative_path).resolve()
        try:
            resolved.relative_to(repo_root)
        except ValueError as exc:
            raise FinancingOverlayError(
                f"source receipt escapes repository root: {relative}"
            ) from exc
        if not resolved.is_file():
            raise FinancingOverlayError(f"source receipt not found: {relative}")
        actual = require_sha256(resolved, expected, f"source receipt {index}")
        bindings.append({"path": relative_path.as_posix(), "sha256": actual})
    return bindings


def result_authorization_flags() -> dict[str, bool]:
    return {
        "calculation_valid": True,
        "historical_pit_financing_proven": False,
        "economic_verdict_authorized": False,
        "performance_verdict_authorized": False,
    }


def calculate_overlay(
    events: Iterable[ExposureEvent],
    start: date,
    end: date,
    contract: dict[str, object],
) -> dict[str, object]:
    if end <= start:
        raise FinancingOverlayError("end must be after start")
    classes = _validate_contract(contract)
    events_by_day: dict[date, list[ExposureEvent]] = {}
    for event in events:
        if start <= event.day < end:
            events_by_day.setdefault(event.day, []).append(event)
    state: ExposureEvent | None = None
    weighted_notional_days = {"fx": 0.0, "xau": 0.0, "btc": 0.0}
    observed_days = 0
    carried_days = 0
    leading_zero_days = 0
    current = start
    while current < end:
        daily_events = events_by_day.get(current, [])
        if daily_events:
            state = daily_events[-1]
            observed_days += 1
        else:
            carried_days += 1
        if state is None:
            # Before the first tester tick there cannot be an EA-opened position.
            # Treat those leading calendar days as zero exposure, then carry the
            # first observed state normally.
            leading_zero_days += 1
            current += timedelta(days=1)
            continue
        weekday = current.weekday()
        weighted_notional_days["fx"] += state.fx_usd * classes["fx"]["coefficients"][weekday]
        weighted_notional_days["xau"] += state.xau_usd * classes["xau"]["coefficients"][weekday]
        weighted_notional_days["btc"] += state.btc_usd * classes["btc"]["coefficients"][weekday]
        current += timedelta(days=1)

    denominator = int(contract.get("day_count_denominator", 0))
    if denominator != 365:
        raise FinancingOverlayError("MTS004 overlay requires a 365-day denominator")
    base_cost_by_class = {
        name: weighted_notional_days[name] * float(classes[name]["rate"]) / denominator
        for name in ("fx", "xau", "btc")
    }
    base_cost = sum(base_cost_by_class.values())
    multipliers = contract.get("stress_multipliers")
    if multipliers != [1.0, 1.5, 2.0]:
        raise FinancingOverlayError("unexpected stress multiplier contract")
    return {
        "calendar_days": (end - start).days,
        "observed_event_days": observed_days,
        "carried_days": carried_days,
        "leading_zero_days": leading_zero_days,
        "unique_events": sum(len(rows) for rows in events_by_day.values()),
        "weighted_notional_days": weighted_notional_days,
        "base_cost_by_class_usd": base_cost_by_class,
        "base_cost_usd": base_cost,
        "stress_cost_usd": {str(value): base_cost * float(value) for value in multipliers},
    }


def load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise FinancingOverlayError(f"expected JSON object: {path}")
    return payload


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply frozen MTS004 financing overlay")
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--journal-sha256", required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--summary-sha256", required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--contract-sha256", required=True)
    parser.add_argument("--from-date", required=True)
    parser.add_argument("--to-date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    journal_sha = require_sha256(args.journal, args.journal_sha256, "journal")
    summary_sha = require_sha256(args.summary, args.summary_sha256, "summary")
    contract_sha = require_sha256(args.contract, args.contract_sha256, "contract")
    journal_text = args.journal.read_text(encoding="utf-8-sig", errors="strict")
    events = parse_exposure_events(journal_text)
    telemetry = parse_unique_economic_telemetry(journal_text)
    summary = load_json(args.summary)
    native_net = float(summary.get("net_profit", math.nan))
    if not math.isfinite(native_net) or not math.isclose(
        native_net, float(telemetry["native_net"]), abs_tol=0.02
    ):
        raise FinancingOverlayError("report summary net_profit disagrees with EA native_net")
    contract = load_json(args.contract)
    receipt_bindings = verify_source_receipts(contract, args.contract)
    overlay = calculate_overlay(
        events, parse_date(args.from_date), parse_date(args.to_date), contract
    )
    pre_financing_net = native_net - float(telemetry["deal_swap"])
    adjusted = {
        multiplier: pre_financing_net - float(cost)
        for multiplier, cost in overlay["stress_cost_usd"].items()
    }
    payload: dict[str, object] = {
        "schema_version": "mts004_financing_overlay_result.v1",
        "hypothesis_id": "HYP-MULTI-TSMOM-D1-004",
        "status": "PASS_CALCULATION",
        "inputs": {
            "journal_path": args.journal.resolve().as_posix(),
            "journal_sha256": journal_sha,
            "summary_path": args.summary.resolve().as_posix(),
            "summary_sha256": summary_sha,
            "contract_path": args.contract.resolve().as_posix(),
            "contract_sha256": contract_sha,
            "source_receipt_bindings": receipt_bindings,
            "from": parse_date(args.from_date).isoformat(),
            "to_exclusive": parse_date(args.to_date).isoformat(),
        },
        "native": telemetry,
        "pre_financing_net_usd": pre_financing_net,
        "overlay": overlay,
        "adjusted_net_usd": adjusted,
        **result_authorization_flags(),
    }
    write_json_atomic(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
