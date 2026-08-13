from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "EA_ProspectiveDOMTape.mq5"


def source() -> str:
    return SOURCE.read_text(encoding="utf-8-sig")


def test_frozen_identity_and_universe() -> None:
    text = source()
    assert '#define COLLECTOR_VER  "1.1.1"' in text
    assert '#define SCHEMA_VER     "1.1"' in text
    assert '{"XAUUSD","EURUSD","GBPUSD","USDJPY"}' in text
    assert "#define N_SYM          4" in text


def test_event_driven_dom_api_only() -> None:
    text = source()
    assert "MarketBookAdd" in text
    assert "void OnBookEvent" in text
    assert "MarketBookGet" in text
    assert "MarketBookRelease" in text
    assert text.count("MarketBookGet(") == 1
    assert "OnTimer(){ Heartbeat(); }" in text


def test_forbidden_market_and_trade_apis_absent() -> None:
    text = source()
    forbidden = (
        "CopyRates",
        "CopyTicks",
        "CalendarValue",
        "WebRequest",
        "Trade.mqh",
        "CTrade",
        "OrderSend",
        "OrderCheck",
        "PositionOpen",
        "PositionSelect",
        "iMA(",
        "iATR(",
    )
    for token in forbidden:
        assert token not in text


def test_tester_fail_closed_and_safety_receipts() -> None:
    text = source()
    assert "MQL_TESTER" in text and "MQL_OPTIMIZATION" in text
    assert "return(INIT_FAILED)" in text
    for literal in (
        '"outcome_accessed\\\":false',
        '"prices_read\\\":false',
        '"orders\\\":false',
        '"trading_disabled\\\":true',
    ):
        assert literal in text


def test_durable_outputs_and_state_gate() -> None:
    text = source()
    for filename in ("dom_tape_v1_1.jsonl", "dom_levels_v1_1.csv", "dom_state_v1_1.txt"):
        assert filename in text
    assert "dom_state_v1_1.tmp" in text
    assert "FileMove(tmp,FILE_COMMON,dst,FILE_COMMON|FILE_REWRITE)" in text
    assert "FileDelete(dst" not in text
    assert "no silent reset" in text
    assert "ns!=N_SYM" in text


def test_single_writer_persistent_handles() -> None:
    text = source()
    assert "dom_writer_v1_1.lock" in text
    assert "g_hLock" in text and "g_hJson" in text and "g_hCsv" in text
    assert "OpenAppendExclusive" in text
    assert "FILE_SHARE_READ" in text
    assert "FILE_SHARE_WRITE" not in text
    assert "CP_UTF8" in text
    assert "FileWriteArray" not in text


def test_reserved_high_water_and_session_tick64() -> None:
    text = source()
    assert "#define SNAP_BLOCK     10000" in text
    assert "#define EV_BLOCK       10000" in text
    assert "snapshot_reserved=" in text and "snapshot_used=" in text
    assert "ReserveSnap()" in text and "ReserveEv(const int ix)" in text
    assert "g_snap_used=g_snap_reserved" in text
    assert "g_s[i].ev_used=g_s[i].ev_reserved" in text
    assert "g_session_tick64" in text
    assert "g_s[ix].last_tick64=0" in text


def test_state_parser_requires_all_high_water_fields() -> None:
    text = source()
    assert "saw_sr" in text and "saw_su" in text
    assert "saw_ev" in text and "saw_sn" in text
    assert "saw_du" in text and "saw_em" in text
    assert "saw_api" in text and "saw_io" in text
    assert "c<48 || c>57" in text


def test_no_per_snapshot_state_replacement() -> None:
    text = source()
    handler = text.split("void OnBookEvent", 1)[1].split("void OnTick", 1)[0]
    assert "SaveState()" not in handler
    assert "ReserveEv(ix)" in handler
    assert "ReserveSnap()" in handler


def test_every_level_and_operational_receipts_present() -> None:
    text = source()
    assert "ArraySize(book)" in text
    assert "for(int i=0;i<n;i++)" in text
    for kind in (
        "INIT",
        "SUBSCRIBE",
        "SNAPSHOT",
        "DUPLICATE",
        "EMPTY_BOOK",
        "API_ERROR_BOOK",
        "HEARTBEAT",
        "IO_ERROR",
        "SHUTDOWN",
        "TICK64_REGRESS",
        "WRITER_LOCK",
        "API_ERROR_TIMER",
    ):
        assert f'"{kind}"' in text or f'\\"{kind}\\"' in text
