"""Known-answer tests for mk_m3_levels.resolve_event (REVIEW_2 F1).

Hand-made M1 paths through a fixed zone.  For each side (+1 support,
-1 resistance) we assert bounce/break labels, overshoot, and that the
outcome freezes at the resolution bar.  A verbatim copy of the PRE-FIX
barrier logic (legacy_resolve) must reproduce the F1 failure
(break-path labelled BOUNCE), proving the old code was wrong and the
new code is right on the same fixture.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mk_common as K                       # noqa: E402
from mk_m3_levels import resolve_event      # noqa: E402

BASE = 1672531200          # 2023-01-01 00:00 UTC (day boundary)
ZLO, ZHI = 1.10000, 1.10100
A = 0.00200                # ABR = 20 pips
TBAR = 10                  # touch M5 bar index
N5 = 120


def _mk(path_lo, path_hi):
    """Build m1/m5 dicts.  path_lo/path_hi: callable(j)->price for M1
    bars j >= start of resolution.  The touch M5 bar (TBAR) contains one
    M1 bar (j=52) intersecting the zone."""
    m5t = BASE + 300 * np.arange(N5)
    m1t = BASE + 60 * np.arange(5 * N5)
    h = np.full(5 * N5, 1.09980)
    l = np.full(5 * N5, 1.09990)
    c = np.full(5 * N5, 1.09985)
    # pre-touch bars sit just outside the zone (no intersection before
    # the touch minute so the scan picks j=52)
    a_end = 5 * TBAR + 5                     # M1 bars of M5-bar TBAR
    for j in range(5 * TBAR, a_end):
        if j == 52:
            h[j], l[j] = 1.10100, 1.09980    # the touch minute
        else:
            h[j], l[j] = 1.10040, 1.10020    # inside zone but not first
    for j in range(a_end, 5 * N5):
        lo, hi = path_lo(j), path_hi(j)
        h[j], l[j], c[j] = hi, lo, (hi + lo) / 2
    m1 = {"t": m1t, "h": h, "l": l, "c": c}
    m5 = {"t": m5t, "h": h[::5].copy(), "l": l[::5].copy(),
          "c": c[::5].copy()}
    return m1, m5


def _ev(side):
    return {"bar": TBAR, "side": side, "abr": A, "zlo": ZLO, "zhi": ZHI,
            "day": 0, "lid": 1}


def legacy_barrier_scan(m1, start, b, side, xs=(1.0,)):
    """Pre-fix logic verbatim: side=+1 barriers pointed inward, so both
    fire on the first scanned bar and the tie resolves to BOUNCE."""
    ev = {"zlo": ZLO, "zhi": ZHI}
    if side == -1:
        brk = {x: ev["zhi"] + x * A for x in xs}
        bnc = {x: ev["zlo"] - x * A for x in xs}
    else:                                   # THE BUG (D25 / F1)
        brk = {x: ev["zlo"] + x * A for x in xs}
        bnc = {x: ev["zhi"] - x * A for x in xs}
    fb = fn = None
    for i in range(start, b):
        hi, lo = m1["h"][i], m1["l"][i]
        if side == -1:
            if fb is None and hi >= brk[xs[0]]:
                fb = i
            if fn is None and lo <= bnc[xs[0]]:
                fn = i
        else:
            if fb is None and lo <= brk[xs[0]]:
                fb = i
            if fn is None and hi >= bnc[xs[0]]:
                fn = i
        if fb is not None and fn is not None:
            break
    if fb is None and fn is None:
        return "NONE"
    if fb is None:
        return "BOUNCE"
    if fn is None:
        return "BREAK"
    return "BREAK" if fb < fn else "BOUNCE"


def _start(m1, m5):
    m1t, m5t = np.asarray(m1["t"]), np.asarray(m5["t"])
    a, b = K.m1_window_for_bars(m1t, m5t, TBAR, min(len(m5t), TBAR + 48))
    a_end = int(np.searchsorted(m1t, m5t[TBAR] + 300, side="left"))
    start = a_end
    for j in range(a, a_end):
        if m1["l"][j] <= ZHI and m1["h"][j] >= ZLO:
            start = j + 1
            break
    return start, b


# --------------------------------------------------------------- tests
def test_support_break():
    """side=+1, path falls through zlo-1A -> BREAK (not BOUNCE)."""
    def lo(j):
        return 1.09850 - (j - 53) * 0.00010 if j >= 53 else 1.1000
    def hi(j):
        return 1.10060 - (j - 53) * 0.00005 if j >= 53 else 1.1000
    m1, m5 = _mk(lo, hi)
    res = resolve_event(m1, m5, _ev(+1), xs=(1.0, 2.0), horizon=48)
    assert res["out_x1"] == "BREAK", res["out_x1"]
    # legacy (pre-fix) labels the same path BOUNCE -> old code was wrong
    s, b = _start(m1, m5)
    assert legacy_barrier_scan(m1, s, b, +1) == "BOUNCE"


def test_support_bounce():
    """side=+1, path rises through zhi+1A -> BOUNCE."""
    def lo(j):
        return 1.10040 + (j - 53) * 0.00002 if j >= 53 else 1.1000
    def hi(j):
        return 1.10080 + (j - 53) * 0.00040 if j >= 53 else 1.1000
    m1, m5 = _mk(lo, hi)
    res = resolve_event(m1, m5, _ev(+1), xs=(1.0, 2.0), horizon=48)
    assert res["out_x1"] == "BOUNCE", res["out_x1"]


def test_resistance_break():
    """side=-1, path rises through zhi+1A -> BREAK."""
    def lo(j):
        return 1.10040 + (j - 53) * 0.00005 if j >= 53 else 1.1000
    def hi(j):
        return 1.10080 + (j - 53) * 0.00040 if j >= 53 else 1.1000
    m1, m5 = _mk(lo, hi)
    res = resolve_event(m1, m5, _ev(-1), xs=(1.0, 2.0), horizon=48)
    assert res["out_x1"] == "BREAK", res["out_x1"]


def test_resistance_bounce():
    """side=-1, path falls through zlo-1A -> BOUNCE."""
    def lo(j):
        return 1.10040 - (j - 53) * 0.00040 if j >= 53 else 1.1000
    def hi(j):
        return 1.10080 - (j - 53) * 0.00010 if j >= 53 else 1.1000
    m1, m5 = _mk(lo, hi)
    res = resolve_event(m1, m5, _ev(-1), xs=(1.0, 2.0), horizon=48)
    assert res["out_x1"] == "BOUNCE", res["out_x1"]


def test_no_resolution_none():
    """Price wanders +-0.5A inside barriers -> NONE."""
    def lo(j):
        return 1.09990 + 0.00020 * np.sin(j) if j >= 53 else 1.1000
    def hi(j):
        return 1.10060 + 0.00020 * np.sin(j) if j >= 53 else 1.1000
    m1, m5 = _mk(lo, hi)
    res = resolve_event(m1, m5, _ev(+1), xs=(1.0, 2.0), horizon=48)
    assert res["out_x1"] == "NONE", res["out_x1"]


def test_overshoot_support():
    """side=+1: a 0.0005 dip below zlo before the bounce -> overshoot
    = zlo - min_low = 0.0005."""
    def lo(j):
        if j == 55:
            return ZLO - 0.00050
        return 1.10040 + (j - 53) * 0.00002 if j >= 53 else 1.1000
    def hi(j):
        return 1.10080 + (j - 53) * 0.00040 if j >= 53 else 1.1000
    m1, m5 = _mk(lo, hi)
    res = resolve_event(m1, m5, _ev(+1), xs=(1.0, 2.0), horizon=48)
    assert res["out_x1"] == "BOUNCE"
    assert abs(res["overshoot_x1"] - 0.00050) < 1e-9, res["overshoot_x1"]


def test_freeze_at_resolution():
    """After the x1 break resolves, a later reversal must NOT change the
    outcome or the resolution bar."""
    def lo(j):
        if j >= 80:                      # hard reversal AFTER the break
            return 1.09900 + (j - 80) * 0.00050
        return 1.09850 - (j - 53) * 0.00010 if j >= 53 else 1.1000
    def hi(j):
        if j >= 80:
            return 1.09940 + (j - 80) * 0.00050
        return 1.10060 - (j - 53) * 0.00005 if j >= 53 else 1.1000
    m1, m5 = _mk(lo, hi)
    res = resolve_event(m1, m5, _ev(+1), xs=(1.0, 2.0), horizon=48)
    assert res["out_x1"] == "BREAK"
    # low first reaches zlo-1A=1.09800 at j=53+50=103? compute expected:
    # lo(j)=1.09850-0.0001*(j-53) <= 1.09800  ->  j-53 >= 5 -> j=58
    exp_m1 = 58
    exp_m5 = int(np.searchsorted(np.asarray(m5["t"]),
                                 int(m1["t"][exp_m1]), side="right") - 1)
    assert res["resbar_x1"] == exp_m5, (res["resbar_x1"], exp_m5)


def test_side_symmetry_rates():
    """Same mirrored path on both sides must give mirrored labels —
    the F1 fingerprint was a 98/64 asymmetry."""
    def dn_lo(j):
        return 1.10040 - (j - 53) * 0.00030 if j >= 53 else 1.1000
    def dn_hi(j):
        return 1.10080 - (j - 53) * 0.00020 if j >= 53 else 1.1000
    def up_lo(j):
        return 1.10040 + (j - 53) * 0.00020 if j >= 53 else 1.1000
    def up_hi(j):
        return 1.10080 + (j - 53) * 0.00030 if j >= 53 else 1.1000
    m1d, m5d = _mk(dn_lo, dn_hi)
    m1u, m5u = _mk(up_lo, up_hi)
    r_sup = resolve_event(m1d, m5d, _ev(+1), xs=(1.0, 2.0), horizon=48)
    r_res = resolve_event(m1d, m5d, _ev(-1), xs=(1.0, 2.0), horizon=48)
    assert r_sup["out_x1"] == "BREAK"     # support fails downward
    assert r_res["out_x1"] == "BOUNCE"    # resistance holds downward
    r_sup_u = resolve_event(m1u, m5u, _ev(+1), xs=(1.0, 2.0), horizon=48)
    r_res_u = resolve_event(m1u, m5u, _ev(-1), xs=(1.0, 2.0), horizon=48)
    assert r_sup_u["out_x1"] == "BOUNCE"
    assert r_res_u["out_x1"] == "BREAK"


if __name__ == "__main__":
    for f in list(v for k, v in list(globals().items())
                  if k.startswith("test_")):
        f()
    print("test_resolver: all pass")
