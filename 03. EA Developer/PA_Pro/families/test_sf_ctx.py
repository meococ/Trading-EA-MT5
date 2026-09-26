"""test_sf_ctx.py — unit + adversarial tests for families/sf_ctx.py.

Run:  python -m pytest test_sf_ctx.py -q   (or python test_sf_ctx.py)

Coverage:
- run_pass == run() + views_at (zone universe AND state, incl. armed flags);
- prefix invariance (truncated ctx -> identical snapshots before the cut);
- future-bar mutation invariance;
- build_arrays causal scalars (trend domain, monotone H1 swing indices,
  warmup mask handling, slot cap);
- cache save/load round-trip.
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PA_PRO = os.path.dirname(HERE)
ZONES_DIR = os.path.join(PA_PRO, "struct", "zones")
TESTS_DIR = os.path.join(ZONES_DIR, "tests")
for _p in (HERE, ZONES_DIR, TESTS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx                       # noqa: E402
import registry                     # noqa: E402
from fixtures import synthetic_ctx, synthetic_bars  # noqa: E402
from common import ZoneContext      # noqa: E402


GENS = ["line1_cluster", "fractal_h1", "sd_base"]


def _collect(ctx, gen_name, step=113):
    """run_pass; return {t: views} at sampled bars."""
    gen = registry.get(gen_name)(ctx)
    snaps = {}

    def cb(t, views):
        if t % step == 0 or t == ctx.n - 1:
            snaps[t] = views

    sf_ctx.run_pass(ctx, gen, cb=cb)
    return snaps


def _view_tuple(v):
    return (v.zid, round(v.lo, 9), round(v.hi, 9), round(v.strength, 6),
            v.touches, bool(v.fresh), v.n_respected, v.broken_idx,
            v.role_flip, v.age, v.last_touch, round(v.quality, 6),
            bool(v.meta.get("_armed")))


def _ref_views(ctx, gen, t):
    """Reference: a fresh run() + views_at(t) with NEAR_ATR subset + arming."""
    import common
    va = gen.views_at(t, arm=False)
    A = ctx.a(t)
    if not (A == A and A > 0):
        return []
    close = float(ctx.bars["c"][t])
    near = [v for v in va
            if abs(0.5 * (v.lo + v.hi) - close) <= sf_ctx.NEAR_ATR * A]
    near.sort(key=lambda v: (-v.strength, v.zid))
    armed = {v.zid for v in common.arm_zones(near, close, A, gen.cfg)}
    for v in near:
        v.meta["_armed"] = v.zid in armed
    return near


def test_run_pass_matches_views_at():
    for g in GENS:
        ctx = synthetic_ctx(n=2400, seed=11)
        snaps = _collect(ctx, g)
        gen2 = registry.get(g)(ctx).run()
        for t, views in snaps.items():
            ref = _ref_views(ctx, gen2, t)
            mine = [_view_tuple(v) for v in views]
            want = [_view_tuple(v) for v in ref]
            assert mine == want, f"{g} t={t}: {mine[:3]} != {want[:3]}"
    print("run_pass == run()+views_at: OK")


def _truncate(m5, h1, n_bars):
    """Slice m5 to n_bars and rebuild H1 from the sliced M5 (complete
    buckets only) — the true 'same data, shorter history' prefix."""
    from fixtures import _h1_from_m5
    m5c = {k: (np.asarray(v)[:n_bars] if hasattr(v, "__len__") and
               not isinstance(v, str) else v) for k, v in m5.items()}
    return m5c, _h1_from_m5(m5c)


def test_prefix_invariance():
    """Truncating the ctx must not change snapshots at earlier bars."""
    for g in GENS:
        m5, h1 = synthetic_bars(n=2400, seed=5)
        ctx_full = ZoneContext(m5, h1)
        m5c, h1c = _truncate(m5, h1, 1200)
        ctx_cut = ZoneContext(m5c, h1c)
        assert np.array_equal(ctx_full.bars["c"][:1200], ctx_cut.bars["c"])
        snaps_full = _collect(ctx_full, g, step=97)
        snaps_cut = _collect(ctx_cut, g, step=97)
        # bars near the cut can legitimately differ (the last H1 bucket of
        # the truncated ctx may be incomplete) -> margin of one H1 bar.
        for t, views in snaps_cut.items():
            if t >= 1200 - 24:
                continue
            assert t in snaps_full
            mine = [_view_tuple(v) for v in views]
            want = [_view_tuple(v) for v in snaps_full[t]]
            assert mine == want, f"{g} t={t} prefix changed: {mine[:3]} != {want[:3]}"
    print("prefix invariance: OK")


def test_future_mutation():
    """Mutating bars after t0 must not change snapshots at bars <= t0."""
    from fixtures import _h1_from_m5
    m5, h1 = synthetic_bars(n=2400, seed=3)
    t0 = 1000
    m5b = dict(m5)
    for k in ("o", "h", "l", "c"):
        a = np.asarray(m5[k]).copy()
        a[t0 + 1:] = a[t0 + 1:] * 1.5 + 0.02   # violent future change
        m5b[k] = a
    h1b = _h1_from_m5(m5b)
    ctx_a = ZoneContext(m5, h1)
    ctx_b = ZoneContext(m5b, h1b)
    for g in ("line1_cluster", "sd_base"):
        snaps_a = _collect(ctx_a, g, step=97)
        snaps_b = _collect(ctx_b, g, step=97)
        for t, views in snaps_a.items():
            if t > t0 - 24:
                continue
            mine = [_view_tuple(v) for v in views]
            want = [_view_tuple(v) for v in snaps_b[t]]
            assert mine == want, f"{g} t={t}: future mutation leaked"
    print("future-mutation invariance: OK")


def _h4_from_h1(h1):
    n = len(h1["t"]) // 4
    if n == 0:
        return h1
    o = h1["o"][0::4][:n]
    h = h1["h"][: n * 4].reshape(n, 4).max(1)
    lo = h1["l"][: n * 4].reshape(n, 4).min(1)
    c = h1["c"][3::4][:n]
    return {"symbol": h1["symbol"], "t": h1["t"][0::4][:n].astype(np.int64),
            "o": o, "h": h, "l": lo, "c": c}


def test_build_arrays_scalars():
    ctx = synthetic_ctx(n=2400, seed=9)
    m5, h1 = ctx.bars, ctx.h1
    h4 = _h4_from_h1(h1)
    D = sf_ctx.build_arrays(ctx, "line1_cluster", "SYN", "DESIGN", h4)
    n = ctx.n
    assert D["t"].shape == (n,)
    assert set(np.unique(D["s_tr_h1"])) <= {-1, 0, 1}
    assert set(np.unique(D["s_tr_h4"])) <= {-1, 0, 1}
    # h1 swing anchors are causal and monotone non-decreasing
    hi_i = D["s_h1_hi_i"]
    seen = hi_i[hi_i >= 0]
    assert np.all(np.diff(seen) >= 0)
    # slot cap respected
    assert D["zf"].shape == (n, sf_ctx.SLOTS, sf_ctx.ZF_N)
    assert D["zcnt"].max() <= 64
    # zones_at round-trips a record
    some = np.flatnonzero(D["zcnt"] > 0)
    assert len(some) > 0, "no zones recorded at all on synthetic data"
    recs = sf_ctx.zones_at(D, int(some[0]))
    assert recs and recs[0]["lo"] <= recs[0]["hi"]
    # warmup flag: synthetic has none -> first_live_idx == 0
    assert int(D["first_live_idx"]) == 0
    print("build_arrays scalars: OK")


def test_cache_roundtrip(tmp_path=None):
    import tempfile
    ctx = synthetic_ctx(n=600, seed=13)
    m5, h1 = ctx.bars, ctx.h1
    h4 = _h4_from_h1(h1)
    D = sf_ctx.build_arrays(ctx, "fractal_h1", "SYN", "DESIGN", h4)
    d = tempfile.mkdtemp()
    path = sf_ctx.cache_path("SYN", "fractal_h1", d)
    np.savez_compressed(path, **{
        k: (np.array([repr(v)]) if isinstance(v, dict)
            else np.array([v]) if isinstance(v, str) else v)
        for k, v in D.items()})
    L = sf_ctx.load_cache("SYN", "fractal_h1", d)
    assert L["symbol"] == "SYN"
    assert np.array_equal(L["zcnt"], D["zcnt"])
    assert np.allclose(L["zlo"], D["zlo"], equal_nan=True)
    print("cache roundtrip: OK")


if __name__ == "__main__":
    test_run_pass_matches_views_at()
    test_prefix_invariance()
    test_future_mutation()
    test_build_arrays_scalars()
    test_cache_roundtrip()
    print("ALL sf_ctx tests passed")
