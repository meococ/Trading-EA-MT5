import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PHYS = os.path.dirname(HERE)
if PHYS not in sys.path:
    sys.path.insert(0, PHYS)

import phys_common as pc  # noqa: E402
from phys_controls import RefIndex, draw_controls  # noqa: E402
from synth import SynthSource, make_bars, flat_zone  # noqa: E402

A = 0.0010


class DummyRef:
    def levels_at(self, t):
        return []


def _scenario(block_ref=False):
    n = 400
    closes = []
    for i in range(n):
        if i < 76:
            closes.append(1.0920 if i % 2 == 0 else 1.0950)
        elif i < 100:
            closes.append(1.0920)
        else:
            closes.append(1.0950)
    closes[50] = 1.0969
    closes[99] = 1.0950
    closes[100] = 1.1000
    bars = make_bars(closes, spread=0.0002)
    bars["h"][50] = 1.0970
    bars["l"][50] = 1.0968
    bars["h"][100] = 1.1005
    bars["l"][100] = 1.0948
    real_zone = flat_zone(1, 1.1000, 1.1010)
    src = SynthSource(bars, [A] * n, [real_zone])
    event = {
        "symbol": "SYNTH", "generator": "synth", "zid": 1, "bar_idx": 100,
        "side": -1, "lo": 1.1000, "hi": 1.1010, "w": 0.0010,
        "near": 1.1000, "far": 1.1010, "m": A, "close_prev": 1.0950,
    }
    return src, bars, event


def test_controls_basic_properties():
    src, bars, event = _scenario()
    ref = RefIndex(DummyRef(), grid_pips=0.0, bars=bars)
    rng = np.random.default_rng([pc.SEED, 99, 100])
    got, cnt = draw_controls(event, src, ref, bars, rng, anchor_i=0)
    assert len(got) == 5
    assert cnt["slots_empty"] == 0
    for g in got:
        assert g["anchor_i"] == 0
        assert g["side"] == -1
        assert g["bar_idx"] == 100
        assert g["w"] == pytest.approx(0.0010)
        assert g["near"] == pytest.approx(g["lo"])
        assert g["lo"] >= event["close_prev"] + pc.AWAY_ATR * A - 1e-12
        assert g["hi"] <= 1.0977 + 1e-12
        assert max(g["lo"] - event["hi"], event["lo"] - g["hi"]) > 0.0
        assert g["tk_dt"] == 0
        assert g["contam_zone"] is False
        assert g["contam_ref"] is False


def test_controls_deterministic():
    src, bars, event = _scenario()
    ref = RefIndex(DummyRef(), grid_pips=0.0, bars=bars)
    out = []
    for _ in range(2):
        rng = np.random.default_rng([pc.SEED, 99, 100])
        got, _ = draw_controls(event, src, ref, bars, rng)
        out.append([(g["lo"], g["hi"], g["bar_idx"]) for g in got])
    assert out[0] == out[1]


def test_controls_self_zone_exclusion():
    src, bars, event = _scenario()
    # place the triggering zone across the sample interval: overlapping draws
    # must be rejected by A1, non-overlapping ones accepted
    event = dict(event, lo=1.0962, hi=1.0972)
    ref = RefIndex(DummyRef(), grid_pips=0.0, bars=bars)
    rng = np.random.default_rng([pc.SEED, 99, 100])
    got, cnt = draw_controls(event, src, ref, bars, rng)
    assert cnt["reject_zone_self"] >= 1
    for g in got:
        assert max(g["lo"] - event["hi"], event["lo"] - g["hi"]) > 0.0


def test_controls_empty_interval():
    src, bars, event = _scenario()
    bars["h"][:100] = np.minimum(bars["h"][:100], 1.0900)
    ref = RefIndex(DummyRef(), grid_pips=0.0, bars=bars)
    rng = np.random.default_rng([pc.SEED, 99, 100])
    got, cnt = draw_controls(event, src, ref, bars, rng)
    assert got == [] and cnt["slots_empty"] == 5


def test_contam_flag_detects_armed_overlap():
    src, bars, event = _scenario()
    # an armed zone covering the sample interval is detection, not exclusion;
    # the close at the fake event bar must be within 2 x A of its centre
    bars["c"][100] = 1.0970
    src._zones.append(flat_zone(7, 1.0962, 1.0972, kind="swing"))
    ref = RefIndex(DummyRef(), grid_pips=0.0, bars=bars)
    rng = np.random.default_rng([pc.SEED, 99, 100])
    got, _ = draw_controls(event, src, ref, bars, rng)
    assert len(got) == 5
    assert any(g["contam_zone"] for g in got)


def test_contam_ref_flag():
    src, bars, event = _scenario()

    class OneRef:
        def levels_at(self, t):
            return [("pdh", 1.0965)]

    ref = RefIndex(OneRef(), grid_pips=0.0, bars=bars)
    rng = np.random.default_rng([pc.SEED, 99, 100])
    got, _ = draw_controls(event, src, ref, bars, rng)
    assert len(got) == 5
    assert any(g["contam_ref"] for g in got)
