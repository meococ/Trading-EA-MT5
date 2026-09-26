"""_ab_report.py — paired A/B report for R14 §14.2/§14.3.

Usage: python _ab_report.py <hashA> <hashB> [labelA labelB]

Both arms must already be in evalcheck/_cache (run scoreboard.py or
the engine over all panels first). Prints, per arm:
  - cumulative recall per family (matched / golden, counts)
  - clutter ratio per panel (engine objects / golden objects), median
  - snapshot live clutter median + snapshot recall
  - births per kind (engine object counts inside panel windows)
"""
import collections
import json
import sys

sys.path.insert(0, "evalcheck")
sys.path.insert(0, ".")

import numpy as np

import common as C
import eval as EV
import eval_v2 as V2
import cache as CA
import funnel as F
from snapshot import tau_of, live_records


def measure(eng_hash, cls):
    recs = C.load_tune()
    hit_g = collections.Counter()
    gold_n = collections.Counter()
    eng_n = collections.Counter()
    born_kind = collections.Counter()
    clutter = []
    ratio = []
    snap_g = 0
    snap_h = 0
    for rec in recs:
        w0 = rec["window"]["x0"]
        w1 = rec["window"]["x1"] or 1439
        t, m, o, h, l, c = CA.bars(rec["date"])
        e = CA.run(eng_hash, cls, rec)
        gobjs, _u, _to = EV.gold_objects(rec)
        g2 = [g for g in gobjs if V2.scorable(g, w0, w1)]
        eobjs = V2.eng_objects(e, m, w0, w1)
        eboxes = [r for r in eobjs if r["type"] != "LABEL_TF"]
        pairs, _mp = C.match_panel(g2, eboxes, [], [], m,
                                   V2.match, V2.match_mark, V2.score)
        hg = {gi for gi, _ in pairs}
        for gi, g in enumerate(g2):
            gold_n[g["spec_type"]] += 1
            hit_g[g["spec_type"]] += gi in hg
        for er in eboxes:
            eng_n[er["type"]] += 1
        for cd in e.cand_log or []:
            if cd.get("outcome") == "born":
                born_kind[cd["kind"]] += 1
        n_g = len(g2)
        n_e = len(eboxes)
        if n_g:
            ratio.append(n_e / n_g)
        by_tau = collections.defaultdict(list)
        for g in g2:
            tau = tau_of(g)
            if tau is None or tau < w0:
                continue
            by_tau[min(tau, w1)].append(g)
        for tau, gs in by_tau.items():
            rec_t = dict(rec)
            rec_t["window"] = dict(rec["window"], x1=tau)
            e_t = CA.run(eng_hash, cls, rec_t)
            eboxes_t, _em = live_records(e_t, m, w0, tau)
            clutter.append(len(eboxes_t))
            for g in gs:
                snap_g += 1
                snap_h += any(V2.match(g, er, m) for er in eboxes_t)
    return {"hit_g": hit_g, "gold_n": gold_n, "eng_n": eng_n,
            "born": born_kind, "clutter": clutter, "ratio": ratio,
            "snap_g": snap_g, "snap_h": snap_h}


def report(tag, r):
    print("\n=== arm %s ===" % tag)
    for st in sorted(r["gold_n"]):
        g, h = r["gold_n"][st], r["hit_g"][st]
        print("  %-14s recall %3d/%-3d = %.3f" % (st, h, g,
                                                  h / g if g else 0))
    print("  engine objects/panel-window:",
          dict(r["eng_n"].most_common()))
    print("  births (cand_log born):",
          dict(r["born"].most_common()))
    print("  clutter live@tau median %.2f | snap recall %d/%d = %.3f"
          % (np.median(r["clutter"]), r["snap_h"], r["snap_g"],
             r["snap_h"] / r["snap_g"] if r["snap_g"] else 0))
    print("  clutter ratio (eng/golden per panel) median %.3f p90 %.3f"
          % (np.median(r["ratio"]), np.percentile(r["ratio"], 90)))


def main():
    ha, hb = sys.argv[1], sys.argv[2]
    la = sys.argv[3] if len(sys.argv) > 3 else "A:" + ha[:8]
    lb = sys.argv[4] if len(sys.argv) > 4 else "B:" + hb[:8]
    import engine
    cls = engine.PerceptionEngine
    report(la, measure(ha, cls))
    report(lb, measure(hb, cls))


if __name__ == "__main__":
    main()
