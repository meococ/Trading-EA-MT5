"""Unit tests for common.py infrastructure (T-PAPRO-ZONE-1)."""

import math

import numpy as np
import pytest
from fixtures import synthetic_ctx, synthetic_bars

from common import (DEFAULTS, AtrH1, ZoneGen, ZoneContext, arm_zones,
                    confirmed_pivots, wilder_atr)


def test_wilder_atr_matches_hand_computation():
    h = np.array([1.0, 1.2, 1.1, 1.4, 1.3, 1.5, 1.6, 1.4, 1.7, 1.8,
                  1.6, 1.9, 2.0, 1.8, 2.1, 2.2])
    l = h - 0.5
    c = h - 0.2
    a = wilder_atr(h, l, c, 14)
    assert np.isnan(a[:13]).all()
    tr = np.maximum(h[1:] - l[1:], np.maximum(np.abs(h[1:] - c[:-1]),
                                              np.abs(l[1:] - c[:-1])))
    first = np.mean(np.concatenate([[h[0] - l[0]], tr[:13]]))
    assert a[13] == pytest.approx(first)
    assert a[14] == pytest.approx((13 * first + tr[13]) / 14.0)


def test_confirmed_pivots_are_lagged_and_exact():
    h = np.array([1, 2, 3, 5, 3, 2, 1, 2, 4, 6, 4, 2, 1], dtype=float)
    l = h - 1.0
    bars = {"h": h, "l": l}
    piv = confirmed_pivots(bars, k=2)
    assert (3, 5.0, +1, 5) in piv
    assert (9, 6.0, +1, 11) in piv
    for (_j, _p, _s, conf) in piv:
        assert conf == _j + 2


def test_atr_h1_alignment_uses_only_closed_buckets():
    m5, h1 = synthetic_bars(n=2400)
    ctx = ZoneContext(m5, h1)
    for t in (100, 700, 1500, 2399):
        idx = int(ctx.h1_idx[t])
        if idx >= 0:
            assert h1["t"][idx] + 3600 <= m5["t"][t] + 300


def test_zone_quality_history_is_causal():
    ctx = synthetic_ctx(n=600)
    g = ZoneGen(ctx)

    class G(ZoneGen):
        def _on_bar(self, t):
            if t == 100:
                self._z = self._new_zone("t", "micro", 90, 100,
                                         1.09, 1.10, quality=1.0)
            if t == 300:
                self._z.add_quality(t, 2.0)

    gen = G(ctx)
    gen.run()
    assert gen._z.quality_at(299) == 1.0
    assert gen._z.quality_at(300) == 2.0


def test_touch_response_break_state_machine():
    ctx = synthetic_ctx(n=800)
    A = 0.0010
    lo, hi = 1.1000, 1.10025        # 0.25 x A
    # hand-made price path on a copy of the synthetic bars
    b = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in ctx.bars.items()}
    n = len(b["t"])
    b["o"][:] = 1.0950
    b["h"][:] = 1.0951
    b["l"][:] = 1.0949
    b["c"][:] = 1.0950
    b["t"][:] = np.arange(n) * 300 + 1451606400
    b["utc_min"][:] = ((b["t"] % 86400) // 60).astype(np.int64)
    h1 = {"t": np.arange(n // 12 + 2) * 3600 + 1451606400,
          "h": np.full(n // 12 + 2, 1.1005), "l": np.full(n // 12 + 2, 1.0995),
          "c": np.full(n // 12 + 2, 1.1000)}
    ctx2 = ZoneContext(b, h1)
    assert ctx2.a(400) == pytest.approx(A, abs=1e-9)      # Wilder ATR(H1)
    gen2 = ZoneGen(ctx2)
    z = gen2._new_zone("t", "micro", 400, 400, lo, hi)
    assert z.end_idx >= 400
    # touch at 450 (range pierces the band), then close 1.0 x A below at 470
    b["h"][450] = 1.1001
    b["l"][450] = 1.0995
    b["c"][450] = 1.0999
    b["c"][470] = lo - 1.0 * A
    st = gen2.state_at(z, 480)
    assert st["touches"] == 1
    assert st["n_respected"] == 1
    # second touch at 600
    b["h"][600] = 1.1001
    b["l"][600] = 1.0995
    b["c"][600] = 1.0999
    st2 = gen2.state_at(z, 620)
    assert st2["touches"] == 2
    # close at 650 beyond the top edge by > 0.1 x A -> BREAK
    b["c"][650] = hi + 0.2 * A
    st3 = gen2.state_at(z, 650)
    assert st3["broken"] == 650
    # ... and a close back inside within 96 bars -> RECLAIM, not a flip
    b["c"][660] = 1.1001
    st4 = gen2.state_at(z, 660)
    assert st4["broken"] is None
    assert st4["n_reclaims"] == 1
    assert st4["role_flip"] == 0


def test_arm_rule_near_price_dedupe_cap():
    class V:
        def __init__(self, lo, hi, s):
            self.lo, self.hi, self.strength = lo, hi, s
            self.broken_idx = None

    A = 0.0010
    views = [V(1.1000, 1.10025, 0.9), V(1.1001, 1.10035, 0.8),
             V(1.1020, 1.10225, 0.7), V(1.0900, 1.09025, 0.6)]
    armed = arm_zones(views, close=1.1002, A=A, cfg=DEFAULTS)
    assert armed[0].strength == 0.9
    assert all(v.strength != 0.8 for v in armed)      # deduped by center
    assert all(abs(0.5 * (v.lo + v.hi) - 1.1002) <= 2 * A for v in armed)
    many = [V(1.0950 + i * 0.005, 1.09525 + i * 0.005, 0.9 - 0.01 * i)
            for i in range(10)]
    assert len(arm_zones(many, 1.1150, 0.01, DEFAULTS)) == DEFAULTS["arm_max"]


def test_h1_pivots_mapped_to_m5_are_causal():
    m5, h1 = synthetic_bars(n=2400)
    ctx = ZoneContext(m5, h1)
    piv = ctx.h1_pivots(2)
    n_m5 = len(m5["t"])
    assert piv, "synthetic data should carry H1 pivots"
    for (j, price, side, m5c, m5a) in piv:
        assert 0 <= m5c < n_m5
        assert h1["t"][j] + 3600 <= m5["t"][m5c] + 300          # known in time
        assert m5["t"][m5a] >= h1["t"][j]                       # anchor >= bucket
        assert price == (h1["h"][j] if side > 0 else h1["l"][j])
        assert m5["t"][m5c] + 300 == h1["t"][j + 2] + 3600      # confirm at close


def test_strength_weights_sum_to_one():
    tot = (DEFAULTS["w_touch"] + DEFAULTS["w_resp"] + DEFAULTS["w_rec"]
           + DEFAULTS["w_age"] + DEFAULTS["w_scale"] + DEFAULTS["w_role"]
           + DEFAULTS["w_ref"] + DEFAULTS["w_qual"])
    assert tot == pytest.approx(1.0)


def test_replay_is_side_effect_free():
    ctx = synthetic_ctx(n=900)
    from line1_cluster_zones import Line1ClusterZones
    g = Line1ClusterZones(ctx).run()
    counters_before = dict(g.counters)
    t = 800
    a = g.zones_at(t)
    b = g.zones_at(t)
    assert a == b
    assert dict(g.counters) == counters_before
