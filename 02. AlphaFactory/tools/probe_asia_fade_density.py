"""Stage-0 densification probe: ASIA-open fade of prior-extreme pierce.

Baseline probe found: at Asia session open (00:00 GMT), a first-hour
pierce of the prior session's last-hour extreme fades back with a
strong edge (GBP +6.7p t=6.2, EUR +4.7p t=4.7, n~265 over ~2.6y ->
~2/wk). Frequency fails the 10-40/wk band alone.

This probe tests whether the edge densifies without diluting:

  V1 baseline : pierce of prior-session last-hour extreme, first 1h
  V2          : pierce of prior-session FULL extreme, first 1h
  V3          : pierce of prior-day high/low, first 1h
  V4          : contra-momentum, first-hour move >0.4xATR, no level
  V5          : V1 trigger but 2h window
  UNION       : any of V1/V2/V3 (dedup by day)

Exit for all: Asia session end (07:00 GMT) close.
Metrics: events/week, mean fade-direction return pips, t-stat,
net vs ~3.6p RT cost. Symbols: GBPUSD EURUSD USDJPY AUDUSD.

Attach: governed isolate via factory_paths.mt5_initialize_kwargs.
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


def atr14(times, data, i, pip):
    if i < 15:
        return None
    s = sum(data[times[j]][1] - data[times[j]][2] for j in range(i - 14, i))
    return s / 14 / pip


def report(tag, rets, days):
    if len(rets) < 25:
        print(f"  {tag}: n={len(rets)} too few")
        return
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
    t = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
    wk = len(rets) / (days / 7.0)
    print(f"  {tag}: n={len(rets)} {wk:.1f}/wk mean={m:+.2f}p t={t:+.2f} net={m - COST:+.2f}p")


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        for sym in SYMS:
            data = get_bars(sym)
            if not data:
                print(f"{sym}: no bars"); continue
            times = sorted(data)
            pip = PIPS[sym]
            days = (times[-1] - times[0]) / 86400.0
            print(f"\n########## {sym} bars={len(times)} days={days:.0f} ##########")

            # Pre-group bars by day for day-extreme lookups.
            by_day = {}
            for t in times:
                by_day.setdefault(day_key(t), []).append(t)

            V = {k: [] for k in ("V1", "V2", "V3", "V4", "V5", "UNION")}
            i = 30
            while i < len(times) - 5:
                t = times[i]
                if gmt_min(t) != 0:           # Asia open 00:00 GMT
                    i += 1; continue
                a = atr14(times, data, i, pip)
                if not a:
                    i += 1; continue

                dk = day_key(t)
                # prior-session last-hour extreme (prev 12 bars)
                ph1 = max(data[times[i - k]][1] for k in range(1, 13))
                pl1 = min(data[times[i - k]][2] for k in range(1, 13))
                # prior-session FULL extreme: NY 12:00-20:00 GMT prev day
                prev_ny = [x for x in times
                           if dk - 1 <= day_key(x) <= dk and 720 <= gmt_min(x) < 1200]
                ph2 = max((data[x][1] for x in prev_ny), default=None)
                pl2 = min((data[x][2] for x in prev_ny), default=None)
                # prior-day extreme
                prev_day = by_day.get(dk - 1, [])
                ph3 = max((data[x][1] for x in prev_day), default=None)
                pl3 = min((data[x][2] for x in prev_day), default=None)

                # first-hour (12 bars) and first-2h (24 bars) scans
                hit1 = hit2 = hit3 = hit5 = 0
                move1h = 0.0
                for k in range(0, 24):
                    if i + k >= len(times) or times[i + k] - t != k * 300:
                        break
                    b = data[times[i + k]]
                    if k == 11:
                        move1h = (b[3] - data[t][0]) / pip
                    if hit1 == 0:
                        if b[1] > ph1: hit1 = -1
                        elif b[2] < pl1: hit1 = +1
                    if ph2 is not None and hit2 == 0:
                        if b[1] > ph2: hit2 = -1
                        elif b[2] < pl2: hit2 = +1
                    if ph3 is not None and hit3 == 0:
                        if b[1] > ph3: hit3 = -1
                        elif b[2] < pl3: hit3 = +1
                    if k < 12 and hit5 == 0:
                        if b[1] > ph1: hit5 = -1
                        elif b[2] < pl1: hit5 = +1

                # exit: last Asia bar (<07:00) close
                j = i
                while j < len(times) and gmt_min(times[j]) < 420:
                    j += 1
                if j <= i + 12:
                    i += 1; continue
                exit_px = data[times[j - 1]][3]
                entry_px = data[times[i + 11]][3]  # enter ~end of first hour

                if hit1: V["V1"].append(hit1 * (exit_px - entry_px) / pip)
                if hit2: V["V2"].append(hit2 * (exit_px - entry_px) / pip)
                if hit3: V["V3"].append(hit3 * (exit_px - entry_px) / pip)
                if hit5: V["V5"].append(hit5 * (exit_px - entry_px) / pip)
                if abs(move1h) > 0.4 * a:
                    V["V4"].append((-1 if move1h > 0 else 1) * (exit_px - entry_px) / pip)
                u = hit1 or hit2 or hit3
                if u: V["UNION"].append(u * (exit_px - entry_px) / pip)
                i = j

            for k in ("V1", "V2", "V3", "V5", "UNION", "V4"):
                report(k, V[k], days)
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
