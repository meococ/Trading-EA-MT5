from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest


ALPHA_ROOT = Path(__file__).resolve().parents[1]
PRODUCER_PATH = ALPHA_ROOT / "tools" / "build_research_cost_proxy_evidence.py"


def _load_producer():
    spec = importlib.util.spec_from_file_location("research_cost_proxy_producer", PRODUCER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_legacy(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "position_id",
                "symbol",
                "action",
                "volume",
                "commission",
                "is_final_close",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_commission_proxy_aggregates_the_complete_lifecycle(tmp_path: Path) -> None:
    producer = _load_producer()
    source = tmp_path / "legacy.csv"
    rows: list[dict[str, object]] = []
    for position in range(30):
        rows.extend(
            [
                {
                    "position_id": f"P{position:02d}",
                    "symbol": "USDJPY",
                    "action": "OPEN",
                    "volume": "0.50",
                    "commission": "-2.00",
                    "is_final_close": "0",
                },
                {
                    "position_id": f"P{position:02d}",
                    "symbol": "USDJPY",
                    "action": "CLOSE",
                    "volume": "0.50",
                    "commission": "0.00",
                    "is_final_close": "1",
                },
            ]
        )
    _write_legacy(source, rows)

    evidence, summary = producer.build_commission_proxy(source, "USDJPY", "USD")

    assert len(evidence) == 30
    assert {float(row["round_turn_account_per_lot"]) for row in evidence} == {4.0}
    assert summary["minimum"] == pytest.approx(4.0)
    assert summary["maximum"] == pytest.approx(4.0)
    assert summary["statistic_used"] == "maximum"


def test_commission_proxy_rejects_an_incomplete_lifecycle(tmp_path: Path) -> None:
    producer = _load_producer()
    source = tmp_path / "legacy.csv"
    _write_legacy(
        source,
        [
            {
                "position_id": "P01",
                "symbol": "USDJPY",
                "action": "OPEN",
                "volume": "0.50",
                "commission": "-2.00",
                "is_final_close": "0",
            }
        ],
    )

    with pytest.raises(ValueError, match="exactly one final close"):
        producer.build_commission_proxy(source, "USDJPY", "USD")


def test_commission_proxy_rejects_lifecycle_without_explicit_entry_volume(
    tmp_path: Path,
) -> None:
    producer = _load_producer()
    source = tmp_path / "legacy.csv"
    _write_legacy(
        source,
        [
            {
                "position_id": "P01",
                "symbol": "USDJPY",
                "action": "",
                "volume": "0.50",
                "commission": "-2.00",
                "is_final_close": "0",
            },
            {
                "position_id": "P01",
                "symbol": "USDJPY",
                "action": "",
                "volume": "0.50",
                "commission": "0.00",
                "is_final_close": "1",
            },
        ],
    )

    with pytest.raises(ValueError, match="no explicit entry-volume row"):
        producer.build_commission_proxy(source, "USDJPY", "USD")


def test_explicit_quote_sources_do_not_expand_to_unselected_siblings(tmp_path: Path) -> None:
    producer = _load_producer()
    selected = tmp_path / "selected" / "USDJPY_quote_ticks.csv"
    ignored = tmp_path / "ignored" / "USDJPY_quote_ticks.csv"
    for path, base in ((selected, 100.0), (ignored, 200.0)):
        path.parent.mkdir()
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["time_msc", "bid", "ask", "symbol"])
            writer.writeheader()
            for index in range(100):
                writer.writerow(
                    {
                        "time_msc": 1_000 + index,
                        "bid": base,
                        "ask": base + 0.01,
                        "symbol": "USDJPY",
                    }
                )

    quotes, sources = producer.load_unique_quotes(tmp_path, "USDJPY", [selected])

    assert sources == [selected.resolve()]
    assert len(quotes) == 100
    assert {row[1] for row in quotes} == {100.0}


def test_in_place_spread_validation_does_not_rewrite_raw_bytes(tmp_path: Path) -> None:
    producer = _load_producer()
    source = tmp_path / "spread.csv"
    source.write_bytes(
        b"timestamp,symbol,bid,ask\n"
        b"2016-01-04T00:00:01.000Z,USDJPY,118.000,118.010\n"
        b"2020-12-31T23:00:01.000Z,USDJPY,103.000,103.010\n"
    )
    before = source.read_bytes()

    summary = producer.slice_spread_evidence(
        source, source, "USDJPY", "2016.01.04", "2020.12.31"
    )

    assert source.read_bytes() == before
    assert summary["sample_count"] == 2
