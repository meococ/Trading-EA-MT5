"""test_f4_trend_pullback.py — unit + adversarial tests for F4 (v1).

F4 = trend-aligned pullback to an armed zone + momentum resumption.
Adversarial coverage: no trend -> no signal; counter-trend zone role
rejected; stale pullback rejected; resumption must beat prev bar extreme;
episode dedupe; session gate; warm-up; prefix invariance; future mutation.

Run:  python test_f4_trend_pullback.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx                     # noqa: E402
import pa_clock                   # noqa: E402
import pa_random                  # noqa: E402
import f4_trend_pullback as f4    # noqa: E402

PIP = 1e-4
N = 300
T0 = pa_clock.utc_epoch_to_server(
    int(np.datetime64("2016-01-04T05:00:00").astype(np.int64)))


def _in_sess(D, i):
    return pa_random.session_of(
        pa_clock.utc_minute_of_day(int(D["t"][i]))) is not None


def _mk_D(n=N, atr_pips=20.0, trend=0):
    t = T0 + 300 * np.arange(n, dtype=np.int64)
    return {
        "symbol": "SYN", "t": t,
        "o": np.full(n, 1.1000), "h": np.full(n, 1.1005),
        "l": np.full(n, 1.0995), "c": np.full(n, 1.1000),
        "pip": PIP, "first_live_idx": 0, "warmup": np.zeros(n, dtype=bool),
        "s_atr_m5": np.full(n, atr_pips * PIP),
        "s_atr_h1": np.full(n, 80 * PIP),
        "s_tr_h1": np.full(n, trend, dtype=np.float64),
        "s_tr_h4": np.full(n, trend, dtype=np.float64),
        "zlo": np.full((n, sf_ctx.SLOTS), np.nan),
        "zhi": np.full((n, sf_ctx.SLOTS), np.nan),
        "zf": np.zeros((n, sf_ctx.SLOTS, sf_ctx.ZF_N)),
        "zcnt": np.zeros(n, dtype=np.int64),
        "h1p_i": np.zeros(0, dtype=np.int64),
        "h1p_px": np.zeros(0, dtype=np.float64),
        "h1p_side": np.zeros(0, dtype=np.int64),
        "h1p_conf": np.zeros(0, dtype=np.int64),
        "h1p_anchor": np.zeros(0, dtype=np.int64),
    }


def _put_zone(D, t, lo, hi, armed=1, broken=0, approach=1, touches=2,
              last_touch=-1, slot=0, zid=100):
    D["zlo"][t, slot] = lo
    D["zhi"][t, slot] = hi
    D["zcnt"][t] = max(D["zcnt"][t], slot + 1)
    f = D["zf"][t, slot]
    f[sf_ctx.ZF["zid"]] = zid
    f[sf_ctx.ZF["armed"]] = armed
    f[sf_ctx.ZF["broken"]] = broken
    f[sf_ctx.ZF["approach_side"]] = approach
    f[sf_ctx.ZF["touches"]] = touches
    f[sf_ctx.ZF["last_touch"]] = last_touch
    f[sf_ctx.ZF["strength"]] = 0.9


def _sess_idx(D, start=5, count=2, step=2):
    out = []
    i = start
    while len(out) < count and i < N - 2:
        if _in_sess(D, i) and all(i - j >= step for j in out):
            out.append(i)
        i += 1
    return out


def _uptrend_pullback_scene(D, touch_i, sig_i, zid=100):
    """Uptrend (s_tr=+1).  Floor zone [1.0990,1.1000] below price,
    approach_side=+1.  Pullback touch at touch_i (dip low 1.0996 into
    band); resumption bar sig_i closes 1.1018 > hi(1.1000) and > h[t-1].
    s_struct: order = h+pip = 1.1023; inv = min l[touch..sig] - pip:
    lows set to 1.1002 except touch 1.0996 -> inv = 1.0995 -> 28p -> 32."""
    for t in range(max(0, touch_i - 6), sig_i + 1):
        _put_zone(D, t, 1.0990, 1.1000, approach=1,
                  last_touch=(touch_i if t >= touch_i else -1), zid=zid)
    lo_i = max(0, touch_i - 6)
    D["l"][lo_i:sig_i + 1] = 1.1002
    D["h"][lo_i:sig_i + 1] = 1.1006
    D["c"][lo_i:sig_i + 1] = 1.1004
    D["l"][touch_i] = 1.0996          # pullback dips into the band
    D["c"][touch_i] = 1.0998
    D["o"][sig_i] = 1.1008
    D["h"][sig_i] = 1.1022
    D["l"][sig_i] = 1.1002
    D["c"][sig_i] = 1.1018            # > hi AND > h[t-1] = 1.1006


def test_basic_uptrend_pullback():
    D = _mk_D(trend=1)
    ti, si = _sess_idx(D)
    _uptrend_pullback_scene(D, ti, si)
    ent = f4.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent
    e = ent[0]
    assert e["sig"] == si and e["side"] == 1
    assert abs(e["order_px"] - (1.1022 + PIP)) < 1e-9
    assert abs(e["inv"] - (1.0996 - PIP)) < 1e-9
    assert f4.detect(D, 1.0, {"S_pips": 24.0}) == []
    print("basic uptrend pullback + rung partition: OK")


def test_downtrend_pullback():
    D = _mk_D(trend=-1)
    ti, si = _sess_idx(D)
    lo, hi = 1.1000, 1.1010             # ceiling above price
    for t in range(max(0, ti - 6), si + 1):
        _put_zone(D, t, lo, hi, approach=-1,
                  last_touch=(ti if t >= ti else -1))
    lo_i = max(0, ti - 6)
    D["h"][lo_i:si + 1] = 1.0998
    D["l"][lo_i:si + 1] = 1.0994
    D["c"][lo_i:si + 1] = 1.0996
    D["h"][ti] = 1.1004                 # pullback up into band
    D["c"][ti] = 1.1002
    D["o"][si] = 1.0992
    D["h"][si] = 1.0998
    D["l"][si] = 1.0978
    D["c"][si] = 1.0982                 # < lo AND < l[t-1]=1.0994
    # inv = max(h[ti..si]) + pip = 1.1005; order = 1.0977 -> 28p -> rung 32
    ent = f4.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1 and ent[0]["side"] == -1
    assert abs(ent[0]["order_px"] - (1.0978 - PIP)) < 1e-9
    assert abs(ent[0]["inv"] - (1.1004 + PIP)) < 1e-9
    print("downtrend pullback short: OK")


def test_no_trend_no_signal():
    D = _mk_D(trend=0)
    ti, si = _sess_idx(D)
    _uptrend_pullback_scene(D, ti, si)
    assert f4.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("no trend -> no signal: OK")


def test_countertrend_zone_rejected():
    # uptrend but the zone is a ceiling (approach_side=-1) -> skip
    D = _mk_D(trend=1)
    ti, si = _sess_idx(D)
    for t in range(max(0, ti - 6), si + 1):
        _put_zone(D, t, 1.0990, 1.1000, approach=-1,
                  last_touch=(ti if t >= ti else -1))
    D["l"][ti] = 1.0996
    D["o"][si], D["h"][si], D["l"][si], D["c"][si] = 1.1008, 1.1022, 1.1002, 1.1018
    assert f4.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("counter-trend zone rejected: OK")


def test_stale_pullback():
    D = _mk_D(trend=1)
    ti, si = _sess_idx(D)
    si2 = min(si + 40, N - 3)
    assert si2 - ti > 24, (si2, ti)     # beyond pull_win
    for t in range(max(0, ti - 6), si2 + 1):
        _put_zone(D, t, 1.0990, 1.1000, approach=1,
                  last_touch=(ti if t >= ti else -1))
    D["l"][ti] = 1.0996
    D["o"][si2], D["h"][si2], D["l"][si2], D["c"][si2] = \
        1.1008, 1.1022, 1.1002, 1.1018
    assert f4.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("stale pullback rejected: OK")


def test_resumption_must_beat_prev_high():
    # c[t] > hi but c[t] <= h[t-1] -> not a momentum resumption
    D = _mk_D(trend=1)
    ti, si = _sess_idx(D)
    _uptrend_pullback_scene(D, ti, si)
    D["h"][si - 1] = 1.1030             # prev bar higher than signal close
    assert f4.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("weak resumption rejected: OK")


def test_episode_dedupe():
    D = _mk_D(trend=1)
    ti, si = _sess_idx(D)
    _uptrend_pullback_scene(D, ti, si)
    si2 = si + 6
    for t in range(si + 1, si2 + 1):
        _put_zone(D, t, 1.0990, 1.1000, approach=1, last_touch=ti)
    D["o"][si2], D["h"][si2], D["l"][si2], D["c"][si2] = \
        1.1008, 1.1022, 1.1002, 1.1018
    ent = f4.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent
    print("episode dedupe: OK")


def test_session_gate():
    D = _mk_D(trend=1)
    oos = None
    for i in range(8, N - 2):
        if not _in_sess(D, i):
            oos = i
            break
    assert oos is not None
    ti = oos - 2
    for t in range(max(0, ti - 6), oos + 1):
        _put_zone(D, t, 1.0990, 1.1000, approach=1,
                  last_touch=(ti if t >= ti else -1))
    D["l"][ti] = 1.0996
    D["o"][oos], D["h"][oos], D["l"][oos], D["c"][oos] = \
        1.1008, 1.1022, 1.1002, 1.1018
    D["h"][oos - 1] = 1.1006
    ent = f4.detect(D, 1.0, {"S_pips": 32.0})
    assert all(e["sig"] != oos for e in ent), ent
    D2 = _mk_D(trend=1)
    ti, si = _sess_idx(D2)
    _uptrend_pullback_scene(D2, ti, si)
    assert len(f4.detect(D2, 1.0, {"S_pips": 32.0})) == 1
    print("session gate: OK")


def test_warmup_boundary():
    D = _mk_D(trend=1)
    D["warmup"][:100] = True
    D["first_live_idx"] = 100
    ti, si = 104, 108
    for t in range(98, si + 1):
        _put_zone(D, t, 1.0990, 1.1000, approach=1,
                  last_touch=(ti if t >= ti else -1))
    D["l"][98:si + 1] = 1.1002
    D["h"][98:si + 1] = 1.1006
    D["c"][98:si + 1] = 1.1004
    D["l"][ti] = 1.0996
    D["c"][ti] = 1.0998
    D["o"][si], D["h"][si], D["l"][si], D["c"][si] = 1.1008, 1.1022, 1.1002, 1.1018
    ent = f4.detect(D, 1.0, {"S_pips": 32.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent)
    print("warmup boundary: OK")


def _truncate_D(D, T):
    out = {}
    for k, v in D.items():
        a = np.asarray(v)
        if k in ("t", "o", "h", "l", "c", "warmup", "s_atr_m5", "s_atr_h1",
                 "s_tr_h1", "s_tr_h4", "zcnt", "zlo", "zhi", "zf"):
            out[k] = a[:T].copy()
        else:
            out[k] = v
    return out


def test_prefix_invariance():
    D = _mk_D(trend=1)
    ti, si = _sess_idx(D)
    _uptrend_pullback_scene(D, ti, si)
    prm = {"S_pips": 32.0}
    full = f4.detect(D, 1.0, prm)
    cut = f4.detect(_truncate_D(D, si + 3), 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] <= si]
    print("prefix invariance: OK")


def test_future_mutation():
    D = _mk_D(trend=1)
    ti, si = _sess_idx(D)
    _uptrend_pullback_scene(D, ti, si)
    prm = {"S_pips": 32.0}
    base = f4.detect(D, 1.0, prm)
    Dm = _mk_D(trend=1)
    _uptrend_pullback_scene(Dm, ti, si)
    Dm["h"][si + 2:] *= 2
    Dm["l"][si + 2:] /= 2
    Dm["c"][si + 2:] *= 1.5
    mut = f4.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["side"], e["order_px"]) for e in mut
            if e["sig"] <= si] == \
           [(e["sig"], e["side"], e["order_px"]) for e in base]
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_uptrend_pullback()
    test_downtrend_pullback()
    test_no_trend_no_signal()
    test_countertrend_zone_rejected()
    test_stale_pullback()
    test_resumption_must_beat_prev_high()
    test_episode_dedupe()
    test_session_gate()
    test_warmup_boundary()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL F4 detector tests passed")
