"""_l4_stab.py — R73 s.73.2 L-4 INFO metrics: jitter / M15 keep-rates
for golden line/level matches, per arm (base, l4_snap, l4_promsnap).

Subset protocol (INFO only, M3 gating pending): every 5th TUNE panel
(~40 panels), variants base + jitter{1,2,3} + m15 mirroring
deepresearch/DR_LINE_consistency.py.  Keep-rate = fraction of
goldens matched at base still matched under the perturbation.

Usage: python _l4_stab.py
"""
import os, sys, json, hashlib
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "evalcheck"))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "lib"))
sys.path.insert(0, _HERE)

import eval as EV                       # noqa: E402
import eval_v2 as V2                   # noqa: E402
import common as C                     # noqa: E402
import _ab_onehash as AB               # noqa: E402

LANE_TYPES = ("PATTERN_LINE", "CONTEXT_LINE",
              "LEVEL_CARRIED", "MINI_LEVEL")
ARMS = ("evb_off", "l4_snap", "l4_promsnap")


def perturbed(t, m, o, h, l, c):
    """Mirror DR_LINE_consistency.variants(): base + jitter + m15."""
    yield "base", (t, m, o, h, l, c)
    for s in (1, 2, 3):
        rng = np.random.RandomState(s)
        jo = o + rng.uniform(-0.3, 0.3, len(o))
        jh = h + rng.uniform(-0.3, 0.3, len(h))
        jl = l + rng.uniform(-0.3, 0.3, len(l))
        jc = c + rng.uniform(-0.3, 0.3, len(c))
        jh = np.maximum.reduce([jh, jo, jc])
        jl = np.minimum.reduce([jl, jo, jc])
        yield "jitter%d" % s, (t, m, jo, jh, jl, jc)
    n15 = len(t) // 3
    yield "m15", (t[:n15 * 3].reshape(-1, 3)[:, 0],
                  m[:n15 * 3].reshape(-1, 3)[:, 0],
                  o[:n15 * 3].reshape(-1, 3)[:, 0],
                  h[:n15 * 3].reshape(-1, 3).max(1),
                  l[:n15 * 3].reshape(-1, 3).min(1),
                  c[:n15 * 3].reshape(-1, 3)[:, 2])


def flicker(e, m, w0, w1):
    n_birth = n_close = n_re = 0
    for ob in e.objects:
        if ob.type in ("LABEL_TF", "BAR_MARKER"):
            continue
        in_win = lambda j: j is not None and \
            w0 <= int(m[min(j, len(m) - 1)]) <= w1
        if in_win(ob.t_birth):
            n_birth += 1
        if in_win(ob.t_right):
            n_close += 1
        for ev in ob.events:
            if ev[1] == "re_anchor" and in_win(ev[0]):
                n_re += 1
    hrs = max((w1 - w0) / 60.0, 0.5)
    return (n_birth + n_close + n_re) / hrs, n_re


def main():
    recs = C.load_tune()
    sub = [r for k, r in enumerate(recs) if k % 5 == 0]
    print("subset panels: %d of %d" % (len(sub), len(recs)), flush=True)
    out = {a: {"keep": {}, "churn": [], "re": [], "det": 0}
           for a in ARMS}
    for k, rec in enumerate(sub):
        w0, w1 = rec["window"]["x0"], rec["window"]["x1"] or 1439
        t, m, o, h, l, c = EV.day_bars(rec["date"])
        gobjs, _u, _to = EV.gold_objects(rec)
        gkeep = [g for g in gobjs
                 if g["spec_type"] in LANE_TYPES
                 and V2.scorable(g, w0, w1)]
        for arm in ARMS:
            base_hit = {}
            canon0 = None
            for vn, (tt, mm, oo, hh, ll, cc) in perturbed(
                    t, m, o, h, l, c):
                e = EV.run_engine(AB.ARMS[arm], mm, tt, oo, hh,
                                  ll, cc, w1, w0=w0)
                eobjs = V2.eng_objects(e, mm, w0, w1)
                hits = {}
                for gi, g in enumerate(gkeep):
                    hits[gi] = any(V2.match(g, eo, mm)
                                   for eo in eobjs)
                ch, re_ = flicker(e, mm, w0, w1)
                if vn == "base":
                    base_hit = hits
                    canon0 = hashlib.sha256(json.dumps(
                        eobjs, sort_keys=True,
                        default=str).encode()).hexdigest()
                    out[arm]["churn"].append(ch)
                    out[arm]["re"].append(re_)
                    continue
                for gi, was in base_hit.items():
                    if not was:
                        continue
                    key = (gkeep[gi]["spec_type"], vn)
                    out[arm]["keep"].setdefault(key, []).append(
                        1 if hits.get(gi) else 0)
                if vn == "jitter1":
                    h2 = hashlib.sha256(json.dumps(
                        eobjs, sort_keys=True,
                        default=str).encode()).hexdigest()
                    # jitter must differ; track same-canon anomalies
                    if h2 == canon0:
                        out[arm]["det"] += 1
        if (k + 1) % 10 == 0:
            print("panel %d/%d" % (k + 1, len(sub)), flush=True)
    print("\n=== L-4 stability (keep-rate of base-matched goldens) ===")
    for arm in ARMS:
        d = out[arm]
        print("\n-- %s --" % arm)
        for (typ, vn), v in sorted(d["keep"].items()):
            print("  %-14s %-7s keep %d/%d = %.2f"
                  % (typ, vn, sum(v), len(v),
                     sum(v) / len(v) if v else 0))
        jk = [x for (ty, vn), v in d["keep"].items()
              if vn.startswith("jitter") for x in v]
        mk = [x for (ty, vn), v in d["keep"].items()
              if vn == "m15" for x in v]
        print("  ALL jitter keep %.2f (%d) | m15 keep %.2f (%d)"
              % (sum(jk) / len(jk) if jk else 0, len(jk),
                 sum(mk) / len(mk) if mk else 0, len(mk)))
        print("  churn/h med %.2f | reanchor/panel med %d | "
              "jitter-same-canon %d"
              % (float(np.median(d["churn"])),
                 int(np.median(d["re"])), d["det"]))


if __name__ == "__main__":
    main()
