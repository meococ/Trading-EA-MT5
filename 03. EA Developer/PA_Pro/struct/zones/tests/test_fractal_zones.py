"""Unit tests for fractal_zones.py (T-PAPRO-ZONE-1)."""

import numpy as np
from fixtures import load_ctx, slice_bars, synthetic_bars, synthetic_ctx

from common import ZoneContext
from fractal_zones import FractalZones


def _h1_cut(h1, bars, t):
    keep = int(bars["t"][t]) + 300
    return int(np.searchsorted(h1["t"] + 3600, keep, side="right"))


def test_zones_created_and_bounded():
    ctx = synthetic_ctx(n=3000)
    g = FractalZones(ctx).run()
    assert len(g._zones) > 0
    by_id = {z.zid: z for z in g._zones}
    n_armed = 0
    for t in (600, 1350, 1600, 1725, 2200, 2375, 2425, 2999):
        A = ctx.a(t)
        close = float(ctx.bars["c"][t])
        armed = g.views_at(t, arm=True)
        assert len(armed) <= g.cfg["arm_max"]
        n_armed += len(armed)
        for v in armed:
            assert v.width > 0.0
            z = by_id[v.zid]
            lo0, hi0 = z.band_at(z.created_idx)
            assert 0.2 * A <= (hi0 - lo0) <= 0.65 * A + 1e-12
            assert abs(v.center - close) <= 2.0 * A + 1e-9
    assert n_armed > 0


def test_prefix_invariance_local():
    m5, h1 = synthetic_bars(n=2600, seed=13)
    g_full = FractalZones(ZoneContext(m5, h1)).run()
    cut = 2000
    ctx_cut = ZoneContext(slice_bars(m5, cut + 1),
                          slice_bars(h1, _h1_cut(h1, m5, cut)))
    g_cut = FractalZones(ctx_cut).run()
    for t in (1200, 1800, 2000):
        assert g_cut.zones_at(t) == g_full.zones_at(t), t


def test_real_data_smoke():
    ctx = load_ctx(max_bars=6000)
    g = FractalZones(ctx).run()
    assert len(g._zones) > 0
    zs = g.zones_at(5999)
    assert isinstance(zs, list)
    for z in zs:
        for key in ("lo", "hi", "kind", "strength", "born_idx", "touches",
                    "fresh"):
            assert key in z, key
        assert z["kind"] == "swing_h1"
        assert z["lo"] <= z["hi"]
        assert z["born_idx"] <= 5999
