"""Stage-0 close-pierce variant map (past-only, lookahead-free).

Earlier probes: wick-pierce fades of prior extremes were noise/negative
everywhere EXCEPT the Asia first-hour CLOSE-pierce of the previous
hour's extreme (Leg-B style: +6.7p GBP t=6.1 at ~3/wk). Wicks are noise;
closes that pierce then revert carry the signal.

This probe maps the close-pierce fade across all session opens and two
level sources, strictly past-only:
  F1: prior-session last-hour extreme (12 bars before open)
  F2: prior-session FULL extreme (per BOUNDS window, strict prior day
      for ASIA)
Trigger: a CLOSE beyond the level during the open's first hour.
Exit: session end close.
"""
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

SYMS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD"]
PIPS = {"GBPUSD": 1e-4, "EURUSD": 1e-4, "USDJPY": 1e-2, "AUDUSD": 1e-4}
COST = 3.6
WANT_FROM = dt.datetime(2022, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)
BOUNDS = [
    ("ASIA", 0, 420, 720, 1200),
    ("LDN", 420, 960, 0, 420),
    ("NY", 720, 1200, 420, 720),
]


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
        time.sleep(0.3)
    return out or None


def gmt_min(ts):
    return (ts % 86400) // 60


def day_key(ts):
    return ts // 86400


def rep(tag, rets, days):
    if len(rets) < 25:
        print(f"  {tag}: n={len(rets)} too few"); return
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
    t = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
    wk = len(rets) / (days / 7.0)
    print(f"  {tag}: n={len(rets)} {wk:.1f}/wk mean={m:+.2f}p t={t:+.2f} net={m-COST:+.2f}p")


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        for sym in SYMS:
            data = get_bars(sym)
            if not data:
                continue
            times = sorted(data)
            pip = PIPS[sym]
            days = (times[-1] - times[0]) / 86400.0
            print(f"\n##### {sym} #####")
            for name, om, cm, pw0, pw1 in BOUNDS:
                f1, f2 = [], []
                i = 30
                while i < len(times) - 5:
                    t = times[i]
                    if gmt_min(t) != om:
                        i += 1; continue
                    dk = day_key(t)
                    ph1 = max(data[times[i - k]][1] for k in range(1, 13))
                    pl1 = min(data[times[i - k]][2] for k in range(1, 13))
                    if om == 0:
                        prior = [x for x in times
                                 if day_key(x) == dk - 1 and pw0 <= gmt_min(x) < pw1]
                    else:
                        prior = [x for x in times
                                 if day_key(x) == dk and pw0 <= gmt_min(x) < pw1]
                    ph2 = max((data[x][1] for x in prior), default=None)
                    pl2 = min((data[x][2] for x in prior), default=None)

                    h1 = h2 = 0
                    for k in range(0, 12):
                        if i + k >= len(times) or times[i + k] - t != k * 300:
                            break
                        c = data[times[i + k]][3]      # CLOSE pierce only
                        if h1 == 0:
                            if c > ph1: h1 = -1
                            elif c < pl1: h1 = +1
                        if ph2 is not None and h2 == 0:
                            if c > ph2: h2 = -1
                            elif c < pl2: h2 = +1

                    j = i
                    while j < len(times) and gmt_min(times[j]) < cm:
                        j += 1
                    if j <= i + 12:
                        i += 1; continue
                    exit_px = data[times[j - 1]][3]
                    entry_px = data[times[i + 11]][3]
                    if h1:
                        f1.append(h1 * (exit_px - entry_px) / pip)
                    if h2:
                        f2.append(h2 * (exit_px - entry_px) / pip)
                    i = j
                rep(f"{name}-F1(close pierce last-hour)", f1, days)
                rep(f"{name}-F2(close pierce prior-full)", f2, days)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
