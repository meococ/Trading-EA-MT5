from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "EA_ProspectiveCalendarPIT.mq5"


def source_text() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_collector_uses_history_only_prospective_snapshot_diff() -> None:
    text = source_text()
    assert "CalendarValueHistoryByEvent(eid,vals,fromt,tot)" in text
    assert "CalendarEventByCurrency(ccy,evs)" in text
    assert "FUTURE_DISCOVERY_HISTORY" in text
    assert "IDLE_PROOF_HISTORY" in text
    assert "CalendarValueLast(" not in text
    assert "CalendarValueLastByEvent(" not in text


def test_collector_is_trading_and_tester_disabled() -> None:
    text = source_text()
    assert "MQLInfoInteger(MQL_TESTER)" in text
    assert "MQLInfoInteger(MQL_OPTIMIZATION)" in text
    for forbidden in ("OrderSend(", "CTrade", "CopyRates(", "CopyTicks(", "iClose("):
        assert forbidden not in text


def test_collector_preserves_pit_receipt_fields() -> None:
    text = source_text()
    required = (
        "ts_local",
        "ts_server",
        "ts_current",
        "tick64",
        "scheduled_unix",
        "period_unix",
        "old_forecast",
        "new_actual",
        "payload_hash",
        "outcome_accessed\\\":false",
        "prices_read\\\":false",
        "trading_disabled\\\":true",
    )
    for marker in required:
        assert marker in text


def test_collector_preregisters_exact_target_currency_set() -> None:
    text = source_text()
    assert 'string g_ccy[N_CCY] = {"USD","EUR","JPY","GBP","CHF","CAD","AUD","NZD"};' in text
    assert "CALENDAR_IMPORTANCE_MODERATE" in text
    assert '\\"outcome_used\\":false' in text


def test_utf8_and_restart_files_are_explicit() -> None:
    text = source_text()
    assert text.count("CP_UTF8") >= 7
    assert '"catalog_state_v15.txt"' in text
    assert '"occurrence_v15.txt"' in text
    assert '"calendar_pit_v15.jsonl"' in text
    assert '"calendar_pit_v15.csv"' in text


def test_tape_io_and_state_commit_are_fail_closed() -> None:
    text = source_text()
    assert "bool WriteTape(" in text
    assert "return (csv_ok && json_ok);" in text
    assert "if(io_failed || !SaveOcc())" in text
    assert 'Emit("IO_ERROR_HISTORY"' in text
    assert "g_fatal=true;" in text


def test_reinitialization_resets_counts_and_validates_state() -> None:
    text = source_text()
    assert "void ResetMemory()" in text
    assert "ArrayResize(g_ev,0); g_nev=0;" in text
    assert "ArrayResize(g_oc,0); g_noc=0;" in text
    assert "bool LoadCatalog()" in text
    assert "bool LoadOcc()" in text
    assert "if(np<18)" in text


def test_scheduler_has_frozen_windows_and_one_call_sites() -> None:
    text = source_text()
    assert "#define PRE_SEC        21600" in text
    assert "#define POST_SEC       21600" in text
    assert "#define HORIZON_SEC    172800" in text
    assert text.count("CalendarCountries(cs)") == 1
    assert text.count("CalendarEventByCurrency(ccy,evs)") == 1
    assert text.count("CalendarValueHistoryByEvent(eid,vals,fromt,tot)") == 1
    assert "#define DUE_CAP        64" in text
