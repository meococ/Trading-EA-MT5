from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
RESEARCH = PACKAGE / "research"
SOURCE = PACKAGE / "EA_MultiAssetTSMOMD1V5.mq5"
EX5 = PACKAGE / "EA_MultiAssetTSMOMD1V5.ex5"
COMPILE_LOG = PACKAGE / "EA_MultiAssetTSMOMD1V5.log"
MANIFEST = PACKAGE / "HYP-MULTI-TSMOM-D1-005_NONREPAINT_MANIFEST.json"
CONTRACT = RESEARCH / "HYP-MULTI-TSMOM-D1-005_JETTA_H1_SOURCE_CONTRACT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_source_contract_is_fixed_eight_to_nine_schedule() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    rows = contract["symbols"]
    assert [row["source_symbol"] for row in rows] == [
        "EURUSD",
        "GBPUSD",
        "AUDUSD",
        "NZDUSD",
        "USDJPY",
        "USDCAD",
        "USDCHF",
        "XAUUSD",
        "BTCUSD",
    ]
    assert all(row["history_from"] == "2017-01-01" for row in rows[:8])
    assert rows[8]["history_from"] == "2017-05-07"
    assert rows[8]["strategy_active_from"] == "2018-05-14T00:00:00Z"


def test_h1_source_contract_is_fail_closed_and_non_economic() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert contract["economics_authorized"] is False
    assert contract["performance_metrics_authorized"] is False
    assert contract["download"]["workers"] == 1
    assert contract["download"]["minimum_request_interval_seconds"] == 0.75
    rates = contract["rate_construction"]
    assert rates["bar_timeframe"] == "H1"
    assert rates["price_ohlc"] == "BID"
    assert rates["spread_lookahead"] is False
    assert "fail the whole weekly snapshot" in rates[
        "missing_active_symbol_at_decision_policy"
    ]


def test_btc_activation_is_after_full_calendar_warmup() -> None:
    listing = date(2017, 5, 7)
    full_warmup = listing + timedelta(days=365)
    assert full_warmup == date(2018, 5, 7)
    assert full_warmup + timedelta(days=7) == date(2018, 5, 14)


def test_mql_uses_closed_d1_and_calendar_cutoff() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "InpLongOnlyComparator=false" in source
    assert "InpMagic!=expected_magic" in source
    assert "260812008 : 260812007" in source
    assert "InpMagic!=260812006" not in source
    assert "CopyRates(g_symbols[index],PERIOD_D1,1,HISTORY_BUFFER,rates)" in source
    assert "CALENDAR_LOOKBACK_SECONDS=365L*86400L" in source
    assert "close_time<=cutoff" in source
    assert "BTC_ACTIVE_FROM=D'2018.05.14 00:00:00'" in source
    assert "CopyBuffer" not in source


def test_long_only_comparator_changes_only_direction_after_source_load() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    load_at = source.index("LoadClosedAssetState(i,decision_time,g_signal[i],g_annual_vol[i])")
    override_at = source.index("if(InpLongOnlyComparator)", load_at)
    weights_at = source.index("BuildFrozenWeights(decision_time)", override_at)
    assert load_at < override_at < weights_at
    assert 'g_signal[i]=1.0;' in source[override_at:weights_at]


def test_mql_is_net_delta_and_keeps_whole_snapshot_fail_closed() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "OwnedSignedVolume" in source
    assert "RebalanceSymbol" in source
    assert "const double sign=(raw>0.0 ? 1.0 : -1.0);" in source
    assert "NormalizeVolumeNearest(symbol,target-current)" in source
    assert 'EmitFinancingExposure(now,true,"rebalance")' in source
    assert "MTS005_DELTA" in source
    assert "MTS005_DEAL_COST" in source
    assert "OneSpreadCostUsd" in source
    assert "DAILY_LOSS_KILL" not in source
    assert "WEEKLY_LOSS_KILL" not in source
    assert "CloseAllOwned" not in source


def test_compile_and_manifest_bind_exact_source() -> None:
    payload = COMPILE_LOG.read_bytes()
    log = (
        payload.decode("utf-16", errors="ignore")
        if payload.startswith((b"\xff\xfe", b"\xfe\xff"))
        else payload.decode("utf-8-sig", errors="ignore")
    )
    assert "Result: 0 errors, 0 warnings" in log
    assert EX5.stat().st_size > 0
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_sha256"] == sha256(SOURCE)
    assert manifest["ex5_sha256"] == sha256(EX5)
    assert manifest["compile_log_sha256"] == sha256(COMPILE_LOG)
    assert manifest["source_intrabar_path_used"] is False
    assert manifest["audit_status"] == "PASS_STATIC"
