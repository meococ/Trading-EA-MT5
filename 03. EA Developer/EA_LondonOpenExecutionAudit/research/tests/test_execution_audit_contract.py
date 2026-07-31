from __future__ import annotations

import hashlib
import importlib.util
import csv
import json
import sys
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
SOURCE = PACKAGE / "EA_LondonOpenExecutionAudit.mq5"
BASE_PREREG = PACKAGE / "research" / "HYP-LOMX-EXEC-AUDIT-M1-003_PREREG.md"
PREREG = PACKAGE / "research" / "HYP-LOMX-EXEC-AUDIT-M1-003_PREREG_V2.md"
VALIDATOR = PACKAGE / "research" / "validate_execution_audit.py"


def text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_source_binds_exact_frozen_prereg() -> None:
    expected = hashlib.sha256(PREREG.read_bytes()).hexdigest().upper()
    base = hashlib.sha256(BASE_PREREG.read_bytes()).hexdigest().upper()
    assert expected == "FA5745BAFFD8FBBE8238D82B143E5F6DFC4E9CD7DD1D9A5557F3B3E01310CABA"
    assert base == "039178106824BD8F2610B55F6AA54DED0CCAB3CE688A77B12142A9C897AC209B"
    assert f'const string PREREG_SHA256="{expected}";' in text()
    assert f'const string BASE_PREREG_SHA256="{base}";' in text()


def test_all_four_scenarios_and_runtime_identity_are_fail_closed() -> None:
    source = text()
    for scenario in (
        "EURUSD_MIDDAY_CONT",
        "GBPUSD_MIDDAY_REV",
        "GBPUSD_LATE_FIX_REV",
        "GBPUSD_FULL_SESSION_REV",
    ):
        assert f'InpScenario=="{scenario}"' in source
    assert "!InpAuditAutoMode" in source
    assert 'InpHypothesisId!="HYP-LOMX-EXEC-AUDIT-M1-003"' in source
    assert "InpMagic!=5601303" in source
    assert "_Period!=PERIOD_M1" in source


def test_signal_reads_only_exact_closed_m1_bars() -> None:
    source = text()
    assert "shift=iBarShift(_Symbol,PERIOD_M1,server_time,true);" in source
    assert "if(shift<1)" in source
    assert "CopyRates(_Symbol,PERIOD_M1,shift,1,bars)" in source
    assert "bars[0].time!=server_time" in source
    assert "iOpen(" not in source
    assert "CopyBuffer(" not in source


def test_entry_and_exit_use_executable_quote_sides() -> None:
    source = text()
    assert "request.price=g_direction>0 ? tick.ask : tick.bid;" in source
    assert "request.price=position_type==POSITION_TYPE_BUY ? tick.bid : tick.ask;" in source
    assert 'WriteDecision(now,"ENTRY_REQUEST","REQUESTED"' in source
    assert 'WriteDecision(now,"EXIT_REQUEST","REQUESTED"' in source


def test_telemetry_is_local_sandbox_only_and_audit_authority_is_false() -> None:
    source = text()
    assert "FILE_COMMON" not in source
    assert "LifecycleTrades" in source
    assert "DecisionTelemetry" in source
    assert "RunMeta" in source
    assert '\\"performance_metrics_authorized\\":false' in source
    assert '\\"promotion_eligible\\":false' in source
    assert "HistoryDealGetInteger(deal,DEAL_TYPE)" in source
    assert "RemainingPositionVolumeFromHistory" in source
    assert "PositionIdentifierExists" not in source


def test_frozen_times_and_no_price_filters_or_stops() -> None:
    source = text()
    assert "g_entry_minute=8*60+31; g_exit_minute=12*60;" in source
    assert "g_entry_minute=15*60+30; g_exit_minute=16*60;" in source
    assert "g_entry_minute=8*60+31; g_exit_minute=16*60+30;" in source
    assert "request.sl" not in source
    assert "request.tp" not in source
    assert "MaxSpread" not in source


def load_validator():
    spec = importlib.util.spec_from_file_location("audit_validator", VALIDATOR)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_validator_freezes_same_four_scenarios() -> None:
    module = load_validator()
    assert module.SCENARIOS == {
        "EURUSD_MIDDAY_CONT": {"symbol": "EURUSD", "polarity": 1, "entry": 511, "exit": 720},
        "GBPUSD_MIDDAY_REV": {"symbol": "GBPUSD", "polarity": -1, "entry": 511, "exit": 720},
        "GBPUSD_LATE_FIX_REV": {"symbol": "GBPUSD", "polarity": -1, "entry": 930, "exit": 960},
        "GBPUSD_FULL_SESSION_REV": {"symbol": "GBPUSD", "polarity": -1, "entry": 511, "exit": 990},
    }
    assert module.MIN_COMPLETED_LIFECYCLES == 1000


DECISION_FIELDS = [
    "server_time", "utc_time", "london_time", "london_date", "event", "status",
    "scenario", "set_name", "hypothesis_id", "formation_sign", "polarity", "direction",
    "source_0800_server", "source_0830_server", "source_0800_open_bid",
    "source_0830_open_bid", "source_0800_shift", "source_0830_shift",
    "signal_observed_server", "entry_eligible_server", "bid", "ask", "spread_points",
    "request_price", "actual_deal_price", "volume", "order_id", "deal_id",
    "position_id", "retcode", "reason",
]


def make_run(tmp_path: Path, *, signal_minute: int = 511, entry_minute: int = 511,
             include_trades: bool = True) -> Path:
    run = tmp_path / "run"
    logs = run / "logs"
    logs.mkdir(parents=True)

    def stamp(minute: int) -> str:
        return f"2020.01.02 {minute//60:02d}:{minute%60:02d}:00"

    common = {
        "server_time": "2020.01.02 10:31:00", "utc_time": "2020.01.02 08:31:00",
        "london_time": stamp(511), "london_date": "2020.01.02", "event": "",
        "status": "", "scenario": "EURUSD_MIDDAY_CONT", "set_name": "MIDDAY",
        "hypothesis_id": "HYP-LOMX-EXEC-AUDIT-M1-003", "formation_sign": "1",
        "polarity": "1", "direction": "1", "source_0800_server": "2020.01.02 10:00:00",
        "source_0830_server": "2020.01.02 10:30:00", "source_0800_open_bid": "1.10000",
        "source_0830_open_bid": "1.10100", "source_0800_shift": "31",
        "source_0830_shift": "1", "signal_observed_server": "2020.01.02 10:31:00",
        "entry_eligible_server": "2020.01.02 10:31:00", "bid": "1.10100",
        "ask": "1.10120", "spread_points": "20", "request_price": "0",
        "actual_deal_price": "0", "volume": "0.01", "order_id": "0", "deal_id": "0",
        "position_id": "0", "retcode": "0", "reason": "fixture",
    }
    rows: list[dict[str, str]] = []
    if include_trades:
        signal = dict(common, event="SIGNAL_READY", status="PASS", london_time=stamp(signal_minute))
        entry_request = dict(common, event="ENTRY_REQUEST", status="REQUESTED",
                             london_time=stamp(entry_minute), request_price="1.10120")
        entry_deal = dict(common, event="ENTRY_DEAL", status="EXECUTED",
                          london_time=stamp(entry_minute), actual_deal_price="1.10120",
                          order_id="10", deal_id="11", position_id="12")
        exit_request = dict(common, event="EXIT_REQUEST", status="REQUESTED",
                            server_time="2020.01.02 14:00:00", utc_time="2020.01.02 12:00:00",
                            london_time=stamp(720), request_price="1.10200", bid="1.10200",
                            ask="1.10220", position_id="12", reason="FROZEN_TIME_EXIT")
        exit_deal = dict(exit_request, event="EXIT_DEAL", status="EXECUTED",
                         request_price="0", actual_deal_price="1.10200",
                         order_id="13", deal_id="14")
        rows = [signal, entry_request, entry_deal, exit_request, exit_deal]
    with (logs / "EURUSD_DecisionTelemetry_fixture.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DECISION_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    lifecycle_fields = [
        "event_time", "action", "order_type", "volume", "price", "symbol", "position_id",
        "risk_pts", "initial_risk_account", "deal", "deal_profit", "deal_commission",
        "deal_swap", "deal_fee", "deal_net", "is_final_close",
    ]
    lifecycle_rows = []
    if include_trades:
        lifecycle_rows = [
            {"event_time": "2020.01.02 10:31:00", "action": "OPEN", "order_type": "BUY",
             "volume": "0.01", "price": "1.10120", "symbol": "EURUSD", "position_id": "12",
             "risk_pts": "0", "initial_risk_account": "0", "deal": "11", "deal_profit": "0",
             "deal_commission": "0", "deal_swap": "0", "deal_fee": "0", "deal_net": "0",
             "is_final_close": "0"},
            {"event_time": "2020.01.02 14:00:00", "action": "CLOSE", "order_type": "BUY",
             "volume": "0.01", "price": "1.10200", "symbol": "EURUSD", "position_id": "12",
             "risk_pts": "0", "initial_risk_account": "0", "deal": "14", "deal_profit": "1",
             "deal_commission": "0", "deal_swap": "0", "deal_fee": "0", "deal_net": "1",
             "is_final_close": "1"},
        ]
    with (logs / "EURUSD_LifecycleTrades_fixture.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=lifecycle_fields)
        writer.writeheader()
        writer.writerows(lifecycle_rows)

    count = 1 if include_trades else 0
    meta = {
        "schema_version": "alphafactory_run_meta.v1", "ea_name": "EA_LondonOpenExecutionAudit",
        "symbol": "EURUSD", "variant_tag": "EURUSD_MIDDAY_CONT", "audit_only": True,
        "performance_metrics_authorized": False, "promotion_eligible": False,
        "diagnostic": {"entries_opened": count, "entries_closed": count, "overnight_violations": 0},
    }
    (logs / "EURUSD_RunMeta_fixture.json").write_text(json.dumps(meta), encoding="utf-8")
    (run / "report.html").write_text("fixture", encoding="utf-8")
    return run


def test_validator_accepts_only_reconciled_fixture(tmp_path: Path, monkeypatch) -> None:
    module = load_validator()
    monkeypatch.setattr(module, "MIN_COMPLETED_LIFECYCLES", 1)
    monkeypatch.setattr(module, "report_deal_counts", lambda _path, _symbol: (1, 1))
    result = module.validate_scenario("EURUSD_MIDDAY_CONT", make_run(tmp_path))
    assert result.passed, result.errors


def test_validator_rejects_wrong_signal_and_late_midday_entry(tmp_path: Path, monkeypatch) -> None:
    module = load_validator()
    monkeypatch.setattr(module, "MIN_COMPLETED_LIFECYCLES", 1)
    monkeypatch.setattr(module, "report_deal_counts", lambda _path, _symbol: (1, 1))
    result = module.validate_scenario(
        "EURUSD_MIDDAY_CONT", make_run(tmp_path, signal_minute=512, entry_minute=600)
    )
    assert not result.passed
    assert any("signal outside exact 08:31" in error for error in result.errors)
    assert any("entry outside exact 08:31" in error for error in result.errors)


def test_validator_rejects_zero_population(tmp_path: Path, monkeypatch) -> None:
    module = load_validator()
    monkeypatch.setattr(module, "MIN_COMPLETED_LIFECYCLES", 1)
    monkeypatch.setattr(module, "report_deal_counts", lambda _path, _symbol: (0, 0))
    result = module.validate_scenario("EURUSD_MIDDAY_CONT", make_run(tmp_path, include_trades=False))
    assert not result.passed
    assert any("below frozen engineering floor" in error for error in result.errors)


def test_validator_rejects_report_sidecar_mismatch(tmp_path: Path, monkeypatch) -> None:
    module = load_validator()
    monkeypatch.setattr(module, "MIN_COMPLETED_LIFECYCLES", 1)
    monkeypatch.setattr(module, "report_deal_counts", lambda _path, _symbol: (0, 0))
    result = module.validate_scenario("EURUSD_MIDDAY_CONT", make_run(tmp_path))
    assert not result.passed
    assert any("report entry deals 0" in error for error in result.errors)
    assert any("report exit deals 0" in error for error in result.errors)
