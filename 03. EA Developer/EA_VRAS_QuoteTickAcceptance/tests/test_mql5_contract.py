"""Static contract tests for EA_VRAS_QuoteTickAcceptance.mq5."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "EA_VRAS_QuoteTickAcceptance.mq5"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"
README = ROOT / "README.md"


def text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_source_and_package_exist():
    assert SOURCE.is_file()
    assert CONTRACT.is_file()
    assert README.is_file()


def test_package_capability_contract():
    raw = CONTRACT.read_text(encoding="utf-8")
    assert '"schema_version": "alphafactory_ea_contract.v1"' in raw
    assert '"telemetry_profile": "none"' in raw
    assert '"market_phase_adapter": "none"' in raw
    assert '"comparison_adapter": "generic-control-improvement-v1"' in raw


def test_readme_is_collection_only_vietnamese():
    readme = README.read_text(encoding="utf-8")
    assert "collection-only" in readme.lower() or "thu thập" in readme.lower()
    assert "không phải EA sinh lời" in readme or "không" in readme
    assert "HYP-VRAS-EURUSD-M5-014" in readme


def test_exact_hypothesis_identity_and_defaults():
    s = text()
    assert 'InpHypothesisId="HYP-VRAS-EURUSD-M5-014"' in s
    assert "InpCollectionOnly=true" in s
    assert "InpH1EmaPeriod=200" in s
    assert "InpRollingVwapBars=48" in s
    assert "InpPrearmRingSize=60" in s
    assert "InpPrearmMinQuotes=30" in s
    assert "InpAcceptAgeMinMs=30000" in s
    assert "InpAcceptAgeMaxMs=120000" in s
    assert "InpMinQuoteUpdates=20" in s
    assert "InpMinPriceChanges=12" in s
    assert "InpMinImbalance=0.60" in s
    assert "InpMaxSpreadRatio=1.50" in s
    assert "InpMaxGapMs=15000" in s
    assert '_Symbol!="EURUSD"' in s or '_Symbol!="EURUSD"' in s
    assert "_Period!=PERIOD_M5" in s
    assert "IdentityOk" in s


def test_closed_bar_shifts_only_for_arm():
    s = text()
    assert "CopyBuffer(g_h1_ema_handle,0,1,1" in s
    assert "iClose(_Symbol,PERIOD_H1,1)" in s
    assert "CopyRates(_Symbol,PERIOD_M5,1,InpRollingVwapBars" in s
    assert "CopyRates(_Symbol,PERIOD_M5,1,3" in s
    assert "history[index].tick_volume" in s
    # Live bar must not drive arm signal
    assert "CopyBuffer(g_h1_ema_handle,0,0," not in s
    assert "CopyRates(_Symbol,PERIOD_M5,0," not in s


def test_mirrored_long_short_arm_logic():
    s = text()
    assert "bars[0].low<=vwap" in s
    assert "bars[0].close>vwap" in s
    assert "bars[0].close>bars[1].high" in s
    assert "bars[0].high>=vwap" in s
    assert "bars[0].close<vwap" in s
    assert "bars[0].close<bars[1].low" in s
    assert "DIR_LONG" in s and "DIR_SHORT" in s


def test_prearm_ring_and_acceptance_gates_present():
    s = text()
    assert "PrearmPush" in s and "PrearmMedian" in s
    assert "InpPrearmMinQuotes" in s
    assert "REJECT_VWAP_RECROSS" in s
    assert "REJECT_SPREAD_SPIKE" in s
    assert "REJECT_STALE_GAP" in s
    assert "REJECT_INVALID_QUOTE" in s
    assert "EXPIRE_NO_ACCEPTANCE" in s
    assert "DEINIT_ACTIVE_ARM" in s
    assert "ACCEPTED_OBSERVATION" in s
    assert "ARMED" in s
    assert "OBSERVE" in s
    assert "AcceptanceGates" in s
    assert "g_max_gap_ms" in s
    assert "g_max_spread_since_arm" in s
    assert "Imbalance" in s


def test_immutable_terminal_and_one_active_arm():
    s = text()
    assert "ST_ACTIVE" in s and "ST_PENDING" in s and "ST_TERMINAL" in s
    assert "TerminateArm" in s
    assert "At most one active/pending arm" in s or "g_state==ST_ACTIVE || g_state==ST_PENDING" in s


def test_csv_schema_and_data_source_contract():
    s = text()
    assert 'SCHEMA_VERSION="vras_quote_acceptance.v1"' in s
    assert '%04d-%02d-%02dT%02d:%02d:%02d.%03dZ' in s
    required = [
        "schema_version",
        "hypothesis_id",
        "run_id",
        "event_time_msc",
        "event_time_utc",
        "symbol",
        "event",
        "direction",
        "arm_bar_time",
        "arm_time_msc",
        "age_ms",
        "bid",
        "ask",
        "mid",
        "spread_points",
        "prearm_median_spread_points",
        "quote_updates",
        "price_changes",
        "directional_moves",
        "opposite_moves",
        "imbalance",
        "directional_net_points",
        "max_gap_ms",
        "max_spread_ratio",
        "frozen_vwap",
        "data_source",
        "promotion_eligible",
    ]
    for col in required:
        assert col in s, col
    assert 'LIVE_QUOTES' in s
    assert 'SYNTHETIC_TESTER_TICKS' in s
    assert 'MQL_TESTER' in s
    assert "NormalizeTickUtcMsc(tick.time_msc)" in s
    assert "TimeCurrent()-(long)TimeGMT()" in s
    assert '"false"' in s or 'promotion_eligible' in s


def test_no_trade_or_file_common_apis():
    s = text()
    forbidden = [
        r"\bMqlTradeRequest\b",
        r"\bOrderSend\b",
        r"\bOrderCheck\b",
        r"\bCTrade\b",
        r"\bPositionOpen\b",
        r"\bPositionClose\b",
        r"\bPositionModify\b",
        r"\bBuy\s*\(",
        r"\bSell\s*\(",
        r"\bOnTradeTransaction\b",
        r"\bFILE_COMMON\b",
        r"\bOrderCalcProfit\b",
        r"\bOrderCalcMargin\b",
    ]
    for pat in forbidden:
        assert re.search(pat, s) is None, pat
    # No SL/TP trade geometry wiring
    assert "StopLoss" not in s
    assert "TakeProfit" not in s
    assert "POSITION_SL" not in s
    assert "POSITION_TP" not in s


def test_causal_ontick_documented_not_closed_bar_violation():
    s = text()
    assert "void OnTick()" in s
    assert "causal" in s.lower() or "Causal OnTick" in s
    assert "closed-bar" in s.lower() or "Closed-bar" in s or "closed_bar" in s
