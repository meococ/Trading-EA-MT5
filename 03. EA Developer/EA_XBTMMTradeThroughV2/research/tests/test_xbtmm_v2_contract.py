from __future__ import annotations

import csv
import gzip
import importlib.util
import json
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[2]
EA_SOURCE = PACKAGE / "EA_XBTMMTradeThroughV2.mq5"
PREREG = PACKAGE / "research" / "HYP-XBT-MM-TRADETHROUGH-002_FROZEN_DESIGN_PREREG.md"
BUILDER = PACKAGE / "research" / "tools" / "build_xbtmm_event_stream.py"

SPEC = importlib.util.spec_from_file_location("build_xbtmm_event_stream", BUILDER)
assert SPEC and SPEC.loader
sut = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sut)


def write_gzip_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def stamp(second: int, micros: int = 0) -> str:
    hour, rem = divmod(second, 3600)
    minute, sec = divmod(rem, 60)
    return f"2018-01-01D{hour:02d}:{minute:02d}:{sec:02d}.{micros:06d}000"


def test_mql5_freezes_strict_trade_through_and_latency_boundaries() -> None:
    source = EA_SOURCE.read_text(encoding="utf-8")

    assert "const long   QUOTE_SIZE=20;" in source
    assert "const long   SOFT_INVENTORY=40;" in source
    assert "const long   HARD_INVENTORY=80;" in source
    assert "const long   ORDER_LATENCY_US=400000;" in source
    assert "const long   ACTION_INTERVAL_US=2000000;" in source
    assert "const long   MAX_QUOTE_AGE_US=2000000;" in source
    assert "const double TAKER_FEE_RATE=0.00075;" in source
    assert "order.pending_effective_us=decision_us+ORDER_LATENCY_US;" in source
    assert "order.pending_effective_us-order.pending_decision_us!=ORDER_LATENCY_US" in source
    assert "state.bid_order.pending_effective_us<time_us" in source
    assert "state.ask_order.pending_effective_us<time_us" in source
    assert "trade_price<state.bid_order.price" in source
    assert "trade_price>state.ask_order.price" in source
    assert '"STRICT_TRADE_THROUGH"' in source
    assert "passive ? 0.0" in source


def test_quote_expiry_precedes_every_trade_match_and_does_not_consume_qvr() -> None:
    source = EA_SOURCE.read_text(encoding="utf-8")
    loop = source.index("while(!FileIsEnding(handle)")
    expiry = source.index("ExpireStaleOrders(g_candidate,time_us);", loop)
    trade = source.index("if(kind==EVENT_TRADE)", loop)

    assert expiry < trade
    assert "time_us>=state.bid_order.expiry_us" in source
    assert "time_us>=state.ask_order.expiry_us" in source
    expiry_body = source[source.index("void ExpireStaleOrders") : source.index("bool FundingBlackout")]
    assert "CountQuoteAction" not in expiry_body
    assert "g_last_quote_us+MAX_QUOTE_AGE_US" in source


def test_funding_retirement_fifo_and_xbt_nav_are_frozen() -> None:
    source = EA_SOURCE.read_text(encoding="utf-8")

    assert "FUNDING_QUIET_LEAD_US=4400000" in source
    assert "FUNDING_FIRST_CANCEL_LEAD_US=2400000" in source
    assert "FUNDING_SECOND_CANCEL_LEAD_US=400000" in source
    assert "FundingRetirementQuiet(time_us)" in source
    assert "InventoryLot lots[8]" in source
    assert "state.lots[0].open_us+MAX_HOLD_US" in source
    assert "RemoveFirstLot(state);" in source
    assert "max_drawdown_xbt_pct" in source
    assert "max_collateral_usd_drawdown_pct" in source
    assert "engineering_gate_pass=%s" in source


def test_terminal_liquidation_is_included_in_xbt_drawdown() -> None:
    source = EA_SOURCE.read_text(encoding="utf-8")
    end = source.index('// Design end is a forced taker liquidation')
    close = source.index('if(g_fill_handle!=INVALID_HANDLE)', end)
    terminal_block = source[end:close]

    assert 'ForceFlatten(g_candidate,g_last_event_us,"END_OF_STREAM");' in terminal_block
    assert 'ForceFlatten(g_null,g_last_event_us,"END_OF_STREAM");' in terminal_block
    assert terminal_block.index("UpdateEquity(g_candidate,MidPrice());") > terminal_block.index(
        'ForceFlatten(g_candidate,g_last_event_us,"END_OF_STREAM");'
    )
    assert terminal_block.index("UpdateEquity(g_null,MidPrice());") > terminal_block.index(
        'ForceFlatten(g_null,g_last_event_us,"END_OF_STREAM");'
    )


def test_builder_preserves_trade_before_quote_ties_and_passes_source_gate(tmp_path: Path) -> None:
    quote_path = tmp_path / "quote-20180101.csv.gz"
    trade_path = tmp_path / "trade-20180101.csv.gz"
    output_path = tmp_path / "20180101.xbtmm"
    manifest_path = tmp_path / "manifest.json"

    quote_rows = []
    for second in range(0, 86_400, 60):
        quote_rows.append(
            {
                "timestamp": stamp(second),
                "symbol": "XBTUSD",
                "bidSize": 100,
                "bidPrice": 10_000.0,
                "askPrice": 10_000.5,
                "askSize": 120,
            }
        )
    quote_rows.append(
        {
            "timestamp": stamp(86_399, 999_000),
            "symbol": "XBTUSD",
            "bidSize": 100,
            "bidPrice": 10_000.0,
            "askPrice": 10_000.5,
            "askSize": 120,
        }
    )
    trade_rows = [
        {
            "timestamp": stamp(60),
            "symbol": "XBTUSD",
            "side": "Sell",
            "size": 20,
            "price": 9_999.5,
            "tickDirection": "MinusTick",
            "trdMatchID": "one",
            "grossValue": 1,
            "homeNotional": 1,
            "foreignNotional": 1,
        },
        {
            "timestamp": stamp(86_399, 500_000),
            "symbol": "XBTUSD",
            "side": "Buy",
            "size": 20,
            "price": 10_001.0,
            "tickDirection": "PlusTick",
            "trdMatchID": "two",
            "grossValue": 1,
            "homeNotional": 1,
            "foreignNotional": 1,
        },
    ]
    write_gzip_csv(
        quote_path,
        ["timestamp", "symbol", "bidSize", "bidPrice", "askPrice", "askSize"],
        quote_rows,
    )
    write_gzip_csv(
        trade_path,
        [
            "timestamp",
            "symbol",
            "side",
            "size",
            "price",
            "tickDirection",
            "trdMatchID",
            "grossValue",
            "homeNotional",
            "foreignNotional",
        ],
        trade_rows,
    )

    manifest = sut.build(quote_path, trade_path, output_path, manifest_path, "XBTUSD")

    assert manifest["schema_version"] == "xbtmm_event_stream_manifest.v2"
    assert manifest["integrity"]["source_gate_pass"] is True
    assert manifest["integrity"]["trade_gap_standalone_gate"] is False
    assert output_path.stat().st_size == sut.HEADER.size + manifest["output"]["records"] * sut.RECORD.size

    with output_path.open("rb") as handle:
        handle.seek(sut.HEADER.size)
        records = [sut.RECORD.unpack(handle.read(sut.RECORD.size)) for _ in range(3)]
    assert [record[1] for record in records] == [sut.QUOTE, sut.TRADE, sut.QUOTE]
    assert records[1][0] == records[2][0]


def test_current_preflight_and_prereg_keep_future_splits_sealed() -> None:
    manifest_path = PACKAGE / "research" / "preflight" / "HYP-XBT-MM-TRADETHROUGH-002" / "20180101_event_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prereg = PREREG.read_text(encoding="utf-8")

    assert manifest["integrity"]["source_gate_pass"] is True
    assert manifest["integrity"]["invalid_quote_time_ratio"] <= 0.005
    assert "DESIGN: `[2018-01-01, 2022-01-01)`" in prereg
    assert "VALIDATION: `[2022-01-01, 2024-01-01)` sealed" in prereg
    assert "HOLDOUT: `[2024-01-01, latest]` sealed" in prereg
