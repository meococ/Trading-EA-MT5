# Day-boundary deep dive — is the 00:00-server conditional drift real,
# executable, and cost-survivable? Stage-0 only; no mechanism minted here.
#   Q1 weekday decomposition: Mon vs Tue-Fri vs Sun-open (week gap vs daily)
#   Q2 executable semantics: drift measured from NEXT bar open, not trigger bar
#   Q3 liquidity reality: bar-range proxy + direction of pre-drift interaction
#   Q4 horizon profile: where does the drift peak / decay (1h..8h)
#   Q5 post-0055 rebound: conditioned on prior dip or unconditional?
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402
import MetaTrader5 as mt5  # noqa: E402

SYMS = ["USDJPY", "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
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


def srv_dow(ts):
    # epoch day0=Thu; MT5 FX week: Sun 22:00 GMT open .. Fri 22:00 GMT close.
    # server-day index: 0=Sun 1=Mon .. 6=Sat (raw epoch day mapping)
    return int(((ts // 86400) + 4) % 7)  # 0=Sun,1=Mon,..,5=Fri,6=Sat


def stats(v):
    n = len(v)
    if n < 15:
        return None
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
    return m, (m / (sd / math.sqrt(n)) if sd > 0 else 0.0), n


def half_cons(vals, ts_l):
    if len(vals) < 30:
        return None
    mid = ts_l[len(ts_l) // 2]
    h1 = stats([v for v, t in zip(vals, ts_l) if t <= mid])
    h2 = stats([v for v, t in zip(vals, ts_l) if t > mid])
    if not h1 or not h2:
        return None
    return h1, h2


def fwd(times, data, i, nbars, entry_bar_open=False):
    """Drift + excursions forward nbars. entry at bar i open (or i+1 open)."""
    ie = i + 1 if entry_bar_open else i
    if ie >= len(times) - 1:
        return None
    o = data[times[ie]][0]
    up = dn = 0.0
    j_end = min(ie + nbars, len(times) - 1)
    for j in range(ie + 1, j_end + 1):
        h, l = data[times[j]][1], data[times[j]][2]
        up = max(up, h - o)
        dn = max(dn, o - l)
    return (data[times[j_end]][3] - o, up, dn)


def q1_weekday(times, data, pip):
    print("  Q1 pierce@00:00 drift by weekday (entry=next bar open, 4h):")
    by_dow = {}
    for i in range(80, len(times) - 60):
        t = times[i]
        if srv_min(t) != 0:
            continue
        hi = max(data[times[j]][1] for j in range(i - 72, i))
        lo = min(data[times[j]][2] for j in range(i - 72, i))
        h, l = data[t][1], data[t][2]
        d = 0
        if h > hi:
            d = 1
        elif l < lo:
            d = -1
        if d == 0:
            continue
        f = fwd(times, data, i, 48, entry_bar_open=True)
        if not f:
            continue
        by_dow.setdefault(srv_dow(t), []).append((f[0] * d / pip, t))
    for dw in sorted(by_dow):
        v = [x[0] for x in by_dow[dw]]
        s = stats(v)
        hc = half_cons(v, [x[1] for x in by_dow[dw]])
        mark = ""
        if hc and hc[0][0] * hc[1][0] > 0:
            mark = "  halves-consistent"
        nm = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][dw]
        if s:
            print(f"    {nm}: n={s[2]:>4} drift={s[0]:+6.2f}p (t={s[1]:+5.2f}){mark}")


def q2_exec(times, data, pip):
    print("  Q2 trigger-open vs next-bar-open drift (4h, all weekdays):")
    for tag, nbo in (("trigger-open", False), ("next-open", True)):
        v = []
        for i in range(80, len(times) - 60):
            t = times[i]
            if srv_min(t) != 0:
                continue
            hi = max(data[times[j]][1] for j in range(i - 72, i))
            lo = min(data[times[j]][2] for j in range(i - 72, i))
            d = 1 if data[t][1] > hi else (-1 if data[t][2] < lo else 0)
            if d == 0:
                continue
            f = fwd(times, data, i, 48, entry_bar_open=nbo)
            if f:
                v.append(f[0] * d / pip)
        s = stats(v)
        if s:
            print(f"    {tag:<14} n={s[2]:>4} drift={s[0]:+6.2f}p (t={s[1]:+5.2f})")


def q3_liquidity(times, data, pip):
    print("  Q3 bar-range liquidity proxy around boundary (pips):")
    for label, mn in (("23:55", 1435), ("00:00", 0), ("00:30", 30),
                      ("01:00", 60), ("07:00", 420), ("15:00", 900)):
        v = [abs(data[t][1] - data[t][2]) / pip
             for t in times if srv_min(t) == mn]
        s = stats(v)
        if s:
            print(f"    {label}: range={s[0]:5.2f}p (n={s[2]})")


def q4_horizon(times, data, pip):
    print("  Q4 drift horizon profile (entry=next open, all weekdays):")
    for nb, lab in ((12, "1h"), (24, "2h"), (48, "4h"), (96, "8h")):
        v = []
        for i in range(80, len(times) - 100):
            t = times[i]
            if srv_min(t) != 0:
                continue
            hi = max(data[times[j]][1] for j in range(i - 72, i))
            lo = min(data[times[j]][2] for j in range(i - 72, i))
            d = 1 if data[t][1] > hi else (-1 if data[t][2] < lo else 0)
            if d == 0:
                continue
            f = fwd(times, data, i, nb, entry_bar_open=True)
            if f:
                v.append(f[0] * d / pip)
        s = stats(v)
        if s:
            print(f"    {lab}: drift={s[0]:+6.2f}p (t={s[1]:+5.2f}) n={s[2]}")


def q5_rebound(times, data, pip):
    print("  Q5 00:55->01:55 drift conditioned on 00:00-00:55 move:")
    up, dn, flat = [], [], []
    for i in range(80, len(times) - 30):
        t = times[i]
        if srv_min(t) != 55:
            continue
        i0 = i - 11
        if i0 < 1 or i + 12 >= len(times):
            continue
        early = data[t][0] - data[times[i0]][0]
        f = data[times[i + 12]][3] - data[t][0]
        th = 2.0 * pip
        (up if early > th else dn if early < -th else flat).append(f / pip)
    for nm, v in (("early_up", up), ("early_dn", dn), ("early_flat", flat)):
        s = stats(v)
        if s:
            print(f"    {nm:<10} n={s[2]:>4} post_drift={s[0]:+6.2f}p (t={s[1]:+5.2f})")


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
            q1_weekday(times, data, pip)
            q2_exec(times, data, pip)
            q3_liquidity(times, data, pip)
            q4_horizon(times, data, pip)
            q5_rebound(times, data, pip)
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
