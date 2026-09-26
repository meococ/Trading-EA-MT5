"""test_f5_second_entry.py — unit + adversarial tests for F5 (v1).

F5 = Brooks second entry: two-legged pullback in trend, fires on the
confirmation bar of the second leg's pivot.  Adversarial coverage: no
trend -> no signal; missing bounce pivot between legs -> no signal;
leg_span and tol_atr gates; dedupe; session; warm-up; prefix invariance;
future mutation.

Run:  python test_f5_second_entry.py
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
import f5_second_entry as f5    # noqa: E402

PIP = 1e-4
N = 300
T0 = pa_clock.utc_epoch_to_server(
    int(np.datetime64("2016-01-04T05:00:00").astype(np.int64)))


def _in_sess(D, i):
    return pa_random.session_of(
        pa_clock.utc_minute_of_day(int(D["t"][i]))) is not None


def _mk_D(n=N, atr_pips=8.0, trend=1):
    t = T0 + 300 * np.arange(n, dtype=np.int64)
    return {
        "symbol": "SYN", "t": t,
        "o": np.full(n, 1.1000), "h": np.full(n, 1.1005),
        "l": np.full(n, 1.0995), "c": np.full(n, 1.1000),
        "pip": PIP, "first_live_idx": 0, "warmup": np.zeros(n, dtype=bool),
        "s_atr_m5": np.full(n, atr_pips * PIP),
        "s_tr_h1": np.full(n, trend, dtype=np.float64),
        "s_tr_h4": np.full(n, trend, dtype=np.float64),
        "piv_idx": np.zeros(0, dtype=np.int64),
        "piv_px": np.zeros(0, dtype=np.float64),
        "piv_side": np.zeros(0, dtype=np.int64),
        "piv_conf": np.zeros(0, dtype=np.int64),
    }


def _pivots(D, pivs):
    """pivs = [(bar, px, side, conf_bar), ...]"""
    D["piv_idx"] = np.array([p[0] for p in pivs], dtype=np.int64)
    D["piv_px"] = np.array([p[1] for p in pivs], dtype=np.float64)
    D["piv_side"] = np.array([p[2] for p in pivs], dtype=np.int64)
    D["piv_conf"] = np.array([p[3] for p in pivs], dtype=np.int64)


def _two_leg_scene(D, L1=10, H1=14, L2=20, conf2=24):
    """Uptrend: L1 low pivot at 10, bounce high at 14, L2 at 20 confirmed
    at conf2.  L2 bar range: l=1.0990 h=1.1008 -> s_struct = 18p+2 = 20p
    -> rung 24."""
    _pivots(D, [
        (L1, 1.0988, -1, L1 + 3),
        (H1, 1.1020, 1, H1 + 3),
        (L2, 1.0990, -1, conf2),
    ])
    D["l"][L2] = 1.0990
    D["h"][L2] = 1.1008
    D["c"][conf2] = 1.1005
    D["h"][conf2] = 1.1012
    D["l"][conf2] = 1.1000


def test_basic_second_entry_long():
    D = _mk_D(trend=1)
    _two_leg_scene(D)
    # v2: make L1 the DEEPER low (classic higher-low second entry)
    D["l"][10] = 1.0985
    # order = h[20]+1p = 1.1009; inv = min(l10,l20)-1p = 1.0984 -> 25p -> 32
    ent = f5.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1, ent
    e = ent[0]
    assert e["sig"] == 24 and e["side"] == 1
    assert abs(e["order_px"] - (1.1008 + PIP)) < 1e-9
    assert abs(e["inv"] - (1.0985 - PIP)) < 1e-9     # deepest point = L1
    assert f5.detect(D, 1.0, {"S_pips": 24.0}) == []   # rung partition
    print("basic second-entry long + rung partition: OK")


def test_second_entry_short():
    D = _mk_D(trend=-1)
    # downtrend: H1 high at 10, bounce low at 14, H2 at 20 conf 24
    _pivots(D, [
        (10, 1.1012, 1, 13),
        (14, 1.0980, -1, 17),
        (20, 1.1010, 1, 24),
    ])
    D["h"][20] = 1.1010
    D["l"][20] = 1.0992
    D["h"][10] = 1.1015               # v2: H1 is the higher high (deeper stop)
    D["c"][24] = 1.0995
    D["h"][24] = 1.1000
    D["l"][24] = 1.0988
    # order = l20-1p = 1.0991; inv = max(h10,h20)+1p = 1.1016 -> 25p -> 32
    ent = f5.detect(D, 1.0, {"S_pips": 32.0})
    assert len(ent) == 1 and ent[0]["side"] == -1
    assert abs(ent[0]["order_px"] - (1.0992 - PIP)) < 1e-9
    assert abs(ent[0]["inv"] - (1.1015 + PIP)) < 1e-9
    print("second-entry short: OK")


def test_no_trend():
    D = _mk_D(trend=0)
    _two_leg_scene(D)
    assert f5.detect(D, 1.0, {"S_pips": 24.0}) == []
    print("no trend -> no signal: OK")


def test_no_bounce_leg():
    # remove the high pivot between the lows -> no two legs
    D = _mk_D(trend=1)
    _pivots(D, [
        (10, 1.0988, -1, 13),
        (20, 1.0990, -1, 24),
    ])
    D["l"][20] = 1.0990
    D["h"][20] = 1.1008
    assert f5.detect(D, 1.0, {"S_pips": 24.0}) == []
    print("missing bounce leg rejected: OK")


def test_leg_span_gate():
    D = _mk_D(trend=1)
    _two_leg_scene(D, L1=10, H1=14, L2=70, conf2=74)
    D["h"][74] = 1.1012
    D["l"][74] = 1.1000
    assert f5.detect(D, 1.0, {"S_pips": 24.0}) == []   # 60 > leg_span 48
    print("leg span gate: OK")


def test_tol_gate():
    D = _mk_D(trend=1)
    # L2 far below L1: |1.0990-1.0988|=2p > tol_atr*A5? A5=8p, tol=1.0 -> 8p
    # keep tol but make L2 much lower
    _two_leg_scene(D)
    D["piv_px"][2] = 1.0960              # L2 28p below L1
    D["l"][20] = 1.0960
    ent = f5.detect(D, 1.0, {"S_pips": 24.0, "tol_atr": 0.5})
    assert ent == []                     # 28p > 0.5*8p=4p
    print("tol_atr gate: OK")


def test_confirmation_timing():
    # pivot confirmed later than conf2 -> must not fire early
    D = _mk_D(trend=1)
    _two_leg_scene(D, conf2=30)
    D["h"][30] = 1.1012
    D["l"][30] = 1.1000
    ent = f5.detect(D, 1.0, {"S_pips": 24.0})
    assert len(ent) == 1 and ent[0]["sig"] == 30
    print("fires at confirmation bar only: OK")


def test_session_gate():
    D = _mk_D(trend=1)
    # place conf bar out of session
    oos = None
    for i in range(30, N - 2):
        if not _in_sess(D, i):
            oos = i
            break
    assert oos is not None
    _two_leg_scene(D, L1=oos - 14, H1=oos - 10, L2=oos - 4, conf2=oos)
    D["h"][oos] = 1.1012
    D["l"][oos] = 1.1000
    ent = f5.detect(D, 1.0, {"S_pips": 24.0})
    assert all(e["sig"] != oos for e in ent), ent
    D2 = _mk_D(trend=1)
    _two_leg_scene(D2)
    assert len(f5.detect(D2, 1.0, {"S_pips": 24.0})) == 1
    print("session gate: OK")


def test_warmup_boundary():
    D = _mk_D(trend=1)
    D["warmup"][:100] = True
    D["first_live_idx"] = 100
    _two_leg_scene(D, L1=104, H1=110, L2=116, conf2=120)
    D["h"][120] = 1.1012
    D["l"][120] = 1.1000
    ent = f5.detect(D, 1.0, {"S_pips": 24.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent)
    # pivot confirmed inside warm-up emits nothing
    D2 = _mk_D(trend=1)
    D2["warmup"][:100] = True
    D2["first_live_idx"] = 100
    _two_leg_scene(D2, L1=60, H1=66, L2=72, conf2=76)
    ent2 = f5.detect(D2, 1.0, {"S_pips": 24.0, "session": 0})
    assert all(e["sig"] >= 100 for e in ent2)
    print("warmup boundary: OK")


def _truncate_D(D, T):
    out = {}
    for k, v in D.items():
        a = np.asarray(v)
        if k in ("t", "o", "h", "l", "c", "warmup", "s_atr_m5",
                 "s_tr_h1", "s_tr_h4"):
            out[k] = a[:T].copy()
        elif k == "piv_conf":
            m = a <= T
            out[k] = a[m].copy()
        elif k in ("piv_idx", "piv_px", "piv_side"):
            m = D["piv_conf"] <= T
            out[k] = a[m].copy()
        else:
            out[k] = v
    return out


def test_prefix_invariance():
    D = _mk_D(trend=1)
    _two_leg_scene(D)
    prm = {"S_pips": 24.0}
    full = f5.detect(D, 1.0, prm)
    cut = f5.detect(_truncate_D(D, 26), 1.0, prm)
    assert [e["sig"] for e in cut] == [e["sig"] for e in full if e["sig"] < 26]
    print("prefix invariance: OK")


def test_future_mutation():
    D = _mk_D(trend=1)
    _two_leg_scene(D)
    prm = {"S_pips": 24.0}
    base = f5.detect(D, 1.0, prm)
    Dm = _mk_D(trend=1)
    _two_leg_scene(Dm)
    Dm["h"][30:] *= 2
    Dm["l"][30:] /= 2
    Dm["c"][30:] *= 1.5
    mut = f5.detect(Dm, 1.0, prm)
    assert [(e["sig"], e["side"], e["order_px"]) for e in mut
            if e["sig"] <= 24] == \
           [(e["sig"], e["side"], e["order_px"]) for e in base]
    print("future mutation: OK")


if __name__ == "__main__":
    test_basic_second_entry_long()
    test_second_entry_short()
    test_no_trend()
    test_no_bounce_leg()
    test_leg_span_gate()
    test_tol_gate()
    test_confirmation_timing()
    test_session_gate()
    test_warmup_boundary()
    test_prefix_invariance()
    test_future_mutation()
    print("ALL F5 detector tests passed")
