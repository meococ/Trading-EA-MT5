"""Stage-0 probe: session-level flow anomalies at WIDE geometry.

The M5-tight geometry is structurally dead on MQ-Demo costs (~45% of
risk eaten per RT). This probe measures the raw directional expectancy
of session-anchored anomalies when held to session END (wide geometry,
~2-8h holds, risk in H1-ATR terms where cost drag is ~5-10%).

Legs measured independently (each needs raw edge to justify a slot in
a session-flow composite; a leg with no edge stays out):

  A) Session momentum (Gao-Han-Li-Zhou intraday momentum, session
     variant): first `open_bars` M5 bars' net return, in ATR units,
     predicts direction of the REST of the session.
  B) Handover fade: prior session's last-hour extreme, if pierced in
     the new session's first hour, fades back toward the prior
     session's midpoint by session end.
  C) Post-fix drift: the 15:00-16:00 GMT move (pre-WM/R flow) reverses
     after 16:00 GMT (post-fix window 16:00-17:00).

All reads are CLOSED bars. Output: per leg/session/symbol event count,
mean next-leg return in trade direction (ATR units + pips), and rough
expectancy minus measured round-trip cost.

Attach: governed isolate via factory_paths.mt5_initialize_kwargs.
"""
import sys, math, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

SYMS = ["GBPUSD", "USDJPY", "EURUSD"]
SESS = [("ASIA", 0, 7), ("LDN", 7, 16), ("NY", 12, 20)]
WANT_FROM = dt.datetime(2024, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)
COST_PIPS = {"GBPUSD": 3.8, "USDJPY": 3.4, "EURUSD": 3.6}  # RT est incl comm


def get_bars(sym):
    mt5.symbol_select(sym, True)
    out = {}
    anchor = END
    for _ in range(25):
        b = mt5.copy_rates_from(sym, mt5.TIMEFRAME_M5, anchor, 30000)
        if b is None or len(b) == 0:
            break
        for x in b:
            out[int(x[0])] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        anchor = dt.datetime.utcfromtimestamp(int(b[0][0]))
        if int(b[0][0]) <= WANT_FROM:
            break
        import time; time.sleep(0.3)
    return out or None


def atr14(times, data, i, pip):
    if i < 15:
        return None
    s = 0.0
    for j in range(i - 14, i):
        h, l = data[times[j]][1], data[times[j]][2]
        s += h - l
    return s / 14 / pip


def gmt_min(ts):
    return (ts % 86400) // 60


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        pips = {"GBPUSD": 1e-4, "USDJPY": 1e-2, "EURUSD": 1e-4}
        for sym in SYMS:
            data = get_bars(sym)
            if not data:
                print(f"{sym}: no bars"); continue
            times = sorted(data)
            pip = pips[sym]
            print(f"\n########## {sym}: {len(times)} bars ##########")

            # ---------- Leg A: session momentum ----------
            # first 6 closed M5 bars of session (30min) -> rest of session
            print("--- A) session momentum (first-30min sign -> session end) ---")
            for name, oh, ch in SESS:
                rets = []
                i = 15
                while i < len(times) - 5:
                    t = times[i]
                    if gmt_min(t) != oh * 60:
                        i += 1; continue
                    # need 6 contiguous OR bars
                    seq = [times[i + k] for k in range(7)
                           if i + k < len(times) and times[i + k] - t == k * 300]
                    if len(seq) < 7:
                        i += 1; continue
                    a = atr14(times, data, i, pip)
                    if not a:
                        i += 1; continue
                    r0 = (data[seq[5]][3] - data[seq[0]][0]) / pip
                    if abs(r0) < 0.25 * a:
                        i += 1; continue
                    # exit: last bar with gmt_min < ch*60
                    j = i + 6
                    while j < len(times) and gmt_min(times[j]) < ch * 60:
                        j += 1
                    if j <= i + 6:
                        i += 1; continue
                    exit_px = data[times[j - 1]][3]
                    entry_px = data[seq[6]][0]
                    ret = (exit_px - entry_px) / pip
                    rets.append(ret if r0 > 0 else -ret)
                    i = j
                if len(rets) > 30:
                    m = sum(rets) / len(rets)
                    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
                    tstat = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
                    net = m - COST_PIPS[sym]
                    print(f"  {name}: n={len(rets)} mean={m:+.2f}p t={tstat:+.2f} net_cost={net:+.2f}p")

            # ---------- Leg C: post-fix drift ----------
            print("--- C) post-WM/R-fix reversal (15-16GMT move -> 16-17GMT) ---")
            rets = []
            i = 15
            while i < len(times) - 5:
                t = times[i]
                if gmt_min(t) != 15 * 60:
                    i += 1; continue
                a = atr14(times, data, i, pip)
                if not a:
                    i += 1; continue
                # find bar at 16:00 and 17:00
                t16 = t + 3600; t17 = t + 7200
                if t16 not in data or t17 not in data:
                    i += 12; continue
                pre = (data[t16 - 300][3] - data[t][0]) / pip
                if abs(pre) < 0.3 * a:
                    i += 12; continue
                post = (data[t17][3] - data[t16][0]) / pip
                rets.append(-post if pre > 0 else post)  # fade the pre-fix move
                i += 12
            if len(rets) > 20:
                m = sum(rets) / len(rets)
                sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
                tstat = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
                net = m - COST_PIPS[sym]
                print(f"  FIX-fade: n={len(rets)} mean={m:+.2f}p t={tstat:+.2f} net={net:+.2f}p")
            else:
                print(f"  FIX-fade: n={len(rets)} (too few)")

            # ---------- Leg B: handover fade ----------
            print("--- B) session-handover fade (prior sess last-hour extreme pierce -> mid) ---")
            for name, oh, ch in SESS:
                rets = []
                i = 30
                while i < len(times) - 5:
                    t = times[i]
                    if gmt_min(t) != oh * 60:
                        i += 1; continue
                    # prior 12 bars = last hour of previous session
                    ph = max(data[times[i - k]][1] for k in range(1, 13))
                    pl = min(data[times[i - k]][2] for k in range(1, 13))
                    pm = (ph + pl) / 2
                    a = atr14(times, data, i, pip)
                    if not a:
                        i += 1; continue
                    # first-hour pierce check happens on bars i..i+11
                    sig = 0
                    for k in range(0, 12):
                        if i + k >= len(times) or times[i + k] - t != k * 300:
                            break
                        c = data[times[i + k]][3]
                        if c > ph:
                            sig = -1; break      # pierced high -> fade short
                        if c < pl:
                            sig = +1; break      # pierced low -> fade long
                    if sig == 0:
                        i += 12; continue
                    # exit at session end
                    j = i
                    while j < len(times) and gmt_min(times[j]) < ch * 60:
                        j += 1
                    if j <= i + 12:
                        i += 12; continue
                    ret = sig * (data[times[j - 1]][3] - data[times[i + k]][3]) / pip
                    rets.append(ret)
                    i = j
                if len(rets) > 30:
                    m = sum(rets) / len(rets)
                    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
                    tstat = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
                    net = m - COST_PIPS[sym]
                    print(f"  {name}: n={len(rets)} mean={m:+.2f}p t={tstat:+.2f} net={net:+.2f}p")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
