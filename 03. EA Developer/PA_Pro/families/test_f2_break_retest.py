"""test_f2_break_retest.py — unit + adversarial tests for the F2 detector (v2).

F2 = first pullback into a broken (or role-flipped) zone rejected in the
break direction; episode anchored at the break bar.  Adversarial coverage:
unbroken zones must not signal, wrong approach role must not signal, stale
retest window must not signal, one signal per episode, reclaim ends the
episode, session gate, warm-up, prefix invariance, future-bar mutation.

Run:  python test_f2_break_retest.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx                  # noqa: E402
import pa_clock                # noqa: E402
import pa_random               # noqa: E402
import f2_break_retest as f2   # noqa: E402

PIP = 1e-4
N = 300
# Monday 2016-01-04, start 05:00 UTC so early bars sit in the eu session.
T0 = pa_clock.utc_epoch_to_server(
    int(np.datetime64("2016-01-04T05:00:00").astype(np.int64)))


def _utc_min(D, i):
    return pa_clock.utc_minute_of_day(int(D["t"][i]))


def _in_sess(D, i):
    return pa_random.session_of(_utc_min(D, i)) is not None


def _mk_D(n=N, atr_pips=20.0):
    t = T0 + 300 * np.arange(n, dtype=np.int64)
    return {
        "symbol": "SYN", "t": t,
        "o": np.full(n, 1.1000), "h": np.full(n, 1.1005),
        "l": np.full(n, 1.0995), "c": np.full(n, 1.1000),
        "pip": PIP, "first_live_idx": 0, "warmup": np.zeros(n, dtype=bool),
        "s_atr_m5": np.full(n, atr_pips * PIP),
        "s_atr_h1": np.full(n, 80 * PIP),
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


def _put_zone(D, t, lo, hi, armed=1, broken=0, broken_idx=-1, role_flip=0,
              broken_side=0, approach=0, touches=2, last_touch=-1,
              slot=0, zid=100):
    D["zlo"][t, slot] = lo
    D["zhi"][t, slot] = hi
    D["zcnt"][t] = max(D["zcnt"][t], slot + 1)
    f = D["zf"][t, slot]
    f[sf_ctx.ZF["zid"]] = zid
    f[sf_ctx.ZF["armed"]] = armed
    f[sf_ctx.ZF["broken"]] = broken
    f[sf_ctx.ZF["broken_idx"]] = broken_idx
    f[sf_ctx.ZF["role_flip"]] = role_flip
    f[sf_ctx.ZF["broken_side"]] = broken_side
    f[sf_ctx.ZF["approach_side"]] = approach
    f[sf_ctx.ZF["touches"]] = touches
    f[sf_ctx.ZF["last_touch"]] = last_touch
    f[sf_ctx.ZF["strength"]] = 0.9


def _sess_idx(D, start=5, count=3, step=2):
    out = []
    i = start
    while len(out) < count and i < N - 2:
        if _in_sess(D, i) and all(i - j >= step for j in out):
            out.append(i)
        i += 1
    return out


def _broken_ceiling_scene(D, brk_i, touch_i, sig_i, zid=100):
    """Ceiling zone [1.1000,1.1010] broke UP at brk_i (broken_side=-1).
    Pullback touch at touch_i (>brk_i); rejection close above hi at sig_i.
    s_struct = order(1.1023) - inv(min l[ti..si] = 1.0998 - pip = 1.0997)
             = 26p -> rung 32."""
    for t in range(brk_i, sig_i + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1,
                  broken_idx=brk_i, broken_side=-1, approach=1,
                  last_touch=(touch_i if t >= touch_i else brk_i - 5),
                  zid=zid)
    D["l"][brk_i:sig_i + 1] = 1.1002   # pullback lows ride the band top
    D["l"][touch_i] = 1.0998           # dip into the band
    D["c"][touch_i] = 1.1004           # inside band
    D["o"][sig_i] = 1.1006
    D["h"][sig_i] = 1.1022
    D["l"][sig_i] = 1.1002
    D["c"][sig_i] = 1.1018             # > hi, bullish
    D["c"][sig_i - 1] = 1.1007         # <= hi


def test_basic_break_retest_long():
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    _broken_ceiling_scene(D, bi, ti, si)
    ent = f2.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent
    e = ent[0]
    assert e["sig"] == si and e["side"] == 1
    assert abs(e["order_px"] - (1.1022 + PIP)) < 1e-9
    assert abs(e["inv"] - (1.0998 - PIP)) < 1e-9
    assert f2.detect(D, 1.0, {"S_pips": 24.0}) == []   # rung partition
    print("basic break-retest long + rung partition: OK")


def test_broken_floor_short():
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    lo, hi = 1.0990, 1.1000
    for t in range(bi, si + 1):
        _put_zone(D, t, lo, hi, armed=0, broken=1, broken_idx=bi,
                  broken_side=1, approach=-1,
                  last_touch=(ti if t >= ti else bi - 5))
    D["h"][bi:si + 1] = 1.0998
    D["h"][ti] = 1.1002               # pullback up into band
    D["c"][ti] = 1.0996
    D["o"][si] = 1.0994
    D["h"][si] = 1.0998
    D["l"][si] = 1.0978
    D["c"][si] = 1.0982               # < lo
    D["c"][si - 1] = 1.0993
    # inv = max(h[ti..si]) + pip = 1.1003; order = 1.0977 -> 26p -> rung 32
    ent = f2.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1 and ent[0]["side"] == -1
    assert abs(ent[0]["order_px"] - (1.0978 - PIP)) < 1e-9
    assert abs(ent[0]["inv"] - (1.1002 + PIP)) < 1e-9
    print("broken floor short: OK")


def test_flipped_phase_still_signals():
    # After flip (broken=0, role_flip=1, armed): anchor carries; a post-flip
    # retest still fires.
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    fi = bi + 3                        # flip observed a few bars post-break
    for t in range(bi, si + 1):
        if t < fi:
            _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1,
                      broken_idx=bi, broken_side=-1, approach=1,
                      last_touch=bi - 5)
        else:
            _put_zone(D, t, 1.1000, 1.1010, armed=1, broken=0,
                      role_flip=1, broken_side=-1, approach=1,
                      last_touch=(ti if t >= ti else bi - 5))
    D["l"][bi:si + 1] = 1.1002
    D["l"][ti] = 1.0998
    D["c"][ti] = 1.1004
    D["o"][si], D["h"][si], D["l"][si], D["c"][si] = 1.1006, 1.1022, 1.1002, 1.1018
    D["c"][si - 1] = 1.1007
    ent = f2.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1 and ent[0]["sig"] == si and ent[0]["side"] == 1
    print("post-flip retest signals (anchor carried): OK")


def test_unbroken_zone_rejected():
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    for t in range(bi, si + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
                  broken_side=0, approach=1,
                  last_touch=(ti if t >= ti else -1))
    D["l"][ti] = 1.0998
    D["o"][si], D["h"][si], D["l"][si], D["c"][si] = 1.1006, 1.1022, 1.1002, 1.1018
    D["c"][si - 1] = 1.1007
    assert f2.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("unbroken zone rejected: OK")


def test_wrong_approach_role():
    # broken ceiling (broke up) but approach_side=-1 (price below band)
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    for t in range(bi, si + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=-1,
                  last_touch=(ti if t >= ti else bi - 5))
    D["l"][ti] = 1.0998
    D["o"][si], D["h"][si], D["l"][si], D["c"][si] = 1.1006, 1.1022, 1.1002, 1.1018
    D["c"][si - 1] = 1.1007
    assert f2.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("wrong approach role rejected: OK")


def test_stale_retest_window():
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    si2 = min(si + 60, N - 3)
    for t in range(bi, si2 + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1,
                  last_touch=(ti if t >= ti else bi - 5))
    D["l"][ti] = 1.0998
    D["o"][si2], D["h"][si2], D["l"][si2], D["c"][si2] = \
        1.1006, 1.1022, 1.1002, 1.1018
    D["c"][si2 - 1] = 1.1007
    assert si2 - ti > 48, (si2, ti)
    assert f2.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("stale retest window rejected: OK")


def test_one_signal_per_episode():
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    _broken_ceiling_scene(D, bi, ti, si)
    si2 = si + 20                      # second rejection, same episode
    for t in range(si + 1, si2 + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1, last_touch=ti)
    D["o"][si2], D["h"][si2], D["l"][si2], D["c"][si2] = \
        1.1006, 1.1022, 1.1002, 1.1018
    D["c"][si2 - 1] = 1.1007
    ent = f2.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent
    print("one signal per episode: OK")


def test_reclaim_ends_episode():
    # zone reclaims (broken=0, no flip) -> episode dead; later identical
    # geometry must not fire
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    _broken_ceiling_scene(D, bi, ti, si)
    si2 = si + 20
    for t in range(si + 1, si2 + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
                  approach=1, last_touch=ti)   # reclaimed
    D["o"][si2], D["h"][si2], D["l"][si2], D["c"][si2] = \
        1.1006, 1.1022, 1.1002, 1.1018
    D["c"][si2 - 1] = 1.1007
    ent = f2.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent          # only the first signal
    print("reclaim ends episode: OK")


def test_session_gate():
    D = _mk_D()
    oos = None
    for i in range(5, N - 2):
        if not _in_sess(D, i):
            oos = i
            break
    assert oos is not None
    bi, ti = oos - 4, oos - 1
    for t in range(bi, oos + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1, last_touch=ti)
    D["l"][ti] = 1.0998
    D["o"][oos], D["h"][oos], D["l"][oos], D["c"][oos] = \
        1.1006, 1.1022, 1.1002, 1.1018
    D["c"][oos - 1] = 1.1007
    ent = f2.detect(D, 1.0, {"S_pips": 32.0})
    assert all(e["sig"] != oos for e in ent), ent
    D2 = _mk_D()
    bi, ti, si = _sess_idx(D2)
    _broken_ceiling_scene(D2, bi, ti, si)
    assert len(f2.detect(D2, 1.0, {"S_pips": 32.0})) == 1
    print("session gate: OK")


def test_warmup_boundary():
    D = _mk_D()
    D["warmup"][:100] = True
    D["first_live_idx"] = 100
    bi, ti, si = 100, 104, 108
    for t in range(bi, si + 1):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1, last_touch=ti)
    D["l"][ti] = 1.0998
    D["o"][si], D["h"][si], D["l"][si], D["c"][si] = 1.1006, 1.1022, 1.1002, 1.1018
    D["c"][si - 1] = 1.1007
    ent = f2.detect(D, 1.0, {"S_pips": 32.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent)
    # episode fully inside warm-up emits nothing
    for t in range(50, 58):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=50,
                  broken_side=-1, approach=1, last_touch=54)
    D["l"][54] = 1.0998
    D["o"][56], D["h"][56], D["l"][56], D["c"][56] = 1.1006, 1.1022, 1.1002, 1.1018
    D["c"][55] = 1.1007
    ent = f2.detect(D, 1.0, {"S_pips": 32.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent)
    print("warmup boundary: OK")


def _truncate_D(D, T):
    out = {}
    for k, v in D.items():
        a = np.asarray(v)
        if k in ("t", "o", "h", "l", "c", "warmup", "s_atr_m5", "s_atr_h1",
                 "zcnt", "zlo", "zhi", "zf"):
            out[k] = a[:T].copy()
        else:
            out[k] = v
    return out


def test_prefix_invariance():
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    _broken_ceiling_scene(D, bi, ti, si)
    prm = {"S_pips": 32.0}
    full = f2.detect(D, 1.0, prm)
    cut = f2.detect(_truncate_D(D, si + 3), 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] < si + 1]
    print("prefix invariance: OK")


def test_future_mutation():
    D = _mk_D()
    bi, ti, si = _sess_idx(D)
    _broken_ceiling_scene(D, bi, ti, si)
    prm = {"S_pips": 32.0}
    base = f2.detect(D, 1.0, prm)
    Dm = _mk_D()
    _broken_ceiling_scene(Dm, bi, ti, si)
    Dm["h"][si + 2:] *= 2
    Dm["l"][si + 2:] /= 2
    Dm["c"][si + 2:] *= 1.5
    mut = f2.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["side"], e["order_px"]) for e in mut
            if e["sig"] <= si] == \
           [(e["sig"], e["side"], e["order_px"]) for e in base]
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_break_retest_long()
    test_broken_floor_short()
    test_flipped_phase_still_signals()
    test_unbroken_zone_rejected()
    test_wrong_approach_role()
    test_stale_retest_window()
    test_one_signal_per_episode()
    test_reclaim_ends_episode()
    test_session_gate()
    test_warmup_boundary()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL F2 detector tests passed")
