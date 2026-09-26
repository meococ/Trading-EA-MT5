"""Deterministic synthetic M5 fixture for the DR1 detector tests.

Base series: one clean long Pattern-Break at B = 1.10120 (pip = 1e-4):
quiet base -> run-up -> touch 1 (rejection) -> dip (higher low) -> touch 2
(pivot) -> drifting tight buildup -> signal bar closing AT the barrier.
Mutations let each gate be broken independently.
"""

P = 1e-4


def build_dr1_series(mut=None):
    """mut: optional dict overriding arrays, e.g. {"close": {51: 1.10115}}."""
    o, h, l, c = [], [], [], []

    def add(op, hi, lo, cl):
        o.append(op); h.append(hi); l.append(lo); c.append(cl)

    # 30 quiet bars around 1.10080 (ranges ~7 pips -> ATR ~2.5-3 pips, no drift)
    px = 1.10080
    for k in range(30):
        op = px
        cl = op + (0.00010 if k % 2 == 0 else -0.00010)
        add(op, max(op, cl) + 0.00035, min(op, cl) - 0.00035, cl)
        px = cl
    # 12 rising bars, +0.875 pip each -> ~1.10175 (wide-ish ranges ~3.2 pips)
    for k in range(12):
        op = px
        cl = op + 0.0000875
        add(op, cl + 0.00015, op - 0.00015, cl)
        px = cl
    # index 42: touch 1 at B=1.10200, rejection close
    add(1.10185, 1.10200, 1.10172, 1.10186)
    # indices 43-45: dip to a higher low (wide bars keep the prior TR high)
    add(1.10186, 1.10196, 1.10166, 1.10174)
    add(1.10174, 1.10188, 1.10158, 1.10168)
    add(1.10168, 1.10184, 1.10168, 1.10174)
    # indices 46-47: back up
    add(1.10174, 1.10192, 1.10168, 1.10182)
    add(1.10182, 1.10200, 1.10176, 1.10190)
    # index 48: touch 2 at B (pivot; barrier locks at t=50)
    add(1.10190, 1.10200, 1.10184, 1.10196)
    # indices 49-64: tight buildup hugging B (closes 1.10194..1.10198, rising
    # lows; ranges ~2.2 pips so ATR stays ~2.4 and contraction ~0.7)
    for k in range(16):
        cl = 1.10194 + min(k, 4) * 0.00001
        op = cl - 0.00002
        add(op, min(cl + 0.00010, 1.10200), op - 0.00010, cl)
    # index 65: signal bar closes AT B, bullish
    add(1.10198, 1.10200, 1.10197, 1.10200)
    # indices 66-75: continuation bars AFTER the decision (so the full series is
    # longer than the prefix used by the prefix-invariance test)
    for k in range(10):
        op = 1.10200 + k * 0.00006
        cl = op + 0.00005
        add(op, cl + 0.00002, op - 0.00002, cl)

    n = len(o)
    if mut:
        for key, vals in mut.items():
            arr = {"o": o, "h": h, "l": l, "c": c}[key]
            for idx, v in vals.items():
                arr[idx] = v
    return {
        "symbol": "EURUSD",
        "t": [i * 300 for i in range(n)],
        "o": o, "h": h, "l": l, "c": c,
        "utc_min": [500] * n,          # 08:20 UTC -> EU session
        "srv_min": [500] * n,
        "dow": [0] * n,
        "pip": P,
        "tick": P / 10.0,
    }


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from vpa_dr1 import run_dr1

    bars = build_dr1_series()
    recs, cnt = run_dr1(bars)
    print("bars:", len(bars["t"]), "records:", len(recs))
    for r in recs:
        if r.get("executable") or r.get("bar_idx", 0) >= 45:
            print(r.get("bar_idx"), r.get("setup"), "side", r.get("side"),
                  "exec", r.get("executable"), r.get("skip_reason"),
                  "n", r.get("n"), "room_r", r.get("room_r"),
                  "slope", r.get("trend_slope"), "frac", r.get("frac_side"),
                  "squeeze", r.get("squeeze"))
    print("counters:", {k: v for k, v in sorted(cnt.items())})
