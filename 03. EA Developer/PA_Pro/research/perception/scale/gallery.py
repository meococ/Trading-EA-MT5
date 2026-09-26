"""gallery.py — Q5/gallery: random DESIGN sessions rendered in book
grammar, one arm per process (the snapshot binds once per process).

C-round-2 update (R48 §48.4.3): 10 random sessions restricted to
Monday–Friday, excluding 1 January and 25 December, each with at least
60 bars in the session window; the same 10 sessions rendered for arm
C1 (engine_9acaa206) and arm V1 (engine_e62f2dc9 + params_stable) so the
Owner can compare side by side.  ``--write-picks`` on the first run
freezes the sample so the second arm draws identical sessions.

render.py is read-only and its object layer divides by PIP where it
must multiply (FINDINGS F5): _ScaledObj pre-scales price-like geometry
by 1e-8 so /1e-4 lands on price.  Its x-axis is minute-of-day, so only
the target day's bars are passed and object indices are shifted.

Usage:
  SCALE_SNAP=engine_9acaa206 python scale/gallery.py --arm C1 \
      --write-picks scale/_gallery_picks.txt
  python scale/gallery.py --arm V1 --picks-file scale/_gallery_picks.txt
  python scale/gallery.py --index        # writes gallery/index.md
"""
import argparse
import collections
import datetime as _dt
import glob
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(
    os.path.join(HERE, "..", "..", "lib")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import design_loader as DL                        # noqa: E402
import harness as H                               # noqa: E402

H.get_engine()      # bind the snapshot's cet/engine BEFORE render pulls
                    # golden.overlay (which imports the live-tree cet)
import render                                     # noqa: E402

GAL = os.path.join(HERE, "gallery")

# render.py unit convention (FINDINGS F5, fixed in C2): the object
# layer now does ``vm.y(g["top"] * PIP)`` with PIP=1e-4 — engine
# geometry is in pips (price*1e4), so *1e-4 lands on price.  The old
# 1e-8 pre-scale shim is removed; only bar indices still shift (the
# bars array handed to render.py is the target day only; engine
# indices are warmup-based).
class _ScaledObj:
    """to_dict() view of an engine Obj: bar indices shifted by
    ``shift`` (geometry passes through in pips for render.py's
    pips->price conversion)."""

    def __init__(self, o, shift):
        self._o = o
        self._shift = shift

    def to_dict(self):
        d = dict(self._o.to_dict())
        s = self._shift
        d["t_birth"] = d["t_birth"] - s
        d["t_left"] = d["t_left"] - s
        if d["t_right"] is not None:
            d["t_right"] = d["t_right"] - s
        return d


class _EngineView:
    """Duck-typed engine for render_engine: scaled+shifted objects."""

    def __init__(self, e, shift):
        self.objects = [_ScaledObj(o, shift) for o in e.objects]
        self.p = e.p


WARM_DAYS = 5
SESS_END = {"asia": 480, "eu": 840, "us": 1140}
SESS_LO = {"asia": 0, "eu": 480, "us": 840}


def _daynum(date_str):
    import calendar
    return int(calendar.timegm(
        _dt.datetime.strptime(date_str, "%Y-%m-%d").timetuple())
        ) // 86400


def session_bars_ok(bars, dn, sess, min_bars=60):
    """At least min_bars bars inside the session window on day dn."""
    days = (bars["cet"] // 86400).astype(np.int64)
    lo, hi = SESS_LO[sess], SESS_END[sess]
    m = (days == dn) & (bars["cet_min"] >= lo) & (bars["cet_min"] < hi)
    return int(m.sum()) >= min_bars


def pick_sessions(bars, n, seed):
    """n distinct (date, session): Mon-Fri, not 01-01/12-25, >=60
    session bars."""
    days = (bars["cet"] // 86400).astype(np.int64)
    pool = []
    for dn in np.unique(days):
        d = _dt.datetime.utcfromtimestamp(int(dn) * 86400)
        if d.weekday() >= 5:                    # Mon-Fri only
            continue
        if (d.month, d.day) in ((1, 1), (12, 25)):
            continue
        for s in ("asia", "eu", "us"):
            if session_bars_ok(bars, int(dn), s):
                pool.append((d.strftime("%Y-%m-%d"), s))
    rng = random.Random(seed)
    rng.shuffle(pool)
    pick = pool[:n]
    if not any(s == "asia" for _, s in pick):
        for d, s in pool[n:]:
            if s == "asia":
                pick[-1] = (d, s)
                break
    return sorted(pick)


def run_session(bars, date, sess, arm):
    """Feed warmup+day bars from the preloaded window; return
    (day-bars, engine, upto_idx-day-relative)."""
    end_min = SESS_END[sess]
    dn = _daynum(date)
    days = (bars["cet"] // 86400).astype(np.int64)
    uniq = np.unique(days)
    di = int(np.searchsorted(uniq, dn))
    sel = uniq[max(0, di - WARM_DAYS):di + 1]
    mask = np.isin(days, sel)
    idx = np.where(mask)[0]
    i0, i1 = int(idx[0]), int(idx[-1]) + 1
    sub = {k: (v[i0:i1] if isinstance(v, np.ndarray) else v)
           for k, v in bars.items()}
    sub_days = days[i0:i1]
    in_sess = np.where((sub_days == dn)
                       & (sub["cet_min"] < end_min))[0]
    upto = int(in_sess[-1]) if len(in_sess) else i1 - i0 - 1
    e = H.make_engine(arm)
    for j in range(upto + 1):
        e.update(int(sub["t"][j]), float(sub["o"][j]), float(sub["h"][j]),
                 float(sub["l"][j]), float(sub["c"][j]),
                 cet_min=int(sub["cet_min"][j]))
    dstart = int(np.searchsorted(sub_days, dn))
    vis = {k: (v[dstart:] if isinstance(v, np.ndarray) else v)
           for k, v in sub.items()}
    return vis, e, upto - dstart, dstart


def write_index():
    """index.md pairing C1 and V1 renders of the same sessions."""
    files = collections.defaultdict(dict)
    for p in glob.glob(os.path.join(GAL, "*_c1.png")) + \
            glob.glob(os.path.join(GAL, "*_v1.png")):
        b = os.path.basename(p)
        date, sess, arm = b[:-4].rsplit("_", 2)
        files[(date, sess)][arm] = b
    idx = ["# SCALE gallery — DESIGN sessions, arms C1 vs V1",
           "",
           "Frozen engine 9acaa206 (arm C1, K1-K6 ON) vs the C-round-1",
           "STABLE line 9283b389 (arm V1).  render.py book grammar;",
           "geometry shim per FINDINGS F5.  No trades, no outcomes, no",
           "labels.  Sessions: Mon-Fri, excl 01-01/12-25, >=60 bars.",
           "",
           "| date | session | arm C1 | arm V1 |",
           "|---|---|---|---|"]
    for (date, sess), d in sorted(files.items()):
        idx.append("| %s | %s | %s | %s |" % (
            date, sess,
            d.get("c1", "—"), d.get("v1", "—")))
    with open(os.path.join(GAL, "index.md"), "w", encoding="utf8") as f:
        f.write("\n".join(idx) + "\n")
    print("wrote gallery/index.md (%d sessions)" % len(files))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--arm", default="C1", choices=["C1", "V1", "KEPT",
                                                    "STABLE"])
    ap.add_argument("--picks-file", default="")
    ap.add_argument("--write-picks", default="")
    ap.add_argument("--index", action="store_true")
    args = ap.parse_args()
    os.makedirs(GAL, exist_ok=True)
    if args.index:
        write_index()
        return
    bars = DL.load_m5("EURUSD")               # one scan, whole window
    if args.picks_file:
        picks = [tuple(x.split(",")) for x in
                 open(args.picks_file, encoding="utf8").read().split()
                 if x.strip()]
    else:
        picks = pick_sessions(bars, args.n, args.seed)
    if args.write_picks:
        with open(args.write_picks, "w") as f:
            for d, s in picks:
                f.write("%s,%s\n" % (d, s))
    for date, sess in picks:
        vis, e, upto_v, dstart = run_session(bars, date, sess, args.arm)
        png = "%s_%s_%s.png" % (date, sess, args.arm.lower())
        path = os.path.join(GAL, png)
        render.render_engine(
            vis, _EngineView(e, dstart), upto_v, path,
            title="%s EURUSD %s M5 (DESIGN, arm %s)" % (date, sess,
                                                        args.arm))
        n_obj = sum(1 for o in e.objects if o.state == "ACTIVE")
        print("  %s %s -> %s (%d live objects)" % (date, sess, png,
                                                   n_obj), flush=True)


if __name__ == "__main__":
    sys.exit(main())
