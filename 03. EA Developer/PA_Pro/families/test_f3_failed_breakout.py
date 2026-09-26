"""test_f3_failed_breakout.py — unit + adversarial tests for F3 (v1).

F3 = reclaim event = failed breakout: zone broken at t-1, broken==0 with
role_flip==0 at t -> fade (side = broken_side).  Adversarial coverage:
still-broken zones don't fire, flips don't fire (F2 regime), reclaim
without a tracked break doesn't fire, stale observation (zone left the
view mid-episode) doesn't fire, one signal per episode, session gate,
warm-up, prefix invariance, future-bar mutation.

Run:  python test_f3_failed_breakout.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sf_ctx                    # noqa: E402
import pa_clock                  # noqa: E402
import pa_random                 # noqa: E402
import f3_failed_breakout as f3  # noqa: E402

PIP = 1e-4
N = 300
T0 = pa_clock.utc_epoch_to_server(
    int(np.datetime64("2016-01-04T05:00:00").astype(np.int64)))


def _in_sess(D, i):
    return pa_random.session_of(
        pa_clock.utc_minute_of_day(int(D["t"][i]))) is not None


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


def _trap_scene(D, brk_i, recl_i, zid=100):
    """Ceiling [1.1000,1.1010] breaks UP at brk_i (broken_side=-1): probe
    high 1.1028; stays broken until recl_i where it reclaims (broken=0,
    role_flip=0, close back inside band).  Fade = SHORT.
    s_struct: inv = max(h[brk..recl]) + pip = 1.1029; order = l[recl]-pip.
    Reclaim bar: o=1.1009 h=1.1012 l=1.0998 c=1.1004 (inside band, 14p
    range) -> order 1.0997 -> s_struct 32p -> rung 32."""
    for t in range(brk_i, recl_i):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=brk_i,
                  broken_side=-1, approach=1, zid=zid)
    D["h"][brk_i] = 1.1028            # the poke extreme
    D["c"][brk_i] = 1.1018            # break close above hi
    # reclaim bar: close back inside band
    _put_zone(D, recl_i, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
              broken_side=-1, approach=1, zid=zid)
    D["o"][recl_i] = 1.1009
    D["h"][recl_i] = 1.1012
    D["l"][recl_i] = 1.0998
    D["c"][recl_i] = 1.1004           # inside band, bearish body


def test_basic_trap_short():
    D = _mk_D()
    bi, _, ri = _sess_idx(D)
    _trap_scene(D, bi, ri)
    ent = f3.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent
    e = ent[0]
    assert e["sig"] == ri and e["side"] == -1
    assert abs(e["order_px"] - (1.0998 - PIP)) < 1e-9
    assert abs(e["inv"] - (1.1028 + PIP)) < 1e-9
    assert f3.detect(D, 1.0, {"S_pips": 24.0}) == []   # rung partition
    print("basic trap short + rung partition: OK")


def test_trap_long():
    D = _mk_D()
    bi, _, ri = _sess_idx(D)
    lo, hi = 1.0990, 1.1000
    for t in range(bi, ri):
        _put_zone(D, t, lo, hi, armed=0, broken=1, broken_idx=bi,
                  broken_side=1, approach=-1)
    D["l"][bi] = 1.0972               # probe extreme below
    D["c"][bi] = 1.0982
    _put_zone(D, ri, lo, hi, armed=1, broken=0, role_flip=0,
              broken_side=1, approach=-1)
    D["o"][ri], D["h"][ri], D["l"][ri], D["c"][ri] = 1.0991, 1.1002, 1.0988, 1.0996
    # inv = min(l[bi..ri]) - pip = 1.0971; order = h+pip = 1.1003
    # s_struct = 32p -> rung 32
    ent = f3.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1 and ent[0]["side"] == 1
    assert abs(ent[0]["order_px"] - (1.1002 + PIP)) < 1e-9
    assert abs(ent[0]["inv"] - (1.0972 - PIP)) < 1e-9
    print("trap long: OK")


def test_still_broken_no_fire():
    D = _mk_D()
    bi, _, ri = _sess_idx(D)
    for t in range(bi, ri + 1):        # still broken at ri -> no reclaim
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1)
    D["h"][bi] = 1.1028
    D["o"][ri], D["h"][ri], D["l"][ri], D["c"][ri] = 1.1009, 1.1012, 1.0998, 1.1004
    assert f3.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("still broken -> no fire: OK")


def test_flip_not_reclaim():
    # broken@ri-1 -> role_flip=1@ri is F2's regime, not F3
    D = _mk_D()
    bi, _, ri = _sess_idx(D)
    for t in range(bi, ri):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1)
    D["h"][bi] = 1.1028
    _put_zone(D, ri, 1.1000, 1.1010, armed=1, broken=0, role_flip=1,
              broken_side=-1, approach=1)
    D["o"][ri], D["h"][ri], D["l"][ri], D["c"][ri] = 1.1015, 1.1030, 1.1010, 1.1026
    assert f3.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("flip is not reclaim: OK")


def test_no_tracked_break():
    # zone appears already unbroken at ri (was never observed broken) -> no
    D = _mk_D()
    _, _, ri = _sess_idx(D)
    _put_zone(D, ri, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
              broken_side=-1, approach=1)
    D["o"][ri], D["h"][ri], D["l"][ri], D["c"][ri] = 1.1009, 1.1012, 1.0998, 1.1004
    assert f3.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("untracked break -> no fire: OK")


def test_stale_observation():
    # zone left the view for one bar mid-episode: last broken obs != ri-1
    D = _mk_D()
    bi, _, ri = _sess_idx(D)
    for t in range(bi, ri - 1):        # broken through ri-2, absent at ri-1
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1)
    D["h"][bi] = 1.1028
    _put_zone(D, ri, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
              broken_side=-1, approach=1)
    D["o"][ri], D["h"][ri], D["l"][ri], D["c"][ri] = 1.1009, 1.1012, 1.0998, 1.1004
    assert f3.detect(D, 1.0, {"S_pips": 32.0}) == []
    print("stale observation -> no fire: OK")


def test_one_signal_per_episode():
    D = _mk_D()
    bi, _, ri = _sess_idx(D)
    _trap_scene(D, bi, ri)
    # zone re-breaks and reclaims again -> new episode -> may fire again;
    # but a DUPLICATE reclaim of the SAME episode must not
    ri2 = ri + 1
    _put_zone(D, ri2, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
              broken_side=-1, approach=1)
    D["o"][ri2], D["h"][ri2], D["l"][ri2], D["c"][ri2] = 1.1009, 1.1012, 1.0998, 1.1004
    ent = f3.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent
    print("one signal per episode: OK")


def test_session_gate():
    D = _mk_D()
    oos = None
    for i in range(6, N - 2):
        if not _in_sess(D, i) and _in_sess(D, i - 1):
            oos = i
            break
    assert oos is not None
    bi = oos - 4
    for t in range(bi, oos):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1)
    D["h"][bi] = 1.1028
    _put_zone(D, oos, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
              broken_side=-1, approach=1)
    D["o"][oos], D["h"][oos], D["l"][oos], D["c"][oos] = 1.1009, 1.1012, 1.0998, 1.1004
    ent = f3.detect(D, 1.0, {"S_pips": 32.0})
    assert all(e["sig"] != oos for e in ent), ent
    D2 = _mk_D()
    bi, _, ri = _sess_idx(D2)
    _trap_scene(D2, bi, ri)
    assert len(f3.detect(D2, 1.0, {"S_pips": 32.0})) == 1
    print("session gate: OK")


def test_warmup_boundary():
    D = _mk_D()
    D["warmup"][:100] = True
    D["first_live_idx"] = 100
    bi, ri = 96, 104                    # break inside warm-up, reclaim live
    for t in range(bi, ri):
        _put_zone(D, t, 1.1000, 1.1010, armed=0, broken=1, broken_idx=bi,
                  broken_side=-1, approach=1)
    D["h"][bi] = 1.1028
    _put_zone(D, ri, 1.1000, 1.1010, armed=1, broken=0, role_flip=0,
              broken_side=-1, approach=1)
    D["o"][ri], D["h"][ri], D["l"][ri], D["c"][ri] = 1.1009, 1.1012, 1.0998, 1.1004
    ent = f3.detect(D, 1.0, {"S_pips": 32.0, "session": 0})
    # break bars 96-99 are warm-up: detector never observes broken state
    # (loop starts at first_live) -> no tracked break -> no signal.  That is
    # the mandated contract: warm-up bars never produce signals or outcomes.
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
    bi, _, ri = _sess_idx(D)
    _trap_scene(D, bi, ri)
    prm = {"S_pips": 32.0}
    full = f3.detect(D, 1.0, prm)
    cut = f3.detect(_truncate_D(D, ri + 3), 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] <= ri]
    print("prefix invariance: OK")


def test_future_mutation():
    D = _mk_D()
    bi, _, ri = _sess_idx(D)
    _trap_scene(D, bi, ri)
    prm = {"S_pips": 32.0}
    base = f3.detect(D, 1.0, prm)
    Dm = _mk_D()
    _trap_scene(Dm, bi, ri)
    Dm["h"][ri + 2:] *= 2
    Dm["l"][ri + 2:] /= 2
    Dm["c"][ri + 2:] *= 1.5
    mut = f3.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["side"], e["order_px"]) for e in mut
            if e["sig"] <= ri] == \
           [(e["sig"], e["side"], e["order_px"]) for e in base]
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_trap_short()
    test_trap_long()
    test_still_broken_no_fire()
    test_flip_not_reclaim()
    test_no_tracked_break()
    test_stale_observation()
    test_one_signal_per_episode()
    test_session_gate()
    test_warmup_boundary()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL F3 detector tests passed")
