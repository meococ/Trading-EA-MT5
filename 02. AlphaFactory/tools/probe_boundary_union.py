# Cadence ceiling: can the day-open fade trigger be broadened within the
# SAME mechanism logic (day-boundary liquidity-grab reversal) to reach
# 10/wk per symbol? Union variants: trigger window 00:00-02:00 server,
# lookback 3h/6h/12h, wick-vs-close pierce. Dedup events per day.
# Plus XAUUSD at its real day boundary (01:00 server).
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402
import MetaTrader5 as mt5  # noqa: E402

SYMS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIPS = {"USDJPY": 1e-2, "XAUUSD": 1e-1}
for s in SYMS + ["XAUUSD"]:
    PIPS.setdefault(s, 1e-4)
WANT_FROM = dt.datetime(2022, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)


def get_bars(sym):
    mt5.symbol_select(sym, True)
    out = {}
    anchor = END
    for _ in range(30):
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


def srv_min(ts):
    return (ts % 86400) // 60


def stats(v):
    n = len(v)
    if n < 15:
        return None
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
    return m, (m / (sd / math.sqrt(n)) if sd > 0 else 0.0), n


def union_scan(times, data, pip, open_min=0, win_bars=24,
               lookbacks=(36, 72, 144), nbars=48):
    """First bar in [open_min, open_min+win*5m) that pierces ANY lookback
    variant -> fade, entry next bar open, 4h. One event per server-day."""
    v, ts_l, per_day = [], [], {}
    for i in range(150, len(times) - nbars - 2):
        t = times[i]
        m = srv_min(t)
        if m < open_min or m >= open_min + win_bars * 5:
            continue
        dk = t // 86400
        if dk in per_day:
            continue
        d = 0
        for lb in lookbacks:
            if i < lb + 1:
                continue
            hi = max(data[times[j]][1] for j in range(i - lb, i))
            lo = min(data[times[j]][2] for j in range(i - lb, i))
            if data[t][1] > hi:
                d = 1; break
            if data[t][2] < lo:
                d = -1; break
        if d == 0:
            continue
        per_day[dk] = True
        o = data[times[i + 1]][0]
        v.append((data[times[i + 1 + nbars]][3] - o) * d / pip)
        ts_l.append(t)
    s = stats(v)
    if not s:
        return 0.0, 0, 0.0
    wk = s[2] / ((ts_l[-1] - ts_l[0]) / 604800.0) if len(ts_l) > 2 else 0
    mid = ts_l[len(ts_l) // 2]
    h1 = stats([x for x, t in zip(v, ts_l) if t <= mid])
    h2 = stats([x for x, t in zip(v, ts_l) if t > mid])
    flag = " consistent" if (h1 and h2 and h1[0] * h2[0] > 0) else ""
    print(f"    union n={s[2]:>4} ({wk:4.1f}/wk) fade={s[0]:+6.2f}p "
          f"(t={s[1]:+5.2f}){flag}")
    return s[0], s[2], wk


def by_hour_scan(times, data, pip, open_min=0, lookback=72, nbars=48):
    """Which hour in 00:00-03:00 carries the fade? Per-bar minute scan."""
    print("    per-30min-slot fade (lookback 6h):")
    for slot in range(0, 180, 30):
        v = []
        for i in range(80, len(times) - nbars - 2):
            t = times[i]
            m = srv_min(t)
            if m < slot or m >= slot + 30:
                continue
            hi = max(data[times[j]][1] for j in range(i - lookback, i))
            lo = min(data[times[j]][2] for j in range(i - lookback, i))
            d = 1 if data[t][1] > hi else (-1 if data[t][2] < lo else 0)
            if d == 0:
                continue
            o = data[times[i + 1]][0]
            v.append((data[times[i + 1 + nbars]][3] - o) * d / pip)
        s = stats(v)
        if s:
            print(f"      {slot//60:02d}:{slot%60:02d}-{slot//60:02d}:{(slot+30)%60:02d} "
                  f"n={s[2]:>4} fade={s[0]:+6.2f}p (t={s[1]:+5.2f})")


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
            print(f"\n##### {sym} #####")
            union_scan(times, data, pip, open_min=0, win_bars=24)
            by_hour_scan(times, data, pip)
        # XAUUSD at its real day boundary 01:00 server
        data = get_bars("XAUUSD")
        if data:
            times = sorted(data)
            print("\n##### XAUUSD (day boundary 01:00 srv) #####")
            union_scan(times, data, PIPS["XAUUSD"], open_min=60, win_bars=12)
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
