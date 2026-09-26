"""run_eval — score the boxlab proposer the way FUNNEL does.

Per TUNE panel: run BoxLabEngine on day bars up to w1 (cached under
boxlab/cache/runs/), convert cand_log with funnel.cand_as_record and
score the oracle ceiling with funnel.cand_right(); born metrics use
eval_v2.eng_objects + the official V2.match / C.match_panel assignment;
legacy eval.py match is reported as an extra column.

Reports: oracle ceiling, born recall, precision, ink/panel, located,
trusted-subset recall, funnel histograms.  Usage:

    python run_eval.py [--tag lab_r1] [--birth-cap N]
"""
import argparse
import collections
import json
import os
import pickle
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PERC = os.path.dirname(_HERE)
_EVALC = os.path.join(_PERC, "evalcheck")
for _p in (_HERE, _PERC, _EVALC, os.path.join(_PERC, "golden"),
           os.path.join(_PERC, "..", "..", "lib")):
    if _p not in sys.path:
        sys.path.insert(0, os.path.abspath(_p))

import pa_slots                     # noqa: E402
import eval as EV                   # noqa: E402
import eval_v2 as V2                # noqa: E402
import common as C                  # noqa: E402
import funnel as FN                 # noqa: E402
import bars_cache as BC             # noqa: E402
import boxes_lab as BL              # noqa: E402

RUNS = os.path.join(_HERE, "cache", "runs")
AUDIT = os.path.join(_HERE, "cache", "box_audit.jsonl")


def trusted_keys():
    out = set()
    if os.path.exists(AUDIT):
        for x in open(AUDIT, encoding="utf8"):
            r = json.loads(x)
            if r.get("trusted"):
                out.add("%s#%d" % (r["panel"], r["idx"]))
    return out


class _Shim:
    """Pickle-safe snapshot of a lab engine run (objects + cand_log)."""
    def __init__(self, e):
        self.objects = e.objects
        self.cand_log = e.cand_log
        self.bars = [0] * len(e.bars)     # only len() is used downstream


def run_lab(tag, rec, params):
    w1 = rec["window"]["x1"] or 1439
    os.makedirs(RUNS, exist_ok=True)
    f = os.path.join(RUNS, "s2_%s_%s_%d.pkl" % (tag, rec["date"], w1))
    if os.path.exists(f) and os.path.getsize(f) > 0:
        try:
            with open(f, "rb") as fh:
                return pickle.load(fh)
        except Exception:
            pass                      # corrupt cache -> recompute
    t, m, o, h, l, c = EV.day_bars(rec["date"])
    e = BL.BoxLabEngine(params)
    for j in np.where(m <= w1)[0]:
        e.update(int(t[j]), float(o[j]) * 1e-4, float(h[j]) * 1e-4,
                 float(l[j]) * 1e-4, float(c[j]) * 1e-4,
                 cet_min=int(m[j]))
    snap = _Shim(e)
    with open(f, "wb") as fh:
        pickle.dump(snap, fh, protocol=4)
    return snap


def eval_panel(rec, e, trusted):
    """One panel -> metric dict for the lab engine."""
    w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
    t, m, o, h, l, c = EV.day_bars(rec["date"])

    gobjs, _un, _to = EV.gold_objects(rec)
    orig_idx = [i for i, o in enumerate(rec["objects"])
                if o.get("status") not in EV.EXCLUDED
                and o.get("spec_type")]
    for g in gobjs:
        if g.get("t0") is None:
            g["t0"] = w0
        if g.get("t1") is None:
            g["t1"] = w1
    gidx = [i for i, g in enumerate(gobjs) if V2.scorable(g, w0, w1)]
    g2 = [gobjs[i] for i in gidx]
    # golden BOX indices (spec_type BOX only — funnel's BOX row)
    gbox = [i for i in gidx if gobjs[i]["spec_type"] == "BOX"]

    cands = []
    for k, cd in enumerate(e.cand_log or []):
        if cd.get("kind") == "LABEL_TF":
            continue
        r = FN.cand_as_record(cd, m, w0, w1)
        if r is not None:
            r["cand_seq"] = k
            r["raw"] = cd
            cands.append(r)
    cbox = [r for r in cands if EV.FAMILY.get(r["type"]) == "box"]

    eobjs = V2.eng_objects(e, m, w0, w1)
    ebox = [r for r in eobjs if EV.FAMILY.get(r["type"]) == "box"]

    # official ruler: assignment on born objects
    pairs, _mp = C.match_panel(g2, ebox, [], [], m,
                               V2.match, V2.match_mark, V2.score)
    born_hit = {gidx[gi] for gi, _ in pairs
                if gobjs[gi]["spec_type"] == "BOX"}
    # born precision: engine box objects matching >=1 golden BOX
    n_born_ok = sum(1 for er in ebox if any(
        V2.match(gobjs[gi], er, m) for gi in gbox))
    # legacy ruler
    pairs_l, _ = C.match_panel(g2, ebox, [], [], m, EV.match,
                               EV.match_mark)
    born_hit_legacy = {gidx[gi] for gi, _ in pairs_l
                       if gobjs[gi]["spec_type"] == "BOX"}

    # oracle + located
    oracle_hit, located_hit, loc_born = set(), set(), set()
    cand_right_of = collections.defaultdict(list)
    for gi in gbox:
        g = gobjs[gi]
        for r in cbox:
            if FN.cand_right(g, r, m):
                oracle_hit.add(gi)
                cand_right_of[gi].append(r)
        for er in ebox:
            if V2.box_located(g, er, m):
                loc_born.add(gi)
        for r in cbox:
            we0, we1 = r["t0"], r["t1"]
            wg0, wg1 = V2._gold_window(g)
            if wg0 is None:
                continue
            if V2._ovcoef(we0, we1, wg0, wg1) >= 0.5 and \
                    FN.edges_pass(g, r) is True:
                located_hit.add(gi)

    # snapshot lens (R13.2/R17.3): tau = golden build_end (else t1);
    # live = born boxes with t_birth <= tau_bar < t_right.  recall@k:
    # top-k live by birth score must contain an eval_v2 match.
    live_tau = []
    rec_at = {1: 0, 2: 0}
    ebox_by_id = {er["id"]: er for er in ebox}
    for gi in gbox:
        g = gobjs[gi]
        wg0, wg1 = V2._gold_window(g)
        tau = wg1 if wg1 is not None else g["t1"]
        tau_bar = int(np.searchsorted(m, tau, side="right")) - 1
        live = [o for o in e.objects
                if o.type == "BOX" and o.t_birth <= tau_bar
                and (o.t_right is None or o.t_right > tau_bar)]
        live_tau.append(len(live))
        live.sort(key=lambda o: -o.geometry.get("score", 0.0))
        for k in rec_at:
            hit = any(ebox_by_id.get(o.id) is not None and
                      V2.match(g, ebox_by_id[o.id], m)
                      for o in live[:k])
            rec_at[k] += int(hit)

    per_gold = {}
    for gi in gbox:
        key = "%s#%d" % (rec["id"], orig_idx[gi])
        per_gold[key] = {
            "trusted": key in trusted,
            "oracle": gi in oracle_hit,
            "born": gi in born_hit,
            "born_legacy": gi in born_hit_legacy,
            "located": gi in located_hit,
        }
    return {"id": rec["id"], "n_gold_box": len(gbox),
            "live_tau_med": float(np.median(live_tau)) if live_tau else 0.0,
            "rec_at1": rec_at[1], "rec_at2": rec_at[2],
            "oracle_hit": len(oracle_hit), "born_hit": len(born_hit),
            "born_hit_legacy": len(born_hit_legacy),
            "located": len(located_hit), "loc_born": len(loc_born),
            "n_cands_box": len(cbox), "n_born_box": len(ebox),
            "born_edges_ok": n_born_ok,
            "per_gold": per_gold,
            "outcomes": collections.Counter(
                str(cd.get("outcome")) for cd in (e.cand_log or [])),
            "cand_feats": [cd for cd in (e.cand_log or [])
                           if cd.get("kind") == "BOX"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="lab_r1")
    ap.add_argument("--params", default=None, help="json overrides")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    params = json.loads(args.params) if args.params else None

    recs = C.load_tune()
    trusted = trusted_keys()
    panels = []
    with pa_slots.slot("boxlab run_eval " + args.tag, timeout=3600):
        for rec in recs:
            e = run_lab(args.tag, rec, params)
            panels.append(eval_panel(rec, e, trusted))
            if not args.quiet:
                print("  %-7s gold=%d oracle=%d born=%d ink=%d cands=%d"
                      % (rec["id"], panels[-1]["n_gold_box"],
                         panels[-1]["oracle_hit"], panels[-1]["born_hit"],
                         panels[-1]["n_born_box"],
                         panels[-1]["n_cands_box"]), flush=True)

    G = sum(p["n_gold_box"] for p in panels)
    OR = sum(p["oracle_hit"] for p in panels)
    BR = sum(p["born_hit"] for p in panels)
    BL_ = sum(p["born_hit_legacy"] for p in panels)
    LOC = sum(p["located"] for p in panels)
    NB = sum(p["n_born_box"] for p in panels)
    NC = sum(p["n_cands_box"] for p in panels)
    t_gold = t_or = t_br = 0
    for p in panels:
        for k, v in p["per_gold"].items():
            if v["trusted"]:
                t_gold += 1
                t_or += v["oracle"]
                t_br += v["born"]
    # precision: born boxes that match any golden BOX
    oc = collections.Counter()
    for p in panels:
        oc.update(p["outcomes"])

    print("\n===== %s =====" % args.tag)
    print("golden BOX: %d" % G)
    print("oracle ceiling: %d/%d = %.3f" % (OR, G, OR / G))
    print("born recall   : %d/%d = %.3f" % (BR, G, BR / G))
    print("born legacy   : %d/%d = %.3f" % (BL_, G, BL_ / G))
    print("located(cand) : %d/%d = %.3f" % (LOC, G, LOC / G))
    print("born boxes    : %d  ink/panel = %.2f" % (NB, NB / len(panels)))
    print("candidates    : %d  (%.2f/panel)" % (NC, NC / len(panels)))
    print("precision est : born_edges_ok=%d -> %.3f"
          % (sum(p["born_edges_ok"] for p in panels),
             sum(p["born_edges_ok"] for p in panels) / max(NB, 1)))
    R1 = sum(p["rec_at1"] for p in panels)
    R2 = sum(p["rec_at2"] for p in panels)
    lv = [p["live_tau_med"] for p in panels if p["n_gold_box"]]
    print("recall@k live : k=1 %d/%d = %.3f   k=2 %d/%d = %.3f"
          % (R1, G, R1 / G, R2, G, R2 / G))
    print("live@tau med  : %.2f boxes (per golden tau)" % np.median(lv))
    print("trusted subset: oracle %d/%d  born %d/%d"
          % (t_or, t_gold, t_br, t_gold))
    print("outcomes      :", dict(oc))

    outp = os.path.join(_HERE, "cache", "eval_%s.json" % args.tag)
    with open(outp, "w", encoding="utf8") as f:
        json.dump({"tag": args.tag, "params": params,
                   "golden": G, "oracle": OR, "born": BR,
                   "born_legacy": BL_, "located": LOC,
                   "n_born": NB, "n_cands": NC,
                   "rec_at1": R1, "rec_at2": R2,
                   "live_tau_med": float(np.median(lv)) if lv else 0.0,
                   "trusted": {"n": t_gold, "oracle": t_or, "born": t_br},
                   "outcomes": dict(oc),
                   "panels": [{k: v for k, v in p.items()
                               if k != "cand_feats"} for p in panels]},
                  f, indent=1)
    print("wrote", outp)


if __name__ == "__main__":
    main()
