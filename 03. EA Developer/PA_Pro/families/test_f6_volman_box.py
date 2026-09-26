"""test_f6_volman_box.py — unit + adversarial tests for F6 (v1).

F6 = Volman box break with buildup: compressed box pressed against an
armed zone edge; close through box + zone edge; stop order 1 pip beyond
the box edge; inv at the far box side.

Zones are injected by monkeypatching ``f6.sf_ctx.zones_at`` so tests
need no real zone generator.

Run:  python test_f6_volman_box.py
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
import f6_volman_box as f6      # noqa: E402

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
    }


def _zone(lo, hi, approach, zid=1, armed=1.0):
    return {"lo": lo, "hi": hi, "approach_side": approach,
            "zid": zid, "armed": armed, "broken": 0.0,
            "broken_idx": -1, "broken_side": 0, "touches": 3,
            "last_touch": -1, "role_flip": 0, "strength": 1,
            "fresh": 0, "n_respected": 0, "age": 50, "quality": 1,
            "kind": 0, "scale": 1}


_ORIG_ZONES_AT = sf_ctx.zones_at


class _Zones:
    """Monkeypatchable zones provider: {bar: [zone dicts]}."""

    def __init__(self):
        self.map = {}
        self._orig = _ORIG_ZONES_AT     # always the true original
        sf_ctx.zones_at = self._get

    def _get(self, D, t):
        return self.map.get(t, [])

    def __del__(self):
        sf_ctx.zones_at = _ORIG_ZONES_AT


def _box_scene(D, t_sig=100, tight=8):
    """Tight box over [t_sig-12 .. t_sig-1]: hi=1.1010 lo=1.0992 (18p
    range; A5=20p -> box height 0.9x ATR, comfortably under box_atr
    2.5/4.0).  Signal bar breaks up through 1.1010."""
    for i in range(t_sig - 12, t_sig):
        D["h"][i] = 1.1010
        D["l"][i] = 1.0992
        D["c"][i] = 1.1001
    D["h"][t_sig] = 1.1028
    D["l"][t_sig] = 1.1000
    D["c"][t_sig] = 1.1025            # through box_hi 1.1010+buf and zone hi


def test_basic_box_break_long():
    D = _mk_D()
    _box_scene(D)
    zs = _Zones()
    # ceiling at 1.1008-1.1012 pressed against box top 1.1010
    for i in range(80, N):
        zs.map[i] = [_zone(1.1008, 1.1012, -1)]
    # s_struct = order(1.1011)-inv(1.0991) = 20p -> rung 24
    ent = f6.detect(D, 1.0, {"S_pips": 24.0})
    assert len(ent) >= 1, ent
    e = ent[0]
    assert e["side"] == 1 and e["zid"] == 1
    assert abs(e["order_px"] - (1.1010 + PIP)) < 1e-9
    assert abs(e["inv"] - (1.0992 - PIP)) < 1e-9
    assert f6.detect(D, 1.0, {"S_pips": 18.0}) == []   # rung partition
    sf_ctx.zones_at = zs._orig
    print("basic box break long + rung partition: OK")


def test_box_break_short():
    D = _mk_D()
    t_sig = 100
    for i in range(t_sig - 12, t_sig):
        D["h"][i] = 1.1008
        D["l"][i] = 1.0990
        D["c"][i] = 1.0999
    D["h"][t_sig] = 1.1000
    D["l"][t_sig] = 1.0972
    D["c"][t_sig] = 1.0975
    zs = _Zones()
    for i in range(80, N):
        zs.map[i] = [_zone(1.0988, 1.0992, 1)]       # floor at box bottom
    # order = box_lo-1p = 1.0989; inv = box_hi+1p = 1.1009 -> 20p -> rung 24
    ent = f6.detect(D, 1.0, {"S_pips": 24.0})
    assert len(ent) == 1 and ent[0]["side"] == -1
    sf_ctx.zones_at = zs._orig
    print("box break short: OK")


def test_no_zone_no_signal():
    D = _mk_D()
    _box_scene(D)
    zs = _Zones()
    ent = f6.detect(D, 1.0, {"S_pips": 24.0})
    assert ent == []
    sf_ctx.zones_at = zs._orig
    print("no zone -> no signal (buildup required): OK")


def test_unarmed_zone_rejected():
    D = _mk_D()
    _box_scene(D)
    zs = _Zones()
    for i in range(80, N):
        zs.map[i] = [_zone(1.1008, 1.1012, -1, armed=0.0)]
    assert f6.detect(D, 1.0, {"S_pips": 24.0}) == []
    sf_ctx.zones_at = zs._orig
    print("unarmed zone rejected: OK")


def test_wide_box_rejected():
    D = _mk_D()
    t_sig = 100
    for i in range(t_sig - 12, t_sig):
        D["h"][i] = 1.1050             # 60p box > 2.5*20p=50p threshold
        D["l"][i] = 1.0990
    D["h"][t_sig] = 1.1068
    D["c"][t_sig] = 1.1065
    D["l"][t_sig] = 1.1040
    zs = _Zones()
    for i in range(80, N):
        zs.map[i] = [_zone(1.1046, 1.1052, -1)]
    assert f6.detect(D, 1.0, {"S_pips": 32.0, "box_atr": 2.5}) == []
    sf_ctx.zones_at = zs._orig
    print("wide box rejected: OK")


def test_zone_edge_not_broken():
    D = _mk_D()
    t_sig = 100
    for i in range(t_sig - 12, t_sig):
        D["h"][i] = 1.1010
        D["l"][i] = 1.0992
        D["c"][i] = 1.1001
    # closes above box but NOT above the zone hi (zone sits above box)
    D["h"][t_sig] = 1.1015
    D["l"][t_sig] = 1.1000
    D["c"][t_sig] = 1.1012            # > box_hi+buf but < zone hi 1.1020
    zs = _Zones()
    for i in range(80, N):
        zs.map[i] = [_zone(1.1016, 1.1020, -1)]
    assert f6.detect(D, 1.0, {"S_pips": 24.0}) == []
    sf_ctx.zones_at = zs._orig
    print("close beyond box but inside zone edge rejected: OK")


def test_dedupe_cooldown():
    D = _mk_D()
    _box_scene(D)
    # a second break 5 bars later on the same zone
    _box_scene(D, t_sig=108)
    D["h"][108] = 1.1030
    D["c"][108] = 1.1028
    zs = _Zones()
    for i in range(80, N):
        zs.map[i] = [_zone(1.1008, 1.1012, -1)]
    ent = f6.detect(D, 1.0, {"S_pips": 24.0})
    sigs = [e["sig"] for e in ent]
    assert len(sigs) == len(set(sigs))
    assert all(abs(a - b) >= 12 for a, b in zip(sigs, sigs[1:]))
    sf_ctx.zones_at = zs._orig
    print("dedupe + cooldown: OK")


def test_session_gate():
    D = _mk_D()
    oos = None
    for i in range(60, N - 2):
        if not _in_sess(D, i) and _in_sess(D, i + 1):
            oos = i
            break
    assert oos is not None
    _box_scene(D, t_sig=oos)
    zs = _Zones()
    for i in range(oos - 20, N):
        zs.map[i] = [_zone(1.1008, 1.1012, -1)]
    ent = f6.detect(D, 1.0, {"S_pips": 24.0})
    assert all(e["sig"] != oos for e in ent), ent
    sf_ctx.zones_at = zs._orig
    print("session gate: OK")


def test_warmup_boundary():
    D = _mk_D()
    D["warmup"][:100] = True
    D["first_live_idx"] = 100
    _box_scene(D, t_sig=120)
    zs = _Zones()
    for i in range(100, N):
        zs.map[i] = [_zone(1.1008, 1.1012, -1)]
    ent = f6.detect(D, 1.0, {"S_pips": 24.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent)
    D2 = _mk_D()
    D2["warmup"][:100] = True
    D2["first_live_idx"] = 100
    _box_scene(D2, t_sig=90)
    zs2 = _Zones()
    for i in range(0, N):
        zs2.map[i] = [_zone(1.1008, 1.1012, -1)]
    ent2 = f6.detect(D2, 1.0, {"S_pips": 24.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent2)
    sf_ctx.zones_at = zs._orig
    sf_ctx.zones_at = zs2._orig
    print("warmup boundary: OK")


def test_prefix_invariance():
    D = _mk_D()
    _box_scene(D)
    zs = _Zones()
    for i in range(80, N):
        zs.map[i] = [_zone(1.1008, 1.1012, -1)]
    prm = {"S_pips": 24.0}
    full = f6.detect(D, 1.0, prm)
    T = 105
    Dp = {k: (v[:T].copy() if isinstance(v, np.ndarray) and
              v.shape and v.shape[0] == N else v)
          for k, v in D.items()}
    cut = f6.detect(Dp, 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] < T]
    sf_ctx.zones_at = zs._orig
    print("prefix invariance: OK")


def test_future_mutation():
    D = _mk_D()
    _box_scene(D)
    zs = _Zones()
    for i in range(80, N):
        zs.map[i] = [_zone(1.1008, 1.1012, -1)]
    prm = {"S_pips": 24.0}
    base = f6.detect(D, 1.0, prm)
    Dm = _mk_D()
    _box_scene(Dm)
    Dm["h"][150:] *= 2
    Dm["l"][150:] /= 2
    Dm["c"][150:] *= 1.5
    mut = f6.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["side"], e["order_px"]) for e in mut
            if e["sig"] <= 100] == \
           [(e["sig"], e["side"], e["order_px"]) for e in base]
    sf_ctx.zones_at = zs._orig
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_box_break_long()
    test_box_break_short()
    test_no_zone_no_signal()
    test_unarmed_zone_rejected()
    test_wide_box_rejected()
    test_zone_edge_not_broken()
    test_dedupe_cooldown()
    test_session_gate()
    test_warmup_boundary()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL F6 detector tests passed")
