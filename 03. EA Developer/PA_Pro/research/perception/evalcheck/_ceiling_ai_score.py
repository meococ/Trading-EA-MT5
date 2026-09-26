"""EVAL-AUDIT AI-ceiling scorer (R76 s.76.3d): score the independent
AI's ceiling-kit drawings against the goldens of the same 10 panels
with the unmodified ruler (eval_v2), then score C-3 on the same
panels for comparison.  n=10 -> descriptive, Wilson CIs.

Conversions (ruling): box -> BOX, line -> PATTERN_LINE,
level -> LEVEL_CARRIED.  Drawing times are chart-clock minutes
(cet_min, same axis as goldens); prices real units -> x1e4 scaled.

Usage: python evalcheck/_ceiling_ai_score.py
"""
import glob
import json
import math
import os
import pickle
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, PERC)

import common as C                              # noqa: E402
import eval as EV                               # noqa: E402
import eval_v2 as V2                            # noqa: E402
import cache as CA                              # noqa: E402
import recall_at_k as RK                        # noqa: E402
from snapshot import live_records               # noqa: E402

KIT = os.path.join(PERC, "ceiling_kit")
AI = os.path.join(KIT, "ai_drawings")
ARM_H = "8361fe85e73f9437"
ARM_V = "uip2_pbbirth"
TOPK = {"box": 1, "level": 1, "line": 2, "bracket": 1}
SC = 1e4

TYPEMAP = {"box": "BOX", "level": "LEVEL_CARRIED", "line": "PATTERN_LINE"}


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, max(0.0, (c - h) / d), min(1.0, (c + h) / d))


def ai_records(drawing, w0, tau):
    """Convert one ai_drawings json to engine-record dicts."""
    out = []
    for o in drawing["objects"]:
        t = TYPEMAP.get(o["type"])
        if t is None:
            continue
        r = {"type": t, "w0": w0, "w1": tau,
             "t0": o["t0"], "t1": o["t1"], "state": "ACTIVE",
             "id": "AI_" + o["type"]}
        if o["type"] == "box":
            r["lo"], r["hi"] = o["p_bot"] * SC, o["p_top"] * SC
        elif o["type"] == "level":
            r["price"] = o["p0"] * SC
        elif o["type"] == "line":
            r["p0"], r["p1"] = o["p0"] * SC, o["p1"] * SC
            r["dirn"] = 1 if o["p1"] >= o["p0"] else -1
        out.append(r)
    return out


def eng_records(rec, m, tau):
    """C-3 engine top-k live records at tau (per-family budget)."""
    f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                     % (ARM_V, ARM_H, rec["date"], tau))
    if not os.path.exists(f):
        # tau not a cached run boundary -> load window-end and
        # truncate live_records at tau
        w1 = rec["window"]["x1"] or 1439
        f = os.path.join(CA.CACHE, "run_%s_%s_%s_%s.pkl"
                         % (ARM_V, ARM_H, rec["date"], w1))
        if not os.path.exists(f):
            return {}
    e = pickle.load(open(f, "rb"))
    w0 = rec["window"]["x0"]
    live, _x = live_records(e, m, w0, tau)
    osc = {o.id: getattr(o, "score", None) for o in e.objects}
    for r in live:
        r["score"] = osc.get(r["id"])
    ranked = RK.rank_live(live, RK.score_map(e))
    out = collections.defaultdict(list)
    for r in ranked:
        fam = EV.FAMILY.get(r["type"])
        if fam and len(out[fam]) < TOPK[fam]:
            out[fam].append(r)
    return out


def score_panel(rec, m, w0, tau, ai_recs, eng_top):
    gobjs, _u, _to = EV.gold_objects(rec)
    per_fam = collections.defaultdict(lambda: [0, 0])
    for g in gobjs:
        fam = EV.FAMILY.get(g["spec_type"])
        if fam not in TOPK or not V2.scorable(g, w0, tau):
            continue
        # golden's own tau: only count goldens at/before the kit tau
        from snapshot import tau_of
        gt = tau_of(g)
        if gt is None or gt > tau:
            continue
        ai_hit = any(V2.match(g, r, m)
                     for r in ai_recs
                     if EV.FAMILY.get(r["type"]) == fam)
        en_hit = any(V2.match(g, r, m) for r in eng_top.get(fam, []))
        per_fam[fam][0] += 0  # placeholder, filled below
        yield fam, g, ai_hit, en_hit


def main():
    recs = {r["id"]: r for r in C.load_tune()}
    rows = []
    for jf in sorted(glob.glob(os.path.join(AI, "ceiling_*.json"))):
        d = json.load(open(jf))
        pid = d["panel"]
        kit = json.load(open(os.path.join(KIT, pid + ".json")))
        tau = kit["tau"]
        rec = recs[pid]
        w0 = rec["window"]["x0"]
        _t, m, _o, _h, _l, _c = CA.bars(rec["date"])
        ai = ai_records(d, w0, tau)
        eng = eng_records(rec, m, tau)
        for fam, g, ah, eh in score_panel(rec, m, w0, tau, ai, eng):
            rows.append((pid, fam, g["spec_type"], ah, eh))
    print("scored goldens: %d" % len(rows))
    print("\n== per family: AI-ceiling vs C-3 hit-rate ==")
    for fam in ("box", "level", "line", "bracket"):
        rr = [r for r in rows if r[1] == fam]
        if not rr:
            continue
        ka = sum(r[3] for r in rr); ke = sum(r[4] for r in rr)
        pa, la, ha = wilson(ka, len(rr))
        pe, le, he = wilson(ke, len(rr))
        print("  %-7s n=%-3d AI %d/%d=%.3f [%.3f,%.3f] | "
              "C-3 %d/%d=%.3f [%.3f,%.3f]"
              % (fam, len(rr), ka, len(rr), pa, la, ha,
                 ke, len(rr), pe, le, he))
    print("\n== per panel ==")
    for pid in sorted(set(r[0] for r in rows)):
        rr = [r for r in rows if r[0] == pid]
        print("  %-6s n=%d AI %d | C-3 %d"
              % (pid, len(rr), sum(r[3] for r in rr), sum(r[4] for r in rr)))
    ka = sum(r[3] for r in rows); ke = sum(r[4] for r in rows)
    pa, la, ha = wilson(ka, len(rows))
    pe, le, he = wilson(ke, len(rows))
    print("\nALL: AI %d/%d=%.3f [%.3f,%.3f] | C-3 %d/%d=%.3f [%.3f,%.3f]"
          % (ka, len(rows), pa, la, ha, ke, len(rows), pe, le, he))


if __name__ == "__main__":
    main()
