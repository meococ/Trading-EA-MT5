from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
SOURCE = ROOT / "EA_PTR_T2_DataEpochD0V2.mq5"
CONTRACT = ROOT / "ALPHAFACTORY_EA_CONTRACT.json"
README = ROOT / "README.md"
ALPHA = WORKSPACE / "02. AlphaFactory" / "alpha.ps1"
ENGINE = WORKSPACE / "02. AlphaFactory" / "tools" / "research_loop_engine.ps1"
EPOCH_VALIDATOR = WORKSPACE / "04. Memory" / "research" / "validate_data_epoch.py"
APPENDER = ROOT / "research" / "append_t2_data_epoch_evidence.py"

EXPECTED_EPOCH_SHA = "F47901F60E4314321B4B201ACED1D8D7366AC5D64589C487E893F0153332F648"
EXPECTED_SERIES_FIELDS = [
    "symbol",
    "m5_synchronized",
    "m5_first_epoch",
    "m5_terminal_first_epoch",
    "m1_server_first_epoch",
    "m1_terminal_first_epoch",
    "m5_bars",
    "terminal_maxbars",
    "copytime_from_epoch",
    "copytime_count",
    "copytime_result",
    "copytime_first_epoch",
    "copytime_last_error",
]


def read_source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_package_files_exist() -> None:
    assert SOURCE.is_file()
    assert CONTRACT.is_file()
    assert README.is_file()


def test_contract_declares_no_telemetry() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert '"schema_version": "alphafactory_ea_contract.v1"' in text
    assert '"telemetry_profile": "none"' in text
    assert '"variant_tag_input": null' in text


def test_source_contains_required_bindings_and_markers() -> None:
    text = read_source()
    required = [
        "class CDataEpochProbe",
        "input string          InpHypothesisId=\"\";",
        "input string          InpGenerationId=\"T2\";",
        f"input string          InpEpochManifestSha256=\"{EXPECTED_EPOCH_SHA}\";",
        "input ENUM_TIMEFRAMES InpExpectedTimeframe=PERIOD_M5;",
        "InpCollectionOnly",
        "DATA_EPOCH_D0_READY",
        "DATA_EPOCH_D0_SERIES_PROOF",
        "DATA_EPOCH_D0_FIRST_CLOSED_BAR",
        "DATA_EPOCH_D0_SUMMARY",
        "no_outcome_metrics=true",
    ]
    for needle in required:
        assert needle in text


def test_source_fails_closed_on_identity_and_timeframe() -> None:
    text = read_source()
    assert "StringLen(m_hypothesis_id)<=0" in text
    assert "m_generation_id!=\"T2\"" in text
    assert "m_epoch_manifest_sha256!=\"" in text
    assert "_Period!=m_expected_timeframe" in text
    assert "m_expected_timeframe!=PERIOD_M5" in text
    assert "m5_synchronized!=1" in text
    assert "copytime_result!=1" in text
    assert "copytime_error!=0" in text
    assert "return INIT_FAILED;" in text


def test_series_proof_marker_has_exact_machine_fields() -> None:
    text = read_source()
    marker = re.search(r'PrintFormat\("DATA_EPOCH_D0_SERIES_PROOF ([^"]+)"', text)
    assert marker
    fields = [part.split("=", 1)[0] for part in marker.group(1).split()]
    assert fields == EXPECTED_SERIES_FIELDS


def test_series_proof_schema_matches_all_pipeline_consumers() -> None:
    alpha = ALPHA.read_text(encoding="utf-8-sig")
    engine = ENGINE.read_text(encoding="utf-8-sig")
    validator = EPOCH_VALIDATOR.read_text(encoding="utf-8-sig")
    appender = APPENDER.read_text(encoding="utf-8-sig")
    consumers = [alpha, engine, validator, appender]
    for field in EXPECTED_SERIES_FIELDS:
        for consumer in consumers:
            assert field in consumer, (field, consumer[:80])
    for legacy in ("copy_count", "copy_first_epoch", "copy_error"):
        for consumer in consumers:
            assert re.search(rf"(?<!time){legacy}", consumer) is None, legacy


def test_series_proof_uses_required_mql5_core_calls() -> None:
    text = read_source()
    required = [
        "ReadSeriesInteger(PERIOD_M5,SERIES_SYNCHRONIZED",
        "ReadSeriesInteger(PERIOD_M5,SERIES_FIRSTDATE",
        "ReadSeriesInteger(PERIOD_M5,SERIES_TERMINAL_FIRSTDATE",
        "ReadSeriesInteger(PERIOD_M1,SERIES_SERVER_FIRSTDATE",
        "ReadSeriesInteger(PERIOD_M1,SERIES_TERMINAL_FIRSTDATE",
        "ReadSeriesInteger(PERIOD_M5,SERIES_BARS_COUNT",
        "SeriesInfoInteger(_Symbol,timeframe,property_id,value)",
        "TerminalInfoInteger(TERMINAL_MAXBARS)",
        "CopyTime(_Symbol,PERIOD_M5,copytime_from,1,copytime_values)",
        "GetLastError()",
    ]
    for needle in required:
        assert needle in text


def test_closed_bar_observation_uses_shift_one_only() -> None:
    text = read_source()
    assert "iTime(_Symbol,PERIOD_M5,1)" in text
    assert "closed_bar_shift=1" in text
    assert "m_first_closed_bar_time" in text
    assert "m_last_closed_bar_time" in text
    assert re.search(r"void\s+OnTick\s*\(\s*\)\s*\{[\s\S]*g_probe\.ObserveClosedBar\(\);[\s\S]*\}", text)


def test_source_forbids_trade_mutation_file_and_outcome_apis() -> None:
    text = read_source()
    forbidden_patterns = [
        r"\bCTrade\b",
        r"\bOrderSend\b",
        r"\bOrderCheck\b",
        r"\bOrderCalc",
        r"\bPosition",
        r"\bPositionsTotal\b",
        r"\bHistoryDeal",
        r"\bDeal",
        r"\bAccountInfo",
        r"\bFileOpen\b",
        r"\bFileWrite",
        r"\bFileRead",
        r"\bFILE_COMMON\b",
        r"\bStopLoss\b",
        r"\bTakeProfit\b",
        r"\bSL\b",
        r"\bTP\b",
        r"\bProfit\b",
        r"\bLoss\b",
        r"\bPnL\b",
        r"\bBalance\b",
        r"\bEquity\b",
    ]
    for pattern in forbidden_patterns:
        assert not re.search(pattern, text, flags=re.IGNORECASE), pattern
