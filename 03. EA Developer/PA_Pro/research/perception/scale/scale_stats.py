"""scale_stats.py — consistency-at-scale measurement (Q2/Q3/Q4).

Feeds the snapshot engine DESIGN bars and records, per (day, session):
  * live objects per bar by family -> median, p90, share over the spec
    budget (>5) and the hard cap (>8);
  * stand_aside reason counts + tagged-bar share;
  * frozen-edge moves per 100 bars, logged vs unlogged (spec §6.1);
and per drawn object:
  * births by kind/route, box height (pips + ABR at birth), box duration
    (bars), level/line geometry, line slope (pips/hour).

Two run modes:
  --mode months : continuous engine per calendar month, warmed by the
                  preceding ~21 trading days (inside the wall); only the
                  month's own days are measured.  Covers all days.
  --mode days   : fresh engine per sampled day + ~25-day warmup; the
                  sampled days come from --days-file or --n + --seed.

Output: _stats_days_<arm>_<sym>_<tf>.jsonl and
        _stats_objs_<arm>_<sym>_<tf>.jsonl under scale/.

Outcome-blind: drawings only.  No forward-looking measure anywhere.
"""
import argparse
import collections
import json
import os
import random
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

WARM_DAYS = 21          # trading days of warmup before a measured month
# --mode days warmup.  Engine cost scales ~objects x bars
# (swings.alive/_floors scan per bar, see FINDINGS): 25d warmup ran at
# ~110 bars/s, so WARM_DAYS_PERDAY=5 keeps day-runs ~150-300 bars/s
# while still covering the grid switch (needs >=3 completed days),
# todvol/ema/abr convergence (~25 bars) and short carried context.
# Limitation: objects born >5 trading days earlier are absent.
WARM_DAYS_PERDAY = 5


def _dates_of(cet_arr):
    return (cet_arr // 86400).astype(np.int64)


def _day_str(daynum):
    import datetime as _dt
    return _dt.datetime.utcfromtimestamp(int(daynum) * 86400) \
        .strftime("%Y-%m-%d")


class Collector:
    """Per-bar and per-object measurement over one engine run.

    All indices are ENGINE-internal (``e.bars`` positions); the caller
    feeds a contiguous slice of a loader dict, so engine index 0 is the
    first bar fed.
    """

    def __init__(self, e, measure_from, bars_per_hour=12.0):
        self.e = e
        self.measure_from = measure_from        # first measured e-index
        self.bars_per_hour = bars_per_hour
        self.prev_sigs = {}
        self.day_rows = {}                      # (day, sess) -> dict
        self.obj_rows = []
        self._n_obj_seen = 0

    def on_bar(self, j, e):
        i = len(e.bars) - 1                     # engine index just fed
        # births
        for o in e.objects[self._n_obj_seen:]:
            o._scale_birth_sess = H.session_of(e.bars[i]["cet_min"])
            o._scale_birth_abr = e.abr[i]
        self._n_obj_seen = len(e.objects)
        if i < self.measure_from:
            # still track signatures so the first measured bar's diff
            # baseline is right
            self.prev_sigs = H.live_sigs(e)
            return
        b = e.bars[i]
        day = int(b["t"] - 3600) // 86400        # CET day (server - 1h)
        sess = H.session_of(b["cet_min"])
        key = (day, sess)
        r = self.day_rows.get(key)
        if r is None:
            r = self.day_rows[key] = {
                "day": day, "sess": sess, "bars": 0,
                "live": {f: [] for f in H.FAMILIES},
                "live_all": [], "live_struct": [],
                "sa_bars": 0, "sa": collections.Counter(),
                "edge_moves_logged": 0, "edge_moves_unlogged": 0,
            }
        r["bars"] += 1
        live = H.live_sigs(e)
        by_fam = collections.Counter(
            H.FAMILY.get(o.type, "?") for o in e.objects
            if o.state == "ACTIVE")
        for f in H.FAMILIES:
            r["live"][f].append(by_fam.get(f, 0))
        r["live_all"].append(sum(by_fam.values()))
        r["live_struct"].append(sum(v for k, v in by_fam.items()
                                    if k != "annot"))
        sa = e.stand_aside(i)
        if sa:
            r["sa_bars"] += 1
            for reason in sa:
                r["sa"][reason] += 1
        # edge stability: signature diff on still-live objects
        omap = {o.id: o for o in e.objects}
        for oid, sig in live.items():
            if oid in self.prev_sigs and self.prev_sigs[oid] != sig:
                logged = any(ev[0] == i and ev[1] in H.LOGGED_MOVE
                             for ev in omap[oid].events)
                r["edge_moves_logged" if logged
                  else "edge_moves_unlogged"] += 1
        self.prev_sigs = live

    def finish(self):
        """Per-object rows + collapse per-bar lists to summaries."""
        e = self.e
        last_i = len(e.bars) - 1
        for o in e.objects:
            if o.t_birth < self.measure_from:
                continue                       # born inside warmup
            g = o.geometry
            row = {"day": int(e.bars[o.t_birth]["t"] - 3600) // 86400,
                   "sess": getattr(o, "_scale_birth_sess",
                                   H.session_of(
                                       e.bars[o.t_birth]["cet_min"])),
                   "type": o.type, "why": o.why, "state": o.state,
                   "t_birth": o.t_birth, "t_left": o.t_left,
                   "t_right": o.t_right,
                   "dur_bars": (o.t_right if o.t_right is not None
                                else last_i) - o.t_left,
                   "n_events": len(o.events),
                   "birth_abr": round(getattr(o, "_scale_birth_abr",
                                              e.abr[o.t_birth]), 3)}
            if "top" in g:
                h_pips = g["top"] - g["bottom"]
                row["height_pips"] = round(h_pips, 2)
                row["height_abr"] = round(
                    h_pips / max(row["birth_abr"], 1e-9), 3)
            if "price" in g:
                row["price"] = g["price"]
            if "slope" in g:
                row["slope_pips_hr"] = round(
                    g["slope"] * self.bars_per_hour, 3)
            if "letter" in g:
                row["letter"] = g["letter"]
            # R38 §38.5: drawn price points (engine pips) for the 00/50
            # round-number share — converted to true pips in the report
            pts = []
            if "top" in g:
                pts += [g["top"], g["bottom"]]
            for k in ("price", "level", "p0"):
                if k in g:
                    pts.append(g[k])
            if pts:
                row["rn_pts"] = [round(p, 3) for p in pts]
            self.obj_rows.append(row)

        out = []
        for (day, sess), r in sorted(self.day_rows.items()):
            row = {"day": day, "sess": sess, "bars": r["bars"],
                   "sa_bars": r["sa_bars"],
                   "sa": dict(r["sa"]),
                   "edge_moves_logged": r["edge_moves_logged"],
                   "edge_moves_unlogged": r["edge_moves_unlogged"]}
            for f in H.FAMILIES:
                v = np.asarray(r["live"][f], dtype=np.float64)
                row["%s_med" % f] = float(np.median(v))
                row["%s_p90" % f] = float(np.percentile(v, 90))
            va = np.asarray(r["live_all"], dtype=np.float64)
            vs = np.asarray(r["live_struct"], dtype=np.float64)
            row["all_med"] = float(np.median(va))
            row["all_p90"] = float(np.percentile(va, 90))
            row["struct_med"] = float(np.median(vs))
            row["struct_p90"] = float(np.percentile(vs, 90))
            row["over5"] = float((vs > 5).mean())
            row["over8"] = float((vs > 8).mean())
            row["over5_all"] = float((va > 5).mean())
            row["over8_all"] = float((va > 8).mean())
            out.append(row)
        return out


def _feed(e, bars, i0, i1, on_bar):
    for j in range(i0, i1):
        e.update(int(bars["t"][j]), float(bars["o"][j]),
                 float(bars["h"][j]), float(bars["l"][j]),
                 float(bars["c"][j]), cet_min=int(bars["cet_min"][j]))
        if on_bar:
            on_bar(j, e)


def run_months(symbol, arm, tf=5, year_lo=2016, year_hi=2021):
    """Month-chunked continuous runs with ~WARM_DAYS warmup days."""
    loader = {5: DL.load_m5, 15: DL.load_m15}[tf]
    bars = loader(symbol)                      # whole DESIGN window
    days = _dates_of(bars["cet"])
    uniq = np.unique(days)
    # month id per day-number
    import datetime as _dt
    mon_of = {}
    for d in uniq:
        s = _day_str(d)
        mon_of[int(d)] = s[:7]
    months = sorted(set(mon_of.values()))
    all_day_rows, all_obj_rows = [], []
    for mon in months:
        if not (str(year_lo) <= mon[:4] <= str(year_hi)):
            continue
        m_days = [d for d in uniq if mon_of[int(d)] == mon]
        di = uniq.tolist().index(m_days[0])
        warm = uniq[max(0, di - WARM_DAYS):di]   # prior days in-window
        sel = np.concatenate([warm, m_days])
        mask = np.isin(days, sel)
        idx = np.where(mask)[0]
        i0, i1 = int(idx[0]), int(idx[-1]) + 1
        # engine index of the first measured bar = number of warmup
        # bars fed before it (the feed is contiguous from i0)
        first_meas = int(np.where(days == m_days[0])[0][0])
        measure_from = first_meas - i0
        e = H.make_engine(arm)
        col = Collector(e, measure_from, bars_per_hour=60.0 / tf)
        t0 = time.time()
        _feed(e, bars, i0, i1, col.on_bar)
        for r in col.finish():
            r["month"] = mon
            all_day_rows.append(r)
        all_obj_rows.extend(col.obj_rows)
        print("  %s %s: %d bars in %.1fs (%d measured day-rows, "
              "%d objs)" % (symbol, mon, i1 - i0, time.time() - t0,
                            len([r for r in col.day_rows.values()]),
                            len(col.obj_rows)), flush=True)
    return all_day_rows, all_obj_rows


def _daynum(date_str):
    import calendar
    import datetime as _dt
    return int(calendar.timegm(
        _dt.datetime.strptime(date_str, "%Y-%m-%d").timetuple())
        ) // 86400


def run_days(symbol, arm, day_list, tf=5):
    """Fresh engine per sampled day, WARM_DAYS_PERDAY warmup days.
    The whole DESIGN window is loaded ONCE (one ctm-pushdown scan) and
    each run slices warmup+day bars from it by position."""
    loader = {5: DL.load_m5, 15: DL.load_m15}[tf]
    bars = loader(symbol)                      # one scan, whole window
    days = _dates_of(bars["cet"])
    uniq = np.unique(days)
    all_day_rows, all_obj_rows = [], []
    for date in day_list:
        dn = _daynum(date)
        di = int(np.searchsorted(uniq, dn))
        if di >= len(uniq) or uniq[di] != dn:
            continue
        sel = uniq[max(0, di - WARM_DAYS_PERDAY):di + 1]
        mask = np.isin(days, sel)
        idx = np.where(mask)[0]
        i0, i1 = int(idx[0]), int(idx[-1]) + 1
        n_warm = int(np.searchsorted(days[i0:i1], dn))
        e = H.make_engine(arm)
        col = Collector(e, n_warm, bars_per_hour=60.0 / tf)
        t0 = time.time()
        _feed(e, bars, i0, i1, col.on_bar)
        rows = col.finish()
        for r in rows:
            r["date"] = date
        all_day_rows.extend(rows)
        all_obj_rows.extend(col.obj_rows)
        print("  %s %s: %d bars (+%d warm) %.1fs, %d objs" % (
            symbol, date, i1 - i0 - n_warm, n_warm, time.time() - t0,
            len(col.obj_rows)), flush=True)
    return all_day_rows, all_obj_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True,
                    choices=["STABLE", "KEPT", "C1", "V1"])
    ap.add_argument("--symbol", default="EURUSD")
    ap.add_argument("--tf", type=int, default=5, choices=[5, 15])
    ap.add_argument("--mode", default="months",
                    choices=["months", "days"])
    ap.add_argument("--n", type=int, default=0,
                    help="--mode days: sample n random days")
    ap.add_argument("--per-year", type=int, default=0,
                    help="--mode days: sample n days per calendar year "
                         "(stratified)")
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--days-file", default="")
    ap.add_argument("--out-tag", default="")
    args = ap.parse_args()

    slot = pa_slots.acquire("scale-stats-%s-%s" % (args.arm, args.symbol),
                            timeout=3600)
    print("pa_slot %d | arm=%s sym=%s tf=M%d mode=%s"
          % (slot, args.arm, args.symbol, args.tf, args.mode),
          flush=True)
    try:
        if args.mode == "months":
            dr, orr = run_months(args.symbol, args.arm, tf=args.tf)
        else:
            days = DL.day_list(args.symbol)
            if args.days_file:
                day_list = [x.strip() for x in
                            open(args.days_file, encoding="utf8")
                            if x.strip()]
            elif args.per_year:
                byy = collections.defaultdict(list)
                for d in days:
                    byy[d[:4]].append(d)
                rng = random.Random(args.seed)
                day_list = sorted(
                    d for y in sorted(byy)
                    for d in rng.sample(byy[y],
                                        min(args.per_year,
                                            len(byy[y]))))
            else:
                day_list = sorted(random.Random(args.seed)
                                  .sample(days, args.n))
            dr, orr = run_days(args.symbol, args.arm, day_list,
                               tf=args.tf)
        tag = args.out_tag or "%s_%s_M%d" % (args.arm, args.symbol,
                                           args.tf)
        fd = os.path.join(HERE, "_stats_days_%s.jsonl" % tag)
        fo = os.path.join(HERE, "_stats_objs_%s.jsonl" % tag)
        with open(fd, "w", encoding="utf8") as f:
            for r in dr:
                r = dict(r)
                r["date"] = r.get("date") or _day_str(r["day"])
                f.write(json.dumps(r, sort_keys=True) + "\n")
        with open(fo, "w", encoding="utf8") as f:
            for r in orr:
                r = dict(r)
                r["date"] = _day_str(r["day"])
                f.write(json.dumps(r, sort_keys=True) + "\n")
        print("wrote %s (%d rows), %s (%d rows)"
              % (fd, len(dr), fo, len(orr)))
    finally:
        pa_slots.release(slot)


if __name__ == "__main__":
    sys.exit(main())
