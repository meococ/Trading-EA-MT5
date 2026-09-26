# Boundary universality: is the sweep-fade specific to 00:00 day-open,
# or does it fire at every session boundary? Decides cadence feasibility.
# Signed fade drift (next-bar-open entry) for pierces at:
#   00:00 srv (day open), 07:00 srv (LDN pre-open), 10:00 srv,
#   15:00 srv (NY/data), plus prior-day-high/low sweep at any hour,
# plus XAUUSD (in universe, not yet measured).
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402
import MetaTrader5 as mt5  # noqa: E402

SYMS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF",
        "USDJPY", "XAUUSD"]
PIPS = {"USDJPY": 1e-2, "XAUUSD": 1e-1}
for s in SYMS:
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


def fade_drift(times, data, i, lookback, nbars):
    """Signed drift against pierce direction, entry next bar open."""
    t = times[i]
    if i < lookback + 1 or i + 1 + nbars >= len(times):
        return None
    hi = max(data[times[j]][1] for j in range(i - lookback, i))
    lo = min(data[times[j]][2] for j in range(i - lookback, i))
    h, l = data[t][1], data[t][2]
    d = 1 if h > hi else (-1 if l < lo else 0)
    if d == 0:
        return None
    o = data[times[i + 1]][0]
    j_end = i + 1 + nbars
    return (data[times[j_end]][3] - o) * d, t


def scan_boundary(times, data, pip, name, minute, lookback, nbars):
    v, ts_l = [], []
    for i in range(lookback + 2, len(times) - nbars - 2):
        if srv_min(times[i]) != minute:
            continue
        r = fade_drift(times, data, i, lookback, nbars)
        if r:
            v.append(r[0] / pip)
            ts_l.append(r[1])
    s = stats(v)
    if not s:
        return 0
    mid = ts_l[len(ts_l) // 2]
    h1 = stats([x for x, t in zip(v, ts_l) if t <= mid])
    h2 = stats([x for x, t in zip(v, ts_l) if t > mid])
    flag = " halves-consistent" if (h1 and h2 and h1[0] * h2[0] > 0) else ""
    print(f"    {name:<28} n={s[2]:>4} fade={s[0]:+6.2f}p (t={s[1]:+5.2f}){flag}")
    return s[2]


def scan_dayhl(times, data, pip, nbars=48):
    """Sweep of PRIOR DAY high/low at any hour -> signed fade, 4h."""
    v, ts_l = [], []
    day_hl = {}
    for t in times:
        dk = t // 86400
        h, l = data[t][1], data[t][2]
        if dk not in day_hl:
            day_hl[dk] = [h, l]
        else:
            day_hl[dk][0] = max(day_hl[dk][0], h)
            day_hl[dk][1] = min(day_hl[dk][1], l)
    used = set()
    for i in range(300, len(times) - nbars - 2):
        t = times[i]
        dk = t // 86400
        ph, pl = day_hl.get(dk - 1, (None, None))
        if ph is None or dk in used:
            continue
        h, l = data[t][1], data[t][2]
        d = 1 if h > ph else (-1 if l < pl else 0)
        if d == 0:
            continue
        used.add(dk)                      # first day-HL sweep per day only
        o = data[times[i + 1]][0]
        v.append((data[times[i + 1 + nbars]][3] - o) * d / pip)
        ts_l.append(t)
    s = stats(v)
    if s:
        mid = ts_l[len(ts_l) // 2]
        h1 = stats([x for x, t in zip(v, ts_l) if t <= mid])
        h2 = stats([x for x, t in zip(v, ts_l) if t > mid])
        flag = " halves-consistent" if (h1 and h2 and h1[0] * h2[0] > 0) else ""
        print(f"    {'dayHL_sweep_any_hour':<28} n={s[2]:>4} "
              f"fade={s[0]:+6.2f}p (t={s[1]:+5.2f}){flag}")
    return s[2] if s else 0


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        for sym in SYMS:
            data = get_bars(sym)
            if not data:
                print(f"\n##### {sym} ##### NO DATA"); continue
            times = sorted(data)
            pip = PIPS[sym]
            print(f"\n##### {sym} ##### bars={len(times)}")
            # boundary pierces vs prior-6h range, fade measured 4h
            for nm, mn in (("day_open_0000", 0), ("ldn_pre_0700", 420),
                           ("mid_am_1000", 600), ("ny_1500", 900)):
                scan_boundary(times, data, pip, nm, mn, 72, 48)
            scan_dayhl(times, data, pip)
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
