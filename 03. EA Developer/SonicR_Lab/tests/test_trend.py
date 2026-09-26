"""test_trend.py - ROUND 2E mandatory tests for the S_T score.

T1 no look-ahead: change every M1 bar AFTER the signal bar's close
(sig_ctm + 900), rebuild M15/H1/H4 and every EMA -> the score at t is
unchanged. Checked at M15 bars at the START, MIDDLE and END of an H1
bar and of an H4 bar, and at the Monday open.
Plus: no Sunday stub bar exists in the H1/H4 series.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from src import data as dm
from src import trend as td


def _small_m1(n_days=140, start_ctm=None):
    """Deterministic synthetic M1: random-walk-ish, Mon-Fri only,
    no Sunday bars (server convention)."""
    rng = np.random.default_rng(7)
    start = 1_577_833_200 if start_ctm is None else start_ctm
    bars = []
    t = start
    while len(bars) < n_days * 1440:
        wd = (t // 86400 + 3) % 7           # epoch 1970-01-01 = Thu
        if wd <= 4:                          # Mon..Fri
            bars.append(t)
        t += 60
    t = np.asarray(bars)
    n = len(t)
    c = 100 + np.cumsum(rng.normal(0, 0.02, n))
    o = np.concatenate(([c[0]], c[:-1]))
    h = np.maximum(o, c) + rng.uniform(0, 0.03, n)
    l = np.minimum(o, c) - rng.uniform(0, 0.03, n)
    return {"t": t, "o": o, "h": h, "l": l, "c": c,
            "tv": np.ones(n), "suspect": np.zeros(n, bool)}


def _score_of(tc, sig_ctm, dr):
    S, A1, A2, A3, valid = td.score_trades(
        tc, pd.DataFrame({"sig_ctm": [sig_ctm], "dir": [dr]}))
    return S[0], (A1[0], A2[0], A3[0]), bool(valid[0])


def test_t1_no_lookahead_positions():
    m1 = _small_m1()
    tc = td.build_trend_ctx(m1)
    t15 = tc["t15"]
    # pick M15 bars at start/mid/end of an H1 bar and an H4 bar,
    # plus the first Monday bar
    i_h1 = {k: None for k in ("start", "mid", "end")}
    i_h4 = {k: None for k in ("start", "mid", "end")}
    monday_i = None
    for i in range(td.WARM240 + 200, len(t15)):
        pos15 = (t15[i] % 3600) // 900            # 0..3 within the hour
        pos60 = (t15[i] % 14400) // 900           # 0..15 within 4h
        wd = (t15[i] // 86400 + 3) % 7
        if i_h1["start"] is None and pos15 == 0:
            i_h1["start"] = i
        if i_h1["mid"] is None and pos15 in (1, 2):
            i_h1["mid"] = i
        if pos15 == 3:
            i_h1["end"] = i
        if i_h4["start"] is None and pos60 == 0:
            i_h4["start"] = i
        if i_h4["mid"] is None and pos60 == 8:
            i_h4["mid"] = i
        if pos60 == 15:
            i_h4["end"] = i
        if monday_i is None and wd == 0 and t15[i] % 86400 == 0:
            monday_i = i
    picks = [i for i in list(i_h1.values()) + list(i_h4.values())
             + [monday_i] if i is not None]
    assert len(picks) >= 6
    for i in picks:
        sig = int(t15[i])
        for dr in (1, -1):
            s0, comp0, v0 = _score_of(tc, sig, dr)
            # alter every M1 bar AFTER the signal bar's close
            m1b = {k: v.copy() for k, v in m1.items()}
            cut = int(np.searchsorted(m1["t"], sig + 900))
            m1b["o"][cut:] += 3.0
            m1b["h"][cut:] += 3.0
            m1b["l"][cut:] += 3.0
            m1b["c"][cut:] += 3.0
            tcb = td.build_trend_ctx(m1b)
            s1, comp1, v1 = _score_of(tcb, sig, dr)
            assert v0 == v1 and (np.isnan(s0) and np.isnan(s1) or
                                 (s0 == s1 and comp0 == comp1)), \
                f"look-ahead at M15 idx {i} dir {dr}"


def test_no_sunday_stub_in_htf():
    m1 = _small_m1()
    tc = td.build_trend_ctx(m1)
    for tf in (tc["tf60"], tc["tf240"]):
        wd = (tf["t"] // 86400 + 3) % 7
        assert not (wd == 6).any()          # no Sunday opens
        assert not (wd == 5).any()          # no Saturday opens
        # mid-series bars are full length
        nm1 = tf["m1_hi"] - tf["m1_lo"]
        step = tf["minutes"]
        assert (nm1[1:-1] == step).all()


def test_no_sunday_stub_real():
    """Real data: any Sunday H1/H4 bar must be suspect-flagged AND must
    never be selected as a trade's usable HTF bar."""
    import pandas as pd
    m1 = dm.load_m1("EURUSD", dm.COMMON_START, dm.VALIDATION_END)
    tc = td.build_trend_ctx(m1)
    tr = pd.read_csv("out/trades_EURUSD_F2_NH_b.csv")
    sig = tr["sig_ctm"].to_numpy()
    for tf, step in ((tc["tf60"], 3600), (tc["tf240"], 14400)):
        wd = (tf["t"] // 86400 + 3) % 7
        sun = np.nonzero(wd == 6)[0]
        assert (tf["suspect"][sun]).all()    # every stub is suspect
        used = np.searchsorted(tf["t"] + step, sig + 900,
                               side="right") - 1
        assert not np.isin(used, sun).any()  # never a usable bar


def test_t1_no_lookahead_real():
    """Same as the synthetic T1 but on real EURUSD M1: pick real signal
    bars at the start/middle/end of their H1 and H4 bars plus a Monday
    open; score must be invariant to edits after sig_ctm + 900."""
    import pandas as pd
    m1 = dm.load_m1("EURUSD", dm.COMMON_START, dm.VALIDATION_END)
    tc = td.build_trend_ctx(m1)
    t15 = tc["t15"]
    tr = pd.read_csv("out/trades_EURUSD_F2_NH_b.csv")
    sigs = np.sort(tr["sig_ctm"].unique())
    picks = {}
    for s in sigs:
        i = int(np.searchsorted(t15, s))
        pos15 = (s % 3600) // 900
        pos60 = (s % 14400) // 900
        wd = (s // 86400 + 3) % 7
        for name, ok in (("h1_start", pos15 == 0), ("h1_end", pos15 == 3),
                         ("h4_start", pos60 == 0), ("h4_end", pos60 == 15),
                         ("monday", wd == 0 and s % 86400 < 86400)):
            if ok and name not in picks:
                picks[name] = i
    assert len(picks) >= 4
    for name, i in picks.items():
        sig = int(t15[i])
        for dr in (1, -1):
            s0, c0, v0 = _score_of(tc, sig, dr)
            m1b = {k: v.copy() for k, v in m1.items()}
            cut = int(np.searchsorted(m1["t"], sig + 900))
            m1b["c"][cut:] += 5.0
            m1b["h"][cut:] += 5.0
            tcb = td.build_trend_ctx(m1b)
            s1, c1, v1 = _score_of(tcb, sig, dr)
            assert v0 == v1 and (np.isnan(s0) and np.isnan(s1) or
                                 (s0 == s1 and c0 == c1)), name
