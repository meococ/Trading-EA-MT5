"""Unit tests for profile_zones.py (T-PAPRO-ZONE-1)."""

import numpy as np
from fixtures import load_ctx, slice_bars, synthetic_bars, synthetic_ctx

from common import ZoneContext
from profile_zones import ProfileZones


def _h1_cut(h1, bars, t):
    keep = int(bars["t"][t]) + 300
    return int(np.searchsorted(h1["t"] + 3600, keep, side="right"))


def test_zones_created_and_bounded():
    ctx = synthetic_ctx(n=3000)
    g = ProfileZones(ctx).run()
    assert len(g._zones) > 0
    for z in g._zones:
        A = ctx.a(z.created_idx)
        assert A == A and A > 0
        lo0, hi0 = z.band_at(z.created_idx)
        assert 0.19 * A <= (hi0 - lo0) <= 0.62 * A + 1e-12, z.zid
        for key in ("poc", "val", "vah", "nbins", "window_bars"):
            assert key in z.meta, (z.zid, key)
    n_armed = 0
    for t in range(288, 3000, 12):
        A = ctx.a(t)
        close = float(ctx.bars["c"][t])
        armed = g.views_at(t, arm=True)
        assert len(armed) <= g.cfg["arm_max"]
        n_armed += len(armed)
        for v in armed:
            assert v.lo <= v.hi
            assert v.width > 0.0
            assert abs(v.center - close) <= 2.0 * A + 1e-9
    assert n_armed > 0


def test_prefix_invariance_local():
    m5, h1 = synthetic_bars(n=2600, seed=13)
    g_full = ProfileZones(ZoneContext(m5, h1)).run()
    cut = 2000
    ctx_cut = ZoneContext(slice_bars(m5, cut + 1),
                          slice_bars(h1, _h1_cut(h1, m5, cut)))
    g_cut = ProfileZones(ctx_cut).run()
    for t in (1200, 1800, 2000):
        assert g_cut.zones_at(t) == g_full.zones_at(t), t


def test_real_data_smoke():
    ctx = load_ctx(max_bars=6000)
    g = ProfileZones(ctx).run()
    assert any(z.kind == "profile_poc" for z in g._zones)
    zs = g.zones_at(5999)
    assert isinstance(zs, list)
    for z in zs:
        for key in ("lo", "hi", "kind", "strength", "born_idx", "touches",
                    "fresh"):
            assert key in z, key
        assert z["kind"] == "profile_poc"
        assert z["lo"] <= z["hi"]
        assert z["born_idx"] <= 5999
