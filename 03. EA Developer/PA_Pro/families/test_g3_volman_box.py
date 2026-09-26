"""test_g3_volman_box.py — unit + adversarial tests for G3 (v1).

G3 = Volman build-up: 12-bar box compressed vs its rolling percentile,
small bodies, pressed against a salient zone, broken WITH the HTF trend.
Zones injected by monkeypatching ``sf_ctx.zones_at``.

Run:  python test_g3_volman_box.py
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
import g3_volman_box as g3      # noqa: E402

PIP = 1e-4
N = 900
T0 = pa_clock.utc_epoch_to_server(
    int(np.datetime64("2016-01-04T05:00:00").astype(np.int64)))


def _in_sess(D, i):
    return pa_random.session_of(
        pa_clock.utc_minute_of_day(int(D["t"][i]))) is not None


def _mk_D(n=N, atr_pips=20.0, atr_h1=50.0, trend=1):
    """Fat volatile history (300p ranges) so a 16p box is a low pct."""
    t = T0 + 300 * np.arange(n, dtype=np.int64)
    return {
        "symbol": "SYN", "t": t,
        "o": np.full(n, 1.1000), "h": np.full(n, 1.1150),
        "l": np.full(n, 1.0850), "c": np.full(n, 1.1000),
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
        self._orig = _ORIG_ZONES_AT     # always the true original
        sf_ctx.zones_at = self._get

    def _get(self, D, t):
        return self.map.get(t, [])

    def close(self):
        sf_ctx.zones_at = _ORIG_ZONES_AT


def _flat_box(D, t_end, hi=1.1008, lo=1.0992):
    """Bars [t_end-40, t_end) flat into a 16p box at `hi`/`lo`."""
    s = max(0, t_end - 40)
    D["h"][s:t_end] = hi
    D["l"][s:t_end] = lo
    D["o"][s:t_end] = 1.1000
    D["c"][s:t_end] = 1.1000


def _scene_up(D, t_sig=850):
    """Uptrend, flat box top 1.1008, break-up bar closing at 1.1020."""
    _flat_box(D, t_sig)
    D["h"][t_sig] = 1.1025
    D["l"][t_sig] = 1.0995
    D["o"][t_sig] = 1.1000
    D["c"][t_sig] = 1.1020


def test_basic_break_up():
    D = _mk_D(trend=1)
    _scene_up(D)
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1)]     # ceiling, hi 2p over box_hi
    ent = g3.detect(D, 1.0, {"S_pips": 18.0, "session": 0})
    assert len(ent) >= 1
    e = ent[0]
    assert e["side"] == 1
    assert abs(e["order_px"] - (1.1008 + PIP)) < 1e-9     # beyond box_hi
    assert abs(e["inv"] - (1.0992 - PIP)) < 1e-9          # far side of box
    zs.close()
    print("basic break-up stop order: OK")


def test_break_down():
    D = _mk_D(trend=-1)
    t_sig = 850
    _flat_box(D, t_sig)
    D["h"][t_sig] = 1.1005
    D["l"][t_sig] = 1.0975
    D["o"][t_sig] = 1.1000
    D["c"][t_sig] = 1.0980
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.0985, 1.0995, 1)]      # floor, lo 3p under box_lo
    ent = g3.detect(D, 1.0, {"S_pips": 18.0, "session": 0})
    assert len(ent) >= 1
    e = ent[0]
    assert e["side"] == -1
    assert abs(e["order_px"] - (1.0992 - PIP)) < 1e-9
    assert abs(e["inv"] - (1.1008 + PIP)) < 1e-9
    zs.close()
    print("break-down stop order: OK")


def test_counter_trend_rejected():
    D = _mk_D(trend=-1)          # downtrend but break UP
    _scene_up(D)
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1)]
    ent = g3.detect(D, 1.0, {"S_pips": 18.0, "session": 0})
    assert ent == []
    zs.close()
    print("counter-trend break rejected: OK")


def test_compression_gate():
    D = _mk_D(trend=1)
    _scene_up(D)
    # history itself is a 16p box too -> box percentile ~100 -> reject
    D["h"][:] = 1.1008
    D["l"][:] = 1.0992
    _scene_up(D)
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1)]
    ent = g3.detect(D, 1.0, {"S_pips": 18.0, "session": 0})
    assert ent == []
    zs.close()
    print("compression percentile gate: OK")


def test_proximity_gate():
    D = _mk_D(trend=1)
    _scene_up(D)
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.1100, 1.1110, -1)]     # zone 100p away
    ent = g3.detect(D, 1.0, {"S_pips": 18.0, "session": 0})
    assert ent == []
    zs.close()
    print("zone proximity gate: OK")


def test_salience_gate():
    D = _mk_D(trend=1)
    _scene_up(D)
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1, n_res=0, age=5)]
    ent = g3.detect(D, 1.0, {"S_pips": 18.0, "session": 0,
                             "sal_min": 2.5})
    assert ent == []
    zs.close()
    print("salience gate: OK")


def test_session_gate():
    D = _mk_D(trend=1)
    oos = None
    for i in range(700, N - 2):
        if not _in_sess(D, i):
            oos = i
            break
    assert oos is not None
    _scene_up(D, t_sig=oos)
    zs = _Zones()
    for i in range(oos - 30, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1)]
    ent = g3.detect(D, 1.0, {"S_pips": 18.0})     # session ON
    assert all(e["sig"] != oos for e in ent)
    zs.close()
    print("session gate: OK")


def test_warmup_boundary():
    D = _mk_D(trend=1)
    D["warmup"][:700] = True
    D["first_live_idx"] = 700
    _scene_up(D, t_sig=850)
    zs = _Zones()
    for i in range(700, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1)]
    ent = g3.detect(D, 1.0, {"S_pips": 18.0, "session": 0})
    assert all(e["sig"] >= 700 for e in ent)
    zs.close()
    print("warmup boundary: OK")


def test_prefix_invariance():
    D = _mk_D(trend=1)
    _scene_up(D)
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1)]
    prm = {"S_pips": 18.0, "session": 0}
    full = g3.detect(D, 1.0, prm)
    T = 860
    Dp = {k: (v[:T].copy() if isinstance(v, np.ndarray) and
              v.shape and v.shape[0] == N else v)
          for k, v in D.items()}
    cut = g3.detect(Dp, 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] < T]
    zs.close()
    print("prefix invariance: OK")


def test_future_mutation():
    D = _mk_D(trend=1)
    _scene_up(D)
    zs = _Zones()
    for i in range(600, N):
        zs.map[i] = [_zone(1.1005, 1.1015, -1)]
    prm = {"S_pips": 18.0, "session": 0}
    base = g3.detect(D, 1.0, prm)
    Dm = _mk_D(trend=1)
    _scene_up(Dm)
    Dm["h"][870:] *= 2
    Dm["l"][870:] /= 2
    mut = g3.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["order_px"]) for e in mut if e["sig"] <= 850] == \
           [(e["sig"], e["order_px"]) for e in base if e["sig"] <= 850]
    zs.close()
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_break_up()
    test_break_down()
    test_counter_trend_rejected()
    test_compression_gate()
    test_proximity_gate()
    test_salience_gate()
    test_session_gate()
    test_warmup_boundary()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL G3 detector tests passed")
