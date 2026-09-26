"""DR_LINE_consistency.py — E3b: stability / flicker / determinism.

The part where a machine can BEAT human subjectivity: a professional's
chart should not redraw because the feed started one bar later or a
wick moved 0.3 pip.

Per TUNE panel, run the engine under perturbations of the SAME day:

  base      — unperturbed, twice (determinism check: identical object
              serialization).
  shift k   — drop the first k bars of the day feed (k in 1,2,3,5,10):
              warm-up/seed sensitivity.
  jitter s  — o/h/l/c += U(-0.3, +0.3) pip, seed s in {1,2,3}, then
              re-fix h>=max(o,c), l<=min(o,c): sub-pip feed noise.
  m15       — resample M5->M15 (3-bar groups, o=first,h=max,l=min,
              c=last): timeframe robustness.

Stability metric per golden line/level (the objects this lane owns):
  frac of perturbed runs where a matching engine object exists in the
  panel (eval_v2 match, cumulative-ink semantics — the same ruler the
  fidelity stage uses).

Flicker metrics per run (signal objects only):
  churn/h = (births + closes + re_anchors) / panel hours
  live_flip/h = bars where the live signal set's identity changes
  geo_flip/h = bars where a live object's (p0,slope) mutates
             (re_anchor events)

Outputs: DR_LINE_consistency.jsonl + printed tables.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PERC = os.path.dirname(HERE)
sys.path.insert(0, PERC)
sys.path.insert(0, os.path.join(PERC, "golden"))
sys.path.insert(0, os.path.join(PERC, "evalcheck"))
sys.path.insert(0, os.path.join(PERC, "..", "..", "lib"))

import numpy as np                      # noqa: E402

import eval as EV                      # noqa: E402
import eval_v2 as V2                   # noqa: E402
import common as C                     # noqa: E402
import engine as ENG                   # noqa: E402

OUT = os.path.join(HERE, "DR_LINE_consistency.jsonl")

LANE_TYPES = ("PATTERN_LINE", "CONTEXT_LINE",
              "LEVEL_CARRIED", "MINI_LEVEL")


def run_feed(m, t, o, h, l, c, w1, w0):
    e = ENG.PerceptionEngine()
    e.cand_log = []
    for j in np.where(m <= w1)[0]:
        e.update(int(t[j]), float(o[j]) / 1e4, float(h[j]) / 1e4,
                 float(l[j]) / 1e4, float(c[j]) / 1e4,
                 cet_min=int(m[j]))
    return e


def canon(e, m, w0, w1):
    recs = V2.eng_objects(e, m, w0, w1)
    return json.dumps(recs, sort_keys=True, default=str)


def flicker(e, m, w0, w1):
    """Birth/close/re-anchor counts and live-set transition count for
    signal-class objects inside the panel window."""
    n_birth = n_close = n_reanchor = 0
    for o in e.objects:
        if o.type in ("LABEL_TF", "BAR_MARKER"):
            continue
        tb, tr = o.t_birth, o.t_right
        in_win = lambda j: j is not None and \
            w0 <= int(m[min(j, len(m) - 1)]) <= w1
        if in_win(tb):
            n_birth += 1
        if in_win(tr):
            n_close += 1
        for ev in o.events:
            if ev[1] == "re_anchor" and in_win(ev[0]):
                n_reanchor += 1
    hrs = max((w1 - w0) / 60.0, 0.5)
    return {"birth": n_birth, "close": n_close,
            "reanchor": n_reanchor,
            "churn_h": (n_birth + n_close + n_reanchor) / hrs}


def variants(t, m, o, h, l, c):
    """Yield (name, arrays) for each perturbation.  Prices in pips."""
    yield "base", (t, m, o, h, l, c)
    yield "base2", (t, m, o, h, l, c)
    for k in (1, 2, 3, 5, 10):
        yield "shift%d" % k, (t[k:], m[k:], o[k:], h[k:], l[k:], c[k:])
    for s in (1, 2, 3):
        rng = np.random.RandomState(s)
        jo = o + rng.uniform(-0.3, 0.3, len(o))
        jh = h + rng.uniform(-0.3, 0.3, len(h))
        jl = l + rng.uniform(-0.3, 0.3, len(l))
        jc = c + rng.uniform(-0.3, 0.3, len(c))
        jh = np.maximum.reduce([jh, jo, jc])
        jl = np.minimum.reduce([jl, jo, jc])
        yield "jitter%d" % s, (t, m, jo, jh, jl, jc)
    # M15: group M5 bars in threes
    n15 = len(t) // 3
    t15 = t[:n15 * 3].reshape(-1, 3)[:, 0]
    m15 = m[:n15 * 3].reshape(-1, 3)[:, 0]
    o15 = o[:n15 * 3].reshape(-1, 3)[:, 0]
    h15 = h[:n15 * 3].reshape(-1, 3).max(1)
    l15 = l[:n15 * 3].reshape(-1, 3).min(1)
    c15 = c[:n15 * 3].reshape(-1, 3)[:, 2]
    yield "m15", (t15, m15, o15, h15, l15, c15)


def main():
    recs = C.load_tune()
    rows = []
    det_fail = []
    for k, rec in enumerate(recs):
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        gkeep = [g for g in gobjs
                 if g["spec_type"] in LANE_TYPES
                 and V2.scorable(g, w0, w1)]
        base_hash = None
        for vn, (tt, mm, oo, hh, ll, cc) in variants(t, m, o, h, l, c):
            w1v = w1 if vn != "m15" else w1
            e = run_feed(mm, tt, oo, hh, ll, cc, w1v, w0)
            eobjs = V2.eng_objects(e, mm, w0, w1)
            if vn == "base":
                base_hash = hashlib.sha256(
                    canon(e, mm, w0, w1).encode()).hexdigest()
            if vn == "base2":
                h2 = hashlib.sha256(
                    canon(e, mm, w0, w1).encode()).hexdigest()
                if h2 != base_hash:
                    det_fail.append(rec["id"])
            fl = flicker(e, mm, w0, w1)
            row = {"panel": rec["id"], "variant": vn, "gold": [],
                   **fl}
            for gi, g in enumerate(gkeep):
                hit = any(V2.match(g, eo, mm) for eo in eobjs)
                row["gold"].append(
                    {"gi": gi, "type": g["spec_type"], "hit": hit})
            rows.append(row)
        if (k + 1) % 20 == 0:
            print("panel %d/%d" % (k + 1, len(recs)), flush=True)
    with open(OUT, "w", encoding="utf8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    print("\n=== determinism: %d panels differ on identical re-run ==="
          % len(det_fail))
    if det_fail:
        print(det_fail[:10])
    print("\n=== stability of golden line/level matches ===")
    base_hit = {}
    for r in rows:
        if r["variant"] != "base":
            continue
        for gr in r["gold"]:
            base_hit[(r["panel"], gr["gi"])] = gr["hit"]
    agg = {}
    for r in rows:
        if r["variant"] in ("base", "base2"):
            continue
        for gr in r["gold"]:
            key = gr["type"]
            agg.setdefault(key, []).append(
                ((r["panel"], gr["gi"]), r["variant"], gr["hit"]))
    for tname, lst in agg.items():
        per_g = {}
        for gid, vn, hit in lst:
            per_g.setdefault(gid, []).append(hit)
        stab = {g: sum(v) / len(v) for g, v in per_g.items()}
        matched_base = [g for g in per_g if base_hit.get(g)]
        print("%-14s goldens=%d  matched@base=%d  "
              "mean_stability(all)=%.2f  stability(matched@base)=%.2f"
              % (tname, len(per_g), len(matched_base),
                 sum(stab.values()) / len(stab),
                 sum(stab[g] for g in matched_base)
                 / max(len(matched_base), 1)))
    print("\n=== flicker (churn events/hour, signal objects) ===")
    for vn in ("base", "shift3", "jitter1", "m15"):
        vals = [r["churn_h"] for r in rows if r["variant"] == vn]
        reb = [r["reanchor"] for r in rows if r["variant"] == vn]
        if vals:
            print("%-8s churn/h med=%.2f p90=%.2f  reanchor/panel med=%d"
                  % (vn, float(np.median(vals)),
                     float(np.percentile(vals, 90)),
                     int(np.median(reb))))


if __name__ == "__main__":
    main()
