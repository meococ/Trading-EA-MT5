from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "research" / "mts004_financing_overlay.py"
CONTRACT = (
    ROOT.parent
    / "03. EA Developer"
    / "EA_MultiAssetTSMOMD1V4"
    / "research"
    / "HYP-MULTI-TSMOM-D1-004_FINANCING_CONTRACT.json"
)

spec = importlib.util.spec_from_file_location("mts004_financing_overlay", TOOL)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def event_line(epoch: int, day: str, reason: str, fx: int, xau: int, btc: int) -> str:
    return (
        f"MTS004_FINANCE_EXPOSURE epoch={epoch} day={day} reason={reason} "
        f"fx_usd={fx:.2f} xau_usd={xau:.2f} btc_usd={btc:.2f}"
    )


def test_parser_deduplicates_controller_and_agent_blocks_but_preserves_rebalance() -> None:
    daily = event_line(100, "20260105", "daily_open", 100, 0, 10)
    rebalance = event_line(100, "20260105", "rebalance", 200, 0, 20)
    events = module.parse_exposure_events("\n".join([daily, rebalance, daily, rebalance]))
    assert [row.reason for row in events] == ["daily_open", "rebalance"]
    assert events[-1].fx_usd == 200


def test_overlay_uses_last_daily_state_and_carries_weekend() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    text = "\n".join(
        [
            event_line(100, "20260102", "daily_open", 365, 365, 365),  # Friday
            event_line(200, "20260105", "daily_open", 365, 365, 365),
            event_line(200, "20260105", "rebalance", 730, 730, 730),
        ]
    )
    events = module.parse_exposure_events(text)
    result = module.calculate_overlay(
        events, date(2026, 1, 2), date(2026, 1, 6), contract
    )
    # Friday: FX/XAU coefficient 3; weekend: only BTC charges; Monday uses
    # the post-rebalance state and coefficient 1.
    assert result["weighted_notional_days"] == {
        "fx": 1825.0,
        "xau": 1825.0,
        "btc": 1825.0,
    }
    assert result["observed_event_days"] == 2
    assert result["carried_days"] == 2
    assert result["leading_zero_days"] == 0
    assert result["base_cost_by_class_usd"] == pytest.approx(
        {"fx": 0.3, "xau": 0.45, "btc": 3.5}
    )
    assert result["stress_cost_usd"] == pytest.approx(
        {"1.0": 4.25, "1.5": 6.375, "2.0": 8.5}
    )


def test_economic_telemetry_must_be_unique_and_add_up() -> None:
    line = (
        "MTS004_ECON_TELEMETRY ticks=10 deal_profit=100.00 "
        "deal_swap=-5.00 deal_commission=-2.00 native_net=93.00"
    )
    assert module.parse_unique_economic_telemetry(line + "\n" + line)["native_net"] == 93
    with pytest.raises(module.FinancingOverlayError):
        module.parse_unique_economic_telemetry(line.replace("native_net=93.00", "native_net=92.00"))


def test_contract_floors_cover_current_class_maxima() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = contract["class_contracts"]
    assert rows["fx"]["base_annual_rate"] == 0.06
    assert rows["xau"]["base_annual_rate"] == 0.09
    assert rows["btc"]["base_annual_rate"] == 0.70
    assert all(
        row["base_annual_rate"] >= row["current_class_max_calendar_annual_rate"]
        for row in rows.values()
    )


def test_overlay_treats_pre_tick_run_days_as_zero_exposure() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    events = module.parse_exposure_events(
        event_line(200, "20260105", "daily_open", 365, 0, 0)
    )
    result = module.calculate_overlay(
        events, date(2026, 1, 3), date(2026, 1, 6), contract
    )
    assert result["leading_zero_days"] == 2
    assert result["weighted_notional_days"]["fx"] == 365


def test_contract_source_receipts_are_hash_bound_and_contained() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    bindings = module.verify_source_receipts(contract, CONTRACT)
    assert len(bindings) == 2
    assert all(len(row["sha256"]) == 64 for row in bindings)


def test_calculation_result_never_self_authorizes_economic_verdict() -> None:
    flags = module.result_authorization_flags()
    assert flags == {
        "calculation_valid": True,
        "historical_pit_financing_proven": False,
        "economic_verdict_authorized": False,
        "performance_verdict_authorized": False,
    }


def test_cli_writes_hash_bound_non_authorizing_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = tmp_path / "journal.log"
    summary = tmp_path / "summary.json"
    output = tmp_path / "financing.json"
    journal.write_text(
        "\n".join(
            [
                event_line(100, "20260105", "daily_open", 365, 0, 0),
                "MTS004_ECON_TELEMETRY ticks=10 deal_profit=100.00 "
                "deal_swap=-5.00 deal_commission=-2.00 native_net=93.00",
            ]
        ),
        encoding="utf-8",
    )
    summary.write_text(json.dumps({"net_profit": 93.0}), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(TOOL),
            "--journal",
            str(journal),
            "--journal-sha256",
            module.sha256_file(journal),
            "--summary",
            str(summary),
            "--summary-sha256",
            module.sha256_file(summary),
            "--contract",
            str(CONTRACT),
            "--contract-sha256",
            module.sha256_file(CONTRACT),
            "--from-date",
            "2026-01-05",
            "--to-date",
            "2026-01-06",
            "--output",
            str(output),
        ],
    )
    assert module.main() == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["pre_financing_net_usd"] == 98.0
    assert result["performance_verdict_authorized"] is False
    assert len(result["inputs"]["source_receipt_bindings"]) == 2
