from datetime import datetime
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("derive_pdac002_source.py")
SPEC = importlib.util.spec_from_file_location("pdac002", MODULE_PATH)
PDAC002 = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(PDAC002)


def row(stamp: str, direction: str = "LONG") -> dict:
    dt = datetime.fromisoformat(stamp)
    return {
        "hypothesis_id": "HYP-PDAC-XAUUSD-H1-001",
        "decision_time_server": stamp,
        "decision_year": dt.year,
        "direction": direction,
    }


def test_friday_before_20utc_is_kept_winter() -> None:
    # 21:00 server winter -> decision 19:00 UTC -> availability 20:00 UTC, blocked.
    report, kept = PDAC002.derive([row("2018-01-05T21:00:00")])
    assert report["friday_20utc_blocked"] == 1
    assert kept == []


def test_friday_19utc_availability_is_kept() -> None:
    report, kept = PDAC002.derive([row("2018-01-05T20:00:00")])
    assert report["friday_20utc_blocked"] == 0
    assert len(kept) == 1


def test_europe_dst_offset_matches_frozen_rule() -> None:
    assert PDAC002.server_to_utc(datetime(2018, 6, 1, 12)) == datetime(2018, 6, 1, 9)
    assert PDAC002.server_to_utc(datetime(2018, 1, 5, 12)) == datetime(2018, 1, 5, 10)
