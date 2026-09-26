"""Stage-0 probe: cross-asset lead-lag on M5 closed bars.

Question: does symbol A's closed-bar return predict symbol B's NEXT-bar
return? If a robust lag-1 relationship exists on any leader->follower
pair, a cross-asset information mechanism is viable; if all ~0, the
class dies cheap without minting an EA.

Pairs tested:
  XAUUSD -> EURUSD/GBPUSD/USDJPY   (gold-dollar basis hypothesis)
  EURUSD -> GBPUSD and reverse     (common-USD-leg co-movement)
  USDJPY -> EURUSD                 (risk-sentiment channel)
Sanity: same-bar correlation (alignment check) and M5 autocorrelation
of each leader (should be ~0 -> proves the test isn't just measuring
trend persistence).

Attach: governed isolate only, via factory_paths.mt5_initialize_kwargs.
"""
import sys, math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

SYMS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
PAIRS = [
    ("XAUUSD", "EURUSD"), ("XAUUSD", "GBPUSD"), ("XAUUSD", "USDJPY"),
    ("EURUSD", "GBPUSD"), ("GBPUSD", "EURUSD"), ("USDJPY", "EURUSD"),
    ("EURUSD", "USDJPY"), ("USDJPY", "XAUUSD"),
]
START = "2024-01-01T00:00:00Z"
END   = "2026-09-11T23:59:59Z"


def get_bars(sym):
    import datetime as dt, time
    mt5.symbol_select(sym, True)
    # copy_rates_range across the stub-filled early .hcc years returns empty;
    # walk back positionally from the end anchor in chunks instead.
    out = {}
    anchor = dt.datetime(2026, 9, 11)
    want_from = dt.datetime(2024, 1, 1).timestamp()
    for _ in range(20):
        b = mt5.copy_rates_from(sym, mt5.TIMEFRAME_M5, anchor, 30000)
        if b is None or len(b) == 0:
            break
        for x in b:
            out[int(x[0])] = float(x[4])
        anchor = dt.datetime.utcfromtimestamp(int(b[0][0]))
        if int(b[0][0]) <= want_from:
            break
        time.sleep(0.3)
    return out or None


def stats(xs, ys):
    n = len(xs)
    if n < 30:
        return None
    mx = sum(xs) / n; my = sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs); vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    rho = cov / math.sqrt(vx * vy)
    # directional: mean follower next-bar return conditioned on leader sign
    up = [y for x, y in zip(xs, ys) if x > 0]
    dn = [y for x, y in zip(xs, ys) if x < 0]
    mu = sum(up) / len(up) if up else 0.0
    md = sum(dn) / len(dn) if dn else 0.0
    return rho, mu, md, n


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        data = {}
        for s in SYMS:
            data[s] = get_bars(s)
            print(f"{s}: {len(data[s]) if data[s] else 0} bars")
        if any(data[s] is None for s in SYMS):
            print("missing history; run tester sync first"); return 2

        print("\n=== same-bar correlation (alignment sanity) ===")
        for a, b in PAIRS:
            ta, tb = data[a], data[b]
            common = sorted(set(ta) & set(tb))
            xs = [ta[t] for t in common]; ys = [tb[t] for t in common]
            # returns need prev close per symbol
            rx = [(xs[i] - xs[i-1]) / xs[i-1] for i in range(1, len(xs))]
            ry = [(ys[i] - ys[i-1]) / ys[i-1] for i in range(1, len(ys))]
            r = stats(rx, ry)
            if r:
                print(f"{a}->{b} same-bar rho={r[0]:+.4f} n={r[3]}")

        print("\n=== lag-1: leader bar t predicts follower bar t+1 ===")
        for a, b in PAIRS:
            ta, tb = data[a], data[b]
            times = sorted(set(ta) & set(tb))
            # follower needs bar at t and t+300 (next M5)
            rx, ry = [], []
            for i in range(1, len(times) - 1):
                t, tn = times[i], times[i] + 300
                if tn not in tb or times[i-1] not in ta:
                    continue
                rl = (ta[t] - ta[times[i-1]]) / ta[times[i-1]]
                rf = (tb[tn] - tb[t]) / tb[t]
                rx.append(rl); ry.append(rf)
            r = stats(rx, ry)
            if r:
                print(f"{a}->{b} lag1 rho={r[0]:+.4f} up_mean={r[1]*1e4:+.3f}p dn_mean={r[2]*1e4:+.3f}p n={r[3]}")

        print("\n=== leader M5 autocorrelation (sanity ~0) ===")
        for s in SYMS:
            t = data[s]; times = sorted(t)
            r1 = [(t[times[i]] - t[times[i-1]]) / t[times[i-1]] for i in range(1, len(times))]
            r2 = r1[1:]; r1 = r1[:-1]
            r = stats(r1, r2)
            if r:
                print(f"{s} auto-lag1 rho={r[0]:+.4f} n={r[3]}")

        print("\n=== thresholded: |leader move| > 0.5xATR-ish (0.1% ) -> follower next bar ===")
        for a, b in PAIRS:
            ta, tb = data[a], data[b]
            times = sorted(set(ta) & set(tb))
            ups, dns = [], []
            for i in range(20, len(times) - 1):
                t, tn = times[i], times[i] + 300
                if tn not in tb or times[i-1] not in ta:
                    continue
                rl = (ta[t] - ta[times[i-1]]) / ta[times[i-1]]
                if abs(rl) < 0.001:
                    continue
                rf = (tb[tn] - tb[t]) / tb[t]
                (ups if rl > 0 else dns).append(rf)
            if len(ups) > 50 and len(dns) > 50:
                mu = sum(ups) / len(ups); md = sum(dns) / len(dns)
                print(f"{a}->{b} big-move n_up={len(ups)} mean={mu*1e4:+.3f}p n_dn={len(dns)} mean={md*1e4:+.3f}p")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
