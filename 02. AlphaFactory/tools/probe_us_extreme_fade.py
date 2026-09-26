"""Stage-0 robustness probe: US-session-extreme fade at Asia open.

The strongest anomaly found in the campaign: at 00:00 GMT (Asia open),
a first-hour pierce of the PRIOR US session's (12:00-20:00 GMT) extreme
fades back with +7-14p expectancy (t=4.4-7.2 across GBP/EUR/JPY/AUD).

Checks here:
  1) year-split stability of the V2 edge (is it alive or decayed?)
  2) unconditional variant: fade NY-session's last-2h MOVE every Asia
     open (no pierce required) -> fires ~5/wk; does a weak version of
     the same edge exist at higher frequency?
  3) V2 + unconditional union cadence.

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

            v2_by_year = {}
            uncond = []
            union_n = 0
            i = 30
            while i < len(times) - 5:
                t = times[i]
                if gmt_min(t) != 0:
                    i += 1; continue
                dk = day_key(t)
                yr = dt.datetime.utcfromtimestamp(t).year

                # STRICTLY prior day only: day_key==dk-1. Including day-dk
                # bars in the 12-20GMT window leaks the same session's future
                # NY prices into the level (lookahead). A previous version of
                # this probe used dk-1<=dk and reported fake +8-19p edges;
                # the corrected map shows no exploitable boundary edge.
                prev_ny = [x for x in times
                           if day_key(x) == dk - 1 and 720 <= gmt_min(x) < 1200]
                if not prev_ny:
                    i += 1; continue
                ph = max(data[x][1] for x in prev_ny)
                pl = min(data[x][2] for x in prev_ny)
                # unconditional: NY last-2h move (18:00-20:00)
                ny2 = [x for x in prev_ny if gmt_min(x) >= 1080]
                ny_move = ((data[ny2[-1]][3] - data[ny2[0]][0]) / pip) if ny2 else 0.0

                hit = 0
                for k in range(0, 12):
                    if i + k >= len(times) or times[i + k] - t != k * 300:
                        break
                    b = data[times[i + k]]
                    if b[1] > ph: hit = -1; break
                    if b[2] < pl: hit = +1; break

                j = i
                while j < len(times) and gmt_min(times[j]) < 420:
                    j += 1
                if j <= i + 12:
                    i += 1; continue
                exit_px = data[times[j - 1]][3]
                entry_px = data[times[i + 11]][3]

                if hit:
                    union_n += 1
                    v2_by_year.setdefault(yr, []).append(hit * (exit_px - entry_px) / pip)
                if abs(ny_move) > 0:
                    sgn = -1 if ny_move > 0 else 1
                    uncond.append(sgn * (exit_px - entry_px) / pip)
                    union_n += 1
                i = j

            print("  V2 by year:")
            for yr in sorted(v2_by_year):
                r = v2_by_year[yr]
                m = sum(r) / len(r)
                sd = math.sqrt(sum((x - m) ** 2 for x in r) / len(r)) if len(r) > 1 else 0
                t = m / (sd / math.sqrt(len(r))) if sd > 0 else 0
                print(f"    {yr}: n={len(r)} mean={m:+.2f}p t={t:+.2f}")
            allv2 = [x for r in v2_by_year.values() for x in r]
            print(f"    ALL: n={len(allv2)} {len(allv2)/(days/7):.1f}/wk mean={sum(allv2)/len(allv2):+.2f}p")
            if len(uncond) > 30:
                m = sum(uncond) / len(uncond)
                sd = math.sqrt(sum((x - m) ** 2 for x in uncond) / len(uncond))
                t = m / (sd / math.sqrt(len(uncond))) if sd > 0 else 0
                print(f"  UNCOND fade-NY-2h: n={len(uncond)} {len(uncond)/(days/7):.1f}/wk mean={m:+.2f}p t={t:+.2f} net={m-COST:+.2f}p")
            print(f"  UNION cadence est: {union_n/(days/7):.1f} events/wk")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
