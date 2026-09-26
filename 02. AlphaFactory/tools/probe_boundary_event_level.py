# Event-level day-boundary test on M1 .hcc history (2010->2025).
# Fixes the per-tranche oversampling bias: ONE event per day.
# Splits: first-pierce fade (up->short / down->long), unconditional 00h long,
# and gap-size conditioning (roll-gap overshoot hypothesis).
import bisect
import datetime as dt
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hcc_reader import read_hcc_year, HISTORY_DIR  # noqa: E402

SYMS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
Y0, Y1 = 2010, 2025
CLIP = 150.0  # pip sanity clip vs corrupt records


def st(v):
    v = [x for x in v if abs(x) < CLIP]
    n = len(v)
    if n < 20:
        return None
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
    w = sum(1 for x in v if x > 0) / n
    return m, m / (sd / math.sqrt(n)) if sd else 0.0, w, n


def year_stats(sym, year, pip):
    f = HISTORY_DIR / sym / f"{year}.hcc"
    if not f.exists():
        return None
    bars = read_hcc_year(f)
    ts = sorted(bars)
    have = set(ts)
    out = {"00h": [], "fadeU": [], "fadeD": [], "gap": [], "gd00": []}
    for t in ts:
        d = dt.datetime.utcfromtimestamp(t)
        if d.weekday() > 4 or d.hour != 0 or d.minute != 0:
            continue
        # prior-6h extremes (18:00..23:59 previous evening, same session)
        t6 = t - 6 * 3600
        i0 = bisect.bisect_left(ts, t6)
        i1 = bisect.bisect_left(ts, t)
        seg = ts[i0:i1]
        if len(seg) < 60:
            continue
        hi6 = max(bars[x][1] for x in seg)
        lo6 = min(bars[x][2] for x in seg)
        prev_close = bars[seg[-1]][3]
        o0 = bars[t][0]
        gap_p = (o0 - prev_close) / pip
        # 00h unconditional long: entry 00:00 open, exit 00:55 close
        t2 = t + 55 * 60
        if t2 in have:
            r = (bars[t2][3] - o0) / pip
            out["00h"].append(r)
            out["gap"].append(gap_p)
            out["gd00"].append((gap_p, r))
        # first-pierce fade: first M1 bar 00:00-00:30 breaking hi6/lo6
        t_exit_base = None
        for k in range(31):
            tb = t + k * 60
            if tb not in have:
                continue
            hb, lb = bars[tb][1], bars[tb][2]
            te = tb + 60 + 120 * 60   # enter next M1 open, hold 2h
            ent = tb + 60
            if hb > hi6 and ent in have and te in have:
                out["fadeU"].append((bars[ent][0] - bars[te][3]) / pip)
                break
            if lb < lo6 and ent in have and te in have:
                out["fadeD"].append((bars[te][3] - bars[ent][0]) / pip)
                break
    return out


def main():
    hdr = " ".join(f"{y}"[2:] for y in range(Y0, Y1 + 1))
    for sym in SYMS:
        pip = PIPS[sym]
        agg = {"00h": [], "fadeU": [], "fadeD": [], "gap": [], "gd00": []}
        per_year = {k: [] for k in agg}
        for y in range(Y0, Y1 + 1):
            r = year_stats(sym, y, pip)
            if r is None:
                for k in per_year:
                    per_year[k].append(None)
                continue
            for k in agg:
                agg[k].extend(r[k])
                s = st(r[k]) if k != "gd00" else None
                per_year[k].append(s)
        print(f"\n===== {sym} (mean/win% per year) =====")
        for k in ("00h", "fadeU", "fadeD"):
            cells = []
            for s in per_year[k]:
                cells.append("   -  " if s is None else f"{s[0]:+5.1f}/{s[2]:.0%}"[:11].ljust(11))
            s = st(agg[k])
            print(f"{k:<6} {' '.join(cells)} | ALL {s[0]:+.2f}p t={s[1]:+.1f} w={s[2]:.0%} n={s[3]}" if s else f"{k} n/a")
        # gap-conditioning: 00h return vs gap size quintiles
        g = sorted(agg["gd00"], key=lambda x: x[0])
        if len(g) > 100:
            q = len(g) // 5
            for i in range(5):
                seg = g[i * q:(i + 1) * q]
                gp = [x[0] for x in seg]
                rr = [x[1] for x in seg]
                s = st(rr)
                print(f"  gapQ{i + 1} [{min(gp):+.1f}..{max(gp):+.1f}p] -> 00h {s[0]:+.2f}p t={s[1]:+.1f} w={s[2]:.0%} n={s[3]}")


if __name__ == "__main__":
    main()
