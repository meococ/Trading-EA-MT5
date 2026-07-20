from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "research" / "analyze_hyp018_tick_collection.py"


def source() -> str:
    return ANALYZER.read_text(encoding="utf-8")


def test_analyzer_exists_and_binds_exact_identity():
    text = source()
    assert "HYP-ICT-FVG-TICK-INIT-COLLECT-EURUSD-M5-018" in text
    assert "41536FFC43BE85B1250A627197BD63FED5C7D5C7CF87D8965163F5449EACDA40" in text


def test_analyzer_never_reads_tester_report():
    text = source().lower()
    assert "report.html" not in text
    assert "profit_factor" not in text
    assert "deal_profit" not in text


def test_analyzer_binds_all_frozen_materiality_gates():
    text = source()
    assert "MIN_DEFINED_FRACTION = 0.99" in text
    assert "MIN_SIGN_SHARE = 0.20" in text
    assert "MIN_AGREE_CADENCE = 2.0" in text
    assert '"2018-2022"' in text
    assert '"2023-YTD"' in text


def test_analyzer_uses_exact_era_hybrid_clock_and_sessions():
    text = source()
    assert "year >= 2024" in text
    assert "LONDON = (7 * 60, 11 * 60)" in text
    assert "NEW_YORK = (13 * 60, 17 * 60)" in text


def test_result_is_deterministic_and_outcome_blind():
    text = source()
    assert "sort_keys=True" in text
    assert "forbidden_result_keys" in text
    assert "LifecycleTrades row count only" in text
