import csv
import hashlib
import importlib.util
import json
import re
from bisect import bisect_left
from datetime import datetime
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
WORKSPACE = PACKAGE.parents[1]
RAW = (
    WORKSPACE
    / "02. AlphaFactory"
    / "data"
    / "forexfactory"
    / "EURUSD"
    / "news_events"
    / "forexfactory_high_impact_eurusd_2019_2022.weekly.raw.json"
)
CSV = RAW.with_name("forexfactory_high_impact_eurusd_2019_2022.csv")
INCLUDE = PACKAGE / "NewsCalendar2019_2022.mqh"
AUDIT = PACKAGE / "research" / "evidence" / "20260718_NEWS_CALENDAR_BUILD_AUDIT.json"
BUILDER = PACKAGE / "research" / "build_news_calendar_artifacts.py"
SOURCE = PACKAGE / "EA_ICTFVGReportFidelity.mq5"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_builder():
    spec = importlib.util.spec_from_file_location("news_builder", BUILDER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_raw_weekly_evidence_validates_fail_closed() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    events, metrics = load_builder().validate(raw)
    assert metrics["week_count"] == 209
    assert metrics["event_count"] == 1282
    assert metrics["unique_event_ids"] == 1282
    assert metrics["anchors"]["nfp_exact"] == 48
    assert metrics["anchors"]["dec_2022_cpi"] == 4
    assert metrics["anchors"]["dec_2022_fomc"] == 4
    assert metrics["anchors"]["dec_2022_ecb"] == 3
    assert not metrics["validation_errors"]
    assert events[0]["event_time_utc"] == "2019-01-03T15:00:00.000Z"
    assert events[-1]["event_time_utc"] == "2022-12-23T13:30:00.000Z"


def test_generated_artifact_hash_chain_is_current() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert audit["verdict"] == "PASS_DIAGNOSTIC_SOURCE_C"
    assert audit["promotion_eligible"] is False
    assert audit["raw_sha256"] == digest(RAW)
    assert audit["csv_sha256"] == digest(CSV)
    assert audit["include_sha256"] == digest(INCLUDE)
    include = INCLUDE.read_text(encoding="utf-8")
    assert audit["raw_sha256"] in include
    assert audit["metrics"]["event_count"] == 1282
    assert audit["metrics"]["calendar_timestamp_count"] == 869
    assert audit["metrics"]["collapsed_same_timestamp_event_count"] == 413
    assert "#define NEWS_CALENDAR_COUNT 869" in include


def test_csv_is_unique_sorted_and_blackout_boundaries_are_symmetric() -> None:
    with CSV.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1282
    assert len({row["event_id"] for row in rows}) == 1282
    epochs = [
        int(datetime.fromisoformat(row["event_time_utc"].replace("Z", "+00:00")).timestamp())
        for row in rows
    ]
    assert epochs == sorted(epochs)

    event = int(datetime.fromisoformat("2022-12-13T13:30:00+00:00").timestamp())
    index = bisect_left(epochs, event)
    assert epochs[index] == event
    assert abs(epochs[index] - (event - 30 * 60)) <= 30 * 60
    assert abs(epochs[index] - (event + 30 * 60)) <= 30 * 60
    assert abs(epochs[index] - (event - 30 * 60 - 1)) > 30 * 60


def test_mql5_lookup_collapses_same_timestamp_events_strictly() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    events, _ = load_builder().validate(raw)
    rendered = load_builder().include_text(events, digest(RAW))
    count_match = re.search(r"#define NEWS_CALENDAR_COUNT (\d+)", rendered)
    array_match = re.search(r"=\s*\{(.*?)\};", rendered, flags=re.DOTALL)
    assert count_match and array_match
    epochs = [int(value) for value in re.findall(r"\d+", array_match.group(1))]
    assert len(events) == 1282
    assert int(count_match.group(1)) == 869
    assert len(epochs) == 869
    assert all(left < right for left, right in zip(epochs, epochs[1:]))


def test_ea_uses_hash_bound_binary_search_and_fails_closed_outside_coverage() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    required = [
        '#include "NewsCalendar2019_2022.mqh"',
        "NewsCalendarValid",
        "NEWS_CALENDAR_COVERAGE_START_UTC",
        "NEWS_CALENDAR_COVERAGE_END_UTC",
        "while(left<right)",
        "InpNewsBlackoutMinutes=30",
        "NEWS_CALENDAR_SOURCE_SHA256",
        "g_news_rejections",
    ]
    for token in required:
        assert token in source
    assert "no hash-bound calendar is installed" not in source
