"""Stage-0 final map: session-boundary anomaly table.

Two live anomalies found so far:
  A) US-session-extreme pierce at Asia open -> FADE (+8-19p, ~1.1/wk)
  B) NY last-2h move at Asia open -> FOLLOW/momentum (+2.5-8.9p, ~5/wk)

This probe completes the boundary map: for each session open, test BOTH
  MOM: prior session's last-2h move, FOLLOW direction (fire every day)
  FAD: prior session's FULL extreme pierced in first hour, FADE

Sessions: ASIA open 00:00 (prior=NY 12-20GMT), LDN open 07:00
(prior=ASIA 00-07), NY open 12:00 (prior=LDN 07-12 partial window
07:00-12:00 since LDN extends past NY open; prior-2h = 10:00-12:00).

Exit: session end close (ASIA 07:00, LDN 16:00, NY 20:00 GMT).
Symbols: GBPUSD EURUSD USDJPY AUDUSD. Window ~last 2y of M5.
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

# (open_min_gmt, close_min_gmt, prior_window_start_min, prior_window_end_min)
BOUNDS = [
    ("ASIA", 0, 420, 720, 1200),     # prior = prev NY 12:00-20:00
    ("LDN", 420, 960, 0, 420),       # prior = same-day ASIA 00:00-07:00
    ("NY", 720, 1200, 420, 720),     # prior = same-day LDN 07:00-12:00
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
        print(f"  {tag}: n={len(rets)} too few"); return 0.0
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
    t = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
    wk = len(rets) / (days / 7.0)
    print(f"  {tag}: n={len(rets)} {wk:.1f}/wk mean={m:+.2f}p t={t:+.2f} net={m-COST:+.2f}p")
    return m


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
                mom, fad = [], []
                i = 30
                while i < len(times) - 5:
                    t = times[i]
                    if gmt_min(t) != om:
                        i += 1; continue
                    dk = day_key(t)
                    # prior window bars (for ASIA prior it's prev day's NY)
                    prior = [x for x in times
                             if om == 0 and day_key(x) == dk - 1 and pw0 <= gmt_min(x) < pw1
                             or om != 0 and day_key(x) == dk and pw0 <= gmt_min(x) < pw1]
                    if len(prior) < 10:
                        i += 1; continue
                    ph = max(data[x][1] for x in prior)
                    pl = min(data[x][2] for x in prior)
                    p2h = [x for x in prior if gmt_min(x) >= pw1 - 120]
                    if om == 0:
                        p2h = [x for x in prior if gmt_min(x) >= 1080]
                    pmove = (data[p2h[-1]][3] - data[p2h[0]][0]) / pip if len(p2h) > 5 else 0.0

                    hit = 0
                    for k in range(0, 12):
                        if i + k >= len(times) or times[i + k] - t != k * 300:
                            break
                        b = data[times[i + k]]
                        if b[1] > ph: hit = -1; break
                        if b[2] < pl: hit = +1; break

                    j = i
                    while j < len(times) and gmt_min(times[j]) < cm:
                        j += 1
                    if j <= i + 12:
                        i += 1; continue
                    exit_px = data[times[j - 1]][3]
                    entry_px = data[times[i + 11]][3]
                    if hit:
                        fad.append(hit * (exit_px - entry_px) / pip)
                    if abs(pmove) > 0:
                        s = 1 if pmove > 0 else -1
                        mom.append(s * (exit_px - entry_px) / pip)
                    i = j
                rep(f"{name}-MOM(follow prior2h)", mom, days)
                rep(f"{name}-FAD(pierce prior-full)", fad, days)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
