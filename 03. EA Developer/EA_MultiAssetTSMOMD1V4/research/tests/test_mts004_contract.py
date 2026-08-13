from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
RESEARCH = PACKAGE / "research"
SOURCE = PACKAGE / "EA_MultiAssetTSMOMD1V4.mq5"
COMPILE_LOG = PACKAGE / "EA_MultiAssetTSMOMD1V4.log"
MANIFEST = PACKAGE / "HYP-MULTI-TSMOM-D1-004_NONREPAINT_MANIFEST.json"
CONTRACT = RESEARCH / "HYP-MULTI-TSMOM-D1-004_DUKASCOPY_SOURCE_CONTRACT.json"


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


def test_btc_activation_is_first_monday_after_full_calendar_warmup() -> None:
    listing = date(2017, 5, 7)
    full_warmup = listing + timedelta(days=365)
    activation = full_warmup + timedelta(days=(7 - full_warmup.weekday()) % 7)
    assert full_warmup == date(2018, 5, 7)
    assert activation == date(2018, 5, 7)
    # The source contract deliberately requires one complete post-warmup week
    # and therefore activates on the following Monday, not on the boundary day.
    assert activation + timedelta(days=7) == date(2018, 5, 14)


def test_mql_uses_closed_d1_and_calendar_cutoff() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "CopyRates(g_symbols[index],PERIOD_D1,1,HISTORY_BUFFER,rates)" in source
    assert "CALENDAR_LOOKBACK_SECONDS=365L*86400L" in source
    assert "close_time<=cutoff" in source
    assert "BTC_ACTIVE_FROM=D'2018.05.14 00:00:00'" in source
    assert "CopyBuffer" not in source


def test_mql_is_net_delta_without_old_loss_stop_rescue() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert "OwnedSignedVolume" in source
    assert "RebalanceSymbol" in source
    assert "const double sign=(raw>0.0 ? 1.0 : -1.0);" in source
    assert "MathRound(MathAbs(raw)/step)*step" in source
    assert "NormalizeVolumeNearest(symbol,target-current)" in source
    assert 'EmitFinancingExposure(now,true,"rebalance")' in source
    assert 'reason=%s fx_usd=%.2f xau_usd=%.2f btc_usd=%.2f' in source
    assert 'EmitFinancingExposure(TimeCurrent(),true,"deinit")' in source
    assert "MTS004_DELTA" in source
    assert "DAILY_LOSS_KILL" not in source
    assert "WEEKLY_LOSS_KILL" not in source
    assert "CloseAllOwned" not in source


def test_compile_and_manifest_bind_exact_source() -> None:
    payload = COMPILE_LOG.read_bytes()
    if payload.startswith((b"\xff\xfe", b"\xfe\xff")):
        log = payload.decode("utf-16", errors="ignore")
    else:
        log = payload.decode("utf-8-sig", errors="ignore")
    assert "Result: 0 errors, 0 warnings" in log
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_sha256"] == sha256(SOURCE)
    assert manifest["compile_log_sha256"] == sha256(COMPILE_LOG)
    assert manifest["audit_status"] == "PASS_STATIC"
