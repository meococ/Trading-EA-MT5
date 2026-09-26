# Market physics characterization — Stage-0 deep research.
# Measures baseline opportunity structure BEFORE any mechanism design:
#   S1 opportunity map   : forward excursion vs cost, by hour-of-week x symbol
#   S2 autocorrelation   : M5 return autocorr by session and vol regime
#   S3 conditional edge  : E[excursion | trigger] - E[excursion | same hour]
#                          for generic trigger classes (pierce / big-bar /
#                          quiet-break / week-open gap)
#   S4 regime transitions: squeeze (low ATR pctile) -> expansion excursion
#   S5 forced-flow events: Tokyo fix, London fix, rollover, week-open
# Discipline: split-half sign consistency + scan-size aware t-threshold.
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402
import MetaTrader5 as mt5  # noqa: E402

SYMS = ["USDJPY", "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
COST_RT = 3.6                       # conservative RT pips, MQ-Demo
WANT_FROM = dt.datetime(2022, 1, 1).timestamp()
END = dt.datetime(2026, 9, 11)
H_FWD = [12, 48]                    # forward windows: 1h and 4h in M5 bars
SCANNED_CELLS = 0                   # multiple-testing counter


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


def gmt_min(ts):
    return (ts % 86400) // 60


def hour_of_week(ts):
    d = (ts // 86400 + 4) % 7        # epoch day0 = Thursday -> 0=Mon..6=Sun
    return int(d * 24 + (ts % 86400) // 3600)


def stats(v):
    n = len(v)
    if n < 20:
        return None
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
    return m, (m / (sd / math.sqrt(n)) if sd > 0 else 0.0), n


def half_consistent(vals, ts_list):
    """Split-half sign consistency: same sign and both halves n>=20."""
    mid = ts_list[len(ts_list) // 2]
    h1 = [v for v, t in zip(vals, ts_list) if t <= mid]
    h2 = [v for v, t in zip(vals, ts_list) if t > mid]
    s1, s2 = stats(h1), stats(h2)
    if not s1 or not s2:
        return None
    if (s1[0] > 0) == (s2[0] > 0):
        return s1, s2
    return (s1, s2)


def fwd_excursion(times, data, i, nbars):
    """Return (max_up_pips_equiv, max_dn, close_move) over next nbars from bar i open."""
    t = times[i]
    o = data[t][0]
    up = dn = 0.0
    j_end = min(i + nbars, len(times) - 1)
    for j in range(i + 1, j_end + 1):
        h, l = data[times[j]][1], data[times[j]][2]
        up = max(up, h - o)
        dn = max(dn, o - l)
    c = data[times[j_end]][3] - o
    return up, dn, c


def atr_series(times, data, pip, n=288):
    """Lightweight ATR proxy: rolling mean of |close-prev close| over n bars, in pips."""
    atr = {}
    acc = 0.0
    q = []
    for i, t in enumerate(times):
        if i == 0:
            continue
        r = abs(data[t][3] - data[times[i - 1]][3]) / pip
        q.append(r)
        acc += r
        if len(q) > n:
            acc -= q.pop(0)
        atr[t] = acc / len(q) if q else 0.0
    return atr


def study_opportunity(sym, times, data, pip):
    """S1: E[max directional excursion] and |move| by hour-of-week, 1h+4h."""
    up = {}; dn = {}; mv = {}
    for i in range(len(times) - 50):
        t = times[i]
        if data[t][0] <= 0:
            continue
        hw = hour_of_week(t)
        u1, d1, c1 = fwd_excursion(times, data, i, H_FWD[0])
        u4, d4, c4 = fwd_excursion(times, data, i, H_FWD[1])
        e1 = max(u1, d1) / pip
        e4 = max(u4, d4) / pip
        up.setdefault(hw, []).append(e1)
        mv.setdefault(hw, []).append((abs(c4) / pip, e4))
    print(f"  S1 top hours by 1h max-excursion (cost {COST_RT}p):")
    ranked = sorted(up.items(), key=lambda kv: -sum(kv[1]) / len(kv[1]))
    for hw, v in ranked[:6]:
        m = sum(v) / len(v)
        e4m = sum(x[1] for x in mv[hw]) / len(mv[hw])
        print(f"    h{hw:>3} ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][hw//24]} {hw%24:02d}h) "
              f"exc1h={m:6.1f}p exc4h={e4m:6.1f}p cost/exc1h={COST_RT/m:4.0%}")
    med = sorted(sum(up.values(), []))[len(up) // 2]
    print(f"    median-hour exc1h={med:5.1f}p")


def study_autocorr(sym, times, data, pip):
    """S2: lag-1..12 M5 return autocorr overall + by session + vol regime."""
    rets = []
    for i in range(1, len(times)):
        t0, t1 = times[i - 1], times[i]
        if t1 - t0 != 300:
            rets.append(0.0)
            continue
        o, c = data[t1][0], data[t1][3]
        rets.append((c - o) / pip)
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / n
    if var <= 0:
        return
    print("  S2 return autocorr (lag, rho):")
    out = []
    for lag in (1, 2, 3, 6, 12):
        cov = sum((rets[i] - mean) * (rets[i - lag] - mean) for i in range(lag, n)) / (n - lag)
        out.append(f"lag{lag}={cov / var:+.4f}")
    print("    " + " ".join(out))


def study_conditional(sym, times, data, pip, atr):
    """S3: E[fwd excursion | trigger] - E[same | hour-of-week baseline]."""
    base = {}
    for i in range(len(times) - 50):
        t = times[i]
        u, d, c = fwd_excursion(times, data, i, H_FWD[1])
        base.setdefault(hour_of_week(t), []).append((max(u, d), c, u - d))
    bmean = {k: (sum(x[0] for x in v) / len(v),
                 sum(x[1] for x in v) / len(v),
                 sum(x[2] for x in v) / len(v)) for k, v in base.items()}

    def run(name, trigger):
        global SCANNED_CELLS
        SCANNED_CELLS += 1
        exc, dr, ts_l, sgn = [], [], [], []
        for i in range(60, len(times) - 50):
            t = times[i]
            if not trigger(i, t):
                continue
            u, d, c = fwd_excursion(times, data, i, H_FWD[1])
            bw = bmean[hour_of_week(t)]
            exc.append(max(u, d) / pip - bw[0] / pip)
            dr.append(c / pip - bw[1] / pip)
            sgn.append((u - d) / pip - bw[2] / pip)
            ts_l.append(t)
        se = stats(exc)
        sd = stats(dr)
        ss = stats(sgn)
        if not se or not sd:
            return
        hc = half_consistent(dr, ts_l)
        flag = ""
        if hc and (hc[0][0] > 0) == (hc[1][0] > 0):
            flag = "  <== consistent" if abs(sd[1]) > 2.0 else ""
        print(f"    {name:<22} n={se[2]:>5} dExc={se[0]:+6.2f}p (t={se[1]:+5.2f}) "
              f"dDrift={sd[0]:+6.2f}p (t={sd[1]:+5.2f}) dSign={ss[0]:+6.2f}p{flag}")

    print("  S3 conditional-vs-baseline (4h fwd):")
    sess_open = {"ASIA": 0, "LDN": 420, "NY": 720}

    def mk_pierce(open_min, lookback_bars):
        def trig(i, t):
            if gmt_min(t) != open_min:
                return False
            hi = max(data[times[j]][1] for j in range(i - lookback_bars, i))
            lo = min(data[times[j]][2] for j in range(i - lookback_bars, i))
            o, h, l = data[t][0], data[t][1], data[t][2]
            return h > hi or l < lo
        return trig

    for nm, om in sess_open.items():
        run(f"pierce_{nm}_6h", mk_pierce(om, 72))

    def bigbar(i, t):
        a = atr.get(t)
        if not a or a <= 0:
            return False
        r = (data[t][3] - data[t][0]) / pip
        return abs(r) > 2.0 * a
    run("bigbar_2xATR", bigbar)

    def quiet_break(i, t):
        a = atr.get(t)
        if not a:
            return False
        hist = sorted(atr.get(times[j], 0) for j in range(max(0, i - 2000), i))
        if len(hist) < 500:
            return False
        pct = sum(1 for x in hist if x <= a) / len(hist)
        if pct > 0.15:
            return False
        hi = max(data[times[j]][1] for j in range(i - 24, i))
        lo = min(data[times[j]][2] for j in range(i - 24, i))
        return data[t][1] > hi or data[t][2] < lo
    run("squeeze_break_15pct", quiet_break)

    def week_open(i, t):
        return gmt_min(t) == 0 and hour_of_week(t) < 24 and i >= 1
    run("week_open", week_open)


def study_regime(sym, times, data, pip, atr):
    """S4: ATR-percentile regime -> forward excursion."""
    hist = sorted(v for v in atr.values() if v > 0)
    if len(hist) < 5000:
        return
    q = [hist[int(len(hist) * p)] for p in (0.1, 0.25, 0.75, 0.9)]
    buckets = {k: [] for k in ("q<10", "10-25", "25-75", "75-90", ">90")}
    for i in range(300, len(times) - 50):
        t = times[i]
        a = atr.get(t)
        if not a or a <= 0:
            continue
        u, d, c = fwd_excursion(times, data, i, H_FWD[1])
        e = max(u, d) / pip
        k = ("q<10" if a <= q[0] else "10-25" if a <= q[1] else
             "25-75" if a <= q[2] else "75-90" if a <= q[3] else ">90")
        buckets[k].append((e, abs(c) / pip))
    print("  S4 ATR regime -> 4h excursion / realized |move|:")
    for k, v in buckets.items():
        if v:
            print(f"    {k:>6}: n={len(v):>6} exc={sum(x[0] for x in v)/len(v):6.1f}p "
                  f"|move4h|={sum(x[1] for x in v)/len(v):6.1f}p")


def study_events(sym, times, data, pip):
    """S5: forced-flow windows: pre/post fix drift."""
    def window_stats(label, center_min, pre, post):
        global SCANNED_CELLS
        SCANNED_CELLS += 1
        pre_r, post_r = [], []
        for i in range(60, len(times) - 60):
            t = times[i]
            if gmt_min(t) != center_min:
                continue
            o = data[t][0]
            j_pre = i - pre // 5
            j_post = i + post // 5
            if j_pre < 0 or j_post >= len(times):
                continue
            pre_r.append((o - data[times[j_pre]][3]) / pip)
            post_r.append((data[times[j_post]][3] - o) / pip)
        sp, sq = stats(pre_r), stats(post_r)
        if sp and sq:
            print(f"    {label:<18} n={sp[2]:>4} pre{pre}m={sp[0]:+6.2f}p (t={sp[1]:+5.2f}) "
                  f"post{post}m={sq[0]:+6.2f}p (t={sq[1]:+5.2f})")
    print("  S5 forced-flow events (drift into vs after):")
    window_stats("tokyo_fix_0055", 55, 60, 60)
    window_stats("london_fix_1500", 900, 60, 60)
    window_stats("ny_10am_1500", 900, 30, 30)
    window_stats("rollover_2100", 1260, 30, 30)


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
            print(f"\n##### {sym} ##### bars={len(times)} "
                  f"days={(times[-1]-times[0])/86400:.0f}")
            atr = atr_series(times, data, pip)
            study_opportunity(sym, times, data, pip)
            study_autocorr(sym, times, data, pip)
            study_conditional(sym, times, data, pip, atr)
            study_regime(sym, times, data, pip, atr)
            study_events(sym, times, data, pip)
        print(f"\n[scan] cells measured ~{SCANNED_CELLS} per symbol")
    finally:
        mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
