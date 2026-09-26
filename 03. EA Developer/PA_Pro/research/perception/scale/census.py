"""census.py — R48 §48.4 item 2: outcome-blind drawing census.

Runs arm C1 (frozen 9acaa206) over EVERY DESIGN trading day 2016-2021,
EURUSD M5, fresh engine per day + WARM_DAYS_PERDAY warmup — the same
day-mode convention as scale_stats.py.

Per measured day it counts DRAWINGS ONLY:
  * boxes born        — objects whose final type is BOX (incl. converted
                        RANGE_OPENs) born inside the measured day;
  * box breakouts     — engine break/pierce events on boxes, counted on
                        the day the event fired (break, break_confirm,
                        pierced; tease_break/tease_pierce kept separate);
  * levels born       — LEVEL_CARRIED + MINI_LEVEL births;
  * lines born        — PATTERN_LINE + CONTEXT_LINE births.

Output: _census_<arm>_<symbol>_M<tf>.jsonl, one row per (day, session)
with counts attributed to the birth/event bar's own session.

No outcomes, no forward returns, no PnL, no setup screens.

Usage:
  SCALE_SNAP=engine_9acaa206 python scale/census.py --arm C1 \
      --symbol EURUSD --tf 5
"""
import argparse
import collections
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(
    os.path.join(HERE, "..", "..", "..", "lib")))
import pa_slots                                   # noqa: E402
import design_loader as DL                        # noqa: E402
import harness as H                               # noqa: E402

WARM_DAYS = 5          # same day-mode warmup as scale_stats.py

BREAK_EVENTS = ("break", "break_confirm", "pierced")
TEASE_EVENTS = ("tease_break", "tease_pierce")
BOX_TYPES = ("BOX", "RANGE_OPEN")      # RANGE_OPEN converts to BOX
LEVEL_TYPES = ("LEVEL_CARRIED", "MINI_LEVEL")
LINE_TYPES = ("PATTERN_LINE", "CONTEXT_LINE")


def _dates_of(cet_arr):
    return (cet_arr // 86400).astype(np.int64)


def _day_str(daynum):
    import datetime as _dt
    return _dt.datetime.utcfromtimestamp(int(daynum) * 86400) \
        .strftime("%Y-%m-%d")


def count_day(e, measure_from, rows):
    """Attribute births and break events in e.objects to (day, sess)."""
    for o in e.objects:
        born_meas = o.t_birth >= measure_from
        if born_meas:
            b = e.bars[o.t_birth]
            key = (int(b["t"] - 3600) // 86400,
                   H.session_of(b["cet_min"]))
            r = rows[key]
            if o.type in BOX_TYPES or o.type == "BOX":
                r["boxes"] += 1
            elif o.type in LEVEL_TYPES:
                r["levels"] += 1
            elif o.type in LINE_TYPES:
                r["lines"] += 1
            if o.type == "RANGE_OPEN":
                r["range_open"] += 1
        for ev in (o.events or []):
            i, code = ev[0], ev[1]
            if i < measure_from:
                continue
            if code in BREAK_EVENTS or code in TEASE_EVENTS:
                b = e.bars[i]
                key = (int(b["t"] - 3600) // 86400,
                       H.session_of(b["cet_min"]))
                rows[key]["breaks" if code in BREAK_EVENTS
                          else "teases"] += 1


def run(symbol, arm, tf=5, out_fh=None):
    loader = {5: DL.load_m5, 15: DL.load_m15}[tf]
    bars = loader(symbol)                      # one scan, whole window
    days = _dates_of(bars["cet"])
    uniq = np.unique(days)
    out = []
    n = len(uniq)
    for di, dn in enumerate(uniq):
        sel = uniq[max(0, di - WARM_DAYS):di + 1]
        mask = np.isin(days, sel)
        idx = np.where(mask)[0]
        i0, i1 = int(idx[0]), int(idx[-1]) + 1
        n_warm = int(np.searchsorted(days[i0:i1], dn))
        e = H.make_engine(arm)
        t0 = time.time()
        for j in range(i0, i1):
            e.update(int(bars["t"][j]), float(bars["o"][j]),
                     float(bars["h"][j]), float(bars["l"][j]),
                     float(bars["c"][j]), cet_min=int(bars["cet_min"][j]))
        rows = collections.defaultdict(
            lambda: {"boxes": 0, "range_open": 0, "breaks": 0,
                     "teases": 0, "levels": 0, "lines": 0})
        count_day(e, n_warm, rows)
        date = _day_str(int(dn))
        for (day, sess), r in rows.items():
            r.update({"day": day, "date": date, "sess": sess,
                      "year": date[:4]})
            line = json.dumps(r, sort_keys=True)
            out.append(r)
            if out_fh is not None:
                out_fh.write(line + "\n")
        if out_fh is not None:
            out_fh.flush()
        if di % 50 == 0 or di == n - 1:
            print("  %d/%d %s %s: %.1fs" % (di + 1, n, symbol, date,
                                            time.time() - t0),
                  flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["C1", "V1",
                                                     "STABLE", "KEPT"])
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--tf", type=int, default=5, choices=[5, 15])
    args = ap.parse_args()
    slot = pa_slots.acquire("scale-census-%s" % args.symbol,
                            timeout=3600)
    print("pa_slot %d | census arm=%s sym=%s tf=M%d" % (
        slot, args.arm, args.symbol, args.tf), flush=True)
    try:
        tag = "%s_%s_M%d" % (args.arm, args.symbol, args.tf)
        fo = os.path.join(HERE, "_census_%s.jsonl" % tag)
        with open(fo, "w", encoding="utf8") as f:
            rows = run(args.symbol, args.arm, tf=args.tf, out_fh=f)
        print("wrote %s (%d rows)" % (fo, len(rows)))
    finally:
        pa_slots.release(slot)


if __name__ == "__main__":
    sys.exit(main())
