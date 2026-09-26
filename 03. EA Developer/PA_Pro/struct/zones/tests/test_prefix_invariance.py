"""Prefix-invariance tests: appending future bars never changes zones known
at t, for every registered generator (mandatory per the task packet).

Anti-vacuity (added after the ZONE-1 review): query bars are chosen
dynamically where the generator's live book is NON-EMPTY, and the test
asserts that non-emptiness.  It compares the FULL live book (`live_dicts`,
including broken/far zones) and the armed set (`zones_at`) between a run on
bars[:T+1] and a run with bars appended (bars[:T2]).

Two forms per generator:
1. synthetic bars (seed 11), full 2200 vs truncated 2001;
2. real EURUSD DESIGN bars (6k slice), full 6000 vs truncated 4501.
"""

import numpy as np
import pytest
from fixtures import load_ctx, slice_bars, synthetic_bars

import registry
from common import ZoneContext


def _gen(name, ctx):
    return registry.get(name)(ctx)


def _pick_query_bars(gen, t_hi, want=3, step=25):
    """Newest `want` sampled bars (<= t_hi) at which the live book is non-empty."""
    hits = []
    for t in range(int(t_hi), 0, -step):
        if gen.views_at(t, arm=False):
            hits.append(t)
        if len(hits) >= want:
            break
    return sorted(hits)


def _assert_prefix_equal(name, bars, h1, t_trunc, want=3):
    ctx_full = ZoneContext(bars, h1)
    g_full = _gen(name, ctx_full).run()
    qbars = _pick_query_bars(g_full, t_trunc, want=want)
    assert qbars, f"{name}: no bar with a non-empty live book <= {t_trunc}"
    ctx_cut = ZoneContext(slice_bars(bars, t_trunc + 1),
                          slice_bars(h1, _h1_cut(h1, bars, t_trunc)))
    g_cut = _gen(name, ctx_cut).run()
    for t in qbars:
        live_full = g_full.live_dicts(t)
        live_cut = g_cut.live_dicts(t)
        assert live_full, (name, t)              # non-vacuous
        assert live_cut == live_full, (name, t)  # full causal state equality
        assert g_cut.zones_at(t) == g_full.zones_at(t), (name, t)
    return qbars


def _h1_cut(h1, bars, t):
    keep = int(bars["t"][t]) + 300
    return int(np.searchsorted(h1["t"] + 3600, keep, side="right"))


@pytest.mark.parametrize("name", registry.names())
def test_prefix_invariance_synthetic(name):
    m5, h1 = synthetic_bars(n=2200, seed=11)
    _assert_prefix_equal(name, m5, h1, t_trunc=2000)


@pytest.mark.parametrize("name", registry.names())
def test_prefix_invariance_real_eurusd(name):
    ctx = load_ctx(max_bars=6000)
    _assert_prefix_equal(name, ctx.bars, ctx.h1, t_trunc=4500)


@pytest.mark.parametrize("name", registry.names())
def test_interface_and_arming(name):
    ctx = load_ctx(max_bars=4000)
    g = _gen(name, ctx).run()
    t = 3999
    A = ctx.a(t)
    close = float(ctx.bars["c"][t])
    zs = g.zones_at(t)
    assert isinstance(zs, list)
    for z in zs:
        for key in ("lo", "hi", "kind", "strength", "born_idx", "touches", "fresh"):
            assert key in z, key
        assert z["lo"] <= z["hi"]
        assert z["born_idx"] <= t
        assert 0.0 <= z["strength"] <= 1.0
        assert abs(0.5 * (z["lo"] + z["hi"]) - close) <= 2.0 * A + 1e-9
    assert len(zs) <= 6


@pytest.mark.parametrize("name", registry.names())
def test_armed_excludes_broken(name):
    ctx = load_ctx(max_bars=8000)
    g = _gen(name, ctx).run()
    for t in (4000, 5500, 7999):
        armed_ids = {z.zid for z in g.views_at(t, arm=True)}
        for v in g.views_at(t, arm=False):
            if v.broken_idx is not None:
                assert v.zid not in armed_ids, (name, t, v.zid)
