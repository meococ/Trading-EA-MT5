"""Stage-0 final scan: retest-entry quality + conditional-calendar drift.

Part A — RETEST entry for the one confirmed anomaly (close-pierce fade):
after a first-hour CLOSE pierces the prior-hour extreme, enter via LIMIT at
the level (filled only if price retraces to it before session end). Compares
IMMEDIATE (piercing close) vs RETEST entry: expectancy, fill rate, per-trade
edge. Sessions: ASIA (00-07GMT), LDN (07-16GMT), NY (12-20GMT).

Part B — CALENDAR scan (the last unexplored anomaly class):
H1 bar drift conditioned on hour-of-week (168 cells/symbol), day-of-week D1
drift (5 cells/symbol). Split-half validation: a cell must have the SAME
sign and |t|>2.8 in BOTH halves (~p 2.6e-5 joint -> survives ~1400 tests).
Reports passing cells and same-sign adjacent-hour chains (candidate windows).
"""
import sys, math, datetime as dt, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402

SYMS_M5 = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD",
           "USDCHF", "XAUUSD"]
SYMS_H1 = ["GBPUSD", "EURUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD",
           "USDCHF", "XAUUSD"]
PIPS = {"GBPUSD": 1e-4, "EURUSD": 1e-4, "USDJPY": 1e-2, "AUDUSD": 1e-4,
        "NZDUSD": 1e-4, "USDCAD": 1e-4, "USDCHF": 1e-4, "XAUUSD": 1e-1}
COST = 3.6
END = dt.datetime(2026, 9, 11)
SESS = [("ASIA", 0, 420), ("LDN", 420, 960), ("NY", 720, 1200)]


def get_bars(sym, tf, want_from):
    mt5.symbol_select(sym, True)
    out = {}
    anchor = END
    for _ in range(40):
        b = mt5.copy_rates_from(sym, tf, anchor, 30000)
        if b is None or len(b) == 0:
            break
        for x in b:
            out[int(x[0])] = (float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        anchor = dt.datetime.utcfromtimestamp(int(b[0][0]))
        if int(b[0][0]) <= want_from:
            break
        time.sleep(0.3)
    return out or None


def gmt_min(ts):
    return (ts % 86400) // 60


def stats(rets):
    n = len(rets)
    if n < 25:
        return None
    m = sum(rets) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in rets) / n)
    t = m / (sd / math.sqrt(n)) if sd > 0 else 0
    return m, t, n


def part_a():
    print("\n========== PART A: RETEST vs IMMEDIATE entry ==========")
    for sym in SYMS_M5:
        data = get_bars(sym, mt5.TIMEFRAME_M5, dt.datetime(2022, 1, 1).timestamp())
        if not data:
            continue
        times = sorted(data)
        pip = PIPS[sym]
        days = (times[-1] - times[0]) / 86400.0
        print(f"\n##### {sym} #####")
        for name, om, cm in SESS:
            imm, ret, filled, missed = [], [], 0, 0
            i = 30
            while i < len(times) - 5:
                t = times[i]
                if gmt_min(t) != om:
                    i += 1; continue
                ph = max(data[times[i - k]][1] for k in range(1, 13))
                pl = min(data[times[i - k]][2] for k in range(1, 13))
                side = 0; pbar = -1
                for k in range(0, 12):
                    if i + k >= len(times) or times[i + k] - t != k * 300:
                        break
                    c = data[times[i + k]][3]
                    if c > ph: side, pbar = -1, i + k; break
                    if c < pl: side, pbar = +1, i + k; break
                j = i
                while j < len(times) and gmt_min(times[j]) < cm:
                    j += 1
                if j <= i + 12:
                    i += 1; continue
                exit_px = data[times[j - 1]][3]
                if side:
                    imm.append(side * (exit_px - data[times[pbar]][3]) / pip)
                    lvl = ph if side == -1 else pl
                    fpx = None
                    for m in range(pbar + 1, j):
                        lo, hi = data[times[m]][2], data[times[m]][1]
                        if (side == -1 and lo <= lvl) or (side == 1 and hi >= lvl):
                            fpx = lvl; break
                    if fpx is not None:
                        filled += 1
                        ret.append(side * (exit_px - fpx) / pip)
                    else:
                        missed += 1
                i = j
            for tag, arr in (("IMM", imm), ("RETEST", ret)):
                r = stats(arr)
                if r:
                    m, tt, n = r
                    wk = n / (days / 7.0)
                    print(f"  {name}-{tag}: n={n} {wk:.1f}/wk mean={m:+.2f}p "
                          f"t={tt:+.2f} net={m - COST:+.2f}p")
            tot = filled + missed
            if tot:
                print(f"  {name}: retest fill={filled}/{tot} ({100*filled/tot:.0f}%)")


def part_b():
    print("\n========== PART B: hour-of-week / day-of-week drift ==========")
    for sym in SYMS_H1:
        data = get_bars(sym, mt5.TIMEFRAME_H1, dt.datetime(1999, 1, 1).timestamp())
        if not data or len(data) < 20000:
            if data:
                print(f"\n##### {sym} ##### coverage {len(data)} H1 bars — skip")
            continue
        times = sorted(data)
        pip = PIPS[sym]
        mid = times[len(times) // 2]
        yrs = (times[-1] - times[0]) / 86400.0 / 365.25
        how = {}
        dow = {}
        for t in times[1:]:
            o, c = data[t][0], data[t][3]
            r = (c - o) / pip
            hidx = (t // 3600 + 72) % 168             # Mon00GMT = 0 (epoch Thu00 = 72)
            didx = ((t // 86400) + 3) % 7          # Mon = 0
            if t >= 7 * 86400:                     # skip weekend-open junk
                pass
            how.setdefault(hidx, []).append((t, r))
            if gmt_min(t) == 0:
                dow.setdefault(didx, []).append((t, r))
        print(f"\n##### {sym} ##### ({len(data)} H1, {yrs:.1f}y)")
        passed = []
        for h in range(168):
            a = [r for t, r in how.get(h, []) if t <= mid]
            b = [r for t, r in how.get(h, []) if t > mid]
            ra, rb = stats(a), stats(b)
            if not ra or not rb:
                continue
            if ra[0] * rb[0] > 0 and abs(ra[1]) > 2.8 and abs(rb[1]) > 2.8:
                tot = ra[2] + rb[2]
                mm = (ra[0] * ra[2] + rb[0] * rb[2]) / tot
                passed.append((h, mm, tot))
                d = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][h // 24]
                print(f"  HoW {d} {h % 24:02d}h: mean={mm:+.2f}p n={tot} "
                      f"(halves {ra[0]:+.2f}/{rb[0]:+.2f})")
        for h, mm, tot in passed:
            nxt = [x for x in passed if x[0] == h + 1]
            if nxt and nxt[0][1] * mm > 0:
                print(f"    chain {h}->{h + 1}: ~{mm + nxt[0][1]:+.2f}p/wk")
        for d in range(7):
            a = [r for t, r in dow.get(d, []) if t <= mid]
            b = [r for t, r in dow.get(d, []) if t > mid]
            ra, rb = stats(a), stats(b)
            if not ra or not rb:
                continue
            dn = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d]
            flag = " <== PASS" if (ra[0] * rb[0] > 0 and abs(ra[1]) > 2.8
                                  and abs(rb[1]) > 2.8) else ""
            print(f"  DoW {dn}: {ra[0]:+.2f}/{rb[0]:+.2f}{flag}")


def main():
    kw = mt5_initialize_kwargs()
    if not mt5.initialize(**kw):
        print("attach failed", mt5.last_error()); return 1
    try:
        part_a()
        part_b()
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
