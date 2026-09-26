"""test_g1_htf_pullback.py — unit + adversarial tests for G1 (v1).

G1 = HTF pullback entered AT a salient zone edge via LIMIT order —
the anti-chase fix for F4.  Zones injected by monkeypatching
``g1.sf_ctx.zones_at``.

Run:  python test_g1_htf_pullback.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "lib")
for _p in (HERE, LIB):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pa_clock                 # noqa: E402
import pa_random                # noqa: E402
import sf_ctx                   # noqa: E402
import sf_autopsy as SA         # noqa: E402
import g1_htf_pullback as g1    # noqa: E402

PIP = 1e-4
N = 300
T0 = pa_clock.utc_epoch_to_server(
    int(np.datetime64("2016-01-04T05:00:00").astype(np.int64)))


def _in_sess(D, i):
    return pa_random.session_of(
        pa_clock.utc_minute_of_day(int(D["t"][i]))) is not None


def _mk_D(n=N, atr_pips=20.0, atr_h1=50.0, trend=1):
    t = T0 + 300 * np.arange(n, dtype=np.int64)
    return {
        "symbol": "SYN", "t": t,
        "o": np.full(n, 1.1000), "h": np.full(n, 1.1005),
        "l": np.full(n, 1.0995), "c": np.full(n, 1.1000),
        "pip": PIP, "first_live_idx": 0, "warmup": np.zeros(n, dtype=bool),
        "s_atr_m5": np.full(n, atr_pips * PIP),
        "s_atr_h1": np.full(n, atr_h1 * PIP),
        "s_tr_h1": np.full(n, trend, dtype=np.float64),
        "s_tr_h4": np.full(n, trend, dtype=np.float64),
        "h1p_i": np.zeros(0, dtype=np.int64),
        "h1p_px": np.zeros(0, dtype=np.float64),
        "h1p_conf": np.zeros(0, dtype=np.int64),
    }


def _zone(lo, hi, approach, zid=1, armed=1.0, n_res=3, age=200):
    return {"lo": lo, "hi": hi, "approach_side": approach,
            "zid": zid, "armed": armed, "broken": 0.0,
            "broken_idx": -1, "broken_side": 0, "touches": 3,
            "last_touch": -1, "role_flip": 0, "strength": 1,
            "fresh": 0, "n_respected": n_res, "age": age,
            "quality": 1, "kind": 0, "scale": 1}


_ORIG_ZONES_AT = sf_ctx.zones_at


class _Zones:
    def __init__(self):
        self.map = {}
        self._orig = _ORIG_ZONES_AT
        sf_ctx.zones_at = self._get

    def _get(self, D, t):
        return self.map.get(t, [])

    def close(self):
        sf_ctx.zones_at = _ORIG_ZONES_AT


def _pull_scene(D, t_sig=100):
    """Uptrend; price pulls down to floor zone [1.0980, 1.0990].
    Signal bar dips to 1.0988 (<= hi 1.0990 + touch). Zone width 10p;
    inv = lo-buf = 1.0979; order = hi-buf = 1.0989 -> s_struct 10p."""
    D["l"][t_sig] = 1.0988
    D["h"][t_sig] = 1.1005
    D["c"][t_sig] = 1.0998


def test_basic_pullback_long():
    D = _mk_D(trend=1)
    _pull_scene(D)
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1)]      # floor from above
    # salience: n_res=3 + pivot? none -> 3 - .5*(10/50) + .25*log(1+200/96)
    #         = 3 - 0.1 + 0.28 = 3.18 >= 2.0
    ent = g1.detect(D, 1.0, {"S_pips": 18.0})
    assert len(ent) >= 1
    e = ent[0]
    assert e["side"] == 1
    assert abs(e["order_px"] - (1.0990 - PIP)) < 1e-9   # limit at edge
    assert abs(e["inv"] - (1.0980 - PIP)) < 1e-9        # below far edge
    assert e["order_px"] < D["c"][e["sig"]]             # not a chase
    zs.close()
    print("basic pullback long (limit at edge): OK")


def test_pullback_short():
    D = _mk_D(trend=-1)
    t_sig = 100
    D["h"][t_sig] = 1.1012     # reaches ceiling lo edge 1.1010
    D["l"][t_sig] = 1.0995
    D["c"][t_sig] = 1.1002
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.1010, 1.1020, -1)]     # ceiling from below
    ent = g1.detect(D, 1.0, {"S_pips": 18.0})
    assert len(ent) >= 1
    e = ent[0]
    assert e["side"] == -1
    assert abs(e["order_px"] - (1.1010 + PIP)) < 1e-9
    assert abs(e["inv"] - (1.1020 + PIP)) < 1e-9
    zs.close()
    print("pullback short: OK")


def test_no_touch_no_signal():
    D = _mk_D(trend=1)
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1)]
    # edge hi = 1.0990; touch tol = 0.35*20p = 7p -> touch iff l<=1.0997
    D["l"][:] = 1.1005            # 15p above the edge: never reaches
    ent = g1.detect(D, 1.0, {"S_pips": 18.0})
    assert ent == []
    zs.close()
    print("no touch -> no signal: OK")


def test_close_through_zone_rejected():
    D = _mk_D(trend=1)
    t_sig = 100
    D["l"][t_sig] = 1.0970     # deep through the zone
    D["h"][t_sig] = 1.1005
    D["c"][t_sig] = 1.0975     # closes BELOW lo 1.0980 -> zone failing
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1)]
    ent = g1.detect(D, 1.0, {"S_pips": 18.0})
    assert all(e["sig"] != t_sig for e in ent), ent   # never at the break bar
    zs.close()
    print("close through zone rejected: OK")


def test_low_salience_rejected():
    D = _mk_D(trend=1)
    _pull_scene(D)
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1, n_res=0, age=5)]
    ent = g1.detect(D, 1.0, {"S_pips": 18.0, "sal_min": 2.5})
    assert ent == []
    zs.close()
    print("low-salience zone rejected: OK")


def test_room_gate():
    D = _mk_D(trend=1)
    _pull_scene(D)
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1),
                     _zone(1.1015, 1.1025, -1, zid=2)]  # ceiling 26p up
    # room from order 1.0989 to opp lo 1.1015 = 26p < 2R*18p=36p -> skip
    ent = g1.detect(D, 1.0, {"S_pips": 18.0})
    assert ent == []
    # but rung 18 at 26p room would pass room>=1R? room_min_R=2 -> 36p
    zs.close()
    zs2 = _Zones()
    for i in range(50, N):
        zs2.map[i] = [_zone(1.0980, 1.0990, 1),
                      _zone(1.1060, 1.1070, -1, zid=2)]  # ceiling 71p up
    ent2 = g1.detect(D, 1.0, {"S_pips": 18.0})
    assert len(ent2) >= 1
    zs2.close()
    print("room-to-opposing-zone gate: OK")


def test_session_gate():
    D = _mk_D(trend=1)
    oos = None
    for i in range(60, N - 2):
        if not _in_sess(D, i):
            oos = i
            break
    assert oos is not None
    _pull_scene(D, t_sig=oos)
    zs = _Zones()
    for i in range(oos - 20, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1)]
    ent = g1.detect(D, 1.0, {"S_pips": 18.0})
    assert all(e["sig"] != oos for e in ent)
    zs.close()
    print("session gate: OK")


def test_warmup_boundary():
    D = _mk_D(trend=1)
    D["warmup"][:100] = True
    D["first_live_idx"] = 100
    _pull_scene(D, t_sig=120)
    zs = _Zones()
    for i in range(100, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1)]
    ent = g1.detect(D, 1.0, {"S_pips": 18.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent)
    zs.close()
    print("warmup boundary: OK")


def test_prefix_invariance():
    D = _mk_D(trend=1)
    _pull_scene(D)
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1)]
    prm = {"S_pips": 18.0}
    full = g1.detect(D, 1.0, prm)
    T = 105
    Dp = {k: (v[:T].copy() if isinstance(v, np.ndarray) and
              v.shape and v.shape[0] == N else v)
          for k, v in D.items()}
    cut = g1.detect(Dp, 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] < T]
    zs.close()
    print("prefix invariance: OK")


def test_future_mutation():
    D = _mk_D(trend=1)
    _pull_scene(D)
    zs = _Zones()
    for i in range(50, N):
        zs.map[i] = [_zone(1.0980, 1.0990, 1)]
    prm = {"S_pips": 18.0}
    base = g1.detect(D, 1.0, prm)
    Dm = _mk_D(trend=1)
    _pull_scene(Dm)
    Dm["h"][150:] *= 2
    Dm["l"][150:] /= 2
    mut = g1.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["side"], e["order_px"]) for e in mut
            if e["sig"] <= 100] == \
           [(e["sig"], e["side"], e["order_px"]) for e in base
            if e["sig"] <= 100]
    zs.close()
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_pullback_long()
    test_pullback_short()
    test_no_touch_no_signal()
    test_close_through_zone_rejected()
    test_low_salience_rejected()
    test_room_gate()
    test_session_gate()
    test_warmup_boundary()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL G1 detector tests passed")
