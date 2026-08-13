from pathlib import Path
import re


HERE = Path(__file__).resolve()
CHILD_ROOT = HERE.parents[2]
PARENT_ROOT = CHILD_ROOT.parent / "EA_ProspectiveCalendarPIT"
CHILD = CHILD_ROOT / "EA_ProspectiveCalendarPITMQDemo.mq5"
PARENT = PARENT_ROOT / "EA_ProspectiveCalendarPIT.mq5"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def test_capability_identity_and_fail_closed_guards() -> None:
    src = _text(CHILD)
    assert "HYP-CALENDAR-PIT-MQDEMO-001" in src
    assert 'AccountInfoString(ACCOUNT_SERVER)!="MetaQuotes-Demo"' in src
    assert "MQLInfoInteger(MQL_TRADE_ALLOWED)" in src
    assert "MQLInfoInteger(MQL_TESTER)" in src
    assert "MQLInfoInteger(MQL_OPTIMIZATION)" in src
    assert '#define FOLDER         "calendar_pit_mqdemo_001/"' in src
    assert "CalendarValueHistoryByEvent" in src
    assert "CalendarValueLast" not in src


def test_no_price_or_trade_surface() -> None:
    src = _text(CHILD)
    forbidden = re.compile(
        r"\b(?:OrderSend|OrderCheck|CTrade|CopyRates|CopyTicks|"
        r"SymbolInfo(?:Double|Integer|String)?|iClose|iOpen|iHigh|iLow|iTime|"
        r"Position(?:Select|Get|Set)?|HistoryDeal)\b"
    )
    assert forbidden.search(src) is None


def test_calendar_catalog_query_and_diff_logic_is_byte_identical() -> None:
    parent = _text(PARENT)
    child = _text(CHILD)
    start = "void DoCountries()"
    end = "void Step()"
    parent_slice = parent[parent.index(start):parent.index(end)]
    child_slice = child[child.index(start):child.index(end)]
    assert child_slice == parent_slice
