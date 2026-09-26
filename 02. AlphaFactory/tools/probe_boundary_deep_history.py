# Day-boundary complex on FULL history (2010->2025, M1 .hcc — same plane as tester).
# Decisive question: do the 23h-short / 00h-long / pierce-fade legs exist across
# eras, or are they a 2025-regime artifact of the 16-month copy_rates window?
import datetime as dt
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hcc_reader import read_hcc_year, HISTORY_DIR  # noqa: E402

SYMS = ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"]
PIPS = {s: (1e-2 if s.endswith("JPY") else 1e-4) for s in SYMS}
Y0, Y1 = 2010, 2025


def stats(v):
    n = len(v)
    if n < 20:
        return None
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / n)
    w = sum(1 for x in v if x > 0) / n
    return m, m / (sd / math.sqrt(n)) if sd > 0 else 0.0, w, n


def legs_for_year(sym, year, pip):
    f = HISTORY_DIR / sym / f"{year}.hcc"
    if not f.exists():
        return None
    bars = read_hcc_year(f)
    ts = sorted(bars)
    idx = {t: i for i, t in enumerate(ts)}
    long00, short23, fade = [], [], []
    for i, t in enumerate(ts):
        d = dt.datetime.utcfromtimestamp(t)
        if d.weekday() > 4:
            continue
        day_min = d.hour * 60 + d.minute
        # --- leg 00h long: open 00:00 -> close 00:55 (M1 bars: t..t+55)
        if day_min == 0:
            t2 = t + 55 * 60
            if t2 in idx:
                long00.append((bars[t2][3] - bars[t][0]) / pip)
        # --- leg 23h short: open 23:00 -> close 23:55
        if day_min == 23 * 60:
            t2 = t + 55 * 60
            if t2 in idx:
                short23.append((bars[t][0] - bars[t2][3]) / pip)
        # --- fade: M1 bar in 00:00-00:30 whose extreme pierces prior-6h extreme
        if 0 <= day_min <= 30:
            t6 = t - 6 * 3600
            j = idx.get(t6)
            if j is None:
                continue
            seg = ts[j:i]
            if not seg:
                continue
            hi6 = max(bars[x][1] for x in seg)
            lo6 = min(bars[x][2] for x in seg)
            o, h, l, c = bars[t][:4]
            nxt = idx.get(t + 60)
            if nxt is None:
                continue
            t_exit = t + 60 + 120 * 60          # entry next M1 open, hold 2h
            if t_exit not in idx:
                continue
            ent = bars[ts[nxt]][0]
            ext = bars[t_exit][3]
            if h > hi6:      # up-pierce -> fade short
                fade.append((ent - ext) / pip)
            elif l < lo6:    # down-pierce -> fade long
                fade.append((ext - ent) / pip)
    return long00, short23, fade


def main():
    print(f"{'sym':<7} {'leg':<8} " + " ".join(f"{y}" for y in range(Y0, Y1 + 1)))
    for sym in SYMS:
        pip = PIPS[sym]
        rows = {"00h long": [], "23h short": [], "fade": []}
        for y in range(Y0, Y1 + 1):
            r = legs_for_year(sym, y, pip)
            if r is None:
                for k in rows:
                    rows[k].append(None)
                continue
            for k, v in zip(rows, r):
                s = stats(v)
                rows[k].append((s[0], s[1], s[2]) if s else None)
        for k, vals in rows.items():
            cells = []
            for v in vals:
                if v is None:
                    cells.append("    -    ")
                else:
                    cells.append(f"{v[0]:+5.1f}/{v[2]:.0%}"[:11].ljust(11))
            print(f"{sym:<7} {k:<8} " + " ".join(cells))
        # totals
        for k, vals in rows.items():
            pass


if __name__ == "__main__":
    main()
