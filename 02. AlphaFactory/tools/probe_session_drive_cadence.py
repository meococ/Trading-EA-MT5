#!/usr/bin/env python3
"""Stage-0 frequency probe: session open-drive continuation on M5.

Counts candidate entries/day before any EA is written. Mechanism (design
prior only, not an outcome read): after a session open, the first OR_BARS
closed M5 bars define the opening range. A later closed M5 bar whose CLOSE
breaks the OR extreme triggers one continuation entry per session.

Sessions (GMT, same doctrine as LSW_Session.mqh):
  London 07:00-16:00, New York 12:00-20:00. OR = first 6 M5 bars.
Server->GMT: offset +2h winter, +3h on US DST (MetaQuotes-Demo, LSW contract).

Attach: governed isolate only, via factory_paths.mt5_initialize_kwargs.
Output: per-symbol/day stats + frequency verdict vs the 10-40/week band.
"""
import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from factory_paths import mt5_initialize_kwargs  # noqa: E402

import MetaTrader5 as mt5  # noqa: E402
import numpy as np  # noqa: E402

SESSIONS = [("LDN", 7, 16), ("NY", 12, 20)]
OR_BARS = 6
MAX_BREAK_BARS = 48        # give up looking for the break after 4h
ATR_PERIOD = 14
OR_MIN_ATR = 0.5           # opening-range floor vs single-bar ATR14
OR_MAX_ATR = 6.0           # opening-range cap vs single-bar ATR14


def nth_sunday_day(year, month, nth):
    d = datetime(year, month, 1)
    first_sunday = 1 + ((7 - d.weekday() + 0) % 7)  # weekday(): Mon=0..Sun=6
    # python weekday: Sunday=6
    first_sunday = 1 + ((6 - d.weekday()) % 7)
    return first_sunday + 7 * (nth - 1)


def us_dst_active(dt):
    if dt.month < 3 or dt.month > 11:
        return False
    if 3 < dt.month < 11:
        return True
    if dt.month == 3:
        sd = nth_sunday_day(dt.year, 3, 2)
        if dt.day > sd:
            return True
        if dt.day < sd:
            return False
        return dt.hour >= 7
    ed = nth_sunday_day(dt.year, 11, 1)
    if dt.day < ed:
        return True
    if dt.day > ed:
        return False
    return dt.hour < 6


def server_to_gmt(ts):
    dt = datetime.utcfromtimestamp(int(ts))
    offset = 2 + (1 if us_dst_active(dt) else 0)
    return dt - timedelta(hours=offset)


def atr14(bars, i):
    if i < ATR_PERIOD:
        return None
    trs = []
    for k in range(i - ATR_PERIOD + 1, i + 1):
        h, l, pc = bars[k]["high"], bars[k]["low"], bars[k - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return float(np.mean(trs))


def probe(symbol, days):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    bars = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, end)
    if bars is None or len(bars) == 0:
        return None
    n = len(bars)
    entries = []
    skipped_or_small = skipped_or_large = no_break = 0
    sessions_seen = 0
    i = 0
    while i < n - OR_BARS - 1:
        g = server_to_gmt(bars[i]["time"])
        for sname, sopen, sclose in SESSIONS:
            if g.hour == sopen and g.minute == 0 and g.weekday() < 5:
                sessions_seen += 1
                orh = max(bars[i + k]["high"] for k in range(OR_BARS))
                orl = min(bars[i + k]["low"] for k in range(OR_BARS))
                a = atr14(bars, i + OR_BARS - 1)
                if a is None or a <= 0:
                    break
                rng = orh - orl
                if rng < OR_MIN_ATR * a:
                    skipped_or_small += 1
                    break
                if rng > OR_MAX_ATR * a:
                    skipped_or_large += 1
                    break
                hit = False
                for j in range(i + OR_BARS, min(i + OR_BARS + MAX_BREAK_BARS, n)):
                    gj = server_to_gmt(bars[j]["time"])
                    if gj.day != g.day or gj.hour >= sclose:
                        break
                    c = bars[j]["close"]
                    if c > orh:
                        entries.append((gj, "LONG", sname))
                        hit = True
                        break
                    if c < orl:
                        entries.append((gj, "SHORT", sname))
                        hit = True
                        break
                if not hit:
                    no_break += 1
                i = i + OR_BARS  # skip past the OR window
                break
        i += 1
    return {
        "sessions": sessions_seen,
        "entries": len(entries),
        "or_small": skipped_or_small,
        "or_large": skipped_or_large,
        "no_break": no_break,
        "entries_detail": entries,
        "days": days,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default="USDJPY,GBPUSD,XAUUSD")
    ap.add_argument("--days", type=int, default=92)
    args = ap.parse_args()

    if not mt5.initialize(**mt5_initialize_kwargs()):
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    try:
        for sym in args.symbols.split(","):
            sym = sym.strip()
            info = mt5.symbol_info(sym)
            if info is None:
                print(f"{sym}: NOT AVAILABLE")
                continue
            if not info.visible:
                mt5.symbol_select(sym, True)
            r = probe(sym, args.days)
            if r is None:
                print(f"{sym}: no bars")
                continue
            weeks = r["days"] / 7.0
            tpw = r["entries"] / weeks
            print(f"{sym}: {r['entries']} entries / {r['sessions']} sessions "
                  f"over {r['days']}d = {tpw:.1f}/wk | "
                  f"or_small={r['or_small']} or_large={r['or_large']} "
                  f"no_break={r['no_break']}")
            by_sess = {}
            for d, side, s in r["entries_detail"]:
                by_sess[s] = by_sess.get(s, 0) + 1
            print(f"   by session: {by_sess}")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
