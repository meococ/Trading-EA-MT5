"""Synthetic fixture builder + debug for the VPA detector tests.

Builds a deterministic 60-bar M5 series on EURUSD-like scale (pip = 1e-4) that
contains one long pattern-break candidate: locked barrier from two touch highs,
a pressure leg, a tight buildup, and a close-break trigger.
"""

import sys

P = 1e-4  # pip


def build_series():
    o, h, l, c, u = [], [], [], [], []

    def add(op, cl, lo_extra, hi_extra, umin=600):
        o.append(op)
        c.append(cl)
        l.append(min(op, cl) - lo_extra)
        h.append(max(op, cl) + hi_extra)
        u.append(umin)

    base = 1.0980
    # 30 quiet oscillation bars (ATR ~2 pips)
    px = base
    for k in range(30):
        op = px
        cl = op + (0.00008 if k % 2 == 0 else -0.00006)
        add(op, cl, 0.00010, 0.00010)
        px = cl
    # rising run: 8 bars up to ~1.09960
    for k in range(8):
        op = px
        cl = op + 0.00020
        add(op, cl, 0.00004, 0.00004)
        px = cl
    # bar 38: approach high 1.09990
    add(px, px + 0.00020, 0.00005, 0.00010)
    px = c[-1]
    # bar 39: first touch high = 1.10000, close lower
    add(px, px - 0.00015, 0.00008, 0.00018)
    # bar 40: touch high 1.09999, close 1.09985
    add(c[-1], c[-1] - 0.00010, 0.00008, None if False else 0.00019)  # high = close+0.00019 -> 1.10004? tune below
    # bar 41: lower high
    add(c[-1], c[-1] - 0.00005, 0.00010, 0.00010)
    # bar 42: second touch high = 1.10000, closes low (rejection) -> pivot
    add(c[-1], c[-1] - 0.00005, 0.00012, 0.00019)
    # bars 43-47: pressure leg up from ~1.09970 to ~1.09995
    for k in range(5):
        op = c[-1]
        cl = op + 0.00006
        add(op, cl, 0.00003, 0.00003)
    # bars 48-53: tight buildup, closes in [B-0.7p, B+0.1p], highs near B at 50 & 52
    closes = [1.09994, 1.09995, 1.099960, 1.099970, 1.099980, 1.099990]
    lows = [1.09993, 1.099950, 1.099955, 1.099965, 1.099970, 1.099980]
    highs = [1.099960, 1.099965, 1.100000, 1.099985, 1.100000, 1.099995]
    for k in range(6):
        op = lows[k] + 0.000005
        add(op, closes[k], closes[k] - lows[k], max(highs[k] - max(op, closes[k]), 0.000005))
    # bar 54: trigger close-break
    add(1.100000, 1.100300, 0.00002, 0.00005)

    return {
        "symbol": "EURUSD",
        "t": [i * 300 for i in range(len(o))],
        "o": o, "h": h, "l": l, "c": c,
        "utc_min": u,
        "srv_min": u,
        "dow": [0] * len(o),
        "pip": P,
        "tick": P / 10.0,
    }


if __name__ == "__main__":
    sys.path.insert(0, ".")
    from vpa_core import run_detector

    bars = build_series()
    print("bars:", len(bars["t"]))
    for i in range(30, len(bars["c"])):
        print(i, f"o={bars['o'][i]:.5f} h={bars['h'][i]:.5f} l={bars['l'][i]:.5f} c={bars['c'][i]:.5f}")
    recs, cnt = run_detector(bars)
    print("records:", len(recs))
    for r in recs:
        print("  ", r.get("bar_idx"), r.get("setup"), r.get("side"), "exec=", r.get("executable"),
              r.get("skip_reason"), "n=", r.get("n"), "room=", r.get("room_pips"))
    print("counters:", cnt)
