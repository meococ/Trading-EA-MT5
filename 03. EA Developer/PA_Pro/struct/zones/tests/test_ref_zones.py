"""Unit tests for ref_zones.py (T-PAPRO-ZONE-1)."""

import numpy as np
import pytest
from fixtures import load_ctx, slice_bars, synthetic_bars, synthetic_ctx

from common import ZoneContext
from ref_zones import RefZones

_SINGLE_KINDS = ("pdh", "pdl", "pdc", "asia_hi", "asia_lo", "wk_hi", "wk_lo")


def _h1_cut(h1, bars, t):
    keep = int(bars["t"][t]) + 300
    return int(np.searchsorted(h1["t"] + 3600, keep, side="right"))


def test_zones_created_and_bounded():
    ctx = synthetic_ctx(n=3000)
    g = RefZones(ctx).run()
    assert len(g._zones) > 0
    kinds = {z.kind for z in g._zones}
    for kind in ("pdh", "pdl", "pdc", "round", "asia_hi", "asia_lo"):
        assert kind in kinds, kind
    for z in g._zones:                                # ~10 synthetic days
        A = ctx.a(z.created_idx)
        assert A == A and A > 0
        lo0, hi0 = z.band_at(z.created_idx)
        assert abs((hi0 - lo0) - g.cfg["width_atr"] * A) <= 1e-9
        assert lo0 <= hi0
    n_armed = 0
    for t in (600, 1350, 1600, 1725, 2200, 2375, 2425, 2999):
        A = ctx.a(t)
        close = float(ctx.bars["c"][t])
        armed = g.views_at(t, arm=True)
        assert len(armed) <= g.cfg["arm_max"]
        n_armed += len(armed)
        for v in armed:
            assert v.width > 0.0
            assert abs(v.center - close) <= 2.0 * A + 1e-9
    assert n_armed > 0


def test_retirement_keeps_only_newest():
    ctx = synthetic_ctx(n=3000)
    g = RefZones(ctx).run()
    b = ctx.bars
    rolls = [t for t in range(1, 3000)
             if (b["t"][t] // 86400) != (b["t"][t - 1] // 86400)]
    assert len(rolls) >= 9                       # ~10 server days
    for r in rolls:
        # the rollover bar itself is a one-bar crossfade: `_retire(prev, r)`
        # sets the retired zone's last visible bar to r (`views_at` drops only
        # `t > end_idx`), so the strict invariant is checked from r + 1 on.
        for t in (r + 1, min(r + 144, 2999)):
            live = g.views_at(t, arm=False)
            for kind in _SINGLE_KINDS:
                assert sum(v.kind == kind for v in live) <= 1, (kind, t)
            assert sum(v.kind == "round" for v in live) <= 2, t
        # "round" publishes two slots per day: the newest pair is exactly the
        # grid pair around the rollover close.
        want = sorted(ctx.refs.round_near(float(b["c"][r])))
        got = sorted(v.center for v in g.views_at(r + 1, arm=False)
                     if v.kind == "round")
        assert got == pytest.approx(want)


def test_prefix_invariance_local():
    m5, h1 = synthetic_bars(n=2600, seed=13)
    g_full = RefZones(ZoneContext(m5, h1)).run()
    cut = 2000
    ctx_cut = ZoneContext(slice_bars(m5, cut + 1),
                          slice_bars(h1, _h1_cut(h1, m5, cut)))
    g_cut = RefZones(ctx_cut).run()
    for t in (1200, 1800, 2000):
        assert g_cut.zones_at(t) == g_full.zones_at(t), t


def test_real_data_smoke():
    ctx = load_ctx(max_bars=6000)
    g = RefZones(ctx).run()
    assert len(g._zones) > 0
    zs = g.zones_at(5999)
    assert isinstance(zs, list)
    for z in zs:
        for key in ("lo", "hi", "kind", "strength", "born_idx", "touches",
                    "fresh"):
            assert key in z, key
        assert z["kind"] in _SINGLE_KINDS + ("round",)
        assert z["lo"] <= z["hi"]
        assert z["born_idx"] <= 5999
    kinds = sorted({z.kind for z in g._zones})
    print(f"real_data zones={len(g._zones)} kinds={kinds} armed_last={len(zs)}")
