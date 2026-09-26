"""snapshot.py — mandate 3, Z2: snapshot fidelity at decision time.

Cumulative-ink metrics ask "was the object ever drawn?"; snapshot
metrics ask "at the moment the golden author decided, was a matching
object live, and how cluttered was the chart?"

Decision time tau (CET minutes), per mandate Z2:
  BOX            : build_end, else drawn t1
  PATTERN_LINE / CONTEXT_LINE : build_end (closest annotated proxy for
                   "last touch before break" — golden carries no touch
                   list), else t1
  LEVEL_CARRIED / RANGE_OPEN / MINI_LEVEL : t0 + 10 min
  BRACKET        : t1
  SQUEEZE        : t1 ;  BAR_MARKER : t0
  LABEL_TF mark  : mark time t

For each tau we re-run the engine feeding only bars <= tau (cache.run,
keyed by (hash, date, w1=tau)) — the run is causal, so e.objects at
tau is exactly the live book.  "Live" = state != DELETED.

  snapshot recall    : fraction of scorable golden objects whose tau
                       state has a live engine object matching under
                       eval_v2 (match() with w1=tau).
  snapshot precision : pooled over all decision events —
                       live signal-class objects matching some golden
                       object alive then / all live signal objects.
  live clutter       : median live signal-class count per decision
                       event.

Engines: v0, current v1, LINE-LAB prototype (linelab/lines_lab.py,
read-only — line types only).  BOX-LAB has no runnable prototype yet.

Usage: python evalcheck/snapshot.py [--limit N]
"""
import argparse
import collections
import hashlib
import json
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "linelab"))

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import funnel as F                              # noqa: E402
import pa_slots                                 # noqa: E402

LINE_T = ("PATTERN_LINE", "CONTEXT_LINE")
LEVEL_T = ("LEVEL_CARRIED", "RANGE_OPEN", "MINI_LEVEL")


def tau_of(g):
    """Decision time (CET minute) for one golden object."""
    st = g["spec_type"]
    if st == "BOX" or st in LINE_T:
        return g.get("build_end") if g.get("build_end") is not None \
            else g.get("t1")
    if st in LEVEL_T:
        return (g["t0"] + 10) if g.get("t0") is not None else None
    if st in ("BRACKET", "SQUEEZE"):
        return g.get("t1")
    if st == "BAR_MARKER":
        return g.get("t0")
    return g.get("t1") if g.get("t1") is not None else g.get("t0")


def live_records(e, m, w0, tau):
    """Engine records live at tau: born objects not DELETED."""
    live = [o for o in e.objects if o.state != "DELETED"]
    shim = types.SimpleNamespace(objects=live, bars=e.bars)
    recs = V2.eng_objects(shim, m, w0, tau)
    return [r for r in recs if r["type"] != "LABEL_TF"], \
        [r for r in recs if r["type"] == "LABEL_TF"]


def run_diag(tag, cls, eng_hash, recs, store=True):
    """Per-engine snapshot metrics.  Returns report dict + rows."""
    rows = []
    events = []          # (tau, n_live, n_live_hit)
    cum_gold = collections.Counter()     # cumulative-ink denominators
    cum_hit = collections.Counter()
    snap_gold = collections.Counter()
    snap_hit = collections.Counter()
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        gmarks = [gm for gm in EV.gold_marks(rec)
                  if V2.scorable_mark(gm, w0, w1)]
        # cumulative-ink reference: full-panel run
        efull = CA.run(eng_hash, cls, rec, store=store)
        ebox_full = [r for r in V2.eng_objects(efull, m, w0, w1)
                     if r["type"] != "LABEL_TF"]
        for g in g2:
            st = g["spec_type"]
            cum_gold[st] += 1
            if any(V2.match(g, er, m) for er in ebox_full):
                cum_hit[st] += 1
        # group golden objects by decision time
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            by_tau[min(tau, w1)].append(g)
        for gm in gmarks:
            if gm.get("t") is not None and w0 <= gm["t"] <= w1:
                by_tau[gm["t"]].append(gm)
        for tau, gs in by_tau.items():
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t, store=store)
            eboxes, emarks = live_records(e_t, m, w0, tau)
            gold_alive = [g for g in g2
                          if (g.get("t0") or w0) <= tau
                          <= (g.get("t1") or 1439)]
            mark_alive = [gm for gm in gmarks
                          if gm.get("t") is not None and gm["t"] <= tau]
            live_all = eboxes + emarks
            n_hit = 0
            for er in eboxes:
                if any(V2.match(g, er, m) for g in gold_alive):
                    n_hit += 1
            for em in emarks:
                if any(V2.match_mark(gm, em) for gm in mark_alive):
                    n_hit += 1
            events.append((tau, len(live_all), n_hit))
            for g in gs:
                if g.get("spec_type") is None:     # mark record
                    snap_gold["LABEL_TF"] += 1
                    ok = any(V2.match_mark(g, em) for em in emarks)
                    snap_hit["LABEL_TF"] += bool(ok)
                    rows.append({"engine": tag, "panel": rec["id"],
                                 "type": "LABEL_TF", "tau": tau,
                                 "hit": bool(ok)})
                    continue
                st = g["spec_type"]
                snap_gold[st] += 1
                ok = any(V2.match(g, er, m) for er in eboxes)
                snap_hit[st] += bool(ok)
                rows.append({"engine": tag, "panel": rec["id"],
                             "type": st, "tau": tau, "hit": bool(ok)})
    return {"tag": tag, "hash": eng_hash,
            "snap_gold": snap_gold, "snap_hit": snap_hit,
            "cum_gold": cum_gold, "cum_hit": cum_hit,
            "events": events}, rows


def file_hash(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def pct(a, b):
    return "%.2f" % (a / b) if b else "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    import engine as ENG_V1
    import engine_v0 as ENG_V0
    recs = C.load_tune()
    if args.limit:
        recs = recs[:args.limit]

    engines = [("v0", ENG_V0.PerceptionEngine,
                F.code_hash(F.V0_FILES)),
               ("v1", ENG_V1.PerceptionEngine,
                F.code_hash(F.V1_FILES))]
    try:
        import lines_lab
        engines.append(("linelab", lines_lab.LineLabEngine,
                        file_hash(os.path.join(PERC, "linelab",
                                               "lines_lab.py"))))
    except Exception as ex:
        print("linelab unavailable:", ex)

    all_rows = []
    out = ["# SNAPSHOT — fidelity at decision time (mandate Z2)", ""]
    out.append("tau: BOX/lines = build_end else t1 ; levels = t0+10 ; "
               "BRACKET/SQUEEZE = t1 ; BAR_MARKER = t0 ; T/F = mark t.")
    out.append("`live` = engine run fed only bars <= tau, objects not "
               "DELETED.  Ruler = eval_v2 with w1=tau.")
    out.append("")
    with pa_slots.slot("evalcheck-snapshot", timeout=1800):
        for tag, cls, h in engines:
            res, rows = run_diag(tag, cls, h, recs,
                                 store=(tag != "linelab"))
            all_rows += rows
            ev = res["events"]
            clutter = float(np.median([e[1] for e in ev])) if ev else 0
            prec = (sum(e[2] for e in ev) / max(sum(e[1] for e in ev), 1))
            out.append("## %s (`%s`)" % (tag, h))
            out.append("")
            out.append("| type | snap recall | cumul-ink recall | n |")
            out.append("|---|---|---|---|")
            for st in sorted(set(res["snap_gold"]) |
                             set(res["cum_gold"])):
                out.append("| %s | %s | %s | %d |"
                           % (st, pct(res["snap_hit"][st],
                                      res["snap_gold"][st]),
                              pct(res["cum_hit"][st],
                                  res["cum_gold"][st]),
                              res["snap_gold"][st]))
            out.append("")
            out.append("snapshot precision (pooled over %d decision "
                       "events): **%.2f** ; live clutter median = "
                       "**%.1f** objects" % (len(ev), prec, clutter))
            out.append("")
            print("%s done: %d events, prec %.2f, clutter %.1f"
                  % (tag, len(ev), prec, clutter), flush=True)

    out.append("## snapshot vs cumulative-ink — the difference in "
               "five lines")
    out.append("")
    out.append("Cumulative-ink credit = the object existed at ANY point "
               "in the panel, even born after the golden decision or "
               "re-anchored later.  Snapshot credit = the object was "
               "live, with its at-that-moment geometry, exactly when "
               "the golden author decided.  A late-born or drifting "
               "object earns ink credit but no snapshot credit.  "
               "Snapshot precision also penalizes clutter that "
               "cumulative precision dilutes over the whole panel.  "
               "So snapshot <= cumulative on recall, and the gap "
               "measures how much of the engine's ink is hindsight.")
    open(os.path.join(HERE, "SNAPSHOT.md"), "w",
         encoding="utf8").write("\n".join(out) + "\n")
    with open(os.path.join(HERE, "_snapshot_rows.jsonl"), "w",
              encoding="utf8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r) + "\n")
    print("wrote SNAPSHOT.md + _snapshot_rows.jsonl")


if __name__ == "__main__":
    main()
