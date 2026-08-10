from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
WORKSPACE = PACKAGE.parents[1]
SOURCE = PACKAGE / "EA_SupertrendBurstScalperTradeV3.mq5"
PARENT = WORKSPACE / "03. EA Developer" / "EA_SupertrendBurstScalperTradeV2" / "EA_SupertrendBurstScalperTradeV2.mq5"
CONTRACT = PACKAGE / "ALPHAFACTORY_EA_CONTRACT.json"
COMPILE_LOG = PACKAGE / "EA_SupertrendBurstScalperTradeV3.log"
EX5 = PACKAGE / "EA_SupertrendBurstScalperTradeV3.ex5"


def _functions(text: str) -> dict[str, str]:
    pattern = re.compile(
        r"(?m)^(?:bool|void|int|double|string|datetime|ulong|long)\s+([A-Za-z_]\w*)\s*\([^;]*?\)\s*\n\{"
    )
    found: dict[str, str] = {}
    for match in pattern.finditer(text):
        depth = 1
        index = match.end()
        while index < len(text) and depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        assert depth == 0, match.group(1)
        found[match.group(1)] = text[match.start() : index]
    return found


def test_trade_logic_is_exactly_parent_except_identity_and_telemetry_hooks() -> None:
    parent = _functions(PARENT.read_text(encoding="utf-8-sig"))
    current = _functions(SOURCE.read_text(encoding="utf-8-sig"))
    allowed_changed = {"OnInit", "OnDeinit", "OnTradeTransaction"}
    for name, body in parent.items():
        if name not in allowed_changed:
            assert current[name] == body, name


def test_frozen_economic_inputs_are_unchanged() -> None:
    text = SOURCE.read_text(encoding="utf-8-sig")
    expected = {
        "InpRiskPercent": "0.25",
        "InpStopAtrMult": "1.00",
        "InpTargetRR": "1.50",
        "InpMaxHoldBars": "8",
        "InpMaxDailyLossPct": "1.50",
        "InpMaxAccountDrawdownPct": "8.00",
        "InpFridayEntryCutoffUtcMinutes": "18*60",
        "InpFridayFlattenUtcMinutes": "20*60",
        "InpDeviationPoints": "20",
    }
    for name, value in expected.items():
        assert re.search(rf"input\s+\w+\s+{name}\s*=\s*{re.escape(value)}\s*;", text), name


def test_lifecycle_v3_contract_and_exact_sidecars_are_fail_closed() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    text = SOURCE.read_text(encoding="utf-8-sig")
    assert contract["telemetry_profile"] == "lifecycle-v3"
    assert 'input bool   InpEnableTelemetry     = true;' in text
    assert '!InpEnableTelemetry || InpMagic!=5604113' in text
    assert '"%s_LifecycleTrades_%s.csv"' in text
    assert '"%s_RunMeta_%s.json"' in text
    assert '\\"schema_version\\":\\"alphafactory_run_meta.v1\\"' in text
    assert 'if(!OpenTelemetry() || !RecoverTelemetryPositionContext())' in text
    assert 'STBS_FATAL|lifecycle_telemetry_init_failed' in text


def test_lifecycle_rows_bind_deals_and_actual_initial_risk() -> None:
    text = SOURCE.read_text(encoding="utf-8-sig")
    required_header = (
        '"event_time","action","order_type","volume","price",\n'
        '             "symbol","position_id","risk_pts","initial_risk_account","deal",\n'
        '             "deal_profit","deal_commission","deal_swap","deal_fee","deal_net",\n'
        '             "is_final_close"'
    )
    assert required_header in text
    assert "OrderCalcProfit(order_type,_Symbol,volume,price,stop,loss)" in text
    assert "risk_points=MathAbs(price-stop)/_Point;" in text
    assert "initial_risk_account=MathAbs(loss);" in text
    assert "HistorySelectByPosition(position_id)" in text
    assert "final_close=is_close && close_volume+1e-8>=open_volume" in text
    assert 'FailRuntime("lifecycle_deal_logging_failed")' in text


def test_compile_checkpoint_is_fresh_zero_error_zero_warning() -> None:
    assert EX5.is_file() and EX5.stat().st_size > 0
    log = COMPILE_LOG.read_text(encoding="utf-16", errors="strict")
    assert "Result: 0 errors, 0 warnings" in log
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest().upper() == "8E1DEA824FC0BC1699FC618AC71F2C8D7848556215699FFF432DA1BF9EEFF3B0"
