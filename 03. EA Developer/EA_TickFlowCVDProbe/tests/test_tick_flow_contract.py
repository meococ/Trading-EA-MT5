from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
SOURCE = PACKAGE / "EA_TickFlowCVDProbe.mq5"
PREREG = PACKAGE / "research" / "HYP-TFCVD-XAUUSD-M5-001_FROZEN_PREREG.md"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8-sig")


def test_identity_and_collection_only_contract() -> None:
    text = source_text()
    assert 'InpHypothesisId="HYP-TFCVD-XAUUSD-M5-001"' in text
    assert 'InpExpectedSymbol="XAUUSD"' in text
    assert "_Period==PERIOD_M5" in text
    assert "InpCollectionOnly" in text
    assert "M5Start(tick.time)" in text


def test_no_trade_or_shared_file_surface() -> None:
    text = source_text()
    forbidden = (
        "#include <Trade/", "CTrade", "OrderSend", "OrderSendAsync",
        "PositionOpen", "PositionClose", "TRADE_ACTION_", "FILE_COMMON",
        "OnTradeTransaction",
    )
    for token in forbidden:
        assert token not in text


def test_closed_bar_emission_precedes_new_bar_consumption() -> None:
    text = source_text()
    branch = text[text.index("else if(bar_start>g_bar_start)") : text.index("ProcessTick(tick);")]
    assert branch.index("FinalizeBar();") < branch.index("ResetBarCounters(bar_start);")
    assert "final_open_bar_omitted=true" in text


def test_tick_polarity_and_primary_unit_are_explicit() -> None:
    text = source_text()
    assert "if(mid>g_previous_mid)" in text
    assert "else if(mid<g_previous_mid)" in text
    assert "sign=g_last_nonzero_sign;" in text
    assert "if(sign!=0)" in text
    assert "g_classified_updates++;" in text
    assert "g_quote_tick_delta+=sign;" in text
    assert "g_exact_duplicate_ticks++" in text


def test_prereg_is_source_only_and_seals_outcomes() -> None:
    text = PREREG.read_text(encoding="utf-8-sig")
    assert "FROZEN_PRE_OUTCOME_SOURCE_ONLY" in text
    assert "Validation 2023-01-01 through 2024-12-31" in text
    assert "zero economic trials" in text
    assert "PASS_SOURCE_FEASIBILITY_MAY_DRAFT_ECONOMIC_CHILD" in text
