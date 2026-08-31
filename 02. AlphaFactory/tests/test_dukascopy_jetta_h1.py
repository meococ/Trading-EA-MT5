from __future__ import annotations

import importlib.util
import json
import struct
import sys
from datetime import date
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "research" / "dukascopy_jetta_h1.py"
spec = importlib.util.spec_from_file_location("dukascopy_jetta_h1", TOOL)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def fixture_payload(side_offset: float = 0.0) -> bytes:
    return json.dumps(
        {
            "timestamp": 1_483_228_800_000,
            "multiplier": 0.00001,
            "shift": 60_000,
            "open": 1.05 + side_offset,
            "high": 1.06 + side_offset,
            "low": 1.04 + side_offset,
            "close": 1.055 + side_offset,
            "times": [60, 60],
            "opens": [1, 2],
            "highs": [1, 2],
            "lows": [1, 2],
            "closes": [1, 2],
            "volumes": [1.25, 2.5],
        }
    ).encode()


def test_month_url_uses_official_monthly_h1_route() -> None:
    assert module.month_url("EUR-USD", "BID", 2017, 1) == (
        "https://jetta.dukascopy.com/v1/candles/trade/hour/EUR-USD/BID/2017/1"
    )
    with pytest.raises(module.JettaH1Error):
        module.month_url("EURUSD", "BID", 2017, 1)
    assert module.month_url(
        "EUR-USD", "ASK", 2026, 8, partial_from_msc=1_785_542_400_000
    ) == (
        "https://jetta.dukascopy.com/v1/candles/trade/hour/EUR-USD/ASK"
        "?from=1785542400000"
    )


def test_decoder_applies_time_and_price_deltas() -> None:
    bars = module.decode_h1(fixture_payload(), "fixture")
    assert len(bars) == 2
    assert bars[0].time == 1_483_232_400
    assert bars[1].time == 1_483_236_000
    assert bars[0].open == pytest.approx(1.05001)
    assert bars[1].close == pytest.approx(1.05503)
    assert bars[0].volume == 1_250_000


def test_decoder_rounds_provider_float_drift_to_source_point() -> None:
    payload = json.loads(fixture_payload())
    payload["low"] = 1.0399999999999998
    payload["close"] = 1.04
    bars = module.decode_h1(json.dumps(payload).encode(), "fixture", point=0.00001)
    assert bars[0].low == pytest.approx(round(bars[0].low, 5))


def test_decoder_envelopes_one_point_provider_ohlc_inconsistency() -> None:
    payload = json.loads(fixture_payload())
    payload["close"] = 1.04
    payload["low"] = 1.04001
    stats: dict[str, int] = {}
    bars = module.decode_h1(
        json.dumps(payload).encode(),
        "fixture",
        point=0.00001,
        normalization_stats=stats,
    )
    assert bars[0].low == bars[0].close
    assert stats["one_point_envelope_corrections"] == 2


def test_decoder_rejects_geometry_correction_larger_than_one_point() -> None:
    payload = json.loads(fixture_payload())
    payload["close"] = 1.04
    payload["low"] = 1.04002
    with pytest.raises(module.JettaH1Error, match="exceeds one point"):
        module.decode_h1(json.dumps(payload).encode(), "fixture", point=0.00001)


def test_decoder_accepts_only_an_explicit_larger_geometry_cap() -> None:
    payload = json.loads(fixture_payload())
    payload["close"] = 1.04
    payload["low"] = 1.04002
    stats: dict[str, int] = {}
    bars = module.decode_h1(
        json.dumps(payload).encode(),
        "fixture",
        point=0.00001,
        max_geometry_correction_points=2,
        normalization_stats=stats,
    )
    assert len(bars) == 2
    assert stats["one_point_envelope_corrections"] == 2


def test_geometry_policy_is_month_specific() -> None:
    row = {
        "max_geometry_correction_points": 1,
        "geometry_exception_months": {
            "2017-09": {
                "max_correction_points": 50,
                "max_corrected_bar_fraction_per_side": 0.05,
            }
        },
    }
    assert module.geometry_policy(row, 2017, 8) == (1, None)
    assert module.geometry_policy(row, 2017, 9) == (50, 0.05)


def test_pairing_uses_bid_ohlc_and_rounded_up_open_spread() -> None:
    bid = module.decode_h1(fixture_payload(), "bid")
    ask = module.decode_h1(fixture_payload(0.000025), "ask")
    paired = module.pair_rates(bid, ask, 0.00001, bid[0].time, bid[-1].time + 1)
    assert [row.spread for row in paired] == [3, 3]
    assert paired[0].open == bid[0].open
    assert paired[0].tick_volume == 1_250_000


def test_pairing_fails_closed_on_timestamp_or_side_mismatch() -> None:
    bid = module.decode_h1(fixture_payload(), "bid")
    ask = module.decode_h1(fixture_payload(0.00002), "ask")
    with pytest.raises(module.JettaH1Error):
        module.pair_rates(bid, ask[:-1], 0.00001, bid[0].time, bid[-1].time + 1)
    crossed = [module.H1Bar(**{**ask[0].__dict__, "open": bid[0].open - 0.00001}), ask[1]]
    with pytest.raises(module.JettaH1Error):
        module.pair_rates(bid, crossed, 0.00001, bid[0].time, bid[-1].time + 1)


def test_pairing_contains_only_crossed_open_before_activation() -> None:
    bid = [module.H1Bar(100, 10.0, 10.1, 9.9, 10.0, 1)]
    ask = [module.H1Bar(100, 9.0, 9.1, 8.9, 9.0, 1)]
    stats: dict[str, int] = {}
    rates = module.pair_rates(
        bid,
        ask,
        0.01,
        100,
        101,
        strategy_active_from=200,
        allow_crossed_open_before_activation=True,
        inactive_crossed_open_spread_points=1,
        pairing_stats=stats,
    )
    assert rates[0].spread == 1
    assert stats["preactivation_crossed_open_count"] == 1
    assert stats["maximum_preactivation_crossed_open_deficit_points"] == 100


def test_pairing_rejects_crossed_open_on_activation() -> None:
    bid = [module.H1Bar(200, 10.0, 10.1, 9.9, 10.0, 1)]
    ask = [module.H1Bar(200, 9.0, 9.1, 8.9, 9.0, 1)]
    with pytest.raises(module.JettaH1Error, match="ASK open below BID open"):
        module.pair_rates(
            bid,
            ask,
            0.01,
            200,
            201,
            strategy_active_from=200,
            allow_crossed_open_before_activation=True,
        )


def test_pairing_allows_independently_timed_h1_extrema() -> None:
    bid = module.decode_h1(fixture_payload(), "bid")
    ask = module.decode_h1(fixture_payload(0.00002), "ask")
    ask[0] = module.H1Bar(
        ask[0].time,
        ask[0].open,
        ask[0].high,
        bid[0].low - 0.00010,
        ask[0].close,
        ask[0].volume,
    )
    paired = module.pair_rates(bid, ask, 0.00001, bid[0].time, bid[-1].time + 1)
    assert paired[0].low == bid[0].low
    assert paired[0].spread >= 1


def test_afrate_binary_contract_is_exact() -> None:
    bid = module.decode_h1(fixture_payload(), "bid")
    ask = module.decode_h1(fixture_payload(0.00002), "ask")
    paired = module.pair_rates(bid, ask, 0.00001, bid[0].time, bid[-1].time + 1)
    payload = module.encode_rates(paired)
    magic, count = module.AFRATE_HEADER.unpack_from(payload)
    assert magic == module.AFRATE_MAGIC
    assert count == 2
    assert len(payload) == module.AFRATE_HEADER.size + 2 * module.AFRATE_RECORD.size
    first = module.AFRATE_RECORD.unpack_from(payload, module.AFRATE_HEADER.size)
    assert first[0] == paired[0].time
    assert first[6] == paired[0].spread


def test_month_iteration_is_inclusive_exclusive() -> None:
    assert list(module.month_iter(date(2017, 12, 15), date(2018, 2, 1))) == [
        (2017, 12),
        (2018, 1),
    ]


def test_cli_exposes_full_download_and_bounded_probe() -> None:
    parser = module.build_parser()
    full = parser.parse_args(
        [
            "download-contract",
            "--contract",
            "contract.json",
            "--contract-sha256",
            "A" * 64,
            "--output-root",
            "data",
        ]
    )
    assert full.func is module.download_contract
    probe = parser.parse_args(
        [
            "probe-month",
            "--contract",
            "contract.json",
            "--contract-sha256",
            "A" * 64,
            "--output-root",
            "data",
            "--symbol",
            "EURUSD",
            "--year",
            "2017",
            "--month",
            "1",
        ]
    )
    assert probe.func is module.probe_month
