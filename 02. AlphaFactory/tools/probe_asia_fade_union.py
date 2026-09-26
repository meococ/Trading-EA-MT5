"""Stage-0 densification for the CONFIRMED Asia close-pierce fade.

Confirmed baseline (probe_retest_calendar Part A): first-hour (00-01GMT)
CLOSE pierce of prior-hour extreme -> immediate fade, exit 07:00GMT.
Net-positive on GBP/EUR/AUD/NZD/CAD/CHF at ~3.1-4.4/wk per symbol.

This probe tests densification variants of the SAME mechanism (not new
anomaly hunting): extend trigger window into hour 2 and vary the level.
  V1: baseline (hour1 pierce, prior-1h level)
  V2: hour1+hour2 pierce, prior-1h level
  V3: hour1 pierce, prior-2h level
  V4: hour1+hour2 pierce, prior-2h level
  V5: hour1 prior-1h  OR  hour2 pierce of hour-1 extreme (sequential)
All variants: enter at piercing-bar close equivalent (next-bar-open proxy
uses same-bar close — conservative), exit Asia end (07:00GMT close).
Also reports first/second-half mean split for stability.
"""
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

SYMS = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"]
PIPS = {"GBPUSD": 1e-4, "EURUSD": 1e-4, "USDJPY": 1e-2, "AUDUSD": 1e-4,
        "NZDUSD": 1e-4, "USDCAD": 1e-4, "USDCHF": 1e-4}
COST = 3.6
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
        if int(b[0][0]) <= dt.datetime(2022, 1, 1).timestamp():
            break
        time.sleep(0.3)
    return out or None


def gmt_min(ts):
    return (ts % 86400) // 60


def rep(tag, rets, days, mid_ts, rts):
    if len(rets) < 25:
        print(f"  {tag}: n={len(rets)} too few"); return
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / len(rets))
    t = m / (sd / math.sqrt(len(rets))) if sd > 0 else 0
    wk = len(rets) / (days / 7.0)
    a = [r for r, ts in zip(rets, rts) if ts <= mid_ts]
    b = [r for r, ts in zip(rets, rts) if ts > mid_ts]
    ma = sum(a) / len(a) if a else 0
    mb = sum(b) / len(b) if b else 0
    print(f"  {tag}: n={len(rets)} {wk:.1f}/wk mean={m:+.2f}p t={t:+.2f} "
          f"net={m - COST:+.2f}p | halves {ma:+.2f}/{mb:+.2f}")


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
            mid_ts = times[len(times) // 2]
            print(f"\n##### {sym} #####")
            v = {k: ([], []) for k in ("V1", "V2", "V3", "V4", "V5")}
            i = 30
            while i < len(times) - 5:
                t = times[i]
                if gmt_min(t) != 0:
                    i += 1; continue
                ph1 = max(data[times[i - k]][1] for k in range(1, 13))
                pl1 = min(data[times[i - k]][2] for k in range(1, 13))
                ph2 = max(data[times[i - k]][1] for k in range(1, 25))
                pl2 = min(data[times[i - k]][2] for k in range(1, 25))
                j = i
                while j < len(times) and gmt_min(times[j]) < 420:
                    j += 1
                if j <= i + 24:
                    i += 1; continue
                exit_px = data[times[j - 1]][3]

                hit1 = hit2 = hit3 = hit4 = 0
                e1 = e2 = e3 = e4 = 0.0
                seq_done = False
                for k in range(0, 24):          # first TWO hours
                    if i + k >= len(times) or times[i + k] - t != k * 300:
                        break
                    c = data[times[i + k]][3]
                    if k < 12:                  # hour 1
                        if hit1 == 0:
                            if c > ph1: hit1, e1 = -1, c
                            elif c < pl1: hit1, e1 = +1, c
                        if hit3 == 0:
                            if c > ph2: hit3, e3 = -1, c
                            elif c < pl2: hit3, e3 = +1, c
                    if hit2 == 0:               # hours 1-2
                        if c > ph1: hit2, e2 = -1, c
                        elif c < pl1: hit2, e2 = +1, c
                    if hit4 == 0:
                        if c > ph2: hit4, e4 = -1, c
                        elif c < pl2: hit4, e4 = +1, c
                    # V5: hour2 pierce of hour-1 extreme (running level)
                    if k == 11:
                        v5h = max(data[times[i - m]][1] for m in range(1, 13))
                        v5l = min(data[times[i - m]][2] for m in range(1, 13))
                    if k >= 12 and not seq_done and hit1 == 0:
                        hh = max(data[times[i + m]][1] for m in range(0, 12))
                        ll = min(data[times[i + m]][2] for m in range(0, 12))
                        if c > max(v5h, hh):
                            v["V5"][0].append(-(exit_px - c) / pip)
                            v["V5"][1].append(t); seq_done = True
                        elif c < min(v5l, ll):
                            v["V5"][0].append((exit_px - c) / pip)
                            v["V5"][1].append(t); seq_done = True
                if hit1:
                    v["V1"][0].append(hit1 * (exit_px - e1) / pip); v["V1"][1].append(t)
                if hit2:
                    v["V2"][0].append(hit2 * (exit_px - e2) / pip); v["V2"][1].append(t)
                if hit3:
                    v["V3"][0].append(hit3 * (exit_px - e3) / pip); v["V3"][1].append(t)
                if hit4:
                    v["V4"][0].append(hit4 * (exit_px - e4) / pip); v["V4"][1].append(t)
                if hit1 and not seq_done:
                    v["V5"][0].append(hit1 * (exit_px - e1) / pip); v["V5"][1].append(t)
                i = j
            for k in ("V1", "V2", "V3", "V4", "V5"):
                rep(k, v[k][0], days, mid_ts, v[k][1])
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
