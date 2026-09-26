"""scale_q1.py — throughput + determinism on random DESIGN days (Q1).

Per the lane brief:
  * seconds per day;
  * prefix invariance: objects at t from bars[:t+1] equal the full run,
    at 50 random t per day (spec §6.3);
  * a byte-identical rerun.

Runs on the KEPT arm (the candidate under test); STABLE spot-check is
available via --arm STABLE.  Prints one line per check and a summary;
failures are listed in detail for FINDINGS.md.

Usage: python scale/scale_q1.py [--arm KEPT] [--days 20] [--seed N]
"""
import argparse
import os
import pickle
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


def pick_days(n, seed):
    days = [d for d in DL.day_list("EURUSD")]
    rng = random.Random(seed)
    return sorted(rng.sample(days, n))


def run_day(date, arm, upto=None):
    b = DL.load_m5("EURUSD", date + " 00:00", date + " 23:55")
    e = H.make_engine(arm)
    n = len(b["t"]) if upto is None else upto + 1
    sigs = []
    for j in range(n):
        e.update(int(b["t"][j]), float(b["o"][j]), float(b["h"][j]),
                 float(b["l"][j]), float(b["c"][j]),
                 cet_min=int(b["cet_min"][j]))
        sigs.append(H.live_sigs(e))
    return e, sigs, n


def obj_map(e):
    return {o.id: o for o in e.objects}


def _type_at(o, t):
    """o.type as of bar t: the engine mutates RANGE_OPEN -> BOX in place
    at asia_convert (boxes.py:755), so a still-active final-BOX object
    was a RANGE_OPEN before its convert bar."""
    if o.type == "BOX":
        for ev in o.events:
            if ev[1] == "asia_convert" and ev[0] > t:
                return "RANGE_OPEN"
    return o.type


def cmp_prefix(e_full, sigs_full, e_pre, t):
    """Compare prefix-run state at t vs the full run at t.
    Returns a list of mismatch strings (empty = invariant holds)."""
    bad = []
    fmap = obj_map(e_full)
    live_full = sigs_full[t]
    for o in e_pre.objects:
        f = fmap.get(o.id)
        if f is None:
            bad.append("%s: born in prefix but absent in full" % o.id)
            continue
        if (_type_at(f, t), f.t_birth, f.t_left) != \
                (o.type, o.t_birth, o.t_left):
            bad.append("%s: birth mismatch %s vs %s" % (
                o.id, (_type_at(f, t), f.t_birth, f.t_left),
                (o.type, o.t_birth, o.t_left)))
            continue
        # state at t: a dead object may revive after t (lines.py
        # 'revive' re-opens the same id), so final t_right is NOT the
        # state at t.  Compare liveness at t instead.
        if o.state == "ACTIVE":
            s_p = H.edge_sig(o)
            s_f = live_full.get(o.id)
            if s_f != s_p:
                bad.append("%s: live sig %s vs %s" % (o.id, s_p, s_f))
        elif o.t_right is not None and o.t_right <= t:
            if o.id in live_full:
                bad.append("%s: dead in prefix at %d but live in "
                           "full at t" % (o.id, o.t_right))
        # event history up to t must match
        ev_p = [ev for ev in o.events if ev[0] <= t]
        ev_f = [ev for ev in f.events if ev[0] <= t]
        if ev_p != ev_f:
            bad.append("%s: events<=t differ (%d vs %d)"
                       % (o.id, len(ev_p), len(ev_f)))
    # objects live in full at t but missing from prefix
    pids = {o.id for o in e_pre.objects}
    for oid in live_full:
        if oid not in pids:
            bad.append("%s: live in full at t, absent in prefix" % oid)
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="KEPT")
    ap.add_argument("--days", type=int, default=20)
    ap.add_argument("--t-per-day", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20260922)
    args = ap.parse_args()

    days = pick_days(args.days, args.seed)
    print("Q1 arm=%s  days=%d  %s..%s" % (args.arm, len(days),
                                        days[0], days[-1]))
    rng = random.Random(args.seed + 1)
    slot = pa_slots.acquire("scale-q1", timeout=600)
    print("pa_slot %d acquired" % slot)

    secs = []
    fails = []
    for date in days:
        t0 = time.time()
        e_full, sigs, n = run_day(date, args.arm)
        dt = time.time() - t0
        secs.append(dt / n * 288)      # normalised to a full session
        # byte-identical rerun
        e2, _s2, _n2 = run_day(date, args.arm)
        same = H.canon_bytes(e_full) == H.canon_bytes(e2)
        if not same:
            fails.append("%s: rerun not byte-identical" % date)
        # prefix invariance at random t (short Sunday-open days: fewer)
        k = min(args.t_per_day, max(0, n - 10))
        ts = sorted(rng.sample(range(10, n), k)) if k else []
        nbad = 0
        nbad_t = 0
        for t in ts:
            e_pre, _s, _ = run_day(date, args.arm, upto=t)
            bad = cmp_prefix(e_full, sigs, e_pre, t)
            nbad += len(bad)
            nbad_t += bool(bad)
            for bmsg in bad[:3]:
                fails.append("%s t=%d %s" % (date, t, bmsg))
        print("  %s  %.1fs/day-equiv  prefix %d/%d ts clean  rerun %s"
              % (date, dt, len(ts) - nbad_t, len(ts),
                 "same" if same else "DIFF"), flush=True)
        if nbad:
            print("    prefix mismatches on this day: %d" % nbad)

    print("\n=== Q1 summary (arm %s) ===" % args.arm)
    print("days: %d" % len(days))
    print("seconds/day: median %.2f  p90 %.2f  max %.2f"
          % (float(np.median(secs)), float(np.percentile(secs, 90)),
             max(secs)))
    print("failures: %d" % len(fails))
    for f in fails[:40]:
        print("  " + f)
    pa_slots.release(slot)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
