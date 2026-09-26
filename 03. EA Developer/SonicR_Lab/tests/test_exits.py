"""test_exits.py - ROUND 2D mandatory tests T2/T3 (synthetic paths).

T1/T4/T5 live in runs/verify_2d.py (need real data files).
T2: synthetic paths for X1/X2 (+ E1b leg A) and short mirrors.
T3: no look-ahead in the dragon exit - indicators RECOMPUTED from
    altered M1 bars; exit unchanged by post-exit edits; changing the
    triggering M15 bar's close changes the decision only from its close.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from src import data as dm
from src import exits as ex
from src.components import indicators as ind


def _mk_m1(bars):
    """bars: list of (o,h,l,c) minute bars starting at t0."""
    t0 = 1_577_833_200        # 2020-01-01 05:00 server-ish
    a = np.array
    return {"t": t0 + 60 * a(range(len(bars))),
            "o": a([b[0] for b in bars], float),
            "h": a([b[1] for b in bars], float),
            "l": a([b[2] for b in bars], float),
            "c": a([b[3] for b in bars], float),
            "tv": np.zeros(len(bars), float),
            "suspect": np.zeros(len(bars), bool)}


def _tfx_from_m1(m1, e34_bias=0.0):
    tf = dm.resample(m1, 15)
    e34h, _c, e34l = ind.dragon(tf)
    return {"t": tf["t"], "c": tf["c"], "e34h": e34h,
            "e34l": e34l, "m1_hi": tf["m1_hi"]}


def _res(m1, dr, rule, fill_i=0, sl=None, tp=None, fill=100.0,
         flat_ctm=None, skip=False, pess=False, sym="EURUSD", tfx=None):
    flat_ctm = m1["t"][-1] + 10 * 86400 if flat_ctm is None else flat_ctm
    return ex.resolve_exit(m1, tfx, sym, dr, fill_i, fill, sl, tp,
                           flat_ctm, rule, skip_suspect=skip,
                           pessimistic=pess)


def test_t2_be1_long():
    """+1R then back to entry -> 'be' ~0R."""
    bars = [(100, 100.2, 99.9, 100.0),            # fill bar
            (100.0, 101.2, 99.95, 101.1),          # trigger +1R (101)
            (101.1, 101.15, 99.9, 100.0)]          # dips below BE
    m1 = _mk_m1(bars)
    r = _res(m1, 1, "X1", sl=99.0, tp=103.0)
    assert r["reason"] == "be"
    assert abs(r["exit_px"] - (100.0 + 1e-4)) < 1e-9


def test_t2_sl_and_trigger_same_bar():
    """SL + trigger inside one bar -> 'sl' at -1R (SL first)."""
    bars = [(100, 100.2, 99.9, 100.0),
            (100.0, 101.5, 98.5, 99.0)]            # +1R and SL together
    m1 = _mk_m1(bars)
    r = _res(m1, 1, "X1", sl=99.0, tp=103.0)
    assert r["reason"] == "sl"
    assert r["exit_px"] == 99.0


def test_t2_x2_formula_both_in_one_bar():
    """One bar reaches +1R and full TP: leg A at +1R, leg B at TP."""
    bars = [(100, 100.2, 99.9, 100.0),
            (100.0, 103.5, 99.95, 103.2)]
    m1 = _mk_m1(bars)
    r = _res(m1, 1, "X2", sl=99.0, tp=103.0)
    assert r["reason"] == "tp" and r["part_i"] == 1
    assert r["part_px"] == 101.0 and r["exit_px"] == 103.0
    gross = 0.5 * (101.0 - 100) + 0.5 * (103.0 - 100)
    assert gross == 2.0


def test_t2_x2_sl_first_both_legs():
    bars = [(100, 100.2, 99.9, 100.0),
            (100.0, 101.4, 98.8, 99.0)]            # +1R and SL same bar
    m1 = _mk_m1(bars)
    r = _res(m1, 1, "X2", sl=99.0, tp=103.0)
    assert r["reason"] == "sl" and r["part_i"] < 0


def test_t2_pessimistic_same_bar():
    """Pessimistic: trigger bar contains +1R and BE -> BE on that bar."""
    bars = [(100, 100.2, 99.9, 100.0),
            (100.0, 101.5, 99.9, 100.5)]          # +1R and BE together
    m1 = _mk_m1(bars)
    r = _res(m1, 1, "X1", sl=99.0, tp=103.0, pess=True)
    assert r["reason"] == "be" and r["exit_i"] == 1
    r2 = _res(m1, 1, "X1", sl=99.0, tp=103.0)     # normal: BE from i+1
    assert r2["reason"] != "be" or r2["exit_i"] > 1


def test_t2_short_mirror():
    bars = [(100, 100.1, 99.8, 100.0),
            (100.0, 100.05, 98.8, 98.9),           # +1R (99) hit
            (98.9, 100.2, 98.85, 100.0)]           # back above BE
    m1 = _mk_m1(bars)
    r = _res(m1, -1, "X1", sl=101.0, tp=97.0)
    assert r["reason"] == "be"
    assert abs(r["exit_px"] - (100.0 - 1e-4)) < 1e-9


def test_t2_x2_e1b_leg_a():
    """Leg A inside roll window pays the stress (exit sell for long)."""
    from src import sim as sm
    a, b = sm.ROLL["EURUSD"][0]
    # build bars whose first bar sits inside the roll window
    t_roll = 1_577_833_200 - (1_577_833_200 % 86400) + a * 60
    bars = [(100, 100.2, 99.9, 100.0),
            (100.0, 101.4, 99.95, 101.2),
            (101.2, 103.2, 101.0, 103.0)]
    m1 = _mk_m1(bars)
    m1["t"] = t_roll + 60 * np.arange(len(bars))
    r = _res(m1, 1, "X2", sl=99.0, tp=103.0)
    assert r["part_px"] < 101.0                    # sell-side stress
    assert abs(r["part_px"] - (101.0 - 2e-4)) < 1e-9


def _ramp_m1(n15=46):
    """Rising market: M15 bar k closes 100 + 0.1k -> EMA34(L) ends above
    entry, so a later dip below the band can fire 'dragon' before BE."""
    n = n15 * 15
    idx = np.arange(n)
    c15 = 100.0 + 0.1 * (idx // 15)
    o = c15 - 0.02; c = c15.copy()
    h = c15 + 0.05; l = c15 - 0.05
    return {"t": 1_577_833_200 + 60 * idx, "o": o, "h": h, "l": l,
            "c": c, "tv": np.zeros(n, float),
            "suspect": np.zeros(n, bool)}, n15


def test_t3_dragon_no_lookahead():
    """Post-exit M1 edits -> recompute -> same exit; altering the
    triggering M15 close moves the decision."""
    m1, n15 = _ramp_m1()
    # +1R trigger around M15 bar 20 (fill=100, SL=98 -> trig=102)
    # ramp reaches it naturally; make one M15 bar (35) a pullback that
    # closes below EMA34(L) while its lows stay above BE=100.0001
    tfx0 = _tfx_from_m1(m1)
    j_pb = 35
    band = tfx0["e34l"][j_pb - 1]                # band before the bar
    assert band > 100.5                          # BE far below the band
    b = slice(j_pb * 15, (j_pb + 1) * 15)
    m1["c"][b] = band - 0.10
    m1["l"][b] = band - 0.11
    m1["h"][b] = band - 0.05
    m1["o"][b] = band - 0.07
    tfx = _tfx_from_m1(m1)
    assert tfx["c"][j_pb] < tfx["e34l"][j_pb]
    r = _res(m1, 1, "X3", sl=98.0, tp=110.0, tfx=tfx)
    assert r["reason"] == "dragon"
    exit_i = r["exit_i"]
    # exit bar must be the first M1 bar AFTER the triggering M15 close
    assert exit_i == tfx["m1_hi"][j_pb]

    # alter every M1 bar AFTER the exit bar, recompute M15+EMA, rerun
    m1b = {k: v.copy() for k, v in m1.items()}
    m1b["h"][exit_i + 1:] += 5.0
    m1b["c"][exit_i + 1:] += 5.0
    tfx_b = _tfx_from_m1(m1b)
    r2 = _res(m1b, 1, "X3", sl=98.0, tp=110.0, tfx=tfx_b)
    assert r2["exit_i"] == exit_i and r2["reason"] == "dragon"

    # alter the triggering M15 bar's close -> decision changes
    m1c = {k: v.copy() for k, v in m1.items()}
    m1c["c"][b] = band + 0.5                     # close back above band
    tfx_c = _tfx_from_m1(m1c)
    r3 = _res(m1c, 1, "X3", sl=98.0, tp=110.0, tfx=tfx_c)
    assert not (r3["reason"] == "dragon" and r3["exit_i"] == exit_i)


def test_t3_h1_suspect_last_bar_skips_check():
    """Under H1 an M15 bar whose last M1 is suspect is not evaluated."""
    m1, n15 = _ramp_m1()
    tfx0 = _tfx_from_m1(m1)
    j_pb = 35
    band = tfx0["e34l"][j_pb - 1]
    b = slice(j_pb * 15, (j_pb + 1) * 15)
    m1["c"][b] = band - 0.10
    m1["l"][b] = band - 0.11
    m1["h"][b] = band - 0.05
    m1["o"][b] = band - 0.07
    m1["suspect"][(j_pb + 1) * 15 - 1] = True    # last M1 of bar 35
    tfx = _tfx_from_m1(m1)
    r_h0 = _res(m1, 1, "X3", sl=98.0, tp=110.0, tfx=tfx, skip=False)
    r_h1 = _res(m1, 1, "X3", sl=98.0, tp=110.0, tfx=tfx, skip=True)
    assert r_h0["reason"] == "dragon"
    assert not (r_h1["reason"] == "dragon" and
                r_h1["exit_i"] == r_h0["exit_i"])
