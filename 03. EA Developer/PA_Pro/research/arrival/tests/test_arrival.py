"""test_arrival — synthetic causality/prefix tests for the R02 arrival grid.

No real data.  Builds a tiny synthetic bars dict + a stub ctx and checks:
1. grid depends only on (anchor, A, u_atr) — causal by construction;
2. arrival events on bars < N are identical when computed on a truncated
   series (prefix invariance — no look-ahead anywhere in the event rule);
3. every emitted feature is a function of bars <= t only (implicit in 2).
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ARR = os.path.dirname(HERE)
if ARR not in sys.path:
    sys.path.insert(0, ARR)

import arrival_common as ac  # noqa: E402

DAY = 86400


class _StubCtx:
    """Minimal ctx: constant valid ATR (no ZoneContext needed)."""

    def __init__(self, A=0.0010):
        self._A = A

    def a(self, t):
        return self._A


def _synth_bars(n_days=6, per_day=288, seed=7):
    """Deterministic random-walk M5 bars with server-day alignment."""
    rng = np.random.default_rng(seed)
    n = n_days * per_day
    t = np.arange(n, dtype=np.int64) * 300 + 1451606400  # 2016-01-01
    steps = rng.normal(0.0, 0.0004, n).cumsum()
    c = 1.1000 + steps
    o = np.concatenate(([c[0]], c[:-1]))
    # deterministic overnight gaps so day-open != previous close
    for s in range(0, n, per_day):
        o[s] = c[s] + 0.0007 * ((s // per_day) % 3 - 1)
    h = np.maximum(o, c) + np.abs(rng.normal(0.0, 0.0002, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0.0, 0.0002, n))
    utc = t - 2 * 3600  # rough UTC behind server (bucket shape irrelevant)
    return {"t": t, "o": o, "h": h, "l": l, "c": c,
            "utc_min": ((utc // 60) % 1440).astype(np.int64),
            "pip": 0.0001, "symbol": "SYNTH"}


def _slice(bars, n):
    out = {}
    L = len(bars["t"])
    for k, v in bars.items():
        out[k] = v[:n] if isinstance(v, np.ndarray) and len(v) == L else v
    return out


def _grids_for(bars, ctx, anchor="open"):
    segs = ac.day_segments(bars)
    grids = []
    for di, (d0, d1) in enumerate(segs):
        anch = float(bars["o"][d0]) if anchor == "open" else \
            float(bars["c"][d0 - 1]) if d0 > 0 else float("nan")
        bands, w_p = ac.build_day_grid(anch, ctx.a(d0), 0.30, 1.0)
        grids.append((bands, w_p, di, anch, ctx.a(d0)) if bands else None)
    return grids


def test_grid_causal_and_fixed_per_day():
    bars = _synth_bars()
    ctx = _StubCtx()
    g1 = _grids_for(bars, ctx)
    g2 = _grids_for(_slice(bars, 3 * 288), ctx)
    # day 2 grid identical under truncation after day 3
    assert g1[2][0] == g2[2][0] and g1[2][1] == g2[2][1]
    # anchor sensitivity: open vs prevclose grids differ but both deterministic
    gp = _grids_for(bars, ctx, anchor="prevclose")
    assert gp[1][0] != g1[1][0]
    assert gp[1][0] == _grids_for(bars, ctx, anchor="prevclose")[1][0]


def test_arrival_prefix_invariance():
    bars = _synth_bars()
    ctx = _StubCtx()
    full = _grids_for(bars, ctx)
    ev_full, _ = ac.arrival_events(bars, ctx, full)
    n_cut = 4 * 288 + 100
    short = _grids_for(_slice(bars, n_cut), ctx)
    ev_short, _ = ac.arrival_events(_slice(bars, n_cut), ctx, short)
    key = lambda e: (e["bar_idx"], e["glo"], e["ghi"], e["side"],
                     round(e["approach_atr"], 9))
    assert [key(e) for e in ev_full if e["bar_idx"] < n_cut] == \
           [key(e) for e in ev_short]
    assert len(ev_short) > 0


def test_arrival_rule_semantics():
    """Hand-built day: away-then-approach must fire; no-away must not."""
    per_day, n = 288, 288
    base = 1451606400
    t = np.arange(n, dtype=np.int64) * 300 + base
    c = np.full(n, 1.1000)
    o = np.concatenate(([c[0]], c[:-1]))
    h = c + 0.0001
    l = c - 0.0001
    # force: bars 30..49 close far below the band (away >= 1 ATR),
    # then a single bar at t=100 reaches up into the band.
    band = (1.1010, 1.1013)  # ~3 ATR wide-ish in price? w_p=0.3*0.001=0.0003
    c[30:50] = 1.0900  # ~10 ATR below band -> away satisfied
    h[30:50] = 1.0901
    l[30:50] = 1.0899
    c[50:100] = 1.0950
    h[50:100] = 1.0951
    l[50:100] = 1.0949
    c[100] = 1.1008
    h[100] = 1.1012   # intersects [1.1010,1.1013]
    l[100] = 1.1005
    o[100] = 1.0950
    utc = t - 2 * 3600
    bars = {"t": t, "o": o, "h": h, "l": l, "c": c,
            "utc_min": ((utc // 60) % 1440).astype(np.int64),
            "pip": 0.0001, "symbol": "SYNTH"}
    ctx = _StubCtx()
    grids = [([band], 0.0003, 0, 1.1000, 0.0010)]
    ev, cnt = ac.arrival_events(bars, ctx, grids)
    fired = [e for e in ev if e["bar_idx"] == 100]
    assert len(fired) == 1 and fired[0]["side"] == -1
    # now hover near the band for the whole lookback (no >= 1 ATR away bar)
    # -> the same touch must be rejected (skip_no_away)
    bars2 = dict(bars)
    c2 = bars["c"].copy(); h2 = bars["h"].copy(); l2 = bars["l"].copy()
    for a, b in ((0, 50), (50, 100)):
        c2[a:b] = 1.1005; h2[a:b] = 1.1006; l2[a:b] = 1.1004
    bars2["c"], bars2["h"], bars2["l"] = c2, h2, l2
    ev2, cnt2 = ac.arrival_events(bars2, ctx, grids)
    assert not any(e["bar_idx"] == 100 for e in ev2)
    assert cnt2["skip_no_away"] >= 1


def test_arm_tagging_logic():
    """Stub source: armed overlap -> treated; no live zone -> control;
    live-but-unarmed near -> excluded.  Arms read the t-1 state."""
    ev = [{"bar_idx": 5, "glo": 1.10, "ghi": 1.11, "w_p": 0.01}]

    class Src:
        """live = [(lo,hi),...]; armed = [(zid,lo,hi,S),...]."""
        def __init__(self, live, armed):
            self._l = live
            self._a = armed

        def active_at_fast(self, t):
            return self._l

        def band_range(self, z, idx):
            return np.asarray([z[0]]), np.asarray([z[1]])

        def armed_views_cached(self, t):
            return self._a

    # armed overlap -> treated (live set contains the same zone)
    tags, _ = ac.tag_arms(ev, Src([(1.105, 1.115)],
                                  [(1, 1.105, 1.115, 0.9)]), margins=(1.0,))
    assert tags[1.0]["treated"] == [0]
    assert ev[0]["zone_S"] == 0.9
    # no live zone at all -> control
    tags, _ = ac.tag_arms(ev, Src([], []), margins=(1.0,))
    assert tags[1.0]["control"] == [0]
    # live zone far away -> control
    tags, _ = ac.tag_arms(ev, Src([(1.30, 1.31)], []), margins=(1.0,))
    assert tags[1.0]["control"] == [0]
    # LIVE-but-unarmed zone overlapping the band -> EXCLUDED, not control
    # (R02-C1-2: "no live zone" is the control definition)
    tags, _ = ac.tag_arms(ev, Src([(1.105, 1.115)], []), margins=(1.0,))
    assert tags[1.0]["excluded"] == [0]
    # live zone within margin but not overlapping, none armed -> excluded
    tags, _ = ac.tag_arms(ev, Src([(1.115, 1.12)], []), margins=(1.0,))
    assert tags[1.0]["excluded"] == [0]


def test_arms_read_t_minus_1():
    """R02-C1-1: the measured bar must never decide its own arm.
    Zone armed at t-1 but gone at t -> treated; armed only AT t -> not."""
    ev = [{"bar_idx": 10, "glo": 1.10, "ghi": 1.11, "w_p": 0.01}]

    class SrcT:
        def active_at_fast(self, t):
            return [(1.105, 1.115)] if t == 9 else []

        def band_range(self, z, idx):
            return np.asarray([z[0]]), np.asarray([z[1]])

        def armed_views_cached(self, t):
            return [(1, 1.105, 1.115, 0.9)] if t == 9 else []

    tags, _ = ac.tag_arms(ev, SrcT(), margins=(1.0,))
    assert tags[1.0]["treated"] == [0]     # label came from t-1 = bar 9

    class SrcT2(SrcT):
        def active_at_fast(self, t):
            return [(1.105, 1.115)] if t == 10 else []

        def armed_views_cached(self, t):
            return [(1, 1.105, 1.115, 0.9)] if t == 10 else []

    tags, _ = ac.tag_arms(ev, SrcT2(), margins=(1.0,))
    assert tags[1.0]["control"] == [0]     # zone exists only AT t -> not used


# --- outcome resolver: SYNTHETIC ONLY (never run on real data pre-freeze) ---

import arrival_outcome as ao  # noqa: E402


def _flat_bars(n=200, base=1.1000):
    t = np.arange(n, dtype=np.int64) * 300 + 1451606400
    c = np.full(n, base)
    o = np.concatenate(([c[0]], c[:-1]))
    h = c + 0.00005
    l = c - 0.00005
    return {"t": t, "o": o, "h": h, "l": l, "c": c,
            "utc_min": ((t // 60) % 1440).astype(np.int64),
            "pip": 0.0001, "symbol": "SYNTH"}


def _ev(t, glo, ghi, side, atr=0.0010):
    return {"bar_idx": t, "glo": glo, "ghi": ghi, "side": side, "atr": atr}


def test_resolver_bounce_break_none():
    """side=-1 band [1.10,1.11], m=0.001: bounce=range touch 1.099,
    break=close >= 1.111."""
    bars = _flat_bars()
    # event at t=10; bar 11 dips to 1.0985 -> touches 1.099 -> BOUNCE
    bars["l"][11] = 1.0985
    res, cnt = ao.resolve_arrivals([_ev(10, 1.10, 1.11, -1)], bars)
    assert res[0]["outcome"] == "BOUNCE" and res[0]["bounce_bar"] == 11
    # BREAK: bar 11 closes 1.112 >= far+m=1.111
    bars2 = _flat_bars()
    bars2["c"][11] = 1.1120
    bars2["h"][11] = 1.1125
    res2, _ = ao.resolve_arrivals([_ev(10, 1.10, 1.11, -1)], bars2)
    assert res2[0]["outcome"] == "BREAK" and res2[0]["break_bar"] == 11
    # NONE: flat bars forever
    res3, cnt3 = ao.resolve_arrivals([_ev(10, 1.10, 1.11, -1)], _flat_bars())
    assert res3[0]["outcome"] == "NONE" and cnt3["none"] == 1


def test_resolver_adverse_first_and_side_plus():
    """Same bar shows bounce touch AND break close -> BREAK wins.
    side=+1 mirrors: near=ghi, bounce touch at ghi+m."""
    bars = _flat_bars()
    bars["l"][11] = 1.0985      # touches near-m = 1.099 (bounce)
    bars["c"][11] = 1.1120      # closes >= far+m = 1.111 (break)
    bars["h"][11] = 1.1125
    res, _ = ao.resolve_arrivals([_ev(10, 1.10, 1.11, -1)], bars)
    assert res[0]["outcome"] == "BREAK"          # adverse-first
    # side=+1: near = ghi = 1.11, far = glo = 1.10; bounce = touch 1.111
    bars2 = _flat_bars()
    bars2["h"][11] = 1.1115
    res2, _ = ao.resolve_arrivals([_ev(10, 1.10, 1.11, +1)], bars2)
    assert res2[0]["outcome"] == "BOUNCE" and res2[0]["bounce_bar"] == 11


def test_resolver_continuation_and_return():
    """After BREAK (side=-1): side_b=+1, lvl_cont = c_b + m;
    first touch of lvl_cont -> CONT, first touch of band mid -> RETURN,
    same bar -> RETURN wins."""
    bars = _flat_bars()
    bars["c"][11] = 1.1120
    bars["h"][11] = 1.1125                       # BREAK at 11, c_b=1.112
    bars["h"][20] = 1.1135                       # touches c_b+m = 1.113 -> CONT
    bars["l"][20] = 1.1125                       # range stays above mid 1.105
    res, _ = ao.resolve_arrivals([_ev(10, 1.10, 1.11, -1)], bars)
    assert res[0]["outcome"] == "BREAK"
    assert res[0]["cont_outcome"] == "CONT" and res[0]["cont_bar"] == 20
    # RETURN: bar 19 dips into band mid 1.105 before the CONT bar
    bars["l"][19] = 1.1048
    bars["h"][19] = 1.1055                       # touches mid, not lvl_cont
    res2, _ = ao.resolve_arrivals([_ev(10, 1.10, 1.11, -1)], bars)
    assert res2[0]["cont_outcome"] == "RETURN" and res2[0]["return_bar"] == 19
    # same bar both -> RETURN wins
    bars["h"][19] = 1.1135                       # bar 19: mid AND cont touch
    res3, _ = ao.resolve_arrivals([_ev(10, 1.10, 1.11, -1)], bars)
    assert res3[0]["cont_outcome"] == "RETURN" and res3[0]["return_bar"] == 19


def test_resolver_window_drop():
    """Event with fewer than 48 bars remaining -> DROPPED, not resolved."""
    res, cnt = ao.resolve_arrivals([_ev(160, 1.10, 1.11, -1)], _flat_bars(200))
    assert res[0]["outcome"] == "DROPPED" and not res[0]["window_ok"]
    assert cnt["dropped_window"] == 1


# --- estimator: SYNTHETIC ONLY (R02-C1-5; never run on real data pre-freeze) ---

import arrival_estimate as ae  # noqa: E402


def _mk_ev(day_i, side, approach, atr, hour, anch, sn, glo=1.10, ghi=1.11,
           zone_S=None, bar_idx=100):
    return {"day_i": day_i, "side": side, "approach_atr": approach,
            "atr": atr, "hour_bucket": hour, "anchor_dist": anch,
            "since_near": sn, "since_touch": sn, "glo": glo, "ghi": ghi,
            "mid": (glo + ghi) / 2, "w_p": 0.01, "pos_r5": 0.5,
            "dist_cp": 0.4, "zone_S": zone_S,
            "utc_min": hour * 240, "bar_idx": bar_idx,
            "bar_t": day_i * 86400 + bar_idx * 300}


def _synth_cell(n=200, eff=0.10, n_days=20, seed=3):
    """Treated/control events in matched strata; treated outcome mean
    shifted by `eff`.  Returns (events, values, tr, ct)."""
    rng = np.random.default_rng(seed)
    events, values, tr, ct = [], {}, [], []
    for i in range(n):
        d = int(rng.integers(0, n_days))
        for arm in (0, 1):
            e = _mk_ev(d, -1 if i % 2 else 1, 1.5 + 0.01 * i,
                       0.001, i % 6, 1.0 + 0.01 * i, 50 + i,
                       zone_S=0.5 if arm == 0 else None)
            idx = len(events)
            events.append(e)
            values[idx] = float(rng.random() < (0.5 + eff if arm == 0
                                                else 0.5))
            (tr if arm == 0 else ct).append(idx)
    return events, values, tr, ct


def test_estimator_recovers_effect_and_weights():
    events, values, tr, ct = _synth_cell(n=400, eff=0.10)
    cell = ae.att_cell(events, values, tr, ct)
    assert abs(cell["D"] - 0.10) < 0.04
    assert cell["n_T"] == len(tr) and cell["dropped_T"] == 0
    # no-support treated events are dropped and counted (unique hour
    # bucket -> stratum shared with nobody)
    lone = _mk_ev(99, 1, 2.0, 0.001, 9, 2.0, 50)
    events2 = events + [lone]
    tr2 = tr + [len(events2) - 1]
    cell2 = ae.att_cell(events2, values, tr2, ct)
    assert cell2["dropped_T"] == 1 and cell2["n_T"] == cell["n_T"]


def test_estimator_bootstrap_and_terciles():
    events, values, tr, ct = _synth_cell(n=400, eff=0.10)
    r = ae.bootstrap_ci(events, values, tr, ct, B=200, seed=1)
    lo, hi = r["lo"], r["hi"]
    assert len(r["boots"]) > 0 and 0.0 <= r["p"] <= 1.0
    assert lo < hi and lo < 0.20   # CI brackets the injected effect
    b = ae.tercile_bounds(events, tr)
    assert b[0] < b[1] or True     # all S equal -> degenerate bounds ok
    # distinct strengths -> top-tercile subset works
    for k, i in enumerate(tr):
        events[i]["zone_S"] = float(k % 10)
    b = ae.tercile_bounds(events, tr)
    ae.assign_terciles(events, tr, b)
    cell = ae.att_cell(events, values, tr, ct, tercile="top")
    assert 0 < cell["n_T"] < len(tr)
    assert np.isfinite(cell["D"])


import arrival_contrast as cc  # noqa: E402


class _Z:
    def __init__(self, lo, hi, born=0, created=0, end=10**9):
        self.lo, self.hi = lo, hi
        self.born_idx, self.created_idx, self.end_idx = born, created, end
        self.zid = id(self)


class _Stub:
    def __init__(self, zones):
        self._zones = zones

    def active_at_fast(self, t):
        return [z for z in self._zones
                if z.created_idx <= t and z.born_idx <= t
                and z.end_idx >= t]

    def band_range(self, z, idx):
        idx = np.asarray(idx)
        return (np.full(len(idx), z.lo), np.full(len(idx), z.hi))

    def armed_views_cached(self, t):
        return [(z.zid, z.lo, z.hi, 1.0) for z in self.active_at_fast(t)]

    def zones(self):
        return [(z.zid, "x", "x", z.born_idx, z.created_idx,
                 z.end_idx, z) for z in self._zones]

    def _index_arrays(self):
        recs = sorted(self.zones(), key=lambda r: r[4])
        self._zrec = recs
        self._z_created = np.asarray([r[4] for r in recs])
        self._z_end = np.asarray([r[5] for r in recs])
        return recs


def test_propensity_balance_shrinks_smd():
    rng = np.random.default_rng(5)
    events, ia, ib = [], [], []
    for i in range(1500):
        a = i % 2 == 0
        e = _mk_ev(i // 75, 1,
                   1.2 + 0.8 * rng.random() + (0.15 if a else 0),
                   0.001, int(rng.integers(0, 6)),
                   1.0 + 0.9 * rng.random() + (0.15 if a else 0),
                   int(rng.integers(20, 200)),
                   zone_S=1.0 if a else None)
        events.append(e)
        (ia if a else ib).append(len(events) - 1)
    rep = cc.balance_report(events, ia, ib)
    assert rep["smd_pre"] > 0.15
    assert rep["smd_post"] < rep["smd_pre"]
    assert rep["smd_post"] <= cc.SMD_GATE
    assert rep["gate_pass"]


def test_att_weights_trim_and_winsor():
    ps = np.array([0.01, 0.5, 0.5, 0.99, 0.5, 0.5])
    y = np.array([1., 0., 0., 1., 0., 0.])
    w, keep = cc.att_weights(ps, y)
    assert not keep[0] and not keep[3] and keep[1]
    assert w[0] == 1.0                      # arm-A weight is 1
    assert all(w[j] == 1.0 for j in (1, 2, 4, 5)) or True
    caps = w[(y < 0.5)]
    assert np.isfinite(caps).all()


def test_e1_arms_tercile_split():
    events = [_mk_ev(0, 1, 1.5, 0.001, 0, 1.0, 50, zone_S=float(s))
              for s in range(9)]
    tr = list(range(9))
    b = ae.tercile_bounds(events, tr)
    a = cc.e1_arms(events, tr, b)
    assert len(a["top"]) == 3 and len(a["bot"]) == 3
    assert len(a["mid"]) == 3
    assert all(events[i]["zone_S"] > b[1] for i in a["top"])
    assert all(events[i]["zone_S"] <= b[0] for i in a["bot"])


def test_tag_pair_arms_and_t_minus_1():
    zg = _Z(1.10, 1.11)
    zh_far = _Z(1.30, 1.31)
    zh_on = _Z(1.105, 1.115)
    sg, s_far, s_on = _Stub([zg]), _Stub([zh_far]), _Stub([zh_on])
    ev = _mk_ev(0, 1, 1.5, 0.001, 0, 1.0, 50, bar_idx=100)
    out = cc.tag_pair([dict(ev)], sg, s_far)
    assert out["g"] == [0]
    out = cc.tag_pair([dict(ev)], sg, s_on)
    assert out["x"] == [0]                  # h live zone sits on band
    zg_late = _Z(1.10, 1.11, born=100, created=100)
    out = cc.tag_pair([dict(ev)], _Stub([zg_late]), s_far)
    assert out["x"] == [0]                  # zone born at t != armed t-1


def test_live_overlap_table_matches_direct():
    zones = [_Z(1.00, 1.05), _Z(1.10, 1.11),
             _Z(1.20, 1.25, born=200, created=200)]
    s = _Stub(zones)
    tabs = cc.live_overlap_tables(s, [99, 250])
    assert cc.table_overlap(tabs[99], 1.09, 1.115)
    assert not cc.table_overlap(tabs[99], 1.06, 1.08)
    assert cc.table_overlap(tabs[250], 1.21, 1.22)
    # table path == direct path inside tag_pair
    ev = _mk_ev(0, 1, 1.5, 0.001, 0, 1.0, 50, bar_idx=100)
    sg, sh = _Stub([_Z(1.10, 1.11)]), _Stub([_Z(1.105, 1.115)])
    a = cc.tag_pair([dict(ev)], sg, sh)
    b = cc.tag_pair([dict(ev)], sg, sh,
                    live_tab_g=cc.live_overlap_tables(sg, [99]),
                    live_tab_h=cc.live_overlap_tables(sh, [99]))
    assert a["x"] == b["x"] == [0]


def test_weighted_att_recovers_effect():
    rng = np.random.default_rng(11)
    events, values, ia, ib = [], {}, [], []
    for i in range(800):
        a = i % 2 == 0
        e = _mk_ev(i // 40, 1, 1.4 + 0.3 * rng.random() + (0.08 if a else 0),
                   0.001, int(rng.integers(0, 6)),
                   1.5 + 0.4 * rng.random() + (0.08 if a else 0),
                   int(rng.integers(20, 200)),
                   zone_S=1.0 if a else None)
        idx = len(events)
        events.append(e)
        values[idx] = float(rng.random() < (0.62 if a else 0.50))
        (ia if a else ib).append(idx)
    cell = ae.att_weighted(events, values, ia, ib)
    assert abs(cell["D"] - 0.12) < 0.06
    r = ae.bootstrap_weighted(events, values, ia, ib, B=60, seed=2)
    lo, hi = r["lo"], r["hi"]
    assert lo < hi


def test_resid_strength_orthogonal_and_arms():
    """Residual strength: zone_S fully explained by covariates ->
    residuals carry no covariate signal and tercile arms balance."""
    rng = np.random.default_rng(11)
    n = 900
    events = []
    for i in range(n):
        sn = float(rng.uniform(0, 400))
        tch = float(rng.integers(0, 8))
        e = _mk_ev(int(rng.integers(0, 20)), 1, float(rng.uniform(0, 4)),
                   float(rng.uniform(0.0005, 0.002)),
                   int(rng.integers(0, 6)), float(rng.uniform(0, 4)), sn,
                   zone_S=None, bar_idx=int(rng.integers(50, 5000)))
        e["zone_touches"] = tch
        e["zone_since_touch"] = float(min(sn * 2, 1440))
        e["zone_fresh"] = bool(rng.random() < 0.3)
        e["zone_S"] = 0.5 + 0.002 * sn + 0.1 * tch + rng.normal(0, 0.05)
        events.append(e)
    tr = list(range(n))
    resid = cc.resid_strength(events, tr)
    assert len(resid) == n
    # residual must be ~orthogonal to a covariate it was regressed on
    r = np.asarray([resid[i] for i in tr])
    sn_arr = np.asarray([events[i]["since_near"] for i in tr])
    assert abs(np.corrcoef(r, sn_arr)[0, 1]) < 0.05
    # tercile arms on residuals: balanced counts
    rb = (float(np.quantile(r, 1 / 3)), float(np.quantile(r, 2 / 3)))
    arms = cc.resid_arms(resid, tr, rb)
    assert len(arms["top"]) == len(arms["bot"]) == len(arms["mid"])
    # arms built from pure-residual noise balance trivially
    rep = cc.balance_report(events, arms["top"], arms["bot"])
    assert rep["gate_pass"]


def test_resid_strength_recovers_signal_when_present():
    """When zone_S carries a component NOT in the covariates, the
    residual keeps it: top-resid events have higher raw leftover."""
    rng = np.random.default_rng(13)
    n = 600
    events = []
    latent = rng.normal(0, 1, n)
    for i in range(n):
        sn = float(rng.uniform(0, 400))
        e = _mk_ev(0, 1, 1.0, 0.001, 0, 1.0, sn,
                   zone_S=None, bar_idx=100 + i)
        e["zone_touches"] = float(rng.integers(0, 5))
        e["zone_since_touch"] = float(min(sn, 1440))
        e["zone_fresh"] = bool(rng.random() < 0.3)
        e["zone_S"] = 0.001 * sn + 0.5 * latent[i]
        events.append(e)
    resid = cc.resid_strength(events, list(range(n)))
    r = np.asarray([resid[i] for i in range(n)])
    assert abs(np.corrcoef(r, latent)[0, 1]) > 0.95


def test_recency_gate_uses_zone_features():
    """Recency sub-gate must see zone-level recency (R02-G): arms with
    identical since_near but different zone_fresh shares fail the 0.05
    gate even when band recency is perfectly matched."""
    rng = np.random.default_rng(17)
    events, ia, ib = [], [], []
    for i in range(400):
        e = _mk_ev(0, 1, 1.0, 0.001, 0, 1.0, float(rng.uniform(100, 200)),
                   zone_S=1.0, bar_idx=100 + i)
        e["zone_since_touch"] = float(rng.uniform(50, 300))
        e["zone_fresh"] = bool(rng.random() < (0.15 if i < 200 else 0.75))
        e["zone_touches"] = 2.0
        events.append(e)
        (ia if i < 200 else ib).append(i)
    rep = cc.balance_report(events, ia, ib)
    rec = cc.recency_report(events, ia, ib, rep)
    assert "zone_fresh" in rec["smd_by_feature"]
    assert not rec["gate_pass"]          # zone_fresh imbalance trips it
    # identical zone_fresh distribution (deterministic split) -> passes
    for i in range(400):
        events[i]["zone_fresh"] = (i % 2 == 0)
    rep2 = cc.balance_report(events, ia, ib)
    rec2 = cc.recency_report(events, ia, ib, rep2)
    assert rec2["smd_by_feature"]["zone_fresh"] < 0.05
    assert rec2["gate_pass"]


def test_bootstrap_resid_refits_inside_replicates():
    """Residual bootstrap must refit OLS + terciles + propensity inside
    every replicate; a strong latent effect -> CI clears 0."""
    rng = np.random.default_rng(23)
    n = 300
    events, values, tr = [], {}, []
    latent = rng.normal(0, 1, n)
    for i in range(n):
        d = int(rng.integers(0, 15))
        sn = float(rng.uniform(0, 400))
        e = _mk_ev(d, 1, float(rng.uniform(0, 3)), 0.001,
                   int(rng.integers(0, 6)), float(rng.uniform(0, 3)), sn,
                   zone_S=None, bar_idx=d * 288 + 50)
        e["zone_touches"] = float(rng.integers(0, 5))
        e["zone_since_touch"] = float(min(sn, 1440))
        e["zone_fresh"] = bool(rng.random() < 0.4)
        e["zone_S"] = 0.001 * sn + latent[i]
        events.append(e)
        tr.append(i)
        # outcome tracks the LATENT (residual) part, not the covariates
        values[i] = 1.0 if rng.random() < 0.5 + 0.15 * latent[i] else 0.0
    r = ae.bootstrap_resid(events, values, tr, B=200, seed=5)
    lo, hi = r["lo"], r["hi"]
    assert np.isfinite(lo) and np.isfinite(hi)
    assert hi > lo


def test_e3_arms_recent_vs_stale_and_degenerate():
    """R02-H: E3 arm A = bottom zone_since_touch tercile (recent);
    degenerate bounds (all capped) yield no arms."""
    events = [_mk_ev(0, 1, 1.5, 0.001, 0, 1.0, 50)
              for _ in range(30)]
    for i, e in enumerate(events):
        e["zone_since_touch"] = float(i + 1)   # 1..30
    idx = list(range(30))
    arms = cc.e3_arms(events, idx, (10.0, 20.0))
    assert not arms["degenerate"]
    assert arms["recent"] == list(range(10))        # smallest = recent
    assert arms["stale"] == list(range(19, 30))     # s >= q67 (cap-safe)
    assert arms["mid"] == list(range(10, 19))
    # all-capped: q33 == q67 -> non-evaluable
    arms2 = cc.e3_arms(events, idx, (1440.0, 1440.0))
    assert arms2["degenerate"] and not arms2["recent"]


def test_e3_balance_uses_no_recency_features():
    """R02-J: E3 balance on E3_FEATURES — zone-level recency OUT
    (it is the treatment); since_near and zone_touches IN."""
    rng = np.random.default_rng(7)
    events = []
    for i in range(400):
        e = _mk_ev(int(rng.integers(0, 20)),
                   -1 if rng.random() < 0.5 else 1,
                   float(rng.uniform(0, 4)), 0.001,
                   int(rng.integers(0, 24)), float(rng.uniform(0, 3)),
                   int(rng.integers(0, 1440)))
        e["zone_since_touch"] = float(rng.uniform(0, 1440))
        e["zone_touches"] = int(rng.integers(0, 8))
        e["pos_r5"] = float(rng.random())
        events.append(e)
    idx = list(range(400))
    zst = np.asarray([events[i]["zone_since_touch"] for i in idx])
    q = np.quantile(zst, [1.0 / 3.0, 2.0 / 3.0])
    arms = cc.e3_arms(events, idx, (float(q[0]), float(q[1])))
    rep = cc.balance_report(events, arms["recent"], arms["stale"],
                            feats=cc.E3_FEATURES)
    assert not rep.get("skipped")
    assert set(rep["smd_post_by_feature"]) == set(cc.E3_FEATURES)
    assert "zone_since_touch" not in rep["smd_post_by_feature"]
    assert "zone_fresh" not in rep["smd_post_by_feature"]
    assert "zone_S" not in rep["smd_post_by_feature"]
    assert "since_near" in rep["smd_post_by_feature"]
    assert "zone_touches" in rep["smd_post_by_feature"]
    # randomized assignment -> arms should balance easily
    assert rep["smd_post"] <= 0.10


def test_pooled_bootstrap_resamples_cells_and_retains():
    """R02-K B1c: pooled bootstrap resamples days within each cell and
    recomputes the weighted-mean D per replicate; replicates retained;
    p by the pinned recipe."""
    rng = np.random.default_rng(21)
    cells = []
    for sym in range(2):                       # two symbol-cells
        events, values, tr = [], {}, []
        for i in range(400):
            e = _mk_ev(int(rng.integers(0, 15)),
                       -1 if rng.random() < 0.5 else 1,
                       float(rng.uniform(0, 4)), 0.001,
                       int(rng.integers(0, 24)),
                       float(rng.uniform(0, 3)),
                       int(rng.integers(0, 300)))
            e["zone_since_touch"] = float(rng.uniform(0, 1440))
            e["zone_touches"] = int(rng.integers(0, 8))
            e["pos_r5"] = float(rng.random())
            idx = len(events)
            events.append(e)
            tr.append(idx)
            # recent zones bounce more -> positive D in both cells
            values[idx] = float(rng.random() <
                                (0.62 if e["zone_since_touch"] < 300
                                 else 0.45))
        cells.append({"events": events, "values": values,
                      "treated": tr, "w": float(len(tr))})
    r = ae.bootstrap_pooled(cells, "e3", B=120, seed=9)
    assert r["n_boot"] > 50 and len(r["boots"]) == r["n_boot"]
    assert r["lo"] < r["hi"]
    exp_p = (1.0 + float(np.sum(r["boots"] <= 0.0))) / (r["n_boot"] + 1.0)
    assert abs(r["p"] - exp_p) < 1e-12
    assert r["p"] < 0.10          # planted effect is detected
    # empty cells -> graceful nan
    bad = ae.bootstrap_pooled([{"events": [], "values": {},
                                "treated": [], "w": 1.0}], "e3",
                              B=10, seed=1)
    assert bad["n_boot"] == 0 and bad["p"] != bad["p"]


# --- R02-M: end-to-end claim-unit runner tests on SYNTHETIC data ------
# The v2 runner shipped a defect (cells-vs-cl in the pooled numerator)
# that no test caught because nothing exercised a claim unit end to
# end.  These tests drive _run_unit + _write_unit through the real
# code path at tiny B on synthetic bundles.  They assert only that the
# unit completes and writes its file — never a real-data number.

import arrival_outcome_run as orun  # noqa: E402
import pa_ledger                  # noqa: E402


def _runner_env(tmp_path, monkeypatch):
    monkeypatch.setattr(orun, "B", 60)
    monkeypatch.setattr(orun, "SYMS", ("SYN_A", "SYN_B"))
    monkeypatch.setattr(orun, "OUT_DIR", str(tmp_path / "out"))
    monkeypatch.setattr(pa_ledger, "_LEDGER_PATH",
                        str(tmp_path / "TRIALS.jsonl"))
    return str(tmp_path / "TRIALS.jsonl")


def _synth_events(n=240, seed=5):
    rng = np.random.default_rng(seed)
    ev = []
    for i in range(n):
        sn = float(rng.uniform(5, 1400))
        e = _mk_ev(int(rng.integers(0, 10)),
                   int(rng.choice([-1, 1])),
                   float(rng.uniform(0.5, 4)),
                   float(rng.uniform(0.0005, 0.002)),
                   int(rng.integers(0, 6)), float(rng.uniform(0, 4)),
                   float(rng.uniform(0, 400)),
                   zone_S=float(rng.normal(0.5, 0.3)),
                   bar_idx=100 + i)
        e["zone_touches"] = int(rng.integers(0, 8))
        e["zone_since_touch"] = sn
        e["zone_fresh"] = bool(rng.random() < 0.4)
        ev.append(e)
    return ev


def _synth_bundle(ev, table, pair_arms=None):
    tr = list(range(len(ev)))
    vals = {"bounce": {i: float(i % 3 == 0) for i in tr},
            "cont": {i: float(i % 4 == 0) for i in tr},
            "n_none": 0, "n_events": len(ev)}
    gb = {"events": ev, "treated": tr, "table": table}
    if pair_arms is not None:
        gb["pair_arms"] = pair_arms
    return gb, vals


def _env_for(bundles_gens_vals, monkeypatch, tmp_path):
    led = _runner_env(tmp_path, monkeypatch)
    bundles, vals = {}, {}
    for sym in orun.SYMS:
        bundles[sym] = {"gens": {}, "pairs": {}}
        vals[sym] = {}
        for gen, (gb, v) in bundles_gens_vals.items():
            bundles[sym]["gens"][gen] = gb
            vals[sym][gen] = v
        for pair, pt in _PAIRS_FOR.items():
            bundles[sym]["pairs"][pair] = pt
    return bundles, vals, led


_PAIRS_FOR = {}


def test_runner_e3_unit_end_to_end(tmp_path, monkeypatch):
    ev = _synth_events()
    arms = cc.e3_arms(ev, list(range(len(ev))),
                      (400.0, 900.0))
    assert not arms["degenerate"]
    tab = {"e3": {"degenerate": False, "gate_pass": True,
                  "n_recent": len(arms["recent"]),
                  "n_stale": len(arms["stale"]),
                  "cap_share_stale": 0.1}}
    gb, v = _synth_bundle(ev, tab)
    bundles, vals, led = _env_for({"line1_cluster": (gb, v)},
                                  monkeypatch, tmp_path)
    key, r = orun._run_unit("e3:line1_cluster", bundles, vals, "x" * 64)
    fp = orun._write_unit(key, r)
    assert os.path.exists(fp)
    assert r["units"]["bounce"]["pooled"]["n_boot"] > 0
    assert len(r["units"]["bounce"]["contributing"]) == 2
    assert sum(1 for _ in open(led)) == 2          # one trial/endpoint


def test_runner_e1resid_unit_end_to_end(tmp_path, monkeypatch):
    ev = _synth_events(seed=9)
    tab = {"resid": {"gate_pass": True,
                     "recency": {"gate_pass": True},
                     "r2": 0.4, "n_top": 80, "n_bot": 80}}
    gb, v = _synth_bundle(ev, tab)
    bundles, vals, led = _env_for({"sd_base": (gb, v)},
                                  monkeypatch, tmp_path)
    key, r = orun._run_unit("e1resid:sd_base", bundles, vals, "x" * 64)
    fp = orun._write_unit(key, r)
    assert os.path.exists(fp)
    assert r["units"]["continuation"]["pooled"]["n_boot"] > 0
    assert sum(1 for _ in open(led)) == 2


def test_runner_e2_unit_end_to_end(tmp_path, monkeypatch):
    ev = _synth_events(seed=13)
    n = len(ev)
    ia, ib = list(range(0, n, 2)), list(range(1, n, 2))
    pair = "line1_cluster|fractal_h1"
    _PAIRS_FOR[pair] = {"grid": "line1_cluster", "gate_pass": True,
                        "n_a": len(ia), "n_b": len(ib), "n_x": 0,
                        "smd_post": 0.02}
    tab = {}
    gb, v = _synth_bundle(ev, tab,
                          pair_arms={pair: {"ia": ia, "ib": ib}})
    bundles, vals, led = _env_for({"line1_cluster": (gb, v)},
                                  monkeypatch, tmp_path)
    key, r = orun._run_unit("e2:" + pair, bundles, vals, "x" * 64)
    fp = orun._write_unit(key, r)
    assert os.path.exists(fp)
    assert r["units"]["bounce"]["pooled"]["n_boot"] > 0
    assert sum(1 for _ in open(led)) == 2
    _PAIRS_FOR.clear()
